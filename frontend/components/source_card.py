import streamlit as st

from ai.validator import is_safe_source_url


_STATUS_LABELS = {
    "SOURCE-GROUNDED AI SUMMARY": "Citation links and provenance passed automated checks. Claim-level semantic support has not been independently verified.",
    "NO REVIEWED EVIDENCE": "No suitable reviewed passage was found. This does not mean no public record exists.",
    "ANSWER NOT VALIDATED": "The generated answer was withheld because it did not pass citation checks.",
    "RAG SERVICE UNAVAILABLE": "Retrieval or generation is unavailable. No generated answer was returned.",
    "NEUTRALITY LIMIT": "This request falls outside SEN’TO’s neutral public-record scope.",
}


def sources(response):
    citations = response.get("citations", [])
    label = response.get("label", "")

    with st.popover("▤  Sources & evidence"):
        st.caption(_STATUS_LABELS.get(label, "Source and evidence status is shown below."))
        if response.get("retrieval_count", 0):
            st.caption(f"Retrieved evidence passages: {response['retrieval_count']}")

        if citations:
            for citation in citations:
                st.markdown(f"**[{citation.get('evidence_id', 'E?')}] {citation.get('title', 'Untitled source')}**")
                st.write(citation.get("issuing_body", "Issuing body unavailable"))
                st.caption(
                    f"Type: {citation.get('source_type', 'unspecified')} · "
                    f"Published: {citation.get('publication_date') or 'date unavailable'} · "
                    f"Retrieved: {citation.get('retrieved_at') or 'date unavailable'}"
                )
                st.caption(
                    f"Period: {citation.get('relevant_period') or 'not specified'} · "
                    f"Locator: {citation.get('locator') or 'not specified'} · "
                    f"Source status: {citation.get('verification_status', 'unknown')}"
                )
                url = citation.get("url")
                if is_safe_source_url(url):
                    st.link_button("Open source", url)
                else:
                    st.caption("No validated source link is available.")
        else:
            st.info(response.get("limitation", "No source citations are attached to this response."))

        st.caption("SEN’TO summaries are generated explanations, not official Senate statements.")
