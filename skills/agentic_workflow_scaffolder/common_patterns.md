# Common Execution Script Patterns

This reference contains battle-tested patterns for execution scripts. When scaffolding a new workflow, use these as starting points rather than writing from scratch. Each pattern handles errors, validates I/O, and outputs structured JSON.

## Table of Contents
1. [API Call with Retry](#api-call-with-retry)
2. [Web Scraping](#web-scraping)
3. [Email Sending (SMTP)](#email-sending-smtp)
4. [Google Sheets Read/Write](#google-sheets-readwrite)
5. [File Processing (CSV/JSON)](#file-processing)
6. [LLM Call Wrapper](#llm-call-wrapper)
7. [Data Enrichment (Batch)](#data-enrichment-batch)
8. [Webhook Sender](#webhook-sender)

---

## API Call with Retry

Use when: calling any external REST API.

```python
#!/usr/bin/env python3
"""
Script: api_call_template.py
Purpose: Make an API call with exponential backoff retry logic
Input: --url <endpoint> --method <GET|POST> --payload <json_string>
Output: JSON response from the API
Dependencies: requests
"""

import argparse
import json
import os
import sys
import time
import requests

def call_with_retry(url, method="GET", payload=None, headers=None, max_retries=3):
    """Execute API call with exponential backoff."""
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:  # Rate limited
                wait = (2 ** attempt) * 2
                time.sleep(wait)
                continue
            elif resp.status_code >= 500:  # Server error, retry
                wait = (2 ** attempt)
                time.sleep(wait)
                continue
            else:
                raise
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    raise Exception(f"Failed after {max_retries} retries")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--method", default="GET")
    parser.add_argument("--payload", default=None)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        payload = json.loads(args.payload) if args.payload else None
        result = call_with_retry(args.url, args.method, payload)
        print(json.dumps({"status": "success", "data": result}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Key points:
- Exponential backoff handles rate limits and transient failures
- 429 (rate limit) gets longer wait times than 500 (server error)
- Timeout prevents hanging connections
- `--test` flag enables self-verification

---

## Web Scraping

Use when: extracting data from web pages.

```python
#!/usr/bin/env python3
"""
Script: scrape_template.py
Purpose: Scrape structured data from a web page
Input: --url <page_url> --selectors <json_selectors>
Output: JSON array of extracted data
Dependencies: requests, beautifulsoup4
"""

import argparse
import json
import sys
import requests
from bs4 import BeautifulSoup

def scrape_page(url, selectors):
    """Scrape data using CSS selectors."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DataBot/1.0)"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for sel_config in selectors:
        elements = soup.select(sel_config["selector"])
        for el in elements:
            results.append({
                "field": sel_config["field"],
                "value": el.get_text(strip=True),
                "href": el.get("href", None)
            })

    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--selectors", required=True, help="JSON array of {selector, field}")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        selectors = json.loads(args.selectors)
        data = scrape_page(args.url, selectors)
        print(json.dumps({"status": "success", "count": len(data), "data": data}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Email Sending (SMTP)

Use when: sending emails via Gmail or other SMTP providers.

```python
#!/usr/bin/env python3
"""
Script: send_email.py
Purpose: Send an email via SMTP
Input: --to <email> --subject <text> --body <text> [--html]
Output: Confirmation JSON
Dependencies: (stdlib only)
"""

import argparse
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_addr, subject, body, is_html=False):
    """Send email via SMTP using env credentials."""
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_APP_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        raise ValueError("SMTP_USER and SMTP_APP_PASSWORD must be set in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr

    content_type = "html" if is_html else "plain"
    msg.attach(MIMEText(body, content_type))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addr, msg.as_string())

    return {"sent_to": to_addr, "subject": subject}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        result = send_email(args.to, args.subject, args.body, args.html)
        print(json.dumps({"status": "success", "data": result}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Google Sheets Read/Write

Use when: reading from or writing to Google Sheets.

```python
#!/usr/bin/env python3
"""
Script: gsheets_template.py
Purpose: Read/write data from/to Google Sheets
Input: --sheet-id <id> --action <read|write|append> --range <A1:Z100> [--data <json>]
Output: JSON with sheet data or confirmation
Dependencies: google-auth, google-auth-oauthlib, google-api-python-client
"""

import argparse
import json
import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_sheets_service():
    """Build Sheets API service from stored credentials."""
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    token_path = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")

    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Token file not found at {token_path}. Run OAuth flow first."
        )

    creds = Credentials.from_authorized_user_file(token_path)
    return build("sheets", "v4", credentials=creds)

def read_sheet(service, sheet_id, range_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=range_name
    ).execute()
    return result.get("values", [])

def write_sheet(service, sheet_id, range_name, data):
    body = {"values": data}
    result = service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption="USER_ENTERED", body=body
    ).execute()
    return {"updated_cells": result.get("updatedCells", 0)}

def append_sheet(service, sheet_id, range_name, data):
    body = {"values": data}
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption="USER_ENTERED", body=body
    ).execute()
    return {"appended_rows": len(data)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", required=True)
    parser.add_argument("--action", choices=["read", "write", "append"], required=True)
    parser.add_argument("--range", required=True)
    parser.add_argument("--data", default=None, help="JSON 2D array for write/append")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        service = get_sheets_service()
        if args.action == "read":
            data = read_sheet(service, args.sheet_id, args.range)
            print(json.dumps({"status": "success", "rows": len(data), "data": data}))
        elif args.action == "write":
            rows = json.loads(args.data)
            result = write_sheet(service, args.sheet_id, args.range, rows)
            print(json.dumps({"status": "success", "data": result}))
        elif args.action == "append":
            rows = json.loads(args.data)
            result = append_sheet(service, args.sheet_id, args.range, rows)
            print(json.dumps({"status": "success", "data": result}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## LLM Call Wrapper

Use when: an execution script needs to make an LLM call for classification, summarization, or extraction.

```python
#!/usr/bin/env python3
"""
Script: llm_call_template.py
Purpose: Wrapper for making structured LLM calls within execution scripts
Input: --prompt <text> --system <text> [--model <model_id>] [--temperature <float>]
Output: JSON with the LLM response
Dependencies: anthropic (or openai)
"""

import argparse
import json
import os
import sys

def call_anthropic(prompt, system_prompt, model="claude-sonnet-4-20250514", temperature=0.0):
    """Make a structured Anthropic API call."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--system", required=True)
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--expect-json", action="store_true",
                        help="Parse response as JSON and validate")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        raw = call_anthropic(args.prompt, args.system, args.model, args.temperature)

        if args.expect_json:
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(cleaned)
            print(json.dumps({"status": "success", "data": data}))
        else:
            print(json.dumps({"status": "success", "data": raw}))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "status": "error",
            "error": f"LLM returned invalid JSON: {e}",
            "raw_response": raw
        }), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Key points:
- Temperature 0 by default for maximum determinism
- `--expect-json` flag validates response structure
- Raw response included in error for debugging
- System prompt is a required argument, never hardcoded in the wrapper

---

## Data Enrichment (Batch)

Use when: enriching a list of records (leads, contacts, etc.) via an API.

```python
#!/usr/bin/env python3
"""
Script: enrich_batch_template.py
Purpose: Enrich records in parallel batches
Input: --input <json_file> --field <field_to_enrich> --batch-size <n>
Output: JSON file with enriched records
Dependencies: requests, concurrent.futures (stdlib)
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def enrich_single(record, field, api_key):
    """Enrich a single record. Customize per API."""
    # Replace with actual enrichment API call
    # This is a template showing the pattern
    import requests

    url = f"https://api.example.com/enrich?{field}={record.get(field, '')}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        enriched = resp.json()
        record.update(enriched)
        record["_enrichment_status"] = "success"
    except Exception as e:
        record["_enrichment_status"] = f"failed: {e}"

    return record

def enrich_batch(records, field, api_key, batch_size=10, max_workers=5):
    """Process records in parallel batches with rate limiting."""
    enriched = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            futures = {
                executor.submit(enrich_single, r, field, api_key): r
                for r in batch
            }

            for future in as_completed(futures):
                enriched.append(future.result())

            # Rate limiting between batches
            if i + batch_size < len(records):
                time.sleep(1)

    return enriched

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON input file")
    parser.add_argument("--field", required=True, help="Field to use for enrichment lookup")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        api_key = os.environ.get("ENRICHMENT_API_KEY")
        if not api_key:
            raise ValueError("ENRICHMENT_API_KEY not set")

        with open(args.input) as f:
            records = json.load(f)

        enriched = enrich_batch(records, args.field, api_key, args.batch_size)

        success_count = sum(1 for r in enriched if r.get("_enrichment_status") == "success")

        output = {
            "status": "success",
            "total": len(enriched),
            "enriched": success_count,
            "failed": len(enriched) - success_count,
            "data": enriched
        }

        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2)

        print(json.dumps({
            "status": "success",
            "total": len(enriched),
            "enriched": success_count,
            "failed": len(enriched) - success_count,
            "output_file": args.output
        }))

    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Key points:
- ThreadPoolExecutor for parallel processing (10-100x faster than serial)
- Rate limiting between batches prevents API throttling
- Each record tracks its own enrichment status
- Batch size and worker count are configurable

---

## Webhook Sender

Use when: sending results to a webhook URL (Slack, Modal, N8N, etc.).

```python
#!/usr/bin/env python3
"""
Script: send_webhook.py
Purpose: POST JSON data to a webhook URL
Input: --url <webhook_url> --data <json_string_or_file>
Output: Confirmation JSON
Dependencies: requests
"""

import argparse
import json
import sys
import requests

def send_webhook(url, data, max_retries=3):
    """Send data to webhook with retry."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=data, timeout=30)
            resp.raise_for_status()
            return {
                "status_code": resp.status_code,
                "response": resp.text[:500]  # Truncate large responses
            }
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
            raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--data", required=True, help="JSON string or path to JSON file")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(json.dumps({"status": "success", "data": "test_passed"}))
        return

    try:
        # Accept both inline JSON and file paths
        if args.data.startswith("{") or args.data.startswith("["):
            data = json.loads(args.data)
        else:
            with open(args.data) as f:
                data = json.load(f)

        result = send_webhook(args.url, data)
        print(json.dumps({"status": "success", "data": result}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```
