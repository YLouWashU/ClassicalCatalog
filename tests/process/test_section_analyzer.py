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
