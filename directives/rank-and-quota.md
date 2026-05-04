# Rank & Quota SOP

## Objective

Curate a deduped scrape down to the top N partners per (city, directory sphere), with strict review-count and rating thresholds, and stamp each kept row with a tier (`Стандартен` or `Безплатен`) and `published=true` so it can be imported directly into Supabase via `import_businesses_to_supabase.py --respect-csv-tier`.

This script is the elimination pass — it keeps the public DB light by importing only curated partners. Anything below the quota or the min-review threshold is silently dropped from the import set (it stays in the deduped CSV archive).

## Required inputs

- `tmp/deduped_all.csv` — output of `dedupe_across_categories.py` (one row per unique business, with `source_keywords` listing pipe-separated niche slugs). Must contain columns `city`, `reviews`, `rating`, `categories`, `legacy_id` — the script validates these up front and exits with a clear ERROR if any are missing.
- `tmp/quotas.yaml` — per-city `standard_per_sphere`, `free_pct`, `min_reviews`.
- `tmp/sphere_map.yaml` — niche keyword → primary sphere + secondary sphere(s).

## Run

```bash
python executions/rank_and_quota.py \
  --input tmp/deduped_all.csv \
  --city "София" \
  --quotas tmp/quotas.yaml \
  --sphere-map tmp/sphere_map.yaml \
  --output tmp/ranked_quota_София.csv
```

Add `--dry-run` to see bucket counts without writing the output file. Use `--niche-from {source_keywords,categories,category}` to override which column the script reads niche signals from (default `source_keywords`).

## Algorithm

1. Filter input to rows whose `city` matches `--city` (NFKC + casefold + non-word→`_` normalisation).
2. For each row, look at `source_keywords` (pipe-separated). Each slug is normalised the same way and looked up in `sphere_map.yaml`. If multiple slugs map to different primary spheres, the sphere with the most hits wins (ties broken by YAML order).
3. Drop rows with no sphere match (logged to stderr) and rows with `reviews < min_reviews[city]`.
4. Per (city, sphere) bucket:
   - Sort by `(reviews DESC, rating DESC)`.
   - Top `standard_per_sphere` → `tier="Стандартен"`, `published=true`.
   - Next `ceil(standard_per_sphere * free_pct / 100)` → `tier="Безплатен"`, `published=true`.
   - Drop the rest from the output set.
5. Augment the kept row's `categories` column: primary sphere first, then any pre-existing labels, then the niche's secondary spheres (deduped, primary always at index 0 so trigger 0012's slice picks it first). Secondary spheres per row are looked up by `legacy_id` from a map built in the pre-filter pass, so the augmentation survives the min-reviews / unmapped-sphere filter without positional re-indexing.

If no rows match `--city`, the script writes an empty CSV with the augmented header (`sphere`, `tier`, `published`) and exits cleanly so the downstream import does not choke on a missing file.

## Output

`tmp/ranked_quota_<city>.csv` — same columns as the deduped CSV plus the columns below. When `--output` is omitted, the city portion of the default filename is sanitised through the same NFKC + casefold + non-word→`_` normaliser used elsewhere (e.g. `София` → `софия`) to avoid path-injection on exotic city strings.

| Column | Value |
|---|---|
| `sphere` | Primary sphere (audit only) |
| `tier` | `"Стандартен"` or `"Безплатен"` |
| `published` | `"true"` (both tiers visible immediately per spec 2026-05-02) |
| `categories` | Augmented: primary sphere + existing categories + secondary spheres |

Feed it directly into the import:

```bash
python executions/import_businesses_to_supabase.py \
  --input tmp/ranked_quota_София.csv \
  --city "София" \
  --import-batch sofia-2026-05-02 \
  --respect-csv-tier \
  --apply
```

The `--respect-csv-tier` flag is **required** — without it, `import_businesses_to_supabase.py` overrides every row to `tier="Безплатен"` and `published=false`.

## Quota config — quotas.yaml

Per-city dict:

```yaml
cities:
  София:
    standard_per_sphere: 50
    free_pct: 30
    min_reviews: 5
```

`free_pct` is a percentage of `standard_per_sphere`, e.g. 30 → ceil(50 * 0.30) = 15 rows in Безплатен per sphere. Total per sphere: standard + free.

## Sphere map — sphere_map.yaml

```yaml
niches:
  "Детски психолог":
    primary: "Специалисти"
    secondary: []
  "Логопед":
    primary: "Специалисти"
    secondary: ["Учене и умения"]
```

Niche keys MUST match what the dedupe writes into `source_keywords` after normalisation (NFKC + casefold + non-word→`_`). The scraper slugifies its filenames with `re.sub(r"[^\w\-]", "_", keyword)`, and dedupe carries that slug forward unchanged. The normaliser in `rank_and_quota.py` matches both forms.

## Spheres (canonical, 8)

Source of truth: `executions/clean_segment_prospects.py` NICHES taxonomy.

- Учене и умения
- Спорт и движение
- Игри и забавления
- Култура
- Специалисти
- Тържества и събития
- Стоки
- Домашна грижа и помощ

## Verification

After import, run this SQL in Supabase to confirm bucket counts match the quota:

```sql
SELECT city, tier, COUNT(*)
FROM businesses
WHERE import_batch = 'sofia-2026-05-02'
GROUP BY 1, 2
ORDER BY 1, 2;
```

Expect: `Стандартен ≤ standard_per_sphere * 8`, `Безплатен ≤ free_per_sphere * 8` per city. Below quota is fine — means a sphere had fewer qualifying businesses than the cap.

## Changelog

- 2026-05-02: Initial. Inserts between `dedupe_across_categories.py` and `import_businesses_to_supabase.py`. Pairs with the `--respect-csv-tier` flag added to the import script the same day.
- 2026-05-03: Post-review hardening — documented required input columns + fail-fast validation, empty-city case writes empty CSV with augmented header, secondaries lookup keyed by `legacy_id` (single pre-filter build), and default output filename now sanitises the city slug via `_norm_key`.
