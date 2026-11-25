from pathlib import Path

import pytest

from ai.senator_markdown import (
    SENATOR_SECTIONS,
    SenatorRecordError,
    ingest_senator_records,
    parse_senator_markdown,
)


REFERENCE = (
    "[1] Official record title — Senate of the Philippines | source_type=official_record "
    "| publication_date=2026-02-03 | retrieved_at=2026-11-25 "
    "| relevant_period=20th Congress | locator=p. 12 "
    "| verification_status=verified | url=https://senate.gov.ph/record.pdf"
)


def make_profile(section_text="A recorded action is described in this source [1].", **overrides):
    metadata = {"senator_id": "sample-senator", **overrides}
    frontmatter = "---\n" + "\n".join(f"{key}: {value}" for key, value in metadata.items()) + "\n---\n"
    sections = []
    for section in SENATOR_SECTIONS:
        content = section_text if section == "Political_History" else "Not researched in this sample."
        sections.append(f"## {section}\n\n{content}")
    sections.append(f"## References\n\n{REFERENCE}")
    return frontmatter + "\n\n".join(sections) + "\n"


def test_parses_claim_and_attaches_reference_provenance(tmp_path):
    path = tmp_path / "sample-senator.md"
    path.write_text(make_profile(), encoding="utf-8")

    chunks = parse_senator_markdown(path)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["senator_id"] == "sample-senator"
    assert chunk["section"] == "Political_History"
    assert "recorded action" in chunk["text"]
    assert chunk["content_trust"] == "untrusted_curated_record_text"
    assert chunk["citation_sources"] == [{
        "source_id": "sample-senator:ref-1",
        "reference_id": "1",
        "title": "Official record title",
        "issuing_body": "Senate of the Philippines",
        "source_type": "official_record",
        "source_url": "https://senate.gov.ph/record.pdf",
        "publication_date": "2026-02-03",
        "retrieved_at": "2026-11-25",
        "relevant_period": "20th Congress",
        "locator": "p. 12",
        "verification_status": "verified",
    }]


def test_reference_sample_is_skipped(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "data/senator_records/francis-escudero.md"
    assert parse_senator_markdown(sample) == []
    assert ingest_senator_records(sample.parent) == []


def test_requires_all_sections_once_and_in_order(tmp_path):
    path = tmp_path / "broken.md"
    path.write_text(make_profile().replace("## Biography\n\nNot researched in this sample.\n\n", ""), encoding="utf-8")
    with pytest.raises(SenatorRecordError, match="missing required section"):
        parse_senator_markdown(path)


def test_rejects_claim_without_inline_reference(tmp_path):
    path = tmp_path / "unreferenced.md"
    path.write_text(make_profile("A claim without a reference."), encoding="utf-8")
    with pytest.raises(SenatorRecordError, match="needs at least one inline reference"):
        parse_senator_markdown(path)


def test_rejects_undefined_reference(tmp_path):
    path = tmp_path / "undefined.md"
    path.write_text(make_profile("A recorded action [2]."), encoding="utf-8")
    with pytest.raises(SenatorRecordError, match="undefined source"):
        parse_senator_markdown(path)


def test_rejects_unverified_source_and_non_https_url(tmp_path):
    path = tmp_path / "unverified.md"
    path.write_text(make_profile().replace("verification_status=verified", "verification_status=candidate"), encoding="utf-8")
    with pytest.raises(SenatorRecordError, match="only verified references"):
        parse_senator_markdown(path)

    path.write_text(make_profile().replace("https://senate.gov.ph", "http://senate.gov.ph"), encoding="utf-8")
    with pytest.raises(SenatorRecordError, match="HTTPS public URL"):
        parse_senator_markdown(path)


def test_publication_date_can_be_unavailable(tmp_path):
    path = tmp_path / "undated.md"
    path.write_text(make_profile().replace("publication_date=2026-02-03", "publication_date=not_stated"), encoding="utf-8")
    chunks = parse_senator_markdown(path)
    assert chunks[0]["citation_sources"][0]["publication_date"] is None
