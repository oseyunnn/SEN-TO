"""Deterministic ingestion for developer-curated official Senate records.

This module reads only files listed in a local manifest. It never fetches a URL.
Extracted source text is untrusted reference material and must not be interpreted
as instructions by a future generation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit



SCHEMA_VERSION = "1.0"
EXTRACTION_VERSION = "1.0"
CHUNKING_VERSION = "paragraph-char-1200-overlap-180-v1"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 180
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 2000
OFFICIAL_HOSTS = {
    "senate.gov.ph",
    "www.senate.gov.ph",
    "legacy.senate.gov.ph",
    "issuances-library.senate.gov.ph",
    "officialgazette.gov.ph",
    "www.officialgazette.gov.ph",
}
ALLOWED_RECORD_TYPES = {
    "bill", "resolution", "journal", "committee_report", "transcript",
    "republic_act", "senate_profile", "senate_publication", "other_official_record",
}


class IngestionError(ValueError):
    """Invalid manifest, source file, or extraction result."""


@dataclass(frozen=True)
class TextUnit:
    locator: str
    text: str


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace while preserving paragraph boundaries."""
    value = unicodedata.normalize("NFKC", value).replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("\u00ad", "")
    value = "".join(
        char for char in value
        if char in "\n\t\f" or unicodedata.category(char) not in {"Cf", "Cc", "Cs"}
    )
    lines = [re.sub(r"[ \t\f]+", " ", line).strip() for line in value.split("\n")]
    paragraphs = []
    for line in lines:
        if line:
            paragraphs.append(line)
        elif paragraphs and paragraphs[-1] != "":
            paragraphs.append("")
    return "\n".join(paragraphs).strip()


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text by heading; scripts and presentation boilerplate are ignored."""

    SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "form", "nav", "footer"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_stack: list[str] = []
        self.heading_tag = None
        self.heading_parts: list[str] = []
        self.section = "Document"
        self.sections: list[tuple[str, list[str]]] = [(self.section, [])]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = {key.lower(): (value or "") for key, value in attrs}
        hidden_style = re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", attributes.get("style", ""), re.I)
        hidden = "hidden" in attributes or attributes.get("aria-hidden", "").lower() == "true" or hidden_style
        if self.skip_stack:
            if tag not in self.VOID_TAGS:
                self.skip_stack.append(tag)
            return
        if tag in self.SKIP_TAGS or hidden:
            if tag not in self.VOID_TAGS:
                self.skip_stack.append(tag)
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.heading_tag = tag
            self.heading_parts = []
        elif tag in {"p", "br", "li", "tr", "article", "section"}:
            self.sections[-1][1].append("\n\n" if tag in {"p", "li", "tr", "article", "section"} else "\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip_stack:
            if tag in self.skip_stack:
                matching = len(self.skip_stack) - 1 - self.skip_stack[::-1].index(tag)
                del self.skip_stack[matching:]
            return
        if self.heading_tag == tag:
            title = normalize_text(" ".join(self.heading_parts))
            if title:
                self.section = title[:240]
                self.sections.append((self.section, []))
            self.heading_tag = None
            self.heading_parts = []
        elif tag in {"p", "li", "tr", "article", "section"}:
            self.sections[-1][1].append("\n\n")

    def handle_data(self, data):
        if self.skip_stack:
            return
        if self.heading_tag:
            self.heading_parts.append(data)
        else:
            self.sections[-1][1].append(data)


def _extract_html(path: Path) -> list[TextUnit]:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        parser.close()
    except Exception as exc:
        raise IngestionError(f"Could not parse HTML file {path.name}: {exc}") from exc
    units = [TextUnit(f"Section: {title}", normalize_text("".join(parts)))
             for title, parts in parser.sections]
    units = [unit for unit in units if unit.text]
    if not units:
        raise IngestionError(f"No readable text found in HTML file {path.name}.")
    return units


def _extract_markdown(path: Path) -> list[TextUnit]:
    """Read local Markdown and use ATX headings as section locators."""
    try:
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        raise IngestionError(f"Could not read Markdown file {path.name} as UTF-8: {exc}") from exc

    units: list[TextUnit] = []
    heading_stack: list[tuple[int, str]] = []
    section_lines: list[str] = []
    fence_char = None
    fence_length = 0

    def flush_section():
        text = normalize_text("\n".join(section_lines))
        if text:
            locator = " > ".join(title for _, title in heading_stack) or "Document"
            units.append(TextUnit(f"Section: {locator}", text))

    for line in lines:
        fence = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if fence_char is None:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char, fence_length = None, 0
            section_lines.append(line)
            continue

        heading = None if fence_char else re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*#*\s*$", line)
        if heading:
            flush_section()
            section_lines = []
            level = len(heading.group(1))
            title = normalize_text(heading.group(2))
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title[:240]))
            continue
        section_lines.append(line)

    flush_section()
    if not units:
        raise IngestionError(f"No readable text found in Markdown file {path.name}.")
    return units


def _extract_pdf(path: Path) -> list[TextUnit]:
    from pypdf import PdfReader
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise IngestionError(f"Encrypted PDF is not supported: {path.name}")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise IngestionError(f"PDF exceeds {MAX_PDF_PAGES} pages: {path.name}")
        units = [TextUnit(f"Page {number}", normalize_text(page.extract_text() or ""))
                 for number, page in enumerate(reader.pages, start=1)]
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"Could not extract PDF {path.name}: {exc}") from exc
    if not any(unit.text for unit in units):
        raise IngestionError(
            f"No selectable text found in {path.name}. Scanned/OCR-only PDFs need manual review; "
            "this importer does not run OCR."
        )
    return [unit for unit in units if unit.text]


def _validate_source_url(value: str, document_id: str) -> None:
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        allowed = host in OFFICIAL_HOSTS
        valid_port = parsed.port in (None, 443)
    except ValueError as exc:
        raise IngestionError(f"{document_id}: source_url is malformed.") from exc
    if parsed.scheme != "https" or not allowed or parsed.username or parsed.password or not valid_port:
        raise IngestionError(
            f"{document_id}: source_url must be HTTPS on an allowlisted official Senate or "
            "Official Gazette host. Review the official-host allowlist before adding other sources."
        )


def _validate_entry(entry, seen_ids: set[str]) -> None:
    required = {
        "document_id", "title", "issuing_body", "source_url", "retrieved_at",
        "relevant_period", "record_type", "verification_status", "source_file",
    }
    missing = required - set(entry)
    if missing:
        raise IngestionError(f"Manifest entry is missing: {', '.join(sorted(missing))}")
    document_id = entry["document_id"]
    if not isinstance(document_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,99}", document_id):
        raise IngestionError("document_id must be a 2-100 character lowercase slug.")
    if document_id in seen_ids:
        raise IngestionError(f"Duplicate document_id: {document_id}")
    seen_ids.add(document_id)
    for key in ("title", "issuing_body", "relevant_period", "source_file"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise IngestionError(f"{document_id}: {key} must be a non-empty string.")
    if not isinstance(entry["record_type"], str) or entry["record_type"] not in ALLOWED_RECORD_TYPES:
        raise IngestionError(f"{document_id}: unsupported record_type {entry['record_type']!r}.")
    if entry["verification_status"] != "verified":
        raise IngestionError(f"{document_id}: only manually reviewed 'verified' records are ingested.")
    if not isinstance(entry["source_url"], str):
        raise IngestionError(f"{document_id}: source_url must be a string.")
    _validate_source_url(entry["source_url"], document_id)
    if not isinstance(entry.get("senator_ids", []), list) or not all(
        isinstance(item, str) and item.strip() for item in entry.get("senator_ids", [])
    ):
        raise IngestionError(f"{document_id}: senator_ids must be a list of non-empty strings.")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["retrieved_at"]):
            raise ValueError("retrieved_at must use YYYY-MM-DD")
        date.fromisoformat(entry["retrieved_at"])
        if entry.get("publication_date"):
            if not isinstance(entry["publication_date"], str) or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}", entry["publication_date"]
            ):
                raise ValueError("publication_date must use YYYY-MM-DD")
            date.fromisoformat(entry["publication_date"])
    except (TypeError, ValueError) as exc:
        raise IngestionError(f"{document_id}: dates must use YYYY-MM-DD format.") from exc


def _source_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    base = root.resolve()
    if not candidate.is_relative_to(base):
        raise IngestionError("source_file must stay inside the configured source directory.")
    if not candidate.is_file():
        raise IngestionError(f"Source file does not exist: {relative_path}")
    size = candidate.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise IngestionError(f"Source file must be between 1 byte and {MAX_SOURCE_BYTES} bytes: {relative_path}")
    return candidate


def _chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Chunk on paragraph/word boundaries where possible, with deterministic overlap."""
    if size <= overlap or overlap < 0:
        raise ValueError("chunk size must exceed a non-negative overlap")
    result: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            lower_bound = start + int(size * 0.65)
            paragraph_break = text.rfind("\n\n", lower_bound, end)
            word_break = text.rfind(" ", lower_bound, end)
            boundary = paragraph_break if paragraph_break > start else word_break
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            result.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return result


def _stable_id(document_id: str, locator: str, chunk_index: int, content: str) -> str:
    digest = hashlib.sha256(f"{document_id}\0{locator}\0{chunk_index}\0{content}".encode("utf-8")).hexdigest()[:20]
    return f"{document_id}:{digest}"


def ingest(manifest_path: Path, source_root: Path) -> list[dict]:
    """Validate, extract and chunk every verified manifest entry."""
    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IngestionError(f"Could not read manifest {manifest_path}: {exc}") from exc
    if not isinstance(entries, list):
        raise IngestionError("Manifest must be a JSON array of document records.")

    output: list[dict] = []
    seen_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise IngestionError("Each manifest entry must be a JSON object.")
        _validate_entry(entry, seen_ids)
        path = _source_path(source_root, entry["source_file"])
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IngestionError(f"Could not read source file {entry['source_file']}: {exc}") from exc
        raw_sha256 = hashlib.sha256(data).hexdigest()
        expected_sha256 = entry.get("expected_sha256")
        if expected_sha256 is not None:
            if not isinstance(expected_sha256, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
                raise IngestionError(f"{entry['document_id']}: expected_sha256 must be 64 hexadecimal characters.")
            if raw_sha256.lower() != expected_sha256.lower():
                raise IngestionError(f"{entry['document_id']}: source file checksum does not match expected_sha256.")
        extension = path.suffix.lower()
        if extension in {".md", ".markdown"}:
            units = _extract_markdown(path)
            mime_type = "text/markdown"
        else:
            raise IngestionError(f"Unsupported source format for {path.name}; only Markdown files are processed.")

        page_chunk_index = 0
        for unit in units:
            for text in _chunks(unit.text):
                page_chunk_index += 1
                output.append({
                    "schema_version": SCHEMA_VERSION,
                    "document_id": entry["document_id"],
                    "chunk_id": _stable_id(entry["document_id"], unit.locator, page_chunk_index, text),
                    "chunk_index": page_chunk_index,
                    "title": entry["title"].strip(),
                    "issuing_body": entry["issuing_body"].strip(),
                    "source_url": entry["source_url"],
                    "publication_date": entry.get("publication_date"),
                    "retrieved_at": entry["retrieved_at"],
                    "relevant_period": entry["relevant_period"].strip(),
                    "record_type": entry["record_type"],
                    "verification_status": "verified",
                    "senator_ids": sorted(set(entry.get("senator_ids", []))),
                    "locator": unit.locator,
                    "source_file": entry["source_file"],
                    "source_mime_type": mime_type,
                    "source_sha256": raw_sha256,
                    "extraction_version": EXTRACTION_VERSION,
                    "chunking_version": CHUNKING_VERSION,
                    "content_trust": "untrusted_official_source_text",
                    "text": text,
                })
    return output


def write_jsonl_atomic(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
