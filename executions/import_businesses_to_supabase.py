"""
Import deduped businesses into the Supabase `businesses` table. Final step of
the lead-ingestion pipeline.

Reads:
  - tmp/deduped_all.csv    (one row per unique business)
  - tmp/image_manifest.csv (logo_public_url + hero_public_url per legacy_id)

Maps columns -> `businesses` schema. Upserts on `legacy_id` so re-runs are
idempotent. Safe defaults: `tier=Безплатен`, `is_sample=false`,
`published=false`, `sop=false`. Nothing goes public until the user flips
`published=true` manually in Supabase.

By default: DRY RUN. Writes `tmp/import_preview.csv` with the exact payload
that WOULD be sent. Use `--apply` to actually upsert.

Requires `SUPABASE_URL` + `SUPABASE_SECRET_KEY` in `.env` (the secret key
`sb_secret_...` bypasses RLS on the businesses table).

Usage:
    # Dry run (default)
    python executions/import_businesses_to_supabase.py \\
        --input tmp/deduped_all.csv \\
        --manifest tmp/image_manifest.csv \\
        --city "Стара Загора"

    # Actually upsert
    python executions/import_businesses_to_supabase.py \\
        --input tmp/deduped_all.csv \\
        --manifest tmp/image_manifest.csv \\
        --city "Стара Загора" \\
        --apply
"""

import argparse
import os
import re
import sys

import pandas as pd
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase python-dotenv", file=sys.stderr)
    sys.exit(1)


LATLNG_RE = re.compile(r"!3d(-?[\d.]+)!4d(-?[\d.]+)")
DEFAULT_TIER = "Безплатен"


def _load_env() -> tuple[str, str]:
    load_dotenv()
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not url or not key:
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY must both be set in .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return url, key


def _extract_latlng(gmaps_url: str) -> tuple[float | None, float | None]:
    m = LATLNG_RE.search(gmaps_url or "")
    if not m:
        return None, None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None, None


def _best_image(manifest_df: pd.DataFrame, legacy_id: str, merged_from: str, kind: str) -> str:
    """Return the best available public URL for the given business. Prefers
    the base's legacy_id; falls back to any legacy_id listed in merged_from.
    `kind` must be 'logo' or 'hero'."""
    col = "logo_public_url" if kind == "logo" else "hero_public_url"
    candidates = [legacy_id]
    for mid in str(merged_from or "").split("|"):
        mid = mid.strip()
        if mid:
            candidates.append(mid)
    for cid in candidates:
        rows = manifest_df[manifest_df["legacy_id"] == cid]
        if len(rows) == 0:
            continue
        v = str(rows.iloc[0][col]).strip()
        if v and not v.startswith("(dry-run)"):
            return v
    return ""


def _str_or_none(v) -> str | None:
    s = str(v or "").strip()
    return s or None


def _clean_phone(raw: str) -> str:
    """Normalize a phone: strip the ".0" suffix left over when pandas coerced
    a digit string through float, and collapse whitespace. Preserves leading
    `+` and in-between spaces so we don't over-sanitize free-form entries."""
    s = str(raw or "").strip()
    if not s:
        return ""
    # Drop the trailing '.0' artifact from float-coerced integer phones.
    if re.fullmatch(r"-?\d+\.0+", s):
        s = s.split(".")[0]
    return s


def _build_record(row: pd.Series, manifest_df: pd.DataFrame | None, city: str, import_batch: str | None, respect_csv_tier: bool = False) -> tuple[dict | None, str]:
    lid = str(row.get("legacy_id", "")).strip()
    name = str(row.get("name", "")).strip()
    if not name:
        return None, "missing name"
    if not lid:
        return None, "missing legacy_id"

    gmaps_url = str(row.get("gmaps_url", "") or row.get("google maps url", ""))
    # The extractor may pre-parse lat/lng into the CSV; fall back to parsing
    # the maps URL if those columns are empty.
    csv_lat = str(row.get("lat", "")).strip()
    csv_lng = str(row.get("lng", "")).strip()
    if csv_lat and csv_lng:
        try:
            lat, lng = float(csv_lat), float(csv_lng)
        except ValueError:
            lat, lng = _extract_latlng(gmaps_url)
    else:
        lat, lng = _extract_latlng(gmaps_url)

    categories = [c.strip() for c in str(row.get("categories", "")).split("|") if c.strip()]

    if manifest_df is not None:
        logo_url = _best_image(manifest_df, lid, str(row.get("merged_from", "")), "logo")
        hero_url = _best_image(manifest_df, lid, str(row.get("merged_from", "")), "hero")
    else:
        logo_url = ""
        hero_url = ""

    # Phone: prefer the scraper's (renamed to phone_existing by the enricher);
    # fallback to the website-crawl result (Additional Phone). Cleaned to
    # drop the '.0' suffix that pandas leaves when a digit string got
    # round-tripped through float upstream.
    phone = _clean_phone(row.get("phone_existing", "")) or _clean_phone(row.get("Additional Phone", ""))

    address = _str_or_none(row.get("address"))

    # Tier + published can be sourced from the CSV row when --respect-csv-tier
    # is set (rank_and_quota.py pre-fills these). Otherwise fall back to the
    # safe defaults (DEFAULT_TIER, published=False).
    if respect_csv_tier:
        csv_tier = str(row.get("tier", "")).strip() or DEFAULT_TIER
        csv_pub_raw = str(row.get("published", "")).strip().lower()
        csv_published = csv_pub_raw in ("true", "1", "yes", "y", "t")
    else:
        csv_tier = DEFAULT_TIER
        csv_published = False

    record = {
        "legacy_id": lid,
        "name": name,
        "tier": csv_tier,
        "city": city,
        "address": address,
        "lat": lat,
        "lng": lng,
        "phone": phone or None,
        "email": _str_or_none(row.get("Email")),
        "website": _str_or_none(row.get("website")),
        "facebook": _str_or_none(row.get("Facebook URL")),
        "instagram": _str_or_none(row.get("Instagram URL")),
        "linkedin": _str_or_none(row.get("LinkedIn URL")),
        "youtube": _str_or_none(row.get("YouTube URL")),
        "tiktok": _str_or_none(row.get("TikTok URL")),
        "maps": _str_or_none(gmaps_url),
        "categories": categories,
        "services": [],
        "age_groups": [],
        "sop": False,
        "published": csv_published,
        "is_sample": False,
    }
    # Only write logo/gallery_urls when a manifest was provided. Re-running
    # without --manifest must never clobber previously-uploaded images.
    if manifest_df is not None:
        record["logo"] = logo_url or None
        record["gallery_urls"] = [hero_url] if hero_url else []
    if import_batch and import_batch.strip():
        record["import_batch"] = import_batch.strip()

    # Good-enough rule (user policy 2026-04-26, see
    # memory/feedback_good_enough_only.md): a listing must have >=1 URL among
    # {website, facebook, instagram} AND >=1 contact among {phone, email}.
    # Anything below that bar is rejected at import time so blanks never make
    # it into the parent journey.
    has_url = any(record.get(f) for f in ("website", "facebook", "instagram"))
    has_contact = any(record.get(f) for f in ("phone", "email"))
    if not (has_url and has_contact):
        missing = []
        if not has_url:
            missing.append("no-url")
        if not has_contact:
            missing.append("no-contact")
        return None, "not good-enough: " + ",".join(missing)

    return record, ""


def _record_to_preview_row(rec: dict) -> dict:
    # Flatten arrays to pipe-separated strings so the preview CSV is easy to
    # scan in Excel / VS Code.
    out = dict(rec)
    for k in ("categories", "services", "age_groups", "gallery_urls"):
        v = out.get(k) or []
        out[k] = "|".join(v) if isinstance(v, list) else str(v)
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
    parser = argparse.ArgumentParser(description="Import deduped businesses into Supabase `businesses`. Dry-run by default.")
    parser.add_argument("--input", required=True, help="Deduped CSV (e.g. tmp/deduped_all.csv).")
    parser.add_argument("--manifest", default=None, help="Optional image manifest CSV with logo_public_url / hero_public_url. Omit if the batch has no uploaded images yet (e.g. first-pass Sofia import).")
    parser.add_argument("--city", required=True, help="City to set on every imported row (e.g. 'Стара Загора').")
    parser.add_argument("--tier", default=DEFAULT_TIER, help=f"Default tier (default: {DEFAULT_TIER}). Must be a valid business_tier enum value.")
    parser.add_argument("--import-batch", default=None, help="Opaque tag written to businesses.import_batch so this load can be wiped cleanly later (e.g. 'sofia-2026-04-21').")
    parser.add_argument("--preview-out", default="tmp/import_preview.csv", help="Where to write the dry-run preview CSV.")
    parser.add_argument("--results-out", default="tmp/import_results.csv", help="Where to write the per-row apply results.")
    parser.add_argument("--apply", action="store_true", help="Actually upsert into Supabase. Without this flag, the script is dry-run.")
    parser.add_argument("--respect-csv-tier", action="store_true", help="Read tier + published from each CSV row instead of overriding with --tier and the published=False default. Required for rank_and_quota.py output.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if args.manifest and not os.path.exists(args.manifest):
        print(f"ERROR: manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(args.input, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    manifest_df: pd.DataFrame | None = None
    if args.manifest:
        manifest_df = pd.read_csv(args.manifest, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    records: list[dict] = []
    skipped: list[dict] = []
    for _, row in df.iterrows():
        rec, err = _build_record(row, manifest_df, args.city, args.import_batch, respect_csv_tier=args.respect_csv_tier)
        if err:
            skipped.append({"legacy_id": str(row.get("legacy_id", "")), "name": str(row.get("name", "")), "reason": err})
        else:
            if not args.respect_csv_tier:
                rec["tier"] = args.tier  # respect --tier override
            records.append(rec)

    # Always write the preview CSV (useful even on --apply for post-hoc audit)
    preview_df = pd.DataFrame([_record_to_preview_row(r) for r in records])
    _atomic_write(preview_df, args.preview_out)

    print(f"Built:   {len(records)} records")
    print(f"Skipped: {len(skipped)} (see summary below)")
    for s in skipped[:5]:
        print(f"  - {s['legacy_id']}: {s['reason']} ({s['name'][:40]})")
    if len(skipped) > 5:
        print(f"  ... +{len(skipped) - 5} more")
    print(f"Preview: {os.path.abspath(args.preview_out)}")

    if not args.apply:
        print()
        print("*** DRY RUN — nothing was sent to Supabase. Re-run with --apply to upsert. ***")
        return

    # Apply
    url, key = _load_env()
    client: Client = create_client(url, key)
    results: list[dict] = []
    ok = 0
    failed = 0
    for i, rec in enumerate(records, start=1):
        try:
            resp = client.table("businesses").upsert(rec, on_conflict="legacy_id").execute()
            supabase_id = resp.data[0].get("id") if resp.data else None
            results.append({
                "legacy_id": rec["legacy_id"],
                "name": rec["name"],
                "status": "ok",
                "supabase_id": supabase_id or "",
                "error": "",
            })
            ok += 1
            print(f"  [{i:3d}/{len(records)}] {rec['legacy_id']:25s} -> {supabase_id or 'ok'}")
        except Exception as e:
            msg = str(e)[:200]
            results.append({
                "legacy_id": rec["legacy_id"],
                "name": rec["name"],
                "status": "error",
                "supabase_id": "",
                "error": msg,
            })
            failed += 1
            print(f"  [{i:3d}/{len(records)}] {rec['legacy_id']:25s} FAILED: {msg}", file=sys.stderr)

    _atomic_write(pd.DataFrame(results), args.results_out)
    print()
    print("=== Apply summary ===")
    print(f"  ok:     {ok}")
    print(f"  failed: {failed}")
    print(f"  skipped (pre-apply): {len(skipped)}")
    print(f"Results: {os.path.abspath(args.results_out)}")


if __name__ == "__main__":
    main()
