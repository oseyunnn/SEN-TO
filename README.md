# SEN’TO — Kilalanin ang Senador Mo!

A local educational civic prototype built with Python and Streamlit. It has Chat and Compare pages. The former simulated answer path is disabled; the Chat page clearly reports that source-backed answers are not connected while the curated corpus is being prepared. The Community page has been removed.

## Run locally

Use Python 3.11 or newer. From this project directory:

```sh
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, normally http://localhost:8501. If Windows execution policy blocks activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m streamlit run app.py` directly. If Windows maps `python` to an unavailable Store alias, use `py` or your installed Python executable.

In the provided development environment, `.venv` uses the already installed Streamlit and pytest packages. A clean installation should use the commands above.

## Features

- Searchable reference directory, reusable profiles, configurable suggested questions, and independent chat histories per senator.
- Developer-run ingestion of curated PDF, HTML, Markdown source documents, and sectioned per-senator Markdown records into provenance-preserving chunks. Ingestion does not fetch URLs.
- Two- or three-person comparisons with distinct selections, eight consistent categories, the same comparison period, and clear missing-data states.
- Screenshot-derived colors, pill navigation, rounded white panels, profile portraits, chat bubbles, and responsive CSS. Mobile users can collapse the directory using “Browse senators/topics”.

## Data and limitations

No source-backed answer system is connected yet. No verified documents are currently in the corpus. The old demonstration documents are not used by the active Chat UI.

The seven names are directory examples supplied in the designs, not a verified current roster or Minority Bloc list. The displayed count reflects the actual local directory rather than the design’s illustrative “24”. Senate and Minority Bloc membership remain unverified. All profile and comparison facts are unavailable until records are collected. Missing information does not imply inactivity or a lack of accomplishments.

The existing directory entries remain design examples, not a verified roster. The future assistant should speak about senators in third person and preserve source attribution and uncertainty.

Portraits for the first three profiles are CSS windows into the user-supplied comparison mockup (`assets/images/design-reference.png`); they are not independently sourced official portraits. Remaining profiles have placeholders. Replace these with appropriately licensed individual assets for production. The CSS intentionally follows the supplied design, with native Streamlit forms/expanders where exact reproduction is impractical.

The former Community storage/services are retained as unused backend code; existing SQLite data is preserved. They are not initialized or exposed by the app. Previously, Community identity was guest-only and session-based. Refreshing or opening a new session may reset identity and chat histories; persisted posts and comments remain. Likes are protected against duplicates per session, not per real person. Names are public and unauthenticated. Moderation is a small rule-based filter and can miss harmful text or reject benign wording. Reports are stored locally for manual review; no moderation dashboard or live moderation team is connected. Share links only work against the same app instance/database.

## Architecture

```text
app.py                       application entry point and session defaults
frontend/components/         navigation, directory, profiles, bubbles, sources
frontend/pages/              chat and comparison
frontend/styles/custom.css   reference-based desktop and responsive styling
backend/                     Streamlit-independent domain services and policies
ai/                          source and senator-record ingestion plus RAG interfaces
database/                    SQLite schema, connection, one-time initialization
data/                        JSON directory, guides, styles, suggested questions
tests/                       service, policy, persistence, and Streamlit UI tests
tools/seed_data.py            regenerate bundled JSON demonstration fixtures
```

`ai/ingestion.py` validates a local manifest, extracts selectable text from PDF or local HTML files, normalizes Unicode and whitespace, and emits deterministic JSONL chunks carrying source provenance, page/section locators, content checksums, and processing versions. `ai/senator_markdown.py` parses the fixed senator section format and binds inline reference IDs to verified bibliography metadata. See [docs/INGESTION.md](docs/INGESTION.md) and [docs/SENATOR_RECORD_FORMAT.md](docs/SENATOR_RECORD_FORMAT.md). Both importers only process developer-curated local files and do not crawl or fetch web pages. Query retrieval, embeddings/vector storage, LLM generation, and evidence validation remain future work.

See [docs/RAG_PROGRESS.md](docs/RAG_PROGRESS.md) for a dated summary of completed RAG groundwork and remaining work.

Retained legacy Community data defaults to `database/community.sqlite3`. Set `SENTO_DB_PATH` in the process environment to use another location. The app does not load `.env` automatically. All paths are resolved relative to the source files so launching from a different working directory does not relocate data.

## Test

```sh
python -m pytest -q
```

Tests cover senator selection, topic detection, context isolation, fallbacks, unsupported evidence, fake-link suppression, neutrality, comparison constraints, SQLite persistence, moderation, ownership checks, sorting/filtering, and page navigation with restored state. UI tests use temporary databases, so they do not alter normal community data. In restricted Windows environments, specify a writable temporary directory with `--basetemp=test-results/pytest-run`.

Historical verification before the ingestion work: 45 tests passed on Python 3.14.5 / Streamlit 1.66.1. Those results do not verify the current ingestion code or the Chat UI change. The legacy chatbot tests still describe the retired simulated default and need to be updated when the retrieval phase is built. The optional `tools/browser_check.cjs` requires Playwright (not an application dependency); configure `SENTO_URL`, `PLAYWRIGHT_MODULE`, and `BROWSER_PATH` for your environment.

## Add verified information later

1. Collect original, attributable government/institution documents and keep provenance, publication/retrieval dates, period, senator ID, and explicit verification status. Confirm Minority Bloc membership separately using a dated authoritative source.
2. Add profile fields under `profile` using the keys in `backend/senator_service.py`, with `content`, `status`, and `sources`. Keep unavailable and unverified fields explicit. Add validated source cards when enabling real profile data; do not merely change demo labels.
3. Add manually reviewed official documents to `data/corpus/originals/` and a provenance-complete entry for each in `data/corpus/manifest.json`; inspect extracted text before indexing.
4. Implement retrieval over reviewed chunks. Start with metadata filters and keyword/full-text search; add embeddings/vector storage only if the small corpus demonstrates a need.
5. Implement the `Generator` contract to call an LLM with retrieved context, third-person instructions, neutral presentation, and explicit abstention for insufficient evidence. Inject it with `generator=...`; never place API keys in UI code or tracked files.
6. Replace `MockFactValidator` with evidence-grounded validation, including claim-to-source checks, citation integrity, date/period consistency, and abstention. Validate source URLs before making them clickable. Wire the new pipeline into `ChatbotService` without changing the page interface.
7. Add retrieval, source-backed generation, evidence validation, and focused security tests before enabling answers or deploying publicly.

## Design mapping

The reference’s top pills map to a styled native navigation radio; senator cards to native buttons with portrait HTML; welcome prompts to buttons; conversation bubbles/input to `st.chat_message` / `st.chat_input`; source information and profiles to popovers; the navbar exposes only Chat and Compare. Comparison uses native senator selectboxes and an HTML grid with working section anchors inside its scroll region. Open the congressional-period control to switch between two and three senators. Desktop panel dimensions are matched against the supplied 1440 × 960 designs; smaller screens use stacked layouts. The screenshot supplies appearance; the project specification supplies behavior. No live Figma access is needed because all four reference images were provided.
