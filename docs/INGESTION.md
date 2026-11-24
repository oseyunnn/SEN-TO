# SEN’TO document ingestion (first version)

This is a developer-run, local ingestion step for a deliberately small corpus. It does not crawl the web, accept uploads, create embeddings, create a vector database, retrieve passages for chat, or call an LLM. Ingested source passages remain untrusted reference text.

## Where to find records

Start with original records published by the Philippine Senate:

- The Senate Legislative Information System and document pages on [senate.gov.ph](https://senate.gov.ph/) and its official legacy subdomain are the first place to look for bills, resolutions, journals, committee reports, and other legislative records.
- The Senate Legislative Reference Bureau describes its [collections](https://issuances-library.senate.gov.ph/collections) and its [online reference services](https://issuances-library.senate.gov.ph/reference-and-information-services). Its page says electronic copies of journals, bills, and legislative history from the 13th Congress onward are available through the Senate website; some older material may require a request.
- For an enacted statute, use an official Senate record for its legislative history and an official publication such as the [Official Gazette](https://www.officialgazette.gov.ph/) for the law text, when available. Do not treat a filed bill as an enacted law.

For this first corpus, a developer manually selects an official record, saves its PDF or HTML page under `data/corpus/originals/`, reviews the source and exact document identity, and records its canonical HTTPS URL and dates in `manifest.json`. Markdown files (`.md` or `.markdown`) are also accepted for locally prepared or transcribed text; retain the official record URL in the manifest and verify the Markdown against that source before marking it `verified`. The importer rejects non-allowlisted source hosts. To add another official publisher later, review and deliberately update the allowlist in `ai/ingestion.py`; do not weaken it to accept arbitrary URLs.

## Metadata manifest

`data/corpus/manifest.json` is an array. Each entry represents one source document, not a chunk. Required fields:

```json
{
  "document_id": "senate-journal-20c-2026-001",
  "title": "Exact title shown by the issuing source",
  "issuing_body": "Senate of the Philippines",
  "source_url": "https://senate.gov.ph/path/to/original-record.pdf",
  "publication_date": "2026-07-27",
  "retrieved_at": "2026-11-24",
  "relevant_period": "20th Congress, First Regular Session",
  "record_type": "journal",
  "verification_status": "verified",
  "senator_ids": [],
  "source_file": "senate-journal-20c-2026-001.pdf"
}
```

Use the source's actual title and issuing body. `publication_date` may be `null` if the source does not provide one. `retrieved_at` is the date the developer saved/reviewed the file. Set `verification_status` to `verified` only after checking that the local file is the same record as the cited official page. The importer intentionally refuses candidate, stale, or conflicting records. Keep `senator_ids` empty unless the record's relationship to those people has been checked; the existing directory IDs are design examples, not evidence.

The importer computes a SHA-256 of each original and stores it with every chunk. Optionally add an `expected_sha256` value (64 hexadecimal characters) after downloading and reviewing a file; ingestion compares the file against that pinned value and stops if it changed. It retains source URL, dates, period, record type, document ID, and an exact page or HTML heading locator on every chunk. It does not modify the original file.

## Extract, normalize, and chunk

Run from the repository root after installing the declared requirements:

```sh
python -m pip install -r requirements.txt
python tools/ingest_documents.py
```

The importer extracts selectable text from PDFs with `pypdf`; PDF pages become locators. It parses HTML locally and drops scripts, styles, forms, navigation, and footer text; headings become section locators. It reads Markdown as UTF-8 and uses ATX headings (`#`, `##`, and so on) as section locators. It does not execute HTML or fetch linked resources. Scanned/image-only PDFs are rejected with an explicit message; OCR is not included because OCR can create factual transcription errors and needs manual review.

Normalization applies Unicode NFKC, removes soft hyphens and formatting/control characters (including zero-width/bidi controls), ignores scripts/styles/forms/navigation/footers and explicitly hidden HTML elements, normalizes line endings and repeated whitespace, and preserves paragraph breaks. Keep the raw original and its checksum so normalization never replaces the source evidence. Chunking is deterministic, paragraph-aware, approximately 1,200 characters with 180 characters of overlap, and does not cross PDF pages or HTML heading sections. Character-based chunking is a starter baseline; inspect the extracted passages and adjust with a reviewed question set before embedding.

Generated chunks go to `data/corpus/processed/chunks.jsonl` and are ignored by Git by default. Each JSONL row is a chunk with a stable content-derived ID, source metadata, locator, checksum, extraction/chunking versions, MIME type, and `content_trust: untrusted_official_source_text`. For Markdown inputs, the checksum is for the local Markdown file; the official source URL and manual review establish its provenance. Do not feed a chunk's text to an LLM as an instruction. A later retrieval step should store the source ID and locator with every vector and validate citations against retrieved chunk IDs.

## First review before embedding

For every ingested record, manually inspect the extracted text against its original file, especially names, bill numbers, dates, vote marks, tables, and page boundaries. Confirm the title, issuing body, URL, publication date, relevant period, and official-source status. If PDF text is empty or garbled, stop and correct the extraction through a separately reviewed process; do not silently index it. No records have been added to the corpus yet.
