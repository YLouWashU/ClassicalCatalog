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
