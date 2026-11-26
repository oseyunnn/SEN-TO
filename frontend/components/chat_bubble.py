import streamlit as st
from frontend.components.source_card import sources


def chat_bubble(message, key=None):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            response = message["response"]
            st.caption(response["label"])
            headings = {"legislation": "Look beyond a bill’s title.", "bills": "Authorship and sponsorship are different roles.", "education": "Start with the original record.", "committees": "Check the role and the date.", "votes": "Read the complete voting record.", "positions": "Follow the evidence.", "statements": "Context matters."}
            st.subheader(headings.get(response["topic"], "Explore the public record."))
            st.markdown(response["answer"])
            sources(response, key=key)
