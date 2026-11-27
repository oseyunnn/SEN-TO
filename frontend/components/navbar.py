import streamlit as st


def _navigate():
    st.session_state.page = st.session_state.main_navigation


def navbar():
    with st.container(key="navbar"):
        is_home = st.session_state.page == "HOME"
        columns = st.columns([1], vertical_alignment="center") if is_home else st.columns([1.25, 1.6, 1.1], vertical_alignment="center")
        brand = columns[0]
        with brand:
            if is_home:
                st.html('<div class="landing-header-row"><a class="brand-home brand-home-landing" href="?view=home" aria-label="SEN’TO home"><span class="brand">SEN<span class="gold">’</span><span class="red">TO</span></span><small>20TH CONGRESS</small></a><span class="roster-source-note">24 roster names · official Senate source dated 28 Jul 2025</span></div>')
            else:
                st.html('<a class="brand-home" href="?view=home" aria-label="SEN’TO home"><span class="brand">SEN<span class="gold">’</span><span class="red">TO</span></span><small>20TH CONGRESS</small></a>')
        if not is_home:
            navigation = columns[1]
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
