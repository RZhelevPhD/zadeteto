---
name: google-maps-scraper
description: Scrape Google Maps for Bulgarian childcare/education providers by keyword and city using Playwright browser automation. Use this skill when the user wants to find детски градини, детски ясли, or other providers in a specific city, build a lead list from Google Maps, or run the scraper tool.
argument-hint: "детска градина" София
---

# Google Maps Scraper

## When to Use
- User says "scrape Google Maps", "find providers in X city", "build a list of детски градини"
- User provides a keyword and city and wants a list of businesses
- User wants to run the lead generation pipeline
- User has a keywords spreadsheet and wants to scrape multiple cities

## Required Inputs
Before running, confirm you have:
1. **Keyword** — e.g. `детска градина`, `частна детска ясла`, `детски център`
2. **City** — e.g. `София`, `Варна`, `Пловдив`
3. OR **Keywords file** — CSV/Excel with `keyword` and `city` columns for batch mode
4. **For full pipeline only**: `credentials.json` in project root + a Google Sheets ID

If any are missing, ask the user before proceeding.

## How to Execute

### Scenario 1 — Scrape only (single keyword/city)
```bash
python executions/scrape_google_maps.py --keyword "детска градина" --city "София"
```
Output: `tmp/scraped_детска_градина_София_TIMESTAMP.csv`

### Scenario 2 — Batch scrape from spreadsheet
Prepare `keywords.csv` with columns `keyword` and `city`, then:
```bash
python executions/scrape_google_maps.py --input keywords.csv --resume
```

### Scenario 3 — Full pipeline (scrape → enrich → Google Sheets)
```bash
python executions/run_pipeline.py \
  --keyword "детска градина" --city "Варна" \
  --sheet-id SHEET_ID \
  --sheet-name "Варна"
```
Or batch:
```bash
python executions/run_pipeline.py --input keywords.csv --sheet-id SHEET_ID --resume
```

### Watch the browser work (optional)
Add `--headed` to any command to open a visible Chrome window.

## First-Time Setup
```bash
pip install playwright pandas
playwright install chromium
```
`playwright install chromium` is a one-time step — downloads ~180MB Chromium binary.

## Resume After Interruption
Add `--resume` to skip already-completed pairs. Checkpoint: `tmp/scrape_checkpoint.json`

## Output Columns
`name` | `category` | `address` | `city` | `phone` | `website` | `rating` | `reviews` | `google maps url`

> Phone is empty in scraper output — it is recovered automatically during the enrichment step by crawling each provider's website.

## Important Notes
- Google Maps caps results at ~120 per search query. For large cities, split by neighbourhood.
- Runs headless (invisible) by default — you can use your computer normally while it runs.
- In `--headed` mode, a Chrome window opens. Don't click inside it while it's working.

## Next Step
Feed scraper output into the `prospect-enrichment` skill to add emails, social profiles, and decision maker names, or use `run_pipeline.py` to do it automatically.

## Reference
Full SOP: `directives/scrape-google-maps.md`
Tools: `executions/scrape_google_maps.py`, `executions/run_pipeline.py`
