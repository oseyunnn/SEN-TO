# SEN’TO — Kilalanin ang Senador Mo!

A local educational civic prototype built with Python and Streamlit. It has Home, Chat, and Compare pages. Chat now calls the source-grounded RAG pipeline through the frontend adapter. The Compare adapter remains a frontend placeholder. The Community page has been removed.

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

- Landing page, searchable reference directory, reusable profiles, configurable suggested questions, and independent chat histories per senator.
- Developer-run ingestion of curated PDF, HTML, Markdown source documents, and claim-based per-senator research profiles into provenance-preserving chunks. Ingestion does not fetch URLs.
- Local Chroma retrieval, Ollama embeddings, Ollama/OpenAI generator adapters, and citation checks power Chat. The senator research files are ingestion inputs; Chat abstains until eligible claims are processed and indexed.
- Two- or three-person comparisons with distinct selections, eight consistent categories, the same comparison period, and clear missing-data states.
- Screenshot-derived colors, pill navigation, rounded white panels, profile portraits, chat bubbles, and responsive CSS.

## Data and limitations

The active RAG corpus has no newly processed senator chunks indexed yet. The latest ingestion wrote 954 claim chunks from the local research files; 200 have complete provenance and an explicit `VERIFIED` claim status and are eligible for indexing. The remaining chunks retain their source and claim statuses but are not eligible. Chat abstains without retrieved evidence and makes no LLM request. The old demonstration documents are not used by the active Chat UI. The directory contains 24 names listed in the Philippine Senate's official 20th Congress group photo release dated 28 July 2025 ([source](https://legacy.senate.gov.ph/photo_release/2025/0728_13.asp)); this is a dated roster reference, not a live membership check. The first three supplied mockup portraits remain illustrative; the other senators use placeholders. Profile cards and Minority Bloc membership remain unverified. Missing information does not imply inactivity or a lack of accomplishments.

The existing directory entries remain design examples, not a verified roster. The future assistant should speak about senators in third person and preserve source attribution and uncertainty.

Portraits for the first three profiles are CSS windows into the user-supplied comparison mockup (`assets/images/design-reference.png`); they are not independently sourced official portraits. Remaining profiles have placeholders. Replace these with appropriately licensed individual assets for production. The CSS intentionally follows the supplied design, with native Streamlit forms/expanders where exact reproduction is impractical.

The former Community storage/services are retained as unused backend code; existing SQLite data is preserved. They are not initialized or exposed by the app. Previously, Community identity was guest-only and session-based. Refreshing or opening a new session may reset identity and chat histories; persisted posts and comments remain. Likes are protected against duplicates per session, not per real person. Names are public and unauthenticated. Moderation is a small rule-based filter and can miss harmful text or reject benign wording. Reports are stored locally for manual review; no moderation dashboard or live moderation team is connected. Share links only work against the same app instance/database.

## Architecture

```text
app.py                       application entry point and session defaults
frontend/components/         navigation, directory, profiles, bubbles, sources
frontend/pages/              landing, chat, and comparison
frontend/api.py              directory/chat/compare service adapters; Chat invokes the RAG service
frontend/styles/custom.css   reference-based desktop and responsive styling
backend/                     Streamlit-independent domain services and policies
ai/                          source and senator-record ingestion plus RAG interfaces
database/                    SQLite schema, connection, one-time initialization
data/                        JSON directory, guides, styles, suggested questions
tests/                       service, policy, persistence, and Streamlit UI tests
tools/seed_data.py            regenerate bundled JSON demonstration fixtures
```

`ai/ingestion.py` validates a local manifest, extracts selectable text from PDF or local HTML files, normalizes Unicode and whitespace, and emits deterministic JSONL chunks carrying source provenance, page/section locators, content checksums, and processing versions. `ai/senator_markdown.py` parses both the current claim-based senator research profiles and the earlier fixed-section format, preserving claim statuses and linking `SRC-*` references to provenance metadata. Only explicitly verified claims with complete safe provenance are eligible for indexing. See [docs/INGESTION.md](docs/INGESTION.md) and [docs/SENATOR_RECORD_FORMAT.md](docs/SENATOR_RECORD_FORMAT.md). Both importers only process developer-curated local files and do not crawl or fetch web pages. `ai/vector_store.py` indexes reviewed chunks in Chroma using Ollama embeddings; `ai/pipeline.py` filters by selected senator, calls the configured generator, validates evidence markers, and prepares citations. The Chat adapter invokes this pipeline. See [docs/RAG_SETUP.md](docs/RAG_SETUP.md) for setup and data flow, and [docs/SECURITY_ASSESSMENT.md](docs/SECURITY_ASSESSMENT.md) for the security review and limits.

See [docs/RAG_PROGRESS.md](docs/RAG_PROGRESS.md) for implementation status, corpus limitations, and remaining data review work.

Retained legacy Community data defaults to `database/community.sqlite3`. Set `SENTO_DB_PATH` in the process environment to use another location. The app does not load `.env` automatically. All paths are resolved relative to the source files so launching from a different working directory does not relocate data.

## Test

```sh
python -m pytest -q
```

Tests cover ingestion and citation parsing, embedding/index filters, retrieval isolation, generator adapters, citation integrity, English/Tagalog/Taglish prompt handling, Unicode normalization, context and output limits, per-session throttling, unsupported evidence, neutrality, comparison constraints, SQLite persistence, moderation, ownership checks, sorting/filtering, and page navigation. UI tests use temporary databases, so they do not alter normal community data. In restricted Windows environments, specify a writable temporary directory with `--basetemp=test-results/pytest-run`.

The optional `tools/browser_check.cjs` requires Playwright (not an application dependency); configure `SENTO_URL`, `PLAYWRIGHT_MODULE`, and `BROWSER_PATH` for your environment.

## Add verified information later

1. Collect original, attributable government/institution documents and keep provenance, publication/retrieval dates, period, senator ID, and explicit verification status. Confirm Minority Bloc membership separately using a dated authoritative source.
2. Add profile fields under `profile` using the keys in `backend/senator_service.py`, with `content`, `status`, and `sources`. Keep unavailable and unverified fields explicit. Add validated source cards when enabling real profile data; do not merely change demo labels.
3. Add manually reviewed official documents to `data/corpus/originals/` and a provenance-complete entry for each in `data/corpus/manifest.json`; inspect extracted text before indexing.
4. Inspect every extracted chunk against its original source, then build the local Chroma index with `python tools/index_corpus.py`.
5. Configure local Ollama generation or, when ready, OpenAI GPT-6 Luna. The OpenAI option sends the user question and retrieved evidence to the Responses API; see the data-flow note in [docs/RAG_SETUP.md](docs/RAG_SETUP.md). Keep keys out of tracked files.
6. Review a representative question set for evidence support, correct abstention, subject isolation, period handling, and prompt injection. Citation-ID validation is mechanical and does not prove semantic entailment.

## Design mapping

The landing page uses native Streamlit buttons for navigation. Chat and Compare navigation use a styled radio; senator cards use native buttons with portrait HTML; welcome prompts use buttons; the conversation input uses `st.chat_input`; source information and profiles use popovers. The pages use frontend adapter seams in `frontend/api.py` for the directory, Chat, and Compare data. Comparison uses native senator selectboxes and an HTML grid with section anchors. Open the congressional-period control to switch between two and three senators. Smaller screens use stacked layouts. The supplied screenshots guide the appearance; backend and evidence work remain outside this frontend implementation.
