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
