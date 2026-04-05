#!/usr/bin/env python3
"""
Main pipeline entrypoint — chains extract → process → enrich → publish.

Usage:
    python pipeline.py                          # all unprocessed issues, full pipeline
    python pipeline.py --issue 2021-11          # specific issue
    python pipeline.py --step extract           # single stage
    python pipeline.py --step process
    python pipeline.py --step enrich
    python pipeline.py --step publish
    python pipeline.py --issue 2021-11 --force  # re-run even if completed
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

STEPS = ["extract", "process", "enrich", "publish"]

STEP_COMMANDS = {
    "extract": [sys.executable, "extract/extract_issues.py"],
    "process": [sys.executable, "process/process_reviews.py"],
    "enrich":  [sys.executable, "enrich/enrich_recordings.py"],
    "publish": [sys.executable, "publish/build_site.py"],
}


def run_step(step: str, issue: str | None, force: bool) -> int:
    cmd = STEP_COMMANDS[step]
    if issue:
        cmd = cmd + ["--issue", issue]
    if force and step != "publish":  # publish always re-runs
        cmd = cmd + ["--force"]
    print(f"\n=== {step.upper()} ===")
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="ClassicalCatalog pipeline")
    parser.add_argument("--issue", help="Process specific issue (YYYY-MM)")
    parser.add_argument("--step", choices=STEPS, help="Run only this stage")
    parser.add_argument("--force", action="store_true", help="Re-run even if completed")
    args = parser.parse_args()

    steps_to_run = [args.step] if args.step else STEPS

    for step in steps_to_run:
        rc = run_step(step, args.issue, args.force)
        if rc != 0 and step != "enrich":
            # enrich failure is non-fatal; other failures stop the pipeline
            print(f"\nPipeline stopped: {step} failed (exit code {rc})", file=sys.stderr)
            sys.exit(rc)

    print("\n=== PIPELINE COMPLETE ===")


if __name__ == "__main__":
    main()
