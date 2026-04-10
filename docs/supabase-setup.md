# ZaDeteto Supabase setup guide

> Last updated: 2026-04-08
>
> Project: **erfndxmqitavqkfeohxh** (`https://erfndxmqitavqkfeohxh.supabase.co`)
> Region: should be `eu-central-1` (Frankfurt) for GDPR
> Plan: Free tier

This guide walks you through everything that has to happen ON the Supabase
side. The frontend code is already wired — once these steps are done, every
form starts persisting to Postgres and the search page starts reading from
Postgres.

---

## Step 1 — Apply the schema migration

1. Open the [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. In the left sidebar click **SQL Editor** → **New query**.
3. Open the file `supabase/migrations/0001_initial_schema.sql` from this repo.
4. Paste the entire contents into the SQL editor.
5. Click **Run** (bottom right). Should complete in 2–5 seconds.
6. Verify in the **Table Editor** (left sidebar): you should see 10 tables:
   - `businesses`
   - `parents`
   - `business_owners`
   - `liked_businesses`
   - `dismissed_businesses`
   - `reviews`
   - `feedback_log`
   - `partner_applications`
   - `contact_messages`
   - `reports`

The migration is **idempotent** — you can re-run it safely. Every `CREATE`
uses `IF NOT EXISTS` and every policy uses `DROP IF EXISTS` + `CREATE`. If
you ever change the schema and need to re-apply, just run it again.

If the migration errors out partway, check the error message — most common
cause is the `postgis` extension not being available on free tier. If that
happens, comment out the line `CREATE EXTENSION IF NOT EXISTS postgis;` and
re-run. (You'll lose the "Близо до мен" feature until you upgrade, but the
rest works.)

---

## Step 2 — Grant yourself admin access

Without admin access, you can't read submissions. Forms still POST and
data still lands in Postgres, but the RLS policies hide reads from non-admins.

### 2a. Sign yourself up

Easiest path: visit your live site, click "Вход" (the auth modal), enter
your email. You'll get a magic-link / OTP email from Supabase. Click it.

Alternative path: in Supabase Dashboard → **Authentication** → **Users** →
**Add user** → enter your email, choose "Send magic link". You'll get the
email immediately.

### 2b. Find your user UUID

In SQL Editor, run:

```sql
SELECT id, email FROM auth.users ORDER BY created_at DESC LIMIT 5;
```

Copy your UUID (looks like `a1b2c3d4-...`).

### 2c. Promote yourself to admin

```sql
INSERT INTO public.business_owners (id, display_name, is_admin)
VALUES ('PASTE_YOUR_UUID_HERE', 'Admin', true)
ON CONFLICT (id) DO UPDATE SET is_admin = true;
```

Done. From now on, when you log in via the live site, you can read every
table (contact_messages, reports, partner_applications, feedback_log,
reviews — all of them). Other authenticated users still see only what
the per-table RLS policies allow.

---

## Step 3 — Verify the integration end-to-end

### 3a. Forms persist to Supabase

1. Visit `contacts.html` on your live site, fill the form, submit.
2. In Supabase Dashboard → **Table Editor** → **`contact_messages`** → you should see a new row appear within 1–2 seconds.
3. Repeat for `report.html` → `reports` table.
4. Repeat for `partners.html` → `partner_applications` table (with `status = 'pending'`).
5. On `search.html`, dismiss 3 cards → on the 3rd dismiss the auth modal should auto-open. Close it. Open the dismiss-feedback wizard on a 4th card, complete it → check `feedback_log`.

### 3b. RLS sanity check

In SQL Editor, switch to the **anonymous role** dropdown (top-right of editor),
then run:

```sql
SELECT COUNT(*) FROM contact_messages;
```

Should return `0` (anon can't read). Now switch back to your authenticated
user (via the dropdown) — should return the actual count. This proves the
RLS policies work.

### 3c. Search reads from Supabase

1. Visit `search.html` — should show **0 results** if you haven't added any businesses yet.
2. Manually insert a test business via SQL editor:

   ```sql
   INSERT INTO businesses (name, tier, city, services, categories, age_groups, published)
   VALUES ('Test Specialist', 'Доверен', 'София',
           ARRAY['Тест услуга'], ARRAY['Специалисти'], ARRAY['3-5','6-12'],
           true);
   ```

3. Reload `search.html` → the test business should appear as a card.
4. In SQL editor: `UPDATE businesses SET published = false;` → reload the page → card disappears.
5. Re-publish: `UPDATE businesses SET published = true;` → reappears.

This proves both the data swap AND the RLS read policy work.

---

## Step 4 — Add real businesses (until business-dashboard is wired)

Until [business-dashboard.html](../business-dashboard.html) is hooked up to
real auth, you'll add businesses via the SQL editor or Table Editor.

### Quick add via Table Editor

Dashboard → **Table Editor** → **businesses** → **Insert row** → fill in
fields. Required: `name`, `tier`. Recommended: `city`, `description`,
`logo`, `services`, `categories`, `age_groups`, contact fields. Set
`published = true` when ready to make it visible.

### Bulk add via SQL

```sql
INSERT INTO businesses (
  name, tier, city, address, lat, lng, description,
  services, categories, age_groups,
  logo, sop, phone, email, website, facebook, instagram,
  cta_label_1, cta_url_1, cta_label_2, cta_url_2,
  published
) VALUES (
  'Little Engineers',
  'Доверен',
  'София',
  'ул. Витоша 15',
  42.6977, 23.3219,
  'STEM програма за деца от 6 до 12 години.',
  ARRAY['LEGO роботика', '3D печат', 'Кодиране'],
  ARRAY['Учене и умения'],
  ARRAY['6-12','13-18'],
  'https://...',
  false,
  '+359 88 123 4567',
  'info@littleengineers.bg',
  'https://littleengineers.bg',
  'https://facebook.com/...',
  'https://instagram.com/...',
  'Запиши се', 'https://littleengineers.bg/signup',
  'Виж курсове', 'https://littleengineers.bg/courses',
  true
);
```

Slug is auto-generated from name via trigger — you don't need to set it.

---

## Step 5 — Enable OAuth providers (optional, do later)

The frontend code already supports Google, Facebook, and LinkedIn buttons.
They're hidden until you enable each provider in the Supabase dashboard.
You can do these one at a time, in any order.

### Google

1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com).
2. **APIs & Services** → **OAuth consent screen** → fill in app name, support email, etc. → publish.
3. **Credentials** → **Create credentials** → **OAuth client ID** → **Web application**.
4. Authorized redirect URIs — add this exact URL:
   `https://erfndxmqitavqkfeohxh.supabase.co/auth/v1/callback`
5. Copy the Client ID and Client Secret.
6. Supabase Dashboard → **Authentication** → **Providers** → **Google** → toggle on → paste both values → Save.

### Facebook

1. [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App** → **Consumer**.
2. Add product **Facebook Login** → **Settings**.
3. Valid OAuth Redirect URI: `https://erfndxmqitavqkfeohxh.supabase.co/auth/v1/callback`
4. Get App ID + App Secret from **Settings → Basic**.
5. Supabase Dashboard → **Authentication** → **Providers** → **Facebook** → enable → paste → Save.

### LinkedIn

1. [linkedin.com/developers](https://linkedin.com/developers/apps) → **Create app**.
2. **Auth** tab → Redirect URLs: `https://erfndxmqitavqkfeohxh.supabase.co/auth/v1/callback`
3. Request access to **Sign In with LinkedIn using OpenID Connect** product.
4. Get Client ID + Client Secret.
5. Supabase Dashboard → **Authentication** → **Providers** → **LinkedIn (OIDC)** → enable → paste → Save.

After enabling any provider, the corresponding button will show up in the
auth modal automatically — no code changes needed.

---

## Step 6 — Localize the magic-link email (optional)

Supabase ships with English email templates. To localize to Bulgarian:

1. Dashboard → **Authentication** → **Email Templates** → **Magic Link**.
2. Replace the subject and body with Bulgarian copy. Keep the `{{ .ConfirmationURL }}` placeholder.
3. Repeat for **Confirm signup**, **Invite user**, **Change Email Address**, and **Reset Password** templates.

---

## Common operations

### View all submitted forms

Dashboard → **Table Editor** → pick the table:
- `contact_messages` — contacts.html
- `reports` — report.html
- `partner_applications` — partners.html
- `feedback_log` — search.html dismiss wizard
- `reviews` — search.html mobile review sheet

Click any row to see full details. You can also filter, sort, and edit inline.

### Recover offline-queued submissions

If a user submitted a form while offline, the data is in their browser's
`localStorage` under key `zd_pending_submissions`. They (or you, while
debugging on their device) can recover it via DevTools console:

```js
ZdApi.getPending()    // see the queue
ZdApi.clearPending()  // wipe after manual import
```

### Reset the schema (nuclear option)

If you want to start over completely:

```sql
-- DANGER: deletes ALL data
DROP TABLE IF EXISTS public.dismissed_businesses CASCADE;
DROP TABLE IF EXISTS public.liked_businesses CASCADE;
DROP TABLE IF EXISTS public.reviews CASCADE;
DROP TABLE IF EXISTS public.feedback_log CASCADE;
DROP TABLE IF EXISTS public.reports CASCADE;
DROP TABLE IF EXISTS public.contact_messages CASCADE;
DROP TABLE IF EXISTS public.partner_applications CASCADE;
DROP TABLE IF EXISTS public.business_owners CASCADE;
DROP TABLE IF EXISTS public.parents CASCADE;
DROP TABLE IF EXISTS public.businesses CASCADE;
DROP TYPE IF EXISTS business_tier CASCADE;
DROP TYPE IF EXISTS application_status CASCADE;
DROP TYPE IF EXISTS report_status CASCADE;
```

Then re-run `0001_initial_schema.sql`.

### Free-tier 7-day pause

Supabase free tier pauses inactive projects after 7 days of no activity.
First request after a pause takes ~5 seconds to wake up the project.
Lifehack: schedule a daily ping via GitHub Actions or a Supabase Edge Function
that does `SELECT 1` against any table. Not urgent until you go live.

---

## Files this integration touches

- `supabase/migrations/0001_initial_schema.sql` — schema source of truth
- `supabase-init.js` — loads supabase-js v2 from CDN, exposes `window.ZdSupabase`
- `api-stub.js` — `_doSubmit()` now calls `ZdSupabase.from(endpoint).insert(...)` with localStorage fallback
- `search.html` — gist fetch replaced with Supabase query, hybrid auth trigger added
- `listing.html` — gist fetch replaced with direct id/slug Supabase lookup
- `contacts.html`, `partners.html`, `report.html` — added `<script src="supabase-init.js">` before `api-stub.js`

## Files this integration does NOT touch (yet)

- `business-login.html` — partner auth UI exists but is still mock; needs the partner-application approval flow + OAuth providers before we wire it
- `business-dashboard.html` — same; also has WebAuthn mock that needs careful migration
- `index.html`, `pricing.html`, `privacy.html`, `terms.html`, `cookies.html` — purely static, no backend dependency

---

## When to upgrade to Pro ($25/month)

The free tier gets you to launch. Upgrade when any of these become true:

- DB approaches **500 MB** (≈ 50,000 businesses)
- Monthly active users approaches **50,000**
- You need **daily backups** (free has 7-day point-in-time restore)
- You need **custom domain** for the API URL (e.g. `api.zadeteto.com`)
- You're tired of the **7-day pause** behavior on idle projects

For ZaDeteto's MVP launch — none of these will be true. Stay on free.
