"""Crawl each prospect's website, re-extract text, and re-run niche classification.

See directives/enrich-and-reclassify-prospects.md for full spec.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Reuse taxonomy + classification logic from the base pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_segment_prospects import (  # noqa: E402
    NICHE_META,
    classify,
    norm_emails,
    norm_phones,
)


UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

SECONDARY_SUFFIXES = [
    "/za-nas", "/about", "/about-us",
    "/kontakti", "/kontakt", "/contact",
]

BLOCKLIST_EXACT = {
    "youtu.be", "youtube.com", "facebook.com", "fb.me", "instagram.com",
    "sites.google.com", "taplink.ws", "linktr.ee",
    "wordpress.com", "preview.bg",
    "easybook.bg", "superdoc.bg", "uchiteli.bg",
    "zdraveopazvaneto.bg", "zdravenregister.com", "clickandplay.bg",
}
BLOCKLIST_SUFFIX = (
    ".taplink.ws", ".my.canva.site", ".blogspot.com", ".blogspot.bg",
    ".wordpress.com", ".alle.bg",
)

TEXT_TRUNCATE = 8000  # per page

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
EMAIL_JUNK = re.compile(
    r"@(example\.com|w3\.org|sentry\.io|schema\.org|cloudflare\.com|"
    r"google\.com|jquery\.com|wordpress\.org|fb\.com|sentry-next\.io)"
)
PHONE_RE = re.compile(
    r"(\+359[\s\-\.]?[\d\s\-\.]{7,13}|0[89]\d[\s\-\.]?\d{3}[\s\-\.]?\d{3,4}|"
    r"0[2-7]\d[\s\-\.]?\d{3}[\s\-\.]?\d{2,3})"
)

WS_RE = re.compile(r"\s+")

CACHE_LOCK = threading.Lock()
PROGRESS_LOCK = threading.Lock()


def is_blocklisted(domain: str) -> bool:
    if not domain:
        return True
    d = domain.lower()
    if d in BLOCKLIST_EXACT:
        return True
    for suf in BLOCKLIST_SUFFIX:
        if d.endswith(suf):
            return True
    return False


def fetch(url: str, timeout: int) -> tuple[int | str, str]:
    """Fetch a URL. Return (status_or_error, body). status=int on success, str on error."""
    headers = {
        "User-Agent": random.choice(UA_POOL),
        "Accept-Language": "bg,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            ctype = resp.headers.get("Content-Type", "").lower()
            if "html" not in ctype and "xml" not in ctype and ctype:
                return resp.status_code, ""
            # requests defaults to ISO-8859-1 for text/html when charset is
            # unset, which mangles Cyrillic. Trust apparent_encoding instead.
            if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.status_code, resp.text or ""
        return resp.status_code, ""
    except requests.exceptions.Timeout:
        return "error:timeout", ""
    except requests.exceptions.SSLError:
        return "error:ssl", ""
    except requests.exceptions.ConnectionError:
        return "error:connection", ""
    except requests.exceptions.RequestException as exc:
        return f"error:{type(exc).__name__}", ""


def normalize_domain(d: str | None) -> str:
    """Strip scheme/path/www/whitespace from a domain. Defensive — input CSV should already be clean."""
    if not d:
        return ""
    d = d.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    # Drop any path/query/fragment.
    d = d.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return d.rstrip(".")


def extract_page(html: str) -> tuple[str, str, str]:
    """Return (title, meta_description, body_text). Empty strings on failure."""
    if not html:
        return "", "", ""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return "", "", ""

    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""

    meta_desc = ""
    for sel in ({"name": "description"}, {"property": "og:description"}):
        tag = soup.find("meta", attrs=sel)
        if tag and tag.get("content"):
            meta_desc = tag["content"].strip()
            if meta_desc:
                break

    for tag_name in ("script", "style", "noscript", "nav", "footer", "header"):
        for t in soup.find_all(tag_name):
            t.decompose()

    body_text = soup.get_text(separator=" ", strip=True)
    body_text = WS_RE.sub(" ", body_text)
    if len(body_text) > TEXT_TRUNCATE:
        body_text = body_text[:TEXT_TRUNCATE]

    return title, meta_desc, body_text


def crawl_prospect(domain: str, timeout: int) -> dict:
    """Crawl homepage + up to 2 secondary pages, return structured extract."""
    domain = normalize_domain(domain)
    result = {
        "domain": domain,
        "http_status": None,
        "pages": [],        # list of {"url", "title", "meta", "text_len"}
        "crawled_text": "",
        "extra_emails": [],
        "extra_phones": [],
    }

    if not domain:
        result["http_status"] = "error:empty_domain"
        return result

    if is_blocklisted(domain):
        result["http_status"] = "skipped_blocklist"
        return result

    base = f"https://{domain}"
    status, html = fetch(base, timeout)
    if not html:
        # Fall back to HTTP whenever HTTPS yielded no usable body.
        status_http, html_http = fetch(f"http://{domain}", timeout)
        if html_http:
            status, html = status_http, html_http
            base = f"http://{domain}"

    result["http_status"] = status
    if not html:
        return result

    title, meta, body = extract_page(html)
    result["pages"].append({
        "url": base, "title": title, "meta": meta, "text_len": len(body),
    })
    texts = [title, meta, body]
    # Run regexes on already-cleaned get_text bodies (plus title+meta), not raw HTML,
    # to avoid false positives from scripts and analytics payloads.
    search_text_parts = [title, meta, body]

    # Try secondary pages: first-success wins for each suffix, up to 2 more.
    secondary_ok = 0
    for suffix in SECONDARY_SUFFIXES:
        if secondary_ok >= 2:
            break
        sec_url = base + suffix
        _s_status, s_html = fetch(sec_url, timeout)
        if s_html:
            s_title, s_meta, s_body = extract_page(s_html)
            result["pages"].append({
                "url": sec_url, "title": s_title, "meta": s_meta, "text_len": len(s_body),
            })
            texts.extend([s_title, s_meta, s_body])
            search_text_parts.extend([s_title, s_meta, s_body])
            secondary_ok += 1

    crawled_text = " | ".join(t for t in texts if t)
    result["crawled_text"] = crawled_text

    # Extract emails + phones from the cleaned text, not raw HTML.
    search_text = " \n ".join(p for p in search_text_parts if p)
    raw_emails = EMAIL_RE.findall(search_text)
    emails: list[str] = []
    seen_e: set[str] = set()
    for e in raw_emails:
        e_low = e.lower()
        if EMAIL_JUNK.search(e_low):
            continue
        if e_low.endswith((".png", ".jpg", ".gif", ".svg", ".webp")):
            continue
        if e_low in seen_e:
            continue
        seen_e.add(e_low)
        emails.append(e_low)
    result["extra_emails"] = emails

    phone_raw = PHONE_RE.findall(search_text)
    result["extra_phones"] = list({(p if isinstance(p, str) else p[0]).strip() for p in phone_raw})
    return result


def load_cache(cache_path: Path) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    if not cache_path.exists():
        return cache
    with cache_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            d = rec.get("domain")
            if d:
                cache[d] = rec
    return cache


def append_cache(cache_path: Path, record: dict) -> None:
    with CACHE_LOCK:
        with cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(";") if p.strip()]


def run(args: argparse.Namespace) -> dict:
    input_path = Path(args.input)
    output_path = Path(args.output)
    cache_path = Path(args.cache)
    report_path = Path(args.report)

    if args.refresh and cache_path.exists():
        cache_path.unlink()

    cache = load_cache(cache_path)

    with input_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        input_fields = reader.fieldnames or []

    total = len(rows)
    print(f"[info] loaded {total} prospects from {input_path}", file=sys.stderr)
    print(f"[info] cache has {len(cache)} prior records", file=sys.stderr)

    # Snapshot old primary niche for diff.
    for r in rows:
        r["niche_primary_before"] = r.get("niche_primary") or "other"

    # Determine what needs crawling.
    to_crawl = [r for r in rows if r.get("domain") and r["domain"] not in cache]
    print(f"[info] will crawl {len(to_crawl)} prospects; {total - len(to_crawl)} from cache/no-domain",
          file=sys.stderr)

    done = [0]

    def _worker(row: dict) -> tuple[str, dict]:
        domain = row["domain"]
        rec = crawl_prospect(domain, args.timeout)
        append_cache(cache_path, rec)
        with PROGRESS_LOCK:
            done[0] += 1
            if done[0] % 25 == 0 or done[0] == len(to_crawl):
                print(f"[progress] crawled {done[0]}/{len(to_crawl)}", file=sys.stderr)
        return domain, rec

    if to_crawl:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(_worker, r) for r in to_crawl]
            for fut in as_completed(futures):
                try:
                    domain, rec = fut.result()
                    cache[domain] = rec
                except Exception as exc:  # noqa: BLE001
                    print(f"[warn] worker crashed: {exc}", file=sys.stderr)
        # Reload cache from disk — a worker could have appended before crashing.
        cache = load_cache(cache_path)

    # Reclassify + enrich each row.
    crawled_success = 0
    crawl_failed = 0
    skipped_blocklist = 0
    reclassified = 0
    still_other_samples: list[dict] = []
    niche_counts_before: dict[str, int] = {}
    niche_counts_after: dict[str, int] = {}

    for row in rows:
        domain = normalize_domain(row.get("domain", ""))
        rec = cache.get(domain, {})
        status = rec.get("http_status")
        crawled_text = rec.get("crawled_text", "") or ""

        # Merge extra emails/phones.
        orig_emails = parse_list(row.get("emails"))
        orig_phones = parse_list(row.get("phones"))
        new_emails = norm_emails(rec.get("extra_emails", []))
        new_phones = norm_phones(rec.get("extra_phones", []))
        merged_emails = orig_emails + [e for e in new_emails if e not in orig_emails]
        merged_phones = orig_phones + [p for p in new_phones if p not in orig_phones]
        row["emails"] = "; ".join(merged_emails)
        row["phones"] = "; ".join(merged_phones)

        # Reclassify.
        blob = " ".join([
            row.get("name_best", ""),
            row.get("website_title", ""),
            row.get("website_description", ""),
            domain,
            crawled_text,
        ])
        niches = classify(blob)

        crawled_ok = status == 200 and len(crawled_text) > 200
        never_attempted = status in ("skipped_blocklist", "error:empty_domain", None)
        if crawled_ok:
            crawled_success += 1
        elif status == "skipped_blocklist":
            skipped_blocklist += 1
        else:
            crawl_failed += 1

        prior_niche = row["niche_primary_before"]
        prior_is_real = prior_niche in NICHE_META

        if not niches:
            # If we never actually crawled (blocklist / empty domain) AND the input
            # CSV had a real niche from the Outscraper-text pass, preserve it.
            if never_attempted and prior_is_real:
                niches = parse_list(row.get("niches_all")) or [prior_niche]
            elif crawled_ok:
                niches = ["other_crawled"]
            else:
                niches = ["other_uncrawled"]

        # Determine spheres for primary/all.
        spheres: list[str] = []
        for n in niches:
            if n in ("other_crawled", "other_uncrawled"):
                s = "Друго / за ръчен преглед"
            else:
                s = NICHE_META.get(n, {}).get("sphere", "Друго / за ръчен преглед")
            if s not in spheres:
                spheres.append(s)

        row["niches_all"] = "; ".join(niches)
        row["spheres_all"] = "; ".join(spheres)
        row["niche_primary"] = niches[0]
        row["sphere_primary"] = spheres[0]
        row["http_status"] = str(status) if status is not None else ""
        row["crawled_pages"] = str(len(rec.get("pages") or []))
        row["crawled_text_len"] = str(len(crawled_text))
        row["niches_changed"] = (
            "TRUE" if row["niche_primary"] != row["niche_primary_before"] else "FALSE"
        )
        if row["niches_changed"] == "TRUE":
            reclassified += 1

        niche_counts_before[row["niche_primary_before"]] = (
            niche_counts_before.get(row["niche_primary_before"], 0) + 1
        )
        niche_counts_after[row["niche_primary"]] = (
            niche_counts_after.get(row["niche_primary"], 0) + 1
        )

        if row["niche_primary"] == "other_crawled" and len(still_other_samples) < 30:
            still_other_samples.append({
                "domain": domain,
                "website_title": row.get("website_title", "")[:120],
                "crawled_text_preview": crawled_text[:200],
            })

    # Output CSV.
    output_fields = list(input_fields)
    for extra in ("http_status", "crawled_pages", "crawled_text_len",
                  "niche_primary_before", "niches_changed"):
        if extra not in output_fields:
            output_fields.append(extra)

    def sort_key(r: dict) -> tuple[str, str, str]:
        return (r.get("sphere_primary", "zzz"), r.get("niche_primary", "zzz"),
                (r.get("name_best") or "").lower())

    rows.sort(key=sort_key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    still_other = niche_counts_after.get("other_crawled", 0) + niche_counts_after.get("other_uncrawled", 0)
    report = {
        "input": str(input_path),
        "output_csv": str(output_path),
        "total_prospects": total,
        "crawled_successfully": crawled_success,
        "crawl_failed": crawl_failed,
        "skipped_blocklist": skipped_blocklist,
        "reclassified_count": reclassified,
        "still_other_count": still_other,
        "niche_primary_before_counts": dict(sorted(niche_counts_before.items(), key=lambda x: -x[1])),
        "niche_primary_counts": dict(sorted(niche_counts_after.items(), key=lambda x: -x[1])),
        "still_other_samples": still_other_samples,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Enrich + reclassify prospects by crawling their sites.")
    p.add_argument("--input", default="tmp/prospects_clean.csv")
    p.add_argument("--output", default="tmp/prospects_enriched.csv")
    p.add_argument("--cache", default="tmp/prospects_enriched_raw.jsonl")
    p.add_argument("--report", default="tmp/prospects_enriched_report.json")
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--timeout", type=int, default=10)
    p.add_argument("--refresh", action="store_true", help="Ignore cache, re-crawl everything.")
    args = p.parse_args()

    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
