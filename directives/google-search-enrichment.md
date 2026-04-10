# Google Search Enrichment Directive — Social Profile Discovery

## Objective
Enrich a single business record with social media profiles and decision maker names by querying Google Search with site-specific queries (e.g., `"Business Name" site:facebook.com`).

## Execution Script
`executions/google_search_enrichment.py`

## How It Works
1. Takes a business name and optional city
2. Detects generic Bulgarian names (e.g., "Слънчице", "Звездичка") and appends city/country for disambiguation
3. Runs site-specific Google queries for: Facebook, Instagram, LinkedIn (company), YouTube, TikTok
4. Searches for decision makers via `"name" директор OR управител OR собственик site:linkedin.com`
5. Falls back to Facebook people search if LinkedIn yields no decision maker
6. Extracts names from LinkedIn/Facebook URL slugs with Bulgarian transliteration

## Usage

```bash
python executions/google_search_enrichment.py "Детска градина Слънчице" --city "София"
```

Optional: `--fields facebook instagram decision_maker` (search only specific fields)

## Output
JSON to stdout:
```json
{
  "facebook": "https://facebook.com/example",
  "instagram": null,
  "linkedin": "https://linkedin.com/company/example",
  "youtube": null,
  "tiktok": null,
  "gmb": null,
  "decision_maker_name": "Иван Петров",
  "decision_maker_linkedin": "https://linkedin.com/in/ivan-petrov",
  "notes": "DM personal contact requires manual research"
}
```

## Rate Limiting
- `INTER_ROW_PAUSE`: 20-40 seconds between rows (used by the enrichment pipeline)
- Per-query pause: 8-15 seconds (randomized)
- Exponential backoff on 429/rate-limit errors: 30s, 60s, 120s (3 retries)
- Uses `googlesearch-python` library (public Google, no API key)

## Constraints
- Google may block after heavy use — use `--resume` in the pipeline to continue later
- LinkedIn slug-to-name transliteration is approximate (Cyrillic approximation from Latin slugs)
- Generic business names are disambiguated with city, but may still return wrong results
- No API key required, but Google rate limiting applies

---

## Changelog
