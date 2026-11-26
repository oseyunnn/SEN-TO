"""Parse claim-based senator research profiles and the legacy cited Markdown format."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from pathlib import Path
import unicodedata
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
_CLAIM_LINE = re.compile(r"^ {0,3}-\s+\[(?P<claim_id>CLM-[A-Z0-9-]+)\]\s*(?P<text>.*)$")
_SOURCE_LINE = re.compile(r"^ {0,3}-\s+\[(?P<source_id>SRC-[A-Z0-9-]+)\]\s*(?P<description>.*)$")
_FIELD_LINE = re.compile(r"^\s{2,}(?P<key>[A-Za-z][A-Za-z0-9_]*)\s*:\s*(?P<value>.*?)\s*$")
_PROFILE_SECTION = re.compile(r"^(?P<number>\d{1,2})_(?P<name>.+)$")
_SOURCE_UNCERTAINTY = (
    "search-result content",
    "search result content",
    "search-result excerpt",
    "search result excerpt",
    "direct open returned",
    "not independently revalidated",
    "not directly opened",
    "could not open",
    "access error",
)
_KNOWN_ISSUERS = (
    "Senate Public Relations and Information Bureau",
    "Senate Legislative Reference Bureau",
    "Senate Budget Transparency Portal",
    "Senate of the Philippines",
    "Senate e-Monitor",
    "Senate.ph",
    "Senate LRB",
    "Commission on Elections",
    "COMELEC",
    "Supreme Court of the Philippines",
    "Supreme Court",
    "Sandiganbayan",
    "Office of the Ombudsman",
    "Ombudsman",
    "Department of Budget and Management",
    "Department of Education",
    "Presidential Legislative Liaison Office",
    "Official Gazette",
    "House of Representatives",
    "Tourism Promotions Board",
    "Philippine News Agency",
    "GMA News Online",
    "GMA News",
    "ABS-CBN News",
    "Manila Bulletin",
    "Philstar Life",
    "Philstar.com",
    "Philstar",
    "Inquirer.net",
    "Inquirer",
    "Rappler",
    "Daily Tribune",
    "Journal News Online",
    "News5",
    "TV5",
    "SunStar Manila",
    "SunStar",
    "VERA Files",
    "BatasWatch",
    "BetterGov SALN Tracker",
    "Wikiwand",
    "Wikipedia",
    "DBM",
    "PNA",
)
_EXPLICIT_RECORD_NAME_ALIASES = {
    "tito sotto": "vicente-sotto-iii",
}


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


def _frontmatter_value(value: str, path: Path, key: str):
    """Read scalar and flow-list values used by the senator record files."""
    value = value.strip()
    if not value:
        return []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise SenatorRecordError(f"{path.name}: malformed frontmatter list for {key}.") from exc
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise SenatorRecordError(f"{path.name}: frontmatter list {key} must contain strings.")
        return parsed
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise SenatorRecordError(f"{path.name}: malformed quoted frontmatter value for {key}.") from exc
        if not isinstance(parsed, str):
            raise SenatorRecordError(f"{path.name}: frontmatter value {key} must be text.")
        return parsed
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if value.casefold() in {"null", "~"}:
        return None
    return value


def _read_frontmatter(lines: list[str], path: Path) -> tuple[dict, list[str]]:
    if not lines or lines[0].strip() != "---":
        raise SenatorRecordError(f"{path.name}: expected YAML-style frontmatter.")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise SenatorRecordError(f"{path.name}: frontmatter is not closed with '---'.") from exc

    metadata: dict = {}
    list_key = None
    scalar_key = None
    scalar_style = "folded"
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.lstrip().startswith("-"):
            if list_key is None or not isinstance(metadata.get(list_key), list):
                raise SenatorRecordError(f"{path.name}: unexpected frontmatter list item {line!r}.")
            metadata[list_key].append(_frontmatter_value(line.lstrip()[1:].strip(), path, list_key))
            continue
        if line[0].isspace():
            if scalar_key is None:
                raise SenatorRecordError(f"{path.name}: unexpected frontmatter continuation {line!r}.")
            continuation = line.strip()
            separator = "\n" if scalar_style == "literal" else " "
            metadata[scalar_key] = f"{metadata[scalar_key]}{separator}{continuation}".strip()
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", line)
        if not match:
            raise SenatorRecordError(f"{path.name}: invalid frontmatter line {line!r}.")
        key, raw_value = match.groups()
        if not key or key in metadata:
            raise SenatorRecordError(f"{path.name}: empty or duplicate frontmatter key {key!r}.")
        if raw_value in {">", ">-", ">+", "|", "|-", "|+"}:
            metadata[key] = ""
            scalar_key = key
            scalar_style = "literal" if raw_value.startswith("|") else "folded"
        else:
            metadata[key] = _frontmatter_value(raw_value, path, key)
            scalar_key = None if isinstance(metadata[key], list) else key if isinstance(metadata[key], str) else None
            scalar_style = "folded"
        list_key = key if isinstance(metadata[key], list) else None
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


def _name_tokens(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    characters = []
    for character in normalized:
        if unicodedata.category(character) == "Mn":
            continue
        characters.append(character if character.isalnum() else " ")
    return tuple("".join(characters).split())


def _contains_name_phrase(name_tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    if not phrase or len(phrase) < 2 or len(phrase) > len(name_tokens):
        return False
    return any(
        name_tokens[offset:offset + len(phrase)] == phrase
        for offset in range(len(name_tokens) - len(phrase) + 1)
    )


def _resolve_profile_senator_id(metadata: dict, path: Path) -> str:
    directory_path = Path(__file__).resolve().parents[1] / "data" / "senators.json"
    try:
        directory = json.loads(directory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SenatorRecordError(f"{path.name}: could not load the senator directory for subject mapping.") from exc

    explicit_id = metadata.get("senator_id")
    if explicit_id is not None:
        if not isinstance(explicit_id, str) or not _SLUG.fullmatch(explicit_id):
            raise SenatorRecordError(f"{path.name}: senator_id must be a lowercase slug.")
        if not any(senator.get("id") == explicit_id for senator in directory):
            raise SenatorRecordError(f"{path.name}: senator_id is not present in data/senators.json.")
        return explicit_id

    aliases = [metadata.get("common_name"), metadata.get("full_name")]
    raw_aliases = metadata.get("aliases", [])
    if isinstance(raw_aliases, list):
        aliases.extend(raw_aliases)
    aliases = [value for value in aliases if isinstance(value, str) and value.strip()]

    candidates: set[str] = set()
    directory_names: dict[str, list[tuple[str, ...]]] = {}
    for senator in directory:
        senator_id = senator.get("id")
        if not isinstance(senator_id, str) or not _SLUG.fullmatch(senator_id):
            continue
        names = [senator.get("name"), senator.get("official_name")]
        directory_names[senator_id] = [
            tokens for name in names if isinstance(name, str) and (tokens := _name_tokens(name))
        ]

    for alias in aliases:
        alias_tokens = _name_tokens(alias)
        if not alias_tokens:
            continue
        normalized_alias = " ".join(alias_tokens)
        explicit_match = _EXPLICIT_RECORD_NAME_ALIASES.get(normalized_alias)
        if explicit_match:
            candidates.add(explicit_match)
        for senator_id, names in directory_names.items():
            if any(
                alias_tokens == name_tokens or _contains_name_phrase(name_tokens, alias_tokens)
                for name_tokens in names
            ):
                candidates.add(senator_id)

    if len(candidates) == 1:
        return next(iter(candidates))
    if not candidates:
        raise SenatorRecordError(
            f"{path.name}: could not map common_name/aliases to a senator directory entry."
        )
    raise SenatorRecordError(
        f"{path.name}: common_name/aliases match multiple senator directory entries: "
        + ", ".join(sorted(candidates))
        + "."
    )


def _is_safe_https_url(value: str | None) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        valid_port = parsed.port in (None, 443)
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https"
        and host
        and "." in host
        and not parsed.username
        and not parsed.password
        and valid_port
    )


def _parse_optional_date(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", value)
    if len(matches) != 1:
        return None
    try:
        return date.fromisoformat(matches[0]).isoformat()
    except ValueError:
        return None


def _source_type(issuing_body: str) -> str:
    folded = issuing_body.casefold()
    official_terms = (
        "senate of the philippines", "senate legislative reference bureau", "senate lrb",
        "commission on elections", "comelec", "supreme court", "sandiganbayan",
        "ombudsman", "department of", "official gazette", "house of representatives",
    )
    news_terms = (
        "gma news", "abs-cbn", "philstar", "inquirer", "manila bulletin", "rappler",
        "daily tribune", "news5", "tv5", "sunstar", "journal news", "cnn philippines",
    )
    research_terms = ("bataswatch", "bettergov", "vera files")
    if any(term in folded for term in official_terms):
        return "government_publication"
    if any(term in folded for term in news_terms):
        return "secondary_news"
    if any(term in folded for term in research_terms):
        return "research_organization"
    return "other"


def _known_issuer(value: str) -> str | None:
    for issuer in sorted(_KNOWN_ISSUERS, key=len, reverse=True):
        match = re.search(re.escape(issuer), value, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _split_source_description(description: str) -> tuple[str, str, str | None]:
    """Split the record's `Title — Issuer, date` bibliography label conservatively."""
    parts = [part.strip() for part in description.split(" — ")]
    if len(parts) == 1:
        return description.strip(), "Unknown issuing body", None

    final_segment = parts[-1]
    final_is_date = bool(re.match(
        r"^(?:\d{4}(?:-\d{2}(?:-\d{2})?)?|publication date unavailable|undated)\b",
        final_segment,
        re.IGNORECASE,
    ))
    if len(parts) >= 3 and final_is_date:
        title = " — ".join(parts[:-2])
        issuer_segment = parts[-2]
        issuer = _known_issuer(issuer_segment) or issuer_segment
        return title.strip(), issuer.strip(" ,.") or "Unknown issuing body", final_segment.rstrip(".")

    title = " — ".join(parts[:-1])
    publisher_and_date = parts[-1]
    date_match = re.search(
        r",\s*(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?|publication date unavailable|undated)\.?\s*$",
        publisher_and_date,
        re.IGNORECASE,
    )
    if date_match:
        issuer_segment = publisher_and_date[:date_match.start()].strip(" ,")
        publication_date_text = date_match.group("date").strip()
    else:
        issuer_segment = publisher_and_date
        date_text_match = re.search(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
            publisher_and_date,
            re.IGNORECASE,
        )
        publication_date_text = date_text_match.group(0) if date_text_match else None
    issuer = _known_issuer(issuer_segment) or issuer_segment.strip(" ,.")
    return title.strip(), issuer or "Unknown issuing body", publication_date_text


def _parse_profile_references(body: list[str], path: Path, senator_id: str) -> dict[str, dict]:
    references: dict[str, dict] = {}
    in_references = False
    index = 0
    while index < len(body):
        heading = re.match(r"^ {0,3}##[ \t]+(.+?)\s*#*\s*$", body[index])
        if heading:
            in_references = heading.group(1).strip() == REFERENCE_HEADING
            index += 1
            continue
        match = _SOURCE_LINE.match(body[index]) if in_references else None
        if not match:
            index += 1
            continue

        source_id = match.group("source_id")
        description = match.group("description").strip()
        fields: dict[str, str] = {}
        next_index = index + 1
        while next_index < len(body):
            if not body[next_index].strip() or _SOURCE_LINE.match(body[next_index]):
                break
            next_heading = re.match(r"^ {0,3}##[ \t]+", body[next_index])
            if next_heading:
                break
            field = _FIELD_LINE.match(body[next_index])
            if field:
                fields[field.group("key").casefold()] = field.group("value").strip()
            next_index += 1

        title, issuing_body, publication_date_text = _split_source_description(description)
        source_url = fields.get("url")
        retrieved_at = _parse_optional_date(fields.get("retrieved"))
        locator = fields.get("locator")
        publication_date = _parse_optional_date(publication_date_text)
        access_note = "; ".join(
            fields[key] for key in ("access", "access_note") if fields.get(key)
        )
        uncertainty_text = " ".join((description, access_note)).casefold()
        source_complete = bool(
            title
            and issuing_body != "Unknown issuing body"
            and _is_safe_https_url(source_url)
            and retrieved_at
            and locator
            and not any(marker in uncertainty_text for marker in _SOURCE_UNCERTAINTY)
        )
        reference = {
            "source_id": f"{senator_id}:{source_id}",
            "reference_id": source_id,
            "title": title or description or f"Unresolved source {source_id}",
            "issuing_body": issuing_body,
            "source_type": _source_type(issuing_body),
            "source_url": source_url,
            "publication_date": publication_date,
            "publication_date_text": publication_date_text,
            "retrieved_at": retrieved_at,
            "retrieved_at_text": fields.get("retrieved"),
            "locator": locator,
            "access_note": access_note or None,
            "source_description": description,
            "verification_status": "candidate_source",
            "_provenance_complete": source_complete,
        }
        if source_id in references:
            duplicate = dict(references[source_id])
            duplicate["_provenance_complete"] = False
            duplicate["duplicate_reference"] = True
            duplicate["source_description"] = f"{duplicate['source_description']} | duplicate: {description}"
            references[source_id] = duplicate
        else:
            references[source_id] = reference
        index = next_index
    return references


def _profile_claim_blocks(body: list[str], path: Path):
    section_heading = None
    index = 0
    while index < len(body):
        heading = re.match(r"^ {0,3}##[ \t]+(.+?)\s*#*\s*$", body[index])
        if heading:
            title = heading.group(1).strip()
            if title == REFERENCE_HEADING:
                break
            section = _PROFILE_SECTION.fullmatch(title)
            section_heading = title if section else None
            index += 1
            continue
        claim = _CLAIM_LINE.match(body[index])
        if not section_heading or not claim:
            index += 1
            continue

        fields: dict[str, str] = {}
        continuation: list[str] = []
        next_index = index + 1
        last_field = None
        while next_index < len(body):
            if _CLAIM_LINE.match(body[next_index]) or re.match(r"^ {0,3}#{1,6}[ \t]+", body[next_index]):
                break
            field = _FIELD_LINE.match(body[next_index])
            if field:
                last_field = field.group("key")
                fields[last_field] = field.group("value").strip()
            elif body[next_index].strip():
                if last_field:
                    fields[last_field] = (fields.get(last_field, "") + " " + body[next_index].strip()).strip()
                else:
                    continuation.append(body[next_index].strip())
            next_index += 1

        statement = " ".join([claim.group("text").strip(), *continuation]).strip()
        yield section_heading, claim.group("claim_id"), statement, fields
        index = next_index


def _parse_research_profile(path: Path, metadata: dict, body: list[str]) -> list[dict]:
    senator_id = _resolve_profile_senator_id(metadata, path)
    references = _parse_profile_references(body, path, senator_id)
    try:
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SenatorRecordError(f"Could not checksum {path.name}: {exc}") from exc

    common_name = metadata.get("common_name")
    display_name = common_name if isinstance(common_name, str) and common_name.strip() else str(metadata.get("full_name") or senator_id)
    output: list[dict] = []
    seen_claims: set[str] = set()
    for section_heading, claim_id, statement, fields in _profile_claim_blocks(body, path):
        if claim_id in seen_claims:
            raise SenatorRecordError(f"{path.name}: duplicate claim ID {claim_id}.")
        seen_claims.add(claim_id)
        evidence_status = fields.get("Evidence_Status", "UNSPECIFIED").strip().upper() or "UNSPECIFIED"
        reference_ids = list(dict.fromkeys(re.findall(r"SRC-[A-Z0-9-]+", fields.get("Sources", ""))))
        period = fields.get("Period", "").strip()

        raw_sources = [references.get(reference_id) for reference_id in reference_ids]
        all_sources_resolved = bool(reference_ids) and all(source is not None for source in raw_sources)
        provenance_complete = all_sources_resolved and all(
            source.get("_provenance_complete") for source in raw_sources if source is not None
        )
        claim_is_verified = evidence_status == "VERIFIED" and provenance_complete

        citation_sources = []
        for reference_id, raw_source in zip(reference_ids, raw_sources):
            source = dict(raw_source) if raw_source else {
                "source_id": f"{senator_id}:{reference_id}",
                "reference_id": reference_id,
                "title": f"Unresolved source {reference_id}",
                "issuing_body": "Unknown issuing body",
                "source_type": "other",
                "source_url": None,
                "publication_date": None,
                "retrieved_at": None,
                "locator": None,
                "verification_status": "candidate_source",
                "_provenance_complete": False,
            }
            source.pop("_provenance_complete", None)
            source["relevant_period"] = period or "Not specified"
            source["evidence_status"] = evidence_status
            source["verification_status"] = "verified" if claim_is_verified else "candidate_source"
            citation_sources.append(source)

        text_parts = [statement]
        for key, value in fields.items():
            if key.casefold() == "sources" or not value:
                continue
            text_parts.append(f"{key.replace('_', ' ')}: {value}")
        claim_text = normalize_text("\n\n".join(part for part in text_parts if part))
        if not claim_text:
            continue

        section_match = _PROFILE_SECTION.fullmatch(section_heading)
        section_name = section_match.group("name").replace("_", " ") if section_match else section_heading
        retrieved_dates = [source.get("retrieved_at") for source in citation_sources if source.get("retrieved_at")]
        chunks = _chunks(claim_text, CHUNK_SIZE, CHUNK_OVERLAP)
        for chunk_index, text in enumerate(chunks, start=1):
            digest = hashlib.sha256(
                f"{senator_id}\0{claim_id}\0{chunk_index}\0{text}".encode("utf-8")
            ).hexdigest()[:20]
            output.append({
                "schema_version": "2.1",
                "document_id": f"senator-record:{senator_id}",
                "source_document_id": metadata.get("document_id"),
                "chunk_id": f"{senator_id}:{claim_id}:{digest}",
                "chunk_index": len(output) + 1,
                "claim_id": claim_id,
                "senator_id": senator_id,
                "senator_ids": [senator_id],
                "senator_name": display_name,
                "section": section_name,
                "section_heading": section_heading,
                "title": f"{display_name} — {section_name}",
                "issuing_body": "SEN’TO curated senator record",
                "record_type": "senator_profile_claim",
                "source_type": "curated_summary",
                "source_url": None,
                "source_ids": [source["source_id"] for source in citation_sources],
                "citation_sources": citation_sources,
                "publication_date": None,
                "retrieved_at": max(retrieved_dates) if retrieved_dates else None,
                "relevant_period": period or "Not specified",
                "evidence_status": evidence_status,
                "verification_status": "verified" if claim_is_verified else "candidate_source",
                "profile_verification_status": metadata.get("verification_status"),
                "profile_research_depth": metadata.get("research_depth"),
                "profile_verification_note": metadata.get("verification_note"),
                "claim_metadata": fields,
                "locator": f"{path.name} > {section_heading} > {claim_id}",
                "source_file": path.name,
                "source_mime_type": "text/markdown",
                "source_sha256": source_sha256,
                "extraction_version": "senator-profile-markdown-1.2",
                "chunking_version": "claim-char-1200-overlap-180-v1",
                "content_trust": "untrusted_curated_record_text",
                "text": text,
            })
    return output


def _paragraphs(lines: list[str]) -> list[str]:
    text = "\n".join(lines)
    return [normalize_text(part) for part in re.split(r"\n\s*\n", text) if normalize_text(part)]


def parse_senator_markdown(path: Path) -> list[dict]:
    """Parse either the current researched-profile schema or the older numbered-reference format."""
    try:
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        raise SenatorRecordError(f"Could not read {path.name} as UTF-8: {exc}") from exc
    if lines:
        lines[0] = lines[0].lstrip("\ufeff")
    metadata, body = _read_frontmatter(lines, path)
    if metadata.get("record_status") == "reference_sample" or metadata.get(
        "ingestion_status"
    ) == "do_not_ingest_as_complete_profile":
        return []
    if metadata.get("document_type") == "senator_profile":
        return _parse_research_profile(path, metadata, body)

    senator_id = metadata.get("senator_id", "")
    if not _SLUG.fullmatch(senator_id):
        raise SenatorRecordError(f"{path.name}: senator_id must be a lowercase slug.")

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
