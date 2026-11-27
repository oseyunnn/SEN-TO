"""Source-grounded retrieval, generation, and citation validation."""

from __future__ import annotations

import inspect
import re
from typing import Callable, Protocol

from ai.embeddings import EmbeddingError
from ai.generation import GenerationError
from ai.intent_classifier import classify
from ai.query_understanding import analyze_query
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
    "This is an AI summary based on the project's curated Markdown notes, not an official Senate statement. "
    "Check the cited source and locator; this dataset may be incomplete."
)
NO_EVIDENCE = (
    "I could not find a passage in the current project-curated notes that answers this question. "
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
    project_curated = document.get("curation_status") == "project_curated"
    external_research = document.get("curation_status") == "external_research"
    if (document.get("verification_status") != "verified" and not project_curated and not external_research) or not isinstance(document.get("text"), str):
        return False
    sources = document.get("citation_sources")
    return bool(
        isinstance(sources, list)
        and sources
        and all(
            isinstance(source, dict)
            and (
                (external_research and is_safe_source_url(source.get("source_url")))
                or project_curated
                or (source.get("verification_status") == "verified" and is_safe_source_url(source.get("source_url")))
            )
            for source in sources
        )
    )


_EVIDENCE_PRIORITY = {
    "VERIFIED": 0.25,
    "CORROBORATED": 0.16,
    "REPORTED": 0.08,
    "DISPUTED": 0.02,
    "ALLEGED": 0.02,
    "UNVERIFIED": 0.0,
}


_TOPIC_STOPWORDS = {
    "what", "who", "when", "where", "why", "how", "is", "are", "was", "were", "do", "does",
    "did", "has", "have", "had", "the", "a", "an", "on", "in", "at", "to", "for", "of",
    "and", "or", "about", "with", "this", "that", "these", "those", "her", "his", "their",
    "she", "he", "they", "senator", "sen", "bill", "stance", "position", "support", "record",
    "ano", "sino", "kailan", "saan", "bakit", "paano", "ang", "ng", "mga", "sa", "na", "ba",
    "si", "ni", "kay", "tungkol", "niya", "siya", "nila", "doas",
}


def _topic_keywords(query: str, senator: dict) -> set[str]:
    sen_tokens = set(re.findall(r"[a-z0-9]{2,}", str(senator.get("name", "")).casefold()))
    tokens = set(re.findall(r"[a-z0-9]{3,}", query.casefold()))
    return tokens - _TOPIC_STOPWORDS - sen_tokens


def _has_topical_coverage(query: str, context: list[dict], senator: dict) -> bool:
    if not context:
        return False
    keywords = _topic_keywords(query, senator)
    if not keywords:
        return True
    combined = " ".join(
        f"{doc.get('section', '')} {doc.get('text', '')}" for doc in context
    ).casefold()
    return any(re.search(rf"\b{re.escape(kw)}", combined) for kw in keywords)


def _rerank_documents(documents: list[dict], analysis) -> list[dict]:
    """Hybrid rerank: vector similarity + lexical overlap + evidence/source quality."""
    query_tokens = set(re.findall(r"[a-z0-9]{2,}", analysis.expanded_query.casefold()))
    orig_tokens = set(re.findall(r"[a-z0-9]{2,}", analysis.original_query.casefold()))
    scored: list[tuple[float, int, dict]] = []
    for idx, doc in enumerate(documents):
        if not isinstance(doc, dict):
            continue
        text = str(doc.get("text") or "")
        section = str(doc.get("section") or "")
        doc_tokens = set(re.findall(r"[a-z0-9]{2,}", f"{section} {text}".casefold()))
        lexical = (
            (len(orig_tokens & doc_tokens) / max(1, len(orig_tokens))) * 0.45
            + (len(query_tokens & doc_tokens) / max(1, len(query_tokens))) * 0.25
        )
        distance = (doc.get("retrieval") or {}).get("distance")
        sim = max(0.0, 1.0 - float(distance)) if isinstance(distance, (int, float)) else 0.5
        ev_status = str(doc.get("evidence_status") or "").upper()
        if not ev_status and doc.get("verification_status") == "verified":
            ev_status = "VERIFIED"
        ev_boost = _EVIDENCE_PRIORITY.get(ev_status, 0.05)
        src_boost = 0.08 if any(
            (s.get("source_type") in {"official_record", "government_publication"})
            for s in (doc.get("citation_sources") or [])
            if isinstance(s, dict)
        ) else 0.0
        score = sim * 0.45 + lexical + ev_boost + src_boost
        scored.append((score, -idx, doc))
    scored.sort(reverse=True)
    return [item[2] for item in scored]


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
        web_researcher=None,
    ):
        self.retriever = retriever
        self.generator = generator
        self.validator = validator or EvidenceValidator()
        self.top_k = min(MAX_RETRIEVED_CHUNKS, max(1, int(top_k)))
        self.request_limiter = request_limiter
        self.web_researcher = web_researcher

    def _call_generator(self, query: str, senator: dict, context: list[dict], style: dict, *, query_analysis=None, history=None, allow_empty_context: bool = False) -> str:
        try:
            params = inspect.signature(self.generator.generate).parameters
        except (TypeError, ValueError):
            params = {}
        kwargs = {}
        if "query_analysis" in params:
            kwargs["query_analysis"] = query_analysis
        if "history" in params:
            kwargs["history"] = history
        if "allow_empty_context" in params:
            kwargs["allow_empty_context"] = allow_empty_context
        return self.generator.generate(query, senator, context, style, **kwargs)

    def run(
        self,
        query: str,
        senator: dict,
        style: dict,
        relevant_period: str | None = None,
        congress_id: str | None = None,
        progress_callback: Callable[[str], None] | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        query = normalize_question(query)
        analysis = analyze_query(query, senator=senator, history=history)
        topic = analysis.topic if analysis.topic != "unknown" else classify(query)
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

        if analysis.intent in {"greeting_or_meta", "off_topic"}:
            try:
                answer = self._call_generator(
                    query, senator, [], style,
                    query_analysis=analysis, history=history, allow_empty_context=True,
                )
                if isinstance(answer, str) and answer.strip() and len(answer) <= MAX_ANSWER_CHARS:
                    return self._response(
                        answer=answer.strip(),
                        label="CIVIC ASSISTANT" if analysis.intent == "greeting_or_meta" else "SCOPE GUIDANCE",
                        limitation=localized_text(
                            query,
                            "SEN’TO focuses on Philippine senators, legislation, and civic records.",
                            "Nakatuon ang SEN’TO sa mga senador ng Pilipinas, mga batas, at pampublikong rekord.",
                        ),
                        topic=topic,
                        validation={"status": "CONVERSATIONAL_OK", "verified": False, "citation_ids": []},
                    )
            except Exception:
                pass

        try:
            _report_progress(progress_callback, "searching_sources")
            if analysis.intent == "general_civic":
                retrieved = []
            else:
                search_query = analysis.expanded_query
                retrieved = self.retriever.retrieve(
                    search_query,
                    senator["id"],
                    top_k=max(self.top_k, 5) if type(self.retriever).__name__ == "FixedRetriever" else min(10, self.top_k * 2),
                    relevant_period=relevant_period,
                    **({"congress_id": congress_id} if congress_id else {}),
                )
        except (EmbeddingError, VectorStoreError, GenerationError):
            return self._unavailable(topic, query)

        _report_progress(progress_callback, "checking_evidence")

        reranked = _rerank_documents(retrieved, analysis)
        context = []
        seen_chunks = set()
        evidence_chars = 0
        for document in reranked:
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

        topical_match = _has_topical_coverage(analysis.original_query, context, senator)
        if self.web_researcher is not None and (not context or not topical_match or analysis.needs_external_research):
            try:
                external_docs = self.web_researcher.search(
                    analysis.resolved_query,
                    senator=senator,
                    general_civic=(analysis.intent == "general_civic"),
                )
            except Exception:
                external_docs = []
            if external_docs:
                # If internal chunks had zero topical match (e.g. SOGIE / Israel not in Markdown),
                # prioritize external research results instead of confusing the model with off-topic chunks.
                if not topical_match:
                    context = []
                    evidence_chars = 0
                for doc in external_docs:
                    if len(context) >= MAX_RETRIEVED_CHUNKS + 2:
                        break
                    remaining = MAX_TOTAL_EVIDENCE_CHARS - evidence_chars
                    if remaining <= 80:
                        break
                    bounded_text = str(doc.get("text") or "")[:min(MAX_EVIDENCE_CHARS, remaining)]
                    if not bounded_text.strip() or not _usable_evidence(doc):
                        continue
                    context.append({
                        **doc,
                        "text": bounded_text,
                        "evidence_id": f"E{len(context) + 1}",
                    })
                    evidence_chars += len(bounded_text)

        if not context and analysis.intent == "general_civic":
            try:
                _report_progress(progress_callback, "writing_answer")
                civic_answer = self._call_generator(
                    query, senator, [], style,
                    query_analysis=analysis, history=history, allow_empty_context=True,
                )
                if isinstance(civic_answer, str) and civic_answer.strip() and len(civic_answer) <= MAX_ANSWER_CHARS:
                    return self._response(
                        answer=civic_answer.strip(),
                        label="CIVIC EDUCATION SUMMARY",
                        limitation=localized_text(
                            query,
                            "General Philippine civic explanation; verify current rules against official Senate or Official Gazette publications.",
                            "Pangkalahatang paliwanag sa proseso ng gobyerno; tiyakin ang kasalukuyang patakaran sa opisyal na publikasyon ng Senado o Official Gazette.",
                        ),
                        topic=topic,
                        validation={"status": "CIVIC_EXPLANATION", "verified": False, "citation_ids": []},
                    )
            except Exception:
                pass

        if not context:
            return self._response(
                answer=no_evidence_response(query, NO_EVIDENCE),
                label="NO CURATED EVIDENCE",
                limitation=no_evidence_limitation(
                    query,
                    "The current project-curated corpus has no passage that supports an answer to this question.",
                ),
                topic=topic,
                validation={"status": "INSUFFICIENT_EVIDENCE", "verified": False, "citation_ids": []},
            )

        try:
            _report_progress(progress_callback, "writing_answer")
            answer = self._call_generator(
                query, senator, context, style,
                query_analysis=analysis, history=history,
            )
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
                    "No source details could be attached to the generated answer.",
                    "Walang source details na maiuugnay sa nabuong sagot.",
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
                "Buod ito mula sa project-curated Markdown notes at hindi opisyal na pahayag ng Senado. Suriin ang citation at locator; maaaring hindi kumpleto ang dataset.",
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
