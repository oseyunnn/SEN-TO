import pytest
from backend.chatbot_service import ChatbotService
from ai.pipeline import RAGPipeline
from ai.retriever import MockRetriever
from ai.validator import MockFactValidator, format_citations


def test_selection_and_missing(senators):
    assert senators.get("risa-hontiveros")["minority_membership"] == "Unverified"
    assert len(senators.search("RISa")) == 1
    assert senators.search("nonexistent") == []
    with pytest.raises(ValueError):
        senators.get("not-a-senator")


def test_response_and_sources(senators):
    bot = ChatbotService(senators)
    bills = bot.ask("What bills has she authored?", "risa-hontiveros")
    votes = bot.ask("What is the voting record?", "risa-hontiveros")
    assert bills["answer"] != votes["answer"]
    assert "Risa Hontiveros" in bills["answer"]
    assert bills["validation"]["status"] == "DEMO_SUPPORTED"
    assert not bills["validation"]["verified"]
    assert all(c["url"] is None for c in bills["citations"])
    assert "SIMULATED" in bills["label"]


def test_fallback_and_missing_evidence(senators):
    bot = ChatbotService(senators, RAGPipeline(retriever=MockRetriever([])))
    response = bot.ask("bills", "risa-hontiveros")
    assert "not covered" in response["answer"]
    assert response["validation"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert response["citations"] == []
    assert "not covered" in ChatbotService().ask("bake a cake", "risa-hontiveros")["answer"]


def test_unsupported_answer_is_not_supported():
    docs = MockRetriever().retrieve("bills", "risa-hontiveros")
    assert MockFactValidator().validate("Invented accomplishment", docs)["status"] == "INSUFFICIENT_EVIDENCE"
    docs[0]["source_url"] = "https://invented.invalid"
    assert format_citations(docs)[0]["url"] is None


def test_injected_retriever_cannot_leak_context(senators):
    class WrongRetriever:
        def retrieve(self, *args):
            return MockRetriever().retrieve("bills", "francis-pangilinan")
    response = ChatbotService(senators, RAGPipeline(retriever=WrongRetriever())).ask("bills", "risa-hontiveros")
    assert response["retrieval_count"] == 0


@pytest.mark.parametrize("query", ["", " ", "x" * 4001])
def test_invalid_question(query):
    with pytest.raises(ValueError):
        ChatbotService().ask(query, "risa-hontiveros")
