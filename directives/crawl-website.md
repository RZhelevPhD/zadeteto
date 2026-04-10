# Crawl Website Directive — Contact & Social Data Extraction

## Objective
Crawl a single business website to extract contact information (emails, phones) and social media profiles (Facebook, Instagram, LinkedIn, YouTube, TikTok, Google My Business).

## Execution Script
`executions/crawl_website.py`

## How It Works
1. Normalizes the input URL (adds https:// if missing, strips trailing slashes)
2. Fetches the homepage
3. Attempts up to 2 additional pages by appending common contact-page suffixes: `/kontakti`, `/kontakt`, `/contact`, `/contacts`, `/za-nas`, `/za_nas`, `/about`, `/about-us`
4. Extracts emails via regex, filtering out junk domains (example.com, schema.org, etc.) and image file extensions
5. Extracts Bulgarian phone numbers (+359 format, 08x/09x mobile, 02-07 landline), normalizes to +359 format
6. Extracts social media URLs from all `<a href>` elements using platform-specific regex patterns

## Usage

```bash
python executions/crawl_website.py https://detska-gradina-example.bg
```

Optional: `--timeout 15` (default: 10 seconds per page)

## Output
JSON to stdout:
```json
{
  "emails": ["info@example.bg"],
  "phones": ["+359888123456"],
  "facebook": "https://facebook.com/example",
  "instagram": null,
  "linkedin": null,
  "youtube": null,
  "tiktok": null,
  "gmb": null
}
```

## Constraints
- Maximum 3 pages fetched per website (homepage + 2 contact pages)
- No JavaScript rendering — static HTML only (sites with SPAs may yield fewer results)
- Randomized User-Agent from a pool of 3 Chrome strings
- No rate limiting needed (single website per call)

---

## Changelog
