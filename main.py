#!/usr/bin/env python3
"""
Calibre Awards Tagger
Main orchestration script for enriching Calibre library with literary award tags.
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure stdout/stderr handle Unicode on Windows (e.g. author names with diacritics)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime
from typing import Optional, Tuple, List

import pandas as pd

from build_db import AWARD_SCRAPERS, build_canonical_database, get_cache_file
from lib_interface import get_calibre_books, batch_apply_tags, verify_calibredb, backup_metadata_db
from matcher import find_matches, generate_tag_assignments
from report import save_report, generate_text_report

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = log_dir / f'calibre_tagger_{timestamp}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

CANONICAL_DB_PATH = Path("data/canonical_awards.csv")


def summarize_canonical_database(db_path: Path = CANONICAL_DB_PATH) -> Tuple[List[str], Optional[pd.DataFrame]]:
    """
    Generate a human-friendly summary of the existing canonical database.

    Returns:
        (summary_lines, grouped_df) where summary_lines is a list of strings to
        print, and grouped_df contains per-award stats for selection prompts.
    """
    if not db_path.exists():
        return [f"No existing canonical database found at {db_path}."], None

    try:
        df = pd.read_csv(db_path)
    except Exception as e:
        logger.warning(f"Could not read canonical database ({db_path}): {e}")
        return [f"Could not load canonical database at {db_path}."], None

    if df.empty:
        return [f"Canonical database at {db_path} is empty."], None

    # Coerce years to numeric for span calculation
    df['year'] = pd.to_numeric(df['year'], errors='coerce')

    grouped = (
        df.groupby('prize')
        .agg(record_count=('title', 'size'), start_year=('year', 'min'), end_year=('year', 'max'))
        .reset_index()
        .sort_values('prize')
    )

    lines = [
        "Existing canonical awards database detected.",
        f"We have a total of {len(df)} book records.",
        "By award:",
    ]

    for row in grouped.itertuples():
        start = int(row.start_year) if pd.notna(row.start_year) else "?"
        end = int(row.end_year) if pd.notna(row.end_year) else "?"
        lines.append(f"  - {row.prize}: {row.record_count} records ({start}–{end})")

    return lines, grouped


def prompt_yes_no(message: str) -> bool:
    """Prompt until user types Y or N (case-insensitive)."""
    while True:
        response = input(message).strip().lower()
        if response in ("y", "n"):
            return response == "y"
        print("Please type Y and Enter, or N and Enter.")


def prompt_award_choice() -> str:
    """Let the user pick a single award key to scrape by number or name."""
    award_keys = list(AWARD_SCRAPERS.keys())
    print("\nAvailable awards:")
    for idx, key in enumerate(award_keys, start=1):
        cache_file = get_cache_file(key)
        cached = "✓ cached" if cache_file.exists() else "✗ not cached"
        print(f"  [{idx}] {key:25s} {cached}")

    while True:
        raw = input("Choose an award by number or key: ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(award_keys):
                return award_keys[idx]

        normalized = raw.lower().replace(" ", "_")
        for key in award_keys:
            if key.lower() == normalized:
                return key

        print("Please choose a valid award (number or key).")


def main():
    """Main entry point for the Calibre Awards Tagger."""
    parser = argparse.ArgumentParser(
        description='Tag Calibre library books with literary award information'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show proposed changes without applying them'
    )
    parser.add_argument(
        '--rebuild-db',
        action='store_true',
        help='Rebuild the canonical awards database from scratch'
    )
    parser.add_argument(
        '--skip-scrape',
        action='store_true',
        help='Skip scraping and use existing database (faster for testing)'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Print per-award canonical database summary and exit (no Calibre or tag actions)'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Calibre Awards Tagger")
    logger.info("=" * 80)
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info(f"Rebuild database: {args.rebuild_db}")
    logger.info(f"Skip scraping: {args.skip_scrape}")
    logger.info("")

    try:
        # Show current database summary to help user decide about scraping
        summary_lines, _award_summary = summarize_canonical_database()
        if summary_lines:
            print("\n" + "=" * 80)
            for line in summary_lines:
                print(line)
            print("=" * 80 + "\n")

        # Optional early exit if the user only wants the summary
        if args.summary_only:
            logger.info("Summary-only mode: exiting after printing canonical database summary.")
            return

        # Scraping confirmation flow
        scrape_awards_list: List[str] = []
        scrape_all_awards = False
        if not args.skip_scrape:
            print("Scraping is slow and network-heavy. A rich canonical database is already included.")
            print("Type Y and Enter to scrape fresh data, or N and Enter to skip scraping.")
            if not prompt_yes_no("Scrape now? [Y/N]: "):
                args.skip_scrape = True
                logger.info("User chose to skip scraping; using existing canonical database.")
            else:
                if args.rebuild_db:
                    scrape_all_awards = True
                    logger.info("--rebuild-db requested; will re-scrape all awards (refresh caches).")
                elif prompt_yes_no("Scrape all awards? [Y/N] (N lets you pick one award): "):
                    scrape_all_awards = True
                else:
                    chosen = prompt_award_choice()
                    scrape_awards_list = [chosen]
                    logger.info(f"User chose to scrape only: {chosen}")
        # Step 0: Verify calibredb is available
        logger.info("Verifying Calibre installation...")
        if not verify_calibredb():
            logger.error("calibredb not found. Please install Calibre and ensure it's in your PATH.")
            sys.exit(1)

        # Step 1: Build/update canonical awards database
        if not args.skip_scrape:
            logger.info("Step 1: Building canonical awards database...")
            try:
                db_file = build_canonical_database(
                    scrape_awards_list=scrape_awards_list,
                    scrape_all=scrape_all_awards,
                )
                logger.info(f"Database ready: {db_file}")
            except Exception as e:
                logger.error(f"Failed to build database: {e}")
                sys.exit(1)
        else:
            db_file = Path("data/canonical_awards.csv")
            if not db_file.exists():
                logger.error(f"Database file not found: {db_file}")
                logger.error("Run without --skip-scrape to build the database first")
                sys.exit(1)
            logger.info(f"Using existing database: {db_file}")

        # Load awards database
        logger.info("")
        logger.info("Loading awards database...")
        awards_df = pd.read_csv(db_file)
        logger.info(f"Loaded {len(awards_df)} award records")

        # Step 2: Extract Calibre library data
        logger.info("")
        logger.info("Step 2: Extracting Calibre library data...")
        try:
            books = get_calibre_books()
            logger.info(f"Found {len(books)} books in Calibre library")
        except Exception as e:
            logger.error(f"Failed to extract Calibre books: {e}")
            sys.exit(1)

        # Step 3: Match and generate proposed tags
        logger.info("")
        logger.info("Step 3: Matching books with award records...")
        matches = find_matches(books, awards_df)
        logger.info(f"Found {len(matches)} total matches")

        if not matches:
            logger.info("No matches found. Nothing to do.")
            return

        # Generate tag assignments
        tag_assignments = generate_tag_assignments(matches)
        logger.info(f"Generated tag assignments for {len(tag_assignments)} books")

        # Step 4: Generate reports
        logger.info("")
        logger.info("Step 4: Generating reports...")
        report_dir = Path("data")
        json_report = report_dir / f"proposed_changes_{timestamp}.json"
        text_report = report_dir / f"proposed_changes_{timestamp}.txt"

        save_report(matches, json_report, text_report)

        # Step 5: Apply tags (if not dry-run)
        logger.info("")
        if args.dry_run:
            logger.info("DRY RUN MODE: No changes will be applied")
            logger.info("")
            print("\n" + generate_text_report(matches))
            logger.info("")
            logger.info("To apply these changes, run without --dry-run flag")
        else:
            logger.info("Step 5: Applying tags to Calibre library...")

            # Confirm with user
            print("\n" + "=" * 80)
            print(f"About to apply tags to {len(tag_assignments)} books.")
            print(f"Total of {len(matches)} tags will be added.")
            print("=" * 80)
            response = input("\nProceed? (yes/no): ").strip().lower()

            if response != 'yes':
                logger.info("User cancelled tag application")
                print("Operation cancelled.")
                return

            # Backup metadata.db before making changes
            print("\n" + "=" * 80)
            print("SAFETY: Creating backup of metadata.db...")
            print("=" * 80)
            backup_path = backup_metadata_db()

            if backup_path:
                print(f"✓ Backup created: {backup_path}")
                print("\nIf anything goes wrong, you can restore by:")
                print("  1. Close Calibre")
                print(f"  2. Copy {backup_path}")
                print(f"     to metadata.db")
                print("=" * 80)
            else:
                print("✗ Warning: Could not create automatic backup!")
                print("\nYou can still restore from Calibre's built-in OPF backups:")
                print("  Calibre → Library Maintenance → Restore database")
                print("=" * 80)
                response = input("\nProceed without backup? (yes/no): ").strip().lower()
                if response != 'yes':
                    logger.info("User cancelled due to backup failure")
                    print("Operation cancelled.")
                    return

            # Apply tags
            results = batch_apply_tags(tag_assignments)

            # Report results
            success_count = sum(1 for success in results.values() if success)
            failure_count = len(results) - success_count

            logger.info("")
            logger.info("=" * 80)
            logger.info("TAG APPLICATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Success: {success_count} books")
            logger.info(f"Failed: {failure_count} books")

            if failure_count > 0:
                logger.warning("Some tags failed to apply. Check logs for details.")

        logger.info("")
        logger.info("=" * 80)
        logger.info("Calibre Awards Tagger completed successfully")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
