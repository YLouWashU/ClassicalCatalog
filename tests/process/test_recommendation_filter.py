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
