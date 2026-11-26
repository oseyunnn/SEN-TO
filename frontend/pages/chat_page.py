from html import escape
import inspect
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


_LOADING_LABELS = {
    "checking_scope": "Checking what this dataset can answer",
    "searching_sources": "Searching reviewed sources",
    "checking_evidence": "Checking the evidence for this senator",
    "writing_answer": "Writing a source-linked answer",
    "checking_citations": "Checking citations and source links",
}


def _loading_status(stage):
    label = escape(_LOADING_LABELS.get(stage, "Searching reviewed sources"))
    return (
        '<div class="chat-loading-status" role="status" aria-live="polite">'
        '<span class="thinking-dots" aria-hidden="true"><i></i><i></i><i></i></span>'
        f"<span>{label}</span></div>"
    )


def _answer_skeleton(first_turn=False):
    turn_class = "welcome-skeleton" if first_turn else "history-skeleton"
    return (
        f'<div class="chat-answer-skeleton {turn_class}" role="status" aria-label="Preparing an answer">'
        '<span class="skeleton-label"></span>'
        '<span class="skeleton-title"></span>'
        '<span class="skeleton-line"></span>'
        '<span class="skeleton-line medium"></span>'
        "</div>"
    )


def _send_with_progress(senator_id, question, progress_callback, congress_id=None):
    try:
        parameters = inspect.signature(send_chat_message).parameters
    except (TypeError, ValueError):
        parameters = {}

    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )

    def accepts_keyword(name):
        parameter = parameters.get(name)
        return accepts_kwargs or (
            parameter is not None
            and parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        )

    options = {}
    if congress_id and accepts_keyword("congress_id"):
        options["congress_id"] = congress_id
    if progress_callback and accepts_keyword("progress_callback"):
        options["progress_callback"] = progress_callback
    return send_chat_message(senator_id, question, **options)


@st.dialog("Sources & evidence", width="large")
def _dataset_profile(senator):
    st.write("Chat searches reviewed, indexed sources for the selected directory entry. Source links and locators for an answer appear with that answer.")
    st.caption("A missing result does not prove that no public record exists; this dataset may not cover every record.")
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
            answer_loading_slot = None
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
                answer_loading_slot = st.empty()
            else:
                with st.container(border=False, key="conversation"):
                    for message_index, message in enumerate(history):
                        chat_bubble(message, key=f"chat_sources_{senator['id']}_{message_index}")
                        for target in message.get('response', {}).get('switch_targets', []):
                            if st.button(f"Open Senator {target['name']}’s chat", key=f"switch_{senator['id']}_{message_index}_{target['id']}"):
                                st.session_state.senator_id = target['id']
                                st.rerun()
                    answer_loading_slot = st.empty()
            if history:
                st.html('<div class="disclaimer">Review each citation and its locator. The indexed records may be incomplete, and summaries are not official statements.</div>')
        with st.container(key="chat_loading"):
            loading_status_slot = st.empty()
        with st.container(key="composer"):
            prompt = st.chat_input("Ask anything about this senator…", key="chat_prompt", max_chars=4000)
            if st.button("Sources & evidence", icon=":material/menu_book:", key="dataset_profile"):
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
                        if answer_loading_slot is not None:
                            answer_loading_slot.html(_answer_skeleton(first_turn=not history))
                        loading_status_slot.html(_loading_status("checking_scope"))

                        def report_progress(stage):
                            loading_status_slot.html(_loading_status(stage))

                        try:
                            result = _send_with_progress(senator["id"], question, report_progress)
                        finally:
                            if answer_loading_slot is not None:
                                answer_loading_slot.empty()
                            loading_status_slot.empty()
                    history.extend([
                        {"role": "user", "content": question},
                        {"role": "assistant", "response": result, "animate_answer": True},
                    ])
                    del history[:-40]
                    st.rerun()
