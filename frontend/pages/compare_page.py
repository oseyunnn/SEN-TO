from html import escape
import streamlit as st
from backend.senator_service import SECTIONS
from frontend.components.senator_card import avatar


def render(service, comparison):
    with st.container(key="compare_panel"):
        st.html('<div class="compare-heading"><h1>Compare Senators</h1><p>Explore legislative records, backgrounds, and documented positions side by side.</p></div>')
        with st.container(key="compare_toolbar"):
            period, links, note = st.columns([284, 672, 300], gap="small")
            with period:
                with st.popover("20th Congress · 2025–2028"):
                    count = st.radio("Number of senators", [2, 3], horizontal=True, key="comparison_count")
                    st.session_state.saved_comparison_count = count
                    st.caption("Directory examples; Senate and Minority Bloc membership are unverified. Missing information does not imply inactivity.")
            with links:
                st.html('<nav class="compare-links" aria-label="Comparison sections">' + ''.join(
                    f'<a href="#compare-{key}" target="_self">{label}</a>' for key, label in
                    [("education", "Education"), ("bills", "Bills"), ("committees", "Committees"), ("votes", "Votes"), ("statements", "Statements"), ("positions", "Issues"), ("sources", "Sources")]) + '</nav>')
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
        records = comparison.compare(chosen)
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
        st.html(f'<div class="comparison-scroll" style="--count:{count}"><div class="comparison-grid comparison-portraits">{people}</div>{"".join(rows)}</div>')
