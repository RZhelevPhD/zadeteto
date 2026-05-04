# Clean Enriched Directive — Drop Viewport-Spill Rows

## Objective
Filter an enriched provider CSV to remove "viewport-spill" rows — businesses that Google Maps surfaced when the scrape was anchored to one city but are actually located in a different Bulgarian city. Writes a kept CSV and a dropped-with-reason sidecar CSV so nothing is lost.

## Execution Script
`executions/clean_enriched.py`

## How It Works
1. Reads the input CSV with `utf-8-sig` encoding and `dtype=str, keep_default_na=False` so empty cells stay as `""` and numeric-looking columns aren't coerced through NaN.
2. For each row, concatenates the `name`, `address`, `category`, `city`, `gmaps_url`, and `google maps url` fields into a single scan string. Both URL column names are scanned because the scraper emits `google maps url` while `enrich_providers.py` renames it to `gmaps_url`.
3. URL-decodes any `%`-encoded segments so Cyrillic city names inside Google Maps URLs become matchable. Applies NFKC normalization and lowercases.
4. Strips the target city substring from the scan string first, so the target cannot self-trigger and substrings like `Загора` (which appear in `Нова Загора`) can still match independently.
5. For every other city in the hardcoded Bulgarian city list (target city excluded at runtime), tests a word-boundary regex (`(?<!\w)…(?!\w)`) against the stripped scan text. Word boundaries under Python 3's Unicode-aware `re` isolate whole words across Cyrillic and Latin scripts — this prevents false positives on Стара Загора street names like `Пловдивско шосе` (which would false-match `Пловдив` under naive substring matching).
6. Any match routes the row to the dropped CSV with a `Drop Reason` column set to `Other city detected: <city>`; otherwise the row is kept.
7. Writes both CSVs atomically (`.tmp` sibling + `os.replace`) with `utf-8-sig` encoding, cleaning up orphan `.tmp` files if the write raises.
8. Prints input/kept/dropped row counts + target city to stdout.

## CLI Flags

| Flag | Required | Default | Purpose |
|------|----------|---------|---------|
| `--input` | Yes | — | Enriched CSV produced by `enrich_providers.py` (or a raw scraped CSV) |
| `--kept` | Yes | — | Output CSV path for rows kept |
| `--dropped` | Yes | — | Output CSV path for rows dropped; same columns plus trailing `Drop Reason` |
| `--target-city` | No | `Стара Загора` | The city the scrape was anchored to. Any row mentioning a different BG city in SCAN_FIELDS is dropped. |

Exits with code 1 if the input file does not exist.

## Usage

```bash
# Стара Загора (default target)
python executions/clean_enriched.py \
    --input tmp/enriched_psiholog.csv \
    --kept tmp/cleaned_psiholog.csv \
    --dropped tmp/dropped_psiholog.csv

# Another city
python executions/clean_enriched.py \
    --input tmp/enriched_plovdiv.csv \
    --kept tmp/cleaned_plovdiv.csv \
    --dropped tmp/dropped_plovdiv.csv \
    --target-city "Пловдив"
```

## Cities Checked
Cyrillic-only, word-boundary matched (Latin transliterations dropped to avoid false positives on common given names like "Sofia"):

София, Пловдив, Варна, Бургас, Стара Загора, Русе, Плевен, Добрич, Сливен, Шумен, Перник, Хасково, Ямбол, Казанлък, Велико Търново, В. Търново, Благоевград, Видин, Монтана, Кърджали, Смолян, Силистра, Кюстендил, Габрово, Враца, Търговище, Ловеч, Разград, Пазарджик, Нова Загора, Асеновград.

The `--target-city` value is removed from this list at runtime before patterns are built.

## Constraints
- Intentionally conservative — off-topic rows (hospitals, universities, ophthalmology, pediatricians) are NOT filtered. Those signals are too noisy to automate reliably and the user curates them at import time.
- If the `--target-city` value is not in the master list, no self-exclusion is applied (all 30 cities become patterns). Warn is not emitted; caller should double-check kept/dropped counts in that case.
- Word-boundary matching scans only the SCAN_FIELDS columns. A row whose *website copy or decision maker bio* mentions a different city will NOT be dropped.
- No resume/checkpoint — single-shot and fast; re-running from scratch is cheap.

## Changelog
- 2026-04-20: Initial directive. Generalizes the prior Стара Загора-only script (`clean_enriched_stara_zagora.py`, deleted) to accept `--target-city`. Fixes applied at the same time: scan `gmaps_url` + `google maps url` (the enricher renames the column), word-boundary regex to eliminate street-name false positives, dropped Latin transliterations, added `Нова Загора` to the city list.
- 2026-05-03: Added `Асеновград` to the master city list to keep lockstep with `CITY_COORDS` in `executions/scrape_google_maps.py` (Tier D scrape coverage).
