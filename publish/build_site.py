#!/usr/bin/env python3
"""
CLI: render enriched/processed data into static HTML site.

Usage:
    python publish/build_site.py
    python publish/build_site.py --issue 2021-11
"""
import argparse
import sys
from pathlib import Path

from common.config import DATA_DIR, DOCS_DIR
from common.status import mark_stage_completed, mark_stage_failed
from publish.site_structure import build_issue_context, build_index_context
from publish.html_renderer import render_issue, render_index

LANGUAGES = ["en", "zh"]


def build_issue_pages(issue_key: str) -> None:
    issue_dir = DATA_DIR / issue_key
    for lang in LANGUAGES:
        context = build_issue_context(issue_key, lang)
        if context is None:
            print(f"  [{issue_key}] no data found, skipping", file=sys.stderr)
            return

        out_dir = DOCS_DIR / lang / "issues" / issue_key
        out_dir.mkdir(parents=True, exist_ok=True)
        html = render_issue(context, lang=lang)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        print(f"  [{issue_key}/{lang}] written to {out_dir}/index.html")

    try:
        mark_stage_completed(issue_dir, "publish")
    except Exception:
        pass  # publish status is best-effort


def build_index_pages() -> None:
    for lang in LANGUAGES:
        context = build_index_context(lang)
        out_path = DOCS_DIR / lang / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = render_index(context, lang=lang)
        out_path.write_text(html, encoding="utf-8")
        print(f"  [index/{lang}] written to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Build static site from processed data")
    parser.add_argument("--issue", help="Build pages for specific issue (YYYY-MM)")
    args = parser.parse_args()

    if args.issue:
        build_issue_pages(args.issue)
    else:
        issue_dirs = sorted(DATA_DIR.glob("????-??"), reverse=True)
        for issue_dir in issue_dirs:
            build_issue_pages(issue_dir.name)

    build_index_pages()
    print("Site build complete.")


if __name__ == "__main__":
    main()
