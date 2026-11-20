from html import escape
import streamlit as st
from frontend.components.senator_card import avatar, profile
from frontend.components.chat_bubble import chat_bubble


def render(service, chatbot):
    senator = service.get(st.session_state.senator_id)
    histories = st.session_state.histories
    history = histories.setdefault(senator["id"], [])
    with st.container(key="chat_panel"):
        st.html(f'<div class="chat-heading">{avatar(senator)}<div><strong>{escape(senator["name"])}</strong><small>Public record assistant · 20th Congress</small></div><span>AI ASSISTANT</span></div>')
        submitted = None
        if not history:
            st.html(f'<div class="welcome">{avatar(senator,"hero")}<div class="tricolor"><i></i><i></i><i></i></div><h1>Kilalanin ang Senador Mo!</h1><p>Ask questions and explore the public record<br>of {escape(senator["name"])}.</p><small>Simulated information assistant. Not the actual senator or an official representative.</small></div>')
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
            st.html('<div class="disclaimer">No specific bill, vote, or committee role is confirmed by these sample answers.</div>')
        with st.container(key="composer"):
            prompt = st.chat_input("Ask anything about this senator…", key="chat_prompt", max_chars=4000)
            with st.popover("▤  Official sources"):
                st.write("No verified government source is connected to this prototype.")
                st.caption("Responses use local demonstration guides. Directory and Minority Bloc membership are unverified.")
                profile(senator)
        st.html('<p class="fine-print">Simulated explanations may be incomplete. Check original sources when available.</p>')
        if submitted or prompt:
            question = submitted or prompt
            with st.spinner("Reviewing local demonstration records…"):
                result = chatbot.ask(question, senator["id"])
            history.extend([{"role": "user", "content": question}, {"role": "assistant", "response": result}])
            st.rerun()
