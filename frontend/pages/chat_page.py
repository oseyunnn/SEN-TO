from html import escape
import streamlit as st
from frontend.api import send_chat_message
from frontend.components.senator_card import avatar, profile
from frontend.components.chat_bubble import chat_bubble


@st.dialog("Dataset & profile", width="large")
def _dataset_profile(senator):
    st.write("The chat field is ready for source-backed search. When connected, requests will be scoped to the selected directory entry. A missing result will not prove that no public record exists.")
    st.caption("The directory names come from a dated official 20th Congress roster; profile facts and affiliations are unverified.")
    profile(senator)


def render(service):
    senator = service.get(st.session_state.senator_id)
    histories = st.session_state.histories
    history = histories.setdefault(senator["id"], [])
    # Streamlit sessions can survive a code reload; do not keep rendering the
    # old simulated answers after retiring that path.
    if any(
        message.get("role") == "assistant"
        and message.get("response", {}).get("label", "").startswith("SIMULATED")
        for message in history
    ):
        history.clear()
    with st.container(key="chat_panel"):
        st.html(f'<div class="chat-heading">{avatar(senator)}<div><strong>{escape(senator["name"])}</strong><small>Public record assistant · 20th Congress</small></div><span>AI ASSISTANT</span></div>')
        submitted = None
        with st.container(key="chat_content"):
            if not history:
                st.html(f'<div class="welcome">{avatar(senator,"hero")}<div class="tricolor"><i></i><i></i><i></i></div><h1>Kilalanin ang Senador Mo!</h1><p>Ask questions and explore the public record <br>of {escape(senator["name"])}.</p><small>When connected, SEN’TO will summarize reviewed sources. It does not speak for a senator, and its records may be incomplete.</small></div>')
                with st.container(key="suggestions"):
                    questions = service.suggestions(senator["id"])
                    labels = ["What bills has this senator authored?", "What committees does this senator serve on?", "What are this senator’s documented positions?", "Explore this senator’s legislative contributions"]
                    for i in (0, 2):
                        columns = st.columns(2)
                        for offset, col in enumerate(columns):
                            with col:
                                question = questions[i + offset]
                                if st.button(labels[i+offset], key=f"suggest_{senator['id']}_{i+offset}", use_container_width=True):
                                    submitted = question
                st.html('<p class="start-hint">Start with a question. Follow the evidence.</p>')
            else:
                with st.container(height=470, border=False, key="conversation"):
                    for message in history:
                        chat_bubble(message)
                st.html('<div class="disclaimer">Review each citation and its locator. The indexed records may be incomplete, and summaries are not official statements.</div>')
        with st.container(key="composer"):
            prompt = st.chat_input("Ask anything about this senator…", key="chat_prompt", max_chars=4000)
            if st.button("▤  Dataset & profile", key="dataset_profile"):
                _dataset_profile(senator)
        st.html('<p class="fine-print">Unsupported questions receive a clear limitation. Every returned citation links to source metadata and a locator when available.</p>')
        if submitted or prompt:
            question = submitted or prompt
            with st.spinner("Preparing your question…"):
                result = send_chat_message(senator["id"], question)
            history.extend([{"role": "user", "content": question}, {"role": "assistant", "response": result}])
            st.rerun()
