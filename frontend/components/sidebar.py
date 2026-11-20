import streamlit as st
from frontend.components.senator_card import avatar


def sidebar(service):
    key = "senator_id"
    title = "Senators"
    with st.container(key="directory"):
        with st.expander("Browse " + title.lower(), expanded=True):
            st.html(f'<div class="directory-heading"><h3>{title}</h3><span>{len(service.senators)}</span></div>')
            query = st.text_input("Search " + title.lower(), placeholder="Search senators…",
                                  key="senator_search", label_visibility="collapsed")
            with st.container(height=620, border=False, key="directory_list"):
                results = service.search(query)
                if not results:
                    st.info("No matching senators. Try another name.")
                for senator in results:
                    selected = st.session_state[key] == senator["id"]
                    with st.container(key=("chosen_" if selected else "option_") + senator["id"]):
                        picture, control = st.columns([48, 186], gap="small", vertical_alignment="center")
                        with picture:
                            st.html(avatar(senator))
                        with control:
                            if st.button(senator["name"], key="select_" + key + senator["id"], use_container_width=True):
                                st.session_state[key] = senator["id"]
                                st.rerun()
                            st.caption("Senator · 20th Congress" if senator.get("portrait") else "Portrait placeholder")
            st.html(f'<div class="directory-foot">{len(service.senators)} reference profiles · Scroll to explore ↓</div>')
