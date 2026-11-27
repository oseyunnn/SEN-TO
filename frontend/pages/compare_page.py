from html import escape

import streamlit as st

from ai.validator import is_safe_source_url
from backend.comparison_service import COMPARISON_CATEGORIES, PERIODS
from frontend.api import get_comparison_records
from frontend.components.senator_card import avatar


def _source_link(source, index):
    title = escape(str(source.get("title") or "Source title unavailable"))
    issuer = escape(str(source.get("issuing_body") or "Issuing body unavailable"))
    publication_date = escape(str(source.get("publication_date") or source.get("publication_date_text") or "publication date unavailable"))
    retrieval_date = escape(str(source.get("retrieved_at") or "retrieval date unavailable"))
    locator = escape(str(source.get("locator") or "locator unavailable"))
    verification = "verified provenance" if source.get("verification_status") == "verified" else "candidate source"
    source_type = {
        "government_publication": "Government publication",
        "secondary_news": "News report",
        "research_organization": "Research organization",
        "other": "Other source",
    }.get(source.get("source_type"), "Source type unavailable")
    source_type = escape(source_type)
    url = source.get("source_url")
    label = f"Source {index}: {title}"
    link = (
        f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{label} ↗</a>'
        if is_safe_source_url(url)
        else f'<span>{label} · no validated source link</span>'
    )
    return (
        '<div class="comparison-source">'
        f'{link}<small>{escape(verification)} · {source_type} · {issuer} · published {publication_date} · '
        f'retrieved {retrieval_date} · {locator}</small>'
        '</div>'
    )


def _claim_html(claim):
    statement = escape(str(claim.get("text") or "Claim text unavailable."))
    period = escape(str(claim.get("period") or "Period not stated"))
    details = "".join(
        f'<p class="comparison-detail"><strong>{escape(str(item["label"]))}:</strong> '
        f'{escape(str(item["value"]))}</p>'
        for item in claim.get("details", [])
    )
    sources = "".join(
        _source_link(source, index)
        for index, source in enumerate(claim.get("sources", []), start=1)
    )
    return (
        '<article class="comparison-claim">'
        f'<p>{statement}</p>{details}'
        f'<div class="comparison-claim-meta"><span>Period: {period}</span>'
        '<span class="comparison-verified">VERIFIED</span></div>'
        f'{sources}</article>'
    )


def _category_cell(record, category_key):
    section = record["sections"][category_key]
    name = escape(str(record["senator"]["name"]))
    claims = section["claims"]
    count = len(claims)
    summary = f'<p class="comparison-coverage">{count} verified {"record" if count == 1 else "records"} in this window.</p>'
    if not claims:
        summary += '<p class="comparison-gap">No verified record is present in these files for this category and period. This gap does not show that no activity occurred.</p>'
    if section["verified_outside_period"]:
        outside = section["verified_outside_period"]
        summary += f'<p class="comparison-gap">{outside} verified {"record is" if outside == 1 else "records are"} in other periods.</p>'
    if section["not_verified_count"]:
        pending = section["not_verified_count"]
        summary += f'<p class="comparison-gap">{pending} other {"claim is" if pending == 1 else "claims are"} not shown because the evidence status or source provenance is not VERIFIED and complete.</p>'
    return (
        f'<div class="comparison-cell"><span class="mobile-person">{name}</span>'
        f'{summary}{"".join(_claim_html(claim) for claim in claims)}</div>'
    )


@st.dialog("Sources used in this comparison", width="large")
def _comparison_sources(records):
    st.caption("Sources below support the displayed VERIFIED claims. The issuing body and locator are shown for each reference.")
    seen = set()
    source_index = 0
    for record in records:
        for section in record["sections"].values():
            for claim in section["claims"]:
                for source in claim.get("sources", []):
                    source_id = source.get("source_id")
                    if not source_id or source_id in seen:
                        continue
                    seen.add(source_id)
                    source_index += 1
                    st.html(
                        f'<article class="source-detail-card"><h2>{escape(str(record["senator"]["name"]))} · '
                        f'{escape(str(source.get("title") or "Source title unavailable"))}</h2>'
                        f'<p>{escape(str(source.get("issuing_body") or "Issuing body unavailable"))} · '
                        f'{escape(str(source.get("publication_date") or "publication date unavailable"))} · '
                        f'{escape(str(source.get("relevant_period") or claim.get("period") or "Period not stated"))}</p>'
                        f'<p class="source-detail-meta">Locator: {escape(str(source.get("locator") or "not stated"))}</p>'
                        f'{_source_link(source, source_index)}</article>'
                    )
    if not seen:
        st.info("No source-complete VERIFIED claims are available for the selected senators and period.")


def render(service):
    if st.session_state.get("comparison_count") not in (2, 3):
        st.session_state.comparison_count = 3
    count = st.session_state.get("comparison_count", 3)
    period_key = st.session_state.get("comparison_period", "20th_congress")
    if period_key not in PERIODS:
        period_key = "20th_congress"
        st.session_state.comparison_period = period_key

    with st.container(key="compare_panel"):
        st.html(
            '<div class="compare-heading"><h1>Compare Senators</h1>'
            '<p>Explore the same public-record categories side by side, with source and period details.</p></div>'
        )
        with st.container(key="compare_toolbar"):
            period, links, note = st.columns([284, 672, 300], gap="small")
            with period:
                period_label = "20th Congress · through 25 Nov 2026" if period_key == "20th_congress" else "All periods · through 25 Nov 2026"
                with st.popover(period_label):
                    count = st.radio("Number of senators", [2, 3], horizontal=True, key="comparison_count")
                    st.radio(
                        "Record period",
                        ["20th_congress", "all_periods"],
                        format_func=lambda value: "20th Congress (2025–2026 cutoff)" if value == "20th_congress" else "All researched periods",
                        key="comparison_period",
                    )
                    st.caption("Research files are dated through 25 November 2026. Claims keep their own period labels; where a file gives only a year, the window can only be matched at year precision.")
            with links:
                nav_labels = {
                    "background": "Profile",
                    "legislation": "Bills",
                    "committees": "Committees",
                    "votes": "Votes",
                    "positions": "Positions",
                    "disclosures": "Disclosures",
                    "accountability": "Accountability",
                    "performance": "Performance",
                }
                nav_items = [(key, nav_labels[key]) for key in COMPARISON_CATEGORIES]
                source_link = '<a href="?view=compare&amp;sources=1" target="_self">Sources</a>'
                st.html(
                    '<nav class="compare-links" aria-label="Comparison sections">'
                    + "".join(f'<a href="?view=compare#compare-{key}" target="_self">{escape(label)}</a>' for key, label in nav_items)
                    + source_link
                    + "</nav>"
                )
            with note:
                st.html('<p class="compare-note">No rankings or endorsements · gaps stay visible</p>')

        ids = [senator["id"] for senator in service.senators]
        stored_ids = list(st.session_state.get("compare_ids", []))
        chosen = []
        for senator_id in stored_ids:
            if senator_id in ids and senator_id not in chosen:
                chosen.append(senator_id)
            if len(chosen) == count:
                break
        for senator_id in ids:
            if len(chosen) == count:
                break
            if senator_id not in chosen:
                chosen.append(senator_id)

        with st.container(key="compare_selectors"):
            for index, column in enumerate(st.columns(count, gap="large")):
                with column:
                    options = [sid for sid in ids if sid not in chosen or sid == chosen[index]]
                    selected = st.selectbox(
                        f"Senator {index + 1}",
                        options,
                        index=options.index(chosen[index]),
                        format_func=lambda sid: service.get(sid)["name"],
                        key=f"compare_select_{index}",
                        label_visibility="collapsed",
                    )
                    if selected != chosen[index]:
                        new_ids = chosen.copy()
                        new_ids[index] = selected
                        st.session_state.compare_ids = new_ids + [sid for sid in ids if sid not in new_ids][:3 - len(new_ids)]
                        st.rerun()
        st.session_state.compare_ids = chosen + [sid for sid in ids if sid not in chosen][:3 - len(chosen)]

        records = get_comparison_records(service, chosen, period=period_key)
        if st.session_state.pop("show_compare_sources", False):
            _comparison_sources(records)

        people = "".join(
            '<div class="comparison-person">'
            + avatar(record["senator"], "large")
            + f'<h3>{escape(str(record["senator"]["name"]))}</h3>'
            + f'<p>{escape(str(record["period"]))}</p>'
            + f'<p>{record["verified_claim_count"]} verified records · {record["source_count"]} sources · '
            + f'research status: {escape(str(record["research_status"]))} · '
            + f'coverage: {escape(str(record["research_depth"]))}</p>'
            + (
                f'<details class="comparison-research-note"><summary>Profile research note</summary>'
                f'<p>{escape(str(record["research_note"]))}</p></details>'
                if record.get("research_note") else ""
            )
            + '</div>'
            for record in records
        )
        rows = []
        for key, category in COMPARISON_CATEGORIES.items():
            cells = "".join(_category_cell(record, key) for record in records)
            rows.append(
                f'<section class="comparison-section" id="compare-{key}">'
                f'<h3>{escape(category["title"])}</h3>'
                f'<div class="comparison-grid">{cells}</div></section>'
            )
        st.html(
            f'<div class="comparison-scroll" role="region" aria-label="Side-by-side senator records" tabindex="0" style="--count:{count}">'
            '<div class="compare-data-note">Only claims marked VERIFIED with complete source provenance are shown. '
            'Other draft claims are counted as gaps; missing data does not mean no record exists.</div>'
            + f'<div class="comparison-grid comparison-portraits">{people}</div>{"".join(rows)}</div>'
        )
