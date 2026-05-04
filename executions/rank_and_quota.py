"""
Rank deduped businesses per (city, sphere), apply min-review threshold,
slice into Стандартен / Безплатен tiers per quota, and emit a CSV ready for
import_businesses_to_supabase.py --respect-csv-tier.

Inserts between dedupe_across_categories.py and import_businesses_to_supabase.py.

Inputs:
  - --input tmp/deduped_all.csv   (output of dedupe_across_categories.py)
  - --city  "София"               (city to process; only matching rows are kept)
  - --quotas tmp/quotas.yaml      (per-city standard_per_sphere, free_pct, min_reviews)
  - --sphere-map tmp/sphere_map.yaml  (niche -> primary sphere + secondary[])

Output:
  - --output tmp/ranked_quota_<city>.csv
    Same columns as the deduped CSV plus:
      tier         "Стандартен" or "Безплатен"
      published    "true"  (both tiers visible immediately, per spec 2026-05-02)
      sphere       primary sphere assigned to this row (for audit)

Algorithm per row:
  1. Determine the row's primary sphere by looking up its niche slug(s) in
     sphere-map.yaml. The niche signal is read from --niche-from, default
     `source_keywords` (the pipe-separated slug list dedupe writes). Slugs
     and YAML keys are normalised (NFKC + casefold + non-word -> '_') before
     comparison so "Детски психолог" matches "Детски_психолог".
  2. If multiple niches map to different primary spheres, pick the sphere
     with the most niche matches; ties broken by first-listed YAML key.
  3. Drop rows whose niche cannot be mapped (logged to stderr).

Algorithm per (city, sphere) bucket:
  1. Drop rows with reviews < min_reviews[city].
  2. Sort by (reviews DESC, rating DESC).
  3. Top `standard_per_sphere` -> tier="Стандартен", published=true.
  4. Next ceil(standard_per_sphere * free_pct/100) -> tier="Безплатен", published=true.
  5. Drop the rest (kept in the deduped CSV but NOT in the output, so they
     do not land in Supabase — this keeps the public DB light per the
     2026-05-02 spec).

Also augments the row's `categories` column with the secondary spheres
listed in sphere-map.yaml (pipe-separated, deduped, primary first).

Usage:
    python executions/rank_and_quota.py \\
        --input tmp/deduped_all.csv \\
        --city "София" \\
        --quotas tmp/quotas.yaml \\
        --sphere-map tmp/sphere_map.yaml \\
        --output tmp/ranked_quota_София.csv

Add --dry-run to print bucket counts without writing the output file.
"""

import argparse
import math
import os
import re
import sys
import unicodedata

import pandas as pd
import yaml


def _norm_key(s: str) -> str:
    """Normalise a niche label / slug for matching: NFKC + casefold +
    collapse non-word chars to '_'. Handles 'Детски психолог' vs
    'Детски_психолог' vs 'детски  психолог'."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).casefold().strip()
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    return s.strip("_")


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_niche_index(sphere_map_yaml: dict) -> dict:
    """Return {normalised_niche_key: {primary, secondary, original_key}}."""
    niches = sphere_map_yaml.get("niches") or {}
    idx = {}
    for raw_key, spec in niches.items():
        nk = _norm_key(raw_key)
        if not nk:
            continue
        primary = (spec or {}).get("primary", "")
        secondary = list((spec or {}).get("secondary") or [])
        idx[nk] = {
            "primary": primary,
            "secondary": secondary,
            "original_key": raw_key,
        }
    return idx


def _row_niches(row: pd.Series, niche_from: str) -> list[str]:
    """Extract pipe-separated niche slugs/keywords from the chosen column."""
    raw = str(row.get(niche_from, "") or "").strip()
    if not raw:
        # Fallback to `category` (the original scraper column) if the
        # primary source is empty.
        raw = str(row.get("category", "") or "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split("|") if p.strip()]


def _assign_sphere(row: pd.Series, niche_from: str, niche_index: dict) -> tuple[str, list[str], list[str]]:
    """Return (primary_sphere, secondary_spheres, matched_niches).
    Empty primary_sphere means no niche match -> row is unmappable."""
    niches = _row_niches(row, niche_from)
    if not niches:
        return "", [], []

    # Tally votes for each primary sphere; collect secondaries from every
    # match. First-match-wins on ties (preserves YAML order intent).
    primary_votes: dict[str, int] = {}
    primary_first_seen: dict[str, int] = {}
    secondaries: list[str] = []
    matched_niches: list[str] = []
    for i, n in enumerate(niches):
        nk = _norm_key(n)
        spec = niche_index.get(nk)
        if not spec:
            continue
        matched_niches.append(spec["original_key"])
        p = spec["primary"]
        if p:
            primary_votes[p] = primary_votes.get(p, 0) + 1
            primary_first_seen.setdefault(p, i)
        for sec in spec["secondary"]:
            if sec and sec not in secondaries:
                secondaries.append(sec)

    if not primary_votes:
        return "", [], matched_niches

    # Pick primary by (votes DESC, first_seen ASC).
    primary = sorted(
        primary_votes.keys(),
        key=lambda p: (-primary_votes[p], primary_first_seen[p]),
    )[0]
    # Drop primary from secondaries to avoid duplication.
    secondaries = [s for s in secondaries if s != primary]
    return primary, secondaries, matched_niches


def _to_int(s) -> int:
    try:
        return int(float(str(s).strip()))
    except (ValueError, TypeError):
        return 0


def _to_float(s) -> float:
    try:
        return float(str(s).strip())
    except (ValueError, TypeError):
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply per-(city, sphere) ranking + quota + tier assignment to a deduped CSV. Output feeds import_businesses_to_supabase.py --respect-csv-tier.")
    parser.add_argument("--input", required=True, help="Deduped CSV (e.g. tmp/deduped_all.csv).")
    parser.add_argument("--city", required=True, help="City to process. Rows whose `city` column does not match this are dropped.")
    parser.add_argument("--quotas", default="tmp/quotas.yaml", help="YAML with cities -> {standard_per_sphere, free_pct, min_reviews}.")
    parser.add_argument("--sphere-map", default="tmp/sphere_map.yaml", help="YAML with niches -> {primary, secondary[]}.")
    parser.add_argument("--output", default=None, help="Output CSV path. Defaults to tmp/ranked_quota_<city>.csv.")
    parser.add_argument("--niche-from", default="source_keywords", choices=["source_keywords", "categories", "category"], help="Which CSV column to read niche slugs from (default: source_keywords).")
    parser.add_argument("--dry-run", action="store_true", help="Print bucket counts without writing the output file.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.quotas):
        print(f"ERROR: quotas YAML not found: {args.quotas}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.sphere_map):
        print(f"ERROR: sphere-map YAML not found: {args.sphere_map}", file=sys.stderr)
        sys.exit(1)

    quotas_yaml = _load_yaml(args.quotas)
    sphere_yaml = _load_yaml(args.sphere_map)
    niche_index = _build_niche_index(sphere_yaml)

    cities_cfg = quotas_yaml.get("cities") or {}
    city_cfg = cities_cfg.get(args.city)
    if not city_cfg:
        print(f"ERROR: no quota config for city '{args.city}' in {args.quotas}.", file=sys.stderr)
        print(f"       Available cities: {sorted(cities_cfg.keys())}", file=sys.stderr)
        sys.exit(1)
    standard_per_sphere = int(city_cfg["standard_per_sphere"])
    free_pct = int(city_cfg["free_pct"])
    min_reviews = int(city_cfg["min_reviews"])

    df = pd.read_csv(args.input, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    # Validate required input columns up front so we fail fast with a clear
    # message rather than a downstream KeyError.
    required_cols = ("city", "reviews", "rating", "categories", "legacy_id")
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"ERROR: input CSV is missing required column(s): {missing}", file=sys.stderr)
        sys.exit(1)

    # Restrict to the target city.
    norm_city = _norm_key(args.city)
    city_mask = df["city"].apply(lambda c: _norm_key(c) == norm_city)
    df = df.loc[city_mask].copy().reset_index(drop=True)
    if df.empty:
        print(f"WARN: no rows in {args.input} for city '{args.city}'. Writing empty output.", file=sys.stderr)
        # Write an empty CSV with the augmented header so downstream import
        # doesn't choke on a missing file.
        empty = df.copy()
        for col in ("sphere", "tier", "published"):
            empty[col] = ""
        out_path = args.output or os.path.join("tmp", f"ranked_quota_{_norm_key(args.city) or 'city'}.csv")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        empty.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\nWrote 0 rows -> {out_path}")
        return

    # Assign sphere + secondary spheres per row. Stash secondaries on the
    # frame itself (keyed by legacy_id) so the kept-row augmentation later
    # doesn't need positional indexing across filter steps.
    primaries: list[str] = []
    sec_lookup: dict[str, list[str]] = {}
    unmapped: list[dict] = []
    for _, row in df.iterrows():
        primary, secondary, _matched = _assign_sphere(row, args.niche_from, niche_index)
        primaries.append(primary)
        lid = str(row.get("legacy_id", "")).strip()
        if lid:
            sec_lookup[lid] = secondary
        if not primary:
            unmapped.append({"legacy_id": lid, "name": row.get("name", ""), "niche_raw": row.get(args.niche_from, "") or row.get("category", "")})

    df["sphere"] = primaries

    if unmapped:
        print(f"WARN: {len(unmapped)} row(s) had no niche match in sphere-map.yaml and were dropped from quota assignment:", file=sys.stderr)
        for u in unmapped[:10]:
            print(f"  - {u['legacy_id']} | {u['name']} | niche='{u['niche_raw']}'", file=sys.stderr)
        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more.", file=sys.stderr)

    # Numeric columns for ranking.
    df["_reviews_int"] = df["reviews"].apply(_to_int)
    df["_rating_float"] = df["rating"].apply(_to_float)

    # Filter min_reviews.
    before = len(df)
    df = df.loc[(df["sphere"] != "") & (df["_reviews_int"] >= min_reviews)].copy()
    dropped_min = before - len(df)
    print(f"INFO: dropped {dropped_min} row(s): unmapped sphere or reviews < {min_reviews}.")

    # Per-sphere bucket assignment.
    free_per_sphere = math.ceil(standard_per_sphere * free_pct / 100)
    total_per_sphere = standard_per_sphere + free_per_sphere

    df["tier"] = ""
    df["published"] = "false"

    bucket_summary: list[tuple[str, int, int]] = []
    for sphere, grp in df.groupby("sphere", sort=False):
        grp_sorted = grp.sort_values(["_reviews_int", "_rating_float"], ascending=[False, False])
        idxs = list(grp_sorted.index)
        std_idxs = idxs[:standard_per_sphere]
        free_idxs = idxs[standard_per_sphere:standard_per_sphere + free_per_sphere]
        df.loc[std_idxs, "tier"] = "Стандартен"
        df.loc[std_idxs, "published"] = "true"
        df.loc[free_idxs, "tier"] = "Безплатен"
        df.loc[free_idxs, "published"] = "true"
        bucket_summary.append((sphere, len(std_idxs), len(free_idxs)))

    # Drop rows that didn't make either tier.
    kept = df.loc[df["tier"] != ""].copy().reset_index(drop=True)
    overflow = len(df) - len(kept)
    print(f"INFO: dropped {overflow} row(s) below quota (kept in deduped CSV, not imported).")

    # Augment categories[] with secondary spheres for kept rows. sec_lookup
    # was built up-front from the pre-filter pass keyed by legacy_id.
    new_categories: list[str] = []
    for _, row in kept.iterrows():
        existing = [c.strip() for c in str(row.get("categories", "")).split("|") if c.strip()]
        primary = row.get("sphere", "")
        secs = sec_lookup.get(str(row.get("legacy_id", "")), [])
        merged: list[str] = []
        for c in [primary] + existing + secs:
            if c and c not in merged:
                merged.append(c)
        new_categories.append("|".join(merged))
    kept["categories"] = new_categories

    # Drop helper columns from output.
    kept = kept.drop(columns=["_reviews_int", "_rating_float"])

    # Print summary.
    print(f"\nQuota plan for {args.city}:")
    print(f"  standard_per_sphere = {standard_per_sphere}")
    print(f"  free_per_sphere     = {free_per_sphere} (ceil({standard_per_sphere} * {free_pct}%))")
    print(f"  min_reviews         = {min_reviews}")
    print(f"\nFilled buckets:")
    for sphere, n_std, n_free in sorted(bucket_summary):
        print(f"  {sphere:32s}  Стандартен={n_std:3d}  Безплатен={n_free:3d}")
    print(f"\nTotal kept (will be imported): {len(kept)}")
    print(f"Total overflow (dropped):      {overflow}")

    if args.dry_run:
        print("\nDRY RUN — no output written.")
        return

    safe_city_slug = _norm_key(args.city) or "city"
    output = args.output or os.path.join("tmp", f"ranked_quota_{safe_city_slug}.csv")
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    tmp = output + ".tmp"
    try:
        kept.to_csv(tmp, index=False, encoding="utf-8-sig")
        os.replace(tmp, output)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
    print(f"\nWrote {len(kept)} rows -> {output}")


if __name__ == "__main__":
    main()
