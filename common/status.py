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
