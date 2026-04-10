# Run Pipeline Directive — Full Lead Generation Orchestration

## Objective
Orchestrate the complete lead generation pipeline: scrape Google Maps for Bulgarian businesses, then enrich each result with contact data and social profiles, and output to Google Sheets.

## Execution Script
`executions/run_pipeline.py`

## Pipeline Steps
1. **Scrape** — Calls `executions/scrape_google_maps.py` with the given keyword/city or batch input file. Produces one or more CSVs in `tmp/`.
2. **Enrich** — For each CSV produced by the scraper, calls `executions/enrich_providers.py` to crawl websites and search Google for emails, phones, social profiles, and decision maker names.
3. **Output** — Writes enriched results to a Google Sheets tab.

## Usage

Single keyword/city:
```bash
python executions/run_pipeline.py \
  --keyword "детска градина" --city "Варна" \
  --sheet-id YOUR_SHEET_ID \
  --sheet-name "Варна"
```

Batch mode:
```bash
python executions/run_pipeline.py \
  --input keywords.csv \
  --sheet-id YOUR_SHEET_ID \
  --sheet-name "Enriched" \
  --resume
```

## CLI Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--keyword` | One of keyword/city or --input | Search keyword |
| `--city` | One of keyword/city or --input | City name |
| `--input` | One of keyword/city or --input | CSV/Excel with keyword,city columns |
| `--sheet-id` | Yes | Google Sheets ID from URL |
| `--sheet-name` | No | Tab name (default: "Enriched") |
| `--headed` | No | Show browser during scraping |
| `--resume` | No | Skip completed steps |
| `--no-search` | No | Crawl websites only, skip Google search |

## Prerequisites
- Python dependencies: `playwright pandas requests beautifulsoup4 googlesearch-python gspread google-auth-oauthlib`
- Playwright browser: `playwright install chromium`
- `credentials.json` in project root (Google OAuth)

## Checkpoints
- `tmp/scrape_checkpoint.json` — completed keyword/city pairs
- `tmp/enrichment_progress.json` — completed enrichment rows

Never delete these during or between runs.

## Timing
- Scraping: 2-5 minutes per keyword/city pair (~120 results max)
- Enrichment: 2-4 minutes per row with Google search
- Full run for 100 rows: 3-7 hours (run overnight for large batches)

---

## Changelog
