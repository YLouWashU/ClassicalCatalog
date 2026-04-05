from pathlib import Path
from common.config import DATA_DIR
from common.models import ProcessedIssue


def _load_issue(issue_key: str) -> ProcessedIssue | None:
    issue_dir = DATA_DIR / issue_key
    for filename in ("enriched.json", "processed.json"):
        path = issue_dir / filename
        if path.exists():
            return ProcessedIssue.model_validate_json(path.read_text())
    return None


def build_index_context(lang: str) -> dict:
    """Return context dict for the index template."""
    issues = []
    for issue_dir in sorted(DATA_DIR.glob("????-??"), reverse=True):
        issue = _load_issue(issue_dir.name)
        if issue is None:
            continue
        total_recordings = sum([
            len(issue.sections.recording_of_the_month),
            len(issue.sections.editors_choice),
            len(issue.sections.orchestral),
            len(issue.sections.chamber),
            len(issue.sections.instrumental),
            len(issue.sections.vocal),
            len(issue.sections.opera),
            len(issue.sections.reissues),
            sum(len(f.recordings) for f in issue.sections.features),
        ])
        issues.append({
            "key": issue_dir.name,
            "title": issue.title,
            "total_recordings": total_recordings,
            "url": f"issues/{issue_dir.name}/index.html",
        })
    return {"issues": issues, "lang": lang}


def build_issue_context(issue_key: str, lang: str) -> dict | None:
    """Return context dict for the issue template."""
    issue = _load_issue(issue_key)
    if issue is None:
        return None

    def text(bilingual) -> str:
        if hasattr(bilingual, "en"):
            return getattr(bilingual, lang, bilingual.en)
        return str(bilingual)

    def rec_dict(rec) -> dict:
        return {
            "composer": rec.composer,
            "work": rec.work,
            "performers": rec.performers,
            "label": rec.label,
            "catalog": rec.catalog,
            "badge": rec.badge,
            "tldr": text(rec.tldr),
            "spotify_url": rec.spotify_url,
            "spotify_status": rec.spotify_status,
            "comparison_recordings": [
                {
                    "composer": c.composer,
                    "work": c.work,
                    "performers": c.performers,
                    "label": c.label,
                    "spotify_url": c.spotify_url,
                    "spotify_status": c.spotify_status,
                }
                for c in rec.comparison_recordings
            ],
        }

    sections = []
    section_map = [
        ("recording_of_the_month", {"en": "Recording of the Month", "zh": "月度最佳录音"}),
        ("editors_choice", {"en": "Editor's Choice", "zh": "编辑精选"}),
        ("orchestral", {"en": "Orchestral", "zh": "管弦乐"}),
        ("chamber", {"en": "Chamber", "zh": "室内乐"}),
        ("instrumental", {"en": "Instrumental", "zh": "器乐"}),
        ("vocal", {"en": "Vocal", "zh": "声乐"}),
        ("opera", {"en": "Opera", "zh": "歌剧"}),
        ("reissues", {"en": "Reissues & Archive", "zh": "再版与档案"}),
    ]
    for key, label_dict in section_map:
        recordings = getattr(issue.sections, key, [])
        if recordings:
            sections.append({
                "key": key,
                "label": label_dict.get(lang, label_dict["en"]),
                "recordings": [rec_dict(r) for r in recordings],
            })

    features = []
    for feat in issue.sections.features:
        features.append({
            "title": feat.feature_title,
            "summary": text(feat.summary),
            "recordings": [rec_dict(r) for r in feat.recordings],
        })

    return {
        "issue_key": issue_key,
        "title": issue.title,
        "sections": sections,
        "features": features,
        "lang": lang,
        "other_lang": "zh" if lang == "en" else "en",
        "other_lang_label": "中文" if lang == "en" else "English",
    }
