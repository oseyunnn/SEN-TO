import base64
from functools import lru_cache
from html import escape
from pathlib import Path
import streamlit as st
from backend.senator_service import SECTIONS, UNAVAILABLE


@lru_cache(maxsize=1)
def portrait_source():
    path = Path(__file__).resolve().parents[2] / "assets" / "images" / "design-reference.png"
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode() if path.exists() else ""


def avatar(senator, size="small"):
    source = portrait_source()
    portrait = senator.get("portrait")
    if portrait is not None and source:
        x = [210, 650, 1090][int(portrait)]
        return (f'<div class="portrait-wrap {size}" role="img" aria-label="{escape(senator["name"])} portrait from supplied mockup">'
                f'<div class="portrait" style="background-image:url({source});background-position:-{x}px -340px"></div></div>')
    return f'<div class="avatar-placeholder {size}" aria-label="Portrait unavailable"><svg width="26" height="30" viewBox="0 0 26 30" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="13" cy="9" r="4"/><path d="M5 26v-5a8 8 0 0 1 16 0v5"/></svg></div>'


def profile(senator):
    with st.expander("Profile & available sources"):
        st.caption("Directory example from the supplied design. Current Senate and Minority Bloc membership are unverified.")
        for key, title in SECTIONS.items():
            record = senator.get("profile", {}).get(key, {})
            st.markdown(f"**{title}**")
            st.write(record.get("content", UNAVAILABLE))
            st.caption("Data status: " + record.get("status", "not_available").replace("_", " "))
        st.caption("No verified government source is connected to this prototype.")
