import re
import os
import csv
import sys
import json
import asyncio
import random
import argparse
from datetime import datetime
from urllib.parse import quote

import pandas as pd

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
SCROLL_PAUSE_MIN = 1.0
SCROLL_PAUSE_MAX = 3.0
MAX_SCROLL_ATTEMPTS = 40
NO_NEW_RESULTS_THRESHOLD = 3

OUTPUT_COLUMNS = [
    "name", "category", "address", "city",
    "phone", "website", "rating", "reviews", "google maps url",
]


async def _dismiss_consent(page):
    consent_selectors = [
        'button[aria-label*="Приеми всички"]',
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


async def _extract_card(card, city: str) -> dict | None:
    try:
        name_el = card.locator("a[aria-label]").first
        if await name_el.count() == 0:
            name_el = card.locator("h3").first
        if await name_el.count() == 0:
            return None

        name = (await name_el.get_attribute("aria-label") or "").strip()
        if not name:
            name = (await name_el.inner_text()).strip()
        if not name:
            return None

        maps_url = (await name_el.get_attribute("href") or "").strip()
        if not maps_url:
            link_el = card.locator('a[href*="/maps/place/"]').first
            if await link_el.count() > 0:
                maps_url = (await link_el.get_attribute("href") or "").strip()

        category = ""
        address = ""
        info_el = card.locator("div.fontBodyMedium").first
        if await info_el.count() > 0:
            info_text = await info_el.inner_text()
            parts = [p.strip() for p in re.split(r"[·\n]", info_text) if p.strip()]
            if len(parts) >= 2:
                category = parts[0]
                address = parts[1]
            elif len(parts) == 1:
                category = parts[0]
        if not category:
            full_text = await card.inner_text()
            lines = [l.strip() for l in full_text.splitlines() if l.strip()]
            if len(lines) >= 2:
                category = lines[1]

        rating = ""
        rating_el = card.locator('span[aria-label*="звезди"], span[aria-label*="stars"]').first
        if await rating_el.count() > 0:
            aria = await rating_el.get_attribute("aria-label") or ""
            m = re.search(r"([\d,\.]+)", aria)
            if m:
                rating = m.group(1).replace(",", ".")
        if not rating:
            m = re.search(r"\b([1-5][,\.]\d)\b", await card.inner_text())
            if m:
                rating = m.group(1).replace(",", ".")

        reviews = ""
        reviews_el = card.locator('span[aria-label*="отзива"], span[aria-label*="reviews"], span[aria-label*="рецензии"]').first
        if await reviews_el.count() > 0:
            aria = await reviews_el.get_attribute("aria-label") or ""
            m = re.search(r"([\d\s\xa0]+)", aria)
            if m:
                reviews = re.sub(r"\s+", "", m.group(1)).strip()
        if not reviews:
            m = re.search(r"\(([\d\s\xa0,]+)\)", await card.inner_text())
            if m:
                reviews = re.sub(r"[\s\xa0,]", "", m.group(1))

        website = ""
        website_el = card.locator('a[data-item-id="authority"]').first
        if await website_el.count() > 0:
            website = (await website_el.get_attribute("href") or "").strip()
        if not website:
            website_el2 = card.locator('a[href^="http"]:not([href*="google"])').first
            if await website_el2.count() > 0:
                href = (await website_el2.get_attribute("href") or "").strip()
                if href and "maps" not in href and "goo.gl" not in href:
                    website = href

        return {
            "name": name,
            "category": category,
            "address": address,
            "city": city,
            "phone": "",
            "website": website,
            "rating": rating,
            "reviews": reviews,
            "google maps url": maps_url,
        }

    except Exception as e:
        print(f"    SKIP card: {e}")
        return None


async def scrape(keyword: str, city: str, headed: bool = False) -> list[dict]:
    results = []

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

        search_query = f"{keyword} {city}"
        url = f"https://www.google.com/maps/search/{quote(search_query)}"
        print(f"  Navigating to Google Maps: {search_query}")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        await _dismiss_consent(page)

        try:
            await page.wait_for_selector('div[role="feed"]', timeout=15000)
        except PlaywrightTimeout:
            print(f"  WARNING: Results feed not found for '{search_query}'. Zero results or CAPTCHA.")
            await browser.close()
            return []

        feed = page.locator('div[role="feed"]')
        prev_count = 0
        no_new_streak = 0

        print("  Scrolling results...")
        for attempt in range(MAX_SCROLL_ATTEMPTS):
            cards = page.locator('div[role="feed"] > div')
            current_count = await cards.count()

            if current_count == prev_count:
                no_new_streak += 1
                if no_new_streak >= NO_NEW_RESULTS_THRESHOLD:
                    print(f"  No new results after {NO_NEW_RESULTS_THRESHOLD} scrolls — done.")
                    break
            else:
                no_new_streak = 0
                prev_count = current_count

            end_sentinel = page.locator('span.HlvSq, p:has-text("края на списъка"), p:has-text("end of the list")')
            if await end_sentinel.count() > 0:
                print("  Reached end of list.")
                break

            await feed.evaluate("el => el.scrollBy(0, 600)")
            pause = random.uniform(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX) * 1000
            await page.wait_for_timeout(pause)

        cards = page.locator('div[role="feed"] > div')
        total_cards = await cards.count()
        print(f"  Extracting {total_cards} cards...")

        for i in range(total_cards):
            card = cards.nth(i)
            result = await _extract_card(card, city)
            if result and result["name"]:
                results.append(result)

        await browser.close()

    print(f"  Extracted {len(results)} valid results.")
    return results


def save_to_csv(results: list[dict], keyword: str, city: str) -> str:
    os.makedirs("tmp", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw = re.sub(r"[^\w\-]", "_", keyword.strip())
    safe_city = re.sub(r"[^\w\-]", "_", city.strip())
    path = os.path.join("tmp", f"scraped_{safe_kw}_{safe_city}_{ts}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    return path


def load_checkpoint(path: str) -> set:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(tuple(pair) for pair in data.get("done", []))
    return set()


def save_checkpoint(done_pairs: set, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"done": [list(p) for p in done_pairs]}, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Scrape Google Maps leads by keyword and city")
    parser.add_argument("--keyword", help="Search keyword (e.g. 'детска градина')")
    parser.add_argument("--city", help="City name (e.g. 'София')")
    parser.add_argument("--input", help="CSV/Excel file with 'keyword' and 'city' columns for batch mode")
    parser.add_argument("--headed", action="store_true", help="Show browser window (default: headless)")
    parser.add_argument("--resume", action="store_true", help="Skip already-completed keyword/city pairs")
    args = parser.parse_args()

    if args.input:
        ext = os.path.splitext(args.input)[1].lower()
        if ext == ".csv":
            kw_df = pd.read_csv(args.input, encoding="utf-8-sig")
        else:
            kw_df = pd.read_excel(args.input)
        kw_df.columns = [c.strip().lower() for c in kw_df.columns]
        if "keyword" not in kw_df.columns or "city" not in kw_df.columns:
            print("ERROR: Input file must have 'keyword' and 'city' columns.")
            sys.exit(1)
        pairs = [(str(r["keyword"]), str(r["city"])) for _, r in kw_df.iterrows()]
    elif args.keyword and args.city:
        pairs = [(args.keyword, args.city)]
    else:
        parser.error("Provide --keyword and --city, or --input with a keywords file.")

    checkpoint_path = os.path.join("tmp", "scrape_checkpoint.json")
    done = load_checkpoint(checkpoint_path) if args.resume else set()

    all_output_paths = []

    for keyword, city in pairs:
        pair_key = (keyword, city)
        if args.resume and pair_key in done:
            print(f"Skipping (already done): {keyword} / {city}")
            continue

        print(f"\nScraping: '{keyword}' in '{city}'")
        results = asyncio.run(scrape(keyword, city, headed=args.headed))

        if results:
            path = save_to_csv(results, keyword, city)
            print(f"  Saved {len(results)} results -> {path}")
            all_output_paths.append(path)
        else:
            print(f"  No results for '{keyword}' in '{city}' — skipping.")

        done.add(pair_key)
        save_checkpoint(done, checkpoint_path)

    for p in all_output_paths:
        print(f"OUTPUT_CSV:{p}")


if __name__ == "__main__":
    main()
