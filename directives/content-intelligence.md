# Content Intelligence Directive — Weekly Outlier Analysis

## Objective
Scrape authority social media accounts across Facebook, Instagram, and LinkedIn in Bulgarian, English, and Spanish. Detect engagement outliers, research why they're trending, and produce weekly PDF reports with graphs and analytics.

## Profiles
The pipeline supports multiple **profiles** — named configurations in `authorities.json` that group authority accounts by content vertical (e.g., "childcare", "marketing"). Run different profiles as separate pipeline instances to track different content niches.

## Execution Scripts

| Script | Purpose |
|--------|---------|
| `executions/fetch_social_data.py` | Fetch posts from Apify actors for a given platform/language/profile |
| `executions/analyze_outliers.py` | Detect engagement outliers using statistical baselines per author |
| `executions/research_trends.py` | Research why top outlier posts might be trending right now |
| `executions/generate_content_report.py` | Generate PDF report with graphs, analytics, and top 10 lists |
| `executions/run_content_intelligence.py` | Orchestrate the full pipeline across all platform/language combos |

## Pipeline Steps

### 1. Fetch Posts (fetch_social_data.py)
Operates in three modes via `--mode`:
- **authority** — scrape specific tracked accounts (benchmarks)
- **discovery** — search by topic/hashtag to find posts from *anyone* (finds small creators with viral posts)
- **both** (default) — merge authority + discovery, deduplicate by post ID

Authority mode reads account URLs from `authorities.json`. Discovery mode uses `search_terms_by_language` from the profile (or built-in defaults). Posts are tagged with `source: "authority"` or `source: "discovery"` so analysis can distinguish benchmark vs. discovered content.

- Normalizes post data into a common schema across platforms
- Classifies content types: static image, reel, video, IG carousel, LinkedIn PDF carousel, text only, link share, story
- Deduplicates by post ID when both modes return the same post
- Outputs JSON to `tmp/`

### 2. Analyze Outliers (analyze_outliers.py)
- Calculates engagement baselines per author (mean + standard deviation)
- An outlier = a post scoring >1.5 standard deviations above its author's mean
- Fallback: if an author has a standard deviation of 0 or fewer than 3 posts, the script uses the global baseline (all posts' mean + 1.5 std) instead of the per-author baseline
- Weighted engagement score: likes(1x) + comments(3x) + shares(2x) + reactions(0.5x) + views(0.01x)
- Groups outliers by content type
- Ranks top 10 overall
- Outputs analysis JSON to `tmp/`

### 3. Research Trends (research_trends.py)
- Extracts keywords and hashtags from top outlier posts
- Searches Google for why those topics might be trending
- Attaches trend context (search sources with titles and meta descriptions) to each outlier
- Rate limited: 8-15 seconds between searches
- Optional step — use `--skip-research` to skip

### 4. Generate PDF Report (generate_content_report.py)
- Creates 3 charts: content type distribution, outlier vs. average, all posts vs. outliers
- Lists top 10 outliers with full metrics, post text, URLs, and trend context
- Groups outliers by content type with top 3 per type
- Saves to `reports/content/` with naming convention: `WW.YYYY.PP.LL.meta.pdf`

## Usage

### Full pipeline (all 9 reports for a profile)
```bash
python executions/run_content_intelligence.py --profile childcare
```

### Specific platforms/languages only
```bash
python executions/run_content_intelligence.py \
  --profile childcare \
  --platforms facebook instagram \
  --languages BG ENG
```

### Discovery only (find viral posts from anyone, skip tracked accounts)
```bash
python executions/run_content_intelligence.py --profile childcare --mode discovery
```

### Authority only (benchmark tracked accounts, no topic search)
```bash
python executions/run_content_intelligence.py --profile childcare --mode authority
```

### Quick run (skip trend research)
```bash
python executions/run_content_intelligence.py --profile childcare --skip-research
```

### Custom top-N count
```bash
python executions/run_content_intelligence.py --profile childcare --top-n 20
```

### Individual script usage
```bash
# Fetch posts for one combo
python executions/fetch_social_data.py --platform instagram --language BG --profile childcare

# Analyze fetched data
python executions/analyze_outliers.py --input tmp/posts_instagram_BG_*.json

# Research trends
python executions/research_trends.py --input tmp/analysis_instagram_BG_*.json

# Generate PDF
python executions/generate_content_report.py --input tmp/analysis_instagram_BG_*.json
```

## Configuration

### authorities.json (project root)
Contains named profiles with authorities per platform/language:
```json
{
  "profiles": {
    "childcare": {
      "description": "Childcare and parenting content",
      "search_terms": ["детска градина", "parenting"],
      "authorities": [
        {"name": "...", "platform": "facebook", "language": "BG", "url": "https://..."}
      ]
    }
  }
}
```

### .env
```
APIFY_API_TOKEN=apify_api_...
```

## Output

### File Naming Convention
`WW.YYYY.PP.LL.meta.pdf`
- `WW` — week number of the year (01-52)
- `YYYY` — year
- `PP` — platform code: FB, IG, LI
- `LL` — language code: BG, ENG, SP
- `meta` — indicates Meta (FB/IG) ecosystem (for future TikTok/YouTube disambiguation)

Example: `15.2026.IG.BG.meta.pdf` = Week 15, 2026, Instagram, Bulgarian

### Content Type Groups
| Type | Description |
|------|-------------|
| `static_image` | Single image post |
| `reel` | Short-form video (Reels/Clips) |
| `video` | Long-form video |
| `ig_carousel` | Instagram multi-image carousel |
| `linkedin_pdf_carousel` | LinkedIn document/PDF carousel |
| `text_only` | Text-only post |
| `link_share` | Link/article share |
| `story` | Story post |

## Prerequisites
```bash
pip install apify-client python-dotenv numpy matplotlib fpdf2 \
            requests beautifulsoup4 googlesearch-python
```

## Rate Limits
- Apify: depends on plan (free tier: 10 actor runs/day)
- Google search (trend research): 8-15s random pause between queries (no 429/backoff handling implemented)
- Full pipeline for 1 profile (all 9 combos): ~30-60 min with research, ~10-15 min without

---

## Changelog

### 2026-04-09 — doc-sync: align directive with reviewed scripts
- **analyze_outliers.py**: Added documentation for the global-baseline fallback when an author has std=0 or fewer than 3 posts.
- **research_trends.py**: Corrected "search sources + titles" to "search sources with titles and meta descriptions" (script also scrapes meta descriptions).
- **research_trends.py**: Removed false claim of "exponential backoff on 429" from Rate Limits — script only uses fixed 8-15s random pauses between searches.
- **run_content_intelligence.py**: Added missing `--top-n` usage example to the Usage section.
