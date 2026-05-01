"""
Bulk-resize business card photos and logos already in Supabase Storage.

Card photos are routinely 1000-2000 px wide JPGs (~250-500 KB) being displayed
at ~300x200 CSS px, which dominates LCP on mobile. This script downloads each
referenced image, downscales + re-encodes as WebP, uploads as a NEW filename
alongside the original (originals preserved as backup), and updates the DB row
to point at the new file.

Buckets and DB columns handled:
  - `business-photos/<slug>/hero.<ext>`  ->  `business-photos/<slug>/hero.webp`
        DB column: businesses.gallery_urls[0]
  - `business-logos/<slug>/logo.<ext>`   ->  `business-logos/<slug>/logo.webp`
        DB column: businesses.logo            (only when --logos is passed)

Behavior:
  - Default DRY-RUN. Prints what would happen and writes a per-row JSON report
    to tmp/resize_business_photos_<timestamp>.json. Touches nothing remote.
  - Originals are NEVER overwritten. New files use a `.webp` extension so the
    original `hero.jpg` (or `logo.png`, etc.) stays as a backup.
  - External URLs (anything not under <SUPABASE_URL>/storage/v1/object/public/)
    are skipped with reason logged. Same for placehold.co fallbacks.
  - --skip-existing (default ON) skips rows whose gallery_urls[0] / logo already
    points at a `.webp` file under our buckets.
  - --rollback re-points the DB column back at the original filename. The .webp
    file stays in Storage but is unreferenced.

Usage:
    # Dry-run a single slug to eyeball one resize
    python executions/resize_business_photos.py --slug sz-psiholog-014 --dry-run

    # Live run, single slug
    python executions/resize_business_photos.py --slug sz-psiholog-014

    # Bulk: hero photos only
    python executions/resize_business_photos.py --all

    # Bulk: hero + logos
    python executions/resize_business_photos.py --all --logos

    # Limit scope for staged rollout
    python executions/resize_business_photos.py --all --limit 50

    # Roll back one slug (re-point DB at originals)
    python executions/resize_business_photos.py --slug sz-psiholog-014 --rollback
"""

import argparse
import datetime as _dt
import io
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install pillow", file=sys.stderr)
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase python-dotenv", file=sys.stderr)
    sys.exit(1)


HERO_BUCKET = "business-photos"
LOGO_BUCKET = "business-logos"
PUBLIC_URL_FRAGMENT = "/storage/v1/object/public/"
DEFAULT_HERO_MAX_WIDTH = 800   # 2x the ~400 px CSS display slot for retina
DEFAULT_LOGO_MAX_WIDTH = 256   # 2x the ~128 px CSS display slot
DEFAULT_QUALITY = 75
DOWNLOAD_TIMEOUT = (5, 30)
PAGE_SIZE = 1000  # PostgREST default cap; the script paginates


def _load_client() -> tuple["Client", str]:
    load_dotenv()
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY must both be set in .env", file=sys.stderr)
        sys.exit(1)
    return create_client(url, key), url


def _is_our_storage_url(url: str, supabase_url: str, bucket: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    expected_prefix = f"{supabase_url.rstrip('/')}{PUBLIC_URL_FRAGMENT}{bucket}/"
    return url.startswith(expected_prefix)


def _parse_object_key(url: str, supabase_url: str, bucket: str) -> str | None:
    """Return the object key inside `bucket` for a public storage URL, or None
    if the URL does not belong to that bucket. The key is URL-decoded so it can
    be passed straight to storage.from_(bucket).download(key)."""
    if not _is_our_storage_url(url, supabase_url, bucket):
        return None
    prefix = f"{supabase_url.rstrip('/')}{PUBLIC_URL_FRAGMENT}{bucket}/"
    raw = url[len(prefix):]
    raw = raw.split("?", 1)[0].split("#", 1)[0]
    return unquote(raw) or None


def _download_bytes(url: str) -> bytes | None:
    """Public bucket files are simplest to fetch via plain HTTP — no auth
    needed and no SDK quirks. Returns None on any failure (status, timeout,
    redirect loop, etc.). One retry on transient failures since CDN edges
    occasionally 5xx."""
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
            if r.status_code == 200:
                return r.content
        except requests.RequestException:
            pass
        if attempt == 0:
            time.sleep(1.0)
    return None


def _resize_to_webp(src_bytes: bytes, max_width: int, quality: int) -> tuple[bytes, tuple[int, int], tuple[int, int]] | None:
    """Resize image to <= max_width and re-encode as WebP. Returns
    (out_bytes, (orig_w, orig_h), (new_w, new_h)) or None if the input cannot
    be decoded (e.g. SVG, corrupt JPEG)."""
    try:
        im = Image.open(io.BytesIO(src_bytes))
        im.load()
    except Exception:
        return None
    orig_size = im.size
    # Convert P/LA/RGBA modes to a flat RGB if there's no real alpha channel
    # (most card photos are opaque JPGs). Preserves alpha for true PNG/WebP
    # logos that depend on it.
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if not has_alpha and im.mode != "RGB":
        im = im.convert("RGB")
    elif has_alpha and im.mode != "RGBA":
        im = im.convert("RGBA")

    w, h = im.size
    if w > max_width:
        scale = max_width / float(w)
        new_size = (max_width, max(1, int(round(h * scale))))
        im = im.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    save_kwargs = {"format": "WEBP", "quality": quality, "method": 6}
    im.save(buf, **save_kwargs)
    return buf.getvalue(), orig_size, im.size


def _upload_webp(client: "Client", bucket: str, key: str, data: bytes) -> tuple[bool, str]:
    """Upload with upsert so re-runs overwrite stale .webp from a prior partial
    run. Returns (ok, note)."""
    try:
        client.storage.from_(bucket).upload(
            path=key,
            file=data,
            file_options={"upsert": "true", "content-type": "image/webp"},
        )
        return True, f"{len(data)} bytes"
    except Exception as e:
        return False, f"upload error: {e}"


def _public_url(client: "Client", bucket: str, key: str) -> str:
    url = client.storage.from_(bucket).get_public_url(key)
    if isinstance(url, str):
        return url.split("?", 1)[0]
    return ""


def _fetch_rows(client: "Client", slug: str | None, only_published: bool, limit: int | None) -> list[dict]:
    cols = "id,slug,gallery_urls,logo,published"
    if slug:
        res = client.table("businesses").select(cols).eq("slug", slug).execute()
        return res.data or []

    rows: list[dict] = []
    start = 0
    while True:
        # When --limit is set, cap the page size of the LAST page so we never
        # over-fetch by up to PAGE_SIZE-1 rows. Without this, --limit 50 still
        # pulled a full 1000-row page.
        page_cap = PAGE_SIZE
        if limit:
            page_cap = min(PAGE_SIZE, limit - len(rows))
            if page_cap <= 0:
                break
        end = start + page_cap - 1
        q = client.table("businesses").select(cols).order("id").range(start, end)
        if only_published:
            q = q.eq("published", True)
        page = q.execute().data or []
        rows.extend(page)
        if len(page) < page_cap:
            break
        if limit and len(rows) >= limit:
            break
        start = end + 1
    return rows[:limit] if limit else rows


def _retry_db_update(client: "Client", row_id, payload: dict) -> tuple[bool, str]:
    """Per the directive: retry the DB update twice on transient failure
    (3 attempts total, short backoff) before giving up. Storage already has
    the new file at this point — leaving the row unupdated is recoverable
    via re-run, but worth retrying here to avoid orphan-WebPs piling up."""
    last_err = ""
    for attempt in range(3):
        try:
            client.table("businesses").update(payload).eq("id", row_id).execute()
            return True, "ok"
        except Exception as e:
            last_err = str(e)
            if attempt < 2:
                time.sleep(0.5 if attempt == 0 else 1.5)
    return False, f"failed after 3 attempts: {last_err}"


def _swap_gallery_first(gallery_urls, new_url: str) -> list:
    """Return a new gallery_urls list with index 0 replaced. Handles the case
    where the column is None or non-list defensively."""
    if not isinstance(gallery_urls, list):
        return [new_url]
    out = list(gallery_urls)
    if out:
        out[0] = new_url
    else:
        out = [new_url]
    return out


def _process_row(
    client: "Client",
    supabase_url: str,
    row: dict,
    do_logos: bool,
    hero_max: int,
    logo_max: int,
    quality: int,
    skip_existing: bool,
    dry_run: bool,
) -> dict:
    out = {"id": row.get("id"), "slug": row.get("slug"), "actions": []}

    # ─── Hero ───
    gallery = row.get("gallery_urls") or []
    hero_url = gallery[0] if isinstance(gallery, list) and gallery else ""
    hero_key = _parse_object_key(hero_url, supabase_url, HERO_BUCKET)
    if not hero_key:
        if hero_url:
            out["actions"].append({"target": "hero", "status": "skipped", "reason": "external or non-bucket URL"})
        else:
            out["actions"].append({"target": "hero", "status": "skipped", "reason": "no gallery photo"})
    elif skip_existing and hero_key.lower().endswith(".webp"):
        out["actions"].append({"target": "hero", "status": "skipped", "reason": "already webp"})
    else:
        new_key = _derive_webp_key(hero_key, "hero")
        result = _resize_one(
            client, supabase_url, hero_url, HERO_BUCKET, new_key,
            hero_max, quality, dry_run,
        )
        if result["status"] == "uploaded" and not dry_run:
            new_url = _public_url(client, HERO_BUCKET, new_key)
            new_gallery = _swap_gallery_first(gallery, new_url)
            ok, note = _retry_db_update(client, row["id"], {"gallery_urls": new_gallery})
            result["db_update"] = note
            if ok:
                result["new_url"] = new_url
        result["target"] = "hero"
        out["actions"].append(result)

    # ─── Logo (optional) ───
    if do_logos:
        logo_url = row.get("logo") or ""
        logo_key = _parse_object_key(logo_url, supabase_url, LOGO_BUCKET)
        if not logo_key:
            if logo_url and "placehold.co" in logo_url:
                reason = "placehold.co fallback"
            elif logo_url:
                reason = "external or non-bucket URL"
            else:
                reason = "no logo"
            out["actions"].append({"target": "logo", "status": "skipped", "reason": reason})
        elif skip_existing and logo_key.lower().endswith(".webp"):
            out["actions"].append({"target": "logo", "status": "skipped", "reason": "already webp"})
        else:
            new_key = _derive_webp_key(logo_key, "logo")
            result = _resize_one(
                client, supabase_url, logo_url, LOGO_BUCKET, new_key,
                logo_max, quality, dry_run,
            )
            if result["status"] == "uploaded" and not dry_run:
                new_url = _public_url(client, LOGO_BUCKET, new_key)
                ok, note = _retry_db_update(client, row["id"], {"logo": new_url})
                result["db_update"] = note
                if ok:
                    result["new_url"] = new_url
            result["target"] = "logo"
            out["actions"].append(result)

    return out


def _derive_webp_key(orig_key: str, default_stem: str) -> str:
    """Replace the file's extension with .webp. Falls back to <slug>/<stem>.webp
    if the original key has no recognisable extension (rare, but handle it)."""
    folder = os.path.dirname(orig_key)
    base = os.path.basename(orig_key)
    stem, ext = os.path.splitext(base)
    if not stem:
        stem = default_stem
    new_base = f"{stem}.webp"
    return f"{folder}/{new_base}" if folder else new_base


def _resize_one(
    client: "Client",
    supabase_url: str,
    src_url: str,
    bucket: str,
    new_key: str,
    max_width: int,
    quality: int,
    dry_run: bool,
) -> dict:
    raw = _download_bytes(src_url)
    if raw is None:
        return {"status": "failed", "reason": "download failed", "src_url": src_url}
    orig_bytes = len(raw)
    out = _resize_to_webp(raw, max_width, quality)
    if out is None:
        return {"status": "failed", "reason": "decode failed", "src_url": src_url, "orig_bytes": orig_bytes}
    new_bytes_data, orig_size, new_size = out
    new_bytes = len(new_bytes_data)
    info = {
        "src_url": src_url,
        "new_key": new_key,
        "orig_bytes": orig_bytes,
        "new_bytes": new_bytes,
        "orig_size": list(orig_size),
        "new_size": list(new_size),
        "savings_pct": round(100.0 * (orig_bytes - new_bytes) / orig_bytes, 1) if orig_bytes else 0.0,
    }
    if dry_run:
        info["status"] = "dry-run"
        return info
    ok, note = _upload_webp(client, bucket, new_key, new_bytes_data)
    info["status"] = "uploaded" if ok else "failed"
    if not ok:
        info["reason"] = note
    return info


def _rollback(client: "Client", supabase_url: str, slug: str, do_logos: bool, dry_run: bool) -> dict:
    """Re-point gallery_urls[0] / logo back at the original (non-webp) file by
    listing the bucket folder and picking the surviving non-.webp sibling.
    Refuses to auto-pick when the choice is ambiguous (multiple non-webp
    siblings AND any candidate is missing metadata.size) — the user must
    resolve manually rather than have the script guess wrong. Honors
    --dry-run by recording the planned URL without writing the DB."""
    res = client.table("businesses").select("id,slug,gallery_urls,logo").eq("slug", slug).execute()
    rows = res.data or []
    if not rows:
        return {"slug": slug, "status": "not-found"}
    row = rows[0]
    out = {"slug": slug, "id": row["id"], "actions": []}

    def _restore(bucket: str, current_url: str, kind: str):
        key = _parse_object_key(current_url, supabase_url, bucket)
        if not key or not key.lower().endswith(".webp"):
            return {"target": kind, "status": "skipped", "reason": "not pointing at webp in our bucket"}
        folder = os.path.dirname(key)
        stem = os.path.splitext(os.path.basename(key))[0]
        try:
            entries = client.storage.from_(bucket).list(folder)
        except Exception as e:
            return {"target": kind, "status": "failed", "reason": f"list error: {e}"}
        candidates = [
            e for e in (entries or [])
            if isinstance(e, dict)
            and e.get("name", "").startswith(stem + ".")
            and not e["name"].lower().endswith(".webp")
        ]
        if not candidates:
            return {"target": kind, "status": "failed", "reason": "unknown-original (no non-webp backup found)"}
        # Refuse to guess when ambiguous: multiple candidates AND we lack a
        # reliable size to break the tie.
        if len(candidates) > 1:
            sizes_known = all(isinstance(c.get("metadata", {}).get("size"), int) for c in candidates)
            if not sizes_known:
                return {
                    "target": kind,
                    "status": "ambiguous-original",
                    "reason": "multiple non-webp siblings with missing metadata.size",
                    "candidates": [c["name"] for c in candidates],
                }
        # Prefer the one with biggest size (the genuine original) if multiple
        candidates.sort(key=lambda e: -(e.get("metadata", {}).get("size") or 0))
        orig_name = candidates[0]["name"]
        orig_key = f"{folder}/{orig_name}" if folder else orig_name
        orig_url = _public_url(client, bucket, orig_key)
        if dry_run:
            return {"target": kind, "status": "dry-run", "would_restore_to": orig_url}
        if kind == "hero":
            new_gallery = _swap_gallery_first(row.get("gallery_urls"), orig_url)
            ok, note = _retry_db_update(client, row["id"], {"gallery_urls": new_gallery})
        else:
            ok, note = _retry_db_update(client, row["id"], {"logo": orig_url})
        if not ok:
            return {"target": kind, "status": "failed", "reason": note}
        return {"target": kind, "status": "rolled-back", "to": orig_url}

    gallery = row.get("gallery_urls") or []
    if isinstance(gallery, list) and gallery:
        out["actions"].append(_restore(HERO_BUCKET, gallery[0], "hero"))
    if do_logos and row.get("logo"):
        out["actions"].append(_restore(LOGO_BUCKET, row["logo"], "logo"))
    return out


def _summarize(records: list[dict]) -> dict:
    counts = {"uploaded": 0, "dry-run": 0, "skipped": 0, "failed": 0}
    bytes_before = 0
    bytes_after = 0
    for rec in records:
        for action in rec.get("actions", []):
            status = action.get("status", "skipped")
            counts[status] = counts.get(status, 0) + 1
            if status in ("uploaded", "dry-run"):
                bytes_before += action.get("orig_bytes", 0) or 0
                bytes_after += action.get("new_bytes", 0) or 0
    return {
        "counts": counts,
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "savings_kb": round((bytes_before - bytes_after) / 1024.0, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-resize business card photos and (optionally) logos in Supabase Storage.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--slug", help="Process a single business by slug.")
    target.add_argument("--all", action="store_true", help="Process every business row.")

    parser.add_argument("--logos", action="store_true", help="Also resize logos (default: hero photos only).")
    parser.add_argument("--published-only", action="store_true", help="Only process rows where published = true.")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of rows processed in --all mode.")
    parser.add_argument("--max-width-hero", type=int, default=DEFAULT_HERO_MAX_WIDTH)
    parser.add_argument("--max-width-logo", type=int, default=DEFAULT_LOGO_MAX_WIDTH)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY, help="WebP quality 0-100 (default 75).")
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-resize rows whose URL already points at .webp (default skips them).")
    parser.add_argument("--dry-run", action="store_true", help="Don't upload or write to DB; just measure.")
    parser.add_argument("--rollback", action="store_true", help="Re-point DB column back at the original (non-webp) file. Requires --slug.")
    parser.add_argument("--report-dir", default="tmp", help="Where to write the JSON run report (default: tmp/).")
    args = parser.parse_args()

    if args.rollback and not args.slug:
        print("ERROR: --rollback requires --slug.", file=sys.stderr)
        sys.exit(1)
    if args.quality < 1 or args.quality > 100:
        print("ERROR: --quality must be 1-100.", file=sys.stderr)
        sys.exit(1)

    client, supabase_url = _load_client()

    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report_dir) / f"resize_business_photos_{ts}.json"

    # Rollback path is short-circuited — no resize loop needed.
    if args.rollback:
        result = _rollback(client, supabase_url, args.slug, args.logos, args.dry_run)
        report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nReport: {report_path}")
        if args.dry_run:
            print("\n*** DRY RUN — no DB changes. ***")
        return

    rows = _fetch_rows(client, args.slug, args.published_only, args.limit)
    if not rows:
        print("No matching businesses found.")
        sys.exit(0)
    print(f"Processing {len(rows)} businesses ({'DRY RUN' if args.dry_run else 'LIVE'}).")

    records: list[dict] = []
    t0 = time.time()
    for i, row in enumerate(rows, start=1):
        rec = _process_row(
            client, supabase_url, row,
            do_logos=args.logos,
            hero_max=args.max_width_hero,
            logo_max=args.max_width_logo,
            quality=args.quality,
            skip_existing=not args.no_skip_existing,
            dry_run=args.dry_run,
        )
        records.append(rec)
        # Surface failures immediately rather than burying them in the JSON
        # report at the end — a 90-minute run with silent download failures is
        # painful to debug.
        for action in rec.get("actions", []):
            if action.get("status") == "failed":
                reason = action.get("reason", "unknown")
                print(f"  FAIL {rec.get('slug')} {action.get('target')}: {reason}", file=sys.stderr)
        if i % 25 == 0 or i == len(rows):
            elapsed = time.time() - t0
            print(f"  [{i}/{len(rows)}] {rec.get('slug')} — {elapsed:.1f}s elapsed")

    summary = _summarize(records)
    full_report = {
        "ts": ts,
        "args": {k: v for k, v in vars(args).items() if k not in ("report_dir",)},
        "summary": summary,
        "records": records,
    }
    report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("=== Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"\nReport: {report_path}")
    if args.dry_run:
        print("\n*** DRY RUN — no uploads, no DB changes. ***")


if __name__ == "__main__":
    main()
