"""
Script: research_trends.py
Purpose: Research why top outlier posts might be relevant/trending right now.
Input: --input analysis JSON from analyze_outliers.py
Output: Enriched analysis JSON with trend context added to each top post.
Dependencies: pip install requests beautifulsoup4
"""

import os
import sys
import json
import re
import time
import random
import argparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup


UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _extract_keywords(post: dict) -> list[str]:
    """Extract searchable keywords from a post's text and metadata."""
    text = post.get("text", "") or ""
    author = post.get("author", "") or ""

    # Extract hashtags
    hashtags = re.findall(r"#(\w+)", text)

    # Extract meaningful phrases (first 2 sentences, cleaned)
    sentences = re.split(r"[.!?\n]", text)
    phrases = [s.strip() for s in sentences[:2] if len(s.strip()) > 10]

    # Combine: author name + key phrases + hashtags
    keywords = []
    if author:
        keywords.append(author)
    keywords.extend(phrases[:1])  # Just the first meaningful phrase
    keywords.extend(hashtags[:3])  # Top 3 hashtags

    return keywords


def _search_for_context(query: str, num_results: int = 3) -> list[dict]:
    """Search Google for context about why a topic might be trending."""
    try:
        from googlesearch import search as google_search
    except ImportError:
        return [{"note": "googlesearch-python not installed — skipping web research"}]

    results = []
    try:
        urls = list(google_search(query, num_results=num_results, sleep_interval=random.uniform(5, 10), lang="en"))
        for url in urls:
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": random.choice(UA_POOL)},
                    timeout=8,
                    allow_redirects=True,
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    # Get meta description
                    meta_desc = ""
                    meta_tag = soup.find("meta", attrs={"name": "description"})
                    if meta_tag:
                        meta_desc = meta_tag.get("content", "")
                    results.append({
                        "url": url,
                        "title": title[:200],
                        "description": meta_desc[:300],
                    })
            except Exception:
                continue
    except Exception as e:
        results.append({"note": f"Search failed: {str(e)[:100]}"})

    return results


def research(input_path: str, max_posts: int = 10) -> dict:
    """Add trend context to top outlier posts."""
    with open(input_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    top_posts = analysis.get("top_10", [])[:max_posts]

    if not top_posts:
        print("  No outlier posts to research.")
        analysis["trend_research"] = []
        return analysis

    print(f"  Researching trends for {len(top_posts)} top posts...")

    researched = []
    for i, post in enumerate(top_posts):
        print(f"  [{i+1}/{len(top_posts)}] Researching: {post.get('author', 'unknown')} — score {post.get('engagement_score', 0)}")

        keywords = _extract_keywords(post)
        if not keywords:
            post["trend_context"] = {"reason": "No searchable keywords found", "sources": []}
            researched.append(post)
            continue

        # Build search query from keywords
        query = " ".join(keywords[:3]) + f" trending {datetime.now().year}"
        sources = _search_for_context(query, num_results=3)

        post["trend_context"] = {
            "search_query": query,
            "keywords": keywords,
            "sources": sources,
            "researched_at": datetime.now().isoformat(),
        }
        researched.append(post)

        # Rate limiting between searches
        if i < len(top_posts) - 1:
            pause = random.uniform(8, 15)
            time.sleep(pause)

    analysis["top_10"] = researched
    analysis["trend_research_completed"] = True
    return analysis


def main():
    parser = argparse.ArgumentParser(description="Research why outlier posts might be trending")
    parser.add_argument("--input", required=True, help="Path to analysis JSON from analyze_outliers.py")
    parser.add_argument("--max-posts", type=int, default=10, help="Max posts to research (default: 10)")
    parser.add_argument("--output", help="Output path (default: overwrites input)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = research(args.input, args.max_posts)

    output_path = args.output or args.input
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  Trend research complete -> {output_path}")
    print(f"OUTPUT_JSON:{output_path}")


if __name__ == "__main__":
    main()
