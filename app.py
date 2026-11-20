"""Run with: streamlit run app.py"""
import logging
from pathlib import Path
import streamlit as st
from backend.senator_service import SenatorService
from backend.chatbot_service import ChatbotService
from backend.comparison_service import ComparisonService
from frontend.components.navbar import navbar
from frontend.components.sidebar import sidebar
from frontend.pages import chat_page, compare_page

st.set_page_config(page_title="SEN’TO — Kilalanin ang Senador Mo!", page_icon="🇵🇭", layout="wide")
st.html("<style>" + (Path(__file__).parent / "frontend/styles/custom.css").read_text(encoding="utf-8") + "</style>")


def main():
    senators = SenatorService()
    # Preserve widget-backed preferences while their page is not rendered.
    for key in ("comparison_count", "compare_category", "senator_search"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    defaults = {"page": "CHAT",
                "senator_id": senators.senators[0]["id"],
                "histories": {}, "guest_name": "Guest reader",
                "compare_ids": [s["id"] for s in senators.senators[:3]],
                "comparison_count": st.session_state.get("saved_comparison_count", 3)}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    if st.session_state.page not in ("CHAT", "COMPARE"):
        st.session_state.page = "CHAT"
    if "post" in st.query_params:
        del st.query_params["post"]
    navbar()
    if st.session_state.page == "COMPARE":
        compare_page.render(senators, ComparisonService(senators))
    else:
        directory, main_panel = st.columns([304, 1072], gap="small")
        with directory:
            sidebar(senators)
        with main_panel:
            chat_page.render(senators, ChatbotService(senators))


try:
    main()
except (ValueError, OSError) as exc:
    logging.exception("SEN’TO could not complete this operation")
    if isinstance(exc, ValueError):
        st.error(str(exc))
    else:
        st.error("SEN’TO could not load local data. Check that the data files exist and are readable, then retry.")
