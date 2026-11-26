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


def send_chat_message(senator_id, message, congress_id=None):
    """Run one question through the selected-subject RAG pipeline."""
    return get_chatbot_service().ask(message, senator_id, **({'congress_id': congress_id} if congress_id else {}))


def get_comparison_records(directory, senator_ids):
    """Build the current local demo shape; replace with a comparison API call."""
    # TODO: Replace this adapter with GET /api/compare once the backend is ready.
    from backend.senator_service import SECTIONS, UNAVAILABLE

    return [
        {
            "senator": directory.get(senator_id),
            "period": "20th Congress · 2025–2028",
            "sections": {
                key: directory.get(senator_id).get("profile", {}).get(key, {
                    "status": "not_available",
                    "content": UNAVAILABLE,
                    "sources": [],
                })
                for key in SECTIONS
            },
        }
        for senator_id in senator_ids
    ]
