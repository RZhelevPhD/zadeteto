"""
Script: generate_content_report.py
Purpose: Generate a PDF report with graphs and analytics from outlier analysis data.
Input: --input analysis JSON from analyze_outliers.py (with optional trend research)
Output: PDF file in reports/content/ with naming convention: WW.YYYY.PP.LL.meta.pdf
Dependencies: pip install matplotlib fpdf2
"""

import os
import sys
import json
import argparse
import textwrap
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from fpdf import FPDF


PLATFORM_CODES = {"facebook": "FB", "instagram": "IG", "linkedin": "LI"}
LANGUAGE_CODES = {"BG": "BG", "ENG": "ENG", "SP": "SP"}

CONTENT_TYPE_LABELS = {
    "static_image": "Static Image",
    "reel": "Reel",
    "video": "Video",
    "ig_carousel": "IG Carousel",
    "linkedin_pdf_carousel": "LI PDF Carousel",
    "text_only": "Text Only",
    "link_share": "Link Share",
    "story": "Story",
    "unknown": "Other",
}

COLORS = {
    "static_image": "#4CAF50",
    "reel": "#FF5722",
    "video": "#2196F3",
    "ig_carousel": "#9C27B0",
    "linkedin_pdf_carousel": "#FF9800",
    "text_only": "#607D8B",
    "link_share": "#795548",
    "story": "#E91E63",
    "unknown": "#9E9E9E",
}


def _generate_filename(platform: str, language: str) -> str:
    """Generate filename per convention: WW.YYYY.PP.LL.meta.pdf"""
    now = datetime.now()
    week = now.isocalendar()[1]
    year = now.year
    pp = PLATFORM_CODES.get(platform, platform.upper()[:2])
    ll = LANGUAGE_CODES.get(language, language.upper()[:3])
    return f"{week:02d}.{year}.{pp}.{ll}.meta.pdf"


def _plot_content_type_distribution(stats: dict, platform: str, language: str) -> str:
    """Create a bar chart of content type distribution and save as PNG."""
    dist = stats.get("content_type_distribution", {})
    if not dist:
        return None

    labels = [CONTENT_TYPE_LABELS.get(k, k) for k in dist.keys()]
    values = list(dist.values())
    colors = [COLORS.get(k, "#9E9E9E") for k in dist.keys()]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Number of Posts")
    ax.set_title(f"Content Type Distribution — {platform.title()} / {language}")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join("tmp", f"chart_dist_{platform}_{language}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_outlier_engagement(top_posts: list[dict], platform: str, language: str) -> str:
    """Create a horizontal bar chart of top 10 outlier engagement scores."""
    if not top_posts:
        return None

    labels = [
        textwrap.shorten(p.get("author", "?"), width=25, placeholder="...")
        for p in reversed(top_posts[:10])
    ]
    scores = [p.get("engagement_score", 0) for p in reversed(top_posts[:10])]
    means = [p.get("author_mean", 0) for p in reversed(top_posts[:10])]

    fig, ax = plt.subplots(figsize=(8, 5))
    y_pos = range(len(labels))
    ax.barh(y_pos, scores, color="#4CAF50", alpha=0.8, label="Outlier Score")
    ax.barh(y_pos, means, color="#BDBDBD", alpha=0.5, label="Author Average")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Engagement Score")
    ax.set_title(f"Top 10 Outliers vs Author Average — {platform.title()} / {language}")
    ax.legend(loc="lower right")
    plt.tight_layout()

    path = os.path.join("tmp", f"chart_outliers_{platform}_{language}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_content_type_comparison(stats: dict, platform: str, language: str) -> str:
    """Compare content types: all posts vs outliers."""
    all_dist = stats.get("content_type_distribution", {})
    outlier_dist = stats.get("outlier_content_type_distribution", {})
    if not all_dist:
        return None

    types = sorted(set(list(all_dist.keys()) + list(outlier_dist.keys())))
    labels = [CONTENT_TYPE_LABELS.get(t, t) for t in types]
    all_vals = [all_dist.get(t, 0) for t in types]
    outlier_vals = [outlier_dist.get(t, 0) for t in types]

    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - width/2 for i in x], all_vals, width, label="All Posts", color="#BDBDBD")
    ax.bar([i + width/2 for i in x], outlier_vals, width, label="Outliers", color="#FF5722")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Count")
    ax.set_title(f"All Posts vs Outliers by Type — {platform.title()} / {language}")
    ax.legend()
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join("tmp", f"chart_comparison_{platform}_{language}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_keyword_frequency(keywords: list[dict], platform: str, language: str) -> str:
    """Create a horizontal bar chart of top keywords by frequency."""
    if not keywords:
        return None

    top = keywords[:15]
    labels = [k["keyword"] for k in reversed(top)]
    counts = [k["count"] for k in reversed(top)]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(range(len(labels)), counts, color="#FF5722", alpha=0.8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Occurrences across outlier posts")
    ax.set_title(f"Top Keywords in Outlier Content -- {platform.title()} / {language}")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join("tmp", f"chart_keywords_{platform}_{language}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


class ContentReport(FPDF):
    def __init__(self):
        super().__init__()
        # Register Arial as a Unicode font (supports Cyrillic + special characters)
        self.add_font("Arial", "", "C:/Windows/Fonts/arial.ttf")
        self.add_font("Arial", "B", "C:/Windows/Fonts/arialbd.ttf")
        self.add_font("Arial", "I", "C:/Windows/Fonts/ariali.ttf")
        self.add_font("Arial", "BI", "C:/Windows/Fonts/arialbi.ttf")

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Content Intelligence Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def key_value(self, key: str, value: str):
        self.set_font("Arial", "B", 9)
        self.cell(55, 5, key + ":")
        self.set_font("Arial", "", 9)
        self.cell(0, 5, str(value), new_x="LMARGIN", new_y="NEXT")

    def post_entry(self, rank: int, post: dict):
        self.set_font("Arial", "B", 10)
        author = post.get("author", "Unknown")
        score = post.get("engagement_score", 0)
        content_type = CONTENT_TYPE_LABELS.get(post.get("content_type", ""), post.get("content_type", ""))
        self.cell(0, 6, f"#{rank}  {author}  |  Score: {score}  |  Type: {content_type}", new_x="LMARGIN", new_y="NEXT")

        # Post text (truncated)
        text = post.get("text", "") or ""
        if text:
            self.set_font("Arial", "", 8)
            truncated = textwrap.shorten(text, width=300, placeholder="...")
            self.multi_cell(0, 4, truncated)
            self.ln(1)

        # Metrics row
        self.set_font("Arial", "", 8)
        metrics = f"Likes: {post.get('likes', 0)}  |  Comments: {post.get('comments', 0)}  |  Shares: {post.get('shares', 0)}  |  Views: {post.get('views', 0)}"
        self.cell(0, 4, metrics, new_x="LMARGIN", new_y="NEXT")

        # Outperformance
        ratio = post.get("outperformance_ratio", 0)
        if ratio > 0:
            self.set_font("Arial", "I", 8)
            self.cell(0, 4, f"Outperformance: {ratio}x author average", new_x="LMARGIN", new_y="NEXT")

        # URL
        url = post.get("url", "")
        if url:
            self.set_font("Arial", "", 7)
            self.set_text_color(0, 0, 200)
            self.cell(0, 4, url[:120], new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)

        # Trend context
        trend = post.get("trend_context", {})
        if trend and trend.get("sources"):
            self.set_font("Arial", "I", 7)
            self.cell(0, 4, f"Trend research: {trend.get('search_query', '')}", new_x="LMARGIN", new_y="NEXT")
            for src in trend["sources"][:2]:
                if isinstance(src, dict) and src.get("title"):
                    self.cell(0, 3, f"  - {src['title'][:100]}", new_x="LMARGIN", new_y="NEXT")

        self.ln(3)


def generate(input_path: str, output_dir: str = "reports/content") -> str:
    """Generate the PDF report from analysis data."""
    with open(input_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    platform = analysis.get("platform", "unknown")
    language = analysis.get("language", "unknown")
    stats = analysis.get("summary_stats", {})
    top_10 = analysis.get("top_10", [])
    by_type = analysis.get("by_content_type", {})
    top_hooks = analysis.get("top_hooks", [])
    top_keywords = analysis.get("top_keywords", [])
    top_hashtags = analysis.get("top_hashtags", [])

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("tmp", exist_ok=True)

    filename = _generate_filename(platform, language)
    output_path = os.path.join(output_dir, filename)

    # Generate charts
    chart_dist = _plot_content_type_distribution(stats, platform, language)
    chart_outliers = _plot_outlier_engagement(top_10, platform, language)
    chart_comparison = _plot_content_type_comparison(stats, platform, language)
    chart_keywords = _plot_keyword_frequency(top_keywords, platform, language)

    # Build PDF
    pdf = ContentReport()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Report header info
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Platform: {platform.title()}  |  Language: {language}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Summary stats
    pdf.section_title("Summary Statistics")
    pdf.key_value("Total Posts Fetched", str(stats.get("total_posts_fetched", 0)))
    pdf.key_value("Total Outliers Detected", str(stats.get("total_outliers", 0)))
    pdf.key_value("Unique Authors Tracked", str(stats.get("unique_authors", 0)))
    pdf.key_value("Mean Engagement Score", str(stats.get("mean_engagement", 0)))
    pdf.key_value("Median Engagement Score", str(stats.get("median_engagement", 0)))
    pdf.key_value("Max Engagement Score", str(stats.get("max_engagement", 0)))
    pdf.ln(5)

    # Content type distribution chart
    if chart_dist:
        pdf.section_title("Content Type Distribution")
        pdf.image(chart_dist, w=170)
        pdf.ln(5)

    # Outliers vs average chart
    if chart_outliers:
        pdf.add_page()
        pdf.section_title("Top 10 Outliers vs Author Average")
        pdf.image(chart_outliers, w=170)
        pdf.ln(5)

    # All vs outliers comparison
    if chart_comparison:
        pdf.section_title("Content Types: All Posts vs Outliers")
        pdf.image(chart_comparison, w=170)
        pdf.ln(5)

    # Top 10 posts detail
    pdf.add_page()
    pdf.section_title(f"Top 10 Outlier Posts — {platform.title()} / {language}")
    for i, post in enumerate(top_10, 1):
        pdf.post_entry(i, post)
        if pdf.get_y() > 260:
            pdf.add_page()

    # Posts by content type
    if by_type:
        pdf.add_page()
        pdf.section_title("Top Outliers by Content Type")
        for ct, posts in by_type.items():
            label = CONTENT_TYPE_LABELS.get(ct, ct)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"--- {label} ({len(posts)} outliers) ---", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            for j, post in enumerate(posts[:3], 1):
                pdf.post_entry(j, post)
                if pdf.get_y() > 260:
                    pdf.add_page()
            pdf.ln(3)

    # Top Hooks section
    if top_hooks:
        pdf.add_page()
        pdf.section_title(f"Top Hooks (Opening Lines) -- {platform.title()} / {language}")
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 4, "The first sentence of each outlier post, ranked by engagement score.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        for i, h in enumerate(top_hooks[:15], 1):
            pdf.set_font("Arial", "B", 9)
            pdf.cell(8, 5, f"{i}.")
            pdf.set_font("Arial", "", 9)
            hook_text = h.get("hook", "")
            # Sanitize for PDF rendering
            hook_text = hook_text.encode("ascii", "replace").decode("ascii") if not hook_text.isascii() else hook_text
            # Keep Cyrillic — only strip actual problematic chars
            pdf.multi_cell(0, 5, h.get("hook", ""))
            pdf.set_font("Arial", "I", 7)
            pdf.cell(0, 4, f"   @{h.get('author', '?')}  |  Score: {h.get('engagement_score', 0)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            if pdf.get_y() > 265:
                pdf.add_page()

    # Keywords section
    if top_keywords:
        pdf.add_page()
        pdf.section_title(f"Top Keywords -- {platform.title()} / {language}")
        if chart_keywords:
            pdf.image(chart_keywords, w=170)
            pdf.ln(5)

        # Keywords table
        pdf.set_font("Arial", "B", 9)
        pdf.cell(90, 6, "Keyword", border=1)
        pdf.cell(30, 6, "Count", border=1, align="C")
        pdf.cell(40, 6, "Avg Engagement", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Arial", "", 8)
        for kw in top_keywords[:20]:
            pdf.cell(90, 5, kw["keyword"], border=1)
            pdf.cell(30, 5, str(kw["count"]), border=1, align="C")
            pdf.cell(40, 5, str(kw["avg_engagement"]), border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    # Hashtags section
    if top_hashtags:
        if pdf.get_y() > 200:
            pdf.add_page()
        pdf.ln(5)
        pdf.section_title(f"Top Hashtags -- {platform.title()} / {language}")
        pdf.set_font("Arial", "B", 9)
        pdf.cell(90, 6, "Hashtag", border=1)
        pdf.cell(30, 6, "Count", border=1, align="C")
        pdf.cell(40, 6, "Avg Engagement", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Arial", "", 8)
        for ht in top_hashtags[:15]:
            pdf.cell(90, 5, ht["hashtag"], border=1)
            pdf.cell(30, 5, str(ht["count"]), border=1, align="C")
            pdf.cell(40, 5, str(ht["avg_engagement"]), border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    print(f"  Report saved -> {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate PDF content intelligence report")
    parser.add_argument("--input", required=True, help="Path to analysis JSON")
    parser.add_argument("--output-dir", default="reports/content", help="Output directory for PDF")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    output_path = generate(args.input, args.output_dir)
    print(f"OUTPUT_PDF:{output_path}")


if __name__ == "__main__":
    main()
