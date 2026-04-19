# Claim Profiles + Lead Enrichment + Card Replacement — Working Checklist

> **Pull this file up** whenever the user asks about claiming profiles, enriching leads, or replacing mock cards with real ones. It is the single source of truth for where these three intertwined workstreams stand.
>
> Keep it up to date: as items flip from `[ ]` to `[x]`, update the "Current state" block at the top.

---

## Current state (update when things change)

- **Last updated:** 2026-04-19
- **Phase 1 claim plumbing:** migration `0009_claim_system.sql` applied to Supabase ✓, `generate_claim_tokens.py` with `is_sample` filter + `--include-samples` escape hatch ✓, `public_html/claim.html` full flow ✓.
- **Real prospect data in DB:** **ZERO** — dry-run `--limit 10` returned 0 rows after the sample filter. Before any real tokens can be issued, the enrichment pipeline has to run and insert real `businesses` rows with `is_sample=false, owner_id=null`.
- **Open bug (pre-existing):** `derive_channels` emits orphan `channel='manual'` tokens that never appear in any CSV. Fix before first live run.

---

## Workstream A — Claim profiles (Flow A, token-based)

### A.0 Pre-launch bug fix
- [ ] **Fix manual-channel orphan rows** in `executions/generate_claim_tokens.py`. Make `manual` a CSV-view only (don't insert a `channel='manual'` row when email/sms/messenger already covers the business). Reviewer-documented 2026-04-19. Trigger `script-reviewer` + `doc-sync` after.

### A.1 Step-by-step launch path
- [x] **Smoke-test migration 0009** — `SELECT preview_claim_token('00000000-...')` returns `{ok:false, error:token_not_found}`. ✓ 2026-04-19.
- [x] **Dry-run token script** — `python executions/generate_claim_tokens.py --dry-run --limit 10`. ✓ 2026-04-19.
- [ ] **Enrichment pipeline must run first** — see Workstream B. Script returns 0 real rows until real unowned businesses exist.
- [ ] **Pilot run (real inserts, small)** — `python executions/generate_claim_tokens.py --city "Пловдив" --limit 25`. Eyeball `tmp/outreach-tokens-*.csv` before sending anything.
- [ ] **End-to-end manual walk-through** — pick one token from the CSV, paste `https://zadeteto.com/claim.html?token=<uuid>` in an incognito window, run signup → email confirm → claim → dashboard redirect. Verify `businesses.owner_id`, `claimed_at`, `claim_method='token'` are set, and `claim_tokens.used_at` / `used_by_user` are stamped.
- [ ] **Localize Supabase auth email templates to Bulgarian** — Dashboard → Authentication → Email Templates. Currently English.
- [ ] **Pick outreach send infrastructure** — Gmail mail-merge vs. Resend / SES vs. manual paste. Script produces CSVs; nothing actually sends yet.
- [ ] **Full run per city** — drop `--limit`, batch by city.

### A.2 Post-claim onboarding gap
- [ ] **Onboarding state in [business-dashboard.html](../public_html/business-dashboard.html)** — detect `claimed_at > now() - 1 day`, show "complete your profile" checklist (logo, working hours, description, gallery). Currently a new owner lands on a generic dashboard with no welcome.
- [ ] **Partners-page CTA** — add visible "Получихте линк за активация?" strip on [partners.html](../public_html/partners.html) pointing to instructions.
- [ ] **Wire business-dashboard.html to read real data** for the logged-in owner (tracked separately in [next-steps-checklist.md:237](next-steps-checklist.md#L237)).

### A.3 Admin / ops
- [ ] **Admin claim queue page** — RLS `claim_tokens_select_admin` already exists (0009). Need a page listing open / used / expired tokens, with revoke + resend buttons.
- [ ] **Daily keep-alive** on `claim_tokens` table (part of general Supabase free-tier keep-alive task).

### A.4 Phase 2 — self-serve (Flow B)
- [ ] **Migration `0010_claim_self_serve.sql`** — EIK-match, email-domain-match, phone-match alternative paths.
- [ ] **"Това е моят бизнес" button** on listing pages → kicks off Flow B.
- [ ] **Founders Circle badge** — `founders_businesses` view exists (0009); surface the gold badge on listing cards + dashboard header for businesses claimed before 2026-06-01.

---

## Workstream B — Lead enrichment (fills the DB with real prospects)

### B.1 Pipeline components (all directives exist in `directives/`)
- [x] **`scrape-google-maps.md` + `scrape_google_maps.py`** — seed discovery from Google Maps. Status: present, last run date unknown.
- [x] **`enrich-providers.md` + `enrich_providers.py`** — adds fields to scraped rows.
- [x] **`crawl-website.md` + `crawl_website.py`** — crawls business websites for email/phone/FB/about/etc.
- [x] **`google-search-enrichment.md` + `google_search_enrichment.py`** — fills gaps via Google Search.
- [x] **`clean-segment-prospects.md` + `clean_segment_prospects.py`** — dedupe + segment.
- [x] **`enrich-and-reclassify-prospects.md` + `enrich_and_reclassify_prospects.py`** — final enrichment + tier assignment.
- [x] **`run-pipeline.md` + `run_pipeline.py`** — orchestrator.

### B.2 What's missing end-to-end
- [ ] **Insert step to `businesses` table** — confirm `run_pipeline.py` actually writes to Supabase with `is_sample=false, owner_id=null`. If it writes to CSV only, a separate "load-prospects-to-supabase" step is needed.
- [ ] **First real pipeline run** — target one category + one city to keep scope tight (e.g. детски градини Пловдив). Count rows inserted.
- [ ] **Spot-check 10 random inserted rows** — website, email, phone, FB present; tier plausible; `is_sample=false`.
- [ ] **Verify claim-token dry-run** now returns real prospects, not 0.

### B.3 Pipeline quality gates
- [ ] **Deduplication across runs** — re-running must not create duplicate `businesses` rows. Composite key on `(name, city, phone)` or `(website)`?
- [ ] **Categorization mapping** — pipeline's output categories must match the 7-category system used on search.html flip cards.
- [ ] **Phone normalization alignment** — pipeline should store `+359...` normalized so `generate_claim_tokens.py` sees canonical values (avoids the SMS-dedup drift flagged by reviewer).

---

## Workstream C — Replace mock cards with real enriched data

### C.1 Inventory of mock data currently in the DB
- [ ] **Identify all mock rows** — everything flagged `is_sample=true`. Per [next-steps-checklist.md:45-46](next-steps-checklist.md#L45-L46) there are ~106 (6 from `sample-businesses.sql` + 100 from `sample-100-mockup-partners.sql`).
- [ ] **Decide retention strategy** — keep samples for dev/staging, purge from prod? Or flip a `display_samples` env flag on search.html?

### C.2 Swap path
- [ ] **Search page filter** — `search.html` already queries Supabase. Add `.eq('is_sample', false)` to the query so only real rows render once enriched data exists. Keep a dev override (`?samples=1`) for testing.
- [ ] **Tier distribution after swap** — Supabase will contain mostly `Безплатен` unowned rows at first. Confirm the 5-tier filter chips + sort order still look good with that skew (currently tuned on mock 10/25/40/25 distribution).
- [ ] **Logo fallbacks** — most real prospects won't have logos. `getCardLogo(d)` already falls back to `placehold.co/144x144/{tierColor}/white?text={firstLetter}` — verify visually on a page of 20 real rows.
- [ ] **Photo fallbacks** — `getCardPhoto(d)` already returns a category-default Unsplash photo. Verify the 8 category defaults still match the categories the enrichment pipeline outputs.
- [ ] **Review counts on real cards** — `loadAllCardRatings()` aggregates from `reviews` table; real prospects have 0 reviews. The `"Оцени!"` nudge will trigger on most. Confirm that's the intended state at launch.
- [ ] **Related specialists** — listing.html queries "same category + same city". Needs enough real rows per (category, city) to populate. Minimum viable density?

### C.3 Production cutover
- [ ] **Dry-run the swap in staging** (or a `?real=1` query param in prod).
- [ ] **Purge or flag-hide sample rows** — either `UPDATE businesses SET published=false WHERE is_sample=true` or a schema change to exclude them from anon SELECTs via RLS.
- [ ] **Update `docs/next-steps-checklist.md`** — mark the sample-data items resolved.

---

## Cross-cutting
- [ ] **Weekly metric:** `SELECT count(*), count(*) FILTER (WHERE claimed_at IS NOT NULL) FROM businesses WHERE is_sample=false` → % claimed.
- [ ] **Alert on orphan tokens** — `SELECT count(*) FROM claim_tokens WHERE used_at IS NULL AND expires_at < now() AND revoked=false` should stay at 0.
- [ ] **OAuth providers** (Google, Facebook, LinkedIn) — still disabled in Supabase Dashboard. Any partner who tries OAuth on claim.html gets "method not enabled". Not blocking email/password + magic link path.

---

## How to use this file (for future-me)

When the user says anything like:
- "what's left on claiming profiles"
- "where are we on lead enrichment"
- "replace the cards"
- "next steps on partners onboarding"
- "where are we with [any of: claim / token / outreach / enrichment / prospects / cards]"

→ **Read this file first before answering.** Then check `git log` and current file state to verify items haven't silently flipped. Don't trust the checkbox state blindly — verify before declaring "done" or "open."

When items are completed, update:
1. The `[ ]` → `[x]` on the specific line.
2. The "Current state" block at the top of this file.
