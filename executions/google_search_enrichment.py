import re
import time
import json
import random
import argparse

try:
    from googlesearch import search as google_search
except ImportError:
    google_search = None

INTER_ROW_PAUSE = (20, 40)

GENERIC_BG_NAMES = {
    "слънчице", "детелина", "звездичка", "усмивка", "зорница", "рай",
    "радост", "пролет", "дъга", "буратино", "пинокио", "мечо пух",
    "мики маус", "снежанка", "пепеляшка", "щастие", "надежда",
}

BG_TRANSLITERATE = {
    "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "e": "е",
    "zh": "ж", "z": "з", "i": "и", "y": "й", "k": "к", "l": "л",
    "m": "м", "n": "н", "o": "о", "p": "п", "r": "р", "s": "с",
    "t": "т", "u": "у", "f": "ф", "h": "х", "ts": "ц", "ch": "ч",
    "sh": "ш", "sht": "щ", "yu": "ю", "ya": "я",
}


def _is_generic_name(name: str) -> bool:
    return name.strip().lower() in GENERIC_BG_NAMES


def _transliterate_slug(slug: str) -> str:
    parts = slug.split("-")
    result = []
    for part in parts:
        word = part
        for latin, cyrillic in sorted(BG_TRANSLITERATE.items(), key=lambda x: -len(x[0])):
            word = word.replace(latin, cyrillic)
        result.append(word.capitalize())
    return " ".join(result)


def _extract_name_from_linkedin_url(url: str) -> str:
    match = re.search(r"linkedin\.com/in/([^/?#]+)", url)
    if not match:
        return ""
    slug = match.group(1)
    slug = re.sub(r"-\w{2,4}$", "", slug)
    parts = slug.split("-")
    if len(parts) >= 2:
        return _transliterate_slug("-".join(parts[:2]))
    return _transliterate_slug(slug)


def _extract_name_from_facebook_url(url: str) -> str:
    match = re.search(r"facebook\.com/(?:people/)?([^/?#]+)", url)
    if not match:
        return ""
    slug = match.group(1)
    if re.match(r"^\d+$", slug):
        return ""
    return slug.replace(".", " ").replace("-", " ").title()


def _search_with_backoff(query: str, num_results: int = 1, pause: float = None) -> list[str]:
    if google_search is None:
        return []
    if pause is None:
        pause = random.uniform(8.0, 15.0)
    for attempt in range(3):
        try:
            results = list(google_search(query, num_results=num_results, pause=pause, lang="bg"))
            return results
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate" in err or "too many" in err:
                wait = (2 ** attempt) * 30
                time.sleep(wait)
            else:
                return []
    return []


def enrich_by_search(
    business_name: str,
    city: str = "",
    missing_fields: list = None,
) -> dict:
    result = {
        "facebook": None,
        "instagram": None,
        "linkedin": None,
        "youtube": None,
        "tiktok": None,
        "gmb": None,
        "decision_maker_name": "",
        "decision_maker_linkedin": "",
        "notes": "",
    }

    notes = []
    name = business_name.strip()
    location_suffix = f" {city}" if city and _is_generic_name(name) else ""
    bg_suffix = " България" if _is_generic_name(name) and not city else ""
    search_name = f"{name}{location_suffix}{bg_suffix}"

    social_queries = {
        "facebook":  f"{search_name} site:facebook.com",
        "instagram": f"{search_name} site:instagram.com",
        "linkedin":  f"{search_name} site:linkedin.com/company",
        "youtube":   f"{search_name} детска градина site:youtube.com",
        "tiktok":    f"{search_name} site:tiktok.com",
    }

    fields_to_search = missing_fields if missing_fields is not None else list(social_queries.keys()) + ["decision_maker"]

    for field, query in social_queries.items():
        if field not in fields_to_search:
            continue
        urls = _search_with_backoff(query, num_results=1)
        if urls:
            result[field] = urls[0]

    if "decision_maker" in fields_to_search:
        dm_query = f'"{name}" директор OR управител OR собственик site:linkedin.com'
        dm_urls = _search_with_backoff(dm_query, num_results=2)

        dm_name = ""
        dm_linkedin = ""

        for url in dm_urls:
            if "linkedin.com/in/" in url:
                dm_name = _extract_name_from_linkedin_url(url)
                dm_linkedin = url
                break

        if not dm_name:
            fb_dm_query = f'"{name}" директор OR управител site:facebook.com'
            fb_urls = _search_with_backoff(fb_dm_query, num_results=2)
            for url in fb_urls:
                if "facebook.com/people/" in url or ("facebook.com/" in url and "/pg/" not in url):
                    extracted = _extract_name_from_facebook_url(url)
                    if extracted:
                        dm_name = extracted
                        break

        result["decision_maker_name"] = dm_name
        result["decision_maker_linkedin"] = dm_linkedin

        if dm_name:
            notes.append("DM personal contact requires manual research")
        else:
            notes.append("Decision maker not found via public search")

    result["notes"] = "; ".join(notes)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google-search enrichment for a single provider")
    parser.add_argument("name", help="Business name (Cyrillic or Latin)")
    parser.add_argument("--city", default="", help="City name (optional)")
    parser.add_argument("--fields", nargs="*", default=None,
                        help="Fields to search: facebook instagram linkedin youtube tiktok decision_maker")
    args = parser.parse_args()

    if google_search is None:
        print("ERROR: googlesearch-python not installed. Run: pip install googlesearch-python")
        exit(1)

    result = enrich_by_search(args.name, city=args.city, missing_fields=args.fields)
    print(json.dumps(result, ensure_ascii=False, indent=2))
