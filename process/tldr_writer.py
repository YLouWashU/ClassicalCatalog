import json
import os
import litellm
from common.config import LLM_MODEL
from common.models import Recording, ComparisonRecording, BilingualText, Feature


REVIEW_SECTION_PROMPT = """You are analyzing classical music reviews from Gramophone magazine.

Section: {section_name}
Issue: {issue_title}

Text:
{text}

Task:
1. Count how many distinct recordings are reviewed in this section (total_reviewed).
2. Select only recordings with CLEARLY positive reviews — enthusiastic language, no significant caveats.
3. For each selected recording, extract all fields and write a 2-3 sentence TLDR in both English and Chinese.
4. Extract any comparison recordings mentioned in the review text.

Return ONLY valid JSON, no markdown:
{{
  "total_reviewed": <integer>,
  "recordings": [
    {{
      "composer": "string",
      "work": "string",
      "performers": "string",
      "label": "string or null",
      "catalog": "string or null",
      "tldr": {{"en": "string", "zh": "string"}},
      "comparison_recordings": [
        {{"composer": "string", "work": "string", "performers": "string", "label": "string or null"}}
      ]
    }}
  ]
}}"""


FEATURE_PROMPT = """You are analyzing a feature article from Gramophone magazine.

Feature: {feature_title}
Issue: {issue_title}

Text:
{text}

Task:
1. Determine if this article is about contemporary music (post-1960 avant-garde, new commissions, living composers writing new works). If so, return {{"skip": true}}.
2. Write a 2-3 paragraph summary in both English (200-300 words) and Chinese.
3. Extract up to 3 recordings explicitly recommended or discussed as exemplary.

Return ONLY valid JSON, no markdown:
{{
  "skip": false,
  "summary": {{"en": "string", "zh": "string"}},
  "recordings": [
    {{
      "composer": "string",
      "work": "string",
      "performers": "string",
      "label": "string or null",
      "catalog": "string or null",
      "tldr": {{"en": "string", "zh": "string"}},
      "comparison_recordings": []
    }}
  ]
}}"""


def _call_llm(prompt: str) -> dict:
    response = litellm.completion(
        model=LLM_MODEL,
        api_base=os.environ.get("MINIMAX_API_BASE"),
        api_key=os.environ.get("MINIMAX_API_KEY"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        timeout=120,
        num_retries=2,
    )
    content = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)


def analyze_review_section(
    text: str, section_name: str, issue_title: str
) -> tuple[list[Recording], int]:
    """
    Returns (recordings, total_reviewed).
    Caller is responsible for applying the <50% cap.
    """
    prompt = REVIEW_SECTION_PROMPT.format(
        section_name=section_name,
        issue_title=issue_title,
        text=text,
    )
    data = _call_llm(prompt)
    total_reviewed = data.get("total_reviewed", 0)

    recordings = []
    for r in data.get("recordings", []):
        comparisons = [
            ComparisonRecording(
                composer=c.get("composer", ""),
                work=c.get("work", ""),
                performers=c.get("performers") or "",
                label=c.get("label"),
            )
            for c in r.get("comparison_recordings", [])
        ]
        recordings.append(Recording(
            composer=r.get("composer", ""),
            work=r.get("work", ""),
            performers=r.get("performers", ""),
            label=r.get("label"),
            catalog=r.get("catalog"),
            tldr=BilingualText(**r["tldr"]),
            comparison_recordings=comparisons,
        ))

    return recordings, total_reviewed


def analyze_feature_section(
    text: str, feature_title: str, issue_title: str
) -> Feature | None:
    """
    Returns a Feature, or None if the section should be skipped (contemporary).
    """
    prompt = FEATURE_PROMPT.format(
        feature_title=feature_title,
        issue_title=issue_title,
        text=text,
    )
    data = _call_llm(prompt)

    if data.get("skip"):
        return None

    recordings = []
    for r in data.get("recordings", []):
        recordings.append(Recording(
            composer=r.get("composer", ""),
            work=r.get("work", ""),
            performers=r.get("performers", ""),
            label=r.get("label"),
            catalog=r.get("catalog"),
            tldr=BilingualText(**r["tldr"]),
        ))

    return Feature(
        feature_title=feature_title,
        summary=BilingualText(**data["summary"]),
        recordings=recordings,
    )
