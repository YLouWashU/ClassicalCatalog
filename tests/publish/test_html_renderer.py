import pytest
from pathlib import Path
from common.models import ProcessedIssue
from publish.html_renderer import render_issue, render_index

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_render_issue_english_contains_composer():
    context = {
        "issue_key": "2021-11",
        "title": "Gramophone November 2021",
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


def test_render_issue_chinese_contains_chinese_label():
    context = {
        "issue_key": "2021-11",
        "title": "Gramophone November 2021",
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
