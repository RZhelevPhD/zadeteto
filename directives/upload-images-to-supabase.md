# Upload Images to Supabase SOP — Phase 4 of the Lead Pipeline

## Objective
Upload every logo + hero image listed in `tmp/image_manifest.csv` to Supabase Storage. Create the two required buckets (`business-logos`, `business-photos`) as public-read if they do not already exist. Write the resulting public URLs back into the manifest as `logo_public_url` / `hero_public_url` so Phase 5 (`businesses` table import) can reference them.

## Execution Script
`executions/upload_images_to_supabase.py`

## Prerequisites
- `.env` contains both `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. The publishable key cannot create buckets or bypass RLS; the secret key (`sb_secret_...`) is required for this server-side job.
- Python deps installed: `pip install supabase python-dotenv`.
- Optional: `pip install pillow` to enable the auto-resize step. If Pillow is missing, the script still runs — it just prints a one-line `WARN: Pillow not installed — auto-resize disabled` to stderr and uploads originals verbatim.
- The manifest at `tmp/image_manifest.csv` has been reconciled via `reconcile_curation.py` (so no paths point at deleted files).

## How It Works
1. Loads `SUPABASE_URL` + `SUPABASE_SECRET_KEY` from `.env` via `python-dotenv`. Exits with a clear error if either is missing.
2. Instantiates a `supabase.Client`.
3. For each bucket (`business-logos`, `business-photos`):
   - Calls `client.storage.list_buckets()` to see if it exists.
   - Creates it with `public=True` if missing. Tolerates concurrent-create races.
4. Reads the manifest (utf-8-sig, `dtype=str, keep_default_na=False`).
5. For every row that has a non-empty `logo_local_path` or `hero_local_path`:
   - Prepares an upload payload from the local file. With auto-resize ON (default), if the file is a resizable raster (`.png .jpg .jpeg .bmp .tiff .tif .webp .gif`) and is either larger than 100 KB on disk OR wider than the configured cap (`--hero-max-width`, default 800; `--logo-max-width`, default 256), Pillow decodes it in memory, downscales to the cap with LANCZOS, and re-encodes to WebP at `--resize-quality` (default 75, method=6). The remote filename's extension is rewritten to `.webp` and the content-type is set to `image/webp`. SVG, ICO, AVIF and any unknown extension pass through verbatim. If the resized WebP comes out *no smaller* than the original, the script falls back to uploading the original bytes with the original extension. The local file on disk is never modified.
   - Builds the remote key `<legacy_id>/<basename-or-stem.webp>` (e.g. `sz-psiholog-001/logo.png` or `sz-psiholog-001/logo.webp` when resize fired).
   - Calls `storage.from_(bucket).list(<legacy_id>)` to check if the object already exists and compares byte length against the upload payload (post-resize, not the on-disk file).
     - Same size → skips (`skipped`).
     - Missing or different size → uploads with `upsert=true` and the correct `content-type` header.
   - Fetches the public URL via `get_public_url()`.
6. Writes `logo_public_url` / `hero_public_url` back into the manifest and rewrites it atomically.
7. Prints a summary: uploaded, skipped (already-uploaded same size), dry-run, failed. The per-row note format is `{kind}:{action}:{prep_note}:{detail}` (e.g. `hero:uploaded:resized:48213 bytes`); the stats counter is anchored to `parts[1]` after splitting on `:`, so a stray `uploaded` substring in an error message or filename can never miscount.

## CLI Flags

| Flag | Required | Default | Purpose |
|------|----------|---------|---------|
| `--manifest` | Yes | — | Image manifest CSV (read + rewritten with new URL columns) |
| `--logo-bucket` | No | `business-logos` | Bucket for logo uploads |
| `--hero-bucket` | No | `business-photos` | Bucket for hero uploads |
| `--skip-bucket-create` | No | off | Assume buckets exist; skip the list/create calls. Use if you pre-created buckets manually. |
| `--dry-run` | No | off | Print what would be uploaded; touch no remote state; do not rewrite the manifest. |
| `--no-auto-resize` | No | off | Disable the WebP resize step and upload originals verbatim. |
| `--hero-max-width` | No | `800` | Max hero width (px) before resize. Targets 2x a ~400 px display slot for retina. |
| `--logo-max-width` | No | `256` | Max logo width (px) before resize. Targets 2x a ~128 px display slot. |
| `--resize-quality` | No | `75` | WebP quality 1–100. Validated; out-of-range exits 1. |

## Usage

Dry run (safe, no network writes):
```bash
python executions/upload_images_to_supabase.py --manifest tmp/image_manifest.csv --dry-run
```

Real run:
```bash
python executions/upload_images_to_supabase.py --manifest tmp/image_manifest.csv
```

Buckets already exist (pre-created in Dashboard):
```bash
python executions/upload_images_to_supabase.py --manifest tmp/image_manifest.csv --skip-bucket-create
```

## Idempotency
Re-running the script is cheap: it lists each bucket folder and skips any object whose remote byte length matches the **upload payload** (post-resize, not the raw on-disk file). File replacements (you edited a logo locally) are detected via the size mismatch and re-uploaded with `upsert=true`. Public URLs are re-computed and re-written regardless, so a corrupted `logo_public_url` column is self-healing on the next run.

Because the size compare is against the post-resize payload, **changing `--resize-quality`, `--hero-max-width`, `--logo-max-width`, or toggling `--no-auto-resize` invalidates the cache**: the byte length of the new payload won't match the previous remote object, and every affected row will be re-uploaded.

## Content-Type Mapping
When the resize step fires, the content-type is forced to `image/webp` regardless of the source extension. Otherwise the type is inferred from the local file extension: `.png` → `image/png`, `.jpg/.jpeg` → `image/jpeg`, `.webp` → `image/webp`, `.svg` → `image/svg+xml`, `.gif` → `image/gif`, `.ico` → `image/x-icon`, `.avif` → `image/avif`. Unknown extensions default to `application/octet-stream`.

## Bucket Policies
Both buckets are created `public=True`. Read access is unrestricted so the frontend can render `<img src={logo_public_url}>` directly. Write access is still gated by service-role key — end-users cannot upload to these buckets via the anon key.

## Failure Modes
- Missing service-role key → exits code 1 with a pointer to the Dashboard.
- Local file gone between manifest reconcile and upload → row logged as `failed: local file missing`; manifest URL columns stay empty for that row.
- Supabase rate limit or network hiccup → row logged as `failed: upload error: ...`; re-run later to retry (skipped rows skip the retry path since they already succeeded once).

## Constraints
- Single-writer script. Do not run two copies in parallel against the same manifest (pandas would race on the rewrite).
- `list_buckets()` and `list()` are called per bucket per run; the current implementation is not optimized for manifests above a few thousand rows (would need pagination + batched listing).
- The script does NOT delete bucket contents for `legacy_id`s that have since been removed from the manifest. That cleanup is a separate step (not shipped).
- Successive runs with different resize settings can leave **both** the original-extension object (e.g. `<legacy_id>/logo.png`) and a resized WebP (`<legacy_id>/logo.webp`) sitting in the bucket. The manifest only tracks the latest URL, so the older sibling is orphaned but not deleted. Same applies if a resize run is followed by a `--no-auto-resize` run, or if the WebP-isn't-smaller fallback fires for one image but not the next. Bucket cleanup is manual.

## Changelog
- 2026-04-20: Initial script + directive. Handles bucket creation + idempotent upload + public-URL capture in one pass.
- 2026-05-01: Documented the new auto-resize step (default ON, Pillow-backed, downscales >100 KB or over-cap rasters to in-memory WebP, originals on disk untouched) and its four new flags (`--no-auto-resize`, `--hero-max-width` 800, `--logo-max-width` 256, `--resize-quality` 75). Pillow noted as an optional dependency with graceful warn-and-skip degradation. Content-type now forced to `image/webp` when resize fires. Idempotency clarified: byte-length compare runs against the post-resize upload payload, so changing any resize setting invalidates the cache and triggers re-upload. Added an edge-case note that the WebP-not-smaller fallback plus successive runs with mixed settings can leave both `<stem>.png` and `<stem>.webp` orphaned in the bucket. Stats counter is now field-position-anchored on `parts[1]` of the colon-split note (no more substring miscounts). Removed reference to the deleted `_upload` helper; uploads now go through `_prepare_payload` + `_upload_bytes`.
