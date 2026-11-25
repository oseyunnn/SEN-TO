"""Frontend-facing service seams.

These functions keep the UI independent from transport and backend details.
Replace their bodies with API calls when a backend endpoint is ready.
"""


def get_senator_directory():
    """Load the local example directory until a directory endpoint exists."""
    # TODO: Replace with GET /api/senators when the backend endpoint exists.
    from backend.senator_service import SenatorService

    return SenatorService()


def send_chat_message(senator_id, message):
    """Return an honest placeholder until the chat endpoint is connected."""
    # TODO: Replace with POST /api/chat when the source-backed endpoint exists.
    return {
        "label": "BACKEND CONNECTION PLACEHOLDER",
        "topic": "sources",
        "answer": (
            "The chat interface is ready. Connect `send_chat_message()` to the "
            "source-backed chat endpoint to return an answer here."
        ),
        "citations": [],
        "retrieval_count": 0,
        "limitation": "The chat endpoint is not connected. No source lookup was performed.",
        "senator_id": senator_id,
        "message": message,
    }


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
