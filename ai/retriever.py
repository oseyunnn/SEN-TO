from backend.senator_service import read_json
from ai.intent_classifier import classify, preprocess


class MockRetriever:
    def __init__(self, documents=None):
        self.documents = read_json("mock_documents.json") if documents is None else documents

    def retrieve(self, query, senator_id, top_k=3):
        topic = classify(query)
        if topic == "unknown" or top_k <= 0:
            return []
        tokens = set(preprocess(query).split())
        hits = []
        for doc in self.documents:
            if doc["senator_id"] != senator_id or doc["topic"] != topic:
                continue
            overlap = len(tokens & set(preprocess(doc["content"] + " " + doc["title"]).split()))
            hits.append({**doc, "retrieval": {"method": "demo_topic_and_token_overlap", "topic": topic,
                                            "score": 1 + overlap, "real_world_verified": False}})
        return sorted(hits, key=lambda d: d["retrieval"]["score"], reverse=True)[:top_k]
