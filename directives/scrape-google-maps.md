# Scrape Google Maps SOP — ZaDeteto Lead Generation

## Objective
Scrape Bulgarian childcare/education providers from Google Maps by keyword and city. Output is a CSV ready to feed directly into the enrichment pipeline (`directives/enrich-providers.md`).

## Required Inputs
- A keyword (e.g. "детска градина", "частна детска ясла")
- A city (e.g. "София", "Варна", "Пловдив")
- OR a `keywords.csv` file with `keyword` and `city` columns for batch mode
- For the full pipeline: `credentials.json` in project root (Google Sheets OAuth)

---

## Step 0 — First-Time Setup

```bash
pip install playwright pandas
playwright install chromium
```

> `playwright install chromium` downloads a ~180MB Chromium browser binary to a local cache. This is a one-time step per machine. The browser runs invisibly in the background by default.

---

## Step 1 — Single Keyword/City Run

```bash
python executions/scrape_google_maps.py --keyword "детска градина" --city "София"
```

Output is saved to `tmp/scraped_детска_градина_София_TIMESTAMP.csv`.

To **watch the browser** work in real time (headed mode):
```bash
python executions/scrape_google_maps.py --keyword "детска ясла" --city "Варна" --headed
```

> In headed mode, a Chrome window opens and controls itself. You can use other apps freely — just don't click inside that Chrome window or you may interrupt the scrape.

---

## Step 2 — Batch Mode (Keywords Spreadsheet)

Prepare a `keywords.csv` file (or Excel) with exactly these column names:

```csv
keyword,city
детска градина,София
детска ясла,Варна
частна детска градина,Пловдив
детска градина,Бургас
```

Run:
```bash
python executions/scrape_google_maps.py --input keywords.csv
```

Each keyword/city pair produces its own CSV in `tmp/`. Use `--resume` to skip pairs already completed if the run was interrupted:
```bash
python executions/scrape_google_maps.py --input keywords.csv --resume
```

---

## Step 3 — Full Pipeline (Scrape + Enrich)

Scrapes Google Maps then automatically enriches each result with emails, phones, social profiles, and decision maker names — in a single command:

```bash
python executions/run_pipeline.py \
  --keyword "детска градина" --city "Варна" \
  --sheet-id YOUR_SHEET_ID \
  --sheet-name "Варна Детски"
```

Batch mode with a keywords file:
```bash
python executions/run_pipeline.py \
  --input keywords.csv \
  --sheet-id YOUR_SHEET_ID \
  --sheet-name "Enriched" \
  --resume
```

Scrape websites only (skip Google search enrichment — much faster):
```bash
python executions/run_pipeline.py \
  --input keywords.csv \
  --sheet-id YOUR_SHEET_ID \
  --no-search
```

---

## Step 4 — Resume After Interruption

**Scraper only:**
```bash
python executions/scrape_google_maps.py --input keywords.csv --resume
```

**Full pipeline:**
```bash
python executions/run_pipeline.py --input keywords.csv --sheet-id ID --resume
```

Checkpoints:
- `tmp/scrape_checkpoint.json` — tracks completed keyword/city pairs
- `tmp/enrichment_progress.json` — tracks enriched rows (from `enrich_providers.py`)

Never delete these files during or between runs.

---

## Output Columns

The scraper CSV contains these 9 columns, which feed directly into `enrich_providers.py`:

| Column | Example |
|--------|---------|
| name | Детска градина "Слънчице" |
| category | Детска градина |
| address | ул. Витоша 12, София |
| city | София |
| phone | (empty — recovered in enrichment step) |
| website | https://gradina-slanchitze.bg |
| rating | 4.7 |
| reviews | 38 |
| google maps url | https://www.google.com/maps/place/... |

> **Phone is intentionally empty** — Google Maps only shows phone numbers on individual business pages, not in search results. The enrichment step recovers phone numbers by crawling each provider's website.

---

## Timing

| Action | Time estimate |
|--------|--------------|
| Single keyword/city (headless) | 2–5 minutes for ~120 results |
| Per keyword/city pair (batch) | 2–5 minutes each |
| Full pipeline per row | +2–4 minutes for enrichment |

Google Maps caps results at approximately 120 per search query.

---

## Known Constraints

| Constraint | Notes |
|-----------|-------|
| ~120 results cap per search | Google Maps limits search results. For large cities, split by neighbourhood (e.g. "детска градина Люлин") |
| Phone not in scraper output | Only available on business detail pages. Recovered via website crawl in enrichment |
| CAPTCHAs | Rare in headless mode. If it happens, run with `--headed` to solve manually, then `--resume` |
| Selector instability | Google Maps DOM changes occasionally. If extraction looks empty, check `div.fontBodyMedium` and `a[aria-label]` in Chrome DevTools |
| End-of-list sentinel `span.HlvSq` | May change on Google Maps updates — if scrolling never stops, the `NO_NEW_RESULTS_THRESHOLD` (3 consecutive empty scrolls) will still stop it |
| Cyrillic in filenames | Non-word characters in keyword/city are replaced with `_` in the output filename |

---

## Maintenance

**Test a single scrape with visible browser:**
```bash
python executions/scrape_google_maps.py --keyword "детска градина" --city "Бургас" --headed
```

**Check what was scraped:**
```bash
# List all output files
ls tmp/scraped_*.csv
```

**Run enrichment on an existing scraped CSV:**
```bash
python executions/enrich_providers.py \
  --input tmp/scraped_детска_градина_София_20240101_120000.csv \
  --sheet-id YOUR_SHEET_ID
```

**Large city coverage strategy** — Google Maps returns ~120 results per query. For Sofia, split by area:
```csv
keyword,city
детска градина,София Люлин
детска градина,София Младост
детска градина,София Витоша
детска градина,София Надежда
детска ясла,София
частна детска градина,София
```
