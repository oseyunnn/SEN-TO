"""Source-grounded retrieval, generation, and citation validation."""

from __future__ import annotations

from typing import Callable, Protocol

from ai.embeddings import EmbeddingError
from ai.generation import GenerationError
from ai.intent_classifier import classify
from ai.validator import EvidenceValidator, format_citations, is_safe_source_url
from ai.vector_store import VectorStoreError
from backend.security import (
    bulk_retrieval_refusal,
    bulk_retrieval_limitation,
    internal_prompt_refusal,
    internal_prompt_limitation,
    localized_text,
    normalize_question,
    no_evidence_limitation,
    no_evidence_response,
    requests_bulk_retrieval,
    requests_internal_prompt,
    service_unavailable_response,
)
from backend.policies import neutral_response, policy_violation


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
MAX_RETRIEVED_CHUNKS = 5
MAX_EVIDENCE_CHARS = 1200
MAX_TOTAL_EVIDENCE_CHARS = 4500
MAX_ANSWER_CHARS = 5000


class Retriever(Protocol):
    def retrieve(self, query: str, senator_id: str, top_k: int = 5, relevant_period: str | None = None, congress_id: str | None = None) -> list[dict]: ...


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


def _report_progress(progress_callback: Callable[[str], None] | None, stage: str) -> None:
    if not progress_callback:
        return
    try:
        progress_callback(stage)
    except Exception:
        # Progress is presentation-only and must not affect answer handling.
        return


class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever,
        generator: Generator,
        validator: Validator | None = None,
        top_k: int = 5,
        request_limiter=None,
    ):
        self.retriever = retriever
        self.generator = generator
        self.validator = validator or EvidenceValidator()
        self.top_k = min(MAX_RETRIEVED_CHUNKS, max(1, int(top_k)))
        self.request_limiter = request_limiter

    def run(
        self,
        query: str,
        senator: dict,
        style: dict,
        relevant_period: str | None = None,
        congress_id: str | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict:
        query = normalize_question(query)
        topic = classify(query)
        _report_progress(progress_callback, "checking_scope")
        if requests_internal_prompt(query):
            return self._response(
                answer=internal_prompt_refusal(query),
                label="SECURITY LIMIT",
                limitation=internal_prompt_limitation(query),
                topic=topic,
                validation={"status": "POLICY_LIMIT", "verified": False, "citation_ids": []},
            )
        if requests_bulk_retrieval(query):
            return self._response(
                answer=bulk_retrieval_refusal(query),
                label="SECURITY LIMIT",
                limitation=bulk_retrieval_limitation(query),
                topic=topic,
                validation={"status": "POLICY_LIMIT", "verified": False, "citation_ids": []},
            )
        if policy_violation(query):
            return self._response(
                answer=neutral_response(query),
                label="NEUTRALITY LIMIT",
                limitation=localized_text(
                    query,
                    "SEN’TO does not provide political endorsements, rankings, or unsupported accusations.",
                    "Hindi nagbibigay ang SEN’TO ng pag-eendorso, pagraranggo, o hindi suportadong paratang.",
                ),
                topic=topic,
                validation={"status": "POLICY_LIMIT", "verified": False, "citation_ids": []},
            )

        if self.request_limiter is not None and not self.request_limiter.allow():
            message = localized_text(
                query,
                "SEN’TO is handling many requests right now. Please try again in about a minute.",
                "Maraming request ang pinoproseso ng SEN’TO ngayon. Subukan ulit pagkalipas ng halos isang minuto.",
            )
            return self._response(
                answer=message,
                label="RATE LIMIT",
                limitation=message,
                topic=topic,
                validation={"status": "RATE_LIMITED", "verified": False, "citation_ids": []},
            )

        try:
            _report_progress(progress_callback, "searching_sources")
            retrieved = self.retriever.retrieve(
                query,
                senator["id"],
                top_k=self.top_k,
                relevant_period=relevant_period,
                **({"congress_id": congress_id} if congress_id else {}),
            )
        except (EmbeddingError, VectorStoreError, GenerationError):
            return self._unavailable(topic, query)

        _report_progress(progress_callback, "checking_evidence")

        context = []
        seen_chunks = set()
        evidence_chars = 0
        for document in retrieved:
            if not isinstance(document, dict) or not _belongs_to_senator(document, senator["id"]):
                continue
            if not _usable_evidence(document):
                continue
            if relevant_period and document.get("relevant_period") != relevant_period:
                continue
            if congress_id and document.get("congress_id") != congress_id:
                continue
            chunk_id = document.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id or chunk_id in seen_chunks:
                continue
            remaining = MAX_TOTAL_EVIDENCE_CHARS - evidence_chars
            if remaining <= 0:
                break
            bounded_text = document["text"][:min(MAX_EVIDENCE_CHARS, remaining)]
            if not bounded_text.strip():
                continue
            seen_chunks.add(chunk_id)
            sources = []
            for source in document["citation_sources"][:2]:
                bounded_source = dict(source)
                sources.append(bounded_source)
            context.append({
                **document,
                "text": bounded_text,
                "citation_sources": sources,
                "section": str(document.get("section", "Public record"))[:240],
                "evidence_id": f"E{len(context) + 1}",
            })
            evidence_chars += len(bounded_text)
            if len(context) >= self.top_k:
                break

        if not context:
            return self._response(
                answer=no_evidence_response(query, NO_EVIDENCE),
                label="NO REVIEWED EVIDENCE",
                limitation=no_evidence_limitation(
                    query,
                    "The current corpus has no reviewed passage that supports an answer to this question.",
                ),
                topic=topic,
                validation={"status": "INSUFFICIENT_EVIDENCE", "verified": False, "citation_ids": []},
            )

        try:
            _report_progress(progress_callback, "writing_answer")
            answer = self.generator.generate(query, senator, context, style)
            if not isinstance(answer, str) or len(answer) > MAX_ANSWER_CHARS:
                return self._response(
                    answer=no_evidence_response(query, NO_EVIDENCE),
                    label="ANSWER NOT VALIDATED",
                    limitation=localized_text(
                        query,
                        "The generated answer exceeded the response limit and was withheld.",
                        "Lumampas sa itinakdang haba ang sagot at hindi ito ipinakita.",
                    ),
                    topic=topic,
                    validation={"status": "OUTPUT_LIMIT", "verified": False, "citation_ids": []},
                    retrieval_count=len(context),
                )
            _report_progress(progress_callback, "checking_citations")
            validation = self.validator.validate(answer, context)
        except (EmbeddingError, VectorStoreError, GenerationError):
            return self._unavailable(topic, query)
        except Exception:
            return self._unavailable(topic, query)

        if validation.get("status") != "CITATIONS_VALIDATED":
            return self._response(
                answer=no_evidence_response(query, NO_EVIDENCE),
                label="ANSWER NOT VALIDATED",
                limitation=localized_text(
                    query,
                    "The generated answer did not pass citation checks and has been withheld.",
                    "Hindi ipinakita ang sagot dahil hindi ito pumasa sa pagsusuri ng mga citation.",
                ),
                topic=topic,
                validation=validation,
                retrieval_count=len(context),
            )

        citations = format_citations(context, validation.get("citation_ids", []))
        if not citations:
            return self._response(
                answer=no_evidence_response(query, NO_EVIDENCE),
                label="ANSWER NOT VALIDATED",
                limitation=localized_text(
                    query,
                    "No safe, verified source link could be attached to the generated answer.",
                    "Walang ligtas at beripikadong source link na maiuugnay sa nabuong sagot.",
                ),
                topic=topic,
                validation={"status": "INVALID_SOURCE", "verified": False, "citation_ids": []},
                retrieval_count=len(context),
            )
        return self._response(
            answer=answer,
            label=LABEL,
            limitation=localized_text(
                query,
                LIMITATION,
                "Buod ito ng nasuring mga rekord at hindi opisyal na pahayag ng Senado. Suriin ang citation at locator; maaaring hindi kumpleto ang dataset.",
            ),
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
    def _unavailable(cls, topic: str, query: str) -> dict:
        return cls._response(
            answer=service_unavailable_response(query, SERVICE_UNAVAILABLE),
            label="RAG SERVICE UNAVAILABLE",
            limitation=localized_text(
                query,
                "Check the configured local model and vector index, then try again.",
                "Suriin ang naka-configure na local model at vector index, saka subukan ulit.",
            ),
            topic=topic,
            validation={"status": "SERVICE_UNAVAILABLE", "verified": False, "citation_ids": []},
        )
