# Resize Business Photos SOP — ZaDeteto Card Image Optimization

## Objective
Bulk-downsize every card photo and (optionally) every business logo stored in the Supabase `business-photos` Storage bucket so cards on `search.html` paint quickly on mobile. Source assets are routinely 1000–2000 px wide JPGs (~250–500 KB each) being displayed at ~300×200 CSS px. The script produces WebP copies sized for the actual display slot, uploads them alongside the originals (originals stay as backup), and updates each business row's `gallery_urls[0]` (and `logo`, when applicable) to point at the new files.

This is a one-shot job per content batch — re-run when new photos are uploaded, or wire the same resize logic into the upload pipeline.

## Required Inputs
- `.env` with `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (the secret key is needed because we write to Storage and the `businesses` table)
- Python dependencies (Step 0)
- Network access to Supabase

## Outputs
- New Storage objects: `business-photos/<slug>/hero.webp` and (when logos are processed) `business-logos/<slug>/logo.webp`
- Updated DB rows: `gallery_urls[0]` swapped to the WebP URL; `logo` swapped when applicable
- Untouched: every original `hero.jpg` (or other extension) — preserved as backup
- Run report: `tmp/resize_business_photos_<timestamp>.json` listing every action (downloaded, resized, uploaded, db-updated, skipped, failed) with reasons

---

## Step 0 — First-Time Setup

### Install Python dependencies

```bash
pip install pillow requests supabase python-dotenv
```

### Verify env vars

```bash
python -c "import os, dotenv; dotenv.load_dotenv(); print(bool(os.getenv('SUPABASE_URL')), bool(os.getenv('SUPABASE_SECRET_KEY')))"
```

Both should print `True True`.

---

## Step 1 — Dry-Run a Single Slug

Always start here. Picks one business, downloads its photo, resizes locally, prints stats, but does **not** upload or write to the DB.

```bash
python executions/resize_business_photos.py --slug sz-psiholog-014 --dry-run
```

Expected output:
- Original: `<width>x<height>`, `<size> KB`
- Resized: `<width>x<height>`, `<size> KB`, format `WebP`
- Action that would be taken: upload + DB update (no actual change)

If the resized file looks reasonable (≤80 KB for hero, ≤25 KB for logo), proceed to Step 2.

---

## Step 2 — Live Run on a Single Slug

Same flag, drop `--dry-run`:

```bash
python executions/resize_business_photos.py --slug sz-psiholog-014
```

This:
1. Downloads the original.
2. Resizes to max 800 px wide for hero (256 px for logo), re-encodes as WebP q=75.
3. Uploads to `business-photos/<slug>/hero.webp`.
4. Updates the row's `gallery_urls[0]` to the new public URL.

Verify:
- Open `https://zadeteto.com/search.html`, find the card for that slug, confirm the photo still renders.
- Check Supabase Studio → Storage → `business-photos/<slug>/` shows both the original and the new `.webp`.

---

## Step 3 — Bulk Run

```bash
python executions/resize_business_photos.py --all
```

Flags:
- `--all` — process every business row (combine with `--published-only` to restrict)
- `--slug <slug>` — process a single business (mutually exclusive with `--all`; one is required)
- `--logos` — also resize logos (default is hero photos only)
- `--published-only` — when used with `--all`, only process rows where `published = true`
- `--limit N` — cap to N businesses. Pagination caps the LAST page's size so the script never over-fetches by up to `PAGE_SIZE - 1` rows (e.g. `--limit 50` requests exactly 50, not a full 1000-row page).
- `--no-skip-existing` — re-process rows whose URL already points at `.webp` (default behavior is to skip them)
- `--max-width-hero` — override the 800 px hero cap
- `--max-width-logo` — override the 256 px logo cap
- `--quality` — WebP quality 1–100 (default 75); values outside this range exit with an error
- `--dry-run` — measure only; no uploads, no DB writes
- `--report-dir <dir>` — where to write the JSON run report (default: `tmp/`)

The script logs progress every 25 rows and prints failures to stderr as they occur. Estimated runtime: ~2–5 seconds per row depending on network. For ~1400 rows expect 30–90 minutes.

---

## Step 4 — Verify

```bash
# Spot-check: open one search page and watch the Network tab in DevTools.
# Card photos should now be ~25–60 KB each instead of 200–500 KB.
```

Or query Supabase directly:

```sql
select count(*) from businesses where gallery_urls[1] ilike '%.webp';
-- Should be roughly equal to the row count after a successful --all run.
```

---

## Step 5 — Rollback (if needed)

Originals are preserved. To revert a single business:

```bash
python executions/resize_business_photos.py --slug <slug> --rollback
# Add --logos to also roll back the logo column.
# Add --dry-run to preview the planned restore URL without writing the DB.
```

This re-points `gallery_urls[0]` (and `logo`, with `--logos`) back to the original file by listing the bucket folder and picking the surviving non-`.webp` sibling. The `.webp` file stays in Storage but is no longer referenced.

Rollback statuses:
- `rolled-back` — DB pointed back at the original.
- `dry-run` — `would_restore_to` URL recorded, no DB write.
- `skipped` — current URL is not a `.webp` under our bucket; nothing to roll back.
- `failed` with reason `unknown-original` — no non-`.webp` sibling was found in the folder.
- `ambiguous-original` — multiple non-`.webp` siblings exist AND at least one is missing `metadata.size`. The script refuses to guess; the response includes a `candidates` list and the user must pick manually. When all sizes are known, the largest non-`.webp` sibling is restored.

`--rollback` requires `--slug`. Running it without one exits with an error.

---

## Behavior Rules

- **Never overwrite originals.** Always upload as a new filename (`hero.webp`, `logo.webp`).
- **Never touch external URLs.** If `logo` or `gallery_urls[0]` is not under `<SUPABASE_URL>/storage/v1/object/public/business-photos/`, skip the row and log the skip.
- **Never touch `placehold.co` URLs.** Same as above.
- **Never run without `.env`.** Refuse to start if `SUPABASE_SECRET_KEY` is missing.
- **Idempotent.** Re-running with `--all` is safe; `--skip-existing` makes it cheap.
- **Atomic per row.** If upload succeeds but DB update fails, retry the DB update twice (3 attempts total, 0.5 s then 1.5 s backoff); if still failing, log the failure note in the per-row report and continue (the orphan WebP can be cleaned up later, or picked up next run).
- **Download retry.** Image downloads retry once on transient failure (1 s pause) before being marked `failed` with reason `download failed`.

## Tuning Notes

- **800 px hero / 256 px logo** is sized for retina (2× the ~400 px / ~128 px CSS display slots). If the cards are ever redesigned to be larger, raise the caps and re-run.
- **WebP q=75** is a good speed/quality compromise. q=80 if you see banding on photos with smooth gradients.
- The script does **not** strip EXIF — Pillow does that for us by default when re-encoding. No PII concern from photos uploaded by businesses.

## Changelog

- 2026-05-01 — Initial draft. Bulk WebP resize for card photos and (optional) logos. Originals preserved.
- 2026-05-01 — Documented `--limit` pagination correctness (caps last page so we never over-fetch by up to `PAGE_SIZE - 1` rows), DB update retry policy (3 attempts, 0.5 s / 1.5 s backoff), `--rollback` honoring `--dry-run`, and the new `ambiguous-original` rollback status when multiple non-`.webp` siblings exist with missing `metadata.size`. Corrected logo bucket name (`business-logos`), replaced non-existent `--skip-existing` flag with the real `--no-skip-existing`, added missing `--published-only`, `--dry-run`, `--report-dir`, and `--slug` flag entries.
