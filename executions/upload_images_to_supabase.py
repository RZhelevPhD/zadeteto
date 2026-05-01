"""
Upload the logo + hero images listed in `tmp/image_manifest.csv` to Supabase
Storage. Creates the two required buckets (`business-logos`, `business-photos`)
if they don't already exist. Writes the resulting public URLs back into the
manifest as `logo_public_url` / `hero_public_url`.

Auto-resize (default ON, requires Pillow):
    Before upload, every raster image larger than 100 KB or wider than the
    configured cap is downscaled and re-encoded as WebP. Heroes target 800 px
    (2x a ~400 px display slot for retina), logos target 256 px. The remote
    filename's extension is rewritten to `.webp` accordingly. SVG, ICO, AVIF
    pass through verbatim. Pass --no-auto-resize to upload originals untouched.
    Originals on disk are never modified — the resize happens in memory.

Requires `SUPABASE_URL` + `SUPABASE_SECRET_KEY` in `.env`. The publishable key
cannot create buckets; the secret key (sb_secret_...) bypasses RLS and Storage
policies for this server-side job. Never commit the secret key.

Idempotent: re-runs skip files whose bucket object has the same byte length
(a stronger sha256 compare is possible but Supabase's object metadata uses
Content-Length, which is cheaper). Any mismatch triggers a re-upload.

Usage:
    python executions/upload_images_to_supabase.py \\
        --manifest tmp/image_manifest.csv

Flags:
    --dry-run             Print what would happen, touch nothing remote.
    --skip-bucket-create  Assume buckets exist (user created them manually).
    --logo-bucket NAME    Override default `business-logos`.
    --hero-bucket NAME    Override default `business-photos`.
    --no-auto-resize      Upload originals verbatim (skip the WebP resize step).
    --hero-max-width PX   Override hero resize cap (default 800).
    --logo-max-width PX   Override logo resize cap (default 256).
    --resize-quality N    WebP quality 1-100 (default 75).
"""

import argparse
import io
import os
import sys

import pandas as pd
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase python-dotenv", file=sys.stderr)
    sys.exit(1)

# Pillow is used for the auto-resize step. Older runs of this script predate
# the resize feature, so missing Pillow is non-fatal — the upload still works,
# we just skip the resize and warn once.
try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    Image = None  # type: ignore
    _HAS_PIL = False


DEFAULT_LOGO_BUCKET = "business-logos"
DEFAULT_HERO_BUCKET = "business-photos"
# Resize targets: 2x the CSS display slot to stay sharp on retina screens.
# Hero cards render at ~400 px wide, logos at ~128 px wide on the search page.
DEFAULT_HERO_MAX_WIDTH = 800
DEFAULT_LOGO_MAX_WIDTH = 256
DEFAULT_RESIZE_QUALITY = 75
# Skip the resize for tiny inputs that are already small enough — re-encoding
# them as WebP can occasionally make the file slightly bigger.
RESIZE_BYTE_THRESHOLD = 100 * 1024  # 100 KB
# Image extensions the resize step understands. SVG, ICO, AVIF are passed
# through unmodified — Pillow's WebP encoder either can't read them or the
# semantic conversion (e.g. SVG -> raster) is unwanted.
RESIZABLE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def _load_env() -> tuple[str, str]:
    load_dotenv()
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not url:
        print("ERROR: SUPABASE_URL not set in .env", file=sys.stderr)
        sys.exit(1)
    if not key:
        print(
            "ERROR: SUPABASE_SECRET_KEY not set in .env\n"
            "       Grab it from Supabase Dashboard -> Project Settings -> API Keys -> 'sb_secret_...' key.\n"
            "       Never commit or share this key.",
            file=sys.stderr,
        )
        sys.exit(1)
    return url, key


def _ensure_bucket(client: Client, name: str, dry_run: bool) -> None:
    try:
        existing = client.storage.list_buckets()
    except Exception as e:
        print(f"ERROR: list_buckets failed: {e}", file=sys.stderr)
        sys.exit(2)
    names = {getattr(b, "name", None) or (b.get("name") if isinstance(b, dict) else None) for b in existing}
    if name in names:
        print(f"  bucket '{name}': exists ✓")
        return
    if dry_run:
        print(f"  bucket '{name}': WOULD CREATE (dry-run)")
        return
    try:
        client.storage.create_bucket(name, options={"public": True})
        print(f"  bucket '{name}': CREATED (public)")
    except Exception as e:
        msg = str(e)
        if "already exists" in msg.lower() or "duplicate" in msg.lower():
            print(f"  bucket '{name}': already exists (race) ✓")
        else:
            print(f"ERROR: create_bucket({name}) failed: {e}", file=sys.stderr)
            sys.exit(2)


def _remote_size(client: Client, bucket: str, key: str) -> int | None:
    """Return the remote object's content length, or None if it doesn't exist.
    Surfaces list() errors to stderr so an auth/URL misconfig doesn't get
    silently masked as a cache miss (which would force a full re-upload of
    every file)."""
    folder = os.path.dirname(key)
    filename = os.path.basename(key)
    try:
        entries = client.storage.from_(bucket).list(folder or "")
    except Exception as e:
        print(f"  WARN: list({bucket}/{folder or '/'}) failed: {e}", file=sys.stderr)
        return None
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") == filename:
            meta = entry.get("metadata") or {}
            size = meta.get("size")
            if isinstance(size, int):
                return size
            try:
                return int(size) if size is not None else None
            except (TypeError, ValueError):
                return None
    return None


def _maybe_resize(local_path: str, max_width: int, quality: int) -> tuple[bytes, str, str] | None:
    """If local_path is a resizable image and bigger than the byte threshold or
    wider than max_width, return (resized_webp_bytes, '.webp', 'image/webp').
    Otherwise return None (caller falls back to the original file). Returns
    None on any decode failure as well — we never let a resize bug block the
    upload of a working image."""
    if not _HAS_PIL:
        return None
    ext = os.path.splitext(local_path)[1].lower()
    if ext not in RESIZABLE_EXTS:
        return None
    try:
        size_on_disk = os.path.getsize(local_path)
    except OSError:
        return None
    try:
        with open(local_path, "rb") as f:
            raw = f.read()
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        return None
    w, h = im.size
    if size_on_disk < RESIZE_BYTE_THRESHOLD and w <= max_width:
        # Already within budget; not worth re-encoding.
        return None
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if not has_alpha and im.mode != "RGB":
        im = im.convert("RGB")
    elif has_alpha and im.mode != "RGBA":
        im = im.convert("RGBA")
    if w > max_width:
        scale = max_width / float(w)
        im = im.resize((max_width, max(1, int(round(h * scale)))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=quality, method=6)
    out = buf.getvalue()
    # Don't bother if WebP isn't actually smaller (rare with very small input).
    if len(out) >= size_on_disk:
        return None
    return out, ".webp", "image/webp"


def _prepare_payload(local_path: str, max_width: int, auto_resize: bool, quality: int) -> tuple[bytes, str, str, str] | None:
    """Return (data_bytes, remote_filename, content_type, note) for upload.
    Caller composes the remote key with the legacy_id folder. Note is a short
    tag ('resized', 'as-is') used for log messages. Returns None if the local
    file is missing."""
    if not os.path.exists(local_path):
        return None
    base = os.path.basename(local_path)
    stem = os.path.splitext(base)[0]
    if auto_resize:
        rz = _maybe_resize(local_path, max_width, quality)
        if rz is not None:
            data, new_ext, ctype = rz
            return data, f"{stem}{new_ext}", ctype, "resized"
    with open(local_path, "rb") as f:
        data = f.read()
    return data, base, _guess_content_type(local_path), "as-is"


def _upload_bytes(client: Client, bucket: str, key: str, data: bytes, ctype: str, dry_run: bool) -> tuple[str, str]:
    """Upload an in-memory payload to bucket/key. Mirrors _upload's contract:
    returns (action, note) with action in {'uploaded','skipped','dry-run','failed'}.
    Idempotency: skips when the remote object's content-length matches the
    payload — same heuristic used by _upload, just adapted to bytes-in-hand."""
    local_size = len(data)
    remote_size = _remote_size(client, bucket, key)
    if remote_size is not None and remote_size == local_size:
        return "skipped", f"same size ({local_size} bytes)"
    if dry_run:
        return "dry-run", f"would {'upload' if remote_size is None else 'replace'} {local_size} bytes"
    try:
        client.storage.from_(bucket).upload(
            path=key,
            file=data,
            file_options={"upsert": "true", "content-type": ctype},
        )
        return "uploaded", f"{local_size} bytes"
    except Exception as e:
        return "failed", f"upload error: {e}"


def _guess_content_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
        ".avif": "image/avif",
    }.get(ext, "application/octet-stream")


def _public_url(client: Client, bucket: str, key: str) -> str:
    url = client.storage.from_(bucket).get_public_url(key)
    return url.rstrip("?") if isinstance(url, str) else ""


def _process_row(
    client: Client,
    row: pd.Series,
    logo_bucket: str,
    hero_bucket: str,
    dry_run: bool,
    auto_resize: bool,
    hero_max_width: int,
    logo_max_width: int,
    quality: int,
) -> dict:
    # Preserves prior URLs on non-fatal failures (network hiccups re-use last
    # good URL), but clears them when the local file is gone — a stale URL
    # pointing at a no-longer-existing business would otherwise leak into
    # the DB import.
    out = {"logo_public_url": None, "hero_public_url": None, "upload_notes": []}
    lid = str(row.get("legacy_id", "")).strip()
    if not lid:
        out["upload_notes"].append("no legacy_id; skipped")
        return out

    def _do(kind: str, local_path: str, bucket: str, max_width: int) -> tuple[str | None, str]:
        """Returns (public_url_value, log_note). public_url_value is None to
        leave the manifest column unchanged, '' to clear it, or a URL string
        to write."""
        if not local_path:
            return None, ""
        prepared = _prepare_payload(local_path, max_width, auto_resize, quality)
        if prepared is None:
            return "", f"{kind}:failed:local file missing: {local_path}"
        data, remote_filename, ctype, prep_note = prepared
        key = f"{lid}/{remote_filename}"
        action, note = _upload_bytes(client, bucket, key, data, ctype, dry_run)
        log_note = f"{kind}:{action}:{prep_note}:{note}"
        if action in ("uploaded", "skipped"):
            return _public_url(client, bucket, key), log_note
        if action == "dry-run":
            return f"(dry-run) {bucket}/{key}", log_note
        return None, log_note  # failed -> preserve prior URL

    logo_local = str(row.get("logo_local_path", "")).strip()
    if logo_local:
        url_val, note = _do("logo", logo_local, logo_bucket, logo_max_width)
        if url_val is not None:
            out["logo_public_url"] = url_val
        out["upload_notes"].append(note)

    hero_local = str(row.get("hero_local_path", "")).strip()
    if hero_local:
        url_val, note = _do("hero", hero_local, hero_bucket, hero_max_width)
        if url_val is not None:
            out["hero_public_url"] = url_val
        out["upload_notes"].append(note)

    return out


def _atomic_write(df: pd.DataFrame, path: str) -> None:
    tmp = path + ".tmp"
    try:
        df.to_csv(tmp, index=False, encoding="utf-8-sig")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload manifest images to Supabase Storage; write public URLs back to the manifest.")
    parser.add_argument("--manifest", required=True, help="Image manifest CSV (read + rewritten with new URL columns).")
    parser.add_argument("--logo-bucket", default=DEFAULT_LOGO_BUCKET)
    parser.add_argument("--hero-bucket", default=DEFAULT_HERO_BUCKET)
    parser.add_argument("--skip-bucket-create", action="store_true", help="Assume buckets already exist; skip the list/create calls.")
    parser.add_argument("--dry-run", action="store_true", help="Don't call any remote write; print would-do-what.")
    parser.add_argument("--no-auto-resize", action="store_true", help="Upload images verbatim without resizing. Default behavior is to downscale large rasters to a WebP sized for the card display slot.")
    parser.add_argument("--hero-max-width", type=int, default=DEFAULT_HERO_MAX_WIDTH, help=f"Max hero photo width before resize (default {DEFAULT_HERO_MAX_WIDTH}px).")
    parser.add_argument("--logo-max-width", type=int, default=DEFAULT_LOGO_MAX_WIDTH, help=f"Max logo width before resize (default {DEFAULT_LOGO_MAX_WIDTH}px).")
    parser.add_argument("--resize-quality", type=int, default=DEFAULT_RESIZE_QUALITY, help=f"WebP quality 1-100 used when resizing (default {DEFAULT_RESIZE_QUALITY}).")
    args = parser.parse_args()

    if args.resize_quality < 1 or args.resize_quality > 100:
        print("ERROR: --resize-quality must be 1-100.", file=sys.stderr)
        sys.exit(1)
    auto_resize = not args.no_auto_resize
    if auto_resize and not _HAS_PIL:
        print("WARN: Pillow not installed — auto-resize disabled. Install with `pip install pillow` to enable.", file=sys.stderr)
        auto_resize = False

    if not os.path.exists(args.manifest):
        print(f"ERROR: manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    url, key = _load_env()
    client = create_client(url, key)

    print("=== Ensuring buckets ===")
    if args.skip_bucket_create:
        print("  (skipped per --skip-bucket-create)")
    else:
        _ensure_bucket(client, args.logo_bucket, args.dry_run)
        _ensure_bucket(client, args.hero_bucket, args.dry_run)

    print()
    print("=== Uploading files ===")
    mdf = pd.read_csv(args.manifest, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    # Ensure URL columns exist (preserve any prior values)
    for col in ("logo_public_url", "hero_public_url"):
        if col not in mdf.columns:
            mdf[col] = ""

    stats = {"uploaded": 0, "skipped": 0, "failed": 0, "dry-run": 0}
    for i, row in mdf.iterrows():
        lid = str(row.get("legacy_id", "")).strip()
        if not lid:
            continue
        has_logo = bool(str(row.get("logo_local_path", "")).strip())
        has_hero = bool(str(row.get("hero_local_path", "")).strip())
        if not (has_logo or has_hero):
            continue
        result = _process_row(
            client, row,
            args.logo_bucket, args.hero_bucket,
            args.dry_run,
            auto_resize=auto_resize,
            hero_max_width=args.hero_max_width,
            logo_max_width=args.logo_max_width,
            quality=args.resize_quality,
        )
        # None means "leave the existing column value alone" (preserve last-known URL on transient failure).
        # Empty string means "actively clear" (local file gone -> stale URL must go).
        # Non-empty string means "write this URL".
        if result["logo_public_url"] is not None:
            mdf.at[i, "logo_public_url"] = result["logo_public_url"]
        if result["hero_public_url"] is not None:
            mdf.at[i, "hero_public_url"] = result["hero_public_url"]
        # Note format is `{kind}:{action}:{prep_note?}:{detail}`. Anchor the
        # action match to the second field so a stray `:uploaded:` substring in
        # an error path or filename can never miscount.
        for note in result["upload_notes"]:
            parts = note.split(":", 3)
            if len(parts) >= 2 and parts[1] in stats:
                stats[parts[1]] += 1
        flags = []
        if has_logo:
            flags.append("L")
        if has_hero:
            flags.append("H")
        print(f"  [{i+1:3d}] {lid:25s} {''.join(flags):3s}  {'; '.join(result['upload_notes'])[:100]}")

    if not args.dry_run:
        _atomic_write(mdf, args.manifest)

    print()
    print("=== Upload summary ===")
    for action in ("uploaded", "skipped", "dry-run", "failed"):
        print(f"  {action:10s} {stats[action]}")
    if args.dry_run:
        print()
        print("*** DRY RUN — nothing was uploaded and the manifest was not rewritten. ***")
    else:
        print(f"\nManifest rewritten: {os.path.abspath(args.manifest)}")


if __name__ == "__main__":
    main()
