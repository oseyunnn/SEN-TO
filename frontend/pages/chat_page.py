from html import escape
import streamlit as st
from backend.security import (
    MAX_SESSION_REQUESTS,
    SESSION_REQUEST_WINDOW_SECONDS,
    allow_session_request,
    bulk_retrieval_refusal,
    bulk_retrieval_limitation,
    internal_prompt_refusal,
    internal_prompt_limitation,
    normalize_question,
    requests_bulk_retrieval,
    requests_internal_prompt,
)
from frontend.api import send_chat_message, get_chatbot_service
from frontend.components.senator_card import avatar, profile
from frontend.components.chat_bubble import chat_bubble


@st.dialog("Dataset & profile", width="large")
def _dataset_profile(senator):
    st.write("Chat searches reviewed, indexed sources for the selected directory entry. A missing result will not prove that no public record exists.")
    st.caption("The directory names come from a dated official 20th Congress roster; profile facts and affiliations are unverified.")
    profile(senator)


def render(service):
    senator = service.get(st.session_state.senator_id)
    histories = st.session_state.histories
    history = histories.setdefault(senator["id"], [])
    coverage = get_chatbot_service().coverage(senator['id'])
    if coverage['status'] == 'reviewed_release':
        st.caption(f"Selected subject: {coverage['count']} reviewed passages · Last review: {coverage['reviewed_at']} · Release: {coverage['release_id']}")
    elif coverage['status'] == 'local_development':
        st.caption('Local development dataset. No published reviewed release is configured.')
    else:
        st.warning('Source service configuration needs attention.' if coverage['status'] == 'configuration_error' else 'Source service is temporarily unavailable.')
    selected_period = st.selectbox('Evidence period', ['All dated records', '20th Congress', '19th Congress'], key='chat_evidence_period')
    congress_id = {'20th Congress': '20', '19th Congress': '19'}.get(selected_period)
    st.caption('Ask a complete question each time. Earlier messages are not sent to the model. Historical evidence does not establish current status.')
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
                st.html(f'<div class="welcome">{avatar(senator,"hero")}<div class="tricolor"><i></i><i></i><i></i></div><h1>Kilalanin ang Senador Mo!</h1><p>Ask questions and explore the public record <br>of {escape(senator["name"])}.</p><small>SEN’TO summarizes reviewed sources. It does not speak for a senator, and its records may be incomplete.</small></div>')
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
                    for message_index, message in enumerate(history):
                        chat_bubble(message, key=f"sources_{senator['id']}_{message_index}")
                        for target in message.get('response', {}).get('switch_targets', []):
                            if st.button(f"Open Senator {target['name']}’s chat", key=f"switch_{senator['id']}_{message_index}_{target['id']}"):
                                st.session_state.senator_id = target['id']
                                st.rerun()
                st.html('<div class="disclaimer">Review each citation and its locator. The indexed records may be incomplete, and summaries are not official statements.</div>')
        with st.container(key="composer"):
            prompt = st.chat_input("Ask anything about this senator…", key="chat_prompt", max_chars=4000)
            if st.button("▤  Dataset & profile", key="dataset_profile"):
                _dataset_profile(senator)
        st.html('<p class="fine-print">Unsupported questions receive a clear limitation. Every returned citation links to source metadata and a locator when available.</p>')
        if submitted or prompt:
            try:
                question = normalize_question(submitted or prompt)
            except ValueError as exc:
                st.warning(str(exc))
            else:
                if not allow_session_request(st.session_state):
                    st.warning(
                        f"Please wait before sending another question. The limit is "
                        f"{MAX_SESSION_REQUESTS} questions per {int(SESSION_REQUEST_WINDOW_SECONDS)} seconds."
                    )
                else:
                    if requests_internal_prompt(question):
                        result = {
                            "label": "SECURITY LIMIT",
                            "topic": "sources",
                            "answer": internal_prompt_refusal(question),
                            "citations": [],
                            "retrieval_count": 0,
                            "limitation": internal_prompt_limitation(question),
                        }
                    elif requests_bulk_retrieval(question):
                        result = {
                            "label": "SECURITY LIMIT",
                            "topic": "sources",
                            "answer": bulk_retrieval_refusal(question),
                            "citations": [],
                            "retrieval_count": 0,
                            "limitation": bulk_retrieval_limitation(question),
                        }
                    else:
                        with st.spinner("Preparing your question…"):
                            result = send_chat_message(senator["id"], question, congress_id=congress_id)
                    history.extend([{"role": "user", "content": question}, {"role": "assistant", "response": result}])
                    del history[:-40]
                    st.rerun()
