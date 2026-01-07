"""
Unit tests for base Wikipedia scraping utilities.
"""

import pytest
from scrapers.base_wiki import (
    clean_citation_marks,
    extract_year,
    normalize_whitespace,
    clean_dataframe
)
import pandas as pd


class TestCleanCitationMarks:
    """Tests for clean_citation_marks function."""

    def test_remove_simple_citation(self):
        """Test removing simple numeric citations."""
        assert clean_citation_marks("Dune[1]") == "Dune"
        assert clean_citation_marks("Frank Herbert[2]") == "Frank Herbert"

    def test_remove_letter_citation(self):
        """Test removing letter citations."""
        assert clean_citation_marks("Book Title[a]") == "Book Title"
        assert clean_citation_marks("Author Name[b]") == "Author Name"

    def test_remove_note_citation(self):
        """Test removing note-style citations."""
        assert clean_citation_marks("Title[note 1]") == "Title"
        assert clean_citation_marks("Author[note 2]") == "Author"

    def test_remove_multiple_citations(self):
        """Test removing multiple citations."""
        assert clean_citation_marks("Title[1][a][note 2]") == "Title"
        assert clean_citation_marks("Author[a][b]") == "Author"

    def test_clean_whitespace_after_removal(self):
        """Test that extra whitespace is removed."""
        assert clean_citation_marks("First [1]  Last") == "First Last"

    def test_handle_non_string_input(self):
        """Test handling of non-string inputs."""
        assert clean_citation_marks(None) == ""
        assert clean_citation_marks(123) == "123"

    def test_no_citations(self):
        """Test strings without citations."""
        assert clean_citation_marks("Clean Title") == "Clean Title"


class TestExtractYear:
    """Tests for extract_year function."""

    def test_extract_four_digit_year(self):
        """Test extracting 4-digit years."""
        assert extract_year("1966") == 1966
        assert extract_year("2020") == 2020

    def test_extract_year_from_text(self):
        """Test extracting year from text."""
        assert extract_year("Winner (2020)") == 2020
        assert extract_year("Published in 1984") == 1984

    def test_extract_year_from_range(self):
        """Test extracting first year from range."""
        assert extract_year("1966-1967") == 1966

    def test_no_year_found(self):
        """Test when no year is present."""
        assert extract_year("no year here") is None
        assert extract_year("abc") is None

    def test_integer_input(self):
        """Test handling integer input."""
        assert extract_year(1966) == 1966
        assert extract_year(2020) == 2020

    def test_invalid_year_range(self):
        """Test years outside valid range."""
        assert extract_year(1800) is None
        assert extract_year(2200) is None

    def test_year_at_boundaries(self):
        """Test years at range boundaries."""
        assert extract_year(1900) == 1900
        assert extract_year(2100) == 2100


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""

    def test_collapse_multiple_spaces(self):
        """Test collapsing multiple spaces."""
        assert normalize_whitespace("Too    many    spaces") == "Too many spaces"

    def test_remove_leading_trailing_space(self):
        """Test removing leading/trailing whitespace."""
        assert normalize_whitespace("  Text  ") == "Text"

    def test_handle_tabs_and_newlines(self):
        """Test handling tabs and newlines."""
        assert normalize_whitespace("Text\t\twith\ttabs") == "Text with tabs"
        assert normalize_whitespace("Text\nwith\nnewlines") == "Text with newlines"

    def test_handle_non_string(self):
        """Test handling non-string inputs."""
        assert normalize_whitespace(None) == ""
        assert normalize_whitespace(123) == "123"


class TestCleanDataFrame:
    """Tests for clean_dataframe function."""

    def test_clean_dataframe_citations(self):
        """Test cleaning citations from DataFrame."""
        df = pd.DataFrame({
            'Title': ['Dune[1]', 'Foundation[2]'],
            'Author': ['Frank Herbert[a]', 'Isaac Asimov[b]']
        })

        cleaned = clean_dataframe(df)

        assert cleaned['Title'][0] == 'Dune'
        assert cleaned['Title'][1] == 'Foundation'
        assert cleaned['Author'][0] == 'Frank Herbert'
        assert cleaned['Author'][1] == 'Isaac Asimov'

    def test_clean_dataframe_whitespace(self):
        """Test normalizing whitespace in DataFrame."""
        df = pd.DataFrame({
            'Title': ['Too    Many    Spaces', '  Leading  '],
            'Author': ['Author  Name', 'Another   One']
        })

        cleaned = clean_dataframe(df)

        assert cleaned['Title'][0] == 'Too Many Spaces'
        assert cleaned['Title'][1] == 'Leading'
        assert cleaned['Author'][0] == 'Author Name'
        assert cleaned['Author'][1] == 'Another One'

    def test_clean_dataframe_preserves_structure(self):
        """Test that DataFrame structure is preserved."""
        df = pd.DataFrame({
            'Col1': ['A', 'B'],
            'Col2': [1, 2]
        })

        cleaned = clean_dataframe(df)

        assert list(cleaned.columns) == ['Col1', 'Col2']
        assert len(cleaned) == 2

    def test_clean_dataframe_with_nulls(self):
        """Test handling null values in DataFrame."""
        df = pd.DataFrame({
            'Title': ['Valid[1]', None],
            'Author': [None, 'Author[a]']
        })

        cleaned = clean_dataframe(df)

        assert cleaned['Title'][0] == 'Valid'
        assert pd.isna(cleaned['Title'][1])
        assert pd.isna(cleaned['Author'][0])
        assert cleaned['Author'][1] == 'Author'
