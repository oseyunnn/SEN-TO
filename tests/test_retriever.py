import pytest
from ai.intent_classifier import classify
from ai.retriever import MockRetriever


@pytest.mark.parametrize("query,topic", [
    ("Educational background?", "education"), ("Authored bills", "bills"),
    ("Committee memberships", "committees"), ("Voting record", "votes"),
    ("Public statements", "statements"), ("Documented positions", "positions"),
    ("Legislative contributions", "legislation"), ("Political experience", "career"),
    ("Senate procedures", "procedures"), ("Chocolate cake recipe", "unknown"),
])
def test_intents(query, topic):
    assert classify(query) == topic


def test_context_isolation(senators):
    retriever = MockRetriever()
    # The frontend roster is broader than the small, unverified mock corpus.
    # Check isolation only for entries that actually have mock documents.
    documented_senators = {doc["senator_id"] for doc in retriever.documents}
    assert documented_senators
    for senator_id in documented_senators:
        docs = retriever.retrieve("What bills were authored?", senator_id)
        assert docs
        assert all(d["senator_id"] == senator_id and d["topic"] == "bills" for d in docs)
        assert all(not d["retrieval"]["real_world_verified"] for d in docs)


def test_empty_and_unknown():
    assert MockRetriever([]).retrieve("bills", "risa-hontiveros") == []
    assert MockRetriever().retrieve("pasta", "risa-hontiveros") == []
    assert MockRetriever().retrieve("bills", "missing") == []
    assert MockRetriever().retrieve("bills", "risa-hontiveros", top_k=0) == []
