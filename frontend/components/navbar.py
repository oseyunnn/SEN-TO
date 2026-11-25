import streamlit as st


def _navigate():
    st.session_state.page = st.session_state.main_navigation


def navbar():
    with st.container(key="navbar"):
        brand, navigation, actions = st.columns([1.25, 1.6, 1.1], vertical_alignment="center")
        with brand:
            st.html('<a class="brand-home" href="?view=home" aria-label="SEN’TO home"><span class="brand">SEN<span class="gold">’</span><span class="red">TO</span></span><small>20TH CONGRESS</small></a>')
        with navigation:
            page = st.session_state.page
            selected = page if page in ("CHAT", "COMPARE") else None
            if st.session_state.get("main_navigation") != selected:
                st.session_state.main_navigation = selected
            st.radio(
                "Main navigation",
                ["CHAT", "COMPARE"],
                index=0 if selected == "CHAT" else 1 if selected == "COMPARE" else None,
                horizontal=True,
                key="main_navigation",
                label_visibility="collapsed",
                on_change=_navigate,
            )
        with actions:
            if st.session_state.page == "HOME":
                if st.button("Talk with SEN’TO →", key="nav_home_start", type="primary", use_container_width=True):
                    st.session_state.page = "CHAT"
                    st.rerun()
