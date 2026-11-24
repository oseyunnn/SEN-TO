from backend.senator_service import SenatorService


class ChatbotService:
    def __init__(self, senators=None, pipeline=None):
        self.senators = senators or SenatorService()
        # A live source-backed query pipeline is a later phase. Do not silently
        # fall back to the old demonstration RAG when one is not supplied.
        self.pipeline = pipeline

    def ask(self, question, senator_id):
        if self.pipeline is None:
            if not question or not question.strip() or len(question) > 4000:
                raise ValueError("Enter a question between 1 and 4,000 characters.")
            self.senators.get(senator_id)
            return {
                "answer": "Answers are temporarily unavailable while the official-record corpus is being prepared. No simulated or unverified records were used.",
                "label": "SOURCE-BACKED RAG NOT CONNECTED",
                "limitation": "The document ingestion step is in progress; retrieval and generation are not connected yet.",
                "topic": "unknown",
                "retrieval_count": 0,
                "validation": {"status": "NOT_RUN", "verified": False},
                "citations": [],
            }
        return self.pipeline.run(question, self.senators.get(senator_id), self.senators.style(senator_id))
