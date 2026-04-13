# Scrape Google Maps by URL SOP — Outscraper Ingest Stage 1

## Objective

Re-scrape Google Maps detail pages for a list of businesses we already know about — typically an Outscraper export that contains `location_link` URLs but is missing canonical name, full address, category, rating, and review count. This is **stage 1** of the Outscraper → Supabase ingest pipeline (see `directives/run-ingest.md`).

This is **not** a general-purpose Maps scraper. For keyword-based searches, use `directives/scrape-google-maps.md` instead.

## Required Inputs

- An XLSX file produced by Outscraper (or any tool) containing a `location_link` column with full Google Maps place URLs
- Playwright with Chromium installed (`pip install playwright openpyxl && playwright install chromium`)

---

## Step 0 — First-Time Setup

```bash
pip install playwright openpyxl
playwright install chromium
```

---

## Step 1 — Smoke Test (10 rows, headed)

Always verify selectors still match the current Google Maps DOM before a full run:

```bash
python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --limit 10 --headed
```

Watch the browser, confirm the place detail panel opens, and inspect `tmp/gmaps_by_url.csv` for populated `name`, `address`, `category` columns.

---

## Step 2 — Full Run

```bash
python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --resume
```

The `--resume` flag makes the run safely restartable — the checkpoint at `tmp/gmaps_url_checkpoint.json` tracks both successful scrapes and failed URLs, so re-running only processes what's left.

---

## Step 3 — Resume After Interruption

If Google Maps rate-limits you or the machine crashes, just re-run the same command. The checkpoint is written every 10 rows.

```bash
python executions/scrape_gmaps_by_url.py --input tmp/outscraper.xlsx --resume
```

To retry previously failed URLs, delete the `"failed"` block from `tmp/gmaps_url_checkpoint.json` first.

---

## Output Columns

Written to `tmp/gmaps_by_url.csv`:

| Column | Source | Example |
|--------|--------|---------|
| legacy_id | Derived from URL Place ID (`os-<hex>`) | `os-f5bf0192ed80f05` |
| name | Page `h1.DUwDvf` | Аниматори София |
| address | Address button `aria-label` | бул. Витоша 1, София |
| city | Hardcoded "София" (Sofia-only ingest) | София |
| lat | URL `!3d<lat>` segment | 42.626264 |
| lng | URL `!4d<lng>` segment | 23.366592 |
| category | Category button text | Аниматор |
| rating | Rating span under heading | 4.7 |
| reviews_count | Review count aria-label | 38 |
| phone | Phone button `aria-label` | +359888123456 |
| maps_url | Original URL (unmodified) | https://www.google.com/maps/place/... |

`legacy_id` is stable across runs — derived from the Google Place ID (CID hex in the `!1s0x...:0x...` URL segment), so re-scraping the same URL always produces the same ID. Stage 3 uses this as the `businesses.legacy_id` upsert key.

---

## Timing

| Action | Time estimate |
|--------|--------------|
| Per URL (headless) | ~4–6 seconds (includes 2–4s random pause) |
| 100 URLs smoke test | ~8–12 minutes |
| Full 2,118 URLs | ~3–4 hours (split across multiple runs recommended) |

Checkpoint is flushed every 10 rows, so interruption losses are bounded.

---

## Known Constraints

| Constraint | Notes |
|-----------|-------|
| Selector instability | Maps DOM changes without notice. If `name` is empty across many rows, update selectors in `extract_detail()` in `scrape_gmaps_by_url.py`. |
| Rate limiting | Google may serve a CAPTCHA after a few hundred requests. The resumable checkpoint makes splitting runs across sessions safe. |
| Stale Place IDs | Some URLs from old exports redirect or 404. These land in `ckpt["failed"]` and are skipped on resume. |
| Lat/lng from URL | Coordinates are parsed from the URL (`!3d`/`!4d`), not scraped from the page — this is 100% reliable when the URL has the segment and saves a DOM query. |
| City field hardcoded | Always writes `"София"`. This script is Sofia-only by design — change the constant in `scrape_one()` if you ever repurpose it. |
| Phone extraction | Sometimes missing — Google only shows phones on verified places. Stage 2 merges with Outscraper's phone data, so gaps here are recoverable. |

---

## Checkpoint Format

`tmp/gmaps_url_checkpoint.json`:
```json
{
  "done": {
    "os-f5bf0192ed80f05": {
      "legacy_id": "os-f5bf0192ed80f05",
      "name": "Аниматори София",
      "address": "...",
      "...": "..."
    }
  },
  "failed": {
    "os-deadbeef": "extract_failed"
  }
}
```

On every run, the script writes every `"done"` entry to `tmp/gmaps_by_url.csv` — so a partial run already produces a usable CSV for downstream stages.

---

## Next Stage

Once `tmp/gmaps_by_url.csv` is ready:
```bash
python executions/merge_and_enrich.py --outscraper tmp/outscraper.xlsx --gmaps tmp/gmaps_by_url.csv
```

See `directives/merge-and-enrich.md`.

---

## Changelog
- 2026-04-11: Initial creation. Stage 1 of the Outscraper → Supabase ingest pipeline.
