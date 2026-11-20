from ai.prompts import FALLBACK


class MockFactValidator:
    def validate(self, answer, retrieved_documents):
        supported = bool(retrieved_documents) and answer != FALLBACK and all(
            d["content"] in answer and d.get("verification_status") == "unverified_demo"
            and d.get("source_type") == "simulation" for d in retrieved_documents
        )
        return {"status": "DEMO_SUPPORTED" if supported else "INSUFFICIENT_EVIDENCE",
                "real_world_status": "UNVERIFIED_DEMO", "verified": False}


def format_citations(documents):
    # No link for missing URLs; simulation documents can never acquire official-looking links.
    return [{"document_id": d["document_id"], "title": d["title"],
             "publication_date": d.get("publication_date"), "agency": d.get("agency"),
             "bill_number": d.get("bill_number"), "retrieval_date": d.get("retrieval_date"),
             "url": None if d.get("source_type") == "simulation" else d.get("source_url"),
             "source_type": d["source_type"]} for d in documents]
