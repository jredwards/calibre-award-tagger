"""
Scraper for National Book Award for Fiction data from Wikipedia.
Uses HTML parsing since Wikipedia has more complete coverage than Wikidata.
"""

import logging
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)

NBA_URL = "https://en.wikipedia.org/wiki/National_Book_Award_for_Fiction"


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


def parse_nba_table(table) -> list[AwardRecord]:
    """
    Parse a National Book Award table and extract records.
    Handles rowspan where finalists share the winner's year.

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

            # Handle special case where first cell might be "Category" (for 1980-1983 tables)
            if first_cell_text in ['Hardcover', 'Paperback', 'Original']:
                # These are category rows in the 1980-1983 section, skip them
                continue

            if first_cell_text.isdigit() and len(first_cell_text) == 4:
                # This row has a year
                current_year = int(first_cell_text)

                # For rows with year: [Year, Author, Title, Result, Ref]
                # OR for 1980-1983: [Year, Category, Author, Title, Result, Ref]
                if len(cells) < 4:
                    continue

                # Check if second cell is a category (Hardcover/Paperback)
                second_cell_text = cells[1].get_text().strip()
                if second_cell_text in ['Hardcover', 'Paperback', 'Original']:
                    # Skip category, start from next cell
                    if len(cells) < 5:
                        continue
                    author = cells[2].get_text().strip()
                    title = cells[3].get_text().strip()
                    result_cells = cells[4:]
                else:
                    # Normal format
                    author = cells[1].get_text().strip()
                    title = cells[2].get_text().strip()
                    result_cells = cells[3:]

                # Find result in remaining cells
                result = None
                for cell in result_cells:
                    cell_text = cell.get_text().strip()
                    if cell_text in ['Winner', 'Finalist']:
                        result = cell_text
                        break

            else:
                # This row doesn't have a year - it's a finalist using rowspan
                # Use the current_year from previous row
                # Format: [Author, Title, Result, Ref]
                if current_year is None or len(cells) < 2:
                    continue

                author = cells[0].get_text().strip()
                title = cells[1].get_text().strip()

                # Find result in remaining cells
                result = None
                for cell in cells[2:]:
                    cell_text = cell.get_text().strip()
                    if cell_text in ['Winner', 'Finalist']:
                        result = cell_text
                        break

            # Validate year exists
            if current_year is None:
                continue

            # Validate author and title
            if not author or author in ['', 'N/A']:
                continue
            if not title or title in ['', 'N/A']:
                continue
            if not result:
                continue

            # Map Wikipedia status to our schema
            if result == 'Winner':
                status = AwardStatus.WINNER.value
            elif result == 'Finalist':
                status = AwardStatus.NOMINEE.value
            else:
                continue

            records.append({
                'prize': 'National Book Award',
                'category': 'Fiction',
                'year': current_year,
                'status': status,
                'title': title,
                'author': author
            })

        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse row: {e}")
            continue

    return records


def scrape_nba_fiction() -> pd.DataFrame:
    """
    Scrape National Book Award for Fiction from Wikipedia.

    Returns:
        DataFrame with all award records
    """
    logger.info("Starting National Book Award for Fiction Wikipedia scraping")

    try:
        soup = fetch_wikipedia_page(NBA_URL)
        all_records = []

        # Find all wikitable tables
        tables = soup.find_all('table', class_='wikitable')
        logger.info(f"Found {len(tables)} tables")

        for table in tables:
            records = parse_nba_table(table)
            all_records.extend(records)

        df = pd.DataFrame(all_records)
        logger.info(f"Total National Book Award records scraped: {len(df)}")

        # Show breakdown
        if not df.empty:
            status_counts = df['status'].value_counts()
            logger.info(f"  Winners: {status_counts.get('Winner', 0)}")
            logger.info(f"  Finalists: {status_counts.get('Nominee', 0)}")

        return df

    except Exception as e:
        logger.error(f"Failed to scrape National Book Award: {e}")
        return pd.DataFrame()
