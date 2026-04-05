import re
import time
from pathlib import Path
from extract.browser_session import run_agent_browser, open_url, get_page_text, get_current_url
from common.config import FEATURE_ALWAYS_SKIP, FEATURE_STOP_AFTER, FEATURE_MAX_COUNT


# Zinio reader URL patterns
READER_HTML_BASE = "https://www.zinio.com/reader/readhtml/{issue_id}/{article_num}"
READER_SVG_BASE = "https://www.zinio.com/reader/readsvg/{issue_id}/{article_num}"

# Known section name -> TOC label mapping
REVIEW_SECTION_LABELS = {
    "recording_of_the_month": ["RECORDING OF THE MONTH"],
    "editors_choice": ["Editor's choice", "EDITOR'S CHOICE"],
    "orchestral": ["Orchestral", "ORCHESTRAL"],
    "chamber": ["Chamber", "CHAMBER"],
    "instrumental": ["Instrumental", "INSTRUMENTAL"],
    "vocal": ["Vocal", "VOCAL"],
    "opera": ["Opera", "OPERA"],
    "reissues": ["Reissues", "REISSUES", "REISSUES & ARCHIVE"],
}


def _switch_to_text_mode() -> None:
    """Ensure reader is in text mode (not PDF mode)."""
    snapshot = run_agent_browser("snapshot", "-i")
    if "switch to PDF view" not in snapshot:
        # Already in text mode
        return
    # Find the reader view switch and toggle it
    lines = snapshot.splitlines()
    for line in lines:
        if "Reader view switch" in line or "reader view" in line.lower():
            ref = re.search(r"\[ref=(e\d+)\]", line)
            if ref:
                run_agent_browser("click", f"@{ref.group(1)}")
                time.sleep(1)
                return


def _navigate_to_article(issue_id: str, article_num: int) -> None:
    url = READER_HTML_BASE.format(issue_id=issue_id, article_num=article_num)
    open_url(url)
    _switch_to_text_mode()


def _find_section_article_num(issue_id: str, section_labels: list[str]) -> int | None:
    """
    Open the Zinio sidebar TOC and find the article number for a section.
    Returns the article number or None if not found.
    """
    # Open TOC sidebar
    snapshot = run_agent_browser("snapshot", "-i")
    toc_ref = None
    for line in snapshot.splitlines():
        if "Table of contents" in line:
            m = re.search(r"\[ref=(e\d+)\]", line)
            if m:
                toc_ref = m.group(1)
                break

    if not toc_ref:
        return None

    run_agent_browser("click", f"@{toc_ref}")
    time.sleep(1)

    toc_snapshot = run_agent_browser("snapshot", "-i")

    for label in section_labels:
        for line in toc_snapshot.splitlines():
            if label in line and "link" in line:
                m = re.search(r"\[ref=(e\d+)\]", line)
                if m:
                    run_agent_browser("click", f"@{m.group(1)}")
                    time.sleep(2)
                    url = get_current_url()
                    num_match = re.search(r"/readhtml/\d+/(\d+)", url)
                    if num_match:
                        # Close TOC
                        _close_toc()
                        return int(num_match.group(1))

    _close_toc()
    return None


def _close_toc() -> None:
    snapshot = run_agent_browser("snapshot", "-i")
    for line in snapshot.splitlines():
        if "Close" in line and "button" in line:
            m = re.search(r"\[ref=(e\d+)\]", line)
            if m:
                run_agent_browser("click", f"@{m.group(1)}")
                time.sleep(0.5)
                return


def _extract_features_from_toc(issue_id: str) -> list[dict]:
    """
    Parse the printed TOC page to extract the Features column.
    Returns list of dicts: [{"title": str, "article_num": int}]
    """
    results = []

    # Open sidebar TOC to find all Features-labeled articles
    _navigate_to_article(issue_id, 2)
    snapshot = run_agent_browser("snapshot", "-i")

    # Find TOC button
    toc_ref = None
    for line in snapshot.splitlines():
        if "Table of contents" in line:
            m = re.search(r"\[ref=(e\d+)\]", line)
            if m:
                toc_ref = m.group(1)
                break

    if not toc_ref:
        return results

    run_agent_browser("click", f"@{toc_ref}")
    time.sleep(1)

    toc_snapshot = run_agent_browser("snapshot", "-i")

    for line in toc_snapshot.splitlines():
        if "Features" not in line and "In this issue" not in line:
            continue
        if "link" not in line:
            continue

        # Extract title from link text
        title_match = re.search(r'link "(?:Features|In this issue)\s+([^"]+?)\s+Page', line)
        if not title_match:
            continue

        title = title_match.group(1).strip()
        title_lower = title.lower()

        # Skip always-skipped sections
        if any(skip in title_lower for skip in FEATURE_ALWAYS_SKIP):
            continue

        # Navigate to get article number
        ref_match = re.search(r"\[ref=(e\d+)\]", line)
        if not ref_match:
            continue

        run_agent_browser("click", f"@{ref_match.group(1)}")
        time.sleep(2)

        url = get_current_url()
        num_match = re.search(r"/readhtml/\d+/(\d+)", url)
        if num_match:
            results.append({
                "title": title,
                "article_num": int(num_match.group(1)),
            })

        # Re-open TOC for next iteration
        snapshot2 = run_agent_browser("snapshot", "-i")
        if "Table of contents" in snapshot2:
            for l2 in snapshot2.splitlines():
                if "Table of contents" in l2:
                    m2 = re.search(r"\[ref=(e\d+)\]", l2)
                    if m2:
                        run_agent_browser("click", f"@{m2.group(1)}")
                        time.sleep(1)
                        toc_snapshot = run_agent_browser("snapshot", "-i")
                        break

        # Check stop condition
        if title_lower == FEATURE_STOP_AFTER.lower():
            break

        if len(results) >= FEATURE_MAX_COUNT:
            break

    _close_toc()
    return results


def extract_section_text(issue_id: str, section_key: str, labels: list[str]) -> str:
    """Navigate to a review section and return its full text."""
    article_num = _find_section_article_num(issue_id, labels)
    if article_num is None:
        raise ValueError(f"Could not find section '{section_key}' in issue {issue_id}")
    _navigate_to_article(issue_id, article_num)
    return get_page_text()


def extract_feature_text(issue_id: str, article_num: int) -> str:
    """Navigate to a feature article and return its full text."""
    _navigate_to_article(issue_id, article_num)
    return get_page_text()


def get_feature_list(issue_id: str) -> list[dict]:
    """Return qualifying feature sections for this issue."""
    return _extract_features_from_toc(issue_id)


def slugify(title: str) -> str:
    """Convert a feature title to a safe filename."""
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
