# Enrich & Reclassify Prospects — Directive

## Purpose

Take the cleaned prospect list produced by `clean-segment-prospects` and upgrade its niche classification by fetching each prospect's actual website and using the richer extracted text (homepage title, meta description, about/contact copy, body text) as the classification input. This fixes the root cause of ~35% `other` tagging in the base pipeline: the Outscraper scrape only captured snippets of each site.

## Inputs

- `tmp/prospects_clean.csv` — deduped + segmented output of `clean_segment_prospects.py`.
- The same niche taxonomy defined in `executions/clean_segment_prospects.py` (`NICHES`). This directive reuses that taxonomy verbatim — the enrichment script imports `classify`, `NICHE_META`, `NICHE_ORDER`, and `FALLBACK_RULES` from that module.

## Outputs

- `tmp/prospects_enriched.csv` — same schema as `prospects_clean.csv` but with niches re-computed from richer text, and with a handful of new columns (see below).
- `tmp/prospects_enriched_report.json` — run summary: crawl success rate, niche reclassification deltas, top "still other" domains for manual review.
- `tmp/prospects_enriched_raw.jsonl` — one JSON record per prospect with the full extracted text + HTTP status. Cached so a re-run does not re-crawl; pass `--refresh` to force re-crawl.

## Crawl strategy

For each prospect with a non-empty `domain`:

1. Defensively normalize the domain via a local `normalize_domain` helper (lowercases, strips scheme, `www.`, trailing path/query/fragment, trailing dots). Input CSVs should already be clean; this is a belt-and-braces pass. Then build `https://<domain>`.
2. Fetch homepage with a random browser User-Agent, `Accept-Language: bg,en;q=0.9`, timeout 10 s, follow redirects. If the server returns no charset or declares `ISO-8859-1` (the `requests` default that mangles Cyrillic), fall back to `resp.apparent_encoding` before reading `.text`.
3. If homepage returned a valid HTML body, also attempt these secondary paths (up to 2 more, first-success-wins for each):
   - `/za-nas`, `/about`, `/about-us`, `/kontakti`, `/kontakt`, `/contact`
4. If the HTTPS fetch yields no usable body (timeout, non-200, SSL error, DNS, empty body), retry once over `http://` before giving up.
5. Parallelize with `ThreadPoolExecutor`, default 10 workers. Each worker handles one domain end-to-end and appends its raw record to the JSONL cache under a lock. After the executor block, the cache is re-loaded from disk so any partial progress from a crashed worker is picked up.
6. Be polite: no per-worker sleep, but cap concurrency at 10. If we hit a block, log and move on.

Do NOT crawl:
- Domains that are shared platforms (carries many unrelated businesses), identified by matching a blocklist.
  - Exact-match blocklist: `youtu.be`, `youtube.com`, `facebook.com`, `fb.me`, `instagram.com`, `sites.google.com`, `taplink.ws`, `linktr.ee`, `wordpress.com`, `preview.bg`, `easybook.bg`, `superdoc.bg`, `uchiteli.bg`, `zdraveopazvaneto.bg`, `zdravenregister.com`, `clickandplay.bg`.
  - Suffix-match blocklist (any domain ending in one of these): `.taplink.ws`, `.my.canva.site`, `.blogspot.com`, `.blogspot.bg`, `.wordpress.com`, `.alle.bg`.
  - These can't represent a single prospect's niche.

Blocklisted rows are **not dropped** — they survive in the output with `http_status = "skipped_blocklist"`, `crawled_pages = 0`, and `niche_primary = "other_uncrawled"` (unless the pre-existing Outscraper text already yielded a niche, in which case that niche is kept). This keeps the row count stable between input and output.

## Text extraction

From each fetched HTML page:
- `<title>` — stripped
- `<meta name="description">` and `<meta property="og:description">` — stripped
- Main body text: strip `<script>`, `<style>`, `<noscript>`, `<nav>`, `<footer>`, `<header>`; then `get_text(separator=" ", strip=True)`. Collapse whitespace. Truncate to the first 8000 characters to keep things bounded.

Concatenate across all fetched pages for a prospect into a single `crawled_text` field, separated by ` | `.

## Reclassification

Build the classification input as:
```
name_best + " " + website_title + " " + website_description + " " + domain + " " + crawled_text
```
Lowercased, then passed to `classify()` from `clean_segment_prospects.py`.

- If `classify()` returns a non-empty list → use those niches, sorted by priority DESC as the underlying function guarantees.
- If still empty AND the crawl genuinely succeeded (`http_status == 200` and `crawled_text` length > 200 chars) → mark `niche_primary = "other_crawled"` so the row is distinguishable from "other uncrawlable".
- If the crawl failed entirely (no text fetched) → mark `niche_primary = "other_uncrawled"` so rows with zero evidence don't pollute `other`.

Both `other_crawled` and `other_uncrawled` map to sphere `Друго / за ръчен преглед`.

## New/updated output columns (compared to `prospects_clean.csv`)

Add:
- `http_status` — primary page HTTP status or `error:<reason>`.
- `crawled_pages` — count of pages successfully fetched.
- `crawled_text_len` — len of combined extracted text (chars).
- `niche_primary_before` — the niche from `prospects_clean.csv` (for easy diff).
- `niches_changed` — boolean, true if new `niche_primary` differs from `niche_primary_before`.

Existing columns (`niche_primary`, `niches_all`, `sphere_primary`, `spheres_all`, etc.) are overwritten with the post-crawl values.

Also: while we have the page HTML, re-extract emails and phones with `crawl_website.py`-style regexes. The regexes run over the **cleaned** `title + meta + body` text (after `get_text` stripping of scripts/styles/etc.), not the raw HTML, to avoid false positives from analytics payloads and inline JS. Extracted emails are lowercased, junk-filtered (e.g. `@example.com`, `@w3.org`, `@sentry.io`, `@schema.org`, `@cloudflare.com`, `@google.com`, `@jquery.com`, `@wordpress.org`, `@fb.com`, `@sentry-next.io`), and addresses ending in image extensions (`.png`, `.jpg`, `.gif`, `.svg`, `.webp`) are dropped. The survivors are normalized via `norm_emails` / `norm_phones` from `clean_segment_prospects.py` and merged into the existing `emails` / `phones` columns (union, order-preserving dedup).

## Report

Write `tmp/prospects_enriched_report.json` with:
- `total_prospects`
- `crawled_successfully`
- `crawl_failed`
- `niche_primary_counts` — post-enrichment
- `niche_primary_before_counts` — pre-enrichment (from input csv)
- `reclassified_count` — number of rows whose primary niche changed
- `still_other_count` — `other_crawled` + `other_uncrawled`
- `still_other_samples` — up to 30 domain + title samples from `other_crawled` for manual inspection

## Run

```bash
python executions/enrich_and_reclassify_prospects.py
```

Flags:
- `--input PATH` — default `tmp/prospects_clean.csv`
- `--output PATH` — default `tmp/prospects_enriched.csv`
- `--cache PATH` — default `tmp/prospects_enriched_raw.jsonl`
- `--report PATH` — default `tmp/prospects_enriched_report.json`
- `--workers N` — default 10
- `--timeout N` — per-request timeout seconds, default 10
- `--refresh` — ignore cache and re-crawl everything

## Changelog

- 2026-04-19 — initial version.
- 2026-04-19 — post script-reviewer hardening: documented encoding fallback (`apparent_encoding` when server declares `ISO-8859-1` / no charset), the defensive `normalize_domain` helper, preservation of pre-existing niche for blocklisted / no-domain rows, phone/email regexes now running on cleaned text (not raw HTML) with junk filtering, cache reload after the executor block, and split the blocklist into exact-match vs suffix-match sets to match the script.
