"""Frontend-facing service seams.

These functions keep the UI independent from transport and backend details.
Replace their bodies with API calls when a backend endpoint is ready.
"""

def get_senator_directory():
    """Load the local example directory until a directory endpoint exists."""
    # TODO: Replace with GET /api/senators when the backend endpoint exists.
    from backend.senator_service import SenatorService

    return SenatorService()


import hashlib
import os
import streamlit as st


@st.cache_resource(show_spinner=False)
def _cached_chatbot_service(settings_key):
    """Build the stateless RAG service for the current chat request."""
    from backend.chatbot_service import ChatbotService

    return ChatbotService()


def get_chatbot_service():
    # Hash credentials so rotations invalidate clients without exposing values in cache keys.
    names = sorted(k for k in os.environ if k.startswith(('SENTO_', 'CHROMA_', 'OPENAI_', 'QDRANT_')))
    digest = hashlib.sha256(repr([(k, os.environ[k]) for k in names]).encode()).hexdigest()
    return _cached_chatbot_service(digest)


def send_chat_message(senator_id, message, congress_id=None, progress_callback=None):
    """Run one question through the selected-subject RAG pipeline."""
    service = get_chatbot_service()
    options = {}
    if congress_id:
        options["congress_id"] = congress_id
    if progress_callback:
        options["progress_callback"] = progress_callback
    return service.ask(message, senator_id, **options)


def get_comparison_records(directory, senator_ids, period="20th_congress"):
    """Read source-linked comparison claims from the curated Markdown profiles."""
    from backend.comparison_service import ComparisonService

    return ComparisonService(senators=directory).compare(senator_ids, period=period)
