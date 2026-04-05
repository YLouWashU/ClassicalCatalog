#!/usr/bin/env python3
"""
CLI: process raw extracted text with LLM to produce processed.json.

Usage:
    python process/process_reviews.py
    python process/process_reviews.py --issue 2021-11
    python process/process_reviews.py --force
"""
import argparse
import sys
from pathlib import Path

from common.config import DATA_DIR
from common.models import ProcessedIssue
from common.status import is_stage_completed, mark_stage_completed, mark_stage_failed
from process.section_analyzer import process_issue_dir


def _issue_title(issue_key: str) -> str:
    """Convert '2021-11' -> 'Gramophone November 2021'."""
    months = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    year, month = issue_key.split("-")
    return f"Gramophone {months[int(month)]} {year}"


def process_issue(issue_key: str, force: bool = False) -> None:
    issue_dir = DATA_DIR / issue_key
    if not issue_dir.exists():
        print(f"  [{issue_key}] no data directory found, run extract first", file=sys.stderr)
        return

    if is_stage_completed(issue_dir, "process") and not force:
        print(f"  [{issue_key}] process already completed, skipping")
        return

    if not is_stage_completed(issue_dir, "extract"):
        print(f"  [{issue_key}] extract not completed yet, skipping", file=sys.stderr)
        return

    title = _issue_title(issue_key)
    print(f"  [{issue_key}] processing '{title}'...")

    try:
        sections = process_issue_dir(issue_dir, title)
        result = ProcessedIssue(issue=issue_key, title=title, sections=sections)
        (issue_dir / "processed.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        mark_stage_completed(issue_dir, "process")
        print(f"  [{issue_key}] process complete")
    except Exception as e:
        mark_stage_failed(issue_dir, "process", str(e))
        print(f"  [{issue_key}] process FAILED: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Process Gramophone issues with LLM")
    parser.add_argument("--issue", help="Process specific issue (YYYY-MM)")
    parser.add_argument("--force", action="store_true", help="Re-run even if completed")
    args = parser.parse_args()

    if args.issue:
        process_issue(args.issue, force=args.force)
    else:
        issue_dirs = sorted(DATA_DIR.glob("????-??"), reverse=True)
        for issue_dir in issue_dirs:
            process_issue(issue_dir.name, force=args.force)


if __name__ == "__main__":
    main()
