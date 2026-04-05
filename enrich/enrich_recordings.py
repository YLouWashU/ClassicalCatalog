#!/usr/bin/env python3
"""
CLI: enrich processed.json with Spotify links -> enriched.json.

Usage:
    python enrich/enrich_recordings.py
    python enrich/enrich_recordings.py --issue 2021-11
    python enrich/enrich_recordings.py --force
"""
import argparse
import sys
from pathlib import Path

from common.config import DATA_DIR
from common.models import ProcessedIssue
from common.status import is_stage_completed, mark_stage_completed, mark_stage_failed
from enrich.spotify_auth import get_spotify_client
from enrich.spotify_search import enrich_recording


def enrich_issue(issue_key: str, force: bool = False) -> None:
    issue_dir = DATA_DIR / issue_key
    processed_path = issue_dir / "processed.json"

    if not processed_path.exists():
        print(f"  [{issue_key}] processed.json not found, run process first", file=sys.stderr)
        return

    if is_stage_completed(issue_dir, "enrich") and not force:
        print(f"  [{issue_key}] enrich already completed, skipping")
        return

    print(f"  [{issue_key}] enriching with Spotify...")

    try:
        sp = get_spotify_client()
        issue = ProcessedIssue.model_validate_json(processed_path.read_text())

        # Enrich all recordings in review sections
        for section_key in [
            "recording_of_the_month", "editors_choice", "orchestral",
            "chamber", "instrumental", "vocal", "opera", "reissues"
        ]:
            recordings = getattr(issue.sections, section_key, [])
            for rec in recordings:
                print(f"    - {rec.composer}: {rec.work}")
                enrich_recording(rec, sp=sp)

        # Enrich feature recordings
        for feature in issue.sections.features:
            for rec in feature.recordings:
                print(f"    - [feature] {rec.composer}: {rec.work}")
                enrich_recording(rec, sp=sp)

        (issue_dir / "enriched.json").write_text(
            issue.model_dump_json(indent=2), encoding="utf-8"
        )
        mark_stage_completed(issue_dir, "enrich")
        print(f"  [{issue_key}] enrich complete")

    except Exception as e:
        mark_stage_failed(issue_dir, "enrich", str(e))
        print(f"  [{issue_key}] enrich FAILED: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Enrich recordings with Spotify links")
    parser.add_argument("--issue", help="Enrich specific issue (YYYY-MM)")
    parser.add_argument("--force", action="store_true", help="Re-run even if completed")
    args = parser.parse_args()

    if args.issue:
        enrich_issue(args.issue, force=args.force)
    else:
        issue_dirs = sorted(DATA_DIR.glob("????-??"), reverse=True)
        for issue_dir in issue_dirs:
            enrich_issue(issue_dir.name, force=args.force)


if __name__ == "__main__":
    main()
