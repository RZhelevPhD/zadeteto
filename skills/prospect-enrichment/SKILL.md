---
name: prospect-enrichment
description: Enrich a CSV or Excel list of Bulgarian childcare/education providers scraped from Google Maps with emails, phone numbers, social media profiles (Facebook, Instagram, LinkedIn, YouTube, TikTok, GMB), and decision maker names. Use this skill when the user provides a supplier list, prospect list, or Google Maps export and asks to find contact info, emails, social media pages, or decision makers.
argument-hint: path/to/google_maps_export.csv
---

# Prospect Enrichment

## When to Use
- User provides a CSV or Excel file and asks to "enrich" it
- User asks to "find emails / phones / social media" for a list of providers
- User asks "who runs this детска градина" or wants decision maker names
- User says "run enrichment", "enrich these providers", "get their contacts"
- User drops a Google Maps export and asks what to do next

## Required Inputs
Before running, confirm you have:
1. **Input file path** — CSV or Excel exported from Google Maps scraper
2. **Google Sheets ID** — from the sheet URL: `docs.google.com/spreadsheets/d/**ID**/edit`
3. **Sheet tab name** — default is `"Enriched"` if the user doesn't specify
4. **`credentials.json`** — must exist in project root for Google Sheets auth

If any are missing, ask the user before proceeding.

## How to Execute

### Step 1 — Check dependencies
```bash
pip install requests beautifulsoup4 googlesearch-python pandas openpyxl xlrd gspread google-auth-oauthlib google-auth python-dotenv
```

### Step 2 — Verify credentials.json
Check that `credentials.json` exists in the project root. If not, direct the user to `directives/enrich-providers.md` Step 0 for the one-time Google OAuth setup.

### Step 3 — Run enrichment
```bash
python executions/enrich_providers.py \
  --input PATH_TO_FILE \
  --sheet-id SHEET_ID \
  --sheet-name "Enriched"
```

To crawl websites only (no Google search, faster):
```bash
python executions/enrich_providers.py --input PATH --sheet-id ID --no-search
```

### Step 4 — Monitor and report
- Print progress to the user every 10 rows
- On completion, share the Google Sheets URL:
  `https://docs.google.com/spreadsheets/d/SHEET_ID`

## Resume After Failure
If the run was interrupted (Google block, crash, etc.):
```bash
python executions/enrich_providers.py --input PATH --sheet-id ID --resume
```
The checkpoint at `tmp/enrichment_progress.json` remembers completed rows. Never delete it mid-run.

## Rate Limiting Warning
Google search enrichment takes 20–40 seconds per row.
- **Do NOT run multiple instances simultaneously**
- Tell the user the estimated duration before starting (see table below)
- If Google blocks: wait 1–2 hours, then `--resume`

| Rows | Estimated time |
|------|---------------|
| 10 | 20–40 min |
| 50 | 2–3 hours |
| 100 | 3–7 hours |

## Output Columns Added
| Column | Source |
|--------|--------|
| Email | Website crawl |
| Additional Phone | Website crawl |
| Facebook URL | Website crawl → Google search |
| Instagram URL | Website crawl → Google search |
| LinkedIn URL | Website crawl → Google search |
| GMB URL | Website crawl → Google search |
| YouTube URL | Website crawl → Google search |
| TikTok URL | Website crawl → Google search |
| Decision Maker Name | Google search (LinkedIn/Facebook slug) |
| DM Phone | Not auto-filled — requires manual outreach |
| DM Email | Not auto-filled — requires manual outreach |
| Enrichment Status | `enriched` / `partial` / `failed` |
| Notes | Warnings and research notes |

## Output Status Meanings
- **enriched** — 4+ fields found, ready for outreach
- **partial** — 1–3 fields found, usable but needs manual review
- **failed** — nothing found, manual research required

## Cyrillic Handling
- Pass Bulgarian business names to Google search **as-is in Cyrillic**
- Do NOT transliterate names before searching
- Generic names (Слънчице, Детелина, etc.) automatically get city appended

## Reference
Full SOP: `directives/enrich-providers.md`
Tools: `executions/crawl_website.py`, `executions/google_search_enrichment.py`, `executions/enrich_providers.py`
