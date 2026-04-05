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
