import re
import sys
import json
import random
import argparse
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

CONTACT_SUFFIXES = [
    "/kontakti", "/kontakt", "/contact", "/contacts",
    "/za-nas", "/za_nas", "/about", "/about-us",
]

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

EMAIL_JUNK = re.compile(
    r"@(example\.com|w3\.org|sentry\.io|schema\.org|cloudflare\.com|"
    r"google\.com|jquery\.com|wordpress\.org|fb\.com)"
)

PHONE_RE = re.compile(
    r"(\+359[\s\-\.]?[\d\s\-\.]{7,13}|0[89]\d[\s\-\.]?\d{3}[\s\-\.]?\d{3,4}|"
    r"0[2-7]\d[\s\-\.]?\d{3}[\s\-\.]?\d{2,3})"
)

SOCIAL_PATTERNS = {
    "facebook":  re.compile(r"https?://(www\.)?facebook\.com/(?!sharer|share|dialog|tr\?|plugins)[^\"\s>?#&]+"),
    "instagram": re.compile(r"https?://(www\.)?instagram\.com/[^\"\s>?#&]+"),
    "linkedin":  re.compile(r"https?://(www\.)?linkedin\.com/(company|in)/[^\"\s>?#&]+"),
    "youtube":   re.compile(r"https?://(www\.)?youtube\.com/(channel|c|@|user)[^\"\s>?#&]+"),
    "tiktok":    re.compile(r"https?://(www\.)?tiktok\.com/@[^\"\s>?#&]+"),
    "gmb":       re.compile(r"https?://g\.page/[^\"\s>?#&]+|https?://maps\.google\.com/[^\"\s>?#&]+"),
}


def _normalize_url(url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def _fetch(url: str, timeout: int = 10) -> str | None:
    headers = {
        "User-Agent": random.choice(UA_POOL),
        "Accept-Language": "bg,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def _extract_emails(html: str) -> list[str]:
    raw = EMAIL_RE.findall(html)
    seen = {}
    for e in raw:
        e_lower = e.lower()
        if EMAIL_JUNK.search(e_lower):
            continue
        if e_lower.endswith((".png", ".jpg", ".gif", ".svg", ".webp")):
            continue
        if e_lower not in seen:
            seen[e_lower] = e
    return list(seen.values())


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"[\s\-\.\(\)]", "", raw)
    if digits.startswith("0") and not digits.startswith("+"):
        digits = "+359" + digits[1:]
    return digits


def _extract_phones(html: str) -> list[str]:
    raw = PHONE_RE.findall(html)
    seen = {}
    for match in raw:
        normalized = _normalize_phone(match if isinstance(match, str) else match[0])
        if len(normalized) >= 10 and normalized not in seen:
            seen[normalized] = normalized
    return list(seen.values())


def _extract_socials(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    hrefs = [a.get("href", "") for a in soup.find_all("a", href=True)]
    search_text = html + "\n" + "\n".join(hrefs)

    result = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(search_text)
        if match:
            url = match.group(0).rstrip(".,;)")
            if platform == "facebook" and "/p/" not in url and len(url) > 30:
                result[platform] = url
            elif platform != "facebook":
                result[platform] = url
        else:
            result[platform] = None
    return result


def crawl(url: str, timeout: int = 10) -> dict:
    base = _normalize_url(url)
    domain = urlparse(base).netloc

    pages_html = []
    fetched_urls = set()

    homepage_html = _fetch(base, timeout)
    if homepage_html:
        pages_html.append(homepage_html)
        fetched_urls.add(base)

    for suffix in CONTACT_SUFFIXES:
        if len(fetched_urls) >= 3:
            break
        candidate = base + suffix
        if candidate in fetched_urls:
            continue
        html = _fetch(candidate, timeout)
        if html:
            pages_html.append(html)
            fetched_urls.add(candidate)

    combined_html = "\n".join(pages_html)

    emails = _extract_emails(combined_html)
    phones = _extract_phones(combined_html)

    socials = {"facebook": None, "instagram": None, "linkedin": None,
               "youtube": None, "tiktok": None, "gmb": None}
    for page_html in pages_html:
        found = _extract_socials(page_html, base)
        for platform, val in found.items():
            if val and not socials[platform]:
                socials[platform] = val

    return {
        "emails": emails,
        "phones": phones,
        **socials,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl a website and extract contact/social data")
    parser.add_argument("url", help="URL to crawl")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    result = crawl(args.url, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
