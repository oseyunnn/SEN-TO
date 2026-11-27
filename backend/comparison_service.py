"""Build fair, source-linked senator comparisons from the curated Markdown records."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path
import re

from ai.senator_markdown import parse_senator_markdown
from backend.senator_service import DATA, SenatorService


RESEARCH_CUTOFF = "2026-11-25"
CONGRESS_START = "2025-05-17"
PERIODS = {
    "20th_congress": f"20th Congress records · {CONGRESS_START} to {RESEARCH_CUTOFF}",
    "all_periods": f"All researched periods · through {RESEARCH_CUTOFF}",
}

# Every selected senator is shown against the same set of categories.
COMPARISON_CATEGORIES = {
    "background": {
        "title": "Background & public service",
        "sections": ("Biography", "Political History", "Public Service"),
    },
    "legislation": {
        "title": "Bills & legislative record",
        "sections": ("Legislative Authorship", "Laws and Accomplishments"),
    },
    "committees": {
        "title": "Current roles & committees",
        "sections": ("Current Position",),
    },
    "votes": {
        "title": "Recorded votes",
        "sections": ("Voting Records",),
    },
    "positions": {
        "title": "Policy positions & public statements",
        "sections": ("Policy Standpoints", "Public Statements"),
    },
    "disclosures": {
        "title": "Financial disclosures",
        "sections": ("Financial Disclosures",),
    },
    "accountability": {
        "title": "Controversies & accountability records",
        "sections": ("Graft and Corruption", "Controversies"),
    },
    "performance": {
        "title": "Historical performance records",
        "sections": ("Historical Performance",),
    },
}

_STANDARD_METADATA = {"period", "evidence_status", "sources"}


def _record_snapshot(records_dir: Path) -> tuple[tuple[str, int, int], ...]:
    snapshot = []
    for path in sorted((*records_dir.glob("*.md"), *records_dir.glob("*.markdown"))):
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(snapshot)


@lru_cache(maxsize=4)
def _load_profile_claims(snapshot: tuple[tuple[str, int, int], ...]) -> dict[str, list[dict]]:
    claims_by_senator: dict[str, dict[str, dict]] = defaultdict(dict)
    for filename, _, _ in snapshot:
        for chunk in parse_senator_markdown(Path(filename)):
            senator_id = chunk["senator_id"]
            claim_id = chunk.get("claim_id") or chunk["chunk_id"]
            key = f"{senator_id}:{claim_id}"
            claim = claims_by_senator[senator_id].get(key)
            if claim is None:
                metadata = dict(chunk.get("claim_metadata") or {})
                claim = {
                    "claim_id": claim_id,
                    "section": chunk.get("section", ""),
                    "evidence_status": str(chunk.get("evidence_status", "UNSPECIFIED")).upper(),
                    "verification_status": chunk.get("verification_status", "candidate_source"),
                    "period": metadata.get("Period") or chunk.get("relevant_period") or "Period not stated",
                    "metadata": metadata,
                    "texts": [],
                    "sources": [],
                    "profile_verification_status": chunk.get("profile_verification_status"),
                    "profile_research_depth": chunk.get("profile_research_depth"),
                    "profile_verification_note": chunk.get("profile_verification_note"),
                }
                claims_by_senator[senator_id][key] = claim
            claim["texts"].append(chunk.get("text", ""))
            for source in chunk.get("citation_sources", []):
                source_key = source.get("source_id") or source.get("reference_id")
                if source_key and all(item.get("source_id") != source_key for item in claim["sources"]):
                    claim["sources"].append(source)

    result: dict[str, list[dict]] = {}
    for senator_id, grouped in claims_by_senator.items():
        result[senator_id] = []
        for claim in grouped.values():
            claim["text"] = _join_claim_chunks(claim.pop("texts"), claim["metadata"])
            claim["details"] = [
                {"label": _display_label(key), "value": value}
                for key, value in claim["metadata"].items()
                if key.casefold() not in _STANDARD_METADATA and value
            ]
            result[senator_id].append(claim)
    return result


def _display_label(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _join_claim_chunks(chunks: list[str], metadata: dict) -> str:
    """Reassemble a long parsed claim while removing importer-added metadata lines."""
    cleaned = []
    generated_lines = {
        f"{key.replace('_', ' ')}: {value}".casefold()
        for key, value in metadata.items()
        if value
    }
    for chunk in chunks:
        lines = [line for line in str(chunk).splitlines() if line.strip().casefold() not in generated_lines]
        cleaned.append("\n".join(lines).strip())

    joined = ""
    for piece in cleaned:
        if not piece:
            continue
        if not joined:
            joined = piece
            continue
        overlap = min(180, len(joined), len(piece))
        while overlap and joined[-overlap:] != piece[:overlap]:
            overlap -= 1
        joined += piece[overlap:]
    return joined.strip()


def _matches_congress_window(period: str) -> bool:
    """Match a period to 2025–2026, using year precision when dates are vague."""
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", period)
    has_present = bool(re.search(r"\b(present|current|ongoing)\b", period, re.IGNORECASE))
    start = date.fromisoformat(CONGRESS_START)
    end = date.fromisoformat(RESEARCH_CUTOFF)
    if len(dates) >= 2:
        try:
            period_start = min(date.fromisoformat(value) for value in dates)
            period_end = max(date.fromisoformat(value) for value in dates)
            return period_start <= end and period_end >= start
        except ValueError:
            pass
    if len(dates) == 1 and (has_present or len(set(re.findall(r"\b(?:19|20)\d{2}\b", period))) == 1):
        try:
            period_start = date.fromisoformat(dates[0])
            period_end = end if has_present else period_start
            return period_start <= end and period_end >= start
        except ValueError:
            pass

    years = [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", period)]
    if not years:
        return False
    return min(years) <= 2026 and max(years) >= 2025


_STATUS_RANK = {
    "VERIFIED": 0,
    "OFFICIAL_STATEMENT": 2,
    "PARTIALLY_VERIFIED": 2,
    "DOCUMENTED": 2,
    "PENDING_INVESTIGATION": 3,
    "CONTESTED": 3,
    "DISPUTED": 3,
    "ALLEGED": 3,
    "UNVERIFIED": 4,
    "UNSPECIFIED": 5,
}


def _claim_sort_key(indexed_claim: tuple[int, dict]) -> tuple[int, int]:
    """Rank verified claims with verified provenance first, then other documented statuses."""
    index, claim = indexed_claim
    evidence_status = str(claim.get("evidence_status") or "UNSPECIFIED").upper()
    verification_status = str(claim.get("verification_status") or "").lower()
    if evidence_status == "VERIFIED" and verification_status == "verified":
        rank = 0
    elif evidence_status == "VERIFIED":
        rank = 1
    else:
        rank = _STATUS_RANK.get(evidence_status, 4)
    return (rank, index)


class ComparisonService:
    def __init__(self, senators=None, records_dir: Path | None = None):
        self.senators = senators or SenatorService()
        self.records_dir = records_dir or DATA / "senator_records"

    def compare(self, ids, period="20th_congress"):
        if len(ids) not in (2, 3) or len(set(ids)) != len(ids):
            raise ValueError("Choose two or three different senators.")
        if period not in PERIODS:
            raise ValueError("Choose a supported comparison period.")

        snapshot = _record_snapshot(self.records_dir)
        claims_by_senator = _load_profile_claims(snapshot)
        output = []
        for senator_id in ids:
            senator = self.senators.get(senator_id)
            claims = claims_by_senator.get(senator_id, [])
            sections = {}
            for category_key, category in COMPARISON_CATEGORIES.items():
                category_claims = [
                    claim for claim in claims
                    if claim["section"] in category["sections"]
                ]
                if period == "20th_congress":
                    window_claims = [
                        claim for claim in category_claims
                        if _matches_congress_window(claim["period"])
                    ]
                else:
                    window_claims = list(category_claims)
                shown_claims = [
                    claim for _, claim in sorted(enumerate(window_claims), key=_claim_sort_key)
                ]
                verified_in_window = [
                    claim for claim in shown_claims
                    if claim["evidence_status"] == "VERIFIED"
                    and claim["verification_status"] == "verified"
                ]
                verified_all = [
                    claim for claim in category_claims
                    if claim["evidence_status"] == "VERIFIED"
                    and claim["verification_status"] == "verified"
                ]
                sections[category_key] = {
                    "title": category["title"],
                    "claims": shown_claims,
                    "verified_count": len(verified_in_window),
                    "outside_period_count": len(category_claims) - len(shown_claims),
                    "verified_outside_period": len(verified_all) - len(verified_in_window),
                    "not_verified_count": len(shown_claims) - len(verified_in_window),
                }

            all_sources = {
                source.get("source_id"): source
                for section in sections.values()
                for claim in section["claims"]
                for source in claim["sources"]
                if source.get("source_id")
            }
            profile_claim = next((claim for claim in claims if claim.get("profile_verification_status")), {})
            output.append({
                "senator": senator,
                "period": PERIODS[period],
                "research_status": profile_claim.get("profile_verification_status") or "not stated",
                "research_depth": profile_claim.get("profile_research_depth") or "not stated",
                "research_note": profile_claim.get("profile_verification_note") or "",
                "sections": sections,
                "total_claim_count": sum(len(section["claims"]) for section in sections.values()),
                "verified_claim_count": sum(section["verified_count"] for section in sections.values()),
                "source_count": len(all_sources),
            })
        return output
