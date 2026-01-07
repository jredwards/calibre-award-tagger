"""
Scrapers for science fiction and fantasy awards.
Covers: Hugo Award, Nebula Award, Arthur C. Clarke Award.
"""

import logging
from typing import List
import pandas as pd
from .base_wiki import fetch_wiki_tables, clean_dataframe, extract_year
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)


def scrape_hugo_award() -> List[AwardRecord]:
    """
    Scrape Hugo Award for Best Novel.

    Returns:
        List of award records
    """
    logger.info("Scraping Hugo Award for Best Novel")
    url = "https://en.wikipedia.org/wiki/Hugo_Award_for_Best_Novel"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Hugo tables typically have Year, Title, Author columns
        # May also have "Result" or similar column indicating winner/nominee
        if 'Year' in df.columns and ('Title' in df.columns or 'Novel' in df.columns):
            title_col = 'Title' if 'Title' in df.columns else 'Novel'
            author_col = 'Author' if 'Author' in df.columns else ('Author(s)' if 'Author(s)' in df.columns else None)

            if not author_col:
                continue

            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                title = str(row[title_col]).strip()
                author = str(row[author_col]).strip()

                if not title or not author or title == 'nan' or author == 'nan':
                    continue

                # Check if there's a status/result column
                status = AwardStatus.WINNER.value
                if 'Result' in df.columns:
                    result = str(row['Result']).lower()
                    if 'nominee' in result or 'nomination' in result:
                        status = AwardStatus.NOMINEE.value
                    elif 'shortlist' in result:
                        status = AwardStatus.SHORTLIST.value

                records.append({
                    'prize': 'Hugo',
                    'category': 'Best Novel',
                    'year': year,
                    'status': status,
                    'title': title,
                    'author': author
                })

    logger.info(f"Found {len(records)} Hugo Award records")
    return records


def scrape_nebula_award() -> List[AwardRecord]:
    """
    Scrape Nebula Award for Best Novel.

    Returns:
        List of award records
    """
    logger.info("Scraping Nebula Award for Best Novel")
    url = "https://en.wikipedia.org/wiki/Nebula_Award_for_Best_Novel"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Nebula tables similar structure to Hugo
        if 'Year' in df.columns and ('Title' in df.columns or 'Novel' in df.columns):
            title_col = 'Title' if 'Title' in df.columns else 'Novel'
            author_col = 'Author' if 'Author' in df.columns else ('Author(s)' if 'Author(s)' in df.columns else None)

            if not author_col:
                continue

            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                title = str(row[title_col]).strip()
                author = str(row[author_col]).strip()

                if not title or not author or title == 'nan' or author == 'nan':
                    continue

                # Check for status
                status = AwardStatus.WINNER.value
                if 'Result' in df.columns:
                    result = str(row['Result']).lower()
                    if 'nominee' in result or 'nomination' in result:
                        status = AwardStatus.NOMINEE.value
                    elif 'shortlist' in result:
                        status = AwardStatus.SHORTLIST.value

                records.append({
                    'prize': 'Nebula',
                    'category': 'Best Novel',
                    'year': year,
                    'status': status,
                    'title': title,
                    'author': author
                })

    logger.info(f"Found {len(records)} Nebula Award records")
    return records


def scrape_clarke_award() -> List[AwardRecord]:
    """
    Scrape Arthur C. Clarke Award.

    Returns:
        List of award records
    """
    logger.info("Scraping Arthur C. Clarke Award")
    url = "https://en.wikipedia.org/wiki/Arthur_C._Clarke_Award"

    tables = fetch_wiki_tables(url)
    records = []

    for table in tables:
        df = clean_dataframe(table)

        # Clarke award tables
        if 'Year' in df.columns and ('Title' in df.columns or 'Novel' in df.columns or 'Book' in df.columns):
            title_col = 'Title' if 'Title' in df.columns else ('Novel' if 'Novel' in df.columns else 'Book')
            author_col = 'Author' if 'Author' in df.columns else ('Author(s)' if 'Author(s)' in df.columns else None)

            if not author_col:
                continue

            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                title = str(row[title_col]).strip()
                author = str(row[author_col]).strip()

                if not title or not author or title == 'nan' or author == 'nan':
                    continue

                # Clarke typically shows winners; shortlist is separate
                status = AwardStatus.WINNER.value
                if 'Status' in df.columns or 'Result' in df.columns:
                    result_col = 'Status' if 'Status' in df.columns else 'Result'
                    result = str(row[result_col]).lower()
                    if 'shortlist' in result or 'nominee' in result:
                        status = AwardStatus.SHORTLIST.value

                records.append({
                    'prize': 'Arthur C. Clarke',
                    'category': 'Best Novel',
                    'year': year,
                    'status': status,
                    'title': title,
                    'author': author
                })

    logger.info(f"Found {len(records)} Arthur C. Clarke Award records")
    return records


def scrape_all_scifi() -> pd.DataFrame:
    """
    Scrape all sci-fi/fantasy awards and return as DataFrame.

    Returns:
        DataFrame with all sci-fi award records
    """
    all_records = []

    try:
        all_records.extend(scrape_hugo_award())
    except Exception as e:
        logger.error(f"Failed to scrape Hugo Award: {e}")

    try:
        all_records.extend(scrape_nebula_award())
    except Exception as e:
        logger.error(f"Failed to scrape Nebula Award: {e}")

    try:
        all_records.extend(scrape_clarke_award())
    except Exception as e:
        logger.error(f"Failed to scrape Clarke Award: {e}")

    df = pd.DataFrame(all_records)
    logger.info(f"Total sci-fi award records: {len(df)}")

    return df
