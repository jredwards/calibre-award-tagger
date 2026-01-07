"""
Scraper for Giller Prize data from Wikipedia.
Uses HTML parsing since Wikipedia has more complete coverage than Wikidata.
"""

import logging
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)

GILLER_URL = "https://en.wikipedia.org/wiki/Giller_Prize"


def fetch_wikipedia_page(url: str) -> BeautifulSoup:
    """
    Fetch and parse a Wikipedia page.

    Args:
        url: Wikipedia page URL

    Returns:
        BeautifulSoup object
    """
    try:
        response = requests.get(
            url,
            headers={'User-Agent': 'Calibre-Awards-Tagger/1.0 (Educational Project)'},
            timeout=30
        )
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        raise


def parse_giller_table(table) -> list[AwardRecord]:
    """
    Parse a Giller Prize table and extract records.
    Handles rowspan where shortlist entries share the winner's year.

    Args:
        table: BeautifulSoup table element

    Returns:
        List of award records
    """
    records = []

    # Get all rows (skip header row)
    rows = table.find_all('tr')[1:]

    # Track the current year for rows with rowspan
    current_year = None

    for row in rows:
        cells = row.find_all(['td', 'th'])

        # Skip rows that don't have enough cells
        if len(cells) < 2:
            continue

        try:
            # Check if first cell contains a year (4 digits)
            first_cell_text = cells[0].get_text().strip()

            if first_cell_text.isdigit() and len(first_cell_text) == 4:
                # This row has a year
                current_year = int(first_cell_text)

                # For rows with year: [Year, Jury, Author, Book, Result?, Ref]
                # Jury column varies in presence, so we need to be flexible
                if len(cells) < 4:
                    continue

                # Skip the Jury column (second column) - it's not consistent
                # Try to find author and book
                # The pattern is usually: Year, Jury, Author, Book, Result, Ref
                # But Jury might be merged or missing

                # Look for author (typically cells[2]) and book (cells[3])
                author_idx = 2
                book_idx = 3

                # If there's no jury column, it might be: Year, Author, Book, Result, Ref
                if len(cells) >= 4:
                    author = cells[author_idx].get_text().strip()
                    book = cells[book_idx].get_text().strip()

                    # Find result in remaining cells
                    result = None
                    for cell in cells[4:]:
                        cell_text = cell.get_text().strip()
                        if cell_text in ['Winner', 'Shortlist']:
                            result = cell_text
                            break

                    # If no result found, assume it's shortlist (some entries don't have explicit "Shortlist")
                    if not result:
                        result = 'Shortlist'

            else:
                # This row doesn't have a year - it's a shortlist entry using rowspan
                # Use the current_year from previous row
                # Format: [Author, Book, Result?, Ref] or [Jury, Author, Book, Result?, Ref]
                if current_year is None or len(cells) < 2:
                    continue

                # The first cell is either Jury (if present) or Author
                # We'll assume it's author, and book is second cell
                author = cells[0].get_text().strip()
                book = cells[1].get_text().strip()

                # Find result in remaining cells
                result = None
                for cell in cells[2:]:
                    cell_text = cell.get_text().strip()
                    if cell_text in ['Winner', 'Shortlist']:
                        result = cell_text
                        break

                # If no result found, assume it's shortlist
                if not result:
                    result = 'Shortlist'

            # Validate year exists
            if current_year is None:
                continue

            # Validate author and book
            if not author or author in ['', 'N/A']:
                continue
            if not book or book in ['', 'N/A']:
                continue

            # Map Wikipedia status to our schema
            if result == 'Winner':
                status = AwardStatus.WINNER.value
            elif result == 'Shortlist':
                status = AwardStatus.SHORTLIST.value
            else:
                continue

            records.append({
                'prize': 'Giller',
                'category': 'Fiction',
                'year': current_year,
                'status': status,
                'title': book,
                'author': author
            })

        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse row: {e}")
            continue

    return records


def scrape_giller_prize() -> pd.DataFrame:
    """
    Scrape Giller Prize from Wikipedia.

    Returns:
        DataFrame with all award records
    """
    logger.info("Starting Giller Prize Wikipedia scraping")

    try:
        soup = fetch_wikipedia_page(GILLER_URL)
        all_records = []

        # Find all wikitable tables
        tables = soup.find_all('table', class_='wikitable')
        logger.info(f"Found {len(tables)} tables")

        for table in tables:
            records = parse_giller_table(table)
            all_records.extend(records)

        df = pd.DataFrame(all_records)
        logger.info(f"Total Giller Prize records scraped: {len(df)}")

        # Show breakdown
        if not df.empty:
            status_counts = df['status'].value_counts()
            logger.info(f"  Winners: {status_counts.get('Winner', 0)}")
            logger.info(f"  Shortlist: {status_counts.get('Nominee', 0)}")

        return df

    except Exception as e:
        logger.error(f"Failed to scrape Giller Prize: {e}")
        return pd.DataFrame()
