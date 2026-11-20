from ai.pipeline import RAGPipeline
from backend.senator_service import SenatorService


class ChatbotService:
    def __init__(self, senators=None, pipeline=None):
        self.senators = senators or SenatorService()
        self.pipeline = pipeline or RAGPipeline()

    def ask(self, question, senator_id):
        return self.pipeline.run(question, self.senators.get(senator_id), self.senators.style(senator_id))
