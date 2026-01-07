"""
Scraper for Agatha Award data from Wikipedia.
Uses HTML parsing since Wikidata has poor coverage for this award.
"""

import logging
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)

AGATHA_URL = "https://en.wikipedia.org/wiki/Agatha_Award"

# Categories to scrape (focusing on novel categories)
AGATHA_CATEGORIES = {
    'Best First Novel': 'Best First Novel',
    'Best Contemporary Novel': 'Best Contemporary Novel',
    'Best Novel': 'Best Novel',
    'Best Historical Novel': 'Best Historical Novel'
}


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


def parse_agatha_table(table, category_name: str) -> list[AwardRecord]:
    """
    Parse an Agatha Award table and extract records.
    Handles rowspan where finalists share the winner's year.

    Args:
        table: BeautifulSoup table element
        category_name: Name of the award category

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
                # This row has a year - it's either a winner row or a new year
                current_year = int(first_cell_text)

                # For rows with year: [Year, Author, Title, Publisher?, Result, Ref]
                if len(cells) < 4:
                    continue

                author = cells[1].get_text().strip()
                title = cells[2].get_text().strip()

                # Find result in remaining cells
                result = None
                for cell in cells[3:]:
                    cell_text = cell.get_text().strip()
                    if cell_text in ['Winner', 'WInner', 'Finalist']:
                        result = cell_text
                        break

            else:
                # This row doesn't have a year - it's a finalist using rowspan
                # Use the current_year from previous row
                # Format: [Author, Title, Publisher?, Result, Ref]
                if current_year is None or len(cells) < 2:
                    continue

                author = cells[0].get_text().strip()
                title = cells[1].get_text().strip()

                # Find result in remaining cells
                result = None
                for cell in cells[2:]:
                    cell_text = cell.get_text().strip()
                    if cell_text in ['Winner', 'WInner', 'Finalist']:
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
            if result in ['Winner', 'WInner']:
                status = AwardStatus.WINNER.value
            elif result == 'Finalist':
                status = AwardStatus.NOMINEE.value
            else:
                continue

            records.append({
                'prize': 'Agatha',
                'category': category_name,
                'year': current_year,
                'status': status,
                'title': title,
                'author': author
            })

        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse row: {e}")
            continue

    return records


def scrape_agatha_category(soup: BeautifulSoup, category_name: str) -> list[AwardRecord]:
    """
    Scrape all tables for a specific Agatha category.

    Args:
        soup: BeautifulSoup object of the page
        category_name: Name of the category to scrape

    Returns:
        List of award records
    """
    logger.info(f"Scraping Agatha - {category_name}")

    all_records = []

    # Find the h3 header for this category
    headers = soup.find_all(['h2', 'h3'])
    category_header = None

    for header in headers:
        header_text = header.get_text().strip()
        # Remove edit links
        header_text = header_text.replace('[edit]', '').strip()
        if header_text == category_name:
            category_header = header
            break

    if not category_header:
        logger.warning(f"Could not find header for {category_name}")
        return []

    # Find all tables after this header until the next h2/h3
    # We need to use find_next() and check each element
    current_element = category_header.find_next()

    while current_element:
        # Stop if we hit another h2 or h3 (next category)
        if current_element.name in ['h2', 'h3']:
            break

        # If it's a table with class wikitable, parse it
        if current_element.name == 'table' and 'wikitable' in current_element.get('class', []):
            records = parse_agatha_table(current_element, category_name)
            all_records.extend(records)

        current_element = current_element.find_next()

    logger.info(f"  Found {len(all_records)} records for {category_name}")
    return all_records


def scrape_agatha_awards() -> pd.DataFrame:
    """
    Scrape all Agatha Award novel categories from Wikipedia.

    Returns:
        DataFrame with all award records
    """
    logger.info("Starting Agatha Award Wikipedia scraping")

    try:
        soup = fetch_wikipedia_page(AGATHA_URL)
        all_records = []

        for category_display, category_name in AGATHA_CATEGORIES.items():
            try:
                records = scrape_agatha_category(soup, category_display)
                all_records.extend(records)
                # Add a small delay between categories
                time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to scrape {category_name}: {e}")

        df = pd.DataFrame(all_records)
        logger.info(f"Total Agatha Award records scraped: {len(df)}")

        return df

    except Exception as e:
        logger.error(f"Failed to scrape Agatha Awards: {e}")
        return pd.DataFrame()
