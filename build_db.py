"""
Build the canonical awards database with selective scraping and per-award caching.

Each award is cached separately so we only re-scrape what's needed.
"""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from author_normalizer import AuthorNormalizer, normalize_title
from schema import CSV_COLUMNS

logger = logging.getLogger(__name__)

# Output files
CANONICAL_DB_FILE = Path("data/canonical_awards.csv")
CACHE_DIR = Path("data/cache")

# Award scraper mapping
AWARD_SCRAPERS = {
    "hugo": ("scrapers.wikidata_scraper", "scrape_award", "hugo"),
    "nebula": ("scrapers.wikidata_scraper", "scrape_award", "nebula"),
    "clarke": ("scrapers.wikidata_scraper", "scrape_award", "clarke"),
    "booker": ("scrapers.wikidata_scraper", "scrape_award", "booker"),
    "international_booker": ("scrapers.wikidata_scraper", "scrape_award", "international_booker"),
    "locus_scifi": ("scrapers.wikidata_scraper", "scrape_award", "locus_scifi"),
    "locus_fantasy": ("scrapers.wikidata_scraper", "scrape_award", "locus_fantasy"),
    "locus_horror": ("scrapers.wikidata_scraper", "scrape_award", "locus_horror"),
    "agatha": ("scrapers.agatha_scraper", "scrape_agatha_awards", None),
    "national_book_award": ("scrapers.nba_scraper", "scrape_nba_fiction", None),
    "giller": ("scrapers.giller_scraper", "scrape_giller_prize", None),
    "pulitzer": ("scrapers.pulitzer_scraper", "scrape_pulitzer_fiction", None),
}


def get_cache_file(award_key: str) -> Path:
    """Return the cache path for an award key."""
    return CACHE_DIR / f"{award_key}.csv"


def load_award_from_cache(award_key: str) -> pd.DataFrame:
    """
    Load an award's data from cache.

    Returns an empty DataFrame if the cache is missing or cannot be read.
    """
    cache_file = get_cache_file(award_key)
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file)
            logger.info(f"Loaded {len(df)} records for {award_key} from cache")
            return df
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"Failed to load cache for {award_key}: {exc}")

    return pd.DataFrame(columns=CSV_COLUMNS)


def save_award_to_cache(award_key: str, df: pd.DataFrame) -> None:
    """Persist a scraped award DataFrame to the cache directory."""
    cache_file = get_cache_file(award_key)
    cache_file.parent.mkdir(exist_ok=True, parents=True)

    try:
        df.to_csv(cache_file, index=False)
        logger.info(f"Saved {len(df)} records for {award_key} to cache")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"Failed to save cache for {award_key}: {exc}")


def scrape_single_award(award_key: str) -> pd.DataFrame:
    """Scrape data for a single award."""
    if award_key not in AWARD_SCRAPERS:
        logger.error(f"Unknown award: {award_key}")
        return pd.DataFrame(columns=CSV_COLUMNS)

    module_name, function_name, arg = AWARD_SCRAPERS[award_key]

    try:
        module = __import__(module_name, fromlist=[function_name])
        scraper_func = getattr(module, function_name)

        if arg:
            records = scraper_func(arg)
            df = pd.DataFrame(records) if isinstance(records, list) else pd.DataFrame()
        else:
            df = scraper_func()

        logger.info(f"Scraped {len(df)} records for {award_key}")
        return df
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"Failed to scrape {award_key}: {exc}")
        return pd.DataFrame(columns=CSV_COLUMNS)


def scrape_awards(award_keys: List[str]) -> pd.DataFrame:
    """
    Scrape specified awards and load others from cache.

    If award_keys is empty, all awards are loaded from cache.
    """
    all_award_keys = list(AWARD_SCRAPERS.keys())
    all_awards_data: List[pd.DataFrame] = []

    for award_key in all_award_keys:
        if award_key in award_keys:
            logger.info(f"Scraping {award_key}...")
            df = scrape_single_award(award_key)
            if not df.empty:
                save_award_to_cache(award_key, df)
                all_awards_data.append(df)
        else:
            logger.info(f"Loading {award_key} from cache...")
            df = load_award_from_cache(award_key)
            if not df.empty:
                all_awards_data.append(df)
            else:
                logger.warning(f"No cached data for {award_key}, skipping")

    if all_awards_data:
        combined_df = pd.concat(all_awards_data, ignore_index=True)
        logger.info(f"Combined {len(combined_df)} total records from {len(all_awards_data)} awards")
        return combined_df

    logger.warning("No award data collected")
    return pd.DataFrame(columns=CSV_COLUMNS)


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize book titles and author names."""
    logger.info("Normalizing award data")
    df = df.copy()

    # Drop rows where Wikidata returned a Q-ID instead of a label (data quality issue
    # caused by P50/title entities with no English label, or photo entities mis-linked).
    qid = df["author"].str.match(r"^Q\d+$", na=False) | df["title"].str.match(r"^Q\d+$", na=False)
    if qid.any():
        logger.warning(f"Dropping {qid.sum()} records with Q-ID author/title: {df[qid][['prize','year','title','author']].to_dict('records')}")
        df = df[~qid]

    df["title"] = df["title"].apply(normalize_title)

    normalizer = AuthorNormalizer()
    unique_authors = set(df["author"].unique())
    logger.info(f"Found {len(unique_authors)} unique authors")

    author_map = normalizer.batch_normalize(unique_authors)
    df["author"] = df["author"].map(author_map)
    logger.info("Normalization complete")
    return df


def deduplicate_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate award records.

    A duplicate is defined as: same prize, category, year, title, author.
    If status differs, keep Winner > Shortlist > Nominee.
    """
    logger.info("Removing duplicate records...")
    initial_count = len(df)
    status_priority = {"Winner": 1, "Shortlist": 2, "Nominee": 3}

    df["_status_priority"] = df["status"].map(status_priority)
    df = df.sort_values("_status_priority")
    df = df.drop_duplicates(
        subset=["prize", "category", "year", "title", "author"],
        keep="first",
    )
    df = df.drop(columns=["_status_priority"])

    removed = initial_count - len(df)
    logger.info(f"Removed {removed} duplicate records ({len(df)} remaining)")
    return df


def list_awards_with_cache_status() -> List[tuple[str, bool]]:
    """Return (award_key, cached?) tuples for all known awards."""
    return [(key, get_cache_file(key).exists()) for key in AWARD_SCRAPERS.keys()]


def build_canonical_database(
    scrape_awards_list: Optional[List[str]] = None,
    scrape_all: bool = False,
) -> Path:
    """
    Build the canonical awards database with optional selective scraping.

    Args:
        scrape_awards_list: List of award keys to scrape. If None, load all from
            cache. If empty list, load all from cache. Any awards not scraped are
            loaded from cache (if present).
        scrape_all: When True, scrape every award and refresh caches before
            building the database (overrides scrape_awards_list).
    """
    if scrape_all:
        scrape_awards_list = list(AWARD_SCRAPERS.keys())
    if scrape_awards_list is None:
        scrape_awards_list = []

    logger.info("Building canonical database")
    if scrape_awards_list:
        logger.info(f"  Scraping: {', '.join(scrape_awards_list)}")
        logger.info("  Loading from cache: remaining awards")
    else:
        logger.info("  Loading all awards from cache (no scraping)")

    df = scrape_awards(scrape_awards_list)
    if df.empty:
        logger.error("No data available, cannot build database")
        raise ValueError("No award data could be loaded")

    df = normalize_data(df)
    df = deduplicate_records(df)
    df = df.sort_values(by=["year", "prize", "status"], ascending=[False, True, True])
    df = df[CSV_COLUMNS]

    CANONICAL_DB_FILE.parent.mkdir(exist_ok=True)
    df.to_csv(CANONICAL_DB_FILE, index=False)

    logger.info(f"Canonical database saved to {CANONICAL_DB_FILE}")
    logger.info(f"Total records in database: {len(df)}")
    logger.info("\nDatabase Summary:")
    logger.info(f"  Total records: {len(df)}")
    logger.info(f"  Unique prizes: {df['prize'].nunique()}")
    logger.info(f"  Unique books: {df['title'].nunique()}")
    logger.info(f"  Unique authors: {df['author'].nunique()}")
    logger.info(f"  Year range: {df['year'].min()} - {df['year'].max()}")
    logger.info("\nRecords by prize:")
    for prize, count in df["prize"].value_counts().items():
        logger.info(f"    {prize}: {count}")
    logger.info("\nRecords by status:")
    for status, count in df["status"].value_counts().items():
        logger.info(f"    {status}: {count}")

    return CANONICAL_DB_FILE


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    import argparse

    parser = argparse.ArgumentParser(
        description="Build canonical awards database with selective scraping",
        epilog=f"Available awards: {', '.join(AWARD_SCRAPERS.keys())}",
    )
    parser.add_argument(
        "--scrape",
        type=str,
        help='Comma-separated list of awards to scrape (e.g., "hugo,nebula,giller"). Others will be loaded from cache.',
    )
    parser.add_argument(
        "--scrape-all",
        action="store_true",
        help="Scrape all awards (ignores --scrape)",
    )
    parser.add_argument(
        "--list-awards",
        action="store_true",
        help="List all available awards and exit",
    )
    args = parser.parse_args()

    if args.list_awards:
        print("Available awards:")
        for key, cached in list_awards_with_cache_status():
            cache_file = get_cache_file(key)
            cached_marker = "[cached]" if cached else "[not cached]"
            print(f"  {key:25s} {cached_marker} ({cache_file})")
        raise SystemExit(0)

    if args.scrape_all:
        scrape_list: List[str] = list(AWARD_SCRAPERS.keys())
    elif args.scrape:
        scrape_list = [s.strip() for s in args.scrape.split(",") if s.strip()]
        invalid = [s for s in scrape_list if s not in AWARD_SCRAPERS]
        if invalid:
            print(f"Error: Unknown awards: {', '.join(invalid)}")
            print(f"Available awards: {', '.join(AWARD_SCRAPERS.keys())}")
            raise SystemExit(1)
    else:
        scrape_list = []

    build_canonical_database(scrape_awards_list=scrape_list, scrape_all=args.scrape_all)
