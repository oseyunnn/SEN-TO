import streamlit as st


def sources(response):
    reference, status = st.columns([268, 628])
    with reference:
        with st.popover('▤  Demonstration references'):
            st.write(f"Retrieval: {response['retrieval_count']} local demonstration record(s)")
            st.caption(f"Evidence: {response['validation']['status']} · Real-world status: UNVERIFIED_DEMO")
            for citation in response['citations']:
                st.write(f"{citation['document_id']} · {citation['title']}")
                st.caption('Simulation · Publication date unavailable · Not an official citation')
                if citation['url']:
                    st.link_button('Open source', citation['url'])
            st.info(response['limitation'])
    with status:
        st.html('<div class="evidence-badge">Record not yet confirmed</div>')
