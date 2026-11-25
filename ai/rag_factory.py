"""Build the configured local RAG pipeline with provider adapters."""

from __future__ import annotations

import os
from pathlib import Path

from ai.embeddings import OllamaEmbeddingProvider
from ai.generation import (
    OllamaChatProvider,
    OpenAIResponsesProvider,
    RAGAnswerGenerator,
)
from ai.pipeline import RAGPipeline
from ai.validator import EvidenceValidator
from ai.vector_store import ChromaVectorStore


class ChromaRetriever:
    """Lazy vector-store wrapper so an empty corpus needs no model service."""

    def __init__(self, embedder, persist_directory: Path | str):
        self.embedder = embedder
        self.persist_directory = Path(persist_directory)
        self._store = None

    def _get_store(self):
        if self._store is None:
            self._store = ChromaVectorStore(
                embedder=self.embedder,
                persist_directory=self.persist_directory,
            )
        return self._store

    def retrieve(
        self,
        query: str,
        senator_id: str,
        top_k: int = 5,
        relevant_period: str | None = None,
    ) -> list[dict]:
        if not self.persist_directory.exists():
            return []
        store = self._get_store()
        if store.count() == 0:
            return []
        return store.retrieve(query, senator_id, top_k=top_k, relevant_period=relevant_period)

    def count_indexed(self) -> int:
        if not self.persist_directory.exists():
            return 0
        return self._get_store().count()


def build_default_pipeline() -> RAGPipeline:
    project_root = Path(__file__).resolve().parents[1]
    embedding_model = os.environ.get("SENTO_OLLAMA_EMBED_MODEL", "embeddinggemma")
    ollama_base_url = os.environ.get("SENTO_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    persist_directory = Path(os.environ.get(
        "SENTO_CHROMA_PATH",
        project_root / "data/corpus/processed/chroma",
    ))
    embedder = OllamaEmbeddingProvider(model=embedding_model, base_url=ollama_base_url)
    retriever = ChromaRetriever(embedder, persist_directory)

    provider_name = os.environ.get("SENTO_GENERATOR_PROVIDER", "ollama").strip().casefold()
    if provider_name == "ollama":
        provider = OllamaChatProvider(base_url=ollama_base_url)
    elif provider_name == "openai":
        provider = OpenAIResponsesProvider()
    else:
        raise ValueError("SENTO_GENERATOR_PROVIDER must be 'ollama' or 'openai'.")

    generator = RAGAnswerGenerator(provider)
    top_k = int(os.environ.get("SENTO_RETRIEVAL_TOP_K", "5"))
    return RAGPipeline(
        retriever=retriever,
        generator=generator,
        validator=EvidenceValidator(),
        top_k=top_k,
    )
