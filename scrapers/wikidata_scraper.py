"""
Scraper for award data from Wikidata using SPARQL queries.
Provides structured winner/nominee data with clear status distinction.
"""

import logging
import time
from typing import List, Optional
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON
from schema import AwardRecord, AwardStatus

logger = logging.getLogger(__name__)

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Award configurations with Q numbers
AWARD_CONFIGS = {
    'hugo': {
        'q_id': 'Q255032',
        'name': 'Hugo',
        'category': 'Best Novel',
        'use_p361': False,
        'category_filter': None
    },
    'nebula': {
        'q_id': 'Q266012',
        'name': 'Nebula',
        'category': 'Best Novel',
        'use_p361': False,
        'category_filter': None
    },
    'clarke': {
        'q_id': 'Q708830',
        'name': 'Arthur C. Clarke',
        'category': 'Best Novel',
        'use_p361': False,
        'category_filter': None
    },
    'booker': {
        'q_id': 'Q160082',
        'name': 'Booker',
        'category': 'Fiction',
        'use_p361': False,
        'category_filter': None
    },
    'international_booker': {
        'q_id': 'Q2052291',
        'name': 'International Booker',
        'category': 'Fiction',
        'use_p361': False,
        'category_filter': None
    },
    # National Book Award disabled - using Wikipedia scraper instead (better coverage)
    # 'national_book_award': {
    #     'q_id': 'Q3873144',
    #     'name': 'National Book Award',
    #     'category': 'Fiction',
    #     'use_p361': False,
    #     'category_filter': None,
    #     'require_book_filter': False
    # },
    # Giller Prize disabled - using Wikipedia scraper instead (better coverage)
    # 'giller': {
    #     'q_id': 'Q1328335',
    #     'name': 'Giller',
    #     'category': 'Fiction',
    #     'use_p361': False,
    #     'category_filter': None
    # },
    # Agatha Award disabled - poor Wikidata coverage (only 7 recipients across all categories)
    # 'agatha': {
    #     'q_id': 'Q390975',
    #     'name': 'Agatha',
    #     'category': 'Best Novel',
    #     'use_p361': True,
    #     'category_filter': 'Agatha Award for Best Novel'
    # },
    'locus_scifi': {
        'q_id': 'Q2576795',
        'name': 'Locus',
        'category': 'Science Fiction Novel',
        'use_p361': False,
        'category_filter': None
    },
    'locus_fantasy': {
        'q_id': 'Q607354',
        'name': 'Locus',
        'category': 'Fantasy Novel',
        'use_p361': False,
        'category_filter': None
    },
    'locus_horror': {
        'q_id': 'Q3404950',
        'name': 'Locus',
        'category': 'Horror Novel',
        'use_p361': False,
        'category_filter': None
    }
}


def execute_sparql_query(query: str) -> List[dict]:
    """
    Execute a SPARQL query against Wikidata and return results.

    Args:
        query: SPARQL query string

    Returns:
        List of result bindings as dictionaries

    Raises:
        Exception: If query execution fails
    """
    logger.debug(f"Executing SPARQL query:\n{query}")

    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(120)  # 2 minute timeout
    sparql.addCustomHttpHeader("User-Agent", "Calibre-Awards-Tagger/1.0 (Educational Project)")

    try:
        results = sparql.query().convert()
        bindings = results['results']['bindings']
        logger.info(f"Query returned {len(bindings)} results")

        # Add delay to avoid rate limiting (5-8 seconds)
        import random
        time.sleep(random.uniform(5, 8))

        return bindings
    except Exception as e:
        logger.error(f"SPARQL query failed: {e}")
        raise


def build_p361_winners_query(
    q_id: str,
    category_filter: Optional[str] = None,
    start_year: Optional[int] = None,
    require_book: bool = True,
) -> str:
    """
    Build SPARQL query for winners using P361 (part of) structure with P166.

    Args:
        q_id: Wikidata Q ID for the main award
        category_filter: Optional filter for specific category label
        start_year: If provided, only get results from this year onwards
        require_book: If True, filter for books only; if False, accept any recipient

    Returns:
        SPARQL query string
    """
    category_clause = ""
    if category_filter:
        category_clause = f'FILTER(STR(?awardLabel) = "{category_filter}")'

    # Book filter clause - only add if require_book is True
    book_filter = ""
    if require_book:
        book_filter = "?recipient wdt:P31/wdt:P279* wd:Q7725634 ."

    year_filter = f"FILTER(?year >= {start_year})" if start_year else ""

    query = f"""
    SELECT ?year ?awardLabel ?recipientLabel ?workLabel ?authorLabel
    WHERE {{
      ?award wdt:P361 wd:{q_id} .
      {category_clause}

      ?recipient p:P166 ?stmt .
      ?stmt ps:P166 ?award .
      ?stmt pq:P585 ?time .

      {book_filter}

      OPTIONAL {{ ?recipient wdt:P50 ?author . }}
      BIND(?recipient AS ?work)

      BIND(YEAR(?time) AS ?year)
      {year_filter}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    ORDER BY DESC(?year)
    LIMIT 2000
    """
    return query


def build_p361_nominees_query(
    q_id: str,
    category_filter: Optional[str] = None,
    start_year: Optional[int] = None,
    require_book: bool = True,
) -> str:
    """
    Build SPARQL query for nominees using P361 (part of) structure with P1411.

    Args:
        q_id: Wikidata Q ID for the main award
        category_filter: Optional filter for specific category label
        start_year: If provided, only get results from this year onwards
        require_book: If True, filter for books only; if False, accept any recipient

    Returns:
        SPARQL query string
    """
    category_clause = ""
    if category_filter:
        category_clause = f'FILTER(STR(?awardLabel) = "{category_filter}")'

    # Book filter clause - only add if require_book is True
    book_filter = ""
    if require_book:
        book_filter = "?recipient wdt:P31/wdt:P279* wd:Q7725634 ."

    year_filter = f"FILTER(?year >= {start_year})" if start_year else ""

    query = f"""
    SELECT ?year ?awardLabel ?recipientLabel ?workLabel ?authorLabel
    WHERE {{
      ?award wdt:P361 wd:{q_id} .
      {category_clause}

      ?recipient p:P1411 ?stmt .
      ?stmt ps:P1411 ?award .
      ?stmt pq:P585 ?time .

      {book_filter}

      OPTIONAL {{ ?recipient wdt:P50 ?author . }}
      BIND(?recipient AS ?work)

      BIND(YEAR(?time) AS ?year)
      {year_filter}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    ORDER BY DESC(?year)
    LIMIT 2000
    """
    return query


def build_direct_winners_query(
    q_id: str,
    start_year: Optional[int] = None,
    require_book: bool = True,
) -> str:
    """
    Build SPARQL query for winners using P166 (award received) - inverse query.

    Args:
        q_id: Wikidata Q ID for the award
        start_year: If provided, only get results from this year onwards
        require_book: If True, filter for books only; if False, accept any recipient

    Returns:
        SPARQL query string
    """
    # Book filter clause - only add if require_book is True
    book_filter = ""
    if require_book:
        book_filter = "?recipient wdt:P31/wdt:P279* wd:Q7725634 ."

    year_filter = f"FILTER(?year >= {start_year})" if start_year else ""

    query = f"""
    SELECT ?year ?recipientLabel ?workLabel ?authorLabel
    WHERE {{
      ?recipient p:P166 ?stmt .
      ?stmt ps:P166 wd:{q_id} .
      ?stmt pq:P585 ?time .

      {book_filter}

      OPTIONAL {{ ?recipient wdt:P50 ?author . }}
      BIND(?recipient AS ?work)

      BIND(YEAR(?time) AS ?year)
      {year_filter}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    ORDER BY DESC(?year)
    LIMIT 2000
    """
    return query


def build_direct_nominees_query(
    q_id: str,
    start_year: Optional[int] = None,
    require_book: bool = True,
) -> str:
    """
    Build SPARQL query for nominees using P1411 (nominated for).

    Args:
        q_id: Wikidata Q ID for the award
        start_year: If provided, only get results from this year onwards
        require_book: If True, filter for books only; if False, accept any recipient

    Returns:
        SPARQL query string
    """
    # Book filter clause - only add if require_book is True
    book_filter = ""
    if require_book:
        book_filter = "?recipient wdt:P31/wdt:P279* wd:Q7725634 ."

    year_filter = f"FILTER(?year >= {start_year})" if start_year else ""

    query = f"""
    SELECT ?year ?recipientLabel ?workLabel ?authorLabel
    WHERE {{
      ?recipient p:P1411 ?stmt .
      ?stmt ps:P1411 wd:{q_id} .
      ?stmt pq:P585 ?time .

      {book_filter}

      OPTIONAL {{ ?recipient wdt:P50 ?author . }}
      BIND(?recipient AS ?work)

      BIND(YEAR(?time) AS ?year)
      {year_filter}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    ORDER BY DESC(?year)
    LIMIT 2000
    """
    return query


def parse_sparql_results(bindings: List[dict], prize_name: str, category: str, status: str) -> List[AwardRecord]:
    """
    Parse SPARQL query results into AwardRecord dictionaries.

    Args:
        bindings: SPARQL result bindings
        prize_name: Name of the prize (e.g., "Hugo")
        category: Category name (e.g., "Best Novel")
        status: Status value ("Winner" or "Nominee")

    Returns:
        List of award records
    """
    records = []

    for binding in bindings:
        try:
            # Extract year
            year_str = binding.get('year', {}).get('value')
            if not year_str:
                continue
            year = int(year_str)

            # Extract work title
            # Try work first, then recipient (in case recipient is the work)
            title = None
            if 'workLabel' in binding:
                title = binding['workLabel'].get('value')
            if not title or title == 'None':
                if 'recipientLabel' in binding:
                    recipient_label = binding['recipientLabel'].get('value')
                    # If recipient looks like a book title (not a person name)
                    # we'll use it as the title
                    title = recipient_label

            if not title or title == 'None':
                continue

            # Extract author
            author = None
            if 'authorLabel' in binding:
                author = binding['authorLabel'].get('value')
            if not author or author == 'None':
                # If no author found, skip this record
                continue

            records.append({
                'prize': prize_name,
                'category': category,
                'year': year,
                'status': status,
                'title': title,
                'author': author
            })

        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse binding: {e}")
            continue

    return records


def scrape_award(award_key: str) -> List[AwardRecord]:
    """
    Scrape a single award from Wikidata.

    Args:
        award_key: Key from AWARD_CONFIGS

    Returns:
        List of award records
    """
    config = AWARD_CONFIGS[award_key]
    logger.info(f"Scraping {config['name']} - {config['category']}")

    all_records = []

    try:
        # Query winners and nominees separately to avoid timeouts
        require_book = config.get('require_book_filter', True)

        # Get winners
        logger.info(f"  Querying winners...")
        if config['use_p361']:
            winners_query = build_p361_winners_query(config['q_id'], config['category_filter'], require_book=require_book)
        else:
            winners_query = build_direct_winners_query(config['q_id'], require_book=require_book)

        winners_bindings = execute_sparql_query(winners_query)
        winner_records = parse_sparql_results(
            winners_bindings,
            config['name'],
            config['category'],
            AwardStatus.WINNER.value
        )
        all_records.extend(winner_records)
        logger.info(f"  Found {len(winner_records)} winners")

        # Get nominees (optional - may timeout for some awards)
        logger.info(f"  Querying nominees...")
        try:
            if config['use_p361']:
                nominees_query = build_p361_nominees_query(config['q_id'], config['category_filter'], require_book=require_book)
            else:
                nominees_query = build_direct_nominees_query(config['q_id'], require_book=require_book)

            nominees_bindings = execute_sparql_query(nominees_query)
            nominee_records = parse_sparql_results(
                nominees_bindings,
                config['name'],
                config['category'],
                AwardStatus.NOMINEE.value
            )
            all_records.extend(nominee_records)
            logger.info(f"  Found {len(nominee_records)} nominees")
        except Exception as e:
            logger.warning(f"  Could not fetch nominees (may timeout): {e}")

        logger.info(f"Total: {len(all_records)} records for {config['name']} - {config['category']}")
        return all_records

    except Exception as e:
        logger.error(f"Failed to scrape {award_key}: {e}")
        return []


def scrape_all_wikidata() -> pd.DataFrame:
    """
    Scrape all awards from Wikidata and return as DataFrame.
    Also includes Agatha Award from Wikipedia (Wikidata has poor coverage).

    Returns:
        DataFrame with all award records
    """
    logger.info("Starting Wikidata SPARQL scraping for all awards")

    all_records = []

    for award_key in AWARD_CONFIGS.keys():
        try:
            records = scrape_award(award_key)
            all_records.extend(records)
        except Exception as e:
            logger.error(f"Failed to scrape {award_key}: {e}")

    df = pd.DataFrame(all_records)
    logger.info(f"Total Wikidata records scraped: {len(df)}")

    # Add Agatha Award from Wikipedia (better coverage than Wikidata)
    try:
        from scrapers.agatha_scraper import scrape_agatha_awards
        agatha_df = scrape_agatha_awards()
        if not agatha_df.empty:
            df = pd.concat([df, agatha_df], ignore_index=True)
            logger.info(f"Added {len(agatha_df)} Agatha Award records from Wikipedia")
    except Exception as e:
        logger.error(f"Failed to scrape Agatha Awards: {e}")

    # Add National Book Award from Wikipedia (better coverage than Wikidata)
    try:
        from scrapers.nba_scraper import scrape_nba_fiction
        nba_df = scrape_nba_fiction()
        if not nba_df.empty:
            df = pd.concat([df, nba_df], ignore_index=True)
            logger.info(f"Added {len(nba_df)} National Book Award records from Wikipedia")
    except Exception as e:
        logger.error(f"Failed to scrape National Book Award: {e}")

    # Add Giller Prize from Wikipedia (better coverage than Wikidata)
    try:
        from scrapers.giller_scraper import scrape_giller_prize
        giller_df = scrape_giller_prize()
        if not giller_df.empty:
            df = pd.concat([df, giller_df], ignore_index=True)
            logger.info(f"Added {len(giller_df)} Giller Prize records from Wikipedia")
    except Exception as e:
        logger.error(f"Failed to scrape Giller Prize: {e}")

    logger.info(f"Total records after all scraping: {len(df)}")

    return df
