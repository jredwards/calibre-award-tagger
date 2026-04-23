"""
Interface for interacting with Calibre library using calibredb.
"""

import json
import logging
import subprocess
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CalibreBook:
    """Represents a book in the Calibre library."""

    def __init__(self, book_id: int, title: str, authors: str, tags: str = ""):
        """
        Initialize a Calibre book.

        Args:
            book_id: Calibre book ID
            title: Book title
            authors: Comma-separated list of authors
            tags: Comma-separated list of existing tags
        """
        self.id = book_id
        self.title = title
        self.authors = authors
        self.tags = _normalize_tags(tags)

    def __repr__(self):
        return f"CalibreBook(id={self.id}, title='{self.title}', authors='{self.authors}')"


def get_calibre_books() -> List[CalibreBook]:
    """
    Extract books from Calibre library using calibredb.

    Returns:
        List of CalibreBook objects

    Raises:
        subprocess.CalledProcessError: If calibredb command fails
        FileNotFoundError: If calibredb is not found in PATH
    """
    logger.info("Extracting books from Calibre library")

    try:
        # Run calibredb list with machine-readable output
        result = subprocess.run(
            ['calibredb', 'list', '--for-machine', '--fields', 'id,title,authors,tags'],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse JSON output — Calibre 9.7+ appends "Integration status: True"
        # after the JSON array, so use raw_decode to parse only the first value.
        books_data, _ = json.JSONDecoder().raw_decode(result.stdout.strip())

        books = []
        for book_data in books_data:
            book = CalibreBook(
                book_id=book_data['id'],
                title=book_data.get('title', ''),
                authors=book_data.get('authors', ''),
                tags=book_data.get('tags', '')
            )
            books.append(book)

        logger.info(f"Found {len(books)} books in Calibre library")
        return books

    except FileNotFoundError:
        logger.error("calibredb command not found. Is Calibre installed?")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"calibredb command failed: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse calibredb output: {e}")
        raise


def get_book_tags(book_id: int) -> List[str]:
    """
    Get current tags for a specific book.

    Args:
        book_id: Calibre book ID

    Returns:
        List of current tags

    Raises:
        subprocess.CalledProcessError: If calibredb command fails
    """
    try:
        result = subprocess.run(
            ['calibredb', 'list', '--for-machine', '--fields', 'tags', '--search', f'id:{book_id}'],
            capture_output=True,
            text=True,
            check=True
        )

        books_data, _ = json.JSONDecoder().raw_decode(result.stdout.strip())
        if books_data:
            return _normalize_tags(books_data[0].get('tags'))

        return []

    except Exception as e:
        logger.error(f"Failed to get tags for book {book_id}: {e}")
        return []


def apply_tags(book_id: int, new_tags: List[str], append: bool = True) -> bool:
    """
    Apply tags to a book in Calibre library.

    Args:
        book_id: Calibre book ID
        new_tags: List of tags to apply
        append: If True, append to existing tags. If False, replace all tags.

    Returns:
        True if successful, False otherwise
    """
    if not new_tags:
        logger.warning(f"No tags to apply for book {book_id}")
        return True

    try:
        if append:
            # Get existing tags
            existing_tags = get_book_tags(book_id)

            # Merge with new tags (avoid duplicates)
            all_tags = list(set(existing_tags + new_tags))
        else:
            all_tags = new_tags

        # Format tags as comma-separated string
        tags_str = ','.join(all_tags)

        # Apply tags using calibredb
        result = subprocess.run(
            ['calibredb', 'set_metadata', str(book_id), '--field', f'tags:{tags_str}'],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info(f"Applied {len(new_tags)} tags to book {book_id}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to apply tags to book {book_id}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error applying tags to book {book_id}: {e}")
        return False


def batch_apply_tags(tag_assignments: Dict[int, List[str]]) -> Dict[int, bool]:
    """
    Apply tags to multiple books.

    Args:
        tag_assignments: Dictionary mapping book IDs to lists of tags

    Returns:
        Dictionary mapping book IDs to success status
    """
    logger.info(f"Applying tags to {len(tag_assignments)} books")

    results = {}
    success_count = 0
    failure_count = 0

    for book_id, tags in tag_assignments.items():
        success = apply_tags(book_id, tags, append=True)
        results[book_id] = success

        if success:
            success_count += 1
        else:
            failure_count += 1

    logger.info(f"Tag application complete: {success_count} succeeded, {failure_count} failed")

    return results


def verify_calibredb() -> bool:
    """
    Verify that calibredb is available and working.

    Returns:
        True if calibredb is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['calibredb', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"calibredb found: {result.stdout.strip()}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("calibredb not found or not working")
        return False


def get_library_path() -> Optional[Path]:
    """
    Get the path to the Calibre library.

    Returns:
        Path to the Calibre library, or None if not found

    Raises:
        subprocess.CalledProcessError: If calibredb command fails
    """
    try:
        # Get library path by listing with --for-machine and extracting from first book
        # Alternatively, we can parse the output of calibredb list to infer the path
        # For now, we'll use a more direct approach: calibredb uses CALIBRE_LIBRARY_PATH env var
        # or the default library location

        # Run a simple command and check if we can find the library path
        result = subprocess.run(
            ['calibredb', 'list', '--limit', '1', '--for-machine'],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse to get library info
        # The library path can be obtained from calibredb's context
        # For a more reliable method, check the Calibre preferences

        # Actually, the simplest way is to check environment variable or use default
        # But calibredb doesn't have a direct --library-path flag to GET the path
        # We need to try the default location or ask user

        # Let's use a different approach: call calibredb with a test command
        # and infer from the metadata.db location

        # Most reliable: check common default locations or use calibredb's working directory
        import os

        # Check environment variable first
        env_path = os.environ.get('CALIBRE_LIBRARY_PATH')
        if env_path:
            library_path = Path(env_path)
            if library_path.exists():
                return library_path

        # Read Calibre's own preferences to find the current library path.
        # gui.json stores library_usage_stats: {path: use_count, ...}
        import json
        appdata = os.environ.get('APPDATA', '')
        gui_json = Path(appdata) / 'calibre' / 'gui.json'
        if gui_json.exists():
            try:
                prefs = json.loads(gui_json.read_text(encoding='utf-8', errors='replace'))
                usage = prefs.get('library_usage_stats', {})
                if usage:
                    # Pick the most-used library
                    best = max(usage, key=lambda p: usage[p])
                    candidate = Path(best)
                    if (candidate / 'metadata.db').exists():
                        logger.info(f"Found Calibre library from preferences: {candidate}")
                        return candidate
            except Exception as e:
                logger.warning(f"Could not read Calibre preferences: {e}")

        # Fall back to common default locations
        home = Path.home()
        default_locations = [
            home / "Calibre Library",
            home / "Documents" / "Calibre Library",
            home / "calibre_library",
        ]

        for location in default_locations:
            if (location / "metadata.db").exists():
                logger.info(f"Found Calibre library at: {location}")
                return location

        logger.error("Could not find Calibre library path")
        return None

    except Exception as e:
        logger.error(f"Failed to get library path: {e}")
        return None


def backup_metadata_db(library_path: Optional[Path] = None) -> Optional[Path]:
    """
    Create a backup of the Calibre metadata.db file.

    Args:
        library_path: Path to Calibre library. If None, will attempt to auto-detect.

    Returns:
        Path to the backup file if successful, None otherwise
    """
    try:
        if library_path is None:
            library_path = get_library_path()

        if library_path is None:
            logger.error("Cannot backup: library path not found")
            return None

        metadata_db = library_path / "metadata.db"

        if not metadata_db.exists():
            logger.error(f"metadata.db not found at {metadata_db}")
            return None

        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = library_path / f"metadata.db.backup-{timestamp}"

        logger.info(f"Creating backup: {backup_path}")
        shutil.copy2(metadata_db, backup_path)

        # Verify backup was created
        if backup_path.exists():
            backup_size = backup_path.stat().st_size
            original_size = metadata_db.stat().st_size

            if backup_size == original_size:
                logger.info(f"Backup created successfully: {backup_path} ({backup_size:,} bytes)")
                return backup_path
            else:
                logger.error(f"Backup size mismatch: {backup_size} vs {original_size}")
                return None
        else:
            logger.error("Backup file was not created")
            return None

    except Exception as e:
        logger.error(f"Failed to backup metadata.db: {e}")
        return None


def _normalize_tags(raw_tags: Any) -> List[str]:
    """
    Normalize a tags value from calibredb (may be list or comma string) into a list.
    """
    if raw_tags is None:
        return []

    if isinstance(raw_tags, list):
        return [str(t).strip() for t in raw_tags if str(t).strip()]

    if isinstance(raw_tags, str):
        return [t.strip() for t in raw_tags.split(',') if t.strip()]

    # Fallback: coerce to string
    coerced = str(raw_tags).strip()
    return [coerced] if coerced else []


if __name__ == "__main__":
    # Test the interface
    logging.basicConfig(level=logging.INFO)

    if verify_calibredb():
        books = get_calibre_books()
        print(f"Found {len(books)} books")
        if books:
            print(f"First book: {books[0]}")
