"""Source-grounded retrieval, generation, and citation validation."""

from __future__ import annotations

from typing import Protocol

from ai.embeddings import EmbeddingError
from ai.generation import GenerationError
from ai.intent_classifier import classify
from ai.validator import EvidenceValidator, format_citations, is_safe_source_url
from ai.vector_store import VectorStoreError
from backend.policies import NEUTRAL_RESPONSE, policy_violation


LABEL = "SOURCE-GROUNDED AI SUMMARY"
LIMITATION = (
    "This is an AI summary of reviewed records, not an official Senate statement. "
    "Check the cited source and locator; this dataset may be incomplete."
)
NO_EVIDENCE = (
    "I could not find a reviewed source in the current dataset that answers this question. "
    "That does not establish that no public record exists."
)
SERVICE_UNAVAILABLE = "The source-backed answer service is temporarily unavailable. No answer was generated."


class Retriever(Protocol):
    def retrieve(self, query: str, senator_id: str, top_k: int = 5, relevant_period: str | None = None) -> list[dict]: ...


class Generator(Protocol):
    def generate(self, query: str, senator: dict, context: list[dict], style: dict) -> str: ...


class Validator(Protocol):
    def validate(self, answer: str, retrieved_documents: list[dict]) -> dict: ...


def _belongs_to_senator(document: dict, senator_id: str) -> bool:
    senator_ids = document.get("senator_ids")
    return document.get("senator_id") == senator_id or (
        isinstance(senator_ids, list) and senator_id in senator_ids
    )


def _usable_evidence(document: dict) -> bool:
    if document.get("verification_status") != "verified" or not isinstance(document.get("text"), str):
        return False
    sources = document.get("citation_sources")
    return bool(
        isinstance(sources, list)
        and sources
        and all(
            isinstance(source, dict)
            and source.get("verification_status") == "verified"
            and is_safe_source_url(source.get("source_url"))
            for source in sources
        )
    )


class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever,
        generator: Generator,
        validator: Validator | None = None,
        top_k: int = 5,
    ):
        self.retriever = retriever
        self.generator = generator
        self.validator = validator or EvidenceValidator()
        self.top_k = max(1, int(top_k))

    def run(self, query: str, senator: dict, style: dict, relevant_period: str | None = None) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            raise ValueError("Enter a question between 1 and 4,000 characters.")
        query = query.strip()
        topic = classify(query)
        if policy_violation(query):
            return self._response(
                answer=NEUTRAL_RESPONSE,
                label="NEUTRALITY LIMIT",
                limitation="SEN’TO does not provide political endorsements, rankings, or unsupported accusations.",
                topic=topic,
                validation={"status": "POLICY_LIMIT", "verified": False, "citation_ids": []},
            )

        try:
            retrieved = self.retriever.retrieve(
                query,
                senator["id"],
                top_k=self.top_k,
                relevant_period=relevant_period,
            )
        except (EmbeddingError, VectorStoreError, GenerationError):
            return self._unavailable(topic)

        context = []
        seen_chunks = set()
        for document in retrieved:
            if not isinstance(document, dict) or not _belongs_to_senator(document, senator["id"]):
                continue
            if not _usable_evidence(document):
                continue
            chunk_id = document.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id or chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            context.append({**document, "evidence_id": f"E{len(context) + 1}"})
            if len(context) >= self.top_k:
                break

        if not context:
            return self._response(
                answer=NO_EVIDENCE,
                label="NO REVIEWED EVIDENCE",
                limitation="The current corpus has no reviewed passage that supports an answer to this question.",
                topic=topic,
                validation={"status": "INSUFFICIENT_EVIDENCE", "verified": False, "citation_ids": []},
            )

        try:
            answer = self.generator.generate(query, senator, context, style)
            validation = self.validator.validate(answer, context)
        except (EmbeddingError, VectorStoreError, GenerationError):
            return self._unavailable(topic)
        except Exception:
            return self._unavailable(topic)

        if validation.get("status") != "CITATIONS_VALIDATED":
            return self._response(
                answer=NO_EVIDENCE,
                label="ANSWER NOT VALIDATED",
                limitation="The generated answer did not pass citation checks and has been withheld.",
                topic=topic,
                validation=validation,
                retrieval_count=len(context),
            )

        citations = format_citations(context, validation.get("citation_ids", []))
        if not citations:
            return self._response(
                answer=NO_EVIDENCE,
                label="ANSWER NOT VALIDATED",
                limitation="No safe, verified source link could be attached to the generated answer.",
                topic=topic,
                validation={"status": "INVALID_SOURCE", "verified": False, "citation_ids": []},
                retrieval_count=len(context),
            )
        return self._response(
            answer=answer,
            label=LABEL,
            limitation=LIMITATION,
            topic=topic,
            validation=validation,
            citations=citations,
            retrieval_count=len(context),
        )

    @staticmethod
    def _response(
        answer: str,
        label: str,
        limitation: str,
        topic: str,
        validation: dict,
        citations: list[dict] | None = None,
        retrieval_count: int = 0,
    ) -> dict:
        return {
            "answer": answer,
            "label": label,
            "limitation": limitation,
            "topic": topic,
            "retrieval_count": retrieval_count,
            "validation": validation,
            "citations": citations or [],
        }

    @classmethod
    def _unavailable(cls, topic: str) -> dict:
        return cls._response(
            answer=SERVICE_UNAVAILABLE,
            label="RAG SERVICE UNAVAILABLE",
            limitation="Check the configured local model and vector index, then try again.",
            topic=topic,
            validation={"status": "SERVICE_UNAVAILABLE", "verified": False, "citation_ids": []},
        )
