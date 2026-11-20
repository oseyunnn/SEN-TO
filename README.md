# SEN’TO — Kilalanin ang Senador Mo!

A local educational civic prototype built with Python and Streamlit. The app has Chat and Compare pages, with the centered two-tab navbar from the latest supplied reference. The Community page has been removed. No API key, external AI service, or paid dependency is required.

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
- Deterministic, topic-aware simulated RAG with senator-isolated context, explicit demo labels, transparent unsupported-question responses, and non-clickable demo references.
- Two- or three-person comparisons with distinct selections, eight consistent categories, the same comparison period, and clear missing-data states.
- Screenshot-derived colors, pill navigation, rounded white panels, profile portraits, chat bubbles, and responsive CSS. Mobile users can collapse the directory using “Browse senators/topics”.

## Data and limitations

This is a simulation, not a trained model or factual Senate research system. **No verified government source is connected.** `DEMO_SUPPORTED` means the answer uses a local demonstration guide; it never means real-world verification. The validator checks template/context inclusion only, not factual truth or semantic entailment.

The seven names are directory examples supplied in the designs, not a verified current roster or Minority Bloc list. The displayed count reflects the actual local directory rather than the design’s illustrative “24”. Senate and Minority Bloc membership remain unverified. All profile and comparison facts are unavailable until records are collected. Missing information does not imply inactivity or a lack of accomplishments.

The local documents contain generic research guidance, not fabricated biographies, bills, quotations, votes, or positions. The assistant speaks about senators in third person. Style configuration affects presentation only and does not claim to imitate anyone’s real personality. Basic English/Filipino keywords are recognized, while demonstration answers are in English.

Portraits for the first three profiles are CSS windows into the user-supplied comparison mockup (`assets/images/design-reference.png`); they are not independently sourced official portraits. Remaining profiles have placeholders. Replace these with appropriately licensed individual assets for production. The CSS intentionally follows the supplied design, with native Streamlit forms/expanders where exact reproduction is impractical.

The former Community storage/services are retained as unused backend code; existing SQLite data is preserved. They are not initialized or exposed by the app. Previously, Community identity was guest-only and session-based. Refreshing or opening a new session may reset identity and chat histories; persisted posts and comments remain. Likes are protected against duplicates per session, not per real person. Names are public and unauthenticated. Moderation is a small rule-based filter and can miss harmful text or reject benign wording. Reports are stored locally for manual review; no moderation dashboard or live moderation team is connected. Share links only work against the same app instance/database.

## Architecture

```text
app.py                       application entry point and session defaults
frontend/components/         navigation, directory, profiles, bubbles, sources
frontend/pages/              chat and comparison
frontend/styles/custom.css   reference-based desktop and responsive styling
backend/                     Streamlit-independent domain services and policies
ai/                          replaceable simulation pipeline components
database/                    SQLite schema, connection, one-time initialization
data/                        JSON directory, guides, styles, suggested questions
tests/                       service, policy, persistence, and Streamlit UI tests
tools/seed_data.py            regenerate bundled JSON demonstration fixtures
```

The pipeline normalizes a query, applies neutrality guards, classifies its topic with whole-word keywords, filters documents by senator and topic, ranks matches by token overlap, selects up to three documents, generates an answer from their content, validates demonstration support, and formats references. Unknown topics yield no context and an explicit fallback. This is lightweight local retrieval, not embeddings or a vector database.

Retained legacy Community data defaults to `database/community.sqlite3`. Set `SENTO_DB_PATH` in the process environment to use another location. The app does not load `.env` automatically. All paths are resolved relative to the source files so launching from a different working directory does not relocate data.

## Test

```sh
python -m pytest -q
```

Tests cover senator selection, topic detection, context isolation, fallbacks, unsupported evidence, fake-link suppression, neutrality, comparison constraints, SQLite persistence, moderation, ownership checks, sorting/filtering, and page navigation with restored state. UI tests use temporary databases, so they do not alter normal community data. In restricted Windows environments, specify a writable temporary directory with `--basetemp=test-results/pytest-run`.

Development verification: 45 tests passed on Python 3.14.5 / Streamlit 1.66.1. Headless Edge checks passed for navigation, suggested questions, post creation, likes, replies, deletion, and desktop/mobile rendering, with no browser errors or mobile horizontal overflow. Screenshots are saved under the ignored `test-results/` directory. The optional `tools/browser_check.cjs` requires Playwright (not an application dependency); configure `SENTO_URL`, `PLAYWRIGHT_MODULE`, and `BROWSER_PATH` for your environment. It checks the two-tab navigation, chat submission, comparison links, and mobile layout without accessing the legacy database.

## Add verified information later

1. Collect original, attributable government/institution documents and keep provenance, publication/retrieval dates, period, senator ID, and explicit verification status. Confirm Minority Bloc membership separately using a dated authoritative source.
2. Add profile fields under `profile` using the keys in `backend/senator_service.py`, with `content`, `status`, and `sources`. Keep unavailable and unverified fields explicit. Add validated source cards when enabling real profile data; do not merely change demo labels.
3. Implement an ingestion process for text extraction and chunking, preserving document IDs and provenance on every chunk. Ingestion is intentionally not implemented in this prototype.
4. Implement the `Retriever` contract in `ai/pipeline.py`. A vector-store adapter should filter by senator and congressional period before similarity search and return compatible context records. Inject it into `RAGPipeline(retriever=...)`.
5. Implement the `Generator` contract to call an LLM with retrieved context, third-person instructions, neutral presentation, and explicit abstention for insufficient evidence. Inject it with `generator=...`; never place API keys in UI code or tracked files.
6. Replace `MockFactValidator` with evidence-grounded validation, including claim-to-source checks, citation integrity, date/period consistency, and abstention. Validate source URLs before making them clickable. Wire the new pipeline into `ChatbotService` without changing the page interface.
7. Keep simulation and verified modes visibly distinct. Update citation rendering, integration tests, and security/moderation before deploying beyond local educational use.

## Design mapping

The reference’s top pills map to a styled native navigation radio; senator cards to native buttons with portrait HTML; welcome prompts to buttons; conversation bubbles/input to `st.chat_message` / `st.chat_input`; source information and profiles to popovers; the navbar exposes only Chat and Compare. Comparison uses native senator selectboxes and an HTML grid with working section anchors inside its scroll region. Open the congressional-period control to switch between two and three senators. Desktop panel dimensions are matched against the supplied 1440 × 960 designs; smaller screens use stacked layouts. The screenshot supplies appearance; the project specification supplies behavior. No live Figma access is needed because all four reference images were provided.
