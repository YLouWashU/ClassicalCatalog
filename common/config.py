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

LLM_MODEL = os.environ.get("LLM_MODEL", "minimax/MiniMax-M2.7")

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

# Feature extraction rules
FEATURE_ALWAYS_SKIP = {"for the record", "sounds of america"}
FEATURE_STOP_AFTER = "icons"   # stop processing features after this title (inclusive)
FEATURE_MAX_COUNT = 5
FEATURE_MAX_RECORDINGS = 3
