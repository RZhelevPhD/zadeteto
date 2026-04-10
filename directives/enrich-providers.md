# Enrich Providers SOP — ZaDeteto Prospect Enrichment

## Objective
Take a raw Google Maps export (CSV or Excel) of Bulgarian childcare/education providers and enrich each record with emails, phone numbers, social media profiles, and decision maker names. Output goes to Google Sheets.

## Required Inputs
- Google Maps export file (CSV or Excel) — place in project root or `tmp/`
- `credentials.json` in project root (Google OAuth — see Step 0 if first time)
- Python dependencies installed (see Step 0)

---

## Step 0 — First-Time Setup

### Install Python dependencies

```bash
pip install requests beautifulsoup4 googlesearch-python \
            pandas openpyxl xlrd gspread \
            google-auth-oauthlib google-auth python-dotenv
```

### Set up Google Sheets OAuth (one-time only)

1. Go to: https://console.cloud.google.com/
2. Create or select a project → **APIs & Services** → **Enable APIs** → enable **Google Sheets API**
3. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
4. Application type: **Desktop app** → name it anything → click **Create**
5. Download the JSON → rename to `credentials.json` → place in project root
6. The first run of the enrichment tool will open a browser window for Google consent
7. After consent, `token.json` is saved automatically — subsequent runs are silent

> `credentials.json` and `token.json` are gitignored. Never commit them.

---

## Step 1 — Prepare Input File

1. Export providers from Google Maps (via a scraper or Outscraper/PhantomBuster output)
2. Place the file in `tmp/` (e.g., `tmp/google_maps_export.csv`)
3. Verify the file has at least a **name** column. Useful optional columns: `website`, `phone`, `city`, `address`, `google maps url`
4. Column names are case-insensitive and support both English and Bulgarian variants

---

## Step 2 — Create the Output Google Sheet

1. Open Google Sheets → create a new blank spreadsheet
2. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/**SHEET_ID_HERE**/edit`
3. Share the sheet with your Google account (the one used for OAuth)

---

## Step 3 — Run Enrichment

```bash
python executions/enrich_providers.py \
  --input tmp/google_maps_export.csv \
  --sheet-id YOUR_SHEET_ID \
  --sheet-name "Enriched"
```

**Options:**

| Flag | Description |
|------|-------------|
| `--input` | Path to CSV or Excel file (required) |
| `--sheet-id` | Google Sheets ID from the URL (required) |
| `--sheet-name` | Tab name in the sheet (default: "Enriched") |
| `--resume` | Skip rows already in `tmp/enrichment_progress.json` |
| `--no-search` | Crawl websites only, skip Google search (faster, less complete) |

---

## Step 4 — Resume After Interruption

If the run stopped mid-way (Google block, network issue, etc.):

```bash
python executions/enrich_providers.py \
  --input tmp/google_maps_export.csv \
  --sheet-id YOUR_SHEET_ID \
  --sheet-name "Enriched" \
  --resume
```

The checkpoint file `tmp/enrichment_progress.json` tracks every completed row. `--resume` skips any row that completed with status `enriched` or `partial`. Rows with status `failed` are re-attempted.

> Never delete `tmp/enrichment_progress.json` during or between runs.

---

## Step 5 — Review Output in Google Sheets

The enriched sheet contains all original columns plus:

| Column | Description |
|--------|-------------|
| Email | Primary email found on website |
| Additional Phone | Phone found on website (may differ from Google Maps phone) |
| Facebook URL | Facebook page link |
| Instagram URL | Instagram profile link |
| LinkedIn URL | LinkedIn company or personal page |
| GMB URL | Google My Business profile link |
| YouTube URL | YouTube channel |
| TikTok URL | TikTok profile |
| Decision Maker Name | Owner / director / manager name (from LinkedIn/Facebook) |
| DM Phone | Personal phone — usually blank, requires manual research |
| DM Email | Personal email — usually blank, requires manual research |
| Enrichment Status | `enriched` / `partial` / `failed` (see below) |
| Notes | Warnings or research notes |

**Status meanings:**

| Status | Meaning |
|--------|---------|
| `enriched` | 4+ fields found — ready for outreach |
| `partial` | 1–3 fields found — usable but review manually |
| `failed` | Nothing found — manual research required |

---

## Rate Limits and Timing

| Source | Pause | Notes |
|--------|-------|-------|
| Website crawl | 2–5s per page (network dependent) | Up to 3 pages per provider |
| Google search | 8–15s per query (randomized) | Built into `googlesearch-python` |
| Between rows | 20–40s (randomized) | Enforced in `enrich_providers.py` |
| Google Sheets write | Single batch at end | One write for all rows |

**Expected duration**: ~2–4 minutes per row with Google search enabled.

| Rows | Estimated time |
|------|---------------|
| 10 | 20–40 minutes |
| 50 | 2–3 hours |
| 100 | 3–7 hours |

Run overnight for large batches.

---

## Known Constraints

| Constraint | Notes |
|-----------|-------|
| Google blocks rapid searches | Built-in jittered delays with exponential backoff. Use `--resume` if blocked mid-run |
| Bulgarian sites without contact pages | Common — partial results expected. `partial` status is normal |
| LinkedIn requires login for full profiles | Only public name slug is extracted; transliteration may be approximate |
| DM personal contacts | Rarely publicly available. `DM Phone` and `DM Email` columns require manual outreach follow-up |
| Cyrillic business names | Passed to Google as-is — do NOT transliterate before searching |
| Generic business names (e.g. "Слънчице") | Tool appends city automatically to improve search precision |
| Excel BOM encoding | Handled automatically with `utf-8-sig` |
| `.xls` format | Requires `xlrd` package (included in setup) |

---

## Maintenance

**Re-run enrichment for failed rows only:**
```bash
python executions/enrich_providers.py --input tmp/file.csv --sheet-id ID --resume
```
Failed rows will be re-attempted; successful rows are skipped.

**Test a single website crawl:**
```bash
python executions/crawl_website.py https://detska-gradina-example.bg
```

**Test Google search for one provider:**
```bash
python executions/google_search_enrichment.py "Детска градина Слънчице" --city "София"
```

**If Google blocks the IP:**
- Wait 1–2 hours before resuming
- Or run with `--no-search` to crawl websites only without Google queries
