# ClassicalCatalog Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local pipeline that extracts Gramophone magazine reviews from Zinio, processes them with an LLM to produce bilingual (EN/ZH) recommended recording lists with TLDRs, enriches with Spotify links, and publishes a static bilingual site to GitHub Pages.

**Architecture:** Four independent stages (extract → process → enrich → publish) connected by JSON files on disk. Each stage is re-runnable; a failed stage does not block subsequent ones. Status is tracked per-issue in `status.json`.

**Tech Stack:** Python 3.11+, Pydantic v2, LiteLLM (with Minimax as the LLM provider), Spotipy, Jinja2, chromium-browser (CDP via subprocess calls to `agent-browser`), pytest, GitHub Pages.

---

## File Map

```
ClassicalCatalog/
├── .env.example
├── .gitignore
├── requirements.txt
├── pipeline.py
├── common/
│   ├── __init__.py
│   ├── models.py          # Pydantic data models shared across all stages
│   ├── config.py          # paths, env vars, section lists
│   └── status.py          # read/write status.json per issue
├── extract/
│   ├── __init__.py
│   ├── browser_session.py # launch chromium-browser, subprocess wrapper for agent-browser
│   ├── zinio_library.py   # enumerate all Gramophone issues from Zinio library
│   ├── zinio_reader.py    # navigate reader, parse TOC, extract section text
│   └── extract_issues.py  # CLI entrypoint
├── process/
│   ├── __init__.py
│   ├── recommendation_filter.py  # enforce <50% cap on review sections
│   ├── tldr_writer.py            # LiteLLM calls, bilingual output
│   ├── section_analyzer.py       # route review vs feature, call LLM, return structured data
│   └── process_reviews.py        # CLI entrypoint
├── enrich/
│   ├── __init__.py
│   ├── spotify_auth.py    # Spotipy OAuth client
│   ├── spotify_search.py  # search logic for classical recordings
│   └── enrich_recordings.py  # CLI entrypoint
├── publish/
│   ├── __init__.py
│   ├── site_structure.py  # assemble per-issue and index data dicts for templates
│   ├── html_renderer.py   # Jinja2 render pass per language
│   └── build_site.py      # CLI entrypoint
├── templates/
│   ├── en/
│   │   ├── index.html.j2
│   │   └── issue.html.j2
│   └── zh/
│       ├── index.html.j2
│       └── issue.html.j2
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── raw/2021-11/
│   │   │   ├── recording_of_the_month.txt
│   │   │   └── features/the_art_of_fugue.txt
│   │   └── processed_2021-11.json
│   ├── extract/
│   │   ├── __init__.py
│   │   └── test_zinio_reader.py
│   ├── process/
│   │   ├── __init__.py
│   │   ├── test_recommendation_filter.py
│   │   └── test_section_analyzer.py
│   ├── enrich/
│   │   ├── __init__.py
│   │   └── test_spotify_search.py
│   └── publish/
│       ├── __init__.py
│       └── test_html_renderer.py
└── docs/
    ├── en/
    └── zh/
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: all `__init__.py` files and empty directories

- [ ] **Step 1: Write requirements.txt**

```
litellm>=1.0.0
spotipy>=2.23.0
jinja2>=3.1.4
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=7.4.0
```

- [ ] **Step 2: Write .env.example**

```
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_GROUP_ID=your_minimax_group_id
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
LLM_MODEL=minimax/abab6.5s-chat
CDP_PORT=9222
```

- [ ] **Step 3: Write .gitignore**

```
.env
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.venv/
venv/
docs/en/
docs/zh/
```

- [ ] **Step 4: Create directory structure and empty __init__.py files**

```bash
mkdir -p common extract process enrich publish templates/en templates/zh \
  tests/extract tests/process tests/enrich tests/publish \
  tests/fixtures/raw/2021-11/features \
  docs/en docs/zh
touch common/__init__.py extract/__init__.py process/__init__.py \
  enrich/__init__.py publish/__init__.py \
  tests/__init__.py tests/extract/__init__.py tests/process/__init__.py \
  tests/enrich/__init__.py tests/publish/__init__.py
```

- [ ] **Step 5: Create virtualenv and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 6: Copy .env.example to .env and fill in your API keys**

```bash
cp .env.example .env
# Edit .env with your real ANTHROPIC_API_KEY and Spotify credentials
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore common/ extract/ process/ enrich/ publish/ templates/ tests/ docs/
git commit -m "feat: project skeleton and dependencies"
```

---

## Task 2: Data Models

**Files:**
- Create: `common/models.py`

- [ ] **Step 1: Write `common/models.py`**

```python
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class SpotifyStatus(str, Enum):
    found = "found"
    not_found = "not_found"
    not_checked = "not_checked"


class StageStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class BilingualText(BaseModel):
    en: str
    zh: str


class ComparisonRecording(BaseModel):
    composer: str
    work: str
    performers: str
    label: Optional[str] = None
    spotify_url: Optional[str] = None
    spotify_status: SpotifyStatus = SpotifyStatus.not_checked


class Recording(BaseModel):
    composer: str
    work: str
    performers: str
    label: Optional[str] = None
    catalog: Optional[str] = None
    badge: Optional[str] = None  # "recording_of_the_month", "editors_choice"
    tldr: BilingualText
    comparison_recordings: list[ComparisonRecording] = []
    spotify_url: Optional[str] = None
    spotify_status: SpotifyStatus = SpotifyStatus.not_checked


class Feature(BaseModel):
    feature_title: str
    summary: BilingualText
    recordings: list[Recording] = []


class IssueSections(BaseModel):
    recording_of_the_month: list[Recording] = []
    editors_choice: list[Recording] = []
    orchestral: list[Recording] = []
    chamber: list[Recording] = []
    instrumental: list[Recording] = []
    vocal: list[Recording] = []
    opera: list[Recording] = []
    reissues: list[Recording] = []
    features: list[Feature] = []


class ProcessedIssue(BaseModel):
    issue: str        # "2021-11"
    title: str        # "Gramophone November 2021"
    sections: IssueSections = IssueSections()


class IssueStatus(BaseModel):
    issue: str
    stages: dict[str, StageStatus] = {
        "extract": StageStatus.pending,
        "process": StageStatus.pending,
        "enrich": StageStatus.pending,
        "publish": StageStatus.pending,
    }
    errors: dict[str, str] = {}
```

- [ ] **Step 2: Verify models parse correctly**

```bash
python3 -c "
from common.models import ProcessedIssue, Recording, BilingualText, Feature, IssueSections
r = Recording(
    composer='Florence Price',
    work='Symphony No 1',
    performers='Philadelphia Orchestra',
    tldr=BilingualText(en='A landmark release.', zh='里程碑式的唱片。')
)
issue = ProcessedIssue(issue='2021-11', title='Gramophone November 2021')
issue.sections.recording_of_the_month.append(r)
print(issue.model_dump_json(indent=2))
"
```

Expected: valid JSON printed with all fields.

- [ ] **Step 3: Commit**

```bash
git add common/models.py
git commit -m "feat: add Pydantic data models"
```

---

## Task 3: Config and Status

**Files:**
- Create: `common/config.py`
- Create: `common/status.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `common/config.py`**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.environ.get(
    "DATA_DIR", "~/Data/ClassicalCatalog/GrammophoneIssues"
)).expanduser()

BROWSER_PROFILE_DIR = Path(os.environ.get(
    "BROWSER_PROFILE_DIR", "~/Data/ClassicalCatalog/ZinioBrowser"
)).expanduser()

DOCS_DIR = Path(__file__).parent.parent / "docs"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
CHROMIUM_BIN = os.environ.get("CHROMIUM_BIN", "chromium-browser")
ZINIO_LIBRARY_URL = "https://www.zinio.com/gb/my-library"

LLM_MODEL = os.environ.get("LLM_MODEL", "minimax/abab6.5s-chat")

REVIEW_SECTIONS = [
    "recording_of_the_month",
    "editors_choice",
    "orchestral",
    "chamber",
    "instrumental",
    "vocal",
    "opera",
    "reissues",
]

# Feature extraction rules
FEATURE_ALWAYS_SKIP = {"for the record", "sounds of america"}
FEATURE_STOP_AFTER = "icons"   # stop processing features after this title (inclusive)
FEATURE_MAX_COUNT = 5
FEATURE_MAX_RECORDINGS = 3
```

- [ ] **Step 2: Write `common/status.py`**

```python
import json
from datetime import datetime
from pathlib import Path
from common.models import IssueStatus, StageStatus


def _status_path(issue_dir: Path) -> Path:
    return issue_dir / "status.json"


def load_status(issue_dir: Path) -> IssueStatus:
    path = _status_path(issue_dir)
    if path.exists():
        return IssueStatus.model_validate_json(path.read_text())
    issue = issue_dir.name  # directory name is "YYYY-MM"
    return IssueStatus(issue=issue)


def save_status(issue_dir: Path, status: IssueStatus) -> None:
    _status_path(issue_dir).write_text(status.model_dump_json(indent=2))


def mark_stage_completed(issue_dir: Path, stage: str) -> None:
    status = load_status(issue_dir)
    status.stages[stage] = StageStatus.completed
    status.errors.pop(stage, None)
    save_status(issue_dir, status)


def mark_stage_failed(issue_dir: Path, stage: str, error: str) -> None:
    status = load_status(issue_dir)
    status.stages[stage] = StageStatus.failed
    status.errors[stage] = f"{error} at {datetime.now().strftime('%H:%M:%S')}"
    save_status(issue_dir, status)


def is_stage_completed(issue_dir: Path, stage: str) -> bool:
    return load_status(issue_dir).stages.get(stage) == StageStatus.completed
```

- [ ] **Step 3: Write `tests/conftest.py`**

```python
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
```

- [ ] **Step 4: Write test for status**

```python
# tests/test_status.py
import pytest
from pathlib import Path
from common.status import (
    load_status, mark_stage_completed, mark_stage_failed, is_stage_completed
)
from common.models import StageStatus


def test_load_status_returns_default_when_missing(tmp_path):
    (tmp_path / "2021-11").mkdir()
    issue_dir = tmp_path / "2021-11"
    status = load_status(issue_dir)
    assert status.issue == "2021-11"
    assert status.stages["extract"] == StageStatus.pending


def test_mark_stage_completed(tmp_path):
    issue_dir = tmp_path / "2021-11"
    issue_dir.mkdir()
    mark_stage_completed(issue_dir, "extract")
    assert is_stage_completed(issue_dir, "extract")


def test_mark_stage_failed_records_error(tmp_path):
    issue_dir = tmp_path / "2021-11"
    issue_dir.mkdir()
    mark_stage_failed(issue_dir, "enrich", "rate limit")
    status = load_status(issue_dir)
    assert status.stages["enrich"] == StageStatus.failed
    assert "rate limit" in status.errors["enrich"]


def test_failed_stage_cleared_on_complete(tmp_path):
    issue_dir = tmp_path / "2021-11"
    issue_dir.mkdir()
    mark_stage_failed(issue_dir, "enrich", "rate limit")
    mark_stage_completed(issue_dir, "enrich")
    status = load_status(issue_dir)
    assert "enrich" not in status.errors
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_status.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add common/config.py common/status.py tests/test_status.py tests/conftest.py
git commit -m "feat: add config, status tracking, and status tests"
```

---

## Task 4: Browser Session

**Files:**
- Create: `extract/browser_session.py`

This module launches chromium-browser with the saved Zinio profile and exposes a simple function to run `agent-browser` commands via subprocess.

- [ ] **Step 1: Write `extract/browser_session.py`**

```python
import subprocess
import time
import signal
import os
from pathlib import Path
from common.config import CHROMIUM_BIN, BROWSER_PROFILE_DIR, CDP_PORT


def run_agent_browser(*args: str) -> str:
    """Run an agent-browser command against the CDP port. Returns stdout."""
    result = subprocess.run(
        ["agent-browser", "--cdp", str(CDP_PORT)] + list(args),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"agent-browser {' '.join(args)} failed:\n{result.stderr}"
        )
    return result.stdout.strip()


def open_url(url: str) -> None:
    """Navigate to a URL and wait for the page to settle."""
    run_agent_browser("open", url)
    time.sleep(2)


def get_page_text() -> str:
    """Return the full visible text of the current page."""
    return run_agent_browser("get", "text", "body")


def get_current_url() -> str:
    return run_agent_browser("get", "url")


class BrowserSession:
    """Context manager that launches chromium-browser and tears it down on exit."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> "BrowserSession":
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [
                CHROMIUM_BIN,
                f"--user-data-dir={BROWSER_PROFILE_DIR}",
                "--no-sandbox",
                f"--remote-debugging-port={CDP_PORT}",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--disable-infobars",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for Chrome to bind the debug port
        time.sleep(4)
        return self

    def __exit__(self, *_):
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
```

- [ ] **Step 2: Verify the session can launch and connect (manual test)**

```bash
python3 -c "
from extract.browser_session import BrowserSession, open_url, get_current_url
with BrowserSession() as s:
    open_url('https://www.zinio.com')
    print(get_current_url())
"
```

Expected: prints `https://www.zinio.com` (or a redirect URL).

- [ ] **Step 3: Commit**

```bash
git add extract/browser_session.py
git commit -m "feat: add browser session manager for chromium-browser CDP"
```

---

## Task 5: Zinio Library Enumeration

**Files:**
- Create: `extract/zinio_library.py`
- Create: `tests/extract/test_zinio_library.py`

- [ ] **Step 1: Write `extract/zinio_library.py`**

```python
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


def _snapshot_links() -> list[str]:
    """Return all href values from the current page snapshot."""
    output = run_agent_browser("snapshot", "-i", "--json")
    # Extract hrefs from JSON snapshot
    import json
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    hrefs = []
    def walk(node):
        if isinstance(node, dict):
            if href := node.get("href"):
                hrefs.append(href)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(data)
    return hrefs


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
```

- [ ] **Step 2: Write `tests/extract/test_zinio_library.py`**

```python
from extract.zinio_library import _parse_issue_key, _extract_issues_from_page
from unittest.mock import patch


def test_parse_issue_key_standard():
    assert _parse_issue_key("November 2021") == "2021-11"


def test_parse_issue_key_january():
    assert _parse_issue_key("January 2020") == "2020-01"


def test_parse_issue_key_invalid_returns_none():
    assert _parse_issue_key("Awards 2020") is None
    assert _parse_issue_key("") is None


def test_extract_issues_from_page_parses_text():
    sample_text = """
My Library
Gramophone Magazine
August 2022
Gramophone Magazine
July 2022
Awards 2021
Gramophone Magazine
June 2022
"""
    with patch("extract.zinio_library.get_page_text", return_value=sample_text):
        issues = _extract_issues_from_page()
    assert len(issues) == 3
    assert issues[0].issue_key == "2022-08"
    assert issues[1].issue_key == "2022-07"
    assert issues[2].issue_key == "2022-06"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/extract/test_zinio_library.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add extract/zinio_library.py tests/extract/test_zinio_library.py
git commit -m "feat: add Zinio library enumeration with pagination"
```

---

## Task 6: Zinio Reader — TOC Parsing and Section Extraction

**Files:**
- Create: `extract/zinio_reader.py`
- Create: `tests/extract/test_zinio_reader.py`
- Create: `tests/fixtures/raw/2021-11/recording_of_the_month.txt`
- Create: `tests/fixtures/raw/2021-11/features/the_art_of_fugue.txt`

- [ ] **Step 1: Save fixture files from the November 2021 issue**

These are the raw texts already extracted during design. Save to fixture paths.

`tests/fixtures/raw/2021-11/recording_of_the_month.txt`:
```
REVIEWS / RECORDING OF THE MONTH
RECORDING OF THE MONTH
Edward Seckerson welcomes the expert guidance of Yannick Nézet-Séguin and the Philadelphia Orchestra in exploring two symphonies by Florence Price

Florence Price
Symphonies Nos 1 & 3
Philadelphia Orchestra / Yannick Nézet-Séguin
DG 486 3452 (75' • DDD)

Florence Price's First Symphony had its premiere in 1933, performed by the Chicago Symphony Orchestra under Frederick Stock — making Price the first Black woman to have a symphony performed by a major American orchestra. The work lay forgotten for decades, rediscovered partly through the efforts of the Library of Congress and partly through the advocacy of conductors like this one, Yannick Nézet-Séguin.

The symphony is a remarkable piece: lyrical, exuberant, and grounded in African-American folk traditions, with a third movement 'Juba' dance of infectious energy. The Philadelphia strings bring warmth and precision; Nézet-Séguin guides the work with an expert sense of its architecture and an evident affection for the music.

The Third Symphony, less frequently performed, receives here its most complete modern advocacy. Both works reward repeated listening and this disc is an essential addition to any collection.

Compare: Fort Smith Symphony / John Jeter (Naxos) — a valuable but less polished account that nonetheless captures the spirit of the First Symphony well.
```

`tests/fixtures/raw/2021-11/features/the_art_of_fugue.txt`:
```
INSTRUMENTAL REVIEWS GRAMOPHONE FOCUS
THE ART OF FUGUE
Peter Quantrill is full of admiration for two very different approaches to Bach's late masterpiece

JS Bach
'The Art of Life'
JS Bach Die Kunst der Fuge, BWV1080. Solo Violin Partita No 2, BWV1004 – Chaconne (transcr Brahms)...
Daniil Trifonov pf
DG 483 8530 (137' • DDD)

JS Bach
Die Kunst der Fuge, BWV1080
Filippo Gorini pf
Alpha ALPHA755 (97' • DDD)

When we say Bach was a family man... [review text]
```

- [ ] **Step 2: Write `extract/zinio_reader.py`**

```python
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
    # The printed TOC is on the supplement pages (S-prefix in page strip)
    # Navigate to article 4 area where masthead/TOC lives, then scan nearby pages
    results = []
    seen_stop = False

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
```

- [ ] **Step 3: Write `tests/extract/test_zinio_reader.py`**

```python
from extract.zinio_reader import slugify, _parse_issue_key
import pytest


def test_slugify_basic():
    assert slugify("The Art of Fugue") == "the_art_of_fugue"


def test_slugify_special_chars():
    assert slugify("Sheku & Isata Kanneh-Mason") == "sheku_isata_kanneh_mason"


def test_slugify_apostrophe():
    assert slugify("Editor's Choice") == "editor_s_choice"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/extract/test_zinio_reader.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add extract/zinio_reader.py tests/extract/test_zinio_reader.py \
  tests/fixtures/raw/2021-11/recording_of_the_month.txt \
  tests/fixtures/raw/2021-11/features/the_art_of_fugue.txt
git commit -m "feat: add Zinio reader TOC parsing and section extraction"
```

---

## Task 7: Extract CLI

**Files:**
- Create: `extract/extract_issues.py`

- [ ] **Step 1: Write `extract/extract_issues.py`**

```python
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
    parser.add_argument("--force", action="store_true", help="Re-run even if completed")
    args = parser.parse_args()

    with BrowserSession():
        if args.issue:
            # Single issue — we need to find its issue_id from the library
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
```

- [ ] **Step 2: Verify CLI help works**

```bash
python extract/extract_issues.py --help
```

Expected: usage message with `--issue` and `--force` options.

- [ ] **Step 3: Commit**

```bash
git add extract/extract_issues.py
git commit -m "feat: add extract CLI entrypoint"
```

---

## Task 8: Recommendation Filter and TLDR Writer

**Files:**
- Create: `process/recommendation_filter.py`
- Create: `process/tldr_writer.py`
- Create: `tests/process/test_recommendation_filter.py`
- Create: `tests/process/test_section_analyzer.py`

- [ ] **Step 1: Write `process/recommendation_filter.py`**

```python
from common.models import Recording


def apply_review_cap(recordings: list[Recording], total_reviewed: int) -> list[Recording]:
    """
    Enforce the <50% rule: keep fewer than half of all reviewed recordings.
    If the LLM already returned fewer than 50%, pass through unchanged.
    If it returned too many, trim to floor(total_reviewed * 0.49).
    """
    if total_reviewed <= 0:
        return recordings
    max_allowed = max(1, int(total_reviewed * 0.49))
    return recordings[:max_allowed]
```

- [ ] **Step 2: Write `tests/process/test_recommendation_filter.py`**

```python
from process.recommendation_filter import apply_review_cap
from common.models import Recording, BilingualText


def _make_recording(composer: str) -> Recording:
    return Recording(
        composer=composer,
        work="Symphony No 1",
        performers="Some Orchestra",
        tldr=BilingualText(en="Great.", zh="很棒。"),
    )


def test_cap_trims_when_over_50_percent():
    recordings = [_make_recording(f"Composer {i}") for i in range(6)]
    result = apply_review_cap(recordings, total_reviewed=10)
    assert len(result) == 4  # floor(10 * 0.49) = 4


def test_cap_passes_through_when_under_50_percent():
    recordings = [_make_recording(f"Composer {i}") for i in range(3)]
    result = apply_review_cap(recordings, total_reviewed=10)
    assert len(result) == 3


def test_cap_returns_at_least_one():
    recordings = [_make_recording("Bach")]
    result = apply_review_cap(recordings, total_reviewed=1)
    assert len(result) == 1


def test_cap_handles_zero_total():
    recordings = [_make_recording("Bach")]
    result = apply_review_cap(recordings, total_reviewed=0)
    assert len(result) == 1
```

- [ ] **Step 3: Run recommendation filter tests**

```bash
pytest tests/process/test_recommendation_filter.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Write `process/tldr_writer.py`**

```python
import json
import litellm
from common.config import LLM_MODEL
from common.models import Recording, ComparisonRecording, BilingualText, Feature


REVIEW_SECTION_PROMPT = """You are analyzing classical music reviews from Gramophone magazine.

Section: {section_name}
Issue: {issue_title}

Text:
{text}

Task:
1. Count how many distinct recordings are reviewed in this section (total_reviewed).
2. Select only recordings with CLEARLY positive reviews — enthusiastic language, no significant caveats.
3. For each selected recording, extract all fields and write a 2-3 sentence TLDR in both English and Chinese.
4. Extract any comparison recordings mentioned in the review text.

Return ONLY valid JSON, no markdown:
{{
  "total_reviewed": <integer>,
  "recordings": [
    {{
      "composer": "string",
      "work": "string",
      "performers": "string",
      "label": "string or null",
      "catalog": "string or null",
      "tldr": {{"en": "string", "zh": "string"}},
      "comparison_recordings": [
        {{"composer": "string", "work": "string", "performers": "string", "label": "string or null"}}
      ]
    }}
  ]
}}"""


FEATURE_PROMPT = """You are analyzing a feature article from Gramophone magazine.

Feature: {feature_title}
Issue: {issue_title}

Text:
{text}

Task:
1. Determine if this article is about contemporary music (post-1960 avant-garde, new commissions, living composers writing new works). If so, return {{"skip": true}}.
2. Write a 2-3 paragraph summary in both English (200-300 words) and Chinese.
3. Extract up to 3 recordings explicitly recommended or discussed as exemplary.

Return ONLY valid JSON, no markdown:
{{
  "skip": false,
  "summary": {{"en": "string", "zh": "string"}},
  "recordings": [
    {{
      "composer": "string",
      "work": "string",
      "performers": "string",
      "label": "string or null",
      "catalog": "string or null",
      "tldr": {{"en": "string", "zh": "string"}},
      "comparison_recordings": []
    }}
  ]
}}"""


def _call_llm(prompt: str) -> dict:
    response = litellm.completion(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)


def analyze_review_section(
    text: str, section_name: str, issue_title: str
) -> tuple[list[Recording], int]:
    """
    Returns (recordings, total_reviewed).
    Caller is responsible for applying the <50% cap.
    """
    prompt = REVIEW_SECTION_PROMPT.format(
        section_name=section_name,
        issue_title=issue_title,
        text=text,
    )
    data = _call_llm(prompt)
    total_reviewed = data.get("total_reviewed", 0)

    recordings = []
    for r in data.get("recordings", []):
        comparisons = [
            ComparisonRecording(
                composer=c.get("composer", ""),
                work=c.get("work", ""),
                performers=c.get("performers", ""),
                label=c.get("label"),
            )
            for c in r.get("comparison_recordings", [])
        ]
        recordings.append(Recording(
            composer=r.get("composer", ""),
            work=r.get("work", ""),
            performers=r.get("performers", ""),
            label=r.get("label"),
            catalog=r.get("catalog"),
            tldr=BilingualText(**r["tldr"]),
            comparison_recordings=comparisons,
        ))

    return recordings, total_reviewed


def analyze_feature_section(
    text: str, feature_title: str, issue_title: str
) -> Feature | None:
    """
    Returns a Feature, or None if the section should be skipped (contemporary).
    """
    prompt = FEATURE_PROMPT.format(
        feature_title=feature_title,
        issue_title=issue_title,
        text=text,
    )
    data = _call_llm(prompt)

    if data.get("skip"):
        return None

    recordings = []
    for r in data.get("recordings", []):
        recordings.append(Recording(
            composer=r.get("composer", ""),
            work=r.get("work", ""),
            performers=r.get("performers", ""),
            label=r.get("label"),
            catalog=r.get("catalog"),
            tldr=BilingualText(**r["tldr"]),
        ))

    return Feature(
        feature_title=feature_title,
        summary=BilingualText(**data["summary"]),
        recordings=recordings,
    )
```

- [ ] **Step 5: Write `tests/process/test_section_analyzer.py`**

This test calls the real LLM with fixture text. Ensure `ANTHROPIC_API_KEY` is set.

```python
import pytest
from pathlib import Path
from process.tldr_writer import analyze_review_section, analyze_feature_section
from common.models import Recording, Feature

FIXTURES = Path(__file__).parent.parent / "fixtures" / "raw" / "2021-11"


@pytest.mark.integration
def test_analyze_review_section_returns_recordings():
    text = (FIXTURES / "recording_of_the_month.txt").read_text()
    recordings, total = analyze_review_section(
        text=text,
        section_name="Recording of the Month",
        issue_title="Gramophone November 2021",
    )
    assert isinstance(recordings, list)
    assert len(recordings) >= 1
    r = recordings[0]
    assert isinstance(r, Recording)
    assert r.composer  # non-empty
    assert r.tldr.en   # non-empty English TLDR
    assert r.tldr.zh   # non-empty Chinese TLDR


@pytest.mark.integration
def test_analyze_feature_section_returns_feature():
    text = (FIXTURES / "features" / "the_art_of_fugue.txt").read_text()
    feature = analyze_feature_section(
        text=text,
        feature_title="The Art of Fugue",
        issue_title="Gramophone November 2021",
    )
    assert isinstance(feature, Feature)
    assert feature.summary.en
    assert feature.summary.zh
    assert len(feature.recordings) <= 3
```

- [ ] **Step 6: Run unit tests (skip integration)**

```bash
pytest tests/process/test_recommendation_filter.py tests/process/test_section_analyzer.py -v -m "not integration"
```

Expected: 4 tests pass (integration tests skipped).

- [ ] **Step 7: Run integration tests (requires ANTHROPIC_API_KEY)**

```bash
pytest tests/process/test_section_analyzer.py -v -m integration
```

Expected: 2 integration tests pass. Inspect printed recordings for quality.

- [ ] **Step 8: Commit**

```bash
git add process/recommendation_filter.py process/tldr_writer.py \
  tests/process/test_recommendation_filter.py tests/process/test_section_analyzer.py
git commit -m "feat: add recommendation filter and LLM-based TLDR writer"
```

---

## Task 9: Section Analyzer and Process CLI

**Files:**
- Create: `process/section_analyzer.py`
- Create: `process/process_reviews.py`

- [ ] **Step 1: Write `process/section_analyzer.py`**

```python
from pathlib import Path
from common.config import REVIEW_SECTIONS, FEATURE_MAX_RECORDINGS
from common.models import IssueSections, Recording
from process.recommendation_filter import apply_review_cap
from process.tldr_writer import analyze_review_section, analyze_feature_section


def process_issue_dir(issue_dir: Path, issue_title: str) -> IssueSections:
    """
    Read all raw/*.txt files for an issue, call LLM for each, and return IssueSections.
    """
    raw_dir = issue_dir / "raw"
    sections = IssueSections()

    # Process review sections
    for section_key in REVIEW_SECTIONS:
        section_file = raw_dir / f"{section_key}.txt"
        if not section_file.exists():
            print(f"    [{section_key}] raw file missing, skipping")
            continue

        print(f"    [{section_key}] calling LLM...")
        text = section_file.read_text(encoding="utf-8")
        recordings, total_reviewed = analyze_review_section(
            text=text,
            section_name=section_key.replace("_", " ").title(),
            issue_title=issue_title,
        )
        recordings = apply_review_cap(recordings, total_reviewed)

        # Set badge for special sections
        if section_key == "recording_of_the_month":
            for r in recordings:
                r.badge = "recording_of_the_month"
        elif section_key == "editors_choice":
            for r in recordings:
                r.badge = "editors_choice"

        setattr(sections, section_key, recordings)

    # Process feature sections
    features_dir = raw_dir / "features"
    if features_dir.exists():
        for feature_file in sorted(features_dir.glob("*.txt")):
            title = feature_file.stem.replace("_", " ").title()
            print(f"    [feature: {title}] calling LLM...")
            text = feature_file.read_text(encoding="utf-8")
            feature = analyze_feature_section(
                text=text,
                feature_title=title,
                issue_title=issue_title,
            )
            if feature is None:
                print(f"    [feature: {title}] skipped (contemporary)")
                continue
            # Enforce max recordings per feature
            feature.recordings = feature.recordings[:FEATURE_MAX_RECORDINGS]
            sections.features.append(feature)

    return sections
```

- [ ] **Step 2: Write `process/process_reviews.py`**

```python
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
```

- [ ] **Step 3: Verify process CLI help works**

```bash
python process/process_reviews.py --help
```

Expected: usage message with `--issue` and `--force` options.

- [ ] **Step 4: Commit**

```bash
git add process/section_analyzer.py process/process_reviews.py
git commit -m "feat: add section analyzer and process CLI"
```

---

## Task 10: Spotify Auth and Search

**Files:**
- Create: `enrich/spotify_auth.py`
- Create: `enrich/spotify_search.py`
- Create: `tests/enrich/test_spotify_search.py`

- [ ] **Step 1: Write `enrich/spotify_auth.py`**

```python
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

_client: spotipy.Spotify | None = None


def get_spotify_client() -> spotipy.Spotify:
    global _client
    if _client is None:
        auth_manager = SpotifyClientCredentials(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        )
        _client = spotipy.Spotify(auth_manager=auth_manager)
    return _client
```

- [ ] **Step 2: Write `enrich/spotify_search.py`**

Classical music search on Spotify is tricky: the same work has many recordings, performers vary, and Spotify's search is keyword-based. Strategy:
1. Search albums with composer + work keywords
2. Filter results by checking if performer name appears in album/artist name
3. Return album URL (not track URL) — classical music is best consumed as albums

```python
import re
from spotipy import Spotify
from enrich.spotify_auth import get_spotify_client
from common.models import Recording, ComparisonRecording, SpotifyStatus


def _clean_query(text: str) -> str:
    """Remove catalog numbers, parenthetical notes, and excess whitespace."""
    text = re.sub(r"\b[A-Z]{2,}\d[\w\s-]*\b", "", text)   # catalog numbers
    text = re.sub(r"\([^)]*\)", "", text)                   # parentheticals
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_main_performer(performers: str) -> str:
    """Extract the primary performer name (before '/', ',', or 'Orchestra')."""
    # e.g. "Philadelphia Orchestra / Yannick Nézet-Séguin" -> "Nézet-Séguin"
    parts = re.split(r"[/,]", performers)
    # Prefer the conductor name (usually after /)
    if len(parts) > 1:
        return parts[-1].strip()
    return parts[0].strip()


def search_recording(
    composer: str,
    work: str,
    performers: str,
    sp: Spotify | None = None,
) -> tuple[str | None, SpotifyStatus]:
    """
    Search Spotify for a classical recording.
    Returns (album_url, status).
    """
    if sp is None:
        sp = get_spotify_client()

    work_clean = _clean_query(work)
    composer_clean = _clean_query(composer).split()[-1]  # use last name
    performer_clean = _extract_main_performer(performers)
    performer_last = performer_clean.split()[-1]

    # Strategy 1: composer + work + performer
    query = f"{composer_clean} {work_clean} {performer_last}"
    results = sp.search(q=query, type="album", limit=10)
    album = _pick_best_album(results, composer_clean, performer_last)
    if album:
        return album["external_urls"]["spotify"], SpotifyStatus.found

    # Strategy 2: composer + work only (broader)
    query2 = f"{composer_clean} {work_clean}"
    results2 = sp.search(q=query2, type="album", limit=20)
    album2 = _pick_best_album(results2, composer_clean, performer_last)
    if album2:
        return album2["external_urls"]["spotify"], SpotifyStatus.found

    return None, SpotifyStatus.not_found


def _pick_best_album(results: dict, composer_last: str, performer_last: str) -> dict | None:
    """
    Pick the best album from Spotify search results.
    Prefer albums where the artist name contains the performer's last name.
    """
    albums = results.get("albums", {}).get("items", [])
    composer_lower = composer_last.lower()
    performer_lower = performer_last.lower()

    # First pass: exact performer match in artist name
    for album in albums:
        artist_names = " ".join(a["name"].lower() for a in album["artists"])
        if performer_lower in artist_names:
            return album

    # Second pass: any album — return first result
    return albums[0] if albums else None


def enrich_recording(recording: Recording, sp: Spotify | None = None) -> Recording:
    """Add spotify_url and spotify_status to a recording in place."""
    url, status = search_recording(
        composer=recording.composer,
        work=recording.work,
        performers=recording.performers,
        sp=sp,
    )
    recording.spotify_url = url
    recording.spotify_status = status

    for comp in recording.comparison_recordings:
        comp_url, comp_status = search_recording(
            composer=comp.composer,
            work=comp.work,
            performers=comp.performers,
            sp=sp,
        )
        comp.spotify_url = comp_url
        comp.spotify_status = comp_status

    return recording
```

- [ ] **Step 3: Write `tests/enrich/test_spotify_search.py`**

These tests hit the real Spotify API. Ensure `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are set in `.env`.

```python
import pytest
from enrich.spotify_search import search_recording, _extract_main_performer, _clean_query
from common.models import SpotifyStatus


def test_extract_main_performer_with_slash():
    result = _extract_main_performer("Philadelphia Orchestra / Yannick Nézet-Séguin")
    assert result == "Yannick Nézet-Séguin"


def test_extract_main_performer_single():
    result = _extract_main_performer("Daniil Trifonov")
    assert result == "Daniil Trifonov"


def test_clean_query_removes_catalog_numbers():
    result = _clean_query("Die Kunst der Fuge BWV1080 DG 483 8530")
    assert "DG" not in result or "483" not in result


@pytest.mark.integration
def test_search_well_known_recording_finds_result():
    """Beethoven 5th by Karajan — should always be on Spotify."""
    url, status = search_recording(
        composer="Beethoven",
        work="Symphony No 5",
        performers="Berlin Philharmonic / Herbert von Karajan",
    )
    assert status == SpotifyStatus.found
    assert url and "open.spotify.com" in url


@pytest.mark.integration
def test_search_florence_price_symphony():
    url, status = search_recording(
        composer="Florence Price",
        work="Symphony No 1",
        performers="Philadelphia Orchestra / Yannick Nézet-Séguin",
    )
    # May or may not be on Spotify — just verify it returns a valid status
    assert status in (SpotifyStatus.found, SpotifyStatus.not_found)


@pytest.mark.integration
def test_search_nonexistent_returns_not_found():
    url, status = search_recording(
        composer="Xyzzy Composer",
        work="Symphony Zzzz",
        performers="Nobody Orchestra",
    )
    assert status == SpotifyStatus.not_found
    assert url is None
```

- [ ] **Step 4: Run unit tests**

```bash
pytest tests/enrich/test_spotify_search.py -v -m "not integration"
```

Expected: 3 tests pass.

- [ ] **Step 5: Run integration tests**

```bash
pytest tests/enrich/test_spotify_search.py -v -m integration
```

Expected: all 3 integration tests pass. Check the printed URL for `test_search_well_known_recording_finds_result`.

- [ ] **Step 6: Commit**

```bash
git add enrich/spotify_auth.py enrich/spotify_search.py tests/enrich/test_spotify_search.py
git commit -m "feat: add Spotify auth and classical music search"
```

---

## Task 11: Enrich CLI

**Files:**
- Create: `enrich/enrich_recordings.py`

- [ ] **Step 1: Write `enrich/enrich_recordings.py`**

```python
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
```

- [ ] **Step 2: Verify CLI help**

```bash
python enrich/enrich_recordings.py --help
```

Expected: usage message with `--issue` and `--force` options.

- [ ] **Step 3: Commit**

```bash
git add enrich/enrich_recordings.py
git commit -m "feat: add enrich CLI"
```

---

## Task 12: Site Structure and Templates

**Files:**
- Create: `publish/site_structure.py`
- Create: `templates/en/index.html.j2`
- Create: `templates/en/issue.html.j2`
- Create: `templates/zh/index.html.j2`
- Create: `templates/zh/issue.html.j2`
- Create: `tests/fixtures/processed_2021-11.json`

- [ ] **Step 1: Write `publish/site_structure.py`**

```python
from pathlib import Path
from common.config import DATA_DIR
from common.models import ProcessedIssue


def _load_issue(issue_key: str) -> ProcessedIssue | None:
    issue_dir = DATA_DIR / issue_key
    for filename in ("enriched.json", "processed.json"):
        path = issue_dir / filename
        if path.exists():
            return ProcessedIssue.model_validate_json(path.read_text())
    return None


def build_index_context(lang: str) -> dict:
    """Return context dict for the index template."""
    issues = []
    for issue_dir in sorted(DATA_DIR.glob("????-??"), reverse=True):
        issue = _load_issue(issue_dir.name)
        if issue is None:
            continue
        total_recordings = sum([
            len(issue.sections.recording_of_the_month),
            len(issue.sections.editors_choice),
            len(issue.sections.orchestral),
            len(issue.sections.chamber),
            len(issue.sections.instrumental),
            len(issue.sections.vocal),
            len(issue.sections.opera),
            len(issue.sections.reissues),
            sum(len(f.recordings) for f in issue.sections.features),
        ])
        issues.append({
            "key": issue.key if hasattr(issue, "key") else issue_dir.name,
            "title": issue.title,
            "total_recordings": total_recordings,
            "url": f"issues/{issue_dir.name}/index.html",
        })
    return {"issues": issues, "lang": lang}


def build_issue_context(issue_key: str, lang: str) -> dict | None:
    """Return context dict for the issue template."""
    issue = _load_issue(issue_key)
    if issue is None:
        return None

    def text(bilingual) -> str:
        if hasattr(bilingual, "en"):
            return getattr(bilingual, lang, bilingual.en)
        return str(bilingual)

    def rec_dict(rec) -> dict:
        return {
            "composer": rec.composer,
            "work": rec.work,
            "performers": rec.performers,
            "label": rec.label,
            "catalog": rec.catalog,
            "badge": rec.badge,
            "tldr": text(rec.tldr),
            "spotify_url": rec.spotify_url,
            "spotify_status": rec.spotify_status,
            "comparison_recordings": [
                {
                    "composer": c.composer,
                    "work": c.work,
                    "performers": c.performers,
                    "label": c.label,
                    "spotify_url": c.spotify_url,
                    "spotify_status": c.spotify_status,
                }
                for c in rec.comparison_recordings
            ],
        }

    sections = []
    section_map = [
        ("recording_of_the_month", {"en": "Recording of the Month", "zh": "月度最佳录音"}),
        ("editors_choice", {"en": "Editor's Choice", "zh": "编辑精选"}),
        ("orchestral", {"en": "Orchestral", "zh": "管弦乐"}),
        ("chamber", {"en": "Chamber", "zh": "室内乐"}),
        ("instrumental", {"en": "Instrumental", "zh": "器乐"}),
        ("vocal", {"en": "Vocal", "zh": "声乐"}),
        ("opera", {"en": "Opera", "zh": "歌剧"}),
        ("reissues", {"en": "Reissues & Archive", "zh": "再版与档案"}),
    ]
    for key, label_dict in section_map:
        recordings = getattr(issue.sections, key, [])
        if recordings:
            sections.append({
                "key": key,
                "label": label_dict.get(lang, label_dict["en"]),
                "recordings": [rec_dict(r) for r in recordings],
            })

    features = []
    for feat in issue.sections.features:
        features.append({
            "title": feat.feature_title,
            "summary": text(feat.summary),
            "recordings": [rec_dict(r) for r in feat.recordings],
        })

    return {
        "issue_key": issue_key,
        "title": issue.title,
        "sections": sections,
        "features": features,
        "lang": lang,
        "other_lang": "zh" if lang == "en" else "en",
        "other_lang_label": "中文" if lang == "en" else "English",
    }
```

- [ ] **Step 2: Write `templates/en/index.html.j2`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Classical Catalog — Gramophone Recommendations</title>
  <style>
    body { font-family: Georgia, serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #222; }
    h1 { font-size: 1.8rem; border-bottom: 2px solid #8B0000; padding-bottom: 0.5rem; }
    .lang-switch { float: right; font-size: 0.9rem; }
    .lang-switch a { color: #8B0000; }
    .issue-list { list-style: none; padding: 0; }
    .issue-list li { padding: 0.75rem 0; border-bottom: 1px solid #ddd; }
    .issue-list a { color: #8B0000; font-size: 1.1rem; text-decoration: none; }
    .issue-list a:hover { text-decoration: underline; }
    .count { color: #666; font-size: 0.9rem; margin-left: 0.5rem; }
  </style>
</head>
<body>
  <span class="lang-switch"><a href="/zh/index.html">中文</a></span>
  <h1>Gramophone Recommendations</h1>
  <p>Curated recording recommendations from Gramophone magazine, with Spotify links.</p>
  <ul class="issue-list">
    {% for issue in issues %}
    <li>
      <a href="{{ issue.url }}">{{ issue.title }}</a>
      <span class="count">{{ issue.total_recordings }} recordings</span>
    </li>
    {% endfor %}
  </ul>
</body>
</html>
```

- [ ] **Step 3: Write `templates/en/issue.html.j2`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} — Classical Catalog</title>
  <style>
    body { font-family: Georgia, serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #222; }
    h1 { font-size: 1.6rem; border-bottom: 2px solid #8B0000; padding-bottom: 0.5rem; }
    h2 { font-size: 1.2rem; color: #8B0000; margin-top: 2rem; }
    h3 { font-size: 1rem; margin: 1.2rem 0 0.3rem; }
    .badge { display: inline-block; background: #8B0000; color: white; font-size: 0.75rem; padding: 2px 8px; border-radius: 3px; margin-left: 0.5rem; vertical-align: middle; }
    .meta { color: #555; font-size: 0.9rem; margin-bottom: 0.4rem; }
    .tldr { margin: 0.4rem 0 0.6rem; line-height: 1.6; }
    .spotify-link a { color: #1DB954; font-weight: bold; text-decoration: none; }
    .spotify-link a:hover { text-decoration: underline; }
    .spotify-missing { color: #999; font-size: 0.85rem; }
    .comparisons { margin-top: 0.5rem; padding-left: 1rem; border-left: 3px solid #ddd; }
    .comparisons h4 { font-size: 0.9rem; color: #555; margin: 0.3rem 0; }
    .comparison-item { font-size: 0.9rem; margin: 0.2rem 0; }
    .feature { background: #f9f5f0; padding: 1rem 1.2rem; margin: 1.5rem 0; border-left: 4px solid #8B0000; }
    .feature h2 { margin-top: 0; }
    .feature-summary { line-height: 1.7; margin-bottom: 1rem; }
    .lang-switch { float: right; font-size: 0.9rem; }
    .lang-switch a { color: #8B0000; }
    .back { font-size: 0.9rem; margin-bottom: 1rem; }
    .back a { color: #8B0000; }
    .recording { margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #eee; }
  </style>
</head>
<body>
  <span class="lang-switch"><a href="/zh/issues/{{ issue_key }}/index.html">中文</a></span>
  <div class="back"><a href="/en/index.html">← All Issues</a></div>
  <h1>{{ title }}</h1>

  {% for section in sections %}
  <h2>{{ section.label }}</h2>
  {% for rec in section.recordings %}
  <div class="recording">
    <h3>
      {{ rec.composer }} — {{ rec.work }}
      {% if rec.badge == "recording_of_the_month" %}<span class="badge">Recording of the Month</span>{% endif %}
      {% if rec.badge == "editors_choice" %}<span class="badge">Editor's Choice</span>{% endif %}
    </h3>
    <div class="meta">{{ rec.performers }}{% if rec.label %} · {{ rec.label }}{% endif %}{% if rec.catalog %} {{ rec.catalog }}{% endif %}</div>
    <div class="tldr">{{ rec.tldr }}</div>
    <div class="spotify-link">
      {% if rec.spotify_url %}
      <a href="{{ rec.spotify_url }}" target="_blank">▶ Listen on Spotify</a>
      {% else %}
      <span class="spotify-missing">Not on Spotify</span>
      {% endif %}
    </div>
    {% if rec.comparison_recordings %}
    <div class="comparisons">
      <h4>Also consider:</h4>
      {% for comp in rec.comparison_recordings %}
      <div class="comparison-item">
        {{ comp.composer }} — {{ comp.work }} · {{ comp.performers }}{% if comp.label %} ({{ comp.label }}){% endif %}
        {% if comp.spotify_url %} · <a href="{{ comp.spotify_url }}" target="_blank" style="color:#1DB954">Spotify</a>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endfor %}
  {% endfor %}

  {% if features %}
  <h2>Features</h2>
  {% for feat in features %}
  <div class="feature">
    <h2>{{ feat.title }}</h2>
    <div class="feature-summary">{{ feat.summary }}</div>
    {% for rec in feat.recordings %}
    <div class="recording">
      <h3>{{ rec.composer }} — {{ rec.work }}</h3>
      <div class="meta">{{ rec.performers }}{% if rec.label %} · {{ rec.label }}{% endif %}</div>
      <div class="tldr">{{ rec.tldr }}</div>
      <div class="spotify-link">
        {% if rec.spotify_url %}
        <a href="{{ rec.spotify_url }}" target="_blank">▶ Listen on Spotify</a>
        {% else %}
        <span class="spotify-missing">Not on Spotify</span>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
  {% endfor %}
  {% endif %}
</body>
</html>
```

- [ ] **Step 4: Write `templates/zh/index.html.j2`**

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>古典乐目录 — 留声机杂志精选</title>
  <style>
    body { font-family: "Noto Serif SC", Georgia, serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #222; }
    h1 { font-size: 1.8rem; border-bottom: 2px solid #8B0000; padding-bottom: 0.5rem; }
    .lang-switch { float: right; font-size: 0.9rem; }
    .lang-switch a { color: #8B0000; }
    .issue-list { list-style: none; padding: 0; }
    .issue-list li { padding: 0.75rem 0; border-bottom: 1px solid #ddd; }
    .issue-list a { color: #8B0000; font-size: 1.1rem; text-decoration: none; }
    .issue-list a:hover { text-decoration: underline; }
    .count { color: #666; font-size: 0.9rem; margin-left: 0.5rem; }
  </style>
</head>
<body>
  <span class="lang-switch"><a href="/en/index.html">English</a></span>
  <h1>留声机杂志精选录音</h1>
  <p>来自《留声机》杂志的精选录音推荐，附 Spotify 收听链接。</p>
  <ul class="issue-list">
    {% for issue in issues %}
    <li>
      <a href="{{ issue.url }}">{{ issue.title }}</a>
      <span class="count">{{ issue.total_recordings }} 张录音</span>
    </li>
    {% endfor %}
  </ul>
</body>
</html>
```

- [ ] **Step 5: Write `templates/zh/issue.html.j2`**

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} — 古典乐目录</title>
  <style>
    body { font-family: "Noto Serif SC", Georgia, serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #222; }
    h1 { font-size: 1.6rem; border-bottom: 2px solid #8B0000; padding-bottom: 0.5rem; }
    h2 { font-size: 1.2rem; color: #8B0000; margin-top: 2rem; }
    h3 { font-size: 1rem; margin: 1.2rem 0 0.3rem; }
    .badge { display: inline-block; background: #8B0000; color: white; font-size: 0.75rem; padding: 2px 8px; border-radius: 3px; margin-left: 0.5rem; vertical-align: middle; }
    .meta { color: #555; font-size: 0.9rem; margin-bottom: 0.4rem; }
    .tldr { margin: 0.4rem 0 0.6rem; line-height: 1.8; }
    .spotify-link a { color: #1DB954; font-weight: bold; text-decoration: none; }
    .spotify-link a:hover { text-decoration: underline; }
    .spotify-missing { color: #999; font-size: 0.85rem; }
    .comparisons { margin-top: 0.5rem; padding-left: 1rem; border-left: 3px solid #ddd; }
    .comparisons h4 { font-size: 0.9rem; color: #555; margin: 0.3rem 0; }
    .comparison-item { font-size: 0.9rem; margin: 0.2rem 0; }
    .feature { background: #f9f5f0; padding: 1rem 1.2rem; margin: 1.5rem 0; border-left: 4px solid #8B0000; }
    .feature h2 { margin-top: 0; }
    .feature-summary { line-height: 1.9; margin-bottom: 1rem; }
    .lang-switch { float: right; font-size: 0.9rem; }
    .lang-switch a { color: #8B0000; }
    .back { font-size: 0.9rem; margin-bottom: 1rem; }
    .back a { color: #8B0000; }
    .recording { margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #eee; }
  </style>
</head>
<body>
  <span class="lang-switch"><a href="/en/issues/{{ issue_key }}/index.html">English</a></span>
  <div class="back"><a href="/zh/index.html">← 返回所有期刊</a></div>
  <h1>{{ title }}</h1>

  {% for section in sections %}
  <h2>{{ section.label }}</h2>
  {% for rec in section.recordings %}
  <div class="recording">
    <h3>
      {{ rec.composer }} — {{ rec.work }}
      {% if rec.badge == "recording_of_the_month" %}<span class="badge">月度最佳录音</span>{% endif %}
      {% if rec.badge == "editors_choice" %}<span class="badge">编辑精选</span>{% endif %}
    </h3>
    <div class="meta">{{ rec.performers }}{% if rec.label %} · {{ rec.label }}{% endif %}{% if rec.catalog %} {{ rec.catalog }}{% endif %}</div>
    <div class="tldr">{{ rec.tldr }}</div>
    <div class="spotify-link">
      {% if rec.spotify_url %}
      <a href="{{ rec.spotify_url }}" target="_blank">▶ 在 Spotify 收听</a>
      {% else %}
      <span class="spotify-missing">Spotify 上暂无此录音</span>
      {% endif %}
    </div>
    {% if rec.comparison_recordings %}
    <div class="comparisons">
      <h4>可参考：</h4>
      {% for comp in rec.comparison_recordings %}
      <div class="comparison-item">
        {{ comp.composer }} — {{ comp.work }} · {{ comp.performers }}{% if comp.label %} ({{ comp.label }}){% endif %}
        {% if comp.spotify_url %} · <a href="{{ comp.spotify_url }}" target="_blank" style="color:#1DB954">Spotify</a>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endfor %}
  {% endfor %}

  {% if features %}
  <h2>专题文章</h2>
  {% for feat in features %}
  <div class="feature">
    <h2>{{ feat.title }}</h2>
    <div class="feature-summary">{{ feat.summary }}</div>
    {% for rec in feat.recordings %}
    <div class="recording">
      <h3>{{ rec.composer }} — {{ rec.work }}</h3>
      <div class="meta">{{ rec.performers }}{% if rec.label %} · {{ rec.label }}{% endif %}</div>
      <div class="tldr">{{ rec.tldr }}</div>
      <div class="spotify-link">
        {% if rec.spotify_url %}
        <a href="{{ rec.spotify_url }}" target="_blank">▶ 在 Spotify 收听</a>
        {% else %}
        <span class="spotify-missing">Spotify 上暂无此录音</span>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
  {% endfor %}
  {% endif %}
</body>
</html>
```

- [ ] **Step 6: Create fixture processed JSON for snapshot tests**

```bash
cat > tests/fixtures/processed_2021-11.json << 'EOF'
{
  "issue": "2021-11",
  "title": "Gramophone November 2021",
  "sections": {
    "recording_of_the_month": [
      {
        "composer": "Florence Price",
        "work": "Symphonies Nos 1 & 3",
        "performers": "Philadelphia Orchestra / Yannick Nézet-Séguin",
        "label": "Deutsche Grammophon",
        "catalog": "486 3452",
        "badge": "recording_of_the_month",
        "tldr": {
          "en": "A landmark release: Nézet-Séguin and the Philadelphia Orchestra give the most complete and persuasive advocacy yet for Price's neglected symphonies, combining warmth, precision, and evident affection for music long overdue its place in the repertoire.",
          "zh": "这是一张里程碑式的唱片：涅泽-塞甘与费城管弦乐团为普莱斯长期被忽视的交响曲提供了迄今最完整、最有说服力的诠释，将温暖、精准与对这些音乐的深厚情感完美融合。"
        },
        "comparison_recordings": [
          {
            "composer": "Florence Price",
            "work": "Symphony No 1",
            "performers": "Fort Smith Symphony / John Jeter",
            "label": "Naxos",
            "spotify_url": null,
            "spotify_status": "not_checked"
          }
        ],
        "spotify_url": null,
        "spotify_status": "not_checked"
      }
    ],
    "editors_choice": [],
    "orchestral": [],
    "chamber": [],
    "instrumental": [],
    "vocal": [],
    "opera": [],
    "reissues": [],
    "features": [
      {
        "feature_title": "The Art Of Fugue",
        "summary": {
          "en": "Peter Quantrill examines two contrasting approaches to Bach's enigmatic final masterwork. Daniil Trifonov frames the work as a family portrait, weaving in music by Bach's sons and culminating in a liberated, dancing account of the contrapuncti. Filippo Gorini takes a more reverential path, bringing luminous tone and tactile sensitivity to a work he contextualises with fourteen original sonnets.\n\nBoth pianists illuminate different facets of a composition that resists definitive interpretation. Trifonov's completion of the unfinished final fugue is audacious yet humble; Gorini's solemnity occasionally tips into preciousness. Together, these two recordings make a compelling case for the work's inexhaustible richness.",
          "zh": "彼得·坎特里尔考察了两种截然不同的巴赫晚期杰作诠释方式。特里福诺夫将这部作品呈现为一幅家族肖像，融入了巴赫儿子们的音乐，最终以活泼、舞蹈般的方式演绎对位曲群。菲利波·戈里尼则采取更为虔诚的路径，带来发光般的音色和触感细腻的演奏。\n\n两位钢琴家从不同角度照亮了这部抗拒任何定论诠释的作品。特里福诺夫对未完成赋格的补全既大胆又谦逊；戈里尼的庄重感有时略显矜持。两张录音共同展现了这部作品无穷无尽的丰富性。"
        },
        "recordings": [
          {
            "composer": "JS Bach",
            "work": "Die Kunst der Fuge BWV1080",
            "performers": "Daniil Trifonov pf",
            "label": "Deutsche Grammophon",
            "catalog": "483 8530",
            "badge": null,
            "tldr": {
              "en": "Trifonov's imaginative programme frames The Art of Fugue within a Bach family portrait, and his liberated, dancing account of the contrapuncti is among the finest on record.",
              "zh": "特里福诺夫富有想象力的曲目将《赋格的艺术》置于巴赫家族肖像的框架内，他那自由奔放、舞蹈般的对位曲诠释堪称录音史上最佳之一。"
            },
            "comparison_recordings": [],
            "spotify_url": null,
            "spotify_status": "not_checked"
          }
        ]
      }
    ]
  }
}
EOF
```

- [ ] **Step 7: Commit**

```bash
git add publish/site_structure.py templates/ tests/fixtures/processed_2021-11.json
git commit -m "feat: add site structure, bilingual templates, and test fixtures"
```

---

## Task 13: HTML Renderer and Build Site CLI

**Files:**
- Create: `publish/html_renderer.py`
- Create: `publish/build_site.py`
- Create: `tests/publish/test_html_renderer.py`

- [ ] **Step 1: Write test first**

```python
# tests/publish/test_html_renderer.py
import pytest
from pathlib import Path
from unittest.mock import patch
from common.models import ProcessedIssue
from publish.site_structure import build_issue_context, build_index_context
from publish.html_renderer import render_issue, render_index

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def processed_issue():
    return ProcessedIssue.model_validate_json(
        (FIXTURES / "processed_2021-11.json").read_text()
    )


def test_render_issue_english_contains_composer(processed_issue, tmp_path):
    with patch("publish.site_structure.DATA_DIR", FIXTURES / ".."):
        context = {
            "issue_key": "2021-11",
            "title": processed_issue.title,
            "sections": [
                {
                    "key": "recording_of_the_month",
                    "label": "Recording of the Month",
                    "recordings": [
                        {
                            "composer": "Florence Price",
                            "work": "Symphonies Nos 1 & 3",
                            "performers": "Philadelphia Orchestra / Yannick Nézet-Séguin",
                            "label": "Deutsche Grammophon",
                            "catalog": "486 3452",
                            "badge": "recording_of_the_month",
                            "tldr": "A landmark release.",
                            "spotify_url": None,
                            "spotify_status": "not_checked",
                            "comparison_recordings": [],
                        }
                    ],
                }
            ],
            "features": [],
            "lang": "en",
            "other_lang": "zh",
            "other_lang_label": "中文",
        }
    html = render_issue(context, lang="en")
    assert "Florence Price" in html
    assert "Recording of the Month" in html
    assert "Not on Spotify" in html


def test_render_issue_chinese_contains_chinese_label(processed_issue, tmp_path):
    context = {
        "issue_key": "2021-11",
        "title": processed_issue.title,
        "sections": [
            {
                "key": "recording_of_the_month",
                "label": "月度最佳录音",
                "recordings": [
                    {
                        "composer": "Florence Price",
                        "work": "Symphonies Nos 1 & 3",
                        "performers": "Philadelphia Orchestra",
                        "label": None,
                        "catalog": None,
                        "badge": "recording_of_the_month",
                        "tldr": "里程碑式的唱片。",
                        "spotify_url": None,
                        "spotify_status": "not_checked",
                        "comparison_recordings": [],
                    }
                ],
            }
        ],
        "features": [],
        "lang": "zh",
        "other_lang": "en",
        "other_lang_label": "English",
    }
    html = render_issue(context, lang="zh")
    assert "月度最佳录音" in html
    assert "Spotify 上暂无此录音" in html


def test_render_index_lists_issues():
    context = {
        "issues": [
            {"key": "2021-11", "title": "Gramophone November 2021",
             "total_recordings": 5, "url": "issues/2021-11/index.html"},
        ],
        "lang": "en",
    }
    html = render_index(context, lang="en")
    assert "Gramophone November 2021" in html
    assert "5 recordings" in html
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/publish/test_html_renderer.py -v
```

Expected: FAIL — `render_issue` and `render_index` not defined yet.

- [ ] **Step 3: Write `publish/html_renderer.py`**

```python
from jinja2 import Environment, FileSystemLoader
from common.config import TEMPLATES_DIR


def _get_env(lang: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR / lang)),
        autoescape=True,
    )


def render_issue(context: dict, lang: str) -> str:
    env = _get_env(lang)
    template = env.get_template("issue.html.j2")
    return template.render(**context)


def render_index(context: dict, lang: str) -> str:
    env = _get_env(lang)
    template = env.get_template("index.html.j2")
    return template.render(**context)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/publish/test_html_renderer.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Write `publish/build_site.py`**

```python
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
```

- [ ] **Step 6: Run all publish tests**

```bash
pytest tests/publish/ -v
```

Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add publish/html_renderer.py publish/build_site.py tests/publish/test_html_renderer.py
git commit -m "feat: add HTML renderer and build site CLI"
```

---

## Task 14: Pipeline Orchestrator

**Files:**
- Create: `pipeline.py`

- [ ] **Step 1: Write `pipeline.py`**

```python
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
import sys
import subprocess
from pathlib import Path

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
    result = subprocess.run(cmd)
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
```

- [ ] **Step 2: Verify pipeline help**

```bash
python pipeline.py --help
```

Expected: usage message showing `--issue`, `--step`, `--force`.

- [ ] **Step 3: Run all tests to confirm nothing is broken**

```bash
pytest -v -m "not integration"
```

Expected: all unit tests pass.

- [ ] **Step 4: Commit**

```bash
git add pipeline.py
git commit -m "feat: add pipeline orchestrator"
```

---

## Task 15: End-to-End Smoke Test

Run the pipeline against one real issue to verify the full flow works.

- [ ] **Step 1: Ensure Zinio browser session is ready**

Log into Zinio in the saved profile if not already done:

```bash
DISPLAY=:1 chromium-browser \
  --user-data-dir=$HOME/Data/ClassicalCatalog/ZinioBrowser \
  --no-sandbox \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  https://www.zinio.com &
# Log in manually, then close the window
```

- [ ] **Step 2: Run extract on November 2021**

```bash
python pipeline.py --issue 2021-11 --step extract
```

Expected: `~/Data/ClassicalCatalog/GrammophoneIssues/2021-11/raw/` populated with `.txt` files.

Verify:
```bash
ls ~/Data/ClassicalCatalog/GrammophoneIssues/2021-11/raw/
ls ~/Data/ClassicalCatalog/GrammophoneIssues/2021-11/raw/features/
```

- [ ] **Step 3: Run process on November 2021**

```bash
python pipeline.py --issue 2021-11 --step process
```

Expected: `processed.json` created. Inspect it:
```bash
python3 -c "
import json
data = json.load(open('$HOME/Data/ClassicalCatalog/GrammophoneIssues/2021-11/processed.json'))
for section, recs in data['sections'].items():
    if isinstance(recs, list) and recs:
        print(f'{section}: {len(recs)} recordings')
"
```

- [ ] **Step 4: Run enrich on November 2021**

```bash
python pipeline.py --issue 2021-11 --step enrich
```

Expected: `enriched.json` created. Check Spotify links:
```bash
python3 -c "
import json
data = json.load(open('$HOME/Data/ClassicalCatalog/GrammophoneIssues/2021-11/enriched.json'))
rotm = data['sections']['recording_of_the_month']
for r in rotm:
    print(r['composer'], '-', r['work'], ':', r['spotify_status'], r.get('spotify_url',''))
"
```

- [ ] **Step 5: Run publish**

```bash
python pipeline.py --step publish
```

Expected: `docs/en/issues/2021-11/index.html` and `docs/zh/issues/2021-11/index.html` created.

Verify HTML:
```bash
python3 -m http.server 8000 --directory docs/
# Open http://localhost:8000/en/index.html in browser
```

- [ ] **Step 6: Commit if everything looks good**

```bash
git add docs/
git commit -m "feat: initial site build from November 2021 issue"
```

---

## Self-Review

**Spec coverage check:**

| Spec Requirement | Task |
|---|---|
| Automated Zinio extraction via browser | Tasks 4–7 |
| Batch all existing issues | Task 5 (list_all_issues paginates) |
| Raw text saved to `~/Data/ClassicalCatalog/GrammophoneIssues/` | Task 7 |
| Review sections: ROTM, Editor's, Orchestral, Chamber, Instrumental, Vocal, Opera, Reissues | Tasks 6–7 |
| Feature sections from printed TOC, stop after Icons | Task 6 (zinio_reader.py) |
| Skip: For the Record, geographic supplements, contemporary | Task 6 + config |
| <50% cap on review section recommendations | Task 8 |
| Max 3 feature recordings | Task 9 |
| Bilingual TLDRs (EN + ZH) in single LLM call | Task 8 |
| Feature 2-3 paragraph summary bilingual | Task 8 |
| Comparison recordings extracted | Task 8 |
| Spotify search with "not on Spotify" fallback | Tasks 10–11 |
| Site publishable before enrich complete | Task 13 (falls back to processed.json) |
| status.json per issue | Task 3 |
| Failed stage doesn't block subsequent | Tasks 7, 9, 11, 14 |
| --force flag | Tasks 7, 9, 11, 14 |
| GitHub Pages: docs/en/ and docs/zh/ | Tasks 12–13 |
| Language toggle between EN and ZH | Templates (Tasks 12) |
| LiteLLM (model-swappable) | Task 8 |
