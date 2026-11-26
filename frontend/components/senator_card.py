import base64
import mimetypes
from functools import lru_cache
from html import escape
from pathlib import Path
import streamlit as st
from backend.senator_service import SECTIONS, UNAVAILABLE

IMAGE_ROOT = Path(__file__).resolve().parents[2] / "assets" / "images"


@lru_cache(maxsize=1)
def portrait_source():
    path = IMAGE_ROOT / "design-reference.png"
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode() if path.exists() else ""


@lru_cache(maxsize=24)
def local_portrait_source(relative_path):
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        return ""

    root = IMAGE_ROOT.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        return ""

    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime_type};base64,{encoded}"


def avatar(senator, size="small"):
    portrait_file = senator.get("portrait_file")
    if portrait_file:
        source = local_portrait_source(portrait_file)
        if source:
            name = escape(senator["name"], quote=True)
            return (f'<div class="portrait-wrap official-portrait {size}">'
                    f'<img class="portrait-image" src="{source}" alt="{name} official Senate portrait" />'
                    '</div>')

    source = portrait_source()
    portrait = senator.get("portrait")
    if portrait is not None and source:
        x = [210, 650, 1090][int(portrait)]
        return (f'<div class="portrait-wrap {size}" role="img" aria-label="{escape(senator["name"])} portrait from supplied mockup">'
                f'<div class="portrait" style="background-image:url({source});background-position:-{x}px -340px"></div></div>')
    return f'<div class="avatar-placeholder {size}" aria-label="Portrait unavailable"><svg width="26" height="30" viewBox="0 0 26 30" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="13" cy="9" r="4"/><path d="M5 26v-5a8 8 0 0 1 16 0v5"/></svg></div>'


def profile(senator):
    with st.expander("Profile & available sources"):
        st.caption("Roster name from the official 20th Congress Senate source dated 28 July 2025. Profile details and Minority Bloc membership are unverified.")
        for key, title in SECTIONS.items():
            record = senator.get("profile", {}).get(key, {})
            st.markdown(f"**{title}**")
            st.write(record.get("content", UNAVAILABLE))
            st.caption("Data status: " + record.get("status", "not_available").replace("_", " "))
        st.caption("No verified government source is connected to this prototype.")
