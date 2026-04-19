"""Generate claim tokens for unowned businesses and export per-channel outreach CSVs.

See directives/generate-claim-tokens.md for the full spec.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import requests


CLAIM_URL_TEMPLATE = "{base}/claim.html?token={token}"
CHANNELS = ("email", "sms", "messenger", "manual")


# ──────────────────────── env + HTTP helpers ────────────────────────


def load_env(env_path: Path) -> dict[str, str]:
    """Parse a .env file. Only `KEY=value` lines (no quoting gymnastics)."""
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def pg_headers(secret_key: str, *, prefer: str | None = None) -> dict[str, str]:
    h = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _http_with_retry(method: str, url: str, *, max_attempts: int = 2, backoff_s: float = 1.0, **kw):
    """GET/POST with one retry on 5xx or connection error."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.request(method, url, **kw)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(backoff_s)
                continue
            raise
        if 500 <= resp.status_code < 600 and attempt < max_attempts:
            time.sleep(backoff_s)
            continue
        return resp
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unreachable")


def fetch_unowned_businesses(
    url: str,
    secret: str,
    *,
    city: str | None,
    tier: str | None,
    limit: int | None,
    include_samples: bool = False,
) -> list[dict]:
    """Pull businesses where owner_id IS NULL, selected fields only.

    By default, rows flagged `is_sample = true` (seed / mock data inserted
    via `supabase/sample-*.sql`) are excluded so a live run cannot issue
    real claim tokens against fake businesses. Pass include_samples=True
    only for internal end-to-end testing.
    """
    select = "id,name,slug,city,tier,email,phone,facebook,instagram,is_sample"
    params: dict[str, str] = {
        "select": select,
        "owner_id": "is.null",
        "order": "created_at.asc",
    }
    if not include_samples:
        # is_sample is NOT NULL with default false (migration 0004), so a
        # plain `eq.false` is safe and indexable. Covers both new rows and
        # legacy rows that were backfilled to false.
        params["is_sample"] = "eq.false"
    if city:
        params["city"] = f"eq.{city}"
    if tier:
        params["tier"] = f"eq.{tier}"
    if limit is not None:
        params["limit"] = str(limit)

    resp = _http_with_retry(
        "GET",
        f"{url}/rest/v1/businesses",
        headers=pg_headers(secret),
        params=params,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase GET /businesses failed: {resp.status_code} {resp.text[:500]}"
        )
    return resp.json()


def fetch_open_tokens(url: str, secret: str, business_ids: list[str]) -> list[dict]:
    """Return open (unused, unrevoked, unexpired) tokens for the given business_ids.

    PostgREST `in` filter; chunked to avoid URL length limits.
    """
    if not business_ids:
        return []
    out: list[dict] = []
    for i in range(0, len(business_ids), 100):
        chunk = business_ids[i : i + 100]
        ids_csv = ",".join(chunk)
        params = {
            "select": "token,business_id,channel,sent_to,created_at,expires_at",
            "business_id": f"in.({ids_csv})",
            "used_at": "is.null",
            "revoked": "eq.false",
            "expires_at": "gte.now()",
        }
        resp = _http_with_retry(
            "GET",
            f"{url}/rest/v1/claim_tokens",
            headers=pg_headers(secret),
            params=params,
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Supabase GET /claim_tokens failed (chunk {i // 100}): "
                f"{resp.status_code} {resp.text[:500]}"
            )
        out.extend(resp.json())
    return out


class InsertPartialFailure(RuntimeError):
    """Raised when a chunked insert fails mid-run. Carries what was already inserted."""

    def __init__(self, message: str, inserted: list[dict], failed_chunk_index: int):
        super().__init__(message)
        self.inserted = inserted
        self.failed_chunk_index = failed_chunk_index


def insert_tokens(url: str, secret: str, rows: list[dict], *, chunk_size: int = 200) -> list[dict]:
    """Bulk-insert rows into claim_tokens in chunks; return successfully inserted rows.

    On failure of chunk N, raises InsertPartialFailure carrying the rows from
    chunks 0..N-1 so the caller can still export what succeeded.
    """
    if not rows:
        return []
    inserted: list[dict] = []
    for idx, start in enumerate(range(0, len(rows), chunk_size)):
        chunk = rows[start : start + chunk_size]
        resp = _http_with_retry(
            "POST",
            f"{url}/rest/v1/claim_tokens",
            headers=pg_headers(secret, prefer="return=representation"),
            data=json.dumps(chunk),
            timeout=60,
        )
        if resp.status_code >= 400:
            raise InsertPartialFailure(
                f"Supabase POST /claim_tokens failed at chunk {idx} "
                f"(rows {start}..{start + len(chunk) - 1}): "
                f"{resp.status_code} {resp.text[:1000]}",
                inserted=inserted,
                failed_chunk_index=idx,
            )
        chunk_out = resp.json()
        if len(chunk_out) != len(chunk):
            print(
                f"WARNING: chunk {idx} returned {len(chunk_out)} rows for {len(chunk)} sent.",
                file=sys.stderr,
            )
        inserted.extend(chunk_out)
    return inserted


# ──────────────────────── channel derivation ────────────────────────

_NON_DIGITS = re.compile(r"\D+")


def normalize_phone(raw: str | None) -> str | None:
    """Return +359... form, or None if unusable.

    Accepts Bulgarian mobile (12 digits starting 359) and landline (11 digits
    starting 359, e.g. Sofia +359 2 ... = 3592XXXXXXX), plus local-format
    numbers with a leading 0 (9 or 10 digits total, e.g. 0888123456 or
    02/9876543 → 029876543).
    """
    if not raw:
        return None
    digits = _NON_DIGITS.sub("", raw)
    if not digits:
        return None
    if digits.startswith("359") and len(digits) in (11, 12):
        return "+" + digits
    if digits.startswith("0") and len(digits) in (9, 10):
        return "+359" + digits[1:]
    # Reject ambiguous shapes — don't guess
    return None


def first_nonempty(value: str | None) -> str | None:
    """Business fields sometimes hold `; `-joined lists — keep the first entry."""
    if not value:
        return None
    first = value.split(";")[0].strip()
    return first or None


def derive_channels(biz: dict, enabled: set[str]) -> list[tuple[str, str]]:
    """Return list of (channel, sent_to) pairs this business can be reached on."""
    pairs: list[tuple[str, str]] = []
    email = first_nonempty(biz.get("email"))
    phone_raw = first_nonempty(biz.get("phone"))
    phone = normalize_phone(phone_raw) if phone_raw else None
    facebook = first_nonempty(biz.get("facebook"))

    if "email" in enabled and email and "@" in email:
        pairs.append(("email", email))
    if "sms" in enabled and phone:
        pairs.append(("sms", phone))
    if "messenger" in enabled and facebook:
        pairs.append(("messenger", facebook))
    if "manual" in enabled:
        # Best-effort: pick the first available contact
        best = email or phone or facebook
        if best:
            pairs.append(("manual", best))
    return pairs


# ──────────────────────── main ────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate claim tokens for unowned businesses.")
    ap.add_argument("--city", default=None, help="Filter by city (exact match).")
    ap.add_argument("--tier", default=None, help="Filter by tier (e.g. 'Безплатен').")
    ap.add_argument("--limit", type=int, default=None, help="Cap number of businesses processed.")
    ap.add_argument(
        "--channels",
        default=",".join(CHANNELS),
        help=f"Comma-separated subset of {CHANNELS}. Default: all.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview only; don't write to DB.")
    ap.add_argument("--reuse-existing", action="store_true", help="Export existing open tokens instead of skipping.")
    ap.add_argument(
        "--include-samples",
        action="store_true",
        help="Include businesses flagged is_sample=true (mock/seed data). Default: exclude. Use only for end-to-end testing.",
    )
    ap.add_argument("--base-url", default="https://zadeteto.com", help="Origin for the claim URL.")
    ap.add_argument("--output-dir", default="tmp", help="Directory for CSV outputs.")
    ap.add_argument("--env-file", default=".env", help="Path to .env file (default: ./.env).")
    args = ap.parse_args()

    enabled_channels = {c.strip() for c in args.channels.split(",") if c.strip()}
    unknown = enabled_channels - set(CHANNELS)
    if unknown:
        print(f"ERROR: unknown channel(s): {unknown}. Valid: {CHANNELS}", file=sys.stderr)
        return 2

    project_root = Path(__file__).resolve().parent.parent
    env_path = (project_root / args.env_file).resolve()
    env = load_env(env_path)
    supabase_url = (env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL") or "").rstrip("/")
    supabase_secret = env.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SECRET_KEY")
    if not supabase_url or not supabase_secret:
        print(
            f"ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY must be set (checked {env_path}).",
            file=sys.stderr,
        )
        return 2

    out_dir = (project_root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch unowned businesses
    businesses = fetch_unowned_businesses(
        supabase_url,
        supabase_secret,
        city=args.city,
        tier=args.tier,
        limit=args.limit,
        include_samples=args.include_samples,
    )
    sample_note = " (including is_sample=true)" if args.include_samples else ""
    print(f"Found {len(businesses)} unowned business(es){sample_note}.")
    if args.include_samples and not args.dry_run:
        print(
            "WARNING: --include-samples + live insert will generate real tokens "
            "against mock businesses. Hit Ctrl+C now if that's not intended.",
            file=sys.stderr,
        )

    # 2. Fetch open tokens (for skip / reuse logic)
    biz_ids = [b["id"] for b in businesses]
    open_tokens = fetch_open_tokens(supabase_url, supabase_secret, biz_ids)
    # Index by (business_id, channel, sent_to)
    open_index: dict[tuple[str, str, str], dict] = {}
    for t in open_tokens:
        key = (t["business_id"], t["channel"], t.get("sent_to") or "")
        open_index[key] = t

    # 3. Decide which tokens to insert vs. reuse vs. skip
    to_insert: list[dict] = []
    to_reuse: list[dict] = []  # existing token rows we'll still export
    biz_by_id = {b["id"]: b for b in businesses}
    skipped: list[dict] = []

    for biz in businesses:
        pairs = derive_channels(biz, enabled_channels)
        if not pairs:
            skipped.append(
                {
                    "business_id": biz["id"],
                    "name": biz.get("name", ""),
                    "reason": "no usable contact (email/phone/facebook all missing)",
                }
            )
            continue
        for channel, sent_to in pairs:
            key = (biz["id"], channel, sent_to)
            existing = open_index.get(key)
            if existing:
                if args.reuse_existing:
                    to_reuse.append(existing)
                # else: silently skip — the open token is still valid
                continue
            to_insert.append(
                {
                    "business_id": biz["id"],
                    "channel": channel,
                    "sent_to": sent_to,
                }
            )

    print(f"Plan: insert {len(to_insert)} new, reuse {len(to_reuse)}, skip {len(skipped)}.")

    # 4. Insert (unless --dry-run)
    inserted: list[dict] = []
    partial_failure: InsertPartialFailure | None = None
    if not args.dry_run and to_insert:
        try:
            inserted = insert_tokens(supabase_url, supabase_secret, to_insert)
            print(f"Inserted {len(inserted)} token(s).")
        except InsertPartialFailure as exc:
            partial_failure = exc
            inserted = exc.inserted
            print(f"PARTIAL INSERT: {len(inserted)} succeeded before failure.", file=sys.stderr)
            print(f"Error: {exc}", file=sys.stderr)
    elif args.dry_run and to_insert:
        # Synthesize rows with real throw-away UUIDs so the CSV is structurally
        # valid — these tokens are NOT persisted and will never validate against
        # the DB; they're only for operator eyeballing.
        inserted = [
            dict(row, token=str(uuid.uuid4()), created_at="(dry-run)")
            for row in to_insert
        ]
        print("Dry-run: no DB writes. Tokens in CSV are placeholder UUIDs, not persisted.")

    # 5. Build per-channel CSVs
    #    One output row per token (new OR reused).
    all_rows: list[dict] = []
    for row in inserted + to_reuse:
        biz = biz_by_id.get(row["business_id"], {})
        token = row.get("token", "")
        claim_url = CLAIM_URL_TEMPLATE.format(base=args.base_url.rstrip("/"), token=token)
        all_rows.append(
            {
                "business_id": row["business_id"],
                "name": biz.get("name", ""),
                "slug": biz.get("slug", "") or "",
                "city": biz.get("city", "") or "",
                "channel": row.get("channel", ""),
                "sent_to": row.get("sent_to", "") or "",
                "claim_url": claim_url,
                "token": token,
                "created_at": row.get("created_at", "") or "",
                "expires_at": row.get("expires_at", "") or "",
            }
        )

    # Write per-channel CSVs. The "manual" CSV is special: per the directive,
    # it contains the UNION of all channels deduped by business_id — one row
    # per business with the best-available channel (email > sms > messenger >
    # explicit manual). Operators use it for ad-hoc calls where they pick the
    # channel on the fly.
    fieldnames = [
        "business_id",
        "name",
        "slug",
        "city",
        "channel",
        "sent_to",
        "claim_url",
        "token",
        "created_at",
        "expires_at",
    ]

    # Bucket rows by their literal channel first
    per_channel: dict[str, list[dict]] = OrderedDict((c, []) for c in CHANNELS)
    for r in all_rows:
        ch = r["channel"]
        if ch in per_channel:
            per_channel[ch].append(r)
        else:
            # Stray channel — should not happen; log and skip
            print(f"WARNING: unknown channel '{ch}' on row for business {r.get('business_id')}", file=sys.stderr)

    # Build the manual union: one row per business, preferring email > sms > messenger > manual
    preference = {"email": 0, "sms": 1, "messenger": 2, "manual": 3}
    best_by_biz: dict[str, dict] = {}
    for r in all_rows:
        bid = r["business_id"]
        cur = best_by_biz.get(bid)
        if cur is None or preference.get(r["channel"], 99) < preference.get(cur["channel"], 99):
            best_by_biz[bid] = r
    per_channel["manual"] = list(best_by_biz.values())

    # Always write all four channel CSVs (empty header-only if disabled or no
    # rows) so operators don't see stale files from previous runs.
    for channel in CHANNELS:
        rows = per_channel.get(channel, [])
        out_path = out_dir / f"outreach-tokens-{channel}.csv"
        with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            if channel in enabled_channels:
                w.writerows(rows)
        written = len(rows) if channel in enabled_channels else 0
        marker = "" if channel in enabled_channels else " (disabled; header-only)"
        print(f"Wrote {out_path} ({written} row(s)){marker}")

    # Skipped
    if skipped:
        skipped_path = out_dir / "claim-tokens-skipped.csv"
        with skipped_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["business_id", "name", "reason"])
            w.writeheader()
            w.writerows(skipped)
        print(f"Wrote {skipped_path} ({len(skipped)} row(s))")

    # 6. Report
    report = {
        "supabase_url": supabase_url,
        "base_url": args.base_url,
        "filters": {
            "city": args.city,
            "tier": args.tier,
            "limit": args.limit,
            "include_samples": bool(args.include_samples),
        },
        "channels": sorted(enabled_channels),
        "businesses_found": len(businesses),
        "tokens_inserted": 0 if args.dry_run else len(inserted),
        "tokens_reused": len(to_reuse),
        "businesses_skipped": len(skipped),
        "dry_run": bool(args.dry_run),
        "include_samples": bool(args.include_samples),
        "reuse_existing": bool(args.reuse_existing),
        "partial_failure": {
            "failed_chunk_index": partial_failure.failed_chunk_index,
            "error": str(partial_failure),
        } if partial_failure else None,
        "per_channel_counts": {c: len(per_channel.get(c, [])) for c in CHANNELS},
    }
    report_path = out_dir / "claim-tokens-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {report_path}")
    return 1 if partial_failure else 0


if __name__ == "__main__":
    sys.exit(main())
