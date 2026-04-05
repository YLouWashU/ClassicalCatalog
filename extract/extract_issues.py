#!/usr/bin/env python3
"""
CLI: extract raw text from Gramophone issues on Zinio.

Usage:
    python extract/extract_issues.py               # all unprocessed issues
    python extract/extract_issues.py --issue 2021-11
    python extract/extract_issues.py --force
"""
import argparse
import sys
from pathlib import Path

from common.config import DATA_DIR, REVIEW_SECTIONS, REVIEW_SECTION_LABELS
from common.status import is_stage_completed, mark_stage_completed, mark_stage_failed
from extract.browser_session import BrowserSession
from extract.zinio_library import list_all_issues
from extract.zinio_reader import (
    extract_section_text, extract_feature_text, get_feature_list, slugify
)


def extract_issue(issue_id: str, issue_key: str, force: bool = False) -> None:
    issue_dir = DATA_DIR / issue_key
    issue_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = issue_dir / "raw"

    if is_stage_completed(issue_dir, "extract") and not force:
        print(f"  [{issue_key}] extract already completed, skipping")
        return

    print(f"  [{issue_key}] extracting review sections...")
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "features").mkdir(exist_ok=True)

    try:
        # Extract review sections
        for section_key in REVIEW_SECTIONS:
            labels = REVIEW_SECTION_LABELS.get(section_key, [section_key])
            print(f"    - {section_key}")
            try:
                text = extract_section_text(issue_id, section_key, labels)
                (raw_dir / f"{section_key}.txt").write_text(text, encoding="utf-8")
            except ValueError as e:
                print(f"      WARNING: {e}")

        # Extract feature sections
        print(f"  [{issue_key}] extracting features...")
        features = get_feature_list(issue_id)
        for feature in features:
            slug = slugify(feature["title"])
            print(f"    - {feature['title']}")
            text = extract_feature_text(issue_id, feature["article_num"])
            (raw_dir / "features" / f"{slug}.txt").write_text(text, encoding="utf-8")

        mark_stage_completed(issue_dir, "extract")
        print(f"  [{issue_key}] extract complete")

    except Exception as e:
        mark_stage_failed(issue_dir, "extract", str(e))
        print(f"  [{issue_key}] extract FAILED: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Extract Gramophone issues from Zinio")
    parser.add_argument("--issue", help="Process specific issue (YYYY-MM)")
    parser.add_argument("--issue-id", dest="issue_id", help="Zinio issue ID (bypasses library enumeration)")
    parser.add_argument("--force", action="store_true", help="Re-run even if completed")
    args = parser.parse_args()

    with BrowserSession():
        if args.issue and args.issue_id:
            # Fast path: issue_id provided directly
            extract_issue(args.issue_id, args.issue, force=args.force)
        elif args.issue:
            # Single issue — find its issue_id from the library
            issues = list_all_issues()
            match = next((i for i in issues if i.issue_key == args.issue), None)
            if not match:
                print(f"Issue {args.issue} not found in Zinio library", file=sys.stderr)
                sys.exit(1)
            extract_issue(match.issue_id, match.issue_key, force=args.force)
        else:
            issues = list_all_issues()
            print(f"Found {len(issues)} issues in library")
            for issue in issues:
                extract_issue(issue.issue_id, issue.issue_key, force=args.force)


if __name__ == "__main__":
    main()
