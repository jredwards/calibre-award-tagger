"""
Scrapers for specialized awards.
Covers: Agatha Award (Mystery), Locus Award.
"""

import logging
from typing import List
import pandas as pd
from .base_wiki import fetch_wiki_tables, clean_dataframe, extract_year
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)


def scrape_agatha_award() -> List[AwardRecord]:
    """
    Scrape Agatha Award (all categories).

    Returns:
        List of award records
    """
    logger.info("Scraping Agatha Award")
    url = "https://en.wikipedia.org/wiki/Agatha_Award"

    tables = fetch_wiki_tables(url)
    records = []

    # Agatha has separate tables for each category
    # Categories: Best Novel, Best First Novel, Best Historical Novel, Best Contemporary Novel, Best Children's/YA
    target_categories = [
        'Best Novel',
        'Best First Novel',
        'Best Historical Novel',
        'Best Contemporary Novel',
        "Best Children's/Young Adult"
    ]

    for table in tables:
        df = clean_dataframe(table)

        # Look for Year and Title/Book columns
        if 'Year' in df.columns and ('Title' in df.columns or 'Book' in df.columns):
            title_col = 'Title' if 'Title' in df.columns else 'Book'
            author_col = 'Author' if 'Author' in df.columns else ('Author(s)' if 'Author(s)' in df.columns else None)

            if not author_col:
                continue

            # Try to infer category from table structure or surrounding context
            # For now, we'll mark as "Best Novel" and refine later if needed
            category = 'Best Novel'

            for _, row in df.iterrows():
                year = extract_year(str(row['Year']))
                if not year:
                    continue

                title = str(row[title_col]).strip()
                author = str(row[author_col]).strip()

                if not title or not author or title == 'nan' or author == 'nan':
                    continue

                # Determine status
                status = AwardStatus.WINNER.value
                if 'Status' in df.columns or 'Result' in df.columns:
                    result_col = 'Status' if 'Status' in df.columns else 'Result'
                    result = str(row[result_col]).lower()
                    if 'nominee' in result or 'nomination' in result:
                        status = AwardStatus.NOMINEE.value
                    elif 'shortlist' in result:
                        status = AwardStatus.SHORTLIST.value

                records.append({
                    'prize': 'Agatha',
                    'category': category,
                    'year': year,
                    'status': status,
                    'title': title,
                    'author': author
                })

    logger.info(f"Found {len(records)} Agatha Award records")
    return records


def scrape_locus_award() -> List[AwardRecord]:
    """
    Scrape Locus Award (Science Fiction Novel, Fantasy Novel, Horror Novel only).

    Returns:
        List of award records
    """
    logger.info("Scraping Locus Award")

    records = []

    # Scrape each category from its specific Wikipedia page
    categories = [
        ('Science Fiction Novel', 'https://en.wikipedia.org/wiki/Locus_Award_for_Best_Science_Fiction_Novel'),
        ('Fantasy Novel', 'https://en.wikipedia.org/wiki/Locus_Award_for_Best_Fantasy_Novel'),
        ('Horror Novel', 'https://en.wikipedia.org/wiki/Locus_Award_for_Best_Horror_Novel'),
    ]

    for category, url in categories:
        logger.info(f"Scraping Locus Award - {category}")

        try:
            tables = fetch_wiki_tables(url)

            for table in tables:
                df = clean_dataframe(table)

                # Locus tables typically have Year and either Title, Novel, Book, or Work columns
                # Work column may have citations like "Work[1]"
                work_col = [col for col in df.columns if col.startswith('Work')]
                work_col = work_col[0] if work_col else None

                if 'Year' in df.columns and ('Title' in df.columns or 'Novel' in df.columns or 'Book' in df.columns or work_col):
                    # Determine which column has the title
                    title_col = None
                    if 'Title' in df.columns:
                        title_col = 'Title'
                    elif 'Novel' in df.columns:
                        title_col = 'Novel'
                    elif 'Book' in df.columns:
                        title_col = 'Book'
                    elif work_col:
                        title_col = work_col

                    # Find author column
                    author_col = None
                    if 'Author' in df.columns:
                        author_col = 'Author'
                    elif 'Author(s)' in df.columns:
                        author_col = 'Author(s)'

                    if not title_col or not author_col:
                        continue

                    for _, row in df.iterrows():
                        year = extract_year(str(row['Year']))
                        if not year:
                            continue

                        title = str(row[title_col]).strip()
                        author = str(row[author_col]).strip()

                        if not title or not author or title == 'nan' or author == 'nan':
                            continue

                        # Determine status (winner vs nominee)
                        status = AwardStatus.WINNER.value
                        if 'Result' in df.columns or 'Status' in df.columns:
                            result_col = 'Result' if 'Result' in df.columns else 'Status'
                            result = str(row[result_col]).lower()
                            if 'nominee' in result or 'nomination' in result:
                                status = AwardStatus.NOMINEE.value
                            elif 'shortlist' in result:
                                status = AwardStatus.SHORTLIST.value

                        records.append({
                            'prize': 'Locus',
                            'category': category,
                            'year': year,
                            'status': status,
                            'title': title,
                            'author': author
                        })

        except Exception as e:
            logger.error(f"Failed to scrape Locus Award - {category}: {e}")

    logger.info(f"Found {len(records)} Locus Award records")
    return records


def scrape_all_specialized() -> pd.DataFrame:
    """
    Scrape all specialized awards and return as DataFrame.

    Returns:
        DataFrame with all specialized award records
    """
    all_records = []

    try:
        all_records.extend(scrape_agatha_award())
    except Exception as e:
        logger.error(f"Failed to scrape Agatha Award: {e}")

    try:
        all_records.extend(scrape_locus_award())
    except Exception as e:
        logger.error(f"Failed to scrape Locus Award: {e}")

    df = pd.DataFrame(all_records)
    logger.info(f"Total specialized award records: {len(df)}")

    return df
