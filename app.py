"""Run with: streamlit run app.py"""
import logging
from pathlib import Path
import streamlit as st
from frontend.components.navbar import navbar
from frontend.components.sidebar import sidebar
from frontend.api import get_senator_directory
from frontend.pages import chat_page, compare_page, home_page

st.set_page_config(page_title="SEN’TO — Kilalanin ang Senador Mo!", page_icon="🇵🇭", layout="wide")
st.html("<style>" + (Path(__file__).parent / "frontend/styles/custom.css").read_text(encoding="utf-8") + "</style>")


def main():
    senators = get_senator_directory()
    # Preserve widget-backed preferences while their page is not rendered.
    for key in ("comparison_count", "compare_category", "senator_search"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    defaults = {"page": "HOME",
                "senator_id": senators.senators[0]["id"],
                "histories": {},
                "compare_ids": [s["id"] for s in senators.senators[:3]],
                "comparison_count": st.session_state.get("saved_comparison_count", 3)}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    requested_view = st.query_params.get("view")
    if requested_view in ("home", "chat", "compare"):
        st.session_state.page = requested_view.upper()
        del st.query_params["view"]
    if st.query_params.get("sources") == "1":
        st.session_state.show_compare_sources = True
        del st.query_params["sources"]
    if st.session_state.page not in ("HOME", "CHAT", "COMPARE"):
        st.session_state.page = "HOME"
    if "post" in st.query_params:
        del st.query_params["post"]
    navbar()
    if st.session_state.page == "HOME":
        home_page.render(senators)
    elif st.session_state.page == "COMPARE":
        compare_page.render(senators)
    else:
        st.session_state.mobile_senator_select = st.session_state.senator_id
        with st.container(key="mobile_directory"):
            st.selectbox(
                "Select a senator",
                [senator["id"] for senator in senators.senators],
                format_func=lambda senator_id: senators.get(senator_id)["name"],
                key="mobile_senator_select",
                on_change=lambda: setattr(st.session_state, "senator_id", st.session_state.mobile_senator_select),
            )
        directory, main_panel = st.columns([304, 1072], gap="small")
        with directory:
            sidebar(senators)
        with main_panel:
            chat_page.render(senators)


try:
    main()
except (ValueError, OSError) as exc:
    logging.exception("SEN’TO could not complete this operation")
    if isinstance(exc, ValueError):
        st.error(str(exc))
    else:
        st.error("SEN’TO could not load local data. Check that the data files exist and are readable, then retry.")
