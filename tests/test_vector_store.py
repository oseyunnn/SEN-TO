import json

import pytest

from ai.embeddings import EmbeddingError, OllamaEmbeddingProvider
from ai.vector_store import ChromaVectorStore, VectorStoreError, read_jsonl


class FakeEmbedder:
    model_name = "test-embeddings-v1"

    def embed(self, texts):
        vectors = []
        for text in texts:
            folded = text.casefold()
            if "education" in folded:
                vectors.append([1.0, 0.0, 0.0])
            elif "voting" in folded:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def chunk(chunk_id, text, senator_ids, *, status="verified", period="20th Congress"):
    return {
        "chunk_id": chunk_id,
        "document_id": f"doc-{chunk_id}",
        "text": text,
        "senator_ids": senator_ids,
        "section": "Biography",
        "record_type": "senator_profile_claim",
        "verification_status": status,
        "relevant_period": period,
        "source_sha256": f"hash-{chunk_id}",
        "citation_sources": [{
            "source_id": f"source-{chunk_id}",
            "title": f"Source for {chunk_id}",
            "issuing_body": "Senate of the Philippines",
            "source_type": "official_record",
            "source_url": "https://senate.gov.ph/record.pdf",
            "publication_date": "2026-01-02",
            "retrieved_at": "2026-11-25",
            "relevant_period": period,
            "locator": "p. 1",
            "verification_status": "verified",
        }],
    }


def test_chroma_index_retrieves_verified_chunks_for_selected_senator(tmp_path):
    store = ChromaVectorStore(FakeEmbedder(), tmp_path / "chroma", collection_name="test-records")
    stats = store.index_documents([
        chunk("education-a", "Education program record", ["alpha"]),
        chunk("voting-a", "Voting record", ["alpha"]),
        chunk("education-b", "Education record", ["beta"]),
        chunk("unverified", "Education rumor", ["alpha"], status="candidate_source"),
    ])

    hits = store.retrieve("education history", "alpha", top_k=5)

    assert stats == {"indexed": 3, "removed": 0, "collection_count": 3}
    assert [item["chunk_id"] for item in hits] == ["education-a"]
    assert hits[0]["citation_sources"][0]["source_url"] == "https://senate.gov.ph/record.pdf"
    assert hits[0]["retrieval"]["method"] == "chroma_cosine"
    assert store.retrieve("education", "missing") == []


def test_index_expands_shared_record_and_enforces_period_filter(tmp_path):
    store = ChromaVectorStore(FakeEmbedder(), tmp_path / "chroma", collection_name="shared-records")
    store.index_documents([
        chunk("shared", "Education record", ["alpha", "beta"], period="19th Congress"),
        chunk("other-period", "Education record", ["alpha"], period="20th Congress"),
    ])

    assert store.count() == 3
    assert store.retrieve("education", "alpha", relevant_period="19th Congress")[0]["chunk_id"] == "shared"
    assert store.retrieve("education", "alpha", relevant_period="18th Congress") == []


def test_reindex_removes_stale_chunk_ids(tmp_path):
    store = ChromaVectorStore(FakeEmbedder(), tmp_path / "chroma", collection_name="refresh-records")
    store.index_documents([chunk("old", "Education record", ["alpha"]), chunk("keep", "Voting record", ["alpha"])])

    stats = store.index_documents([chunk("keep", "Voting record", ["alpha"])])

    assert stats == {"indexed": 1, "removed": 1, "collection_count": 1}
    assert store.retrieve("education", "alpha") == []


def test_rejects_empty_unlinked_or_unverified_index_input(tmp_path):
    store = ChromaVectorStore(FakeEmbedder(), tmp_path / "chroma", collection_name="empty-records")
    with pytest.raises(VectorStoreError, match="No verified"):
        store.index_documents([chunk("bad", "No source", [], status="candidate_source")])


def test_read_jsonl_reports_bad_rows(tmp_path):
    path = tmp_path / "chunks.jsonl"
    path.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(VectorStoreError, match="not valid JSON"):
        read_jsonl([path])


def test_ollama_embedder_posts_batch_and_checks_response(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"embeddings": [[0.1, 0.2], [0.3, 0.4]]}).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("ai.embeddings.urlopen", fake_urlopen)
    provider = OllamaEmbeddingProvider(model="embeddinggemma", base_url="http://localhost:11434")

    assert provider.embed(["first", "second"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["body"] == {"model": "embeddinggemma", "input": ["first", "second"]}


def test_ollama_embedder_rejects_bad_vector_count(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"embeddings": [[0.1]]}'

    monkeypatch.setattr("ai.embeddings.urlopen", lambda *args, **kwargs: Response())
    provider = OllamaEmbeddingProvider(model="embeddinggemma", base_url="http://localhost:11434")
    with pytest.raises(EmbeddingError, match="embedding count"):
        provider.embed(["one", "two"])
