"""
Filter enriched CSVs to drop viewport-spill rows — businesses that Google Maps
surfaced in a keyword query anchored on one city but are actually located in a
different Bulgarian city. Writes a kept CSV and a dropped-with-reason sidecar
CSV so nothing is lost.

Detection strategy: scan the business name + google maps url + category +
address text for any major Bulgarian city name other than the `--target-city`.
If a different city appears, the row is treated as pollution.

This script is intentionally conservative — off-topic rows (hospitals,
universities, ophthalmology, pediatricians) are NOT filtered here because the
signals are too noisy to automate reliably. The user will curate those at
import time. This script only filters city pollution, which is mechanical.

Usage:
    python executions/clean_enriched.py \
        --input tmp/enriched_psiholog.csv \
        --kept tmp/cleaned_psiholog.csv \
        --dropped tmp/dropped_psiholog.csv \
        --target-city "Стара Загора"
"""

import argparse
import os
import re
import sys
import unicodedata
from urllib.parse import unquote

import pandas as pd

# Master list of major Bulgarian cities (Cyrillic, no transliterations — Latin
# forms cause false positives on common given names like "Sofia"). The target
# city is removed from this list at runtime via --target-city.
_ALL_BG_CITIES = [
    "София",
    "Пловдив",
    "Варна",
    "Бургас",
    "Стара Загора",
    "Русе",
    "Плевен",
    "Добрич",
    "Сливен",
    "Шумен",
    "Перник",
    "Хасково",
    "Ямбол",
    "Казанлък",
    "Велико Търново",
    "В. Търново",
    "Благоевград",
    "Видин",
    "Монтана",
    "Кърджали",
    "Смолян",
    "Силистра",
    "Кюстендил",
    "Габрово",
    "Враца",
    "Търговище",
    "Ловеч",
    "Разград",
    "Пазарджик",
    "Нова Загора",
    "Асеновград",
]

# Fields to scan per row. Enricher renames the scraper's `google maps url`
# column to `gmaps_url` via its INPUT_COLUMN_ALIASES, so we scan both forms —
# the script works on both raw scraped CSVs and post-enrichment CSVs.
SCAN_FIELDS = ["name", "address", "category", "city", "gmaps_url", "google maps url"]


def _normalize(text) -> str:
    if text is None:
        return ""
    s = str(text)
    if "%" in s:
        try:
            s = unquote(s)
        except Exception:
            pass
    s = unicodedata.normalize("NFKC", s).lower()
    return s


def _build_patterns(target_city: str) -> list[tuple[str, re.Pattern]]:
    """Word-boundary regex per city, excluding the target city itself.
    Word boundaries (`(?<!\\w)…(?!\\w)`) correctly isolate whole words across
    Cyrillic and Latin scripts under Python 3's default Unicode-aware `re`."""
    target_norm = _normalize(target_city)
    patterns = []
    for city in _ALL_BG_CITIES:
        if _normalize(city) == target_norm:
            continue
        patterns.append((
            city,
            re.compile(rf"(?<!\w){re.escape(_normalize(city))}(?!\w)"),
        ))
    return patterns


def _row_text(row: pd.Series) -> str:
    parts = []
    for col in SCAN_FIELDS:
        if col in row.index:
            parts.append(_normalize(row[col]))
    return " || ".join(parts)


def _detect_other_city(row_text: str, target_city: str, patterns) -> str | None:
    # Strip the target city substring first so e.g. "Нова Загора" can still
    # match when target is "Стара Загора" (shared "Загора" suffix), and so
    # the target city itself cannot self-trigger if it somehow ended up in
    # the pattern list.
    stripped = row_text.replace(_normalize(target_city), "")
    for city, pattern in patterns:
        if pattern.search(stripped):
            return city
    return None


def main():
    parser = argparse.ArgumentParser(description="Drop viewport-spill rows from an enriched CSV.")
    parser.add_argument("--input", required=True, help="Enriched CSV produced by enrich_providers.py")
    parser.add_argument("--kept", required=True, help="Output CSV for rows kept")
    parser.add_argument("--dropped", required=True, help="Output CSV for rows dropped (with reason column)")
    parser.add_argument("--target-city", default="Стара Загора", help="The city the scrape was anchored to (default: Стара Загора). Rows mentioning other BG cities are dropped.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    patterns = _build_patterns(args.target_city)

    df = pd.read_csv(args.input, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    total = len(df)

    dropped_rows = []
    kept_rows = []
    for _, row in df.iterrows():
        text = _row_text(row)
        other = _detect_other_city(text, args.target_city, patterns)
        if other:
            rec = row.to_dict()
            rec["Drop Reason"] = f"Other city detected: {other}"
            dropped_rows.append(rec)
        else:
            kept_rows.append(row.to_dict())

    kept_df = pd.DataFrame(kept_rows, columns=df.columns)
    dropped_df = pd.DataFrame(dropped_rows, columns=list(df.columns) + ["Drop Reason"])

    for out_path, out_df in [(args.kept, kept_df), (args.dropped, dropped_df)]:
        out_abs = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
        tmp_path = out_abs + ".tmp"
        try:
            out_df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
            os.replace(tmp_path, out_abs)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    print(f"Input:       {args.input} ({total} rows)")
    print(f"Target city: {args.target_city}")
    print(f"Kept:        {os.path.abspath(args.kept)} ({len(kept_df)} rows)")
    print(f"Dropped:     {os.path.abspath(args.dropped)} ({len(dropped_df)} rows)")


if __name__ == "__main__":
    main()
