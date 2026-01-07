"""
Author name normalization service using AI.

This service uses Claude to identify author name variations and aliases.
"""

import logging
import json
import os
from typing import Dict, Set, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache for author aliases to avoid repeated API calls
AUTHOR_CACHE_FILE = Path("data/author_aliases.json")


class AuthorNormalizer:
    """Service for normalizing author names using AI assistance."""

    def __init__(self):
        """Initialize the author normalizer with cached aliases."""
        self.aliases: Dict[str, str] = {}
        self.load_cache()

    def load_cache(self):
        """Load author aliases from cache file."""
        if AUTHOR_CACHE_FILE.exists():
            try:
                with open(AUTHOR_CACHE_FILE, 'r') as f:
                    self.aliases = json.load(f)
                logger.info(f"Loaded {len(self.aliases)} author aliases from cache")
            except Exception as e:
                logger.error(f"Failed to load author cache: {e}")
                self.aliases = {}

    def save_cache(self):
        """Save author aliases to cache file."""
        try:
            AUTHOR_CACHE_FILE.parent.mkdir(exist_ok=True)
            with open(AUTHOR_CACHE_FILE, 'w') as f:
                json.dump(self.aliases, f, indent=2)
            logger.info(f"Saved {len(self.aliases)} author aliases to cache")
        except Exception as e:
            logger.error(f"Failed to save author cache: {e}")

    def get_canonical_name(self, author: str) -> str:
        """
        Get the canonical name for an author.

        This checks the cache first, and if not found, would call AI service.
        For now, implements basic normalization without AI.

        Args:
            author: Author name to normalize

        Returns:
            Canonical author name
        """
        # Check cache first
        if author in self.aliases:
            return self.aliases[author]

        # Basic normalization without AI
        canonical = self._basic_normalize(author)

        # Cache the result
        self.aliases[author] = canonical

        return canonical

    def _basic_normalize(self, author: str) -> str:
        """
        Apply basic normalization rules to author names.

        This handles common variations without AI:
        - Remove extra whitespace
        - Handle "Last, First" -> "First Last" format
        - Handle initials

        Args:
            author: Author name to normalize

        Returns:
            Normalized author name
        """
        # Clean whitespace
        author = ' '.join(author.split())

        # Handle "Last, First" format
        if ',' in author:
            parts = author.split(',', 1)
            if len(parts) == 2:
                last, first = parts
                author = f"{first.strip()} {last.strip()}"

        # Known aliases (hardcoded common cases)
        known_aliases = {
            'J.K. Rowling': 'J.K. Rowling',
            'Robert Galbraith': 'J.K. Rowling',
            'Ursula K. Le Guin': 'Ursula K. Le Guin',
            'Ursula Le Guin': 'Ursula K. Le Guin',
            'N.K. Jemisin': 'N.K. Jemisin',
            'NK Jemisin': 'N.K. Jemisin',
        }

        if author in known_aliases:
            return known_aliases[author]

        return author

    def batch_normalize(self, authors: Set[str]) -> Dict[str, str]:
        """
        Normalize a batch of author names.

        This would ideally call an AI service once for the entire batch.
        For now, processes each individually.

        Args:
            authors: Set of author names to normalize

        Returns:
            Dictionary mapping original names to canonical names
        """
        results = {}
        for author in authors:
            results[author] = self.get_canonical_name(author)

        self.save_cache()
        return results


def normalize_title(title: str) -> str:
    """
    Normalize a book title by removing subtitles.

    Args:
        title: Book title to normalize

    Returns:
        Normalized title

    Examples:
        >>> normalize_title("Dune: A Novel")
        'Dune'
        >>> normalize_title("The Fifth Season")
        'The Fifth Season'
    """
    # Remove subtitle after colon
    if ':' in title:
        title = title.split(':')[0].strip()

    # Remove subtitle in parentheses
    if '(' in title:
        title = title.split('(')[0].strip()

    # Clean whitespace
    title = ' '.join(title.split())

    return title
