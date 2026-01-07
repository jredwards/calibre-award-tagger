"""
Scrapers for general fiction literary awards.
Covers: Booker Prize, International Booker, National Book Award, Scotiabank Giller Prize.
"""

import logging
from typing import List
import pandas as pd
from .base_wiki import fetch_wiki_tables, clean_dataframe, extract_year
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)


def scrape_booker_prize() -> List[AwardRecord]:
    """
    Scrape Booker Prize winners and shortlists.

    Returns:
        List of award records
    """
    logger.info("Scraping Booker Prize")
    url = "https://en.wikipedia.org/wiki/Booker_Prize"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Look for tables with Year, Author, Title columns
        # Booker has separate winner and shortlist tables
        if 'Year' in df.columns and ('Author' in df.columns or 'Writer' in df.columns) and 'Title' in df.columns:
            author_col = 'Author' if 'Author' in df.columns else 'Writer'

            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                author = str(row[author_col]).strip()
                title = str(row['Title']).strip()

                if author and title and author != 'nan' and title != 'nan':
                    # Determine if winner or shortlist based on table context
                    # For now, assume winners (we'll handle shortlists separately if needed)
                    records.append({
                        'prize': 'Booker',
                        'category': 'Fiction',
                        'year': year,
                        'status': AwardStatus.WINNER.value,
                        'title': title,
                        'author': author
                    })

    logger.info(f"Found {len(records)} Booker Prize records")
    return records


def scrape_international_booker() -> List[AwardRecord]:
    """
    Scrape International Booker Prize (author only, not translator).

    Returns:
        List of award records
    """
    logger.info("Scraping International Booker Prize")
    url = "https://en.wikipedia.org/wiki/International_Booker_Prize"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Look for Year, Author, and Title/Work columns
        # International Booker uses "Work" column in newer tables
        if 'Year' in df.columns and 'Author' in df.columns and ('Title' in df.columns or 'Work' in df.columns):
            title_col = 'Title' if 'Title' in df.columns else 'Work'

            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                author = str(row['Author']).strip()
                title = str(row[title_col]).strip()

                if author and title and author != 'nan' and title != 'nan':
                    records.append({
                        'prize': 'International Booker',
                        'category': 'Fiction',
                        'year': year,
                        'status': AwardStatus.WINNER.value,
                        'title': title,
                        'author': author
                    })

    logger.info(f"Found {len(records)} International Booker Prize records")
    return records


def scrape_national_book_award() -> List[AwardRecord]:
    """
    Scrape National Book Award for Fiction.

    Returns:
        List of award records
    """
    logger.info("Scraping National Book Award for Fiction")
    url = "https://en.wikipedia.org/wiki/National_Book_Award_for_Fiction"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Look for Year, Author, Title columns
        if 'Year' in df.columns and 'Author' in df.columns and 'Title' in df.columns:
            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                author = str(row['Author']).strip()
                title = str(row['Title']).strip()

                if author and title and author != 'nan' and title != 'nan':
                    records.append({
                        'prize': 'National Book Award',
                        'category': 'Fiction',
                        'year': year,
                        'status': AwardStatus.WINNER.value,
                        'title': title,
                        'author': author
                    })

    logger.info(f"Found {len(records)} National Book Award records")
    return records


def scrape_giller_prize() -> List[AwardRecord]:
    """
    Scrape Scotiabank Giller Prize.

    Returns:
        List of award records
    """
    logger.info("Scraping Giller Prize")
    url = "https://en.wikipedia.org/wiki/Giller_Prize"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Look for Year, Author, Title columns
        if 'Year' in df.columns and 'Author' in df.columns and 'Book' in df.columns:
            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                author = str(row['Author']).strip()
                title = str(row['Book']).strip()

                if author and title and author != 'nan' and title != 'nan':
                    records.append({
                        'prize': 'Giller',
                        'category': 'Fiction',
                        'year': year,
                        'status': AwardStatus.WINNER.value,
                        'title': title,
                        'author': author
                    })

    logger.info(f"Found {len(records)} Giller Prize records")
    return records


def scrape_all_general_fiction() -> pd.DataFrame:
    """
    Scrape all general fiction awards and return as DataFrame.

    Returns:
        DataFrame with all general fiction award records
    """
    all_records = []

    try:
        all_records.extend(scrape_booker_prize())
    except Exception as e:
        logger.error(f"Failed to scrape Booker Prize: {e}")

    try:
        all_records.extend(scrape_international_booker())
    except Exception as e:
        logger.error(f"Failed to scrape International Booker: {e}")

    try:
        all_records.extend(scrape_national_book_award())
    except Exception as e:
        logger.error(f"Failed to scrape National Book Award: {e}")

    try:
        all_records.extend(scrape_giller_prize())
    except Exception as e:
        logger.error(f"Failed to scrape Giller Prize: {e}")

    df = pd.DataFrame(all_records)
    logger.info(f"Total general fiction records: {len(df)}")

    return df
