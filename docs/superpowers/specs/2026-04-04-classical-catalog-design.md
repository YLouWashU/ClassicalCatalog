# ClassicalCatalog — Stage 1 Design

**Date:** 2026-04-04
**Scope:** Personal tool for extracting and presenting recommended recordings from Gramophone magazine (Zinio subscription), with Spotify links. Stage 2 (public catalog) is out of scope but considered in structural decisions.

---

## 1. Goal

Automatically process each monthly issue of Gramophone magazine and produce a browsable static website listing:
- Recommended recordings per section with TLDRs
- Comparison recordings mentioned in reviews
- Spotify links where available
- Feature article summaries (2-3 paragraphs) with their recording recommendations

---

## 2. Architecture

Modular pipeline with JSON as the intermediate data store. Each stage is independently re-runnable. Output is a static site hosted on GitHub Pages.

```
pipeline.py (chains all stages)
  │
  ├── extract/    → ~/Data/ClassicalCatalog/GrammophoneIssues/<YYYY-MM>/raw/
  ├── process/    → .../processed.json
  ├── enrich/     → .../enriched.json
  └── publish/    → ~/Code/ClassicalCatalog/docs/
```

**Tech stack:**
- Python 3
- `chromium-browser` via CDP (port 9222) for Zinio extraction
- LiteLLM for LLM calls (model-swappable: Claude, GPT-4, Ollama, etc.)
- Spotipy for Spotify Web API
- Jinja2 for HTML templating
- GitHub Pages for hosting (push manually)

**Bilingual support:** The site is published in both English (`docs/en/`) and Chinese (`docs/zh/`). All LLM-generated text (TLDRs, feature summaries) is produced in both languages in a single LLM call, with the response structured as `{"en": "...", "zh": "..."}` for each text field. UI strings in templates are translated separately per language.

**Zinio auth:** Chromium profile saved to `~/Data/ClassicalCatalog/ZinioBrowser/` — log in once, reused on all subsequent runs.

---

## 3. Project Structure

```
ClassicalCatalog/
├── pipeline.py                      # chains all stages; main entrypoint
│
├── extract/
│   ├── extract_issues.py            # CLI: run extraction
│   ├── zinio_library.py             # enumerate & paginate issues from library
│   ├── zinio_reader.py              # navigate reader, extract section text
│   └── browser_session.py           # chromium profile & CDP session management
│
├── process/
│   ├── process_reviews.py           # CLI: run processing
│   ├── section_analyzer.py          # per-section LLM calls via LiteLLM
│   ├── recommendation_filter.py     # pick highlights, enforce <50% cap
│   └── tldr_writer.py               # generate TLDRs & extract comparison recordings
│
├── enrich/
│   ├── enrich_recordings.py         # CLI: run enrichment
│   ├── spotify_search.py            # search Spotify for each recording
│   └── spotify_auth.py              # OAuth token management
│
├── publish/
│   ├── build_site.py                # CLI: render & write HTML
│   ├── site_structure.py            # assemble index + per-issue page data
│   └── html_renderer.py             # Jinja2 template rendering
│
├── templates/
│   ├── en/
│   │   ├── index.html.j2            # all-issues overview (English)
│   │   └── issue.html.j2            # per-issue recordings page (English)
│   └── zh/
│       ├── index.html.j2            # all-issues overview (Chinese)
│       └── issue.html.j2            # per-issue recordings page (Chinese)
│
├── docs/                            # GitHub Pages output
└── requirements.txt
```

---

## 4. CLI Usage

```bash
python pipeline.py                         # full pipeline, all unprocessed issues
python pipeline.py --issue 2021-11         # specific issue only
python pipeline.py --step extract          # run only extraction
python pipeline.py --step process          # run only processing
python pipeline.py --step enrich           # run only enrichment
python pipeline.py --step publish          # regenerate HTML only
python pipeline.py --issue 2021-11 --force # re-run even if already completed
```

Individual stage CLIs (`extract/extract_issues.py`, etc.) accept the same flags.

---

## 5. Sections Extracted

### Review Sections (always included)
- Recording of the Month
- Editor's Choice
- Orchestral
- Chamber
- Instrumental
- Vocal
- Opera
- Reissues & Archive

### Feature Sections (from printed TOC)
Read the printed TOC page from the magazine (not the Zinio sidebar). Features are listed in a dedicated column separate from Reviews.

**Rules:**
1. Stop after "Icons" — skip everything after it (What Next, Gramophone Focus, High Fidelity, etc.)
2. Always skip: "For the Record", geographic/supplement sections (e.g. "Sounds of America")
3. Skip any section about contemporary music (post ~1960 avant-garde, new commissions)
4. Take up to 5 qualifying sections
5. Max 3 recommendations per Feature section

---

## 6. Recommendation Filtering

**Review sections:** AI picks only clearly recommended recordings — positive language, no significant caveats. Cap at fewer than 50% of recordings reviewed in the section.

**Feature sections:** AI picks up to 3 recordings explicitly recommended or discussed as exemplary. No percentage cap.

**Comparison recordings:** Always included alongside the primary recommended recording, even if the comparison is not independently "recommended."

---

## 7. Data Models

### Local Storage Layout
```
~/Data/ClassicalCatalog/GrammophoneIssues/
└── 2021-11/
    ├── raw/
    │   ├── recording_of_the_month.txt
    │   ├── editors_choice.txt
    │   ├── orchestral.txt
    │   ├── chamber.txt
    │   ├── instrumental.txt
    │   ├── vocal.txt
    │   ├── opera.txt
    │   ├── reissues.txt
    │   └── features/
    │       ├── influencing_netrebko.txt
    │       ├── appreciating_florence_price.txt
    │       ├── the_musician_and_the_score.txt
    │       └── icons.txt
    ├── processed.json
    ├── enriched.json
    └── status.json
```

### processed.json
```json
{
  "issue": "2021-11",
  "title": "Gramophone November 2021",
  "sections": {
    "recording_of_the_month": [
      {
        "composer": "Florence Price",
        "work": "Symphonies Nos 1 & 3",
        "performers": "Philadelphia Orchestra / Yannick Nézet-Séguin",
        "label": "Deutsche Grammophon",
        "catalog": "...",
        "badge": "recording_of_the_month",
        "tldr": {"en": "A landmark release ...", "zh": "这是一张里程碑式的唱片..."},
        "comparison_recordings": [
          {
            "composer": "Florence Price",
            "work": "Symphony No 1",
            "performers": "Fort Smith Symphony / John Jeter",
            "label": "Naxos"
          }
        ]
      }
    ],
    "orchestral": [ ... ],
    "features": [
      {
        "feature_title": "Appreciating Florence Price",
        "summary": {"en": "2-3 paragraph summary ...", "zh": "2-3段中文摘要..."},
        "recordings": [
          {
            "composer": "Florence Price",
            "work": "Symphony No 1",
            "performers": "...",
            "label": "...",
            "tldr": "..."
          }
        ]
      }
    ]
  }
}
```

### enriched.json
Identical to `processed.json` but each recording (including comparison recordings and feature recordings) gains:
```json
{
  "spotify_url": "https://open.spotify.com/album/...",
  "spotify_status": "found"
}
```
or:
```json
{
  "spotify_url": null,
  "spotify_status": "not_found"
}
```

### status.json
```json
{
  "issue": "2021-11",
  "stages": {
    "extract": "completed",
    "process": "completed",
    "enrich": "failed",
    "publish": "pending"
  },
  "errors": {
    "enrich": "Spotify API rate limit at 14:32"
  }
}
```

---

## 8. Pipeline Flow

### Stage 1 — Extraction
1. Launch chromium-browser with saved Zinio profile
2. Navigate to Zinio library, paginate through all pages, build list of all issues
3. Skip issues where `raw/` already exists (unless `--force`)
4. For each issue:
   a. Open the printed TOC page, extract Features list
   b. For each target section (reviews + qualifying features), navigate and `get text body`
   c. Save to `raw/<section>.txt`

### Stage 2 — Processing
One LiteLLM call per section:
- **Review sections:** extract recommended recordings, generate TLDRs, extract comparison recordings
- **Feature sections:** generate 2-3 paragraph summary, extract up to 3 recommended recordings with TLDRs
- Enforce <50% cap on review sections
- Save to `processed.json`

### Stage 3 — Enrichment
For each recording in `processed.json` (primary + comparisons + feature recordings):
- Search Spotify using composer + work + performer
- Classical music matching is non-trivial — search logic will be iterated on
- Save results to `enriched.json`
- Site can be published before enrichment is complete — missing Spotify links render as "not on Spotify"

### Stage 4 — Site Build
Reads all available `enriched.json` (falls back to `processed.json` if enrich not yet run). Runs two render passes — one per language:
- `docs/en/index.html` and `docs/zh/index.html` — all issues, newest first
- `docs/en/issues/<YYYY-MM>/index.html` and `docs/zh/issues/<YYYY-MM>/index.html` — per-issue pages

Each render pass uses the language-specific templates and selects the appropriate `en` or `zh` value from bilingual text fields.

---

## 9. Error Handling

- Each stage checks `status.json` before running — skips completed stages
- A failed stage does not block subsequent stages (enrich failure → publish still runs with missing Spotify data)
- `--force` flag re-runs a stage regardless of status
- Errors logged to `status.json` with timestamp

---

## 10. Testing

- **Extraction:** Saved raw `.txt` fixtures from November 2021 used to test processor without hitting Zinio
- **Processing:** Unit tests for `recommendation_filter.py` (<50% cap) and `tldr_writer.py` (output schema validation)
- **Enrichment:** Direct Spotify API tests — no mocks. Search logic expected to require iteration.
- **Site build:** Snapshot tests — render from known `enriched.json`, compare HTML output

---

## 11. GitHub Pages Deployment

Output goes to `~/Code/ClassicalCatalog/docs/`. Push manually after running the pipeline:

```bash
cd ~/Code/ClassicalCatalog
git add docs/
git commit -m "Add/update issues YYYY-MM"
git push
```

---

## 12. Stage 2 Considerations

Stage 2 (public classical music catalog) is out of scope for this implementation but the design accommodates it:
- JSON data structure is designed to be database-ready (normalised recording + issue references)
- Each recording has enough metadata to support filtering by composer, performer, piece
- The site structure (per-issue pages) naturally extends to per-composer and per-piece pages
- Migrating from JSON to SQLite or Postgres requires only changes to `publish/site_structure.py`
