import re
import time
from dataclasses import dataclass
from extract.browser_session import run_agent_browser, open_url, get_page_text
from common.config import ZINIO_LIBRARY_URL


@dataclass
class ZinioIssue:
    title: str       # "Gramophone Magazine"
    date_label: str  # "November 2021"
    issue_id: str    # "504030" (from reader URL)
    issue_key: str   # "2021-11" (YYYY-MM for file storage)


def _parse_issue_key(date_label: str) -> str | None:
    """Convert 'November 2021' -> '2021-11'."""
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    parts = date_label.strip().split()
    if len(parts) == 2:
        month_name, year = parts
        month_num = months.get(month_name.lower())
        if month_num and year.isdigit():
            return f"{year}-{month_num}"
    return None


def _extract_issues_from_page() -> list[ZinioIssue]:
    """Extract Gramophone issue entries from the current library page text."""
    text = get_page_text()
    issues = []
    # Library page lists issues as: "Gramophone Magazine\n<Month> <Year>"
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if line == "Gramophone Magazine" and i + 1 < len(lines):
            date_label = lines[i + 1]
            issue_key = _parse_issue_key(date_label)
            if issue_key:
                issues.append(ZinioIssue(
                    title="Gramophone Magazine",
                    date_label=date_label,
                    issue_id="",       # filled in by _resolve_issue_ids
                    issue_key=issue_key,
                ))
    return issues


def _resolve_issue_ids(issues: list[ZinioIssue]) -> list[ZinioIssue]:
    """
    Click each issue thumbnail to get its reader URL and extract the issue ID.
    The reader URL pattern is: /reader/readsvg/<issue_id>/Cover
    """
    # We navigate via the library page links; snapshot gives us href attributes
    snapshot_output = run_agent_browser("snapshot", "-i")
    # Find reader links: href="/reader/readsvg/<id>/Cover"
    reader_pattern = re.compile(r"/reader/read(?:svg|html)/(\d+)/")
    found_ids = list(dict.fromkeys(reader_pattern.findall(snapshot_output)))

    # Match by order (library shows newest first, same order as our extracted list)
    for issue, issue_id in zip(issues, found_ids):
        issue.issue_id = issue_id
    return [i for i in issues if i.issue_id]


def list_all_issues() -> list[ZinioIssue]:
    """
    Navigate the Zinio library and return all Gramophone issues, newest first.
    Handles pagination automatically.
    """
    open_url(ZINIO_LIBRARY_URL)
    time.sleep(2)

    all_issues: list[ZinioIssue] = []
    page = 1

    while True:
        page_issues = _extract_issues_from_page()
        page_issues = _resolve_issue_ids(page_issues)
        all_issues.extend(page_issues)

        # Check for next page button
        snapshot = run_agent_browser("snapshot", "-i")
        if "Next page" in snapshot:
            run_agent_browser("find", "text", "Next page", "click")
            time.sleep(2)
            page += 1
        else:
            break

    return all_issues
