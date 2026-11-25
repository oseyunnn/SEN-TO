# SEN’TO RAG progress

**Status as of 25 November 2026**

## Completed groundwork

- Retired the deterministic mock-answer path from the active Chat UI. Chat now clearly says source-backed answers are unavailable and does not present the legacy demonstration guides as evidence.
- Added a local, developer-run ingestion pipeline for manually curated PDF, HTML, and Markdown records. It reads only files named in a manifest; it does not crawl the web or download source URLs.
- Added manifest checks for required provenance, dates, record type, verified status, official HTTPS source hosts, file location and size, and optional pinned checksums.
- Added PDF text extraction and local HTML parsing, text normalization, and deterministic paragraph-aware chunking. Scanned PDFs that have no selectable text are rejected; OCR is not included.
- Preserved provenance on every generated chunk, including source title and issuing body, URL, dates, period, record type, verification status, page or section locator, original-file SHA-256, and processing versions. Chunk text is marked as untrusted source material.
- Added atomic JSONL output at `data/corpus/processed/chunks.jsonl` and documentation describing how to curate, ingest, and manually review records.
- Added a second ingestion path for the fixed 13-section, one-file-per-senator Markdown format. Inline numeric references are resolved against the end bibliography and copied onto each claim chunk; malformed or unverified references stop ingestion. Reference-only sample files are skipped.

## Current state and limits

The original-document manifest contains no records, and the only senator Markdown file is a skipped reference sample, so there are no ingested or reviewed chunks available to answer questions. The ingestion pipeline prepares source text; it is not query-time retrieval. No real retriever, embeddings, vector store, LLM generator, evidence-grounded validator, or citation renderer is connected to Chat. The old mock retrieval and generation modules remain in the repository as legacy code, but the default active Chat path does not use them.

## Implementation plan for the remaining RAG

The intended coverage is the 24 Senate seats of the 20th Congress. This is a research target, not an assumption that the same 24 people occupy those seats for the entire Congress. Verify and date the roster. Keep the initial corpus small: select common record types and one comparable period, then expand after the workflow is reliable. Keep official PDF/HTML records or reviewed Markdown transcriptions with their source manifest; derive searchable chunks from those files.

### 1. Set the coverage and metadata rules

- Maintain a dated roster/evidence register for the 20th Congress; record changes with their effective dates and sources.
- Choose a small shared set of question types, records, and time window for all 24. Start with records available from Senate sources; add other government publishers only for a defined need.
- Treat each document as one source even if it concerns several senators. Add senator IDs only when the connection is verified.
- Keep missing, conflicting, and stale evidence distinguishable. Never treat an empty search as proof that a senator had no activity.

**Ready to proceed when:** the first record types, period, roster snapshot date, and source rules are written down.

### 2. Pilot ingestion and manual review

- Add a few official PDFs/HTML pages or reviewed Markdown transcriptions and complete manifest entries. Use the current importer and inspect every extracted passage against its source, especially names, dates, bill numbers, tables, and vote marks.
- Record extraction failures and decide separately whether scanned documents are out of scope or need a reviewed OCR workflow. Do not index unreviewed OCR output.
- Add focused ingestion tests for manifest validation, path/URL checks, provenance, deterministic chunking, and PDF/HTML/Markdown locators.
- Keep originals, manifest, and generated chunks separate. Generated chunks and indexes should be reproducible and ignored by Git unless the project later decides otherwise.

**Ready to proceed when:** a reviewer can trace each pilot chunk back to a reviewed source file, canonical URL, and exact page or section.

### 3. Implement local query retrieval

- Add a production retriever for the processed JSONL corpus. Start with a small local keyword/full-text index; do not add embeddings or a hosted vector service until measured search quality shows a need.
- Filter by verified senator association and relevant period before ranking. Define how records with no verified senator association can answer institution-level questions without leaking into a senator-specific answer.
- Return chunk IDs plus full provenance and locators. Enforce the same subject/period checks again at the pipeline boundary, including for injected retrievers.
- Return an explicit no-evidence result when no suitable passage is found; never fall back to the retired mock corpus.
- Keep the app’s answer path disabled while this retrieval layer is being built.

**Ready to proceed when:** focused tests show correct results for known queries, no cross-senator or out-of-period leakage, and explicit no-match behavior.

### 4. Add answer generation behind the existing interface

- Implement the `Generator` seam to receive only the question, selected senator, neutral style, and filtered passages.
- Require third-person attribution, source-backed factual claims, and abstention when evidence is inadequate, contradictory, stale, or outside the selected period. Treat passage text as untrusted data, never as instructions.
- Begin with a transparent extractive or otherwise limited generator to validate the interface. Decide on an external LLM only after retrieval works and the project explicitly documents provider, data sent, secrets, cost, and failure behavior.

**Ready to proceed when:** responses cannot introduce unsupported factual details in the reviewed question set and can abstain cleanly.

### 5. Validate evidence and render citations

- Replace the mock validator with checks that every citation refers to a chunk actually retrieved for that response and retains a valid source URL, title, issuing body, locator, dates, period, and verification status.
- Check that responses distinguish a filed bill from an enacted law, authorship from sponsorship, and votes from absence or abstention when the underlying record makes those distinctions.
- Validate URLs before rendering them as links. Show source status and relevant period in the UI.
- Treat semantic claim support as a separate review problem; metadata and citation-ID checks alone do not prove that a passage supports the wording of a claim.

**Ready to proceed when:** invalid, missing, or unrelated citations fail closed and reviewed answers link to the exact supporting passages.

### 6. Evaluate the 24-seat workflow and enable it gradually

- Build a small manually reviewed question set covering supported questions, no-evidence questions, cross-senator isolation, period boundaries, conflicting/stale records, and prompt-injection text in documents.
- Check equal source criteria and comparable coverage across the 24-seat target. Display coverage gaps; do not summarize missing records as inactivity.
- Update Chat only after source ingestion, retrieval, generation, citation validation, and focused checks pass. Show an answer’s evidence and limitations in the interface.
- Track corpus and retrieval updates so users can see when records were last reviewed.

**Completion condition:** the active Chat uses reviewed source chunks end to end, preserves citations and subject/period filters, and abstains transparently when the corpus cannot support an answer.

Until these steps are complete, SEN’TO should not describe itself as providing source-backed RAG answers. Ingestion support exists; the end-to-end retrieval-augmented answer system does not.
