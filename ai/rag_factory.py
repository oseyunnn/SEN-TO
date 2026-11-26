"""Build the configured local RAG pipeline with provider adapters."""

from __future__ import annotations

import os
from pathlib import Path

from ai.generation import (
    OllamaChatProvider,
    OpenAIResponsesProvider,
    RAGAnswerGenerator,
)
from ai.pipeline import RAGPipeline
from ai.validator import EvidenceValidator
from ai.vector_store import ChromaVectorStore, VectorStoreError
from ai.rag_config import RAGConfig
from threading import RLock


class ChromaRetriever:
    """Lazy vector-store wrapper so an empty corpus needs no model service."""

    def __init__(self, embedder, persist_directory: Path | str, config=None):
        self.embedder = embedder
        self.persist_directory = Path(persist_directory)
        self._store = None
        self.config = config
        self._lock = RLock()

    def _get_store(self):
        with self._lock:
            try:
                return self._open_store()
            except VectorStoreError:
                raise
            except Exception:
                raise VectorStoreError('The configured source service is unavailable.') from None

    def _open_store(self):
        if self._store is None:
            cloud = self.config and self.config.backend == "chroma_cloud"
            self._store = ChromaVectorStore(
                embedder=self.embedder,
                persist_directory=self.persist_directory,
                collection_name=(self.config.collection or None) if self.config else None,
                client=self.config.cloud_client() if cloud else None,
                read_only=True,
                expected_metadata=self.config.metadata() if cloud else None,
                max_cosine_distance=self.config.max_distance if self.config else None,
            )
        return self._store

    def retrieve(
        self,
        query: str,
        senator_id: str,
        top_k: int = 5,
        relevant_period: str | None = None,
        congress_id: str | None = None,
    ) -> list[dict]:
        if not (self.config and self.config.backend != "local") and not self.persist_directory.exists():
            return []
        store = self._get_store()
        if store.count() == 0:
            return []
        return store.retrieve(query, senator_id, top_k=top_k, relevant_period=relevant_period, congress_id=congress_id)

    def count_indexed(self) -> int:
        if not (self.config and self.config.backend != "local") and not self.persist_directory.exists():
            return 0
        return self._get_store().count()


class QdrantRetriever(ChromaRetriever):
    """Reuse lazy initialization, with no local path gate in cloud mode."""

    def _open_store(self):
        if self._store is None:
            from ai.qdrant_store import QdrantVectorStore
            self._store = QdrantVectorStore(self.embedder, self.config)
        return self._store


def build_retriever(config, embedder=None):
    retriever_type = QdrantRetriever if config.backend == 'qdrant_cloud' else ChromaRetriever
    return retriever_type(embedder or config.embedder(), config.path, config)


def build_default_pipeline(config=None) -> RAGPipeline:
    config = config or RAGConfig.load()
    ollama_base_url = os.environ.get("SENTO_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    embedder = config.embedder()
    retriever = build_retriever(config, embedder)

    provider_name = os.environ.get("SENTO_GENERATOR_PROVIDER", "ollama").strip().casefold()
    if provider_name == "ollama":
        provider = OllamaChatProvider(base_url=ollama_base_url)
    elif provider_name == "openai":
        provider = OpenAIResponsesProvider()
    else:
        raise ValueError("SENTO_GENERATOR_PROVIDER must be 'ollama' or 'openai'.")

    generator = RAGAnswerGenerator(provider)
    top_k = config.top_k
    return RAGPipeline(
        retriever=retriever,
        generator=generator,
        validator=EvidenceValidator(),
        top_k=top_k,
    )
