import os
import sys
import subprocess
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: scrape Google Maps -> enrich with contacts -> CSV + Google Sheets"
    )
    parser.add_argument("--keyword", help="Search keyword (e.g. 'детска градина')")
    parser.add_argument("--city", help="City name (e.g. 'София')")
    parser.add_argument("--input", help="CSV/Excel with 'keyword' and 'city' columns for batch mode")
    parser.add_argument("--headed", action="store_true", help="Show browser window during scraping")
    parser.add_argument("--resume", action="store_true", help="Skip already-completed steps")
    parser.add_argument("--sheet-id", required=True, help="Google Sheets ID for enrichment output")
    parser.add_argument("--sheet-name", default="Enriched", help="Sheet tab name (default: Enriched)")
    parser.add_argument("--no-search", action="store_true", help="Skip Google search in enrichment (crawl only)")
    args = parser.parse_args()

    tools_dir = os.path.dirname(os.path.abspath(__file__))

    # --- Step 1: Scrape Google Maps ---
    print("=" * 60)
    print("STEP 1: Scraping Google Maps")
    print("=" * 60)

    scrape_cmd = [sys.executable, os.path.join(tools_dir, "scrape_google_maps.py")]
    if args.keyword:
        scrape_cmd += ["--keyword", args.keyword]
    if args.city:
        scrape_cmd += ["--city", args.city]
    if args.input:
        scrape_cmd += ["--input", args.input]
    if args.headed:
        scrape_cmd += ["--headed"]
    if args.resume:
        scrape_cmd += ["--resume"]

    scrape_result = subprocess.run(scrape_cmd, capture_output=False, text=True, stdout=subprocess.PIPE)

    if scrape_result.stdout:
        for line in scrape_result.stdout.splitlines():
            if not line.startswith("OUTPUT_CSV:"):
                print(line)

    csv_paths = [
        line.split("OUTPUT_CSV:", 1)[1].strip()
        for line in (scrape_result.stdout or "").splitlines()
        if line.startswith("OUTPUT_CSV:")
    ]

    if not csv_paths:
        print("\nNo CSV output from scraper — nothing to enrich. Exiting.")
        sys.exit(0)

    print(f"\nScraper produced {len(csv_paths)} CSV file(s).")

    # --- Step 2: Enrich each CSV ---
    print("\n" + "=" * 60)
    print("STEP 2: Enriching with contacts and social profiles")
    print("=" * 60)

    for i, csv_path in enumerate(csv_paths, 1):
        print(f"\n[{i}/{len(csv_paths)}] Enriching: {csv_path}")

        enrich_cmd = [
            sys.executable, os.path.join(tools_dir, "enrich_providers.py"),
            "--input", csv_path,
            "--sheet-id", args.sheet_id,
            "--sheet-name", args.sheet_name,
        ]
        if args.resume:
            enrich_cmd += ["--resume"]
        if args.no_search:
            enrich_cmd += ["--no-search"]

        subprocess.run(enrich_cmd, check=True)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print(f"Results in Google Sheets: https://docs.google.com/spreadsheets/d/{args.sheet_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
