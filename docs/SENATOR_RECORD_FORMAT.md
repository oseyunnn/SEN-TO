# Senator Markdown record format

SEN’TO keeps one curated Markdown file per senator under `data/senator_records/`. The file is a reviewed, searchable summary layer. The cited PDFs, web pages, or other source files remain the evidence archive; the Markdown summary does not replace them.

## Required layout

Start with frontmatter containing a stable directory ID:

```md
---
senator_id: stable-senator-id
---
```

Use these section headings exactly once and in this order:

```md
## Biography
## Political_History
## Current_Position.
## Legislative_Authorship.
## Voting_Records
## Policy_Standpoints
## Laws_and_Accomplishments
## Public_Service
## Graft_and_Corruption
## Controversies
## Public_Statements
## Financial_Disclosures
## Historical_Performance
## References
```

Each factual paragraph or bullet group needs an inline numbered reference, such as `[1]`. If a section has not been reviewed, use a plain coverage marker such as `Not researched in the current dataset.` The importer omits these markers and does not treat them as evidence that no record exists.

## Reference entries

Number references per file. Keep one reference on one line and include the source details the importer needs:

```md
[1] Exact title — Issuing body | source_type=official_record | publication_date=2026-07-27 | retrieved_at=2026-11-25 | relevant_period=20th Congress, First Regular Session | locator=p. 14 | verification_status=verified | url=https://senate.gov.ph/path/to/record.pdf
```

Use `publication_date=not_stated` when the source does not provide a publication date. Allowed `source_type` values are `official_record`, `government_publication`, `secondary_news`, `research_organization`, and `other`. Describe secondary sources as secondary; never label them official. Only `verification_status=verified` entries can be indexed. The URL must be HTTPS. The importer does not visit URLs.

Example claim:

```md
## Voting_Records

- **Recorded vote:** The journal records the senator voting Yes on the cited measure [1].
- **Relevant period:** 20th Congress, First Regular Session.
- **Record locator:** Journal entry and roll-call table.
```

The bibliography is parsed into each matching claim chunk, not indexed as free-standing evidence. A claim without an inline reference, an undefined reference number, or an unverified reference stops ingestion.

## Ingest

```sh
python tools/ingest_senator_records.py
```

The command writes `data/corpus/processed/senator_chunks.jsonl`. Generated chunks are derived data and are ignored by Git. The separate `python tools/ingest_documents.py` flow continues to ingest reviewed original PDFs, HTML, and Markdown source documents from the corpus manifest.

Reference-only examples must set `record_status: reference_sample` or `ingestion_status: do_not_ingest_as_complete_profile`; the importer skips those files. Do not put sample content into production answers.
