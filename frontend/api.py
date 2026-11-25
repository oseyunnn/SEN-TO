"""Frontend-facing service seams.

These functions keep the UI independent from transport and backend details.
Replace their bodies with API calls when a backend endpoint is ready.
"""

def get_senator_directory():
    """Load the local example directory until a directory endpoint exists."""
    # TODO: Replace with GET /api/senators when the backend endpoint exists.
    from backend.senator_service import SenatorService

    return SenatorService()


def get_chatbot_service():
    """Build the stateless RAG service for the current chat request."""
    from backend.chatbot_service import ChatbotService

    return ChatbotService()


def send_chat_message(senator_id, message):
    """Run one question through the selected-subject RAG pipeline."""
    return get_chatbot_service().ask(message, senator_id)


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
