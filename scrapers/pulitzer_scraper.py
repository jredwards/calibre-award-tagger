"""
Scraper for Pulitzer Prize for Fiction data from Wikipedia.
Table 0 covers 1917-1979 (winners only); Table 1 covers 1980+ (winner + finalists).
"""

import logging
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)

PULITZER_URL = "https://en.wikipedia.org/wiki/Pulitzer_Prize_for_Fiction"


def fetch_page(url: str) -> BeautifulSoup:
    response = requests.get(
        url,
        headers={'User-Agent': 'Calibre-Awards-Tagger/1.0 (Educational Project)'},
        timeout=30
    )
    response.raise_for_status()
    return BeautifulSoup(response.content, 'html.parser')


def clean_text(text: str) -> str:
    """Strip footnote markers like [a], [14], (posthumously), etc."""
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(posthumously\)', '', text, flags=re.IGNORECASE)
    return text.strip()


def parse_table(table, winners_only: bool = False) -> list[AwardRecord]:
    """
    Parse a Pulitzer wikitable.

    Winners have a year in the first cell. Finalists (1980+) share the year
    via rowspan and have no year cell — same pattern as the NBA scraper.
    """
    records = []
    current_year = None

    for row in table.find_all('tr')[1:]:  # skip header
        cells = row.find_all(['td', 'th'])
        if not cells:
            continue

        first = clean_text(cells[0].get_text())

        if first.isdigit() and len(first) == 4:
            current_year = int(first)
            if len(cells) < 3:
                continue  # "Not awarded" rows only have 1-2 cells
            author = clean_text(cells[1].get_text())
            title = clean_text(cells[2].get_text())
            status = AwardStatus.WINNER.value
        else:
            if winners_only or current_year is None or len(cells) < 2:
                continue
            author = clean_text(cells[0].get_text())
            title = clean_text(cells[1].get_text())
            status = AwardStatus.NOMINEE.value

        if not author or not title:
            continue
        if 'not awarded' in author.lower() or 'not awarded' in title.lower():
            continue

        records.append({
            'prize': 'Pulitzer',
            'category': 'Fiction',
            'year': current_year,
            'status': status,
            'title': title,
            'author': author,
        })

    return records


def scrape_pulitzer_fiction() -> pd.DataFrame:
    """Scrape Pulitzer Prize for Fiction from Wikipedia."""
    logger.info("Starting Pulitzer Prize for Fiction Wikipedia scraping")

    soup = fetch_page(PULITZER_URL)
    tables = soup.find_all('table', class_='wikitable')
    logger.info(f"Found {len(tables)} tables")

    all_records = []

    for i, table in enumerate(tables):
        # Table 0 (1917-1979) has no finalists listed
        winners_only = (i == 0)
        records = parse_table(table, winners_only=winners_only)
        all_records.extend(records)
        logger.info(f"  Table {i}: {len(records)} records")

    winners = sum(1 for r in all_records if r['status'] == AwardStatus.WINNER.value)
    nominees = sum(1 for r in all_records if r['status'] == AwardStatus.NOMINEE.value)
    logger.info(f"Total Pulitzer records: {len(all_records)} ({winners} winners, {nominees} finalists)")

    return pd.DataFrame(all_records)
