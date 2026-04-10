# Sample data tracking — safety guarantees

> Last updated: 2026-04-08
>
> This document explains how mockup / sample / demo data is tracked in
> the ZaDeteto Supabase database, and how to clean it up safely WITHOUT
> ever deleting real partner data.

---

## The contract

**Real partner data must NEVER have `is_sample = true`.**

Every business row in `public.businesses` has an `is_sample boolean` column
with default `false`. This is the single source of truth for "is this row
mockup data".

| What | `is_sample` value |
|---|---|
| Real partner who signed up via partners.html | `false` (hard default) |
| Real partner inserted via business-dashboard | `false` |
| Real partner inserted by admin via SQL editor (when you remember to omit the column) | `false` (default kicks in) |
| Mockup row from `sample-businesses.sql` | `true` (set explicitly) |
| Mockup row from `sample-100-mockup-partners.sql` | `true` (set explicitly) |

There is **no UI, no form, no API path** that ever sets `is_sample = true`.
The only way a row gets that flag is by being explicitly inserted from
one of the sample SQL files in this folder.

This means: **`DELETE FROM businesses WHERE is_sample = true` is always safe.**
It deletes mockup data and only mockup data.

---

## How it works under the hood

[Migration 0004](migrations/0004_is_sample_flag.sql) adds the column with
`DEFAULT false NOT NULL`. Three things matter:

1. **`NOT NULL`** — every row MUST have a value. There's no "unknown" state.
2. **`DEFAULT false`** — any INSERT that doesn't specify the column gets `false` automatically. So if you forget the column name when inserting a real business, it defaults to NOT being a mockup.
3. **Partial index** — `CREATE INDEX … WHERE is_sample = true` makes cleanup queries instant even if the table grows to millions of rows. The index only stores TRUE rows, so its size scales with the mockup count, not the real-data count.

---

## Sample data files (always tagged `is_sample = true`)

### [supabase/sample-businesses.sql](sample-businesses.sql)
6 hand-crafted businesses for the listing page demo:
- `sample-001` — Little Engineers (Доверен / София) — the rich hero with full description, working hours, gallery URLs, lat/lng
- `sample-002` — STEM Lab София (Проверен)
- `sample-003` — Coding Kids Academy (Проверен, SOP flag)
- `sample-004` — Robotics School Sofia (Стандартен)
- `sample-005` — Детска школа Изкуство (Доверен / Пловдив / Култура — different category, won't show in related-specialists for the others)
- `sample-006` — Online Code Camp (Проверен / Онлайн)

All have `legacy_id` starting with `sample-`.

### [supabase/sample-100-mockup-partners.sql](sample-100-mockup-partners.sql)
100 procedurally-generated rows (`mock-001` through `mock-100`) for visual
density / UX testing of the search page, filters, related specialists,
pagination, etc.

Distribution:
- **Tiers**: 10 Доверен / 25 Проверен / 40 Стандартен / 25 Безплатен (matches a realistic free→paid funnel)
- **Cities**: 40% София, 15% Пловдив, 12% Варна, 10% Бургас, 5% Стара Загора, 5% Русе, 5% Велико Търново, 5% Онлайн, 3% other
- **Categories**: round-robin across all 8 main categories (12-13 per category)
- **SOP flag**: ~14% of rows
- **Lat/lng**: present for all non-Online businesses, with small per-row offsets so map pins don't stack
- **Working hours**: every 4th paid-tier business (~12 rows) has a full schedule
- **Description**: paid tiers only (~50% of rows)

All have `legacy_id` starting with `mock-`.

---

## Daily-use queries

Paste these into Supabase SQL Editor whenever you need to know what's in your DB.

### How many real vs mockup rows do I have right now?
```sql
SELECT
  is_sample,
  count(*) AS rows,
  count(*) FILTER (WHERE published = true) AS published_rows
FROM public.businesses
GROUP BY is_sample
ORDER BY is_sample;
```
Expected output after running both sample files:
```
 is_sample | rows | published_rows
-----------+------+----------------
 false     |    0 |              0     ← real partners
 true      |  106 |            106     ← 6 + 100 sample rows
```

### Which categories are well-represented in my sample data?
```sql
SELECT unnest(categories) AS category, count(*) AS rows
FROM public.businesses
WHERE is_sample = true
GROUP BY category
ORDER BY rows DESC;
```

### Which cities are well-represented?
```sql
SELECT city, count(*) AS rows, count(*) FILTER (WHERE tier IN ('Доверен','Проверен')) AS paid
FROM public.businesses
WHERE is_sample = true
GROUP BY city
ORDER BY rows DESC;
```

### Spot a row I'm not sure about
```sql
SELECT id, legacy_id, name, tier, city, is_sample, created_at
FROM public.businesses
WHERE name ILIKE '%suspicious-name-here%';
```
Look at `is_sample` and `legacy_id`. If `legacy_id` starts with `sample-` or
`mock-` AND `is_sample = true`, it's a mockup. Anything else is real.

---

## Cleanup operations

### Delete ALL sample data (the nuclear option, safe)
```sql
DELETE FROM public.businesses WHERE is_sample = true;
```
This removes every row inserted by the sample SQL files. It does NOT touch
any real partner data — the WHERE clause guarantees that.

After running, verify with:
```sql
SELECT count(*) FROM public.businesses WHERE is_sample = true;
-- Expected: 0
```

### Delete only the 100 mockup batch (keep the 6 listing-demo rows)
```sql
DELETE FROM public.businesses WHERE legacy_id LIKE 'mock-%';
```
Useful if you want to keep the rich `sample-001..006` businesses for
listing-page demo screenshots but clear out the bulk filter-test data.

### Delete only the 6 listing-demo rows (keep the 100 mockup batch)
```sql
DELETE FROM public.businesses WHERE legacy_id LIKE 'sample-%';
```

### Re-seed (delete + re-insert)
```sql
-- 1. Wipe
DELETE FROM public.businesses WHERE is_sample = true;
-- 2. Re-run sample-businesses.sql in the SQL editor
-- 3. Re-run sample-100-mockup-partners.sql in the SQL editor
```
Both files use `ON CONFLICT (legacy_id) DO UPDATE` so you can also skip
the wipe step and just re-run the inserts to refresh the data.

---

## What the sample data is NOT

- **NOT visible to anonymous visitors as "sample data"** — the rendering code on
  search.html and listing.html doesn't read `is_sample`. Sample rows look
  identical to real rows in the UI. This is intentional — the whole point
  of having mockup data is that it stress-tests the real rendering paths.
- **NOT excluded from the search results** — sample rows show up in search.html
  alongside real ones. If you want to hide them, add `.eq('is_sample', false)`
  to the search query in [search.html](../search.html), but that defeats the
  purpose.
- **NOT counted as real conversions** — when you look at your own metrics
  (Contentsquare, future Plausible), the page views happen on real URLs but
  the data they're viewing is fake. Mark this clearly in your dashboards.

---

## When to clean up

**Before launch**: at minimum, decide whether the 6 `sample-` rows should
ship. The 100 `mock-` rows should DEFINITELY be cleaned up before launch
(unless you intentionally want the directory to look populated for the
first visitors — discuss with stakeholders).

**Before any backup / export**: if you ever export the database to share
with a third party, run the cleanup query first OR explicitly note that
106 of the rows are mockups.

**Before connecting Plausible / GA / external analytics**: not strictly
necessary, but useful so your initial dashboards show real activity.

---

## Adding your own sample data later

If you want to add MORE mockup data (e.g., 50 more businesses for a
specific city or category test), follow this pattern:

1. Create a new file `supabase/sample-XXX-description.sql`
2. **Always include `is_sample` in the column list and set it to `true`**
3. Use a `legacy_id` prefix that's unique to your batch (e.g., `varna-batch-NNN`)
4. Add `ON CONFLICT (legacy_id) DO UPDATE SET ... is_sample = EXCLUDED.is_sample`
5. Document the file at the top with a comment explaining what it's for

The cleanup query (`WHERE is_sample = true`) will pick it up automatically —
no need to update any other code or docs.
