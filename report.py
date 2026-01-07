"""
Report generation for proposed tag changes.
"""

import json
import logging
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from matcher import BookMatch

logger = logging.getLogger(__name__)


def generate_json_report(matches: List[BookMatch], output_file: Path) -> Path:
    """
    Generate JSON report of proposed changes.

    Args:
        matches: List of BookMatch objects
        output_file: Path to output JSON file

    Returns:
        Path to generated report
    """
    logger.info(f"Generating JSON report to {output_file}")

    report_data = {
        "generated_at": datetime.now().isoformat(),
        "total_matches": len(matches),
        "proposed_changes": []
    }

    # Group matches by book
    from matcher import group_matches_by_book
    grouped = group_matches_by_book(matches)

    for book_id, book_matches in grouped.items():
        book = book_matches[0].book  # All matches have the same book
        tags = [match.tag for match in book_matches]
        confidences = {match.tag: match.confidence for match in book_matches}

        change = {
            "book_id": book_id,
            "title": book.title,
            "authors": book.authors,
            "existing_tags": book.tags,
            "new_tags": tags,
            "tag_confidences": confidences
        }

        report_data["proposed_changes"].append(change)

    # Save to file
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)

    logger.info(f"JSON report saved: {len(report_data['proposed_changes'])} books with proposed changes")

    return output_file


def generate_text_report(matches: List[BookMatch]) -> str:
    """
    Generate human-readable text report of proposed changes.

    Args:
        matches: List of BookMatch objects

    Returns:
        Formatted text report
    """
    from matcher import group_matches_by_book

    grouped = group_matches_by_book(matches)

    lines = []
    lines.append("=" * 80)
    lines.append("PROPOSED TAG CHANGES")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total books to update: {len(grouped)}")
    lines.append(f"Total tags to add: {len(matches)}")
    lines.append("")

    # Sort by book ID
    for book_id in sorted(grouped.keys()):
        book_matches = grouped[book_id]
        book = book_matches[0].book

        lines.append("-" * 80)
        lines.append(f"[BOOK ID: {book_id}]")
        lines.append(f"  Title:   {book.title}")
        lines.append(f"  Author:  {book.authors}")

        if book.tags:
            lines.append(f"  Current tags: {', '.join(book.tags)}")

        lines.append(f"  New tags to add:")

        for match in book_matches:
            lines.append(f"    - {match.tag} (confidence: {match.confidence:.1f}%)")
            lines.append(f"      Matched with: {match.award_record['title']} by {match.award_record['author']} ({match.award_record['year']})")

        lines.append("")

    lines.append("=" * 80)

    return '\n'.join(lines)


def print_summary(matches: List[BookMatch]):
    """
    Print a summary of matches to the console.

    Args:
        matches: List of BookMatch objects
    """
    from matcher import group_matches_by_book

    grouped = group_matches_by_book(matches)

    print(f"\n{'='*80}")
    print(f"MATCH SUMMARY")
    print(f"{'='*80}")
    print(f"Books matched: {len(grouped)}")
    print(f"Total tags to add: {len(matches)}")
    print(f"{'='*80}\n")

    # Count by prize
    prize_counts = {}
    for match in matches:
        prize = match.award_record['prize']
        prize_counts[prize] = prize_counts.get(prize, 0) + 1

    print("Tags by award:")
    for prize, count in sorted(prize_counts.items()):
        print(f"  {prize}: {count}")

    print(f"\n{'='*80}\n")


def save_report(matches: List[BookMatch], json_path: Path, text_path: Path):
    """
    Save both JSON and text reports.

    Args:
        matches: List of BookMatch objects
        json_path: Path for JSON report
        text_path: Path for text report
    """
    # Generate JSON report
    generate_json_report(matches, json_path)

    # Generate and save text report
    text_report = generate_text_report(matches)
    text_path.parent.mkdir(exist_ok=True)
    with open(text_path, 'w') as f:
        f.write(text_report)

    logger.info(f"Text report saved to {text_path}")

    # Print summary to console
    print_summary(matches)

    print(f"\nReports saved:")
    print(f"  JSON: {json_path}")
    print(f"  Text: {text_path}")
