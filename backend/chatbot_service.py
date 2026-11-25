from backend.senator_service import SenatorService
from ai.rag_factory import build_default_pipeline


class ChatbotService:
    def __init__(self, senators=None, pipeline=None):
        self.senators = senators or SenatorService()
        self.pipeline = pipeline or build_default_pipeline()

    def ask(self, question, senator_id):
        return self.pipeline.run(question, self.senators.get(senator_id), self.senators.style(senator_id))

    def indexed_passage_count(self):
        count_indexed = getattr(self.pipeline.retriever, "count_indexed", None)
        if not callable(count_indexed):
            return None
        try:
            return count_indexed()
        except Exception:
            return None
