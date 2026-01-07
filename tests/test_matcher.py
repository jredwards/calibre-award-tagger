"""
Unit tests for the fuzzy matching engine.
"""

import pytest
import pandas as pd
from lib_interface import CalibreBook
from matcher import (
    extract_last_name,
    normalize_for_matching,
    match_authors,
    match_titles,
    find_matches,
    filter_duplicate_tags,
    generate_tag_assignments,
    BookMatch
)


class TestExtractLastName:
    """Tests for extract_last_name function."""

    def test_first_last_format(self):
        """Test extracting last name from First Last format."""
        assert extract_last_name("Frank Herbert") == "Herbert"
        assert extract_last_name("Isaac Asimov") == "Asimov"

    def test_first_middle_last_format(self):
        """Test extracting last name with middle name."""
        assert extract_last_name("Ursula K. Le Guin") == "Guin"
        assert extract_last_name("J.R.R. Tolkien") == "Tolkien"

    def test_last_first_format(self):
        """Test extracting last name from Last, First format."""
        assert extract_last_name("Herbert, Frank") == "Herbert"
        assert extract_last_name("Le Guin, Ursula K.") == "Le Guin"

    def test_single_name(self):
        """Test handling single names."""
        assert extract_last_name("Voltaire") == "Voltaire"

    def test_whitespace(self):
        """Test handling whitespace."""
        assert extract_last_name("  Frank Herbert  ") == "Herbert"


class TestNormalizeForMatching:
    """Tests for normalize_for_matching function."""

    def test_lowercase_conversion(self):
        """Test conversion to lowercase."""
        assert normalize_for_matching("The Fifth Season") == "fifth season"
        assert normalize_for_matching("DUNE") == "dune"

    def test_remove_articles(self):
        """Test removing articles."""
        assert normalize_for_matching("The Book") == "book"
        assert normalize_for_matching("A Tale") == "tale"
        assert normalize_for_matching("An Adventure") == "adventure"

    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        assert normalize_for_matching("Too   Many   Spaces") == "too many spaces"

    def test_combined_normalization(self):
        """Test combined normalization."""
        assert normalize_for_matching("The  Book  Title") == "book title"


class TestMatchAuthors:
    """Tests for match_authors function."""

    def test_exact_match(self):
        """Test exact author matches."""
        score = match_authors("Frank Herbert", "Frank Herbert")
        assert score == 100.0

    def test_exact_match_case_insensitive(self):
        """Test exact match ignoring case."""
        score = match_authors("Frank Herbert", "frank herbert")
        assert score == 100.0

    def test_last_name_match(self):
        """Test matching by last name."""
        score = match_authors("Frank Herbert", "F. Herbert")
        assert score >= 75.0  # Should be reasonable due to last name match

    def test_different_authors(self):
        """Test completely different authors."""
        score = match_authors("Frank Herbert", "Isaac Asimov")
        assert score < 50.0  # Should be low

    def test_similar_names(self):
        """Test similar but not identical names."""
        score = match_authors("Ursula K. Le Guin", "Ursula Le Guin")
        assert score >= 85.0  # Should be high


class TestMatchTitles:
    """Tests for match_titles function."""

    def test_exact_match(self):
        """Test exact title matches."""
        score = match_titles("Dune", "Dune")
        assert score == 100.0

    def test_exact_match_case_insensitive(self):
        """Test exact match ignoring case."""
        score = match_titles("Dune", "dune")
        assert score == 100.0

    def test_match_with_subtitle(self):
        """Test matching titles with subtitles."""
        score = match_titles("Dune: A Novel", "Dune")
        assert score >= 90.0  # Should match well after subtitle removal

    def test_match_ignoring_articles(self):
        """Test matching ignoring articles."""
        score = match_titles("The Fifth Season", "Fifth Season")
        assert score >= 95.0

    def test_different_titles(self):
        """Test completely different titles."""
        score = match_titles("Dune", "Foundation")
        assert score < 50.0

    def test_similar_titles(self):
        """Test similar titles."""
        score = match_titles("The City and The City", "The City & The City")
        assert score >= 80.0  # Fuzzy match handles minor differences


class TestFindMatches:
    """Tests for find_matches function."""

    def test_find_exact_match(self):
        """Test finding exact matches."""
        books = [
            CalibreBook(1, "Dune", "Frank Herbert")
        ]

        awards_df = pd.DataFrame([
            {
                'prize': 'Hugo',
                'category': 'Best Novel',
                'year': 1966,
                'status': 'Winner',
                'title': 'Dune',
                'author': 'Frank Herbert'
            }
        ])

        matches = find_matches(books, awards_df)

        assert len(matches) == 1
        assert matches[0].book.id == 1
        assert matches[0].award_record['prize'] == 'Hugo'
        assert matches[0].confidence >= 95.0

    def test_find_fuzzy_match(self):
        """Test finding fuzzy matches."""
        books = [
            CalibreBook(1, "The Fifth Season", "N.K. Jemisin")
        ]

        awards_df = pd.DataFrame([
            {
                'prize': 'Hugo',
                'category': 'Best Novel',
                'year': 2016,
                'status': 'Winner',
                'title': 'Fifth Season',  # Missing "The"
                'author': 'N.K. Jemisin'   # Author must match exactly enough (>95%)
            }
        ])

        matches = find_matches(books, awards_df)

        assert len(matches) == 1

    def test_author_constraint(self):
        """Test that author must match before checking title."""
        books = [
            CalibreBook(1, "The City", "China Miéville")
        ]

        awards_df = pd.DataFrame([
            {
                'prize': 'Hugo',
                'category': 'Best Novel',
                'year': 2020,
                'status': 'Winner',
                'title': 'The City We Became',  # Similar title
                'author': 'N.K. Jemisin'        # Different author
            }
        ])

        matches = find_matches(books, awards_df)

        # Should not match because authors don't match
        assert len(matches) == 0

    def test_no_matches(self):
        """Test when no matches are found."""
        books = [
            CalibreBook(1, "Unknown Book", "Unknown Author")
        ]

        awards_df = pd.DataFrame([
            {
                'prize': 'Hugo',
                'category': 'Best Novel',
                'year': 2020,
                'status': 'Winner',
                'title': 'Known Book',
                'author': 'Known Author'
            }
        ])

        matches = find_matches(books, awards_df)

        assert len(matches) == 0

    def test_multiple_authors(self):
        """Test matching with multiple authors."""
        books = [
            CalibreBook(1, "Good Omens", "Neil Gaiman, Terry Pratchett")
        ]

        awards_df = pd.DataFrame([
            {
                'prize': 'Some Award',
                'category': 'Best Novel',
                'year': 1990,
                'status': 'Winner',
                'title': 'Good Omens',
                'author': 'Neil Gaiman'
            }
        ])

        matches = find_matches(books, awards_df)

        # Should match because one of the authors matches
        assert len(matches) == 1


class TestFilterDuplicateTags:
    """Tests for filter_duplicate_tags function."""

    def test_filter_duplicate_tags_same_book(self):
        """Test filtering duplicate tags for the same book."""
        book = CalibreBook(1, "Dune", "Frank Herbert")

        # Create duplicate matches with different confidence
        award1 = {
            'prize': 'Hugo',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'Frank Herbert'
        }

        award2 = {
            'prize': 'Hugo',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'F. Herbert'
        }

        match1 = BookMatch(book, award1, confidence=100.0)
        match2 = BookMatch(book, award2, confidence=90.0)

        # Both generate the same tag
        assert match1.tag == match2.tag

        filtered = filter_duplicate_tags([match1, match2])

        # Should keep only the highest confidence match
        assert len(filtered) == 1
        assert filtered[0].confidence == 100.0

    def test_keep_different_tags(self):
        """Test keeping different tags for the same book."""
        book = CalibreBook(1, "Dune", "Frank Herbert")

        award1 = {
            'prize': 'Hugo',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'Frank Herbert'
        }

        award2 = {
            'prize': 'Nebula',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'Frank Herbert'
        }

        match1 = BookMatch(book, award1, confidence=100.0)
        match2 = BookMatch(book, award2, confidence=100.0)

        # Different tags
        assert match1.tag != match2.tag

        filtered = filter_duplicate_tags([match1, match2])

        # Should keep both
        assert len(filtered) == 2


class TestGenerateTagAssignments:
    """Tests for generate_tag_assignments function."""

    def test_generate_assignments_single_book(self):
        """Test generating assignments for a single book."""
        book = CalibreBook(1, "Dune", "Frank Herbert")

        award1 = {
            'prize': 'Hugo',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'Frank Herbert'
        }

        award2 = {
            'prize': 'Nebula',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'Frank Herbert'
        }

        matches = [
            BookMatch(book, award1, confidence=100.0),
            BookMatch(book, award2, confidence=100.0)
        ]

        assignments = generate_tag_assignments(matches)

        assert 1 in assignments
        assert len(assignments[1]) == 2

    def test_generate_assignments_multiple_books(self):
        """Test generating assignments for multiple books."""
        book1 = CalibreBook(1, "Dune", "Frank Herbert")
        book2 = CalibreBook(2, "Foundation", "Isaac Asimov")

        award1 = {
            'prize': 'Hugo',
            'category': 'Best Novel',
            'year': 1966,
            'status': 'Winner',
            'title': 'Dune',
            'author': 'Frank Herbert'
        }

        award2 = {
            'prize': 'Hugo',
            'category': 'Best Novel',
            'year': 1951,
            'status': 'Winner',
            'title': 'Foundation',
            'author': 'Isaac Asimov'
        }

        matches = [
            BookMatch(book1, award1, confidence=100.0),
            BookMatch(book2, award2, confidence=100.0)
        ]

        assignments = generate_tag_assignments(matches)

        assert len(assignments) == 2
        assert 1 in assignments
        assert 2 in assignments
