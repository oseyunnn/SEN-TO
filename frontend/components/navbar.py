import streamlit as st


def navbar():
    with st.container(key="navbar"):
        brand, navigation, guest = st.columns([1.25, 1.6, 1.1], vertical_alignment="center")
        with brand:
            st.html('<div class="brand">SEN<span class="gold">’</span><span class="red">TO</span><small>20TH CONGRESS</small></div>')
        with navigation:
            st.radio("Main navigation", ["CHAT", "COMPARE"], horizontal=True,
                     key="page", label_visibility="collapsed")
        with guest:
            with st.popover("JD", help="Guest profile"):
                st.text_input("Guest display name", key="guest_name", max_chars=60)
                st.caption("Local guest mode. Authentication is not implemented.")
