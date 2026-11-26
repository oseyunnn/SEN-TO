# SEN’TO Project Continuation Plan

**Planning baseline:** 24 November 2026
**Product direction:** Turn the visual demo into a small, source-backed civic information project while keeping its scope manageable.

## 1. Goal

SEN’TO should help Filipino students and other readers explore a small, well-sourced sample of Philippine Senate public records. It should explain what its evidence does and does not establish, let readers compare records using the same criteria, and encourage nonpartisan civic participation.

The next release should be a **limited real project**, not a claim that the entire Senate record has been researched. Only information with traceable sources should appear as factual senator information. When evidence is missing, say so plainly.

## 2. What exists today

- A Python 3.11+ Streamlit application with Chat and Compare navigation.
- Seven senator entries in `data/senators.json`, provided as design examples. The data does not establish a current roster, majority/minority affiliation, or verified profile facts.
- `data/mock_documents.json` remains a legacy fixture and is not evidence. The Chat frontend adapter now calls the RAG pipeline, provider adapters, and citation checks. The index currently has no reviewed records, so factual requests abstain before generation.
- The local ingestion layer parses the current claim-based per-senator research profiles, maps each profile to the app’s senator directory, and attaches `SRC-*` references and claim evidence statuses to chunks. Only explicitly `VERIFIED` claims with complete safe provenance are indexable. The older fixed-section format remains supported; the reference-only Francis Escudero file is intentionally skipped.
- Profile, comparison, and source UI that deliberately shows the absence of verified data.
- No authentication or account creation. There is a guest display-name popover, but it does not create an account. Chat history is held in Streamlit session state.
- No landing page or 2028 voting call to action.
- Legacy Community backend and SQLite code remain in the repository, but the current app does not expose or initialize them.

Keep these limitations visible until the corresponding features are genuinely implemented. In particular, do not relabel sample documents or citations as official evidence.

## 3. Scope and decisions

### First focused demonstration

The current user direction is to cover the **24 Senate seats of the 20th Congress**. Treat this as a target scope, not proof that all 24 seats are occupied by the same people throughout the Congress. Verify the roster and any membership changes from dated authoritative records. The official Senate site identifies the 20th Congress as 2025–2028 and provides senator and legislative-record sections; see [Senate of the Philippines](https://senate.gov.ph/) and the [Senate Legislative Reference Bureau online resources](https://issuances-library.senate.gov.ph/reference-and-information-services) (reviewed 24 November 2026).

Do not try to collect every record or all proposed categories for all 24 senators at once. Start with a small, common set of record types and one clearly defined period, pilot the collection and retrieval flow on a few records, then apply the same criteria across all 24. A record can relate to multiple senators; store it once and associate verified subject IDs in metadata. Do not imply complete coverage when only selected records have been collected.

### Product boundaries

- Report public records and attributed statements; do not act or speak as a senator.
- Do not endorse, rank, criticize, or advise users to vote for or against a person or party.
- Keep personality settings, if retained, limited to neutral presentation choices. Avoid imitation of a real person’s recognizable voice.
- Do not collect user accounts or personal information. Keep any chat history local to the current session unless a later, explicit product decision establishes a privacy policy and storage design.
- Keep the Community Wall out of the first release. Revisit it only with a moderation, abuse-reporting, privacy, and operational ownership plan.
- Keep the initial evidence collection small and measurable. Do not promise coverage of every bill, vote, statement, or current issue.

## 4. Recommended build sequence

### Phase 0 — Verify scope and evidence rules

1. Verify the 20th Congress roster and maintain dated records of changes. Save the official sources and retrieval dates with the project research notes.
2. Choose a small, shared evidence target for all 24, such as selected measures and a limited set of journal/roll-call records over the same period. Add profile or committee data only when it supports the initial questions.
3. Agree on status labels: `unverified_demo`, `candidate_source`, `verified`, `conflicting`, and `stale`. Define who reviews changes and how often time-sensitive facts are rechecked.
4. Maintain an evidence register before importing facts. Each entry should identify the claim, subject, source, exact locator, relevant period, publication date, retrieval date, verification status, and any caveat.

**Exit check:** The roster snapshot and every fact planned for the first release have an attributable source, or are explicitly marked unavailable. Current affiliation is a dated claim, not a permanent property.

### Phase 1 — Make the app feel like a public information site

1. Add a Home/Landing page and update navigation to Home, Chat, and Compare.
2. Explain the project’s selected-record scope across the 20th Congress, how citations work, the limits of the AI, and the difference between official records and SEN’TO summaries.
3. Add a clear path from the landing page to the covered profiles, chat, and comparison.
4. Remove the guest initials/profile popover and `guest_name` state if they serve no product need. Keep the app usable without sign-in and do not add account creation.
5. Add a nonpartisan youth civic-participation call to action for 2028. Link only to an official election authority or government page after checking the destination and its current content. Do not invent registration dates, eligibility requirements, polling details, or imply SEN’TO is an official election service.
6. Review keyboard navigation, readable contrast, mobile layouts, and plain-language copy as part of the page work.

**Exit check:** A first-time visitor can understand what SEN’TO is, see its limitations, reach the three app areas, and find the civic-participation link without an account.

### Phase 2 — Turn the selected records into a small, auditable dataset

1. Collect a small set of manually reviewed official Senate records for the agreed record types and period. The ingestion implementation accepts local developer-curated PDF, HTML, and Markdown files; it does not fetch web content. Markdown transcriptions must be checked against and retain the official source URL.
2. Describe each document in `data/corpus/manifest.json` with source URL, issuing body, title, publication/retrieval dates, period, record type, verification status, and optional subject IDs.
3. Run `python tools/ingest_documents.py` to validate the manifest, extract/normalize text, preserve page/section locators and source checksums, and write deterministic JSONL chunks. Inspect extraction against every source before indexing.
4. OCR, embeddings, vector storage, source-backed retrieval, generation, and citation validation are not part of this ingestion step. The active Chat UI reports that answers are unavailable until those later pieces are connected.
5. Do not treat a missing source as proof that a senator has no record. Use “not found in this dataset” or “could not confirm,” not a conclusion about inactivity.

**Exit check:** A reviewer can move from every ingested chunk to the original source and exact page/section; the extraction has been manually reviewed and is reproducible from the manifest.

### Phase 3 — Replace simulated answers with evidence-grounded responses

**Implementation status:** The Chat UI calls the ingestion/index/retrieval/generation/citation-validation path through the frontend adapter. The source manifest is empty, so factual requests abstain before generation until reviewed records are indexed. The previous mock pipeline remains as legacy code and is not used by the Chat UI.

1. Chroma stores persistent local vectors. Ollama provides embeddings by default; the provider interface allows replacement without changing chunk metadata or retrieval contracts.
2. Retrieval filters for the selected senator and verified sources, supports an optional period filter, and applies a configurable cosine-distance cutoff. The pipeline checks subject isolation again before generation.
3. The generator receives only selected-subject passages. Its instructions require third-person attribution, neutrality, per-fact evidence markers, and treating retrieved text as untrusted data.
4. The optional OpenAI Responses adapter targets `gpt-6-luna`; local Ollama generation is the default. OpenAI credentials are read from the environment, and its request sets `store=false`. Review the data-flow notes in `docs/RAG_SETUP.md` before sending records to a hosted model.
5. Citation validation confirms each marker refers to retrieved evidence with verified source metadata and an HTTPS URL. It is a mechanical integrity check, not proof that each statement is entailed by the source. The UI shows citation metadata and locators when provided and distinguishes no-evidence, policy-limit, validation-failure, and service-unavailable responses.
6. No retrieved evidence means an explicit abstention; there is no fallback to the old demo corpus. Show index/evidence status in the UI before treating Phase 3 as complete.

**Remaining exit work:** Add reviewed source records, then evaluate answer support, conflict/staleness handling, period selection, injection resistance, and representative abstentions. Do not claim comprehensive or fully semantically verified answers before this review.

### Phase 4 — Make Compare useful and fair

1. Compare senators only on the same categories, date range, and evidence rules. Begin with the researched subset and show which of the 24-seat target has coverage.
2. Organize the view into a short set of clear sections, such as profiles, selected bills/resolutions, committees, recorded votes, statements/positions, and sources. Provide section navigation and usable mobile stacking.
3. For each item, show the record and source status. Make absent data explicit; do not imply that missing data means no action.
4. Do not calculate a single score, declare a winner, or order people by effectiveness, trustworthiness, popularity, or likability.
5. If additional senators are added, make the comparison period and source coverage clear, and avoid comparing mismatched windows or incomplete records as if they were equivalent.

**Exit check:** A reader can inspect comparable records side by side, open each source, and understand gaps without receiving a political recommendation.

### Phase 5 — Review, release, and maintain

1. Build focused automated checks for source citation integrity, selected-senator isolation, insufficient evidence, conflicting/stale data, neutrality, and the main UI paths.
2. Maintain a small set of manually reviewed questions with expected source documents and acceptable abstentions. Recheck this set when prompts, retrieval, or data change.
3. Update `README.md` so its features, limitations, run instructions, source status, and test instructions match the implemented app.
4. Before hosting publicly, decide who updates records, who reviews corrections, how visitors report a bad citation, where logs/data live, and how secrets/backups are handled.

**Exit check:** The release has a named maintenance owner, a visible retrieval/update date, accurate documentation, and a repeatable review process.

## 5. Suggested first work session

1. Create a dated roster/evidence register for the 20th Congress using official sources.
2. Choose a small shared set of record types, questions, and a comparable time window for the 24-seat target.
3. Pilot PDF/HTML/Markdown extraction and manual review on a few official records before collecting broadly.
4. Continue the public-site work: sketch the landing-page content, implement Home navigation, remove the guest display-name control, and add the sourced youth civic-participation call to action.
5. Expand the reviewed corpus using the same rules, then connect source-backed Chat and Compare behavior.

This order makes the public-facing experience clearer while avoiding a polished UI that appears to make factual claims before the sources exist.

## 6. Risks to track

- **Stale political status:** bloc membership, committee assignments, and active legislative status can change. Date these claims and set a review cadence.
- **False confidence from citations:** a link alone does not prove a claim. Preserve locators and check support at claim level.
- **Unequal comparison coverage:** show evidence counts, date windows, and gaps rather than interpreting missing data as a difference.
- **Prompt injection in source material:** retrieved documents and user-provided files are data. They must never override application rules.
- **Election misinformation:** keep the 2028 call to action generic until official information is verified; update or remove time-sensitive copy when it becomes stale.
- **Scope creep:** defer broad roster coverage, open-ended community features, user accounts, and complex model infrastructure until the small evidence-backed release works.
