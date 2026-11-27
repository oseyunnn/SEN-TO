"""Audit all 24 senator Markdown profiles for attribution, evidence status, and source integrity."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai.senator_markdown import parse_senator_markdown
from ai.validator import is_safe_source_url
from backend.senator_service import SenatorService

OFFICIAL_DOMAINS = (
    "senate.gov.ph",
    "legacy.senate.gov.ph",
    "web.senate.gov.ph",
    "congress.gov.ph",
    "officialgazette.gov.ph",
    "sc.judiciary.gov.ph",
    "elibrary.judiciary.gov.ph",
    "comelec.gov.ph",
    "coa.gov.ph",
    "ombudsman.gov.ph",
    "dbm.gov.ph",
    "pna.gov.ph",
    "pia.gov.ph",
    "gov.ph",
)

CREDIBLE_NEWS_DOMAINS = (
    "rappler.com",
    "inquirer.net",
    "newsinfo.inquirer.net",
    "philstar.com",
    "mb.com.ph",
    "abs-cbn.com",
    "news.abs-cbn.com",
    "gmanetwork.com",
    "manilatimes.net",
    "bworldonline.com",
    "pna.gov.ph",
    "reuters.com",
    "apnews.com",
    "verafiles.org",
    "pcij.org",
)

SHARED_SURNAME_GROUPS = {
    "cayetano": ("alan-peter-cayetano", "pia-cayetano"),
    "tulfo": ("erwin-tulfo", "raffy-tulfo"),
    "villar": ("camille-villar", "mark-villar"),
    "ejercito": ("jinggoy-ejercito-estrada", "joseph-victor-ejercito"),
}


def classify_source_reliability(url: str | None, source_type: str | None) -> str:
    if not url or not is_safe_source_url(url):
        return "inaccessible_or_invalid_url"
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS):
        return "official_government"
    if any(host == d or host.endswith("." + d) for d in CREDIBLE_NEWS_DOMAINS):
        return "credible_news_or_factcheck"
    if source_type == "research_organization":
        return "research_organization"
    return "secondary_or_other"


def check_attribution(senator_id: str, senator_name: str, text: str, source_title: str) -> tuple[str, str]:
    """Detect primary attribution vs surname collision or multi-senator mention."""
    combined = f"{text} {source_title}".casefold()
    surname = senator_name.split()[-1].casefold()
    if surname in {"iii", "iv", "jr."}:
        surname = senator_name.split()[-2].casefold()

    # Check shared-surname collisions
    for group_surname, peer_ids in SHARED_SURNAME_GROUPS.items():
        if senator_id in peer_ids:
            other_peers = [pid for pid in peer_ids if pid != senator_id]
            first_tokens = {
                "alan-peter-cayetano": ("alan", "alan peter"),
                "pia-cayetano": ("pia",),
                "erwin-tulfo": ("erwin",),
                "raffy-tulfo": ("raffy",),
                "camille-villar": ("camille",),
                "mark-villar": ("mark",),
                "jinggoy-ejercito-estrada": ("jinggoy", "estrada"),
                "joseph-victor-ejercito": ("jv", "joseph victor"),
            }
            own_hits = any(re.search(rf"\b{re.escape(t)}\b", combined) for t in first_tokens.get(senator_id, ()))
            peer_hits = any(
                re.search(rf"\b{re.escape(t)}\b", combined)
                for pid in other_peers
                for t in first_tokens.get(pid, ())
            )
            if peer_hits and not own_hits:
                return ("POTENTIAL_MISATTRIBUTION", f"Mentions sibling/namesake ({', '.join(other_peers)}) without own given name.")
            if peer_hits and own_hits:
                return ("JOINT_OR_SHARED_SURNAME", "Mentions both senator and shared-surname peer; verify primary subject.")

    if re.search(rf"\b{re.escape(surname)}\b", combined):
        return ("PRIMARY_SUBJECT", "Senator name/surname present in claim or source title.")
    return ("CONTEXTUAL_OR_IMPLICIT", "Claim appears in senator's file without explicit name repetition in chunk/title.")


def run_audit() -> dict:
    senators = SenatorService()
    records_dir = PROJECT_ROOT / "data" / "senator_records"
    name_by_id = {s["id"]: s["name"] for s in senators.senators}

    matrix: list[dict] = []
    url_to_senators: dict[str, set[str]] = defaultdict(set)
    status_counts = Counter()
    reliability_counts = Counter()
    attribution_counts = Counter()
    senator_summaries: dict[str, dict] = {}

    for path in sorted((*records_dir.glob("*.md"), *records_dir.glob("*.markdown"))):
        chunks = parse_senator_markdown(path)
        seen_claims: set[str] = set()
        for chunk in chunks:
            sid = chunk["senator_id"]
            sname = name_by_id.get(sid, sid)
            claim_id = chunk.get("claim_id") or chunk.get("chunk_id")
            if claim_id in seen_claims:
                continue
            seen_claims.add(claim_id)

            ev_status = str(chunk.get("evidence_status") or "UNSPECIFIED").upper()
            ver_status = str(chunk.get("verification_status") or "candidate_source")
            sources = chunk.get("citation_sources") or []
            status_counts[ev_status] += 1

            summary = senator_summaries.setdefault(
                sid,
                {
                    "senator_id": sid,
                    "senator_name": sname,
                    "file": path.name,
                    "claims": 0,
                    "verified_claims": 0,
                    "sources": 0,
                    "official_sources": 0,
                    "invalid_urls": 0,
                    "missing_pub_dates": 0,
                    "attribution_flags": 0,
                },
            )
            summary["claims"] += 1
            if ev_status == "VERIFIED" and ver_status == "verified":
                summary["verified_claims"] += 1

            if not sources:
                matrix.append({
                    "senator_id": sid,
                    "senator_name": sname,
                    "file": path.name,
                    "claim_id": claim_id,
                    "section": chunk.get("section", ""),
                    "source_url": "",
                    "source_title": "",
                    "attribution_status": "UNVERIFIED_NO_SOURCE",
                    "evidence_status": "UNSUPPORTED",
                    "source_reliability": "missing",
                    "publication_date": None,
                    "findings": "No citation source attached to claim.",
                    "recommended_action": "flag",
                })
                continue

            for src in sources:
                url = src.get("source_url") or ""
                title = src.get("title") or ""
                pub_date = src.get("publication_date") or src.get("publication_date_text")
                rel = classify_source_reliability(url, src.get("source_type"))
                attr_status, attr_note = check_attribution(sid, sname, chunk.get("text", ""), title)

                summary["sources"] += 1
                if rel == "official_government":
                    summary["official_sources"] += 1
                if rel == "inaccessible_or_invalid_url":
                    summary["invalid_urls"] += 1
                if not pub_date:
                    summary["missing_pub_dates"] += 1
                if attr_status == "POTENTIAL_MISATTRIBUTION":
                    summary["attribution_flags"] += 1

                if url:
                    url_to_senators[url].add(sid)
                reliability_counts[rel] += 1
                attribution_counts[attr_status] += 1

                findings = [attr_note]
                action = "retain"
                if rel == "inaccessible_or_invalid_url":
                    findings.append("URL missing or failed HTTPS validation.")
                    action = "replace_or_fix_url"
                if not pub_date:
                    findings.append("Publication date not stated.")
                if attr_status == "POTENTIAL_MISATTRIBUTION":
                    action = "review_attribution"
                elif ev_status != "VERIFIED":
                    action = "retain_with_status_label"

                matrix.append({
                    "senator_id": sid,
                    "senator_name": sname,
                    "file": path.name,
                    "claim_id": claim_id,
                    "section": chunk.get("section", ""),
                    "source_url": url,
                    "source_title": title[:160],
                    "attribution_status": attr_status,
                    "evidence_status": ev_status,
                    "source_reliability": rel,
                    "publication_date": pub_date,
                    "findings": " ".join(findings),
                    "recommended_action": action,
                })

    shared_urls = {url: sorted(sids) for url, sids in url_to_senators.items() if len(sids) > 1}
    return {
        "total_senators": len(senator_summaries),
        "total_matrix_rows": len(matrix),
        "evidence_status_counts": dict(status_counts),
        "source_reliability_counts": dict(reliability_counts),
        "attribution_counts": dict(attribution_counts),
        "shared_urls_across_senators": shared_urls,
        "senator_summaries": list(senator_summaries.values()),
        "matrix": matrix,
    }


def write_reports(audit: dict) -> None:
    (PROJECT_ROOT / "data" / "audit_matrix.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# SEN'TO Evidence & Attribution Audit Report",
        "",
        "Automated structural, attribution, and source-reliability audit across all 24 curated Markdown profiles in `data/senator_records/`.",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Senators audited:** {audit['total_senators']}",
        f"- **Claim-to-source matrix rows:** {audit['total_matrix_rows']}",
        f"- **Evidence status breakdown:** `{json.dumps(audit['evidence_status_counts'])}`",
        f"- **Source reliability breakdown:** `{json.dumps(audit['source_reliability_counts'])}`",
        f"- **Attribution checks:** `{json.dumps(audit['attribution_counts'])}`",
        f"- **URLs shared across multiple senators:** {len(audit['shared_urls_across_senators'])}",
        "",
        "## 2. Per-Senator Summary",
        "",
        "| Senator | File | Claims | Verified | Sources | Official (.gov.ph) | Invalid/Missing URLs | Missing Pub Dates | Attribution Flags |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in audit["senator_summaries"]:
        lines.append(
            f"| {s['senator_name']} | `{s['file']}` | {s['claims']} | {s['verified_claims']} | "
            f"{s['sources']} | {s['official_sources']} | {s['invalid_urls']} | {s['missing_pub_dates']} | {s['attribution_flags']} |"
        )

    flagged = [row for row in audit["matrix"] if row["attribution_status"] == "POTENTIAL_MISATTRIBUTION"]
    lines.extend([
        "",
        "## 3. Potential Attribution Flags (Shared Surnames / Namesakes)",
        "",
        f"Found **{len(flagged)}** claim-source rows where a shared-surname peer's given name appears without the file senator's given name:",
        "",
    ])
    for row in flagged[:40]:
        lines.append(
            f"- **{row['senator_name']}** (`{row['file']}`, `{row['claim_id']}`): {row['findings']} — *{row['source_title']}*"
        )
    if not flagged:
        lines.append("- None detected.")

    lines.extend([
        "",
        "## 4. Shared URLs Across Multiple Senators (Top 20)",
        "",
    ])
    for url, sids in list(audit["shared_urls_across_senators"].items())[:20]:
        lines.append(f"- `{url}` → {', '.join(sids)}")

    lines.extend([
        "",
        "## 5. Full Matrix",
        "",
        "The complete machine-readable claim-to-source validation matrix is saved at `data/audit_matrix.json`.",
        "",
    ])
    (PROJECT_ROOT / "docs" / "EVIDENCE_AUDIT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    result = run_audit()
    write_reports(result)
    print(json.dumps({
        "total_senators": result["total_senators"],
        "total_matrix_rows": result["total_matrix_rows"],
        "evidence_status_counts": result["evidence_status_counts"],
        "source_reliability_counts": result["source_reliability_counts"],
        "attribution_counts": result["attribution_counts"],
        "shared_urls_count": len(result["shared_urls_across_senators"]),
    }, indent=2))
