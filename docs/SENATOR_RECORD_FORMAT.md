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

The Chat importer now includes every body section and claim regardless of `Evidence_Status`. It preserves claim and profile statuses as supplied, attaches resolved or unresolved source metadata when available, and records a locator and checksum for each Markdown file. The separate Compare page keeps its existing display rule for `VERIFIED` claims. Retrieved text remains reference data and cannot change the assistant's instructions.

## Legacy format

The importer continues to accept the earlier format with `senator_id`, the fixed 13 headings (`## Biography`, `## Political_History`, and so on), inline numeric citations such as `[1]`, and one-line bibliography entries with explicit provenance fields. Files marked `record_status: reference_sample` or `ingestion_status: do_not_ingest_as_complete_profile` are skipped.

## Ingest

```sh
python tools/ingest_senator_records.py
```

The command writes all Markdown sections to `data/corpus/processed/senator_chunks.jsonl`. The separate original-document manifest flow is not used by Chat and rejects PDF/HTML inputs.
