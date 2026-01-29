"""
Module for loading and managing known word lists for furigana filtering.

Word lists are stored as CSV files in the words_lists/ directory.
Each file contains one word per line (the kanji/expression form).
"""

import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Set, List, Tuple

# Directory containing word list files
WORDS_LISTS_DIR = Path(__file__).parent / "words_lists"


def sanitize_list_name(filename: str) -> str:
    """
    Convert a filename to a display-friendly label.

    - Removes .csv extension
    - Replaces underscores with spaces
    - Strips control characters and problematic Unicode

    Example: "JLPT_N5.csv" -> "JLPT N5"
    """
    # Remove .csv extension
    name = filename
    if name.lower().endswith(".csv"):
        name = name[:-4]

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Remove control characters and normalize Unicode
    # Keep only printable characters
    cleaned = []
    for char in name:
        category = unicodedata.category(char)
        # Skip control characters (Cc), format characters (Cf),
        # surrogate (Cs), private use (Co), unassigned (Cn)
        if category[0] not in ("C",):
            cleaned.append(char)

    name = "".join(cleaned)

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()

    return name


def list_available_word_lists() -> List[Tuple[str, str, int]]:
    """
    Scan the words_lists directory for available word list CSV files.

    Returns a list of (filename, display_name, word_count) tuples, sorted by filename.
    """
    if not WORDS_LISTS_DIR.exists():
        logging.warning("Frequency lists directory not found: %s", WORDS_LISTS_DIR)
        return []

    word_lists = []
    for filepath in sorted(WORDS_LISTS_DIR.glob("*.csv")):
        filename = filepath.name
        display_name = sanitize_list_name(filename)
        words = load_word_list(filename)
        word_lists.append((filename, display_name, len(words)))

    return word_lists


@lru_cache(maxsize=16)
def load_word_list(name: str) -> Set[str]:
    """
    Load a word list from a CSV file.

    Args:
        name: The filename (with or without .csv extension) of the word list.

    Returns:
        A set of words from the file.

    Raises:
        FileNotFoundError: If the word list file doesn't exist.
    """
    # Ensure .csv extension
    if not name.lower().endswith(".csv"):
        name = name + ".csv"

    filepath = WORDS_LISTS_DIR / name

    if not filepath.exists():
        raise FileNotFoundError(f"Word list not found: {filepath}")

    words = set()
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            word = line.strip()
            if word:
                words.add(word)

    logging.info("Loaded %d words from %s", len(words), name)
    return words
