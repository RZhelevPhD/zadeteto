"""
Script: run_content_intelligence.py
Purpose: Orchestrate the full content intelligence pipeline: fetch -> analyze -> research -> PDF.
Input: --profile (authority profile name), optional --platforms and --languages filters.
Output: PDF reports in reports/content/ for each platform/language combination.
Dependencies: All dependencies from fetch_social_data, analyze_outliers, research_trends, generate_content_report.
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime

PLATFORMS = ["facebook", "instagram", "linkedin"]
LANGUAGES = ["BG", "ENG", "SP"]


def _run_step(cmd: list[str], step_name: str) -> subprocess.CompletedProcess:
    """Run a subprocess step and handle errors."""
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.stdout:
        for line in result.stdout.splitlines():
            print(f"  {line}")

    if result.returncode != 0:
        print(f"  WARNING: {step_name} exited with code {result.returncode}")
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                print(f"  ERROR: {line}")

    return result


def _extract_output_path(stdout: str, prefix: str) -> str:
    """Extract output path from stdout lines like OUTPUT_JSON:path."""
    for line in (stdout or "").splitlines():
        if line.startswith(prefix):
            return line.split(prefix, 1)[1].strip()
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Run the full content intelligence pipeline for all platform/language combos"
    )
    parser.add_argument("--profile", required=True, help="Authority profile name (e.g. 'childcare', 'marketing')")
    parser.add_argument("--authorities", default="authorities.json", help="Path to authorities JSON file")
    parser.add_argument("--platforms", nargs="*", default=None,
                        help="Platforms to process (default: all). Choices: facebook instagram linkedin")
    parser.add_argument("--languages", nargs="*", default=None,
                        help="Languages to process (default: all). Choices: BG ENG SP")
    parser.add_argument("--days-back", type=int, default=7, help="Days of posts to fetch (default: 7)")
    parser.add_argument("--skip-research", action="store_true", help="Skip trend research step (faster)")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top posts per report (default: 10)")
    parser.add_argument("--mode", default="both", choices=["authority", "discovery", "both"],
                        help="authority=tracked accounts, discovery=topic search, both=merge (default)")
    args = parser.parse_args()

    platforms = args.platforms or PLATFORMS
    languages = args.languages or LANGUAGES
    tools_dir = os.path.dirname(os.path.abspath(__file__))

    # Validate profile exists
    with open(args.authorities, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    if "profiles" in auth_data and args.profile not in auth_data["profiles"]:
        print(f"ERROR: Profile '{args.profile}' not found. Available: {list(auth_data['profiles'].keys())}")
        sys.exit(1)

    total_combos = len(platforms) * len(languages)
    completed = 0
    reports = []

    print(f"\nContent Intelligence Pipeline")
    print(f"Profile: {args.profile}")
    print(f"Platforms: {', '.join(platforms)}")
    print(f"Languages: {', '.join(languages)}")
    print(f"Total reports to generate: {total_combos}")
    print(f"{'='*60}")

    for platform in platforms:
        for language in languages:
            completed += 1
            combo_label = f"{platform.upper()}/{language}"
            print(f"\n{'#'*60}")
            print(f"  [{completed}/{total_combos}] Processing: {combo_label}")
            print(f"{'#'*60}")

            # Step 1: Fetch
            fetch_result = _run_step([
                sys.executable, os.path.join(tools_dir, "fetch_social_data.py"),
                "--platform", platform,
                "--language", language,
                "--authorities", args.authorities,
                "--profile", args.profile,
                "--days-back", str(args.days_back),
                "--mode", args.mode,
            ], f"FETCH: {combo_label}")

            posts_path = _extract_output_path(fetch_result.stdout, "OUTPUT_JSON:")
            if not posts_path or not os.path.exists(posts_path):
                print(f"  SKIP {combo_label}: No posts fetched")
                continue

            # Step 2: Analyze
            analyze_result = _run_step([
                sys.executable, os.path.join(tools_dir, "analyze_outliers.py"),
                "--input", posts_path,
                "--top-n", str(args.top_n),
            ], f"ANALYZE: {combo_label}")

            analysis_path = _extract_output_path(analyze_result.stdout, "OUTPUT_JSON:")
            if not analysis_path or not os.path.exists(analysis_path):
                print(f"  SKIP {combo_label}: Analysis failed")
                continue

            # Step 3: Research trends (optional)
            if not args.skip_research:
                research_result = _run_step([
                    sys.executable, os.path.join(tools_dir, "research_trends.py"),
                    "--input", analysis_path,
                    "--max-posts", str(min(args.top_n, 10)),
                ], f"RESEARCH: {combo_label}")

                # research_trends overwrites the analysis file by default
                research_path = _extract_output_path(research_result.stdout, "OUTPUT_JSON:")
                if research_path:
                    analysis_path = research_path

            # Step 4: Generate PDF
            pdf_result = _run_step([
                sys.executable, os.path.join(tools_dir, "generate_content_report.py"),
                "--input", analysis_path,
            ], f"REPORT: {combo_label}")

            pdf_path = _extract_output_path(pdf_result.stdout, "OUTPUT_PDF:")
            if pdf_path:
                reports.append({"platform": platform, "language": language, "path": pdf_path})

    # Summary
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Reports generated: {len(reports)}/{total_combos}")
    for r in reports:
        print(f"  {r['platform'].upper()}/{r['language']}: {r['path']}")

    if not reports:
        print("\nNo reports generated. Check that authorities.json has entries for the selected profile/platform/language combos.")


if __name__ == "__main__":
    main()
