# ZaDeteto 2.0 — Next Steps Checklist

> Snapshot taken: 2026-04-06 (last updated 2026-04-07)
> Current state: All frontend pages complete, no backend, vanilla HTML/CSS/JS
>
> **2026-04-07 update:** `search.html` and `search-mobile.html` merged into one
> responsive file with a 900px breakpoint (desktop grid above, swipe stack below).
> `search-mobile.html` deleted. Single SEO URL preserved for both UX modes.

---

## Current Pages (all complete)

| Page | File | Size | Key Features |
|------|------|------|--------------|
| Home | `index.html` | 31KB | Video hero, GSAP scroll animations, flip cards (7 categories), kinetic marquee |
| Search (desktop) | `search.html` | 62KB | Filter sidebar, swipeable card stack, category system, tier filters |
| Search (mobile) | `search-mobile.html` | 60KB | Mobile-optimized variant of search |
| Partners (B2B) | `partners.html` | 21KB | Pain/pro points, FAQ accordion, location quotas, application form |
| Contacts | `contacts.html` | 9KB | Contact cards + feedback form |
| Business Login | `business-login.html` | 5KB | Email/password login form |
| Business Dashboard | `business-dashboard.html` | 12KB | Stats cards, recent reviews, messages sidebar |

**Brand assets:** 10 logo SVGs + brand scripts doc in `brand_assets/`  
**Dev tools:** `serve.mjs` (localhost:3000), `screenshot.mjs` (headless Chrome)  
**Stack:** Vanilla HTML/CSS/JS, Tailwind CDN, GSAP + ScrollTrigger, DM Sans + DM Serif Display  

---

## Priority 1: Missing Pages

- [x] **Specialist Profile / Listing Page** (`listing.html`) — DONE 2026-04-08 (enrichment pass):
  - [x] Full specialist info (name, tier, badges, city, contacts, description, services, age groups) — already present
  - [ ] Photo gallery — placeholders kept as-is for now (user choice). Schema column `gallery_urls text[]` added in migration 0003 so future activation is one SQL UPDATE per business.
  - [x] **Parent reviews — wired to real Supabase** + mock fallback. New `loadRealReviews()` queries `reviews WHERE business_id = X AND approved = true ORDER BY created_at DESC LIMIT 20`. Falls back to mock data with a yellow "Примерни данни" badge when zero approved reviews exist. The moment you approve any real review in the dashboard, it replaces the mock for that business.
  - [x] Contact / booking CTA — already present (sticky sidebar)
  - [x] **Location section** — replaced "Очаквайте скоро" placeholder with **Google Maps Embed iframe**, consent-gated. If user has not accepted analytics cookies, shows a click-to-load placeholder ("Картата изисква съгласие за бисквитки") with explicit consent button. Listens for `zd-consent-change` event so if user accepts cookies elsewhere, the placeholder upgrades to a real map automatically. No API key needed for the basic embed.
  - [x] **Related specialists ("Подобни специалисти")** — new section at the bottom of the listing column. Queries Supabase for 4-6 other businesses with same category + same city, falls back to "any city" if not enough matches. Excludes free tier and current business. Renders as horizontal scroll of compact cards. Click → navigates to that listing.
  - [x] Link from search card → this page (already working before this bundle)
  - [x] **Real working hours** in sidebar — new `renderWorkingHours()` reads `businesses.working_hours jsonb` column. Highlights today's day in brand purple. Hides the entire block when null (no more misleading hardcoded "Пн–Пт: 9:00–18:00" on every page). Schema column added in migration 0003.
  - **NEW SQL FILES (require user action):**
    - [supabase/migrations/0003_listing_enrichment.sql](../supabase/migrations/0003_listing_enrichment.sql) — adds `working_hours jsonb` and `gallery_urls text[]` columns to businesses table. Idempotent.
    - [supabase/migrations/0004_is_sample_flag.sql](../supabase/migrations/0004_is_sample_flag.sql) — adds `is_sample boolean DEFAULT false NOT NULL` column for safe sample-data tracking. Idempotent. Backfills the 6 rows from `sample-businesses.sql` automatically.
    - [supabase/sample-businesses.sql](../supabase/sample-businesses.sql) — inserts 6 sample businesses (1 elite hero + 5 supporting in same category) so the listing page has something to render and the related-specialists section has something to populate. All flagged `is_sample = true`. Safe to re-run.
    - [supabase/sample-100-mockup-partners.sql](../supabase/sample-100-mockup-partners.sql) — 100 procedurally-generated mockup businesses for visual density / UX testing of search.html, filters, related specialists. Distribution: 10 Доверен / 25 Проверен / 40 Стандартен / 25 Безплатен tiers. 8 categories round-robined. Cities weighted toward София. ~14% SOP. Lat/lng with per-row offsets. All flagged `is_sample = true`.
    - [supabase/sample-data-tracking.md](../supabase/sample-data-tracking.md) — full safety contract documentation. Explains how `is_sample` works, daily-use queries (count real vs mock, identify unknown rows), cleanup operations, and how to add your own sample data later. **Read this before launch** to make sure no mockup data ships to production.
  - **Privacy policy updated** — Google Maps now mentioned explicitly as a third-party processor with details on cookie behavior and consent gating.

- [ ] **About / How It Works Page** (optional — could be section on index.html)
  - Explain verification process
  - Show parent journey: Search → Compare → Choose → Review
  - Build trust with transparency

---

## Priority 2: Consolidation & Code Health

- [x] **Merge search pages** — DONE 2026-04-07. `search.html` + `search-mobile.html`
  combined into single file with 900px breakpoint (Option 2: coexist DOM, CSS swap).
  Both UX modes preserved 1:1, shared state, single SEO URL. Old file deleted.

- [x] **Clean up root directory** — DONE 2026-04-08. Moved 5 experiment files
  (`flip-cards.html`, `kinetic-marquee.html`, `sticky-stack.html`, `particle-button.html`,
  `mesh-gradient.html`) plus `partners.html.bak` into `_archive_experiments/`. Verified
  no production HTML/JS/CSS references them. Root now contains exactly the 12
  production HTML pages. Both `hero-video.mp4` AND `hero-video-2.mp4` are kept —
  index.html uses both for the crossfade hero (lines 224 + 227).
  - [ ] Organize `temporary screenshots/` — separate, not blocking launch.

---

## Priority 3: Visual QA & Polish

- [x] **Cross-page consistency check** — PARTIALLY DONE 2026-04-08. Audit ran against all 12 production HTML files:
  - ✅ **Footer consistency** — all 12 pages use `.zd-footer` with identical link list and copyright, no drift detected
  - ✅ **Typography** — DM Sans + DM Serif Display on every page, no rogue `Inter`/`Playfair`/etc imports
  - ✅ **Logo heights bumped to 80px** — initially normalized to 44px during the QA bundle, then bumped to 80px on 2026-04-08 because the smaller logo wasn't readable enough at typical viewing distance. All 12 nav contexts now uniform at 80px. business-dashboard sidebar logo is the exception at 64px (constrained-width sidebar). business-login hero logo also 80px.
  - ✅ **Color palette** — brand purple/gold/mint used consistently via CSS vars. The `#2e994d` in pricing.html is NOT drift — it's `--zd-mint-600` (darker shade) used intentionally for text on light backgrounds, matching search.html's scale.
  - [ ] **Nav bar deep consistency** — some pages have inline nav, some have class-based nav with minor style drift (glass effect on index.html vs solid purple on others). Not blocking launch but deserves a dedicated pass later.
  - [ ] **Mobile collapse audit** — only index.html and listing.html have `.nav-links a:not(.nav-auth){display:none}` at `max-width:768px`. Others vary slightly. Separate item.

- [x] **Responsive breakpoints — search page narrow window fix** — DONE 2026-04-08. The desktop grid was using `repeat(auto-fill, minmax(400px, 1fr))` which caused horizontal clipping at narrow non-maximized window widths (the 260px sidebar + content area together couldn't fit a 400px column on windows < ~1100px). Added two stepped media queries: at 1100-1280px the minmax floor drops to 340px, at 900-1100px it drops to 280px with tighter padding. Plus `overflow-x: hidden` on `.directory-wrapper` and `min-width: 0` on `main` as defensive guards. The mobile breakpoint at 900px is untouched. Verified visually at 1024 / 1280 / 1440 / 1920 — no horizontal scrollbar at any width.
- [ ] Test partners page FAQ on mobile
- [ ] Test business dashboard sidebar collapse

- [x] **Search card sizing — feel premium at every viewport** — DONE 2026-04-08.
  Replaced fixed `repeat(N, 1fr)` columns with `repeat(auto-fill, minmax(400px, 1fr))`,
  capped `.card-stack` at `max-width: 1900px` (centered), and added `max-width: 480px`
  per card. Verified at 1280/1440/1920/2125 — cards now stay in the 400–480px sweet
  spot at every viewport, no more 4-column crowding at 1440px. Single fix in
  search.html responsive block (one media query, no JS changes).

- [x] **Interactive states — focus-visible site-wide** — DONE 2026-04-08. Audit found 0 occurrences of `:focus-visible` site-wide + 15 instances of `outline:none` (CLAUDE.md hard-rule violation, accessibility blocker). Fix: `nav-inject.js` (loaded on every page) now injects a global `<style id="zd-a11y-css">` block at the top of `<head>` with `:focus-visible` rules for `a`, `button`, `input`, `select`, `textarea`, `[role=button]`, and `[tabindex]`. Purple 3px ring (brand color) with 2px offset. Mouse-click focus suppressed via `:focus:not(:focus-visible){outline:none}`. One file edit, lands on all 12 pages.
  - [ ] Hover state audit — still need to verify every clickable element has a visible hover change. Not blocking launch.
  - [ ] Keyboard navigation test — tab order, skip-to-content link. Not blocking launch.
  - [ ] Flip cards on touch devices — manual test needed, not blocking.

- [x] **prefers-reduced-motion support** — DONE 2026-04-08. Same `nav-inject.js` a11y style block includes `@media (prefers-reduced-motion:reduce)` that kills animation-duration, animation-iteration-count, transition-duration, and scroll-behavior site-wide. CSS-only guard; GSAP ScrollTrigger tweens still fire but finish in 0.01ms. For full GSAP suppression the page scripts can also check `matchMedia("(prefers-reduced-motion)")` — follow-up if needed.
  - [ ] Verify video autoplay on mobile (iOS restrictions) — needs a real device test, not blocking launch.
  - [ ] Ensure GSAP animations don't cause layout shifts — separate perf audit.

---

## Search page demo polish (2026-04-08)

The user prepared 100 mockup partners for an influencer demo. First-look surfaced 6 issues; all fixed in a single bundle:

- [x] **Audit score `NaN` bug** — `getTierScore()` did `d.id * 7 + 13` assuming numeric ids. Supabase returns string UUIDs → `string × number = NaN`. Fixed by reading the real `audit_score` column from the businesses table first, falling back to a hash-of-id-string synthesis when missing. Sort order on the search grid is now meaningful (highest-audit-score businesses sit at the top).
- [x] **Tagline truncation algorithm broken** — produced ugly outputs like `"Аниматори Усмивка предлага професионални услуги в ..."`. The 60-char first-sentence threshold was too short; mock descriptions started with 65-char openers and fell through to a hard 50-char slice. Fixed: raised threshold to 90 chars + word-boundary snap on overflow. Same fix applied to mobile renderer. Both [search.html:1542-1564](search.html#L1542-L1564) and [search.html:2655-2670](search.html#L2655-L2670).
- [x] **Cards in same row have different heights (chaotic look)** — desktop grid was using auto-fill but each card sized to its own content. Fixed with `grid-auto-rows: 1fr` + `align-items: stretch` + `.zd-card { height: 100%; display: flex; flex-direction: column }` + body grows + bottom CTA sticks via `margin-top: auto`. Cards in any row now align perfectly. [search.html:528-560](search.html#L528-L560).
- [x] **Slow scrolling with 100+ cards rendered** — `render()` was rebuilding 450 KB of HTML strings on every filter/search/like/dismiss. Refactored with **lazy loading via IntersectionObserver**: only renders the first 30 cards initially, appends an invisible sentinel below, watches it with a single global IntersectionObserver, bumps `_visibleCount += 30` and re-renders when the user scrolls near the bottom. New `resetLazyAndRender()` helper resets back to 30 on filter/search/sort changes (NOT on dismiss/like/undo where the user expects to stay mid-scroll). 9 callsites in [search.html](search.html) updated to use the helper. **Verified: DOM contains 31 cards instead of 108 on first paint.** [search.html:1257-1284](search.html#L1257-L1284), [search.html:1622-1745](search.html#L1622-L1745).
- [x] **Window cut through cards when not maximized** — see "Responsive breakpoints" entry above in Priority 3. Stepped minmax breakpoints + overflow-x:hidden defensive guards.
- [x] **Mock descriptions were template-stamped** — every paid-tier mock said `"X предлага професионални услуги в категория Y..."`. Wrote [supabase/sample-100-descriptions-fix.sql](../supabase/sample-100-descriptions-fix.sql) — 8 category-specific UPDATE statements with short, varied, punchy openers (all under 90 chars first sentence, verified by awk pre-flight). Targets ONLY rows where `is_sample = true AND legacy_id LIKE 'mock-%'` so real partner data is provably untouched. Idempotent (plain UPDATE). User must run in Supabase SQL editor.
- **Phase 4 (animation cost reductions) deferred** — recommended in plan but not executed. With lazy loading capping the rendered card count at 30-90, the day-one impact is small. Worth applying if the site grows past ~200 cards or if scroll still feels janky on lower-end laptops. See plan file for the 3 specific recommendations.

---

## Tinder card refactor (2026-04-08, follow-up bundle)

After the demo polish bundle the user reviewed the populated search page and rejected the existing card design as "crowded". Iterated through 3 mockup rounds (`temporary screenshots/card-mockups.html` → `flip-comparison.html`) and landed on a Tinder-inspired 3D flip card system. Implemented end-to-end:

- [x] **5-tier system** (was 4) — added **Премиум** as the rare top-tier award (gold). Score range 150-250 (above Доверен). Added to `tierVals`, `tierRank`, `tierClassMap`, `allowedIconsByTier`, `tagLimits`, `tierColMap`, `TC_MAP`. Reserved for the rare partners — current mock dataset has 0 Премиум rows. The filter UI shows "Премиум" so users can filter for it once any partner is awarded the tier.
- [x] **Tinder card visual** — photo full-bleed, dark gradient at the bottom, name + city + rating + tagline + chips overlay on the gradient, glass-morphism CTAs (Профил + dynamic primary). Replaces the old white-body card with the photo-as-background pattern. [search.html:255-700](search.html#L255-L700).
- [x] **3D flip mechanism** — whole card is tappable. Rotates 180° via `rotateY(180deg)` on the inner `.zd-flipper`. Critical CSS gotcha: NO `overflow:hidden` on `.zd-card` or `.zd-flipper` (would create a stacking context and break `transform-style:preserve-3d`). Faces clip themselves via `border-radius` + `overflow:hidden` on `.zd-face`. Tap-to-flip is detected in `initSwipe()` by `Math.abs(currentX) < 6` on release (large drags trigger like/dismiss instead).
- [x] **Tier-themed back face** — light background with tier wash (white + purple for Доверен, white + mint for Проверен, white + gold for Премиум, neutral gray for Стандартен). Square logo top-left + business name + sub line + sections (За нас, Работно време, Адрес, Контакти). Free tier does NOT render a back face — front-only.
- [x] **Discoverability** — `.zd-flip-wobble` keyframe runs **twice on first load** (1s delay, ~7s total duration) to hint that the card has a back side. Hover tilts the card via `rotateY(-7deg) rotateX(2deg)`. A pulsing **`↻` arrow pill** sits below the audit score badge, top-right. Once the user touches ANY card (`_anyCardTouched` global flag), the wobble stops on every card permanently for the session.
- [x] **Free tier (Безплатен) has NO flip** — `.zd-card--free` overrides `cursor:default`, `perspective:none`, `animation:none`, hides the flip hint, desaturates the photo via `filter:saturate(.55)`, and `initSwipe()` early-exits before binding the click handler. Free partners get directory presence with phone+email contact only.
- [x] **Google Maps icon** in the back-face socials row — appended at the end of every paid-tier card's contacts row. Uses Google's brand colors (4-color radial gradient) for instant recognition. Links to `https://www.google.com/maps/search/?api=1&query={lat},{lng}` if coordinates exist, otherwise falls back to address+city query. Same icon also appears on the mobile front card via `_buildSocialsM(d)` since there's no embedded map anywhere on the cards.
- [x] **Photo fallback** via `getCardPhoto(d)` — if `gallery_urls` is empty, returns a category-default Unsplash photo (8 categories, one default each). Logo fallback via `getCardLogo(d)` — if no real logo, uses `placehold.co/144x144/{tierColor}/white?text={firstLetter}`. Eliminates the old M004 letter placeholder boxes that dominated empty cards.
- [x] **Tutorial v2** — added a 3rd `tutorial-demo--flip` step ("Натисни картата = Детайли") next to the existing two swipe demos. Animation rotates the card ghost on a 2.5s loop. Bumped localStorage flag from `zd_tutorial_seen` to `zd_tutorial_seen_v2` so existing users see the new tutorial once. [search.html:1066-1085](search.html#L1066-L1085).
- [x] **Mobile renderer (cf-/tier- namespace)** — added `.tier-premium` rules with the same animated gold border, badge, CTA gradient. Updated `_buildSocialsM(d)` to append the Google Maps pin. Updated `_buildCTAsM(d)` and `isExpandable` check to include Премиум alongside Доверен/Проверен. Mobile already had its own `flipCard()` / `flipBack()` mechanism so the back panel works for Премиум automatically.
- [x] **Verification** — screenshot regression at 1024 / 1280 / 1440 / 1920 desktop + 390 mobile. All widths render the new card structure correctly. Доверен (gold-shimmer purple) + Проверен (mint) tiers visible in the screenshots; Free dashed-border tier rendered correctly. Smoke test caught one bug during refactor (`isFree is not defined` — fixed). Lazy load + IntersectionObserver from previous bundle still works (verified by DOM dump).

**Reference mockup kept for future polish:** [temporary screenshots/flip-comparison.html](../temporary%20screenshots/flip-comparison.html) — interactive 5-tier comparison page with all front + back faces. Source of truth for any future card style tweaks.

**Deferred to a later bundle (Phase 2 of the plan):** Ad card render path. The user explicitly chose to hold ad monetization for later. Plan documents the full implementation (~2-3 hours when scheduled): banner-only ad cards with mandatory `Реклама` ribbon, `ads` table in Supabase, slot insertion every 8th card via `injectAdSlots(activeCards)`, frequency capping via localStorage, no targeting/billing/dashboard yet. Bulgarian advertising law + EU DSA compliance noted in the plan.

---

## Real review counts on search cards (2026-04-09)

The card ratings on the search page used to be `Math.random()` per render, which meant refreshing the page changed the numbers — same business showed 4.2 (87) one moment and 4.8 (12) the next. An influencer recording the demo would catch this in <30 seconds. Fixed end-to-end in a small follow-up bundle:

- [x] **`getCardRating(d)` helper with deterministic fallback** — replaces the `Math.random()` calls in `buildCardHTML()` and `buildStackCard()`. Returns `{ avg, count, real }` for any business. Real path reads from `_ratingsCache`. Fallback path hashes the business id (UUID-safe via charCodeAt loop) into a stable avg between 4.0 and 4.9 plus a tier-boosted count (Премиум +80, Доверен +50, Проверен +25, Стандартен +10, Безплатен +0). The numbers no longer change between refreshes. Same fallback shape as the listing page so the directory feels consistent.
- [x] **`loadAllCardRatings()` — single bulk fetch** — fires once after `init()` loads businesses. One `select('business_id, stars').eq('approved', true)` query against the `reviews` table, aggregated client-side into a `Map<id, {avg, count}>`. No N+1, no PostgREST view, no RPC needed. With ~100 businesses and likely <500 demo reviews this is a single small round-trip.
- [x] **`patchVisibleCardRatings()` — in-place patcher** — the second the bulk fetch resolves, surgically updates the rendered cards' `.zd-rating .num` and `.zd-rating .cnt` text nodes (and the mobile `.cf-hero-rating` equivalents) WITHOUT re-rendering. Keeps scroll position, doesn't disturb the IntersectionObserver lazy-load sentinel, doesn't reset the user-touched wobble flag. Also called from `render()` itself so cards rendered AFTER the cache loaded (lazy-load batch 2+, filter changes, etc.) get patched on next render.
- [x] **"Оцени!" nudge stays smart** — only shows when (a) no real reviews exist for that business AND (b) the deterministic fallback count is artificially low (<10). Real popular businesses never get a "Rate me!" nudge.
- [x] **Verified deterministic** — two screenshots taken back-to-back at 1440px show identical ratings on the same cards. Before the fix, the same screenshot pass would have produced different numbers.

**Files touched:** [search.html:1532-1632](search.html#L1532-L1632) (helpers), [search.html:1885](search.html#L1885) (desktop builder), [search.html:3190](search.html#L3190) (mobile builder), [search.html:2208](search.html#L2208) (render() patch call), [search.html:2480, 2495](search.html#L2480) (init() loader call).

**What's NOT in this bundle:**
- The "rating distribution histogram" some directories show on the listing page — already covered by `loadRealReviews()` in [listing.html](listing.html), separate concern
- Partner-side review moderation UI in business-dashboard — separate bundle

---

## Wobble + sync polish (2026-04-09)

Two small follow-ups after the real-ratings bundle:

- [x] **Wobble fix** — the load-time `flip-wobble` animation was running on EVERY rendered card simultaneously (~7s × 30+ cards). Visually overwhelming and a measurable GPU cost. Replaced with a hover-triggered one-shot wobble: now only the card the cursor is over wobbles, and only once per hover-in. The static `rotateY(-7deg) rotateX(2deg)` tilt is the resting hover state — the wobble plays once on top of it then settles into the tilt. [search.html:307-326](search.html#L307-L326). Removed the load-side `_anyCardTouched` requirement for the wobble (still used by the flip-hint pulse).
- [x] **Continuous like/dismiss sync** — see Priority 5.4 line above for the full description. Closes the auth integration loop: new likes/dismisses while logged in now go to Supabase in real time, not just on signup.

## Priority 4: SEO & Production Readiness

- [x] **Meta tags on every page** — DONE 2026-04-08. All 12 HTML pages updated:
  - `<html lang="bg">` ✓ (was already present)
  - `<meta name="description">` ✓ (added to search.html and listing.html which had none; kept existing on others)
  - Canonical link → `https://zadeteto.com/...` ✓
  - Open Graph (og:type, og:site_name, og:locale, og:url, og:title, og:description, og:image, og:image:width/height/alt) ✓
  - Twitter Card (summary_large_image) ✓
  - Favicon (`brand_assets/zadeteto-app-icon.svg`) ✓
  - `business-login.html` and `business-dashboard.html` flagged `noindex, nofollow` (app surfaces, not marketing)
  - OG image generated: `brand_assets/og-image.svg` (editable source) + `og-image.png` (1200×630, what's actually shipped to og:image)

- [ ] **Structured data**
  - JSON-LD for local business directory
  - Breadcrumb markup on inner pages

- [x] **Performance bundle (partial)** — DONE 2026-04-08:
  - [x] **Lazy load images** — DONE. Audit found most JS-rendered card images already had `loading="lazy"`. Added it to the OAuth provider icons (Google/Facebook) in the auth modals on listing.html and search.html, and to the sample reviewer avatar in business-dashboard.html. Nav logos correctly stay eager (above-the-fold = LCP).
  - [x] **Self-host fonts** — DONE. Replaced Google Fonts CDN with local woff2 files in `brand_assets/fonts/` (6 files, 213 KB total). New `fonts.css` declares Inter (4 subsets: latin, latin-ext, cyrillic, cyrillic-ext) AND DM Serif Display (2 latin subsets). All 12 production HTML pages now load `brand_assets/fonts/fonts.css` instead of `fonts.googleapis.com`. **GDPR fix**: Google Fonts CDN sends visitor IPs to Google — a 2022 German court ruling found this violates GDPR for sites without consent. Self-hosting eliminates the risk for our EU audience.
  - [x] **DISCOVERED: DM Sans has NO Cyrillic glyphs** — verified empirically with a width-comparison test in headless Chrome. The previous setup was silently falling back to system fonts (Segoe UI / San Francisco / Roboto) for all Bulgarian text, which is ~95% of the site. **Switched body font to Inter** (full Cyrillic + same modern geometric-sans aesthetic). `fonts.css` registers Inter under BOTH the `'Inter'` family name AND the `'DM Sans'` family name as an alias, so all existing inline `font-family: 'DM Sans'` rules transparently start using Inter without needing to edit any CSS.
  - [x] **Fixed search.html Playfair Display bug** — search.html was importing `Playfair Display` instead of `DM Serif Display` for the mobile-mode card heading. Replaced the `--zd-display` CSS variable with `'DM Serif Display','Inter',serif`.
  - [x] **Hero video poster** — captured a frame from `hero-video.mp4` at the 1.5s mark via headless Chrome → saved as `brand_assets/hero-poster.png` (1MB, mom + daughter playing with blocks). Added `poster="..."` attribute to both `<video>` tags in index.html. Browsers now show the still frame instantly while the video downloads → no more "broken hero" first-paint impression on slow connections.
  - [ ] **Compress hero videos with ffmpeg** — NOT DONE. ffmpeg is not installed on this machine and the Antigravity sandbox can't install it. Wrote `docs/video-compression.md` with exact one-command ffmpeg recipes (CRF 28 H.264, faststart flag, audio strip → expected 80-86% size reduction). User runs locally when ready. Combined videos are currently 9.7 MB; after compression should be ~1.8 MB.
  - [ ] **DM Serif Display has NO Cyrillic either** — Bulgarian headings (h1/h2/h3) currently fall back to the system serif (Times New Roman, Georgia). Not blocking launch but worth a separate brand decision: replace with Playfair Display or Cormorant which both ship full Cyrillic. Tracked as a separate item below.

- [x] **Replaced DM Serif Display with PT Serif** — DONE 2026-04-08. PT Serif is a more editorial / readable serif (less dramatic than DM Serif Display, but ships full Latin + Cyrillic + Latin-Ext + Cyrillic-Ext for both regular and bold weights). 8 woff2 files added to `brand_assets/fonts/` (204 KB total). `fonts.css` registers PT Serif under both `'PT Serif'` AND `'DM Serif Display'` (as alias) so all existing inline `font-family: 'DM Serif Display', serif` declarations transparently start using PT Serif. Old `dmserifdisplay-*.woff2` files deleted. Verified visually on pricing.html, privacy.html, index.html hero, and partners.html — Bulgarian headings (h1/h2/h3) now render in PT Serif Bold instead of system serif fallback. Slight visual change: PT Serif characters are marginally wider than the old system serif, so partners.html headline now wraps to 4 lines instead of 3. Easy fix if you want it: bump that headline's font-size down 2-4px.

---

## Priority 5: Backend — Supabase Integration

> **Decision (2026-04-07):** Backend will be **Supabase** (Postgres + Auth + Storage
> + Realtime). Free tier to start (500MB DB, 50K MAU, EU/Frankfurt region for GDPR).
> Upgrade to Pro ($25/mo) only when limits hit. Replaces the current github-gist
> JSON data source and the localStorage-only state for likes/dismisses/reviews.

### 5.1 Supabase setup (user action)
- [x] Create Supabase account — DONE
- [x] Create project `erfndxmqitavqkfeohxh` (`https://erfndxmqitavqkfeohxh.supabase.co`) — DONE 2026-04-08
- [x] Send Claude: Project URL + anon (public) API key — DONE 2026-04-08, embedded in `supabase-init.js`
- [x] **Apply migration 0001_initial_schema.sql** — DONE 2026-04-08
- [x] **Apply migration 0002_fix_anon_insert_policies.sql** — DONE 2026-04-08 (added explicit `TO anon, authenticated` role binding to all anon-insertable form table policies, plus matching table-level GRANTs)
- [ ] Save DB password in password manager (cannot be easily reset)
- [ ] (Optional) Create separate `zadeteto-staging` project for testing
- [ ] **TODO: Grant yourself admin** so you can read submissions — see [docs/supabase-setup.md](supabase-setup.md) Step 2. (5.1 is otherwise complete; this is the last user-action step before you can read form submissions in the dashboard.)

### 5.2 Database schema (Claude work)
- [x] **SQL migration written and ready to apply** — DONE 2026-04-08. File: [supabase/migrations/0001_initial_schema.sql](../supabase/migrations/0001_initial_schema.sql). 10 tables (`businesses`, `parents`, `business_owners`, `liked_businesses`, `dismissed_businesses`, `reviews`, `feedback_log`, `partner_applications`, `contact_messages`, `reports`), 3 enums (`business_tier`, `application_status`, `report_status`), all RLS policies, all triggers (auto-slug, auto-coords, auto-touch updated_at, auto-create parents row on signup), `is_admin()` helper function, PostGIS geography column for "Близо до мен", indexes for the hot query paths.
- [x] **Row Level Security policies for every table** — DONE in same migration. Anon read on published businesses + approved reviews; admin-only read on contact_messages/reports/feedback_log/partner_applications; per-user RLS on liked/dismissed/parents.
- [ ] **User must apply migration via Supabase Dashboard** (5 min, see [supabase-setup.md](supabase-setup.md) Step 1)
- [ ] User said start empty — no seed script needed. (Test data via SQL editor as shown in setup doc)
- [ ] Set up daily DB keep-alive ping to prevent free-tier 7-day pause (separate small task, not blocking launch)

### 5.3 Auth integration
- [x] **Decide auth methods** — DONE 2026-04-08. Email magic link + email/password (partners) + Google/Facebook/LinkedIn OAuth (wired in code, providers enabled later in dashboard).
- [x] **Wire `auth-modal` (parent login on search.html) to real Supabase auth** — DONE 2026-04-08. `parentSendMagicLink()` calls `ZdSupabase.auth.signInWithOtp({ email })`, OTP step replaced with "check your email" message. Google/Facebook OAuth buttons wired via `parentSignInOAuth(provider)` — return graceful "method not enabled" error until you turn them on in the dashboard.
- [x] **Wire `business-login.html` to real Supabase auth** — DONE 2026-04-08. Dual-mode tabs: "С парола" (signInWithPassword) and "С линк по имейл" (signInWithOtp with `shouldCreateUser: false` so non-partners can't signup here). "Forgot password" link calls `auth.resetPasswordForEmail`. Auto-redirect to dashboard if user is already logged in. Biometric button kept as mock (separate WebAuthn bundle later).
- [x] **Wire `partners.html` signup** — DONE 2026-04-08. Application form now also auto-creates the auth user via `signUp()` with a throwaway password, then explicitly sends a magic link to the partner's inbox. Partner row in `partner_applications` is created regardless (so you can review even if signUp fails). Onboarding flow: partner submits form → app created with status='pending' → auth user created → magic link sent → partner clicks link → lands in business-dashboard. Business listing stays unpublished until you flip `published=true` after review.
- [x] **Add session gate to `business-dashboard.html`** — DONE 2026-04-08. New auth gate IIFE redirects unauthenticated visitors to `business-login.html`. Listens for sign-out events from other tabs. Exposes `window.ZdCurrentUser` for dashboard code to use.
- [x] **Add anonymous → logged-in localStorage migration** — DONE 2026-04-08. `_migrateLocalStateToSupabase(userId)` runs on `SIGNED_IN` event, bulk-upserts liked_businesses + dismissed_businesses for the new parent. Idempotent via composite PK. Skips legacy gist IDs (only valid UUIDs migrate, since the gist data hasn't been imported to businesses table yet).
- [ ] **TODO (your action, separate session):** Create Google OAuth app, give Claude client_id + client_secret, enable in Supabase Dashboard
- [ ] **TODO (your action, separate session):** Create Facebook OAuth app, enable in Supabase Dashboard
- [ ] **TODO (your action, separate session):** Create LinkedIn OAuth app, enable in Supabase Dashboard
- [ ] **TODO (separate bundle):** Localize Supabase email templates from English to Bulgarian (Dashboard → Authentication → Email Templates)

### 5.4 Frontend integration (Claude work)
- [x] **Add supabase-js client via CDN to all pages that need it** — DONE 2026-04-08. New file `supabase-init.js` loads `@supabase/supabase-js@2` from jsDelivr CDN, exposes `window.ZdSupabase`, fires `zd-supabase-ready` event when ready. Loaded by: contacts.html, partners.html, report.html, search.html, listing.html.
- [x] **Replace gist fetch in search.html with Supabase query** — DONE 2026-04-08. New flow: 1) try Supabase if loaded, 2) wait briefly for `zd-supabase-ready` event if it isn't, 3) fall back to `companyData_v4` localStorage cache, 4) empty state. Field aliasing layer (`_aliasBusinessRow`) maps `age_groups` → `ageGroups` so the rendering code stays untouched. Same swap applied to listing.html with direct id/slug `eq()` filters instead of full table scan.
- [x] **Wire form submissions: partners.html, contacts.html, report.html, feedback wizards** — DONE 2026-04-08 (Supabase). All 4 forms POST through `ZdApi.submitForm(endpoint, payload)` defined in `api-stub.js`. `_doSubmit` now calls `ZdSupabase.from(endpoint).insert(payload).select('id').single()`. On network failure / RLS rejection / schema mismatch, persists to `localStorage` (key `zd_pending_submissions`) AND still resolves successfully so the user sees the success state — offline-first by design. Field key aliasing handles camelCase→snake_case (`otherText` → `other_text`, strips client-side `timestamp` since DB has `created_at` default). Endpoints: `contact_messages`, `reports`, `partner_applications`, `feedback_log`, `reviews`. Recovery: `ZdApi.getPending()` in DevTools.
- [x] **Sync `likedIds`/`dismissedIds` to `liked_businesses`/`dismissed_businesses` on signup** — DONE 2026-04-08 (one-shot migration via `_migrateLocalStateToSupabase` on SIGNED_IN event).
- [x] **Continuous like/dismiss/undo sync while logged in** — DONE 2026-04-09. New `_syncLikeDismissToSupabase(businessId, action)` helper in [search.html](search.html) wired into all 6 entry points: desktop `likeCard()` / `dismissCard()` / `undoDismiss()` and mobile `doLike()` / `doDismiss()` / `undoLast()`. Tracks the current user via a module-level `_currentUserId` updated by `updateAuthUI(session)`. Anonymous users no-op (UUID guard + null check). Fire-and-forget — never blocks the UI. Errors logged to console as `[zd-sync]`. Upsert uses the existing `parent_id,business_id` composite PK so re-clicking the same like is idempotent.
- [x] **Wire review system (mobile review sheet + desktop feedback wizard) to `reviews` table** — DONE 2026-04-08 (stub layer). Both `fbSubmit`, `mfbSubmit`, and `submitReview` in search.html now also fire `ZdApi.submitForm` alongside their existing localStorage writes. Offline-first: localStorage is the source of truth, backend sync is fire-and-forget so the user is never blocked by network failures.
- [ ] Wire business-dashboard.html to read real data for the logged-in owner
- [ ] Add real-time updates for business owners (new reviews, messages)

### 5.5 Storage (images)
- [ ] Create Supabase Storage bucket `business-logos` (public read)
- [ ] Create bucket `business-photos` (public read, owner write)
- [ ] Migrate existing `logo` URLs from external CDN to Supabase Storage
- [ ] Set image transformation policies (auto-resize for thumbnails)

### 5.6 Compliance (depends on Priority 1.4)
- [x] **Update Privacy Policy to list Supabase as data processor** — DONE 2026-04-08. Added Supabase Inc. (eu-central-1 / Frankfurt) and Contentsquare SAS (France) to the data processors list in privacy.html section 6, with links to their respective privacy policies and DPAs. Both are GDPR-compliant by region.
- [ ] Document data retention policy (how long we keep dismissed/feedback data)
- [ ] Add account deletion flow (GDPR right to erasure)
- [ ] Add data export flow (GDPR right to portability)
- [x] **Wire Contentsquare (UXA session replay) consent-gated** — DONE 2026-04-08. New `analytics-loader.js` checks `ZdConsent.has('analytics')` on page load. If true, dynamically injects `<script src="https://t.contentsquare.net/uxa/6dc8ffe946b20.js">`. If false, does nothing. Listens for `zd-consent-change` event from `cookie-banner.js` so the moment a user clicks "Accept all" the script loads without a page reload. Idempotent — re-firing the event does not inject duplicate scripts. Patched `cookie-banner.js` saveConsent() to dispatch the event and added a small `window.ZdConsent` API (`get()`, `has(category)`) for clean third-party access. All 12 production HTML pages load `analytics-loader.js` after `cookie-banner.js`. End-to-end tested with 10/10 PASS on consent gate scenarios.
- [ ] **TODO: Wire Umami / Plausible / Cloudflare Web Analytics** — quantitative analytics (visitor counts, conversion rates) deferred. Pattern is the same: add a `_loadUmami()` function inside `analytics-loader.js`, call it from `_loadIfConsented()` under the same `analytics: true` gate. ~5 min when you pick a provider and have the script tag.

### 5.7 Pre-Pro upgrade triggers (when to start paying $25/mo)
- DB approaches 500MB (≈50K businesses)
- MAU approaches 50K
- Need custom domain for API (api.zadeteto.bg)
- Need daily backups instead of 7-day rollback
