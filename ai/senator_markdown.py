"""Parse reviewed, sectioned senator Markdown records into cited chunks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

from ai.ingestion import CHUNK_SIZE, CHUNK_OVERLAP, _chunks, normalize_text


SENATOR_SECTIONS = (
    "Biography",
    "Political_History",
    "Current_Position.",
    "Legislative_Authorship.",
    "Voting_Records",
    "Policy_Standpoints",
    "Laws_and_Accomplishments",
    "Public_Service",
    "Graft_and_Corruption",
    "Controversies",
    "Public_Statements",
    "Financial_Disclosures",
    "Historical_Performance",
)
REFERENCE_HEADING = "References"
SOURCE_TYPES = {
    "official_record",
    "government_publication",
    "secondary_news",
    "research_organization",
    "other",
}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
_REFERENCE = re.compile(r"^\[(?P<id>\d{1,4})\]\s+(?P<description>.+?)\s*$")
_CITATION = re.compile(r"\[(\d{1,4})\]")
_PLACEHOLDER = re.compile(
    r"^(?:not researched|not covered|not available in the current dataset|"
    r"no verified records in the current dataset|coverage not reviewed)\b",
    re.IGNORECASE,
)


class SenatorRecordError(ValueError):
    """A senator record is malformed or lacks required claim-level provenance."""


@dataclass(frozen=True)
class SenatorReference:
    reference_id: str
    title: str
    issuing_body: str
    source_type: str
    source_url: str
    publication_date: str | None
    retrieved_at: str
    relevant_period: str
    locator: str
    verification_status: str

    def as_dict(self, senator_id: str) -> dict:
        return {
            "source_id": f"{senator_id}:ref-{self.reference_id}",
            "reference_id": self.reference_id,
            "title": self.title,
            "issuing_body": self.issuing_body,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "publication_date": self.publication_date,
            "retrieved_at": self.retrieved_at,
            "relevant_period": self.relevant_period,
            "locator": self.locator,
            "verification_status": self.verification_status,
        }


def _read_frontmatter(lines: list[str], path: Path) -> tuple[dict[str, str], list[str]]:
    if not lines or lines[0].strip() != "---":
        raise SenatorRecordError(f"{path.name}: expected YAML-style frontmatter with senator_id.")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise SenatorRecordError(f"{path.name}: frontmatter is not closed with '---'.") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise SenatorRecordError(f"{path.name}: invalid frontmatter line {line!r}.")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if not key or key in metadata:
            raise SenatorRecordError(f"{path.name}: empty or duplicate frontmatter key {key!r}.")
        metadata[key] = value
    return metadata, lines[end + 1:]


def _parse_date(value: str, label: str, path: Path, *, optional: bool = False) -> str | None:
    value = value.strip()
    if optional and value.casefold() in {"", "unknown", "not stated", "not_stated", "n/a", "null"}:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SenatorRecordError(f"{path.name}: {label} must be YYYY-MM-DD.") from exc
    return parsed.isoformat()


def _validate_reference_url(value: str, path: Path, reference_id: str) -> None:
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        valid_port = parsed.port in (None, 443)
    except ValueError as exc:
        raise SenatorRecordError(f"{path.name}: reference [{reference_id}] has a malformed URL.") from exc
    if (
        parsed.scheme != "https"
        or not host
        or "." not in host
        or parsed.username
        or parsed.password
        or not valid_port
    ):
        raise SenatorRecordError(
            f"{path.name}: reference [{reference_id}] must use an HTTPS public URL without credentials."
        )


def _parse_reference_line(line: str, path: Path) -> SenatorReference:
    match = _REFERENCE.fullmatch(line.strip())
    if not match:
        raise SenatorRecordError(
            f"{path.name}: malformed reference line; use '[n] Title — Issuing body | key=value ...'."
        )
    reference_id = match.group("id")
    fields = match.group("description").split(" | ")
    title_and_body = fields[0].strip()
    if " — " not in title_and_body:
        raise SenatorRecordError(f"{path.name}: reference [{reference_id}] needs a title and issuing body.")
    title, issuing_body = (part.strip() for part in title_and_body.split(" — ", 1))
    values: dict[str, str] = {}
    for field in fields[1:]:
        if "=" not in field:
            raise SenatorRecordError(f"{path.name}: invalid metadata for reference [{reference_id}].")
        key, value = (part.strip() for part in field.split("=", 1))
        if not key or not value or key in values:
            raise SenatorRecordError(f"{path.name}: empty or duplicate metadata for reference [{reference_id}].")
        values[key] = value

    required = {
        "source_type", "publication_date", "retrieved_at", "relevant_period",
        "locator", "verification_status", "url",
    }
    missing = required - values.keys()
    if missing:
        raise SenatorRecordError(
            f"{path.name}: reference [{reference_id}] is missing {', '.join(sorted(missing))}."
        )
    if values["source_type"] not in SOURCE_TYPES:
        raise SenatorRecordError(f"{path.name}: reference [{reference_id}] has an unsupported source_type.")
    if values["verification_status"] != "verified":
        raise SenatorRecordError(
            f"{path.name}: only verified references may support indexed claims ({reference_id})."
        )
    if not title or not issuing_body or not values["relevant_period"].strip() or not values["locator"].strip():
        raise SenatorRecordError(f"{path.name}: reference [{reference_id}] has empty provenance fields.")
    _validate_reference_url(values["url"], path, reference_id)
    return SenatorReference(
        reference_id=reference_id,
        title=title,
        issuing_body=issuing_body,
        source_type=values["source_type"],
        source_url=values["url"],
        publication_date=_parse_date(values["publication_date"], "publication_date", path, optional=True),
        retrieved_at=_parse_date(values["retrieved_at"], "retrieved_at", path),
        relevant_period=values["relevant_period"],
        locator=values["locator"],
        verification_status=values["verification_status"],
    )


def _split_headings(lines: list[str], path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        heading = re.match(r"^ {0,3}##[ \t]+(.+?)\s*#*\s*$", line)
        if heading:
            current = heading.group(1).strip()
            if current in sections:
                raise SenatorRecordError(f"{path.name}: duplicate section heading {current!r}.")
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    expected = [*SENATOR_SECTIONS, REFERENCE_HEADING]
    missing = [heading for heading in expected if heading not in sections]
    if missing:
        raise SenatorRecordError(f"{path.name}: missing required section(s): {', '.join(missing)}.")
    actual = list(sections)
    if actual != expected:
        raise SenatorRecordError(
            f"{path.name}: section headings must appear once and in the specified order."
        )
    return sections


def _paragraphs(lines: list[str]) -> list[str]:
    text = "\n".join(lines)
    return [normalize_text(part) for part in re.split(r"\n\s*\n", text) if normalize_text(part)]


def parse_senator_markdown(path: Path) -> list[dict]:
    """Return cited claim chunks. Reference samples and intentionally disabled files return []."""
    try:
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        raise SenatorRecordError(f"Could not read {path.name} as UTF-8: {exc}") from exc
    if lines:
        lines[0] = lines[0].lstrip("\ufeff")
    metadata, body = _read_frontmatter(lines, path)
    senator_id = metadata.get("senator_id", "")
    if not _SLUG.fullmatch(senator_id):
        raise SenatorRecordError(f"{path.name}: senator_id must be a lowercase slug.")
    if metadata.get("record_status") == "reference_sample" or metadata.get(
        "ingestion_status"
    ) == "do_not_ingest_as_complete_profile":
        return []

    sections = _split_headings(body, path)
    references: dict[str, SenatorReference] = {}
    for line in sections[REFERENCE_HEADING]:
        if not line.strip():
            continue
        reference = _parse_reference_line(line, path)
        if reference.reference_id in references:
            raise SenatorRecordError(f"{path.name}: duplicate reference [{reference.reference_id}].")
        references[reference.reference_id] = reference

    try:
        raw_file = path.read_bytes()
    except OSError as exc:
        raise SenatorRecordError(f"Could not checksum {path.name}: {exc}") from exc
    source_sha256 = hashlib.sha256(raw_file).hexdigest()
    output: list[dict] = []
    for section in SENATOR_SECTIONS:
        for block_index, block in enumerate(_paragraphs(sections[section]), start=1):
            if _PLACEHOLDER.match(block):
                continue
            reference_ids = list(dict.fromkeys(_CITATION.findall(block)))
            if not reference_ids:
                raise SenatorRecordError(
                    f"{path.name}: content in {section} needs at least one inline reference ID."
                )
            missing_refs = [reference_id for reference_id in reference_ids if reference_id not in references]
            if missing_refs:
                raise SenatorRecordError(
                    f"{path.name}: {section} refers to undefined source(s): "
                    + ", ".join(f"[{item}]" for item in missing_refs)
                    + "."
                )
            citation_sources = [references[item].as_dict(senator_id) for item in reference_ids]
            for chunk_index, text in enumerate(_chunks(block, CHUNK_SIZE, CHUNK_OVERLAP), start=1):
                digest = hashlib.sha256(
                    f"{senator_id}\0{section}\0{block_index}\0{chunk_index}\0{text}".encode("utf-8")
                ).hexdigest()[:20]
                output.append({
                    "schema_version": "2.0",
                    "document_id": f"senator-record:{senator_id}",
                    "chunk_id": f"{senator_id}:{digest}",
                    "chunk_index": len(output) + 1,
                    "senator_id": senator_id,
                    "senator_ids": [senator_id],
                    "section": section,
                    "title": f"{senator_id} — {section}",
                    "issuing_body": "SEN’TO curated senator record",
                    "record_type": "senator_profile_claim",
                    "source_type": "curated_summary",
                    "source_url": None,
                    "source_ids": [source["source_id"] for source in citation_sources],
                    "citation_sources": citation_sources,
                    "publication_date": None,
                    "retrieved_at": max(source["retrieved_at"] for source in citation_sources),
                    "relevant_period": "; ".join(dict.fromkeys(
                        source["relevant_period"] for source in citation_sources
                    )),
                    "verification_status": "verified",
                    "locator": f"Section: {section}",
                    "source_file": path.name,
                    "source_mime_type": "text/markdown",
                    "source_sha256": source_sha256,
                    "extraction_version": "senator-markdown-1.0",
                    "chunking_version": "claim-paragraph-1200-overlap-180-v1",
                    "content_trust": "untrusted_curated_record_text",
                    "text": text,
                })
    return output


def ingest_senator_records(records_dir: Path) -> list[dict]:
    """Parse every top-level Markdown senator file in a directory."""
    if not records_dir.exists():
        return []
    output: list[dict] = []
    seen_senators: set[str] = set()
    for path in sorted([*records_dir.glob("*.md"), *records_dir.glob("*.markdown")]):
        chunks = parse_senator_markdown(path)
        if chunks:
            senator_id = chunks[0]["senator_id"]
            if senator_id in seen_senators:
                raise SenatorRecordError(f"Duplicate senator_id in {records_dir}: {senator_id}.")
            seen_senators.add(senator_id)
            output.extend(chunks)
    return output
