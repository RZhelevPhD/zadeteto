"""
Per-city post-scrape orchestrator. Wraps enrich -> clean -> stamp legacy_id ->
dedupe -> rank_and_quota into a single command for one city. Stops short of
the Supabase import so the operator can review the preview first.

Picks up the per-keyword scraped CSVs that scrape_google_maps.py produced for
the target city (matched by `_<City>_<TIMESTAMP>.csv` filename pattern), runs
each stage end-to-end, and writes everything into a per-city work folder so
parallel cities never collide on filenames.

Usage:
    python executions/process_city_post_scrape.py \\
        --city "Пловдив" \\
        --legacy-prefix plv \\
        --scraped-since 2026-05-03

Optional:
    --workdir tmp/runs/<city-slug>     (default)
    --quotas tmp/quotas.yaml           (default)
    --sphere-map tmp/sphere_map.yaml   (default)
    --skip-enrich                      Reuse existing enriched_<kw>.csv files
    --skip-clean                       Reuse existing cleaned_<kw>.csv files

Then to actually push to Supabase, the operator runs:
    python executions/import_businesses_to_supabase.py \\
        --input <workdir>/ranked_quota.csv \\
        --city "<city>" \\
        --import-batch <city-slug>-<date> \\
        --respect-csv-tier \\
        --apply
"""

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime

import pandas as pd


def _norm_city_slug(s: str) -> str:
    """ASCII-ish slug suitable for filenames: NFKC + casefold + non-word -> '_'.
    Cyrillic preserved (works on NTFS)."""
    if not s:
        return "city"
    s = unicodedata.normalize("NFKC", str(s)).casefold().strip()
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    return s.strip("_") or "city"


def _city_filename_pattern(city: str) -> str:
    """Match the slugified city portion of scraper filenames. The scraper uses
    re.sub(r'[^\\w\\-]', '_', city.strip()) which preserves Cyrillic and
    replaces only spaces/punctuation with '_'."""
    return re.sub(r"[^\w\-]", "_", city.strip())


def _scraped_files_for_city(city: str, since: str | None, tmp_dir: str) -> list[tuple[str, str, str, str]]:
    """Return [(keyword_slug, ymd, hms, full_path)]. Skips ambiguous filenames
    where the city pattern could split the keyword/city boundary at more than
    one position (defensive against keywords that contain the city's first
    token literally)."""
    pat = _city_filename_pattern(city)
    pat_escaped = re.escape(pat)
    rx_lazy = re.compile(r"^scraped_(.+?)_" + pat_escaped + r"_(\d{8})_(\d{6})\.csv$")
    rx_greedy = re.compile(r"^scraped_(.+)_" + pat_escaped + r"_(\d{8})_(\d{6})\.csv$")
    out: list[tuple[str, str, str, str]] = []
    for fn in sorted(os.listdir(tmp_dir)):
        if not fn.startswith("scraped_") or not fn.endswith(".csv"):
            continue
        m_lazy = rx_lazy.match(fn)
        m_greedy = rx_greedy.match(fn)
        if not m_lazy or not m_greedy:
            continue
        if m_lazy.group(1) != m_greedy.group(1):
            print(f"WARN: ambiguous filename, skipping: {fn} (lazy='{m_lazy.group(1)}' vs greedy='{m_greedy.group(1)}')", file=sys.stderr)
            continue
        keyword_slug, ymd, hms = m_lazy.group(1), m_lazy.group(2), m_lazy.group(3)
        if since:
            since_compact = since.replace("-", "")
            if ymd < since_compact:
                continue
        out.append((keyword_slug, ymd, hms, os.path.join(tmp_dir, fn)))
    return out


def _run(cmd: list[str], log_path: str | None = None) -> int:
    print(f"  $ {' '.join(cmd)}")
    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        return r.returncode
    r = subprocess.run(cmd, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description="Per-city post-scrape orchestrator: enrich -> clean -> stamp -> dedupe -> rank.")
    ap.add_argument("--city", required=True, help="Bulgarian city name, e.g. 'Пловдив'.")
    ap.add_argument("--legacy-prefix", required=True, help="Short prefix for legacy_id stamping, e.g. 'plv', 'var', 'brg'.")
    ap.add_argument("--scraped-since", default=None, help="Only pick up scraped CSVs from this YYYY-MM-DD onward (avoids stale files from older runs).")
    ap.add_argument("--workdir", default=None, help="Per-city work folder (default: tmp/runs/<city-slug>).")
    ap.add_argument("--quotas", default="tmp/quotas.yaml")
    ap.add_argument("--sphere-map", default="tmp/sphere_map.yaml")
    ap.add_argument("--skip-enrich", action="store_true")
    ap.add_argument("--skip-clean", action="store_true")
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]{2,8}", args.legacy_prefix):
        ap.error("--legacy-prefix must be 2-8 lowercase alphanumerics, e.g. 'plv'")

    # Anchor tmp/ to the repo root so the orchestrator works regardless of CWD.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp_dir = os.path.join(repo_root, "tmp")

    city_slug = _norm_city_slug(args.city)
    workdir = args.workdir or os.path.join(tmp_dir, "runs", city_slug)
    enrich_dir = os.path.join(workdir, "enrich")
    clean_dir = os.path.join(workdir, "clean")
    for d in (workdir, enrich_dir, clean_dir):
        os.makedirs(d, exist_ok=True)

    raw = _scraped_files_for_city(args.city, args.scraped_since, tmp_dir)
    if not raw:
        print(f"ERROR: no scraped_*_{_city_filename_pattern(args.city)}_*.csv files found in {tmp_dir}/ for --city '{args.city}' (since={args.scraped_since}).", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(raw)} scraped file(s) for {args.city}.")

    # If multiple scraped files share the same keyword (e.g. a re-run created a
    # newer timestamp), keep the most recent one only — compare on (ymd, hms)
    # tuples extracted by the regex, not full path strings.
    by_kw: dict[str, tuple[str, str, str]] = {}
    for kw, ymd, hms, path in raw:
        cur = by_kw.get(kw)
        if cur is None or (ymd, hms) > (cur[0], cur[1]):
            by_kw[kw] = (ymd, hms, path)
    pairs: list[tuple[str, str]] = sorted((kw, v[2]) for kw, v in by_kw.items())
    print(f"After de-duplicating by keyword: {len(pairs)} pair(s).")

    # 1. ENRICH per keyword
    enriched_paths: list[tuple[str, str]] = []
    for kw, scraped_path in pairs:
        out = os.path.join(enrich_dir, f"enriched_{kw}.csv")
        if args.skip_enrich and os.path.exists(out):
            print(f"[enrich] SKIP {kw} (file exists)")
            enriched_paths.append((kw, out))
            continue
        log = os.path.join(enrich_dir, f"_log_{kw}.log")
        print(f"[enrich] {kw} -> {out}")
        rc = _run([sys.executable, "executions/enrich_providers.py", "--input", scraped_path, "--output-csv", out, "--no-search"], log_path=log)
        if rc != 0 or not os.path.exists(out):
            print(f"[enrich] FAILED for {kw} (rc={rc}). See {log}.", file=sys.stderr)
            continue
        enriched_paths.append((kw, out))
    print(f"[enrich] {len(enriched_paths)}/{len(pairs)} succeeded.")
    if not enriched_paths:
        print("ERROR: enrich produced 0 successful outputs. Aborting.", file=sys.stderr)
        sys.exit(1)

    # 2. CLEAN per keyword (drop viewport-spill rows mentioning OTHER cities)
    cleaned_paths: list[tuple[str, str]] = []
    for kw, enr_path in enriched_paths:
        out = os.path.join(clean_dir, f"cleaned_{kw}.csv")
        dropped = os.path.join(clean_dir, f"dropped_{kw}.csv")
        if args.skip_clean and os.path.exists(out):
            print(f"[clean] SKIP {kw} (file exists)")
            cleaned_paths.append((kw, out))
            continue
        print(f"[clean] {kw} -> {out}")
        rc = _run([sys.executable, "executions/clean_enriched.py", "--input", enr_path, "--kept", out, "--dropped", dropped, "--target-city", args.city])
        if rc != 0 or not os.path.exists(out):
            print(f"[clean] FAILED for {kw} (rc={rc}).", file=sys.stderr)
            continue
        cleaned_paths.append((kw, out))

    print(f"[clean] {len(cleaned_paths)}/{len(enriched_paths)} succeeded.")
    if not cleaned_paths:
        print("ERROR: clean produced 0 successful outputs. Aborting.", file=sys.stderr)
        sys.exit(1)

    # 3. STAMP legacy_id on cleaned files (positional <prefix>-<kw>-<NNN>).
    # Only fills BLANK rows so partial prior runs aren't clobbered.
    print(f"[stamp] adding legacy_id to {len(cleaned_paths)} cleaned file(s).")
    for kw, p in cleaned_paths:
        df = pd.read_csv(p, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        if "legacy_id" not in df.columns:
            df.insert(0, "legacy_id", "")
        existing = df["legacy_id"].astype(str).str.strip()
        # Find positional index of each blank row; counter `n` increments only
        # when we stamp, producing dense `<prefix>-<kw>-<NNN>` IDs.
        n = 0
        new_ids = []
        for cur in existing:
            if cur == "":
                n += 1
                new_ids.append(f"{args.legacy_prefix}-{kw}-{n:03d}")
            else:
                new_ids.append(cur)
        # Only rewrite if we actually changed anything.
        if any(a != b for a, b in zip(new_ids, existing.tolist())):
            df["legacy_id"] = new_ids
            tmp = p + ".tmp"
            df.to_csv(tmp, index=False, encoding="utf-8-sig")
            os.replace(tmp, p)

    # 4. DEDUPE across all cleaned files
    deduped_path = os.path.join(workdir, "deduped.csv")
    report_path = os.path.join(workdir, "dedupe_report.csv")
    print(f"[dedupe] -> {deduped_path}")
    cmd = [sys.executable, "executions/dedupe_across_categories.py", "--cleaned"]
    cmd.extend(p for _, p in cleaned_paths)
    cmd.extend(["--output", deduped_path, "--report", report_path])
    rc = _run(cmd)
    if rc != 0 or not os.path.exists(deduped_path):
        print("[dedupe] FAILED.", file=sys.stderr)
        sys.exit(rc)

    # 5. RANK + QUOTA
    ranked_path = os.path.join(workdir, "ranked_quota.csv")
    print(f"[rank] -> {ranked_path}")
    rc = _run([sys.executable, "executions/rank_and_quota.py",
               "--input", deduped_path,
               "--city", args.city,
               "--quotas", args.quotas,
               "--sphere-map", args.sphere_map,
               "--output", ranked_path])
    if rc != 0 or not os.path.exists(ranked_path):
        print("[rank] FAILED.", file=sys.stderr)
        sys.exit(rc)

    # 6. SUMMARY + next step hint
    print()
    print("=" * 60)
    print(f"DONE. Workdir: {workdir}")
    print(f"     Deduped:  {deduped_path}")
    print(f"     Ranked:   {ranked_path}")
    print()
    today = datetime.now().strftime("%Y-%m-%d")
    print("Next: dry-run import + apply")
    print(f"  python executions/import_businesses_to_supabase.py \\")
    print(f"    --input {ranked_path} \\")
    print(f"    --city \"{args.city}\" \\")
    print(f"    --import-batch {city_slug}-{today} \\")
    print(f"    --respect-csv-tier")
    print("  # then add --apply to push for real.")


if __name__ == "__main__":
    main()
