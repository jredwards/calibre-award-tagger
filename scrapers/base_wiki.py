"""
Base utilities for scraping Wikipedia pages.
"""

import re
import logging
from typing import List, Optional
import requests
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_wiki_tables(url: str, parser: str = "html.parser") -> List[pd.DataFrame]:
    """
    Fetch all tables from a Wikipedia page as DataFrames.

    Args:
        url: Wikipedia page URL
        parser: HTML parser to use (html.parser, lxml, or html5lib)

    Returns:
        List of DataFrames, one per table on the page

    Raises:
        requests.RequestException: If fetching the page fails
    """
    logger.info(f"Fetching tables from {url}")

    headers = {
        'User-Agent': 'Calibre-Awards-Tagger/1.0 (Educational Project)'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        raise

    # Use pandas to parse tables
    try:
        tables = pd.read_html(response.text, flavor='html5lib')
        logger.info(f"Found {len(tables)} tables on page")
        return tables
    except ValueError as e:
        logger.warning(f"No tables found on {url}: {e}")
        return []


def clean_citation_marks(text: str) -> str:
    """
    Remove citation marks like [1], [a], [note 1] from text.

    Args:
        text: Input text with potential citation marks

    Returns:
        Cleaned text

    Examples:
        >>> clean_citation_marks("Dune[1]")
        'Dune'
        >>> clean_citation_marks("Frank Herbert[a][note 2]")
        'Frank Herbert'
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    # Remove patterns like [1], [a], [note 1], etc.
    cleaned = re.sub(r'\[[\w\s]+\]', '', text)
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()


def extract_year(text: str) -> Optional[int]:
    """
    Extract a 4-digit year from text.

    Args:
        text: Input text potentially containing a year

    Returns:
        Extracted year as integer, or None if not found

    Examples:
        >>> extract_year("1966")
        1966
        >>> extract_year("Winner (2020)")
        2020
        >>> extract_year("no year here")
        None
    """
    if isinstance(text, int):
        # Already a year
        if 1900 <= text <= 2100:
            return text
        return None

    if not isinstance(text, str):
        text = str(text)

    # Look for 4-digit year
    match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if match:
        return int(match.group(1))

    return None


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text (collapse multiple spaces, strip).

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    return ' '.join(text.split()).strip()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply common cleaning operations to a DataFrame.

    Args:
        df: Input DataFrame

    Returns:
        Cleaned DataFrame
    """
    df = df.copy()

    # Apply citation cleaning to all string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: clean_citation_marks(str(x)) if pd.notna(x) else x)
            df[col] = df[col].apply(lambda x: normalize_whitespace(str(x)) if pd.notna(x) else x)

    return df


def parse_wiki_page(url: str) -> BeautifulSoup:
    """
    Fetch and parse a Wikipedia page with BeautifulSoup.

    Args:
        url: Wikipedia page URL

    Returns:
        BeautifulSoup object

    Raises:
        requests.RequestException: If fetching the page fails
    """
    logger.info(f"Parsing Wikipedia page: {url}")

    headers = {
        'User-Agent': 'Calibre-Awards-Tagger/1.0 (Educational Project)'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        raise

    soup = BeautifulSoup(response.text, 'html.parser')
    return soup
