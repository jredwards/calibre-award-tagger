"""
Fuzzy matching engine for correlating Calibre books with award records.
"""

import logging
from time import perf_counter
from typing import List, Dict, Optional, Tuple
import pandas as pd
from rapidfuzz import fuzz, process
from lib_interface import CalibreBook
from schema import format_award_tag
from author_normalizer import normalize_title

logger = logging.getLogger(__name__)

# Matching thresholds
AUTHOR_EXACT_THRESHOLD = 95  # For author matching
TITLE_FUZZY_THRESHOLD = 90   # For title matching after author match


class BookMatch:
    """Represents a match between a Calibre book and an award record."""

    def __init__(self, book: CalibreBook, award_record: Dict, confidence: float):
        """
        Initialize a book match.

        Args:
            book: Calibre book
            award_record: Award record dictionary
            confidence: Match confidence score (0-100)
        """
        self.book = book
        self.award_record = award_record
        self.confidence = confidence

        # Generate tag
        self.tag = format_award_tag(
            prize=award_record['prize'],
            category=award_record['category'],
            status=award_record['status']
        )

    def __repr__(self):
        return f"BookMatch(book_id={self.book.id}, title='{self.book.title}', tag='{self.tag}', confidence={self.confidence:.1f})"


def extract_last_name(author: str) -> str:
    """
    Extract the last name from an author string.

    Handles formats like:
    - "First Last" -> "Last"
    - "First Middle Last" -> "Last"
    - "Last, First" -> "Last"

    Args:
        author: Author name

    Returns:
        Last name
    """
    author = author.strip()

    # Handle "Last, First" format
    if ',' in author:
        return author.split(',')[0].strip()

    # Handle "First Last" format
    parts = author.split()
    if parts:
        return parts[-1]

    return author


def normalize_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower()

    # Remove leading articles
    for article in ['the ', 'a ', 'an ']:
        if text.startswith(article):
            text = text[len(article):]
            break

    # Remove common articles in middle/end
    for article in [' the ', ' a ', ' an ']:
        text = text.replace(article, ' ')

    # Remove extra whitespace
    text = ' '.join(text.split())

    return text.strip()


def match_authors(calibre_author: str, award_author: str) -> float:
    """
    Calculate author match score.

    Uses last name matching with high threshold for certainty.

    Args:
        calibre_author: Author from Calibre library
        award_author: Author from award record

    Returns:
        Match score (0-100)
    """
    # Handle "Last, First" format
    def fix_name_format(name: str) -> str:
        """Convert 'Last, First' to 'First Last'."""
        if ',' in name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                return f"{parts[1].strip()} {parts[0].strip()}"
        return name

    calibre_author = fix_name_format(calibre_author)
    award_author = fix_name_format(award_author)

    # Normalize
    calibre_norm = normalize_for_matching(calibre_author)
    award_norm = normalize_for_matching(award_author)

    # Exact match after normalization
    if calibre_norm == award_norm:
        return 100.0

    # Last name matching
    calibre_last = normalize_for_matching(extract_last_name(calibre_author))
    award_last = normalize_for_matching(extract_last_name(award_author))

    if calibre_last == award_last:
        # Last names match exactly, check full name similarity
        return fuzz.ratio(calibre_norm, award_norm)

    # Fuzzy match on full names
    return fuzz.ratio(calibre_norm, award_norm)


def match_titles(calibre_title: str, award_title: str) -> float:
    """
    Calculate title match score using fuzzy matching.

    Args:
        calibre_title: Title from Calibre library
        award_title: Title from award record

    Returns:
        Match score (0-100)
    """
    # Normalize titles
    calibre_norm = normalize_for_matching(normalize_title(calibre_title))
    award_norm = normalize_for_matching(normalize_title(award_title))

    # Exact match
    if calibre_norm == award_norm:
        return 100.0

    # Fuzzy match
    return fuzz.ratio(calibre_norm, award_norm)


def find_matches(
    books: List[CalibreBook],
    awards_df: pd.DataFrame,
    author_threshold: float = AUTHOR_EXACT_THRESHOLD,
    title_threshold: float = TITLE_FUZZY_THRESHOLD,
    progress_every: Optional[int] = 30
) -> List[BookMatch]:
    """
    Find matches between Calibre books and award records.

    The matching process:
    1. For each Calibre book, find awards where author matches highly
    2. Among those, find awards where title also matches
    3. Only accept matches above both thresholds

    Args:
        books: List of Calibre books
        awards_df: DataFrame of award records
        author_threshold: Minimum author match score
        title_threshold: Minimum title match score
        progress_every: Log progress every N books (set to None/0 to disable)

    Returns:
        List of BookMatch objects
    """
    total_books = len(books)
    total_awards = len(awards_df)
    logger.info(f"Finding matches for {total_books} books against {total_awards} award records")

    matches = []
    start_time = perf_counter()
    last_log_time = start_time

    for idx, book in enumerate(books, start=1):
        # Handle multiple authors (Calibre stores as comma-separated)
        calibre_authors = [a.strip() for a in book.authors.split(',')]

        # Check each award record
        for _, award in awards_df.iterrows():
            award_author = award['author']

            # Check if any of the book's authors match the award author
            best_author_score = max(
                match_authors(calibre_author, award_author)
                for calibre_author in calibre_authors
            )

            # If author match is good enough, check title
            if best_author_score >= author_threshold:
                title_score = match_titles(book.title, award['title'])

                if title_score >= title_threshold:
                    # Calculate overall confidence (weighted average)
                    confidence = (best_author_score * 0.6 + title_score * 0.4)

                    match = BookMatch(
                        book=book,
                        award_record=award.to_dict(),
                        confidence=confidence
                    )
                    matches.append(match)

                    logger.debug(f"Match found: {book.title} -> {award['title']} "
                               f"(author: {best_author_score:.1f}, title: {title_score:.1f})")

        if progress_every and total_books and idx % progress_every == 0:
            now = perf_counter()
            elapsed = now - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            percent = (idx / total_books) * 100
            logger.info(
                f"[match progress] {idx}/{total_books} books "
                f"({percent:.1f}%), matches so far: {len(matches)}, "
                f"{rate:.1f} books/sec"
            )
            last_log_time = now

    total_duration = perf_counter() - start_time
    logger.info(f"Found {len(matches)} matches in {total_duration:.1f}s")

    return matches


def group_matches_by_book(matches: List[BookMatch]) -> Dict[int, List[BookMatch]]:
    """
    Group matches by book ID.

    Args:
        matches: List of BookMatch objects

    Returns:
        Dictionary mapping book IDs to lists of matches
    """
    grouped = {}

    for match in matches:
        book_id = match.book.id
        if book_id not in grouped:
            grouped[book_id] = []
        grouped[book_id].append(match)

    return grouped


def filter_duplicate_tags(matches: List[BookMatch]) -> List[BookMatch]:
    """
    Filter out duplicate tags from matches for the same book.

    If a book has multiple matches generating the same tag, keep only the highest confidence match.

    Args:
        matches: List of BookMatch objects

    Returns:
        Filtered list of BookMatch objects
    """
    # Group by book ID
    grouped = group_matches_by_book(matches)

    filtered = []

    for book_id, book_matches in grouped.items():
        # Group by tag
        tag_groups = {}
        for match in book_matches:
            if match.tag not in tag_groups:
                tag_groups[match.tag] = []
            tag_groups[match.tag].append(match)

        # Keep only the highest confidence match for each tag
        for tag, tag_matches in tag_groups.items():
            best_match = max(tag_matches, key=lambda m: m.confidence)
            filtered.append(best_match)

    logger.info(f"Filtered {len(matches)} matches to {len(filtered)} unique tags")

    return filtered


def generate_tag_assignments(matches: List[BookMatch]) -> Dict[int, List[str]]:
    """
    Generate tag assignments from matches.

    Args:
        matches: List of BookMatch objects

    Returns:
        Dictionary mapping book IDs to lists of tags to apply
    """
    # Filter duplicate tags
    filtered_matches = filter_duplicate_tags(matches)

    # Group by book
    grouped = group_matches_by_book(filtered_matches)

    # Generate assignments
    assignments = {}
    for book_id, book_matches in grouped.items():
        tags = [match.tag for match in book_matches]
        assignments[book_id] = tags

    return assignments
