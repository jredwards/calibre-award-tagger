"""
Unit tests for author name normalization.
"""

import pytest
from author_normalizer import AuthorNormalizer, normalize_title


class TestNormalizeTitle:
    """Tests for normalize_title function."""

    def test_remove_subtitle_after_colon(self):
        """Test removing subtitle after colon."""
        assert normalize_title("Dune: A Novel") == "Dune"
        assert normalize_title("The Fifth Season: Book One") == "The Fifth Season"

    def test_remove_subtitle_in_parentheses(self):
        """Test removing subtitle in parentheses."""
        assert normalize_title("Foundation (First Book)") == "Foundation"
        assert normalize_title("Neuromancer (Novel)") == "Neuromancer"

    def test_preserve_title_without_subtitle(self):
        """Test preserving titles without subtitles."""
        assert normalize_title("The Fifth Season") == "The Fifth Season"
        assert normalize_title("Dune") == "Dune"

    def test_clean_whitespace(self):
        """Test cleaning whitespace."""
        assert normalize_title("Title  With  Spaces") == "Title With Spaces"
        assert normalize_title("  Leading  ") == "Leading"


class TestAuthorNormalizer:
    """Tests for AuthorNormalizer class."""

    def test_basic_normalization(self):
        """Test basic author name normalization."""
        normalizer = AuthorNormalizer()

        # Should normalize whitespace
        assert normalizer.get_canonical_name("Frank  Herbert") == "Frank Herbert"
        # Note: "Ursula Le Guin" gets normalized to canonical "Ursula K. Le Guin"
        assert normalizer.get_canonical_name("  Ursula Le Guin  ") == "Ursula K. Le Guin"

    def test_last_first_format(self):
        """Test converting Last, First format."""
        normalizer = AuthorNormalizer()

        assert normalizer.get_canonical_name("Herbert, Frank") == "Frank Herbert"
        assert normalizer.get_canonical_name("Le Guin, Ursula K.") == "Ursula K. Le Guin"

    def test_known_aliases(self):
        """Test known author aliases."""
        normalizer = AuthorNormalizer()

        # Robert Galbraith is J.K. Rowling
        assert normalizer.get_canonical_name("Robert Galbraith") == "J.K. Rowling"
        assert normalizer.get_canonical_name("J.K. Rowling") == "J.K. Rowling"

        # Ursula Le Guin variations
        assert normalizer.get_canonical_name("Ursula Le Guin") == "Ursula K. Le Guin"
        assert normalizer.get_canonical_name("Ursula K. Le Guin") == "Ursula K. Le Guin"

    def test_caching(self):
        """Test that results are cached."""
        normalizer = AuthorNormalizer()

        # First call
        result1 = normalizer.get_canonical_name("Frank Herbert")

        # Should be cached
        assert "Frank Herbert" in normalizer.aliases

        # Second call should return cached result
        result2 = normalizer.get_canonical_name("Frank Herbert")

        assert result1 == result2

    def test_batch_normalize(self):
        """Test batch normalization."""
        normalizer = AuthorNormalizer()

        authors = {"Frank Herbert", "Isaac Asimov", "Ursula Le Guin"}
        results = normalizer.batch_normalize(authors)

        assert len(results) == 3
        assert results["Frank Herbert"] == "Frank Herbert"
        assert results["Isaac Asimov"] == "Isaac Asimov"
        assert results["Ursula Le Guin"] == "Ursula K. Le Guin"

    def test_empty_author(self):
        """Test handling empty author names."""
        normalizer = AuthorNormalizer()

        assert normalizer.get_canonical_name("") == ""
        assert normalizer.get_canonical_name("   ") == ""
