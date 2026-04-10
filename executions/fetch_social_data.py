"""
Script: fetch_social_data.py
Purpose: Fetch social media posts via Apify in two modes:
  - AUTHORITY mode: scrape specific accounts as benchmarks
  - DISCOVERY mode: search by topic/hashtag to find outlier posts from anyone
Input: --platform, --language, --profile, --mode (authority|discovery|both)
Output: JSON file in tmp/ with post data and engagement metrics.
Dependencies: pip install apify-client python-dotenv
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# Apify actor IDs for scraping specific accounts
AUTHORITY_ACTOR_IDS = {
    "facebook": "apify/facebook-posts-scraper",
    "instagram": "apify/instagram-scraper",
    "linkedin": "curious_coder/linkedin-post-search-scraper",
}

# Apify actor IDs for topic/keyword search (discovery mode)
DISCOVERY_ACTOR_IDS = {
    "facebook": "apify/facebook-posts-scraper",
    "instagram": "apify/instagram-hashtag-scraper",
    "linkedin": "curious_coder/linkedin-post-search-scraper",
}

CONTENT_TYPES = {
    "static_image": ["photo", "image"],
    "reel": ["reel", "clips"],
    "video": ["video", "native_video"],
    "ig_carousel": ["carousel", "sidecar", "album"],
    "linkedin_pdf_carousel": ["document", "pdf"],
    "text_only": ["status", "text"],
    "link_share": ["link", "share"],
    "story": ["story"],
}

# Search terms by language for discovery mode
DEFAULT_SEARCH_TERMS = {
    "BG": [
        "детска градина", "родителство", "деца", "майчинство",
        "детско развитие", "ранно детство",
    ],
    "ENG": [
        "parenting tips", "early childhood", "toddler activities",
        "gentle parenting", "childhood education",
    ],
    "SP": [
        "crianza respetuosa", "educación infantil", "maternidad",
        "desarrollo infantil", "actividades para niños",
    ],
}


def _classify_content_type(post: dict) -> str:
    """Classify a post into a content type bucket."""
    post_type = str(post.get("type", "") or "").lower()
    media_type = str(post.get("mediaType", post.get("media_type", "")) or "").lower()
    combined = f"{post_type} {media_type}"

    if any(k in combined for k in ["document", "pdf"]):
        return "linkedin_pdf_carousel"
    if any(k in combined for k in ["carousel", "sidecar", "album"]):
        return "ig_carousel"
    if any(k in combined for k in ["reel", "clips"]):
        return "reel"
    if any(k in combined for k in ["video", "native_video"]):
        return "video"
    if any(k in combined for k in ["photo", "image"]):
        return "static_image"
    if any(k in combined for k in ["link", "share"]):
        return "link_share"
    if any(k in combined for k in ["story"]):
        return "story"

    if post.get("images") or post.get("imageUrl") or post.get("displayUrl"):
        return "static_image"
    if post.get("videoUrl") or post.get("video_url"):
        return "video"

    return "text_only"


def _normalize_post(post: dict, platform: str) -> dict:
    """Normalize post data across platforms into a common schema."""

    if platform == "facebook":
        return {
            "id": post.get("postId", post.get("id", "")),
            "url": post.get("url", post.get("postUrl", "")),
            "author": post.get("pageName", post.get("user", {}).get("name", "")),
            "author_url": post.get("pageUrl", ""),
            "text": post.get("text", post.get("message", "")),
            "timestamp": post.get("time", post.get("timestamp", "")),
            "likes": _int(post.get("likes", post.get("likesCount", 0))),
            "comments": _int(post.get("comments", post.get("commentsCount", 0))),
            "shares": _int(post.get("shares", post.get("sharesCount", 0))),
            "reactions": _int(post.get("reactions", post.get("reactionsCount", 0))),
            "views": _int(post.get("views", post.get("videoViewCount", 0))),
            "image_url": post.get("imageUrl", post.get("full_picture", "")),
            "video_url": post.get("videoUrl", ""),
            "content_type": _classify_content_type(post),
            "raw_type": post.get("type", ""),
            "platform": "facebook",
        }

    elif platform == "instagram":
        return {
            "id": post.get("id", post.get("shortCode", "")),
            "url": post.get("url", f"https://www.instagram.com/p/{post.get('shortCode', '')}"),
            "author": post.get("ownerUsername", post.get("owner", {}).get("username", "")),
            "author_url": f"https://www.instagram.com/{post.get('ownerUsername', '')}",
            "text": post.get("caption", post.get("text", "")),
            "timestamp": post.get("timestamp", post.get("taken_at", "")),
            "likes": _int(post.get("likesCount", post.get("likes", 0))),
            "comments": _int(post.get("commentsCount", post.get("comments", 0))),
            "shares": 0,
            "reactions": 0,
            "views": _int(post.get("videoViewCount", post.get("video_view_count", 0))),
            "image_url": post.get("displayUrl", post.get("imageUrl", "")),
            "video_url": post.get("videoUrl", ""),
            "content_type": _classify_content_type(post),
            "raw_type": post.get("type", ""),
            "platform": "instagram",
        }

    elif platform == "linkedin":
        return {
            "id": str(post.get("urn", post.get("id", ""))),
            "url": post.get("postUrl", post.get("url", "")),
            "author": post.get("authorName", post.get("author", {}).get("name", "")),
            "author_url": post.get("authorUrl", post.get("author", {}).get("url", "")),
            "text": post.get("text", post.get("commentary", "")),
            "timestamp": post.get("postedAt", post.get("timestamp", "")),
            "likes": _int(post.get("likesCount", post.get("numLikes", 0))),
            "comments": _int(post.get("commentsCount", post.get("numComments", 0))),
            "shares": _int(post.get("repostsCount", post.get("numShares", 0))),
            "reactions": _int(post.get("reactionsCount", 0)),
            "views": _int(post.get("impressionsCount", post.get("views", 0))),
            "image_url": post.get("imageUrl", ""),
            "video_url": post.get("videoUrl", ""),
            "content_type": _classify_content_type(post),
            "raw_type": post.get("type", ""),
            "platform": "linkedin",
        }

    raise ValueError(f"Unsupported platform: {platform}")


def _int(val) -> int:
    """Safely convert to int."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _load_profile(path: str, profile: str = None) -> dict:
    """Load a profile from authorities.json."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "profiles" in data:
        if profile is None:
            profile = next(iter(data["profiles"]))
            print(f"  No profile specified, using: {profile}")
        profile_data = data["profiles"].get(profile)
        if not profile_data:
            print(f"ERROR: Profile '{profile}' not found. Available: {list(data['profiles'].keys())}", file=sys.stderr)
            sys.exit(1)
        return profile_data
    else:
        return {"authorities": data.get("authorities", []), "search_terms": []}


def _get_authorities(profile_data: dict, platform: str, language: str) -> list[dict]:
    """Filter authorities by platform and language."""
    return [
        a for a in profile_data.get("authorities", [])
        if a["platform"] == platform and a["language"] == language
    ]


def _get_search_terms(profile_data: dict, language: str) -> list[str]:
    """Get search terms for discovery, from profile or defaults."""
    # Profile may have language-specific search terms
    lang_terms = profile_data.get("search_terms_by_language", {}).get(language, [])
    if lang_terms:
        return lang_terms
    # Fall back to profile's generic search terms
    generic = profile_data.get("search_terms", [])
    if generic:
        return generic
    # Fall back to defaults
    return DEFAULT_SEARCH_TERMS.get(language, [])


def _build_authority_input(platform: str, urls: list[str], days_back: int) -> dict:
    """Build Apify input for scraping specific authority accounts."""
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    if platform == "facebook":
        return {
            "startUrls": [{"url": u} for u in urls],
            "maxPosts": 50,
            "onlyPostsNewerThan": since,
        }
    elif platform == "instagram":
        return {
            "directUrls": urls,
            "resultsLimit": 50,
            "searchType": "user",
            "addParentData": True,
            "onlyPostsNewerThan": since,
        }
    elif platform == "linkedin":
        return {
            "urls": urls,
            "deepScrape": True,
            "maxItems": 50,
            "publishedAt": "past-week",
        }
    return {}


def _build_discovery_input(platform: str, search_terms: list[str], days_back: int) -> dict:
    """Build Apify input for topic-based discovery searches."""
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    if platform == "facebook":
        # Facebook posts scraper can search by keyword
        return {
            "searchQueries": search_terms,
            "maxPosts": 100,
            "onlyPostsNewerThan": since,
        }
    elif platform == "instagram":
        # Instagram hashtag scraper searches by hashtag
        # Strip # if present, Apify expects clean hashtag names
        hashtags = [t.replace("#", "").replace(" ", "") for t in search_terms]
        return {
            "hashtags": hashtags,
            "resultsLimit": 100,
            "addParentData": True,
        }
    elif platform == "linkedin":
        # LinkedIn search by keywords
        return {
            "searchQueries": search_terms,
            "maxItems": 100,
            "publishedAt": "past-week",
        }
    return {}


def _run_actor(client, actor_id: str, actor_input: dict, label: str) -> list[dict]:
    """Run an Apify actor and return the results."""
    print(f"  Running {actor_id} for {label}...")
    try:
        run = client.actor(actor_id).call(run_input=actor_input)
        raw_posts = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"  Got {len(raw_posts)} raw posts from {label}")
        return raw_posts
    except Exception as e:
        print(f"  ERROR running {actor_id}: {e}", file=sys.stderr)
        return []


def fetch(platform: str, language: str, authorities_path: str,
          days_back: int = 7, profile: str = None, mode: str = "both") -> list[dict]:
    """
    Fetch posts from Apify.
    mode: "authority" = only tracked accounts, "discovery" = topic search, "both" = merge both.
    """
    from apify_client import ApifyClient

    api_key = os.environ.get("APIFY_API_TOKEN")
    if not api_key:
        print("ERROR: APIFY_API_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    profile_data = _load_profile(authorities_path, profile)
    client = ApifyClient(api_key)

    all_raw_posts = []

    # --- Authority mode: scrape specific accounts ---
    if mode in ("authority", "both"):
        authorities = _get_authorities(profile_data, platform, language)
        if authorities:
            urls = [a["url"] for a in authorities]
            actor_id = AUTHORITY_ACTOR_IDS.get(platform)
            actor_input = _build_authority_input(platform, urls, days_back)
            raw = _run_actor(client, actor_id, actor_input, f"authority {platform}/{language}")
            # Tag as authority source
            for p in raw:
                p["_source"] = "authority"
            all_raw_posts.extend(raw)
        else:
            print(f"  No authorities found for {platform}/{language} — skipping authority fetch")

    # --- Discovery mode: search by topic/hashtag ---
    if mode in ("discovery", "both"):
        search_terms = _get_search_terms(profile_data, language)
        if search_terms:
            actor_id = DISCOVERY_ACTOR_IDS.get(platform)
            actor_input = _build_discovery_input(platform, search_terms, days_back)
            raw = _run_actor(client, actor_id, actor_input, f"discovery {platform}/{language}")
            # Tag as discovery source
            for p in raw:
                p["_source"] = "discovery"
            all_raw_posts.extend(raw)
        else:
            print(f"  No search terms for {language} — skipping discovery fetch")

    print(f"  Total raw posts: {len(all_raw_posts)}")

    # Normalize and deduplicate
    normalized = []
    seen_ids = set()
    for post in all_raw_posts:
        try:
            n = _normalize_post(post, platform)
            n["source"] = post.get("_source", "unknown")
            post_id = n.get("id", "")
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                normalized.append(n)
            elif not post_id:
                normalized.append(n)
        except Exception as e:
            print(f"  SKIP post normalization: {e}")

    # Tag with language
    for p in normalized:
        p["language"] = language

    print(f"  Normalized & deduplicated: {len(normalized)} posts")
    return normalized


def main():
    parser = argparse.ArgumentParser(description="Fetch social media posts via Apify")
    parser.add_argument("--platform", required=True, choices=["facebook", "instagram", "linkedin"])
    parser.add_argument("--language", required=True, choices=["BG", "ENG", "SP"])
    parser.add_argument("--authorities", default="authorities.json", help="Path to authorities JSON")
    parser.add_argument("--days-back", type=int, default=7, help="How many days of posts to fetch")
    parser.add_argument("--profile", default=None, help="Authority profile name")
    parser.add_argument("--mode", default="both", choices=["authority", "discovery", "both"],
                        help="authority=tracked accounts only, discovery=topic search, both=merge (default)")
    parser.add_argument("--output", help="Output JSON path (default: auto-generated in tmp/)")
    args = parser.parse_args()

    posts = fetch(args.platform, args.language, args.authorities, args.days_back, args.profile, args.mode)

    os.makedirs("tmp", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or os.path.join(
        "tmp", f"posts_{args.platform}_{args.language}_{ts}.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(posts)} posts -> {output_path}")
    print(f"OUTPUT_JSON:{output_path}")


if __name__ == "__main__":
    main()
