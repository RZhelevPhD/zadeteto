# ZaDeteto GHL Build — Phase 1 Files

**Generated: 2026-05-13 · Version 1.0**

This package contains everything needed to ship the Bulgarian/tier-locked
GHL experience for ZaDeteto partners.

## What's inside

| File | What it is | Where it goes |
|---|---|---|
| `agency-custom.css` | Custom CSS (~470 lines) | Paste into GHL Settings → Company → Custom CSS (Agency) |
| `agency-custom.js` | Custom JavaScript (~440 lines) | Paste into GHL Settings → Company → Custom JavaScript (Agency) |
| `ghl-locations.json` | Partner whitelist | **Lives at `public_html/ghl-locations.json` (one level up)** — served as `https://zadeteto.com/ghl-locations.json`. This `ghl/` folder is the docs/master copy only; the live file is at deploy root. |
| `SOP-onboarding.md` | Step-by-step onboarding manual | Reference doc, save in repo |
| `README.md` | This file | — |

## Recommended order of operations

### Phase A — Set up infrastructure (1–2 hours)

1. Deploy `ghl-locations.json` to `zadeteto.com/ghl-locations.json`
   - The file lives at `public_html/ghl-locations.json` (deploy root); the master copy in this `ghl/` folder is for reference only.
   - CORS + cache headers are configured in `public_html/_headers` (Cloudflare Pages picks it up automatically): `Access-Control-Allow-Origin: *`, `Cache-Control: public, max-age=60`.
   - After deploy, verify: `curl -I https://zadeteto.com/ghl-locations.json` returns the headers above.
2. Paste `agency-custom.css` into GHL Settings → Company → Custom CSS
3. Paste `agency-custom.js` into GHL Settings → Company → Custom JavaScript
4. Save both. The CSS and JS take effect immediately on next page load.

### Phase B — Test with the template sub-account (30 min)

The template sub-account `ZCexGFW5RHvLTGxtLmtb` is already in the whitelist
as `premium` with `ai_agents` activated, so when you open it, you should see:

- Sidebar in Bulgarian
- All tier items unlocked (no padlocks except potentially for `unlimited_sms`)
- AI Агенти visible without ✦ badge (it's activated)
- "Начало" link at top
- "Помощ и активиране" link at bottom

If something is off, see Troubleshooting in `SOP-onboarding.md`.

### Phase C — Test tier downgrade (10 min)

To verify the lock logic works:

1. Edit `ghl-locations.json` — change the template's `tier` to `verified`
2. Save, push to zadeteto.com
3. Hard refresh GHL (Ctrl+Shift+R)
4. You should see: Calendars, Opportunities, Automation, Sites, etc. all locked with 🔒
5. Click one — modal should open
6. Set tier back to `premium` when done testing

### Phase D — Custom Menu Links (manual, in GHL UI)

The CSS hides `sb_dashboard` and `sb_launchpad`. You need to add the two
custom links manually:

1. GHL Agency → Settings → **Custom Menu Links** → Create New
2. **Link 1: Начало**
   - Title: `Начало`
   - URL: `https://zadeteto.com/dashboard?location_id={{location.id}}&user_name={{user.first_name}}`
   - Icon: 🏠 (or pick a house icon)
   - Open in: **Embedded Page (iFrame)**
   - Show On: **Sub-Account sidebar**
   - Assigned to: leave blank (= all subaccounts) or specifically the ZaDeteto ones
   - Role: All
3. **Link 2: Помощ и активиране**
   - Title: `Помощ и активиране`
   - URL: `https://zadeteto.com/crm-upgrade?location_id={{location.id}}`
   - Icon: ❓
   - Open in: **Embedded Page (iFrame)**
   - Show On: **Sub-Account sidebar**
   - Role: All
4. Drag "Начало" to the top of the sidebar
5. Drag "Помощ и активиране" to the bottom

### Phase E — Build the two zadeteto.com pages (next phase)

These two pages are NOT in this package — they'll be built next:

- `zadeteto.com/dashboard` — Welcome dashboard (refactored from Claude Design output)
- `zadeteto.com/crm-upgrade` — Upgrade explainer (refactored from Claude Design output)

Until these are built, the Custom Menu Links will 404. The padlock modal
CTA will also lead to a 404. So for the first end-to-end test, you'll need
these pages live.

### Phase F — Build the snapshot

Once all of the above is verified working in the template sub-account:

1. Set up the rest of the template sub-account:
   - Custom Fields on Contact (parent_child_age, parent_city, lead_source, specialist_interest)
   - Default workflows (Welcome lead, Booking confirmation, Follow-up after 3 days)
   - Default Bulgarian SMS/email templates
   - Default calendar ("Безплатна 15-минутна консултация")
   - Default forms ("Заявка за информация")
2. GHL Agency → Account Snapshots → **Create**
3. Name: `ZaDeteto Partner v1.0`
4. Source: ZaDeteto Template
5. Include: everything except contacts/conversations

### Phase G — Onboard first real partner

Follow `SOP-onboarding.md`. Target: under 5 minutes per partner.

## Known limitations & gotchas

1. **GHL CSS classes are partially obfuscated.** This package uses `id` and
   `meta` attributes (stable) for selectors. If GHL changes those, the
   diagnostic snippet in the SOP will tell you what to update.

2. **The "Action Required: Messaging and Voice services" banner is hidden
   by CSS.** This is intentional — partners shouldn't see it. But it means
   if Messaging/Voice IS legitimately broken for a sub-account, you won't
   see the warning either. Check Conversations functionality manually
   during onboarding.

3. **AI Agents item ID has a space** (`sb_AI Agents`). This is GHL's bug,
   not ours. The JS handles it via attribute selector. Don't try to fix it.

4. **Manrope font fallback chain** includes system fonts, so if Google
   Fonts is slow/blocked, text still renders cleanly.

5. **The whitelist JSON has a 60s cache TTL** in sessionStorage. After
   changing a partner's tier, they may need to wait up to 60 seconds OR
   close all GHL tabs and reopen.

6. **Премиум divider visibility logic** — the divider only appears when at
   least one premium-only feature is locked. A Премиум-tier partner won't
   see the divider (because nothing below it is locked). That's intentional.

7. **The modal close button uses ✕ (Unicode multiplication sign)** rather
   than an SVG. If the partner's browser doesn't render it well, swap it
   for an inline SVG in the buildModal() function.

## Versioning

- `agency-custom.css` — v1.0
- `agency-custom.js` — v1.0
- `ghl-locations.json` schema — v1.0

When making changes:
- Patch fixes (typos, copy edits): no version bump
- New features (new tier, new addon): bump JSON `version` to 1.1
- Breaking changes (e.g., renaming `tier` to `plan`): bump JSON `version` to 2.0 and the JS must handle both
