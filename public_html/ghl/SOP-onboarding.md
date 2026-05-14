# ZaDeteto GHL Partner Onboarding — SOP

**Version 1.0 · Last updated 2026-05-13**

Target time per partner: **under 5 minutes**

---

## Prerequisites (one-time, do these once)

1. ✅ `ZaDeteto Partner v1.0` snapshot exists in your GHL Agency Snapshots
2. ✅ Agency Custom CSS installed (Settings → Company → Custom CSS)
3. ✅ Agency Custom JS installed (Settings → Company → Custom JavaScript)
4. ✅ Custom Menu Links created (Settings → Custom Menu Links):
   - **Начало** → `https://zadeteto.com/dashboard?location_id={{location.id}}&user_name={{user.first_name}}`
   - **Помощ и активиране** → `https://zadeteto.com/crm-upgrade?location_id={{location.id}}`
5. ✅ `ghl-locations.json` deployed at `https://zadeteto.com/ghl-locations.json` (with `Access-Control-Allow-Origin: *` header)

---

## For each new partner

### STEP 1 — Create sub-account (2 min)

1. GHL Agency Dashboard → Sub-Accounts → **+ Create**
2. Apply snapshot: **ZaDeteto Partner v1.0**
3. Fields:
   - **Business Name:** Partner business name in Cyrillic (e.g., "Логопед Иванова")
   - **Timezone:** Europe/Sofia
   - **Currency:** BGN
   - **Email:** Partner's contact email
4. Click Create
5. Copy the Location ID from the URL bar
   (Pattern: `/v2/location/XXXXXXXXXXXX/...` — copy the X part)

### STEP 2 — Add to whitelist (1 min)

1. Open repo: `zadeteto-site/ghl-locations.json`
2. Add new entry inside `"locations": { ... }`:
   ```json
   "PASTE_LOCATION_ID_HERE": {
     "name": "Партньор име на български",
     "tier": "verified",
     "addons": []
   }
   ```
3. Set `tier` based on what they paid:
   - **`"verified"`** — Проверен tier (Conversations + Contacts)
   - **`"trusted"`** — Доверен tier (+ Calendars + Opportunities)
   - **`"premium"`** — Премиум tier (everything)
4. Set `addons` based on add-ons they purchased:
   - `["ai_agents"]` if they bought AI Agents
   - `[]` (empty) for most partners
5. Commit and push to production
6. Wait ~60 seconds for CDN cache

### STEP 3 — Smoke test (1 min)

1. Log into the new sub-account
2. Verify checklist:
   - [ ] Sidebar shows Bulgarian text (Разговори, Контакти, etc.)
   - [ ] Free items (per tier) are unlocked, no padlock
   - [ ] Locked items show gold padlock 🔒
   - [ ] AI Агенти shows purple sparkle ✦ (if not activated)
   - [ ] "Премиум" divider visible above locked premium items
   - [ ] "Начало" custom link at top of sidebar (loads dashboard)
   - [ ] "Помощ и активиране" at bottom of sidebar
   - [ ] Clicking a locked item opens the upgrade modal
   - [ ] Modal "Обнови до X" button opens zadeteto.com/crm-upgrade
   - [ ] AI Агенти modal opens mailto with prefilled subject

### STEP 4 — Partner handoff (1 min)

1. Inside the sub-account: Settings → Team → **+ Add User**
2. Create user account for the partner:
   - Role: **User** (not Admin — keeps them out of settings)
   - Email: partner's login email
3. Send the welcome email with login credentials
4. Optional: schedule onboarding call (15 min)

---

## Common operations

### To upgrade a partner's tier later

1. Open `ghl-locations.json`
2. Change their `tier` field: `"verified"` → `"trusted"` or `"premium"`
3. Commit, push
4. Partner refreshes their browser — new items unlock immediately

### To activate AI Agents for a partner

1. Open `ghl-locations.json`
2. Add `"ai_agents"` to their `addons` array:
   ```json
   "addons": ["ai_agents"]
   ```
3. Commit, push
4. Partner refreshes — purple sparkle disappears from AI Agents, item is unlocked

### To deactivate a feature

1. Same as above but **remove** the value
   (Downgrade tier OR remove from addons)

### To remove a partner entirely

1. Delete their entry from `locations`
2. Commit, push
3. Their GHL sub-account stays alive but reverts to default English GHL
4. To fully offboard, also pause/delete the sub-account in GHL

---

## Troubleshooting

### "The sidebar is still in English after I added them to the whitelist"

- Check the Location ID was copied correctly (no spaces, exact case)
- Hard refresh the browser (Ctrl+Shift+R) — sessionStorage cache holds 60s
- Open DevTools Console — look for `[ZaDeteto] Activated for ...` message
- Check Network tab — `ghl-locations.json` should return 200 OK with CORS headers

### "Padlocks disappeared after a GHL update"

- GHL changed sidebar IDs or markup
- Quick fix: run the diagnostic snippet in Console:
  ```javascript
  [...document.querySelectorAll('[id^="sb_"]')].map(el => ({
    id: el.id, meta: el.getAttribute('meta'), text: el.querySelector('.nav-title')?.textContent?.trim()
  }))
  ```
- Compare output to the expected list in `agency-custom.js` (TRANSLATIONS object)
- If `meta` attribute values changed, update the JS accordingly

### "The 'Начало' or 'Помощ и активиране' links open in a new tab instead of iframe"

- The destination page is sending `X-Frame-Options: deny` or a strict `Content-Security-Policy: frame-ancestors`
- Fix on zadeteto.com side: ensure `/dashboard` and `/crm-upgrade` allow embedding from `app.gohighlevel.com`

### "Modal doesn't open when I click a locked item"

- Check Console for JS errors
- Verify the click handler is bound: `document.body.hasAttribute('data-zd-clicks-bound')` should return `true`
- The click handler uses capture-phase listener — if a GHL update intercepts clicks first, may need to debug

---

## File inventory

| File | Location | Purpose |
|---|---|---|
| `agency-custom.css` | GHL Settings → Company → Custom CSS | Visual styling, Manrope font, padlock animations, modal styling |
| `agency-custom.js` | GHL Settings → Company → Custom JavaScript | Whitelist fetch, Bulgarian translation, lock logic, modal injection |
| `ghl-locations.json` | `zadeteto.com/ghl-locations.json` | Source of truth for partner tiers and add-ons |
| `zadeteto.com/dashboard` | Web page, brand-styled, iframe-friendly | Welcome dashboard partners see when they log in |
| `zadeteto.com/crm-upgrade` | Web page, brand-styled | Upgrade explainer; deep-linked from modal `?feature=X` |

---

## Phase 1 launch checklist

Before onboarding the first real partner:

- [ ] Agency CSS pasted into GHL Settings, saved
- [ ] Agency JS pasted into GHL Settings, saved
- [ ] `ghl-locations.json` deployed with template entries removed, CORS header set
- [ ] `zadeteto.com/dashboard` page live and tested in iframe
- [ ] `zadeteto.com/crm-upgrade` page live, accepts `?feature=X` param
- [ ] Custom Menu Links created (Начало + Помощ и активиране)
- [ ] Template sub-account built with all custom fields, workflows, calendars, forms
- [ ] Snapshot created from template sub-account (`ZaDeteto Partner v1.0`)
- [ ] End-to-end test: created throwaway sub-account from snapshot, added to whitelist, verified all sidebar states + modals work

---

**Questions or issues?** partner@zadeteto.com
