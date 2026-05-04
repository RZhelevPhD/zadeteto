# Process City Post-Scrape SOP

## Objective

Wrap the per-city post-scrape pipeline (`enrich → clean → stamp legacy_id → dedupe → rank_and_quota`) into a single command for one Bulgarian city. Stops short of the Supabase import so the operator can review the rank_and_quota preview before pushing.

This script is the second half of the multi-city ingest flow. The first half is the scrape itself, run with `executions/scrape_google_maps.py --input <tier_X_keywords.csv>` against a multi-city keywords CSV.

## Execution Script

`executions/process_city_post_scrape.py`

## How It Works

1. Picks up every `tmp/scraped_<keyword>_<city>_<YYYYMMDD>_<HHMMSS>.csv` whose city portion matches `--city` (slug match, NFKC + casefold + non-word→`_`). Filters by `--scraped-since YYYY-MM-DD` to ignore stale files from older runs. If multiple timestamps share a keyword, keeps the most recent.
2. Per keyword:
   - **Enrich** — `enrich_providers.py --no-search --output-csv <workdir>/enrich/enriched_<kw>.csv`. Skipped if `--skip-enrich` and the file already exists.
   - **Clean** — `clean_enriched.py --target-city <city> --kept <workdir>/clean/cleaned_<kw>.csv --dropped <workdir>/clean/dropped_<kw>.csv`. Skipped if `--skip-clean` and the kept file exists.
3. Stamps a positional `legacy_id` column on every cleaned CSV using `<prefix>-<kw>-<NNN>` (e.g. `plv-Логопед-001`). Idempotent — leaves existing non-empty legacy_id columns alone.
4. **Dedupe** — `dedupe_across_categories.py` across all cleaned files. Output → `<workdir>/deduped.csv`, audit → `<workdir>/dedupe_report.csv`.
5. **Rank + quota** — `rank_and_quota.py --city <city>`. Reads `tmp/quotas.yaml` + `tmp/sphere_map.yaml` to filter (min_reviews) + sort + slice into Стандартен / Безплатен tiers. Output → `<workdir>/ranked_quota.csv`.
6. Prints a final hint with the exact import command the operator should run next.

## CLI Flags

| Flag | Required | Default | Purpose |
|---|---|---|---|
| `--city` | Yes | — | Bulgarian city name, e.g. `"Пловдив"`. Drives both file matching and `--target-city` for `clean_enriched.py`. |
| `--legacy-prefix` | Yes | — | Short prefix for `legacy_id`, e.g. `plv`, `var`, `brg`, `sof`. |
| `--scraped-since` | No | none | Only pick up scraped CSVs whose date portion ≥ this `YYYY-MM-DD`. |
| `--workdir` | No | `tmp/runs/<city-slug>` | Per-city work folder. |
| `--quotas` | No | `tmp/quotas.yaml` | Quotas YAML for `rank_and_quota.py`. |
| `--sphere-map` | No | `tmp/sphere_map.yaml` | Niche → sphere YAML for `rank_and_quota.py`. |
| `--skip-enrich` | No | off | Reuse existing `<workdir>/enrich/enriched_<kw>.csv` files. |
| `--skip-clean` | No | off | Reuse existing `<workdir>/clean/cleaned_<kw>.csv` files. |

## Usage

```bash
# Full run for Plovdiv after the Tier B scrape finishes
python executions/process_city_post_scrape.py \
    --city "Пловдив" \
    --legacy-prefix plv \
    --scraped-since 2026-05-03

# Re-run only the dedupe+rank stages (clean + enrich already done)
python executions/process_city_post_scrape.py \
    --city "Пловдив" \
    --legacy-prefix plv \
    --scraped-since 2026-05-03 \
    --skip-enrich --skip-clean
```

After the script finishes, verify `<workdir>/ranked_quota.csv` (bucket counts, sample rows), then push to Supabase:

```bash
python executions/import_businesses_to_supabase.py \
    --input tmp/runs/<city-slug>/ranked_quota.csv \
    --city "<city>" \
    --import-batch <city-slug>-<YYYY-MM-DD> \
    --respect-csv-tier \
    --apply
```

## Constraints

- Single-threaded — runs the inner scripts one keyword at a time so log output stays interleavable and Google's site-crawl rate limits aren't tripped.
- Inherits each inner script's atomic-write + dry-run-by-default semantics; the orchestrator itself does not delete or overwrite the operator's own data outside `<workdir>` and the cleaned-file `legacy_id` stamp.
- Cyrillic city/keyword names are preserved on disk via NFKC + casefold + non-word→`_` slugging — works on NTFS, ext4, and APFS.
- The orchestrator does NOT push to Supabase. The operator confirms the rank_and_quota output and runs the import explicitly.

## Changelog

- 2026-05-03: Initial. Wraps the four-step post-scrape pipeline so per-city orchestration is one command. Pairs with `directives/rank-and-quota.md` and the `--respect-csv-tier` import flag added the same day.
- 2026-05-03: doc-sync verification pass — directive matches script behaviour (pipeline stages, all 8 CLI flags, workdir layout, manual import step, single-threaded + Cyrillic-safe + no-Supabase-write constraints). No edits needed.
