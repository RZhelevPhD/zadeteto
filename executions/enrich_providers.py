import os
import re
import sys
import json
import time
import random
import argparse

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import crawl_website
import google_search_enrichment

PHONE_RE = re.compile(r"^\+?[\d\s\-\.\(\)]{7,}$")

INPUT_COLUMN_ALIASES = {
    "business name": "name",
    "name": "name",
    "название": "name",
    "наименование": "name",
    "category": "category",
    "категория": "category",
    "address": "address",
    "адрес": "address",
    "city": "city",
    "град": "city",
    "phone": "phone_existing",
    "телефон": "phone_existing",
    "phone number": "phone_existing",
    "website": "website",
    "уебсайт": "website",
    "сайт": "website",
    "google maps url": "gmaps_url",
    "maps url": "gmaps_url",
    "url": "gmaps_url",
    "link": "gmaps_url",
    "rating": "rating",
    "рейтинг": "rating",
    "reviews": "reviews",
    "отзиви": "reviews",
}

SOCIAL_FIELDS = [
    "Facebook URL", "Instagram URL", "LinkedIn URL",
    "GMB URL", "YouTube URL", "TikTok URL",
]

SEARCH_FIELD_MAP = {
    "Facebook URL":  "facebook",
    "Instagram URL": "instagram",
    "LinkedIn URL":  "linkedin",
    "YouTube URL":   "youtube",
    "TikTok URL":    "tiktok",
    "GMB URL":       "gmb",
}

OUTPUT_NEW_COLUMNS = [
    "Email",
    "Additional Phone",
    "Facebook URL",
    "Instagram URL",
    "LinkedIn URL",
    "GMB URL",
    "YouTube URL",
    "TikTok URL",
    "Decision Maker Name",
    "DM Phone",
    "DM Email",
    "Enrichment Status",
    "Notes",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in INPUT_COLUMN_ALIASES:
            rename_map[col] = INPUT_COLUMN_ALIASES[key]
    return df.rename(columns=rename_map)


def _fix_swapped_columns(row: pd.Series) -> pd.Series:
    row = row.copy()
    website = str(row.get("website", "") or "")
    if website and PHONE_RE.match(website.strip()) and not website.startswith("http"):
        existing_phone = str(row.get("phone_existing", "") or "")
        if not existing_phone:
            row["phone_existing"] = website
        row["website"] = ""
    return row


def _load_checkpoint(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rows": {}}


def _save_checkpoint(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_sheets_client():
    import gspread
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "credentials.json not found. Download it from Google Cloud Console "
                    "(APIs & Services -> Credentials -> OAuth 2.0 Client -> Desktop app)."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return gspread.authorize(creds)


def _write_to_sheets(client, sheet_id: str, sheet_name: str, rows: list[list]):
    import gspread

    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=len(rows) + 10, cols=len(rows[0]) + 5)

    for attempt in range(3):
        try:
            worksheet.clear()
            worksheet.update(rows, value_input_option="USER_ENTERED")
            return
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = (2 ** attempt) * 30
                print(f"  Sheets API rate limit hit, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def _process_row(row: pd.Series) -> dict:
    result = {col: "" for col in OUTPUT_NEW_COLUMNS}
    notes = []

    row = _fix_swapped_columns(row)
    website = str(row.get("website", "") or "").strip()
    name = str(row.get("name", "") or "").strip()
    city = str(row.get("city", "") or "").strip()

    if website and website.startswith("http"):
        print(f"    Crawling {website} ...")
        crawl_data = crawl_website.crawl(website)
        if crawl_data["emails"]:
            result["Email"] = crawl_data["emails"][0]
        if crawl_data["phones"]:
            result["Additional Phone"] = crawl_data["phones"][0]
        result["Facebook URL"] = crawl_data.get("facebook") or ""
        result["Instagram URL"] = crawl_data.get("instagram") or ""
        result["LinkedIn URL"] = crawl_data.get("linkedin") or ""
        result["GMB URL"] = crawl_data.get("gmb") or ""
        result["YouTube URL"] = crawl_data.get("youtube") or ""
        result["TikTok URL"] = crawl_data.get("tiktok") or ""

    if name:
        missing_social_keys = [
            SEARCH_FIELD_MAP[f] for f in SOCIAL_FIELDS if not result[f]
        ]
        search_fields = missing_social_keys + ["decision_maker"]

        print(f"    Searching Google for: {name} ...")
        search_data = google_search_enrichment.enrich_by_search(
            business_name=name,
            city=city,
            missing_fields=search_fields,
        )

        for output_col, search_key in SEARCH_FIELD_MAP.items():
            if not result[output_col] and search_data.get(search_key):
                result[output_col] = search_data[search_key]

        result["Decision Maker Name"] = search_data.get("decision_maker_name", "")
        result["DM Phone"] = ""
        result["DM Email"] = ""

        if search_data.get("notes"):
            notes.append(search_data["notes"])

    filled = sum(1 for col in OUTPUT_NEW_COLUMNS[:-2] if result[col])
    if filled >= 4:
        result["Enrichment Status"] = "enriched"
    elif filled >= 1:
        result["Enrichment Status"] = "partial"
    else:
        result["Enrichment Status"] = "failed"
        notes.append("No data found")

    result["Notes"] = "; ".join(notes)
    return result


def main():
    parser = argparse.ArgumentParser(description="Enrich Google Maps provider list with contact and social data")
    parser.add_argument("--input", required=True, help="Path to CSV or Excel input file")
    parser.add_argument("--sheet-id", required=True, help="Google Sheets ID (from the URL)")
    parser.add_argument("--sheet-name", default="Enriched", help="Tab name in the sheet")
    parser.add_argument("--resume", action="store_true", help="Skip rows already in checkpoint")
    parser.add_argument("--no-search", action="store_true", help="Skip Google search (crawl only)")
    args = parser.parse_args()

    checkpoint_path = os.path.join("tmp", "enrichment_progress.json")
    checkpoint = _load_checkpoint(checkpoint_path)
    checkpoint["input_file"] = args.input
    checkpoint["sheet_id"] = args.sheet_id

    ext = os.path.splitext(args.input)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(args.input, encoding="utf-8-sig")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(args.input)
    else:
        print(f"ERROR: Unsupported file type: {ext}. Use .csv, .xlsx, or .xls")
        sys.exit(1)

    df = _normalize_columns(df)
    total = len(df)
    print(f"Loaded {total} rows from {args.input}")

    enriched_results = []

    for idx, row in df.iterrows():
        row_key = str(idx)

        if args.resume and row_key in checkpoint.get("rows", {}):
            status = checkpoint["rows"][row_key].get("Enrichment Status", "")
            if status != "failed":
                print(f"[{idx+1}/{total}] Skipping (already enriched)")
                enriched_results.append(checkpoint["rows"][row_key])
                continue

        name = str(row.get("name", "") or "").strip()
        print(f"[{idx+1}/{total}] Processing: {name or '(unnamed)'}")

        result = {col: "" for col in OUTPUT_NEW_COLUMNS}
        try:
            if args.no_search:
                row_copy = _fix_swapped_columns(row)
                website = str(row_copy.get("website", "") or "").strip()
                if website and website.startswith("http"):
                    crawl_data = crawl_website.crawl(website)
                    result["Email"] = crawl_data["emails"][0] if crawl_data["emails"] else ""
                    result["Additional Phone"] = crawl_data["phones"][0] if crawl_data["phones"] else ""
                    for out_col, key in SEARCH_FIELD_MAP.items():
                        result[out_col] = crawl_data.get(key) or ""
                filled = sum(1 for col in OUTPUT_NEW_COLUMNS[:-2] if result[col])
                result["Enrichment Status"] = "enriched" if filled >= 4 else ("partial" if filled >= 1 else "failed")
            else:
                result = _process_row(row)
        except Exception as e:
            print(f"  ERROR: {e}")
            result["Enrichment Status"] = "failed"
            result["Notes"] = f"Error: {str(e)[:200]}"

        checkpoint.setdefault("rows", {})[row_key] = result
        _save_checkpoint(checkpoint, checkpoint_path)
        enriched_results.append(result)

        pause = random.uniform(*google_search_enrichment.INTER_ROW_PAUSE)
        if not args.no_search and idx < total - 1:
            print(f"  Waiting {pause:.0f}s before next row...")
            time.sleep(pause)

    print("\nWriting results to Google Sheets...")
    all_input_cols = list(df.columns)
    header = all_input_cols + OUTPUT_NEW_COLUMNS
    rows_out = [header]

    for idx, (_, row) in enumerate(df.iterrows()):
        input_vals = [str(row.get(col, "") or "") for col in all_input_cols]
        enrich_vals = enriched_results[idx] if idx < len(enriched_results) else {col: "" for col in OUTPUT_NEW_COLUMNS}
        output_vals = [str(enrich_vals.get(col, "") or "") for col in OUTPUT_NEW_COLUMNS]
        rows_out.append(input_vals + output_vals)

    try:
        client = _get_sheets_client()
        _write_to_sheets(client, args.sheet_id, args.sheet_name, rows_out)
        print(f"Done. {len(rows_out)-1} rows written to sheet '{args.sheet_name}'.")
        print(f"Open: https://docs.google.com/spreadsheets/d/{args.sheet_id}")
    except Exception as e:
        print(f"ERROR writing to Sheets: {e}")
        fallback = os.path.join("tmp", "enriched_output.csv")
        pd.DataFrame(rows_out[1:], columns=rows_out[0]).to_csv(fallback, index=False, encoding="utf-8-sig")
        print(f"Fallback CSV saved to: {fallback}")


if __name__ == "__main__":
    main()
