#!/usr/bin/env python3
"""
Job Scraper Tool
  - Auto-generates company list from location (tech, startups, quant, trading)
  - OR reads companies from an Excel file
  - Filters by skills, locations, and experience level
  - Outputs matching jobs to CSV
"""
import argparse
import os
import sys
import time

import requests

from companies_db import get_companies_for_location
from config import EXPERIENCE_LEVELS
from csv_io import write_results_csv
from excel_io import read_companies
from scraper import scrape_company_jobs

VALID_CATEGORIES = ["big_tech", "startup", "quant", "trading", "fintech"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape job listings from company career pages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-generate companies from a location (all categories):
  python main.py --scrape-location "New York" --skills "Python" "Machine Learning"

  # Only quant and trading firms in New York:
  python main.py --scrape-location "New York" --categories quant trading --experience senior mid

  # Remote-friendly startups, multiple skills:
  python main.py --scrape-location remote --categories startup --skills "Go" "Kubernetes" "gRPC"

  # Use your own Excel company list:
  python main.py --input companies.xlsx --skills "System Design" "Distributed Systems"
  python main.py --input companies.xlsx --locations "Remote" "Bangalore" --experience senior mid
        """,
    )

    # ── Source mode ──────────────────────────────────────────────────────────
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--scrape-location", "-L",
        metavar="LOCATION",
        help=(
            "Generate company list automatically for this location "
            "(e.g. 'New York', 'San Francisco', 'Remote', 'Bangalore'). "
            "Use 'any' to include all locations."
        ),
    )
    source.add_argument(
        "--input", "-i",
        metavar="FILE",
        help="Path to input Excel file (.xlsx) with Company Name / Domain columns.",
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    parser.add_argument(
        "--skills", "-s",
        nargs="+",
        default=[],
        metavar="SKILL",
        help=(
            "One or more skills to filter by. "
            "Jobs must mention at least one skill. "
            "Example: --skills Python 'Machine Learning' 'System Design'"
        ),
    )
    parser.add_argument(
        "--locations", "-l",
        nargs="+",
        default=[],
        metavar="LOC",
        help=(
            "Filter job postings by location keywords "
            "(e.g. 'Remote' 'New York' 'Bangalore'). "
            "Defaults to any location."
        ),
    )
    parser.add_argument(
        "--experience", "-e",
        nargs="+",
        default=[],
        choices=list(EXPERIENCE_LEVELS.keys()),
        metavar="LEVEL",
        help=(
            f"Experience levels to include. Choices: {', '.join(EXPERIENCE_LEVELS)}. "
            "Jobs with no experience info are always included."
        ),
    )
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        default=[],
        choices=VALID_CATEGORIES,
        metavar="CAT",
        help=(
            f"Company categories when using --scrape-location. "
            f"Choices: {', '.join(VALID_CATEGORIES)}. Defaults to all."
        ),
    )

    # ── Output / misc ─────────────────────────────────────────────────────────
    parser.add_argument(
        "--output", "-o",
        default="",
        metavar="FILE",
        help="Output CSV file path. Defaults to job_results_<timestamp>.csv",
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=1.0,
        metavar="SECS",
        help="Delay in seconds between companies (default: 1.0)",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=0,
        metavar="N",
        help="Maximum number of companies to scrape (0 = unlimited)",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # ── Set output path ───────────────────────────────────────────────────────
    if not args.output:
        args.output = f"job_results_{time.strftime('%Y%m%d_%H%M%S')}.csv"

    # ── Load companies ────────────────────────────────────────────────────────
    if args.scrape_location:
        location_input = args.scrape_location
        categories = args.categories if args.categories else None
        companies = get_companies_for_location([location_input], categories)
        print(f"[*] Auto-generated company list for location: '{location_input}'")
        if categories:
            print(f"    Categories: {', '.join(categories)}")
        print(f"[+] {len(companies)} companies found in database")
    else:
        if not os.path.exists(args.input):
            print(f"[ERROR] Input file not found: {args.input}")
            sys.exit(1)
        print(f"[*] Reading companies from: {args.input}")
        companies = read_companies(args.input)
        print(f"[+] Found {len(companies)} companies")

    if not companies:
        print("[!] No companies found. Check the location / file / filters.")
        sys.exit(1)

    if args.limit and args.limit > 0:
        companies = companies[: args.limit]
        print(f"[*] Limiting to {len(companies)} companies (--limit {args.limit})")

    # ── Print filter settings ─────────────────────────────────────────────────
    print("\n[*] Filter settings:")
    print(f"    Skills     : {', '.join(args.skills) if args.skills else 'Any'}")
    print(f"    Locations  : {', '.join(args.locations) if args.locations else 'Any'}")
    print(f"    Experience : {', '.join(args.experience) if args.experience else 'Any (incl. unspecified)'}")
    print()

    # ── Scrape ────────────────────────────────────────────────────────────────
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    })

    all_jobs: list[dict] = []
    for idx, company in enumerate(companies):
        try:
            jobs = scrape_company_jobs(
                company, args.skills, args.locations, args.experience, session
            )
            all_jobs.extend(jobs)
        except KeyboardInterrupt:
            print("\n\n[!] Interrupted. Saving results so far...")
            break
        except Exception as e:
            print(f"  [!] Error scraping {company['name']}: {e}")
        if idx < len(companies) - 1:
            time.sleep(args.delay)

    # ── Output ────────────────────────────────────────────────────────────────
    if all_jobs:
        write_results_csv(args.output, all_jobs)
    else:
        print("\n[!] No matching jobs found. Try broadening your filters.")

    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    print(f"  Companies scraped : {len(companies)}")
    print(f"  Total jobs found  : {len(all_jobs)}")
    if all_jobs:
        print(f"  Results saved to  : {args.output}")


if __name__ == "__main__":
    main()
