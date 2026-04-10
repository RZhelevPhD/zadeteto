"""
Script: analyze_outliers.py
Purpose: Analyze fetched social media posts, detect engagement outliers, rank top 10.
Input: --input JSON file from fetch_social_data.py
Output: JSON analysis with outlier posts grouped by content type, ranked by engagement.
Dependencies: pip install numpy
"""

import os
import re
import sys
import json
import argparse
from collections import Counter
from datetime import datetime

import numpy as np

# Stopwords for keyword extraction (BG + EN + SP + social noise)
_STOPWORDS = {
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "and", "but", "or",
    "nor", "not", "so", "yet", "for", "to", "of", "in", "on", "at", "by",
    "with", "from", "up", "out", "if", "then", "than", "too", "very",
    "just", "about", "it", "its", "this", "that", "these", "those",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "they",
    "them", "his", "her", "who", "what", "which", "when", "where", "how",
    "all", "each", "every", "no", "any", "some", "more", "most", "other",
    "into", "over", "after", "before", "between", "under", "again",
    "here", "there", "because", "while", "also", "even", "as",
    # Bulgarian
    "и", "в", "на", "за", "с", "от", "е", "се", "не", "да", "по",
    "ще", "са", "си", "до", "при", "но", "или", "ни", "ви", "им",
    "му", "го", "ги", "ме", "те", "ни", "ви", "тя", "то", "те",
    "той", "тя", "ние", "вие", "те", "този", "тази", "това", "тези",
    "как", "какво", "кой", "коя", "кое", "кои", "къде", "кога",
    "че", "ако", "като", "без", "между", "над", "под", "след", "преди",
    "много", "още", "вече", "само", "може", "има", "нямa", "така",
    "бъде", "беше", "била", "бил", "било", "били", "съм", "сте",
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
    "en", "con", "por", "para", "es", "son", "ser", "estar", "fue",
    "como", "que", "no", "si", "su", "sus", "al", "lo", "le", "les",
    "se", "me", "te", "nos", "mi", "tu", "yo", "ya", "mas", "pero",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "muy", "tan", "hay", "tiene", "tienen", "puede", "cada", "todo",
    "toda", "todos", "todas", "otro", "otra", "otros", "otras",
}


def _engagement_score(post: dict) -> float:
    """Calculate a weighted engagement score for a post."""
    likes = post.get("likes", 0)
    comments = post.get("comments", 0)
    shares = post.get("shares", 0)
    reactions = post.get("reactions", 0)
    views = post.get("views", 0)

    # Weighted: comments > shares > likes (comments signal deeper engagement)
    score = (likes * 1.0) + (comments * 3.0) + (shares * 2.0) + (reactions * 0.5)

    # Add view-based score for video content (normalized down since views >> likes)
    if views > 0:
        score += views * 0.01

    return score


def _calculate_author_baseline(posts: list[dict]) -> dict[str, dict]:
    """Calculate engagement baselines per author."""
    author_posts = {}
    for post in posts:
        author = post.get("author", "unknown")
        author_posts.setdefault(author, []).append(post)

    baselines = {}
    for author, author_post_list in author_posts.items():
        scores = [_engagement_score(p) for p in author_post_list]
        if len(scores) < 2:
            baselines[author] = {
                "mean": scores[0] if scores else 0,
                "std": 0,
                "count": len(scores),
            }
        else:
            baselines[author] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "count": len(scores),
            }

    return baselines


def _detect_outliers(posts: list[dict], baselines: dict) -> list[dict]:
    """
    Identify posts that significantly outperform their author's baseline.
    A post is an outlier if its engagement score is > 1.5 standard deviations
    above the author's mean.
    """
    # Pre-compute global baseline for authors with too few posts
    all_scores = [_engagement_score(p) for p in posts]
    global_mean = float(np.mean(all_scores)) if all_scores else 0
    global_std = float(np.std(all_scores)) if len(all_scores) > 1 else 0

    outliers = []
    for post in posts:
        author = post.get("author", "unknown")
        baseline = baselines.get(author, {"mean": 0, "std": 0, "count": 0})
        score = _engagement_score(post)

        threshold = baseline["mean"] + (1.5 * baseline["std"])

        # If std is 0 or fewer than 3 posts, fall back to global baseline (same 1.5x multiplier)
        if baseline["std"] == 0 or baseline["count"] < 3:
            threshold = global_mean + (1.5 * global_std)

        if score > threshold and score > 0:
            post_enriched = {
                **post,
                "engagement_score": round(score, 1),
                "author_mean": round(baseline["mean"], 1),
                "author_std": round(baseline["std"], 1),
                "outperformance_ratio": round(
                    score / baseline["mean"], 2
                ) if baseline["mean"] > 0 else 0,
                "is_outlier": True,
            }
            outliers.append(post_enriched)

    # Sort by engagement score descending
    outliers.sort(key=lambda p: p["engagement_score"], reverse=True)
    return outliers


def _group_by_content_type(posts: list[dict]) -> dict[str, list[dict]]:
    """Group posts by their content type."""
    groups = {}
    for post in posts:
        ct = post.get("content_type", "unknown")
        groups.setdefault(ct, []).append(post)
    return groups


def _top_n(posts: list[dict], n: int = 10) -> list[dict]:
    """Return top N posts by engagement score."""
    sorted_posts = sorted(posts, key=lambda p: p.get("engagement_score", 0), reverse=True)
    return sorted_posts[:n]


def _extract_hook(text: str, max_len: int = 150) -> str:
    """Extract the opening hook — the first sentence of a caption."""
    if not text:
        return ""
    # Split on first sentence-ending punctuation or newline
    match = re.split(r'[.!?\n]', text.strip(), maxsplit=1)
    hook = match[0].strip() if match else text.strip()
    # Remove leading hashtags/mentions that aren't the actual hook
    hook = re.sub(r'^[@#]\S+\s*', '', hook).strip()
    if len(hook) > max_len:
        hook = hook[:max_len].rsplit(' ', 1)[0] + "..."
    return hook


def _extract_keywords(outliers: list[dict], top_n: int = 20) -> list[dict]:
    """Extract most common keywords and bigrams from outlier captions."""
    word_scores = {}  # word -> list of engagement scores
    bigram_scores = {}

    for post in outliers:
        text = post.get("text", "") or ""
        score = post.get("engagement_score", 0)

        # Clean text: remove URLs, mentions, hashtags, emojis, punctuation
        clean = re.sub(r'https?://\S+', '', text)
        clean = re.sub(r'@\w+', '', clean)
        clean = re.sub(r'#\w+', '', clean)
        clean = re.sub(r'[^\w\s]', ' ', clean, flags=re.UNICODE)
        clean = re.sub(r'\s+', ' ', clean).strip().lower()

        words = [w for w in clean.split() if w not in _STOPWORDS and len(w) > 2]

        for word in words:
            word_scores.setdefault(word, []).append(score)

        # Bigrams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            bigram_scores.setdefault(bigram, []).append(score)

    # Combine words and bigrams, sort by frequency then avg engagement
    combined = {}
    for word, scores in word_scores.items():
        if len(scores) >= 2:  # Appear in at least 2 outlier posts
            combined[word] = {
                "keyword": word,
                "count": len(scores),
                "avg_engagement": round(float(np.mean(scores)), 1),
            }
    for bigram, scores in bigram_scores.items():
        if len(scores) >= 2:
            combined[bigram] = {
                "keyword": bigram,
                "count": len(scores),
                "avg_engagement": round(float(np.mean(scores)), 1),
            }

    # Sort: frequency first, then avg engagement as tiebreaker
    ranked = sorted(combined.values(), key=lambda x: (x["count"], x["avg_engagement"]), reverse=True)
    return ranked[:top_n]


def _extract_hashtags(outliers: list[dict], top_n: int = 15) -> list[dict]:
    """Extract most common hashtags from outlier captions with engagement scores."""
    hashtag_scores = {}

    for post in outliers:
        text = post.get("text", "") or ""
        score = post.get("engagement_score", 0)
        tags = re.findall(r'#(\w+)', text, flags=re.UNICODE)

        for tag in tags:
            tag_lower = tag.lower()
            hashtag_scores.setdefault(tag_lower, []).append(score)

    ranked = []
    for tag, scores in hashtag_scores.items():
        ranked.append({
            "hashtag": f"#{tag}",
            "count": len(scores),
            "avg_engagement": round(float(np.mean(scores)), 1),
        })

    ranked.sort(key=lambda x: (x["count"], x["avg_engagement"]), reverse=True)
    return ranked[:top_n]


def analyze(input_path: str) -> dict:
    """Run full outlier analysis on fetched posts."""
    with open(input_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        return {
            "platform": "unknown",
            "language": "unknown",
            "total_posts": 0,
            "outliers": [],
            "top_10": [],
            "top_hooks": [],
            "top_keywords": [],
            "top_hashtags": [],
            "by_content_type": {},
            "summary_stats": {
                "total_posts_fetched": 0,
                "total_outliers": 0,
                "unique_authors": 0,
                "mean_engagement": 0,
                "median_engagement": 0,
                "max_engagement": 0,
                "content_type_distribution": {},
                "outlier_content_type_distribution": {},
            },
        }

    platform = posts[0].get("platform", "unknown")
    language = posts[0].get("language", "unknown")

    # Calculate baselines and detect outliers
    baselines = _calculate_author_baseline(posts)
    outliers = _detect_outliers(posts, baselines)

    # Add hook to each outlier
    for post in outliers:
        post["hook"] = _extract_hook(post.get("text", ""))

    # Extract keywords and hashtags from outliers
    top_keywords = _extract_keywords(outliers)
    top_hashtags = _extract_hashtags(outliers)

    # Collect hooks sorted by engagement
    top_hooks = [
        {"hook": p["hook"], "author": p.get("author", ""), "engagement_score": p.get("engagement_score", 0)}
        for p in outliers if p.get("hook")
    ]

    # Top 10 overall
    top_10 = _top_n(outliers, 10)

    # Group outliers by content type
    grouped = _group_by_content_type(outliers)
    grouped_top = {ct: _top_n(group, 5) for ct, group in grouped.items()}

    # Summary statistics
    all_scores = [_engagement_score(p) for p in posts]
    summary = {
        "total_posts_fetched": len(posts),
        "total_outliers": len(outliers),
        "unique_authors": len(baselines),
        "mean_engagement": round(float(np.mean(all_scores)), 1) if all_scores else 0,
        "median_engagement": round(float(np.median(all_scores)), 1) if all_scores else 0,
        "max_engagement": round(float(np.max(all_scores)), 1) if all_scores else 0,
        "content_type_distribution": {
            ct: len(group) for ct, group in _group_by_content_type(posts).items()
        },
        "outlier_content_type_distribution": {
            ct: len(group) for ct, group in grouped.items()
        },
    }

    return {
        "platform": platform,
        "language": language,
        "analyzed_at": datetime.now().isoformat(),
        "total_posts": len(posts),
        "outliers": outliers,
        "top_10": top_10,
        "top_hooks": top_hooks,
        "top_keywords": top_keywords,
        "top_hashtags": top_hashtags,
        "by_content_type": grouped_top,
        "summary_stats": summary,
        "author_baselines": {
            author: {
                "mean_engagement": round(b["mean"], 1),
                "std_engagement": round(b["std"], 1),
                "post_count": b["count"],
            }
            for author, b in baselines.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze social media posts for engagement outliers")
    parser.add_argument("--input", required=True, help="Path to JSON from fetch_social_data.py")
    parser.add_argument("--output", help="Output analysis JSON path (default: auto in tmp/)")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top posts to include")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    analysis = analyze(args.input)

    # Override top N if specified
    if args.top_n != 10:
        analysis["top_10"] = _top_n(analysis["outliers"], args.top_n)

    os.makedirs("tmp", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    platform = analysis.get("platform", "unknown")
    language = analysis.get("language", "unknown")
    output_path = args.output or os.path.join(
        "tmp", f"analysis_{platform}_{language}_{ts}.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"  Analysis complete: {analysis['summary_stats']['total_outliers']} outliers from {analysis['total_posts']} posts")
    print(f"  Top 10 engagement scores: {[p['engagement_score'] for p in analysis['top_10']]}")
    print(f"  Saved -> {output_path}")
    print(f"OUTPUT_JSON:{output_path}")


if __name__ == "__main__":
    main()
