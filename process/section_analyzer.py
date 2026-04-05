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
