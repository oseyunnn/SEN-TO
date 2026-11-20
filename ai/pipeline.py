from typing import Protocol
from ai.intent_classifier import preprocess, classify
from ai.retriever import MockRetriever
from ai.answer_generator import MockAnswerGenerator
from ai.validator import MockFactValidator, format_citations
from ai.prompts import LABEL, LIMITATION
from backend.policies import policy_violation, NEUTRAL_RESPONSE


class Retriever(Protocol):
    def retrieve(self, query, senator_id, top_k=3): ...


class Generator(Protocol):
    def generate(self, query, senator, context, style): ...


class Validator(Protocol):
    def validate(self, answer, retrieved_documents): ...


class RAGPipeline:
    def __init__(self, retriever: Retriever = None, generator: Generator = None, validator: Validator = None):
        self.retriever = retriever if retriever is not None else MockRetriever()
        self.generator = generator if generator is not None else MockAnswerGenerator()
        self.validator = validator if validator is not None else MockFactValidator()

    def run(self, query, senator, style):
        query = preprocess(query)
        if not query or len(query) > 4000:
            raise ValueError("Enter a question between 1 and 4,000 characters.")
        guarded = policy_violation(query)
        documents = [] if guarded else self.retriever.retrieve(query, senator["id"])
        # Enforce context isolation even with an injected retriever.
        context = [d for d in documents if d["senator_id"] == senator["id"]][:3]
        answer = NEUTRAL_RESPONSE if guarded else self.generator.generate(query, senator, context, style)
        return {"answer": answer, "label": LABEL, "limitation": LIMITATION,
                "topic": classify(query), "retrieval_count": len(context),
                "validation": self.validator.validate(answer, context), "citations": format_citations(context)}
