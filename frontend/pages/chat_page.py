from html import escape
import streamlit as st
from frontend.components.senator_card import avatar, profile
from frontend.components.chat_bubble import chat_bubble


def render(service, chatbot):
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
        st.html(f'<div class="chat-heading">{avatar(senator)}<div><strong>{escape(senator["name"])}</strong><small>Public-record assistant · selected senator</small></div><span>AI ASSISTANT</span></div>')
        submitted = None
        if not history:
            st.html(f'<div class="welcome">{avatar(senator,"hero")}<div class="tricolor"><i></i><i></i><i></i></div><h1>Kilalanin ang Senador Mo!</h1><p>Ask questions and explore the public record<br>of {escape(senator["name"])}.</p><small>AI summaries of reviewed sources, not official statements or a senator’s own words. SEN’TO may not have records for every question.</small></div>')
            indexed_count = chatbot.indexed_passage_count()
            if indexed_count == 0:
                st.info("No reviewed passages are indexed yet. Add and review source records to enable source-backed answers.")
            elif indexed_count is None:
                st.info("The local evidence index could not be checked. A query will report if retrieval is unavailable.")
            else:
                st.caption(f"{indexed_count} reviewed evidence passage(s) are currently indexed.")
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
            with st.popover("▤  Dataset & profile"):
                st.write("Chat searches reviewed, indexed passages linked to the selected directory entry. A missing result means this dataset could not confirm the answer; it does not prove that no record exists.")
                st.caption("The directory entries are design examples; current office and affiliations are unverified.")
                profile(senator)
        st.html('<p class="fine-print">Unsupported questions receive a clear limitation. Every returned citation links to source metadata and a locator when available.</p>')
        if submitted or prompt:
            question = submitted or prompt
            with st.spinner("Checking source-backed records…"):
                result = chatbot.ask(question, senator["id"])
            history.extend([{"role": "user", "content": question}, {"role": "assistant", "response": result}])
            st.rerun()
