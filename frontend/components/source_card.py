from html import escape
import streamlit as st

from ai.validator import is_safe_source_url


_STATUS_LABELS = {
    "SOURCE-GROUNDED AI SUMMARY": "Citation links and provenance passed automated checks. Claim-level semantic support has not been independently verified.",
    "NO REVIEWED EVIDENCE": "No suitable reviewed passage was found. This does not mean no public record exists.",
    "ANSWER NOT VALIDATED": "The generated answer was withheld because it did not pass citation checks.",
    "RAG SERVICE UNAVAILABLE": "Retrieval or generation is unavailable. No generated answer was returned.",
    "NEUTRALITY LIMIT": "This request falls outside SEN’TO’s neutral public-record scope.",
    "BACKEND CONNECTION PLACEHOLDER": "The frontend is ready to connect to a source-backed chat endpoint. No source lookup was performed.",
}


@st.dialog("Follow the original record", width="large")
def _source_details(response):
    citations = response.get("citations", [])
    label = response.get("label", "")
    st.caption(_STATUS_LABELS.get(label, "Source and evidence status is shown below."))
    st.caption("AI explanations are not official statements.")
    if response.get("retrieval_count", 0):
        st.caption(f"Retrieved evidence passages: {response['retrieval_count']}")

    if citations:
        for index, citation in enumerate(citations):
            title = escape(str(citation.get("title", "Untitled source")))
            evidence_id = escape(str(citation.get("evidence_id", f"E{index + 1}")))
            issuing_body = escape(str(citation.get("issuing_body", "Issuing body unavailable")))
            source_type = escape(str(citation.get("source_type", "unspecified")))
            publication_date = escape(str(citation.get("publication_date") or "date unavailable"))
            retrieved_at = escape(str(citation.get("retrieved_at") or "date unavailable"))
            relevant_period = escape(str(citation.get("relevant_period") or "not specified"))
            locator = escape(str(citation.get("locator") or "not specified"))
            verification_status = escape(str(citation.get("verification_status", "unknown")))
            url = citation.get("url")
            if is_safe_source_url(url):
                link = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">Open original document ↗</a>'
            else:
                link = '<span class="source-detail-unavailable">No validated source link is available.</span>'
            st.html(
                f'<article class="source-detail-card"><h2>{evidence_id} · {title}</h2>'
                f'<p class="source-detail-meta">{issuing_body} · Publication date {publication_date}</p>'
                f'<p>Type: {source_type} · Retrieved: {retrieved_at}</p>'
                f'<p>Period: {relevant_period} · Locator: {locator} · Status: {verification_status}</p>'
                f'{link}</article>'
            )
    else:
        st.info(response.get("limitation", "No source citations are attached to this response."))

    st.caption("Incomplete or conflicting evidence should remain visibly qualified.")


def sources(response):
    if st.button("▤  Sources & evidence"):
        _source_details(response)
