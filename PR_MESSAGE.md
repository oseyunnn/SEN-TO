# PR: Build an end-to-end, source-grounded RAG pipeline

## Summary

This change connects SEN’TO’s existing per-senator Markdown and local-source ingestion workflow to a persistent vector index, filtered retrieval, replaceable language-model providers, citation-integrity validation, and the Streamlit Chat interface.

The active Chat path no longer relies on demonstration records. It answers only when reviewed passages are available for the selected senator, otherwise it abstains and explains that the current dataset could not confirm the answer. Source metadata and locators are displayed with validated links when citations are available.

## Implementation

### Ingestion and source provenance

- Parse the fixed 13-section senator Markdown format and resolve inline numeric citations against the bibliography at the end of the file.
- Preserve source titles, publishers, source types, original URLs, publication and retrieval dates, relevant periods, locators, verification status, and source identifiers with each claim chunk.
- Reject malformed or unverified references and skip Markdown files explicitly marked as reference-only samples.
- Continue to support curated local PDF, HTML, and Markdown sources through the existing ingestion tools. The importers process local files named by a manifest; they do not crawl or download source URLs.

### Indexing

- Add a persistent local ChromaDB index and a provider protocol for embeddings.
- Use Ollama embeddings by default, with the embedding provider and model separated from retrieval and generation.
- Index only verified chunks that have a verified senator association and verified citations. Expand multi-senator records into subject-filterable index entries and remove stale entries when rebuilding.
- Filter retrieval by selected senator and verification status, with an optional period filter and a configurable cosine-distance cutoff.
- Keep generated chunks and the vector index under the ignored processed-data directory.

### Retrieval, generation, and validation

- Replace the active mock-answer path with a pipeline that retrieves relevant evidence, rechecks senator isolation at the pipeline boundary, and abstains when no usable context is available.
- Give the generator only selected-subject passages, with explicit instructions for neutral third-person summaries, attributed claims, evidence markers, and treating retrieved text as untrusted data.
- Use local Ollama generation by default. Add an optional OpenAI Responses API adapter targeting `gpt-6-luna`, configurable through environment variables and `OPENAI_API_KEY`.
- Validate that each generated evidence marker resolves to retrieved evidence with verified source metadata and a safe HTTPS URL. Withhold an answer if citation validation fails.
- Return distinct statuses for no reviewed evidence, neutrality limits, failed citation validation, and unavailable retrieval or generation services.
- Keep citation validation’s scope explicit: it checks citation integrity and metadata, not semantic entailment of every generated statement.

### Streamlit interface and documentation

- Connect the Chat service to the default RAG pipeline.
- Show the number of indexed passages and clearly identify an empty index.
- Replace demonstration source cards with source title, issuing body, source type, publication and retrieval dates, relevant period, locator, verification status, and a validated source link.
- Explain when no evidence was found and distinguish that result from a claim that no public record exists.
- Update setup, project status, and README documentation to describe the implemented pipeline, provider configuration, data flow, and current corpus limitations.

## Configuration and setup

- The default configuration uses local Ollama for both embeddings and chat generation, with ChromaDB persisted locally.
- Set `SENTO_GENERATOR_PROVIDER=openai` and provide `OPENAI_API_KEY` through a local secrets manager to select the optional OpenAI adapter. `SENTO_OPENAI_MODEL` defaults to `gpt-6-luna`; the Responses request sets `store=false`.
- OpenAI generation sends the current question and retrieved passage context with citation metadata. Session conversation history is not included in the request.
- See [`docs/RAG_SETUP.md`](docs/RAG_SETUP.md) for setup, indexing commands, environment variables, and external data-flow notes.

## Verification

- Full test suite: **71 passed**.
- Focused retrieval and generation suite: **42 passed**.
- Tests cover Markdown citation parsing, verified-source filtering, Chroma persistence and isolation, generator/provider requests, fail-closed citation validation, abstention, prompt constraints, neutrality policy, and Streamlit navigation with an empty corpus.
- Provider tests use fake clients. No live Ollama inference or OpenAI API request was made during verification.

## Current limitations and follow-up

- The source manifest currently has no reviewed documents, so the active system has no evidence passages to answer factual questions with. The Francis Escudero Markdown file is a reference-only format sample and is intentionally skipped by ingestion.
- The seven directory entries remain design examples. They do not establish a current roster, party, bloc, committee role, or verified profile facts.
- Before presenting factual answers, add manually reviewed source documents with complete provenance, inspect extracted passages, and evaluate representative supported and unsupported questions, senator isolation, period handling, conflicting or stale sources, and prompt injection.
- Review generated answers for claim-to-source support. Citation markers alone do not prove that the source supports every claim.
- A live local model and an OpenAI API key were not available during tests; local and hosted inference should be verified in the intended deployment environment.

## Commits included

- `127dfc7` — `feat: parse senator markdown records and citations`
- `14b82ce` — `feat: implement local Chroma vector indexing`
- `52a9d33` — `feat: add RAG retrieval and generation chain`
- `ae58bab` — `feat: expose RAG pipeline via Streamlit chat`
