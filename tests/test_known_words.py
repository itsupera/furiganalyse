import pytest

from furiganalyse.known_words import (
    sanitize_list_name,
    list_available_word_lists,
    load_word_list,
)


class TestSanitizeListName:
    """Tests for sanitize_list_name function"""

    def test_removes_csv_extension(self):
        assert sanitize_list_name("JLPT_N5.csv") == "JLPT N5"
        assert sanitize_list_name("words.CSV") == "words"

    def test_replaces_underscores_with_spaces(self):
        assert sanitize_list_name("my_word_list.csv") == "my word list"
        assert sanitize_list_name("JLPT_N5") == "JLPT N5"

    def test_handles_no_extension(self):
        assert sanitize_list_name("JLPT_N5") == "JLPT N5"

    def test_strips_control_characters(self):
        # Control characters should be removed
        assert sanitize_list_name("test\x00name.csv") == "testname"
        assert sanitize_list_name("test\nname.csv") == "testname"
        assert sanitize_list_name("test\tname.csv") == "testname"

    def test_normalizes_whitespace(self):
        assert sanitize_list_name("test  name.csv") == "test name"
        # Double underscores become double spaces, then normalized to single
        assert sanitize_list_name("test__name.csv") == "test name"

    def test_empty_string(self):
        assert sanitize_list_name("") == ""
        assert sanitize_list_name(".csv") == ""


class TestListAvailableWordLists:
    """Tests for list_available_word_lists function"""

    def test_returns_list_of_tuples(self):
        result = list_available_word_lists()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 3

    def test_includes_jlpt_files(self):
        """Should include the JLPT files we created"""
        result = list_available_word_lists()
        filenames = [name for name, _, _ in result]
        assert "JLPT_N5.csv" in filenames
        assert "JLPT_N1.csv" in filenames

    def test_display_names_are_sanitized(self):
        """Display names should have underscores replaced with spaces"""
        result = list_available_word_lists()
        for filename, display_name, _ in result:
            if "JLPT_N5" in filename:
                assert display_name == "JLPT N5"
                break

    def test_sorted_by_filename(self):
        """Results should be sorted by filename"""
        result = list_available_word_lists()
        filenames = [name for name, _, _ in result]
        assert filenames == sorted(filenames)

    def test_includes_word_count(self):
        """Word count should match loaded word list size"""
        result = list_available_word_lists()
        for filename, _, word_count in result:
            if "JLPT_N5" in filename:
                words = load_word_list(filename)
                assert word_count == len(words)
                assert word_count > 0
                break


class TestLoadWordList:
    """Tests for load_word_list function"""

    def test_loads_jlpt_n5(self):
        """Should load JLPT N5 word list"""
        words = load_word_list("JLPT_N5.csv")
        assert isinstance(words, set)
        assert len(words) > 0
        # Common N5 words should be present
        assert "私" in words or "あなた" in words

    def test_loads_without_extension(self):
        """Should work without .csv extension"""
        words = load_word_list("JLPT_N5")
        assert isinstance(words, set)
        assert len(words) > 0

    def test_cumulative_lists(self):
        """N4 list should contain more words than N5"""
        n5_words = load_word_list("JLPT_N5")
        n4_words = load_word_list("JLPT_N4")
        n1_words = load_word_list("JLPT_N1")

        assert len(n4_words) > len(n5_words)
        assert len(n1_words) > len(n4_words)

        # N4 should be a superset of N5
        assert n5_words.issubset(n4_words)

    def test_file_not_found(self):
        """Should raise FileNotFoundError for nonexistent file"""
        with pytest.raises(FileNotFoundError):
            load_word_list("nonexistent_file.csv")

    def test_caching(self):
        """Loading same file twice should return same object (cached)"""
        # Clear cache first
        load_word_list.cache_clear()

        words1 = load_word_list("JLPT_N5.csv")
        words2 = load_word_list("JLPT_N5.csv")
        assert words1 is words2  # Same object due to caching
