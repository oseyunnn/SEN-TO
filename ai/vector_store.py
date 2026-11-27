"""Persistent Chroma indexing and senator-filtered vector retrieval."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Iterable

from ai.embeddings import EmbeddingProvider


class VectorStoreError(RuntimeError):
    """Vector index could not be read, written, or queried safely."""


def _citation_sources(chunk: dict) -> list[dict]:
    sources = chunk.get("citation_sources")
    if isinstance(sources, list) and sources:
        return sources
    if not chunk.get("source_url"):
        return []
    return [{
        "source_id": chunk.get("document_id") or chunk.get("chunk_id"),
        "title": chunk.get("title", "Untitled source"),
        "issuing_body": chunk.get("issuing_body", "Unknown issuing body"),
        "source_type": chunk.get("source_type", "official_record"),
        "source_url": chunk.get("source_url"),
        "publication_date": chunk.get("publication_date"),
        "retrieved_at": chunk.get("retrieved_at"),
        "relevant_period": chunk.get("relevant_period", "Not specified"),
        "locator": chunk.get("locator", "Document"),
        "verification_status": chunk.get("verification_status"),
    }]


def _prepare_chunks(chunks: Iterable[dict]) -> list[dict]:
    prepared: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for original in chunks:
        if not isinstance(original, dict):
            continue
        project_curated = original.get("curation_status") == "project_curated"
        if original.get("verification_status") != "verified" and not project_curated:
            continue
        chunk_id = original.get("chunk_id")
        text = original.get("text")
        if not isinstance(chunk_id, str) or not chunk_id or not isinstance(text, str) or not text.strip():
            continue
        sources = _citation_sources(original)
        if not sources or (not project_curated and any(source.get("verification_status") != "verified" for source in sources)):
            continue
        senator_ids = original.get("senator_ids") or []
        if original.get("senator_id"):
            senator_ids = [*senator_ids, original["senator_id"]]
        if not isinstance(senator_ids, list):
            continue
        for senator_id in dict.fromkeys(item for item in senator_ids if isinstance(item, str) and item):
            unique_key = (chunk_id, senator_id)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            record = dict(original)
            record["senator_id"] = senator_id
            record["senator_ids"] = [senator_id]
            record["citation_sources"] = sources
            record["source_ids"] = [source.get("source_id") for source in sources if source.get("source_id")]
            record.setdefault("curation_status", "verified_source")
            record["section"] = record.get("section") or record.get("record_type") or "Public record"
            record["relevant_period"] = record.get("relevant_period") or "Not specified"
            record["index_id"] = f"{chunk_id}::{senator_id}"
            prepared.append(record)
    return prepared


def read_jsonl(paths: Iterable[Path]) -> list[dict]:
    chunks: list[dict] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise VectorStoreError(f"{path.name}:{line_number} is not valid JSON.") from exc
                    if not isinstance(value, dict):
                        raise VectorStoreError(f"{path.name}:{line_number} must contain a JSON object.")
                    chunks.append(value)
        except OSError as exc:
            raise VectorStoreError(f"Could not read chunk file {path}: {exc}") from exc
    return chunks


def _metadata_for(record: dict) -> dict[str, str]:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
    return {
        "senator_id": record["senator_id"],
        "verification_status": str(record.get("verification_status") or "unknown"),
        "curation_status": str(record.get("curation_status") or "verified_source"),
        "relevant_period": str(record["relevant_period"]),
        "congress_id": str(record.get("congress_id") or ""),
        "section": str(record["section"]),
        "document_id": str(record.get("document_id") or ""),
        "source_sha256": str(record.get("source_sha256") or ""),
        "payload_json": payload,
    }


class ChromaVectorStore:
    """Chroma-backed store; embeddings remain injectable for tests and provider swaps."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        persist_directory: Path | str | None = None,
        collection_name: str | None = None,
        batch_size: int = 32,
        max_cosine_distance: float | None = None,
        collection=None,
        client=None,
        read_only=False,
        expected_metadata=None,
    ):
        self.embedder = embedder
        self.read_only = read_only
        self.persist_directory = Path(
            persist_directory or os.environ.get(
                "SENTO_CHROMA_PATH",
                Path(__file__).resolve().parents[1] / "data/corpus/processed/chroma",
            )
        )
        self.batch_size = max(1, int(batch_size))
        configured_distance = os.environ.get("SENTO_MAX_COSINE_DISTANCE", "0.65")
        self.max_cosine_distance = float(
            configured_distance if max_cosine_distance is None else max_cosine_distance
        )
        if not math.isfinite(self.max_cosine_distance) or not 0 <= self.max_cosine_distance <= 2:
            raise ValueError("SENTO_MAX_COSINE_DISTANCE must be between 0 and 2.")
        provider_name = getattr(embedder, "provider_name", "custom")
        provider_token = re.sub(r"[^a-zA-Z0-9_]+", "_", provider_name).strip("_").lower()[:8] or "provider"
        model_token = re.sub(r"[^a-zA-Z0-9_]+", "_", embedder.model_name).strip("_").lower()[:20] or "model"
        model_hash = hashlib.sha256(f"{provider_name}:{embedder.model_name}".encode("utf-8")).hexdigest()[:8]
        self.embedding_provider = provider_name
        self.collection_name = collection_name or f"sento_v1_{provider_token}_{model_token}_{model_hash}"
        if collection is not None or client is not None:
            self.client = client
            try:
                self.collection = collection if collection is not None else client.get_collection(name=self.collection_name, embedding_function=None)
            except Exception:
                raise VectorStoreError("The configured Chroma collection could not be opened.") from None
            self._validate_metadata(expected_metadata)
            return
        try:
            import chromadb
        except ImportError as exc:
            raise VectorStoreError("ChromaDB is required. Install the project dependencies first.") from exc
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(path=str(self.persist_directory), settings=Settings(anonymized_telemetry=False))
            if read_only:
                self.collection = self.client.get_collection(name=self.collection_name, embedding_function=None)
                self._validate_metadata(expected_metadata)
                return
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "schema_version": "1",
                    "embedding_provider": provider_name,
                    "embedding_model": embedder.model_name,
                },
                embedding_function=None,
            )
        except Exception as exc:
            raise VectorStoreError(f"Could not open the local Chroma index: {exc}") from exc
        self._validate_metadata(expected_metadata)

    def _validate_metadata(self, expected_metadata=None):
        collection_metadata = getattr(self.collection, "metadata", None) or {}
        stored_model = collection_metadata.get("embedding_model")
        stored_provider = collection_metadata.get("embedding_provider")
        if (stored_model and stored_model != self.embedder.model_name) or (
            stored_provider and stored_provider != self.embedding_provider
        ):
            raise VectorStoreError(
                "The saved Chroma collection uses a different embedding model. Choose a new collection name or rebuild the index."
            )

        if expected_metadata:
            if any(collection_metadata.get(key) != value for key, value in expected_metadata.items()):
                raise VectorStoreError("Collection release, schema or embedding identity does not match configuration.")
            if collection_metadata.get('publication_status') != 'ready':
                raise VectorStoreError("Collection publication is incomplete; keep the previous release active.")
            schema = getattr(self.collection, "schema", None)
            try:
                index = schema.keys['#embedding'].float_list.vector_index
                metric = index.config.space if index.enabled else None
            except (AttributeError, KeyError, TypeError):
                metric = None
            if metric != "cosine":
                raise VectorStoreError("The saved cloud vector index must use cosine distance.")

    def index_documents(self, chunks: Iterable[dict]) -> dict[str, int]:
        if self.read_only:
            raise VectorStoreError("Runtime collections are read-only.")
        records = _prepare_chunks(chunks)
        if not records:
            raise VectorStoreError("No verified, senator-linked, cited chunks are available to index.")
        desired_ids = {record["index_id"] for record in records}
        try:
            existing = self.collection.get(include=["metadatas"])
            existing_ids = set(existing.get("ids") or [])
            for offset in range(0, len(records), self.batch_size):
                batch = records[offset:offset + self.batch_size]
                vectors = self.embedder.embed([item["text"] for item in batch])
                if len(vectors) != len(batch):
                    raise VectorStoreError("Embedding provider returned the wrong number of vectors.")
                dimensions = {len(vector) for vector in vectors if isinstance(vector, list)}
                if len(dimensions) != 1 or any(not vector for vector in vectors):
                    raise VectorStoreError("Embedding provider returned empty or inconsistent vectors.")
                self.collection.upsert(
                    ids=[item["index_id"] for item in batch],
                    embeddings=vectors,
                    documents=[item["text"] for item in batch],
                    metadatas=[_metadata_for(item) for item in batch],
                )
            stale_ids = existing_ids - desired_ids
            if stale_ids:
                self.collection.delete(ids=sorted(stale_ids))
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"Could not update the local Chroma index: {exc}") from exc
        return {"indexed": len(records), "removed": len(stale_ids), "collection_count": int(self.collection.count())}

    def retrieve(
        self,
        query: str,
        senator_id: str,
        top_k: int = 5,
        relevant_period: str | None = None,
        congress_id: str | None = None,
    ) -> list[dict]:
        if not query or not query.strip() or not senator_id or top_k <= 0:
            return []
        try:
            total = int(self.collection.count())
            if total == 0:
                return []
            vector = self.embedder.embed([query])[0]
            filters = [
                {"senator_id": senator_id},
                {"$or": [
                    {"curation_status": "project_curated"},
                    {"verification_status": "verified"},
                ]},
            ]
            if relevant_period:
                filters.append({"relevant_period": relevant_period})
            if congress_id:
                filters.append({"congress_id": congress_id})
            result = self.collection.query(
                query_embeddings=[vector],
                n_results=min(top_k, total),
                where={"$and": filters},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"Could not query the local Chroma index: {exc}") from exc

        documents: list[dict] = []
        ids = (result.get("ids") or [[]])[0]
        texts = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        for row_id, text, metadata, distance in zip(ids, texts, metadatas, distances):
            if not isinstance(metadata, dict):
                continue
            try:
                record = json.loads(metadata["payload_json"])
            except (KeyError, TypeError, json.JSONDecodeError):
                continue
            if (
                record.get("senator_id") != senator_id
                or (record.get("curation_status") != "project_curated" and record.get("verification_status") != "verified")
                or (relevant_period and record.get("relevant_period") != relevant_period)
                or (congress_id and record.get("congress_id") != congress_id)
                or not text
                or distance is None
                or not math.isfinite(float(distance))
                or float(distance) > self.max_cosine_distance
            ):
                continue
            record["text"] = text
            record["retrieval"] = {
                "method": "chroma_cosine",
                "distance": float(distance),
                "embedding_model": self.embedder.model_name,
                "index_id": row_id,
            }
            documents.append(record)
        return documents

    def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception:
            raise VectorStoreError('The configured source service is unavailable.') from None

    @property
    def metadata(self):
        return self.collection.metadata
