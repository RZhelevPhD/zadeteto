"""
Stage 1 of the Outscraper → Supabase ingest pipeline.

Reads an Outscraper XLSX export, visits each Google Maps URL from the
`location_link` column, and extracts the canonical data the source file is
missing: clean business name, full address, category, rating, review count.

Latitude and longitude are parsed directly from each URL's `!3d<lat>!4d<lng>`
segment — no page scraping needed for coords. A stable `legacy_id` is derived
from the Place ID segment `!1s<hex>:<hex>` (format: `os-<hex_tail>`).

Output CSV: tmp/gmaps_by_url.csv
Checkpoint: tmp/gmaps_url_checkpoint.json (resumable via --resume)

Usage:
    python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --resume
    python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --resume --limit 100
    python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --resume --headed
    python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --resume --retry-failed
"""
from __future__ import annotations

import re
import os
import csv
import sys
import json
import asyncio
import random
import argparse

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

VIEWPORT = {"width": 1280, "height": 900}
PAGE_PAUSE_MIN = 2.0
PAGE_PAUSE_MAX = 4.0
DETAIL_TIMEOUT_MS = 15000

OUTPUT_COLUMNS = [
    "legacy_id", "name", "address", "city",
    "lat", "lng", "category", "rating",
    "reviews_count", "phone", "maps_url",
]

OUTPUT_PATH = os.path.join("tmp", "gmaps_by_url.csv")
CHECKPOINT_PATH = os.path.join("tmp", "gmaps_url_checkpoint.json")

LATLNG_RE = re.compile(r"!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)")
PLACEID_RE = re.compile(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)")


def parse_latlng(url: str) -> tuple[float | None, float | None]:
    """Extract lat/lng from the !3d!4d segment of a Google Maps place URL."""
    m = LATLNG_RE.search(url)
    if not m:
        return None, None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None, None


def parse_legacy_id(url: str) -> str | None:
    """
    Derive a stable ID from the Place ID segment !1s<hex>:<hex>.
    Uses the second hex (the CID) which is the canonical place identifier.
    Returns None if the URL does not contain a recognizable Place ID.
    """
    m = PLACEID_RE.search(url)
    if not m:
        return None
    pid = m.group(1)
    cid = pid.split(":", 1)[1] if ":" in pid else pid
    return f"os-{cid.lower().removeprefix('0x')}"


def load_urls_from_xlsx(path: str) -> list[str]:
    """Read the `location_link` column from an Outscraper XLSX export."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    headers = None
    urls = []
    for row in ws.iter_rows(values_only=True):
        if headers is None:
            headers = [str(c).strip() if c is not None else "" for c in row]
            if "location_link" not in headers:
                wb.close()
                raise ValueError(
                    f"Input file missing 'location_link' column. Found: {headers}"
                )
            link_idx = headers.index("location_link")
            continue
        val = row[link_idx] if link_idx < len(row) else None
        if val and isinstance(val, str) and val.startswith("http"):
            urls.append(val.strip())
    wb.close()
    return urls


def load_checkpoint() -> dict:
    """
    Checkpoint shape:
      {
        "done": {"<legacy_id>": {<output_row_dict>}},
        "failed": {"<legacy_id>": "<error>"}
      }
    Rows in `done` will be written to the output CSV on every run.
    Rows in `failed` are skipped on --resume.
    """
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "done": data.get("done", {}),
                "failed": data.get("failed", {}),
            }
    return {"done": {}, "failed": {}}


def save_checkpoint(ckpt: dict) -> None:
    os.makedirs(os.path.dirname(CHECKPOINT_PATH) or ".", exist_ok=True)
    tmp_path = CHECKPOINT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(ckpt, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CHECKPOINT_PATH)


async def _dismiss_consent(page) -> None:
    consent_selectors = [
        'button[aria-label*="Приеми всички"]',
        'button[aria-label*="Приеми"]',
        'button[aria-label*="Accept all"]',
        'button[aria-label*="Agree to all"]',
        'form[action*="consent"] button',
        '#L2AGLb',
    ]
    for selector in consent_selectors:
        try:
            btn = page.locator(selector).first
            if await btn.count() > 0:
                await btn.click()
                await page.wait_for_timeout(1500)
                return
        except Exception:
            continue


async def _text_or_empty(locator) -> str:
    try:
        if await locator.count() == 0:
            return ""
        return (await locator.first.inner_text()).strip()
    except Exception:
        return ""


async def _attr_or_empty(locator, attr: str) -> str:
    try:
        if await locator.count() == 0:
            return ""
        val = await locator.first.get_attribute(attr)
        return (val or "").strip()
    except Exception:
        return ""


async def extract_detail(page) -> dict:
    """
    Extract fields from the Google Maps place detail panel.

    Google Maps markup is notoriously volatile — every selector below has a
    fallback (aria-label based, then class-based, then text-based). If Google
    changes the DOM, update this function first.
    """
    # Wait for the place heading to appear — the clearest signal the detail
    # panel has loaded.
    try:
        await page.wait_for_selector("h1.DUwDvf, h1", timeout=DETAIL_TIMEOUT_MS)
    except PlaywrightTimeout:
        return {}

    name = await _text_or_empty(page.locator("h1.DUwDvf"))
    if not name:
        name = await _text_or_empty(page.locator("h1").first)

    # Category sits in a button next to the rating on the detail page.
    category = await _text_or_empty(page.locator('button[jsaction*="category"]'))

    # Address: the Maps UI exposes address as a button with aria-label that
    # starts with "Адрес:" (Bulgarian) or "Address:" (English).
    address = ""
    for aria_prefix in ("Адрес:", "Address:"):
        loc = page.locator(f'button[aria-label^="{aria_prefix}"]')
        if await loc.count() > 0:
            label = await _attr_or_empty(loc, "aria-label")
            address = label.split(":", 1)[1].strip() if ":" in label else label
            break
    if not address:
        # Fallback: any button with data-item-id="address"
        address = await _text_or_empty(page.locator('button[data-item-id="address"]'))

    # Phone: aria-label starts with "Телефон:" (bg) or "Phone:" (en).
    phone = ""
    for aria_prefix in ("Телефон:", "Phone:"):
        loc = page.locator(f'button[aria-label^="{aria_prefix}"]')
        if await loc.count() > 0:
            label = await _attr_or_empty(loc, "aria-label")
            phone = label.split(":", 1)[1].strip() if ":" in label else label
            break
    if not phone:
        phone = await _text_or_empty(page.locator('button[data-item-id^="phone"]'))

    # Rating: the span directly under the heading, format "4,5" or "4.5".
    rating = ""
    rating_el = page.locator('div.F7nice span[aria-hidden="true"]').first
    if await rating_el.count() > 0:
        rating_text = (await rating_el.inner_text()).strip()
        m = re.search(r"([\d,\.]+)", rating_text)
        if m:
            rating = m.group(1).replace(",", ".")

    # Review count: sibling span with aria-label like "1 234 отзива" or "reviews".
    reviews_count = ""
    reviews_el = page.locator(
        'div.F7nice span[aria-label*="отзива"], '
        'div.F7nice span[aria-label*="reviews"], '
        'div.F7nice span[aria-label*="рецензии"]'
    ).first
    if await reviews_el.count() > 0:
        aria = await reviews_el.get_attribute("aria-label") or ""
        m = re.search(r"([\d\s\xa0,]+)", aria)
        if m:
            reviews_count = re.sub(r"[\s\xa0,]", "", m.group(1))

    return {
        "name": name,
        "category": category,
        "address": address,
        "phone": phone,
        "rating": rating,
        "reviews_count": reviews_count,
    }


async def scrape_one(page, url: str) -> dict | None:
    """Navigate to a single place URL and return a row dict, or None on failure."""
    legacy_id = parse_legacy_id(url)
    lat, lng = parse_latlng(url)
    if not legacy_id:
        print(f"  SKIP: no Place ID in URL")
        return None

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except PlaywrightTimeout:
        print(f"  TIMEOUT: page navigation for {legacy_id}")
        return None
    except Exception as e:
        print(f"  NAV ERROR ({legacy_id}): {e}")
        return None

    await page.wait_for_timeout(1200)
    await _dismiss_consent(page)

    detail = await extract_detail(page)
    if not detail or not detail.get("name"):
        print(f"  NO DETAIL: {legacy_id}")
        return None

    return {
        "legacy_id": legacy_id,
        "name": detail["name"],
        "address": detail["address"],
        "city": "София",
        "lat": f"{lat}" if lat is not None else "",
        "lng": f"{lng}" if lng is not None else "",
        "category": detail["category"],
        "rating": detail["rating"],
        "reviews_count": detail["reviews_count"],
        "phone": detail["phone"],
        "maps_url": url,
    }


async def scrape_all(urls: list[str], headed: bool, limit: int | None, resume: bool) -> None:
    ckpt = load_checkpoint() if resume else {"done": {}, "failed": {}}

    os.makedirs("tmp", exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=not headed,
            args=["--lang=bg-BG,bg", "--no-sandbox"],
        )
        context = await browser.new_context(
            viewport=VIEWPORT,
            user_agent=random.choice(UA_POOL),
            locale="bg-BG",
            timezone_id="Europe/Sofia",
        )
        page = await context.new_page()

        processed = 0
        scraped = 0
        skipped = 0

        for idx, url in enumerate(urls, start=1):
            if limit is not None and processed >= limit:
                break

            legacy_id = parse_legacy_id(url)
            if resume and legacy_id and (legacy_id in ckpt["done"] or legacy_id in ckpt["failed"]):
                skipped += 1
                continue

            print(f"[{idx}/{len(urls)}] {legacy_id or 'no-id'}")
            row = await scrape_one(page, url)
            processed += 1

            if row:
                ckpt["done"][row["legacy_id"]] = row
                scraped += 1
            elif legacy_id:
                ckpt["failed"][legacy_id] = "extract_failed"

            # Persist checkpoint every 10 rows to survive crashes.
            if processed % 10 == 0:
                save_checkpoint(ckpt)
                print(f"  checkpoint saved: {scraped} scraped, {len(ckpt['failed'])} failed")

            pause_ms = int(random.uniform(PAGE_PAUSE_MIN, PAGE_PAUSE_MAX) * 1000)
            await page.wait_for_timeout(pause_ms)

        await browser.close()

    save_checkpoint(ckpt)

    # Write the output CSV from every successfully scraped row in the checkpoint.
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in ckpt["done"].values():
            writer.writerow(row)

    print(f"\nDone. scraped={scraped} skipped={skipped} failed={len(ckpt['failed'])}")
    print(f"OUTPUT_CSV:{OUTPUT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Google Maps detail pages by URL list (stage 1 of Outscraper ingest)"
    )
    parser.add_argument("--input", required=True, help="Path to Outscraper XLSX export")
    parser.add_argument("--resume", action="store_true", help="Skip URLs already in the checkpoint")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N URLs (for smoke tests)")
    parser.add_argument("--headed", action="store_true", help="Show browser window (default: headless)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input file not found: {args.input}")
        sys.exit(1)

    urls = load_urls_from_xlsx(args.input)
    if not urls:
        print("ERROR: no URLs found in the `location_link` column")
        sys.exit(1)

    print(f"Loaded {len(urls)} URLs from {args.input}")
    if args.limit:
        print(f"Limit: {args.limit}")
    if args.resume:
        print("Resume mode: skipping URLs already in checkpoint")

    asyncio.run(scrape_all(urls, headed=args.headed, limit=args.limit, resume=args.resume))


if __name__ == "__main__":
    main()
