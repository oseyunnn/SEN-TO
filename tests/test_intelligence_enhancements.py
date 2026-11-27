"""Tests for intent-aware query understanding, hybrid reranking, web research, and fallbacks."""

from ai.pipeline import RAGPipeline, _rerank_documents
from ai.query_understanding import analyze_query
from ai.web_research import WebResearcher, _is_public_https_url, _source_tier
from backend.chatbot_service import ChatbotService


def _senator():
    return {"id": "risa-hontiveros", "name": "Risa Hontiveros"}


class _CapturingGenerator:
    def __init__(self, reply="Here is a clear summary. [E1]"):
        self.reply = reply
        self.calls = []

    def generate(self, query, senator, context, style, *, query_analysis=None, history=None, allow_empty_context=False):
        self.calls.append({
            "query": query,
            "context_ids": [c.get("chunk_id") for c in context],
            "intent": getattr(query_analysis, "intent", None),
            "history": history,
            "allow_empty_context": allow_empty_context,
        })
        return self.reply


class _StaticRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.queries = []

    def retrieve(self, query, senator_id, top_k=5, relevant_period=None, congress_id=None):
        self.queries.append(query)
        return self.docs[:top_k]


class _FakeWebResearcher:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    def search(self, query, senator=None, *, general_civic=False):
        self.calls.append((query, general_civic))
        return self.docs


def test_query_understanding_intents_and_expansion():
    sen = _senator()
    assert analyze_query("How does a bill become a law in the Philippines?", sen).intent == "general_civic"
    assert analyze_query("What controversies surround this senator?", sen).intent == "controversy_accountability"
    assert analyze_query("Is she actually doing her job?", sen).intent == "performance_evaluation"
    assert analyze_query("Hello!", sen).intent == "greeting_or_meta"

    students = analyze_query("What has she done for students?", sen)
    assert "education" in students.expanded_query.lower()
    assert "scholarship" in students.expanded_query.lower()


def test_follow_up_resolution_uses_recent_history():
    history = [
        {"role": "user", "content": "What bills did Risa Hontiveros author?"},
        {"role": "assistant", "response": {"answer": "She authored the Mental Health Act (RA 11036) and Safe Spaces Act."}},
    ]
    analysis = analyze_query("Which ones actually became law?", _senator(), history=history)
    assert analysis.is_follow_up is True
    assert analysis.intent == "follow_up"
    assert "Mental Health Act" in analysis.resolved_query


def test_reranker_prioritizes_verified_official_and_lexical_match():
    analysis = analyze_query("Mental Health Act RA 11036", _senator())
    unverified = {
        "chunk_id": "c1",
        "text": "General statement about health.",
        "evidence_status": "UNVERIFIED",
        "citation_sources": [{"source_type": "secondary_news"}],
        "retrieval": {"distance": 0.35},
    }
    verified_official = {
        "chunk_id": "c2",
        "text": "Risa Hontiveros authored the Mental Health Act (RA 11036).",
        "evidence_status": "VERIFIED",
        "citation_sources": [{"source_type": "official_record"}],
        "retrieval": {"distance": 0.40},
    }
    ranked = _rerank_documents([unverified, verified_official], analysis)
    assert ranked[0]["chunk_id"] == "c2"


def test_general_civic_question_does_not_return_no_curated_evidence(senators):
    gen = _CapturingGenerator(reply="In the Philippines, a bill passes three readings in both chambers before presidential action.")
    bot = ChatbotService(senators, RAGPipeline(_StaticRetriever([]), gen))
    resp = bot.ask("How does a bill become a law in the Philippines?", "risa-hontiveros")
    assert resp["label"] == "CIVIC EDUCATION SUMMARY"
    assert "three readings" in resp["answer"]
    assert gen.calls[0]["allow_empty_context"] is True


def test_external_web_research_triggers_when_internal_empty(senators):
    ext_doc = {
        "chunk_id": "web-1",
        "senator_id": "risa-hontiveros",
        "curation_status": "external_research",
        "verification_status": "external_retrieved",
        "section": "Official external source",
        "text": "Senate of the Philippines official committee directory lists Risa Hontiveros.",
        "citation_sources": [{
            "source_id": "WEB-1",
            "title": "Senate Directory",
            "issuing_body": "senate.gov.ph",
            "source_type": "official_record",
            "source_url": "https://web.senate.gov.ph/senators/sen_bio/hontiveros_bio.asp",
            "verification_status": "external_retrieved",
        }],
    }
    gen = _CapturingGenerator(reply="She serves on Senate committees listed in the official directory. [E1]")
    web = _FakeWebResearcher([ext_doc])
    bot = ChatbotService(senators, RAGPipeline(_StaticRetriever([]), gen, web_researcher=web))
    resp = bot.ask("What committees does she currently chair?", "risa-hontiveros")
    assert resp["label"] == "SOURCE-GROUNDED AI SUMMARY"
    assert len(resp["citations"]) == 1
    assert resp["citations"][0]["url"] == "https://web.senate.gov.ph/senators/sen_bio/hontiveros_bio.asp"


def test_web_researcher_source_hierarchy_and_url_safety():
    assert _source_tier("https://senate.gov.ph/lis/bill.aspx")[0] == 1
    assert _source_tier("https://www.rappler.com/nation/test")[0] == 2
    assert _source_tier("https://random-blog.example.com/post")[0] == 99
    assert _is_public_https_url("https://senate.gov.ph") is True
    assert _is_public_https_url("http://senate.gov.ph") is False
    assert _is_public_https_url("https://127.0.0.1/admin") is False
    assert WebResearcher(enabled=False).search("test", _senator()) == []
