# Senator Markdown records

`data/senator_records/` contains the curated research profiles used by SEN’TO’s senator-record importer. These Markdown files are the summary layer; citations point back to the source pages, records, or publications. The importer reads local files only and never fetches bibliography URLs.

## Current researched-profile format

The current files use YAML-style frontmatter with `document_type: senator_profile`, a `full_name`, a `common_name`, optional `aliases`, and profile-level review metadata. The importer maps the names and aliases to one unique ID in `data/senators.json`. It does not use `document_id` as the app’s subject ID.

Sections use numbered level-two headings, such as `## 01_Biography` and `## 03_Current_Position`. Claims begin with a stable claim ID and carry their own period, evidence status, and source IDs:

```md
## 01_Biography

- [CLM-BIO-001] A concise claim checked against the listed records.
  Period: Historical
  Context: Any needed limitation or qualification.
  Evidence_Status: VERIFIED
  Sources: [SRC-001, SRC-002]
```

The final `## References` section defines each `SRC-*` entry and its provenance:

```md
## References

- [SRC-001] Exact source title — Issuing body, 2026-07-27.
  URL: https://example.gov.ph/path/to/record
  Retrieved: 2026-11-25
  Locator: p. 14, roll-call table
```

The source title and issuing body are preserved as written. A full ISO publication date is extracted when present; otherwise the original date wording is retained and `publication_date` remains unavailable. `Access` and `Access_Note` fields are also preserved. URLs must be HTTPS to qualify for indexing; the importer does not verify a page by making a network request.

Only a claim explicitly labeled `Evidence_Status: VERIFIED` with resolved source IDs and complete, safe provenance becomes `verification_status: verified`. Other statuses such as `CORROBORATED`, `REPORTED`, `ALLEGED`, `DISPUTED`, or `UNVERIFIED` remain in the JSONL as `candidate_source`; Chroma excludes those chunks. A missing or malformed bibliography entry also keeps the affected claim out of the index while allowing other claims to be processed. Profile-level `verification_status: PARTIAL` and `verification_note` are retained on every chunk; they do not promote claims to verified.

The importer preserves the claim ID, section, period, context, evidence status, source metadata, and source-file checksum. Research-limitations sections are not treated as factual claim chunks. Retrieved claim text remains untrusted reference data, not instructions.

## Legacy format

The importer continues to accept the earlier format with `senator_id`, the fixed 13 headings (`## Biography`, `## Political_History`, and so on), inline numeric citations such as `[1]`, and one-line bibliography entries with explicit provenance fields. Files marked `record_status: reference_sample` or `ingestion_status: do_not_ingest_as_complete_profile` are skipped.

## Ingest

```sh
python tools/ingest_senator_records.py
```

The command writes `data/corpus/processed/senator_chunks.jsonl`. The separate `python tools/ingest_documents.py` flow continues to process reviewed original PDFs, HTML, and Markdown source documents from the corpus manifest.
