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
    performers: str = ""
    label: Optional[str] = None
    spotify_url: Optional[str] = None
    spotify_status: SpotifyStatus = SpotifyStatus.not_checked
    album_image_url: Optional[str] = None


class Recording(BaseModel):
    composer: str
    work: str
    performers: str = ""
    label: Optional[str] = None
    catalog: Optional[str] = None
    badge: Optional[str] = None  # "recording_of_the_month", "editors_choice"
    tldr: BilingualText
    comparison_recordings: list[ComparisonRecording] = []
    spotify_url: Optional[str] = None
    spotify_status: SpotifyStatus = SpotifyStatus.not_checked
    album_image_url: Optional[str] = None


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
