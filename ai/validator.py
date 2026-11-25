"""Fail-closed citation integrity checks and source metadata formatting."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


_EVIDENCE_MARKER = re.compile(r"\[(E\d+)\]")
_ANY_EVIDENCE_MARKER = re.compile(r"\[E[^\]]*\]")


def is_safe_source_url(value: str | None) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = urlsplit(value)
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


class EvidenceValidator:
    """Validate that generated evidence markers resolve only to retrieved, verified sources."""

    def validate(self, answer: str, retrieved_documents: list[dict]) -> dict:
        if not isinstance(answer, str) or not answer.strip() or not retrieved_documents:
            return self._result("INSUFFICIENT_EVIDENCE", [], "No answer or evidence was available.")
        by_id = {
            item.get("evidence_id"): item
            for item in retrieved_documents
            if isinstance(item.get("evidence_id"), str)
        }
        markers = _EVIDENCE_MARKER.findall(answer)
        all_markers = _ANY_EVIDENCE_MARKER.findall(answer)
        if not markers or len(markers) != len(all_markers):
            return self._result("UNCITED_ANSWER", [], "The answer did not include valid evidence markers.")
        cited_ids = list(dict.fromkeys(markers))
        unknown = [item for item in cited_ids if item not in by_id]
        if unknown:
            return self._result("INVALID_CITATION", [], "The answer cited evidence that was not retrieved.")

        for evidence_id in cited_ids:
            document = by_id[evidence_id]
            sources = document.get("citation_sources")
            if document.get("verification_status") != "verified" or not isinstance(sources, list) or not sources:
                return self._result("UNVERIFIED_SOURCE", [], "Retrieved evidence did not have verified source metadata.")
            for source in sources:
                if (
                    not isinstance(source, dict)
                    or source.get("verification_status") != "verified"
                    or not is_safe_source_url(source.get("source_url"))
                ):
                    return self._result("INVALID_SOURCE", [], "A cited source failed provenance or URL checks.")
        return self._result(
            "CITATIONS_VALIDATED",
            cited_ids,
            "Citation IDs resolve to verified sources retrieved for this answer. This check does not prove semantic claim support.",
        )

    @staticmethod
    def _result(status: str, citation_ids: list[str], detail: str) -> dict:
        return {
            "status": status,
            "verified": False,
            "citation_ids": citation_ids,
            "semantic_support_checked": False,
            "detail": detail,
        }


def format_citations(documents: list[dict], citation_ids: list[str] | None = None) -> list[dict]:
    allowed_ids = set(citation_ids or [])
    citations: list[dict] = []
    seen: set[str] = set()
    for document in documents:
        evidence_id = document.get("evidence_id")
        if evidence_id not in allowed_ids:
            continue
        for source in document.get("citation_sources", []):
            source_id = str(source.get("source_id") or f"{document.get('chunk_id')}:{source.get('source_url')}")
            if source_id in seen:
                continue
            seen.add(source_id)
            url = source.get("source_url")
            citations.append({
                "citation_id": source_id,
                "evidence_id": evidence_id,
                "title": source.get("title", "Untitled source"),
                "issuing_body": source.get("issuing_body", "Unknown issuing body"),
                "source_type": source.get("source_type", "other"),
                "publication_date": source.get("publication_date"),
                "retrieved_at": source.get("retrieved_at"),
                "relevant_period": source.get("relevant_period", "Not specified"),
                "locator": source.get("locator", "Not specified"),
                "verification_status": source.get("verification_status", "unknown"),
                "url": url if is_safe_source_url(url) else None,
            })
    return citations
