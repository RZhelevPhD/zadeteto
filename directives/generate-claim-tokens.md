# Generate Claim Tokens — Directive

## Purpose

Generate one-time UUID claim tokens for every unowned business in Supabase, so the outreach team can send `/claim.html?token=<uuid>` links via email, SMS, Messenger, or during phone calls. Each link is single-use and expires in 90 days.

This is the primary outreach path (Flow A) in the claim-profile plan. Organic self-serve discovery (Flow B) is a separate system (see `directives/claim-self-serve.md`, Phase 2).

## Inputs

- **Supabase credentials** — loaded from `.env`:
  - `SUPABASE_URL`
  - `SUPABASE_SECRET_KEY` (the `sb_secret_...` key; needed because RLS blocks the publishable key from inserting into `claim_tokens`)
- **Filter flags** (all optional):
  - `--city "Пловдив"` — only prospects in this city
  - `--tier "Безплатен"` — only this tier (default: any tier where `owner_id IS NULL`)
  - `--limit N` — cap the number of businesses processed (for pilot runs)
  - `--channels email,sms,messenger,manual` — which channels to generate tokens for (default: all available)
  - `--dry-run` — preview what would be inserted; do not write to DB
  - `--base-url https://zadeteto.com` — override claim URL origin (default: `https://zadeteto.com`)
  - `--output-dir tmp/` — where to write the per-channel CSVs
  - `--reuse-existing` — reuse an already-open (non-expired, non-used, non-revoked) token for a given (business, channel, sent_to) triple instead of inserting a new one. Default: skip that triple.
  - `--include-samples` — include businesses flagged `is_sample = true` (mock/seed data inserted via `supabase/sample-*.sql`, column added in migration 0004). **Default: exclude.** Use only for internal end-to-end testing. When combined with a live (non-dry-run) insert, the script prints a stderr WARNING because it will generate real tokens against mock businesses.

## Channel → contact mapping

For each unowned business, the script decides which channels it has enough data for:

| Channel | Source field(s) | `sent_to` |
|---|---|---|
| `email` | `businesses.email` | that email |
| `sms` | `businesses.phone` — normalized to `+359...`. Accepts BG mobile (12 digits starting `359`), BG landline (11 digits starting `359`, e.g. Sofia `+359 2 ...`), and local-format numbers (9 or 10 digits starting `0`). Anything else is rejected. | normalized phone |
| `messenger` | `businesses.facebook` | the FB page URL/handle |
| `manual` | Always generated if the business has any contact at all | the first available contact (email > phone > FB) |

If a business has **no** email, phone, or Facebook — nothing is generated. That row ends up in `tmp/claim-tokens-skipped.csv` for manual follow-up.

## Outputs

All written under `--output-dir` (default `tmp/`):

- `outreach-tokens-email.csv` — columns: `business_id, name, slug, city, channel, sent_to, claim_url, token, created_at, expires_at`
- `outreach-tokens-sms.csv` — same columns, `sent_to` is `+359...` normalized
- `outreach-tokens-messenger.csv` — same columns, `sent_to` is the FB URL
- `outreach-tokens-manual.csv` — all businesses (union of above); use for personal calls where you pick the best channel on the fly
- `claim-tokens-skipped.csv` — businesses with no usable contact; columns: `business_id, name, reason`
- `claim-tokens-report.json` — summary: total prospects, per-channel token counts, skip count, `dry_run` flag, top-level `include_samples` and `reuse_existing` booleans (mirroring the CLI flags used), a `filters` sub-object containing `city`, `tier`, `limit`, and `include_samples`, and a `partial_failure` field (null on success; `{failed_chunk_index, error}` if a chunked insert failed mid-run)

All four channel CSVs (`email`, `sms`, `messenger`, `manual`) are **always** written on every run, even when a channel is disabled via `--channels` or has zero rows. Disabled/empty CSVs are header-only. This is intentional: it prevents operators from acting on stale CSVs left behind by previous runs.

CSV encoding: UTF-8 with BOM (so Excel opens Cyrillic correctly).

## Database writes

The upstream SELECT on `public.businesses` already filters out rows where `is_sample = true` (unless `--include-samples` is passed), so mock/seed businesses never reach the insert step. The filter uses `is_sample = false` and relies on the column being `NOT NULL DEFAULT false` (guaranteed by migration 0004, including its backfill of legacy rows).

One row per generated token, inserted into `public.claim_tokens` via the Supabase REST API using `SUPABASE_SECRET_KEY`. Inserts are **chunked** at 200 rows per POST to keep payloads small and to bound the blast radius of a single failure. If chunk N fails, chunks `0..N-1` that already succeeded are kept, written to the channel CSVs, and the report's `partial_failure` field is populated; the script exits non-zero.

Row shape:

```
{
  "business_id": "<uuid>",
  "channel": "email",           -- one of: email, sms, messenger, manual
  "sent_to": "owner@business.bg"
  -- token, created_at, expires_at (+90 days), used_at (NULL), revoked (false) all defaulted
}
```

The RPC `preview_claim_token` + `claim_profile_with_token` handle the redemption flow; this script only generates the tokens.

When checking for existing open tokens (for skip / `--reuse-existing` logic), the SELECT pulls `token, business_id, channel, sent_to, created_at, expires_at` so reused rows carry full metadata through to the CSVs.

## Idempotency

Re-running the script:
- By default, a business that already has an open (non-expired, non-used, non-revoked) token for a given (channel, sent_to) is **skipped** — the open token remains valid.
- With `--reuse-existing`, the existing open token's URL is re-exported to the CSVs (so you can resend without invalidating the old link).
- The script never revokes or overwrites existing tokens. To revoke, do it manually via SQL:
  ```sql
  UPDATE public.claim_tokens SET revoked = true WHERE business_id = '<uuid>' AND used_at IS NULL;
  ```

## Error handling

- **Missing env vars** → abort immediately with a clear message.
- **Transient HTTP failures** — every Supabase GET/POST is wrapped with a single retry with 1s backoff on 5xx responses or connection/timeout errors. A second failure is raised to the caller.
- **Supabase 4xx on bulk insert** → no retry. Log the response body. Any chunks that already succeeded are written to CSVs, the `partial_failure` field in the report is populated, and the script exits non-zero.
- **Malformed phone** (doesn't match the accepted `+359` / `0`-prefixed shapes above) → skip the SMS channel for that row; still generate email/manual if available.

## Dry-run behavior

With `--dry-run`, no rows are written to the DB. The CSVs are still produced so operators can eyeball the plan; each "inserted" row is synthesized with a **real throwaway UUID** (via `uuid.uuid4()`) in the `token` column and the literal string `(dry-run)` in `created_at`. These UUIDs are structurally valid but are not persisted and will never redeem against the live DB — do **not** send them to anyone.

## Running the script

```bash
python executions/generate_claim_tokens.py --dry-run --limit 10
python executions/generate_claim_tokens.py --city "Пловдив" --channels email,manual
python executions/generate_claim_tokens.py            # full run, all channels (excludes is_sample=true)
python executions/generate_claim_tokens.py --dry-run --include-samples --limit 5   # test scenario only: preview against mock data
```

## Changelog

- 2026-04-19 — Initial version (Phase 1 of claim-profile flow).
- 2026-04-19 — Reviewer-driven fixes: documented relaxed phone normalization (11-digit `+359` landlines, 9-digit local format); chunked bulk insert (200 rows/chunk) with partial-failure recovery and `partial_failure` report field; 1-retry-with-backoff on 5xx/connection errors; all four channel CSVs always written (header-only if disabled/empty) to avoid stale files; dry-run tokens are now real throwaway UUIDs (not the `<dry-run-no-token>` literal); CSV columns now include `expires_at` (and `channel`); reused-token SELECT also pulls `created_at`.
- 2026-04-19 — Documented new `is_sample = false` default filter in `fetch_unowned_businesses` so live runs cannot issue real claim tokens against mock/seed businesses (migration 0004 column). Added `--include-samples` CLI flag for internal end-to-end testing (prints stderr WARNING if used with a live insert). Updated `claim-tokens-report.json` spec to include top-level `include_samples` and `reuse_existing` fields plus `filters.include_samples`. Added a test-scenario example to the Running the script block.
