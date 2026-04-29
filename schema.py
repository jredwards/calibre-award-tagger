"""
Data schema definitions for the Canonical Awards Database.
"""

from enum import Enum
from typing import TypedDict


class AwardStatus(str, Enum):
    """Award status enumeration."""
    WINNER = "Winner"
    SHORTLIST = "Shortlist"
    NOMINEE = "Nominee"


class AwardRecord(TypedDict):
    """Structure for a canonical award record."""
    prize: str          # Name of the award (e.g., "Hugo Award")
    category: str       # Award sub-category (e.g., "Best Novel")
    year: int          # Year of the award
    status: str        # "Winner", "Shortlist", or "Nominee"
    title: str         # Canonical book title
    author: str        # Canonical author name


# Canonical CSV column names
CSV_COLUMNS = ["prize", "category", "year", "status", "title", "author"]

# Tag format template
# Example: "Award: Hugo [Winner]"
TAG_FORMAT = "Award: {prize}{category_suffix} [{status}]"


def format_award_tag(prize: str, category: str, status: str) -> str:
    """
    Format an award into a Calibre tag.

    Args:
        prize: Award name (e.g., "Hugo")
        category: Category name (e.g., "Best Novel")
        status: Award status (Winner/Shortlist/Nominee)

    Returns:
        Formatted tag string

    Examples:
        >>> format_award_tag("Hugo", "Best Novel", "Winner")
        'Award: Hugo [Winner]'
        >>> format_award_tag("Agatha", "Best First Novel", "Shortlist")
        'Award: Agatha, Best First Novel [Shortlist]'
    """
    # For most awards, don't include category in tag
    # For Agatha, include the category
    if prize == "Agatha":
        category_suffix = f" - {category}"
    else:
        category_suffix = ""

    return TAG_FORMAT.format(
        prize=prize,
        category_suffix=category_suffix,
        status=status
    )


# Award configurations
AWARDS_CONFIG = {
    "hugo": {
        "name": "Hugo",
        "category_filter": ["Best Novel"],
        "url": "https://en.wikipedia.org/wiki/Hugo_Award_for_Best_Novel"
    },
    "nebula": {
        "name": "Nebula",
        "category_filter": ["Best Novel"],
        "url": "https://en.wikipedia.org/wiki/Nebula_Award_for_Best_Novel"
    },
    "clarke": {
        "name": "Arthur C. Clarke",
        "category_filter": ["Best Novel"],
        "url": "https://en.wikipedia.org/wiki/Arthur_C._Clarke_Award"
    },
    "locus": {
        "name": "Locus",
        "category_filter": ["Science Fiction Novel", "Fantasy Novel", "Horror Novel"],
        "url": "https://en.wikipedia.org/wiki/Locus_Award"
    },
    "booker": {
        "name": "Booker",
        "category_filter": ["Fiction"],
        "url": "https://en.wikipedia.org/wiki/Booker_Prize"
    },
    "international_booker": {
        "name": "International Booker",
        "category_filter": ["Fiction"],
        "url": "https://en.wikipedia.org/wiki/International_Booker_Prize"
    },
    "national_book_award": {
        "name": "National Book Award",
        "category_filter": ["Fiction"],
        "url": "https://en.wikipedia.org/wiki/National_Book_Award_for_Fiction"
    },
    "giller": {
        "name": "Giller",
        "category_filter": ["Fiction"],
        "url": "https://en.wikipedia.org/wiki/Giller_Prize"
    },
    "agatha": {
        "name": "Agatha",
        "category_filter": None,  # Include all categories
        "url": "https://en.wikipedia.org/wiki/Agatha_Award"
    },
    "pulitzer": {
        "name": "Pulitzer",
        "category_filter": ["Fiction"],
        "url": "https://en.wikipedia.org/wiki/Pulitzer_Prize_for_Fiction"
    }
}
