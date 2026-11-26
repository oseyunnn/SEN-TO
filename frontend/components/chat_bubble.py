import time

import streamlit as st
from frontend.components.source_card import sources


def _answer_chunks(answer):
    chunk_size = 28
    chunk_count = max(1, (len(answer) + chunk_size - 1) // chunk_size)
    pause = min(0.025, 1.5 / chunk_count)
    for index in range(0, len(answer), chunk_size):
        yield answer[index:index + chunk_size]
        if index + chunk_size < len(answer):
            time.sleep(pause)


def chat_bubble(message, key=None):
    key = key or "chat_sources"
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            response = message["response"]
            st.caption(response["label"])
            headings = {"legislation": "Look beyond a bill’s title.", "bills": "Authorship and sponsorship are different roles.", "education": "Start with the original record.", "committees": "Check the role and the date.", "votes": "Read the complete voting record.", "positions": "Follow the evidence.", "statements": "Context matters."}
            st.subheader(headings.get(response["topic"], "Explore the public record."))
            if message.get("animate_answer"):
                with st.container(key=f"answer_reveal_{key}"):
                    st.write_stream(_answer_chunks(response["answer"]), cursor="▍")
                message["animate_answer"] = False
            else:
                st.markdown(response["answer"])
            sources(response, key=key)
