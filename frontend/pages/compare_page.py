from html import escape
import streamlit as st
from ai.validator import is_safe_source_url
from backend.senator_service import SECTIONS
from frontend.api import get_comparison_records
from frontend.components.senator_card import avatar


@st.dialog("Comparison sources", width="large")
def _comparison_sources(records):
    st.caption("Education and membership only. Other fields remain unconfirmed.")
    available_sources = 0
    for record in records:
        senator_name = escape(str(record["senator"]["name"]))
        for section_key, field in record.get("sections", {}).items():
            if not isinstance(field, dict):
                continue
            for source in field.get("sources", []):
                if not isinstance(source, dict):
                    continue
                source_scope = source.get("category", section_key)
                if source_scope not in ("education", "membership"):
                    continue
                available_sources += 1
                section_title = "Senate membership" if source_scope == "membership" else SECTIONS.get(section_key, "Education")
                title = escape(str(source.get("title") or section_title))
                issuing_body = escape(str(source.get("issuing_body") or "Issuing body unavailable"))
                publication_date = escape(str(source.get("publication_date") or "date unavailable"))
                url = source.get("url")
                link = (
                    f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
                    "Open original document ↗</a>"
                    if is_safe_source_url(url)
                    else '<span class="source-detail-unavailable">No validated source link is available.</span>'
                )
                st.html(
                    f'<article class="source-detail-card"><h2>{senator_name} · {title}</h2>'
                    f'<p>{issuing_body} · {publication_date}</p>{link}</article>'
                )
    if not available_sources:
        st.info("No verified government source is connected to this prototype.")


def render(service):
    with st.container(key="compare_panel"):
        st.html('<div class="compare-heading"><h1>Compare Senators</h1><p>Explore legislative records, backgrounds, and documented positions side by side.</p></div>')
        with st.container(key="compare_toolbar"):
            period, links, note = st.columns([284, 672, 300], gap="small")
            with period:
                with st.popover("20th Congress · 2025–2028"):
                    count = st.radio("Number of senators", [1, 2, 3], horizontal=True, key="comparison_count")
                    st.session_state.saved_comparison_count = count
                    st.caption("Official Senate roster source dated 28 July 2025. Comparison profile facts and Minority Bloc membership remain unverified; missing information does not imply inactivity.")
            with links:
                nav_items = [("education", "Education"), ("bills", "Bills"), ("committees", "Committees"),
                             ("votes", "Votes"), ("statements", "Statements"), ("positions", "Issues")]
                source_link = '<a href="?view=compare&amp;sources=1" target="_self">Sources</a>'
                st.html('<nav class="compare-links" aria-label="Comparison sections">' + ''.join(
                    f'<a href="#compare-{key}" target="_self">{label}</a>' for key, label in nav_items
                ) + source_link + '</nav>')
            with note:
                st.html('<p class="compare-note">No rankings. No endorsements. Just the public record.</p>')
        ids = [s["id"] for s in service.senators]
        chosen = st.session_state.compare_ids[:count]
        with st.container(key="compare_selectors"):
            for i, col in enumerate(st.columns(count, gap="large")):
                with col:
                    options = [sid for sid in ids if sid not in chosen or sid == chosen[i]]
                    selected = st.selectbox(f"Senator {i+1}", options, index=options.index(chosen[i]),
                                            format_func=lambda sid: service.get(sid)["name"], key=f"compare_select_{i}", label_visibility="collapsed")
                    if selected != chosen[i]:
                        st.session_state.compare_ids[i] = selected
                        if len(set(st.session_state.compare_ids)) < 3:
                            st.session_state.compare_ids[2] = next(s for s in ids if s not in st.session_state.compare_ids[:2])
                        st.rerun()
        records = get_comparison_records(service, chosen)
        if st.session_state.pop("show_compare_sources", False):
            _comparison_sources(records)
        people = ''.join(f'<div class="comparison-person">{avatar(r["senator"], "large")}<h3>{escape(r["senator"]["name"])}</h3><p>Senator · 20th Congress</p></div>' for r in records)
        rows = []
        for key in ["education", "legislation", "career", "bills", "committees", "votes", "statements", "positions", "sources"]:
            cells = []
            for record in records:
                field = record["sections"].get(key)
                content = "No verified government source is connected to this prototype." if field is None else field["content"]
                if key in ("legislation", "bills") and field["status"] == "not_available":
                    content = "Authored / sponsored bills & resolutions<br>No verified record available.<br>Legislative status not established in this prototype."
                else:
                    content = escape(content)
                cells.append(f'<div class="comparison-cell"><span class="mobile-person">{escape(record["senator"]["name"])}</span><p>{content}</p><small>Demonstration dataset · unverified</small></div>')
            rows.append(f'<section class="comparison-section" id="compare-{key}"><h3>{SECTIONS.get(key, "Available sources")}</h3><div class="comparison-grid">{"".join(cells)}</div></section>')
        st.html(f'<div class="comparison-scroll" role="region" aria-label="Side-by-side senator records" tabindex="0" style="--count:{count}"><div class="comparison-grid comparison-portraits">{people}</div>{"".join(rows)}</div>')
