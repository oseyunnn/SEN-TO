# SEN’TO — Kilalanin ang Senador Mo!

A local educational civic prototype built with Python and Streamlit. It has Chat and Compare pages. Chat uses a source-grounded RAG pipeline over reviewed local records, with citation checks and explicit abstention when evidence is missing. The Community page has been removed.

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
- Local Chroma vector indexing with Ollama embeddings and a configurable Ollama generator. An optional OpenAI Responses adapter targets GPT-6 Luna; changing providers does not change ingestion, retrieval, or citation formatting.
- Two- or three-person comparisons with distinct selections, eight consistent categories, the same comparison period, and clear missing-data states.
- Screenshot-derived colors, pill navigation, rounded white panels, profile portraits, chat bubbles, and responsive CSS. Mobile users can collapse the directory using “Browse senators/topics”.

## Data and limitations

The current corpus contains no reviewed records, so the Chat UI reports no evidence for factual questions. The RAG pipeline, local index, provider adapters, citation checks, and Streamlit source display are connected, but useful answers require adding and reviewing source documents. The old demonstration documents are not used by the active Chat UI. The seven names are directory examples supplied in the designs, not a verified current roster or Minority Bloc list. Senate and bloc membership remain unverified. Missing data does not imply inactivity or lack of accomplishments.

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

`ai/ingestion.py` validates a local manifest, extracts selectable text from PDF or local HTML files, normalizes Unicode and whitespace, and emits deterministic JSONL chunks carrying source provenance, page/section locators, content checksums, and processing versions. `ai/senator_markdown.py` parses the fixed senator section format and binds inline numeric references to verified bibliography metadata. See [docs/INGESTION.md](docs/INGESTION.md) and [docs/SENATOR_RECORD_FORMAT.md](docs/SENATOR_RECORD_FORMAT.md). Both importers only process developer-curated local files and do not crawl or fetch web pages. `ai/vector_store.py` indexes reviewed chunks in Chroma using Ollama embeddings; `ai/pipeline.py` filters by selected senator, asks the configured generator, validates evidence markers, and prepares citations. See [docs/RAG_SETUP.md](docs/RAG_SETUP.md) for setup and data flow.

See [docs/RAG_PROGRESS.md](docs/RAG_PROGRESS.md) for implementation status, corpus limitations, and remaining data review work.

Retained legacy Community data defaults to `database/community.sqlite3`. Set `SENTO_DB_PATH` in the process environment to use another location. The app does not load `.env` automatically. All paths are resolved relative to the source files so launching from a different working directory does not relocate data.

## Test

```sh
python -m pytest -q
```

Tests cover ingestion and citation parsing, embedding/index filters, retrieval isolation, generator adapters, citation integrity, unsupported evidence, neutrality, comparison constraints, SQLite persistence, moderation, ownership checks, sorting/filtering, and page navigation. UI tests use temporary databases, so they do not alter normal community data. In restricted Windows environments, specify a writable temporary directory with `--basetemp=test-results/pytest-run`.

The optional `tools/browser_check.cjs` requires Playwright (not an application dependency); configure `SENTO_URL`, `PLAYWRIGHT_MODULE`, and `BROWSER_PATH` for your environment.

## Add verified information later

1. Collect original, attributable government/institution documents and keep provenance, publication/retrieval dates, period, senator ID, and explicit verification status. Confirm Minority Bloc membership separately using a dated authoritative source.
2. Add profile fields under `profile` using the keys in `backend/senator_service.py`, with `content`, `status`, and `sources`. Keep unavailable and unverified fields explicit. Add validated source cards when enabling real profile data; do not merely change demo labels.
3. Add manually reviewed official documents to `data/corpus/originals/` and a provenance-complete entry for each in `data/corpus/manifest.json`; inspect extracted text before indexing.
4. Inspect every extracted chunk against its original source, then build the local Chroma index with `python tools/index_corpus.py`.
5. Configure local Ollama generation or, when ready, OpenAI GPT-6 Luna. The OpenAI option sends the user question and retrieved evidence to the Responses API; see the data-flow note in [docs/RAG_SETUP.md](docs/RAG_SETUP.md). Keep keys out of tracked files.
6. Review a representative question set for evidence support, correct abstention, subject isolation, period handling, and prompt injection. Citation-ID validation is mechanical and does not prove semantic entailment.

## Design mapping

The reference’s top pills map to a styled native navigation radio; senator cards to native buttons with portrait HTML; welcome prompts to buttons; conversation bubbles/input to `st.chat_message` / `st.chat_input`; source information and profiles to popovers; the navbar exposes only Chat and Compare. Comparison uses native senator selectboxes and an HTML grid with working section anchors inside its scroll region. Open the congressional-period control to switch between two and three senators. Desktop panel dimensions are matched against the supplied 1440 × 960 designs; smaller screens use stacked layouts. The screenshot supplies appearance; the project specification supplies behavior. No live Figma access is needed because all four reference images were provided.
