"""Embedding provider interfaces and the local Ollama adapter."""

from __future__ import annotations

import json
import math
import os
from typing import Protocol
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmbeddingError(RuntimeError):
    """Embedding provider failed or returned invalid vectors."""


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    """Explicit hosted embeddings, with bounded requests and strict response validation."""
    provider_name = "openai"

    def __init__(self, *, api_key, base_url, model="text-embedding-3-small", dimensions=1536, client=None):
        if model != "text-embedding-3-small" or dimensions != 1536:
            raise ValueError("Hosted embeddings require text-embedding-3-small / 1536.")
        self._model, self.dimensions = model, dimensions
        self.client = client
        self._client_lock = RLock()
        self._api_key, self.base_url = api_key, base_url

    @property
    def model_name(self):
        return self._model

    def embed(self, texts):
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingError("Embedding inputs must be nonempty strings.")
        try:
            with self._client_lock:
                if self.client is None:
                    if not self._api_key:
                        raise EmbeddingError("Hosted embedding credentials are missing.")
                    from openai import OpenAI
                    self.client = OpenAI(api_key=self._api_key, base_url=self.base_url, timeout=45, max_retries=0)
            response = self.client.embeddings.create(model=self.model_name, input=texts, dimensions=self.dimensions)
            rows = response.data
            if len(rows) != len(texts) or sorted(row.index for row in rows) != list(range(len(texts))):
                raise EmbeddingError("Unexpected embedding count or indexes.")
            vectors = []
            for row in sorted(rows, key=lambda row: row.index):
                vector = row.embedding
                if len(vector) != self.dimensions or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
                    raise EmbeddingError("Malformed embedding dimensions or numeric values.")
                vectors.append([float(v) for v in vector])
            return vectors
        except EmbeddingError:
            raise
        except Exception:
            raise EmbeddingError("The hosted embedding service is unavailable.") from None


class OllamaEmbeddingProvider:
    """Call Ollama's local /api/embed endpoint without coupling Chroma to Ollama."""

    provider_name = "ollama"

    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: float = 60):
        self._model = model or os.environ.get("SENTO_OLLAMA_EMBED_MODEL", "embeddinggemma")
        self.base_url = (base_url or os.environ.get("SENTO_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout
        if not self._model.strip():
            raise ValueError("SENTO_OLLAMA_EMBED_MODEL must name an installed Ollama embedding model.")

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding inputs must be non-empty strings.")
        request_body = json.dumps({"model": self._model, "input": texts}).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/embed",
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise EmbeddingError(
                "Could not obtain embeddings from Ollama. Confirm it is running and the configured model is installed."
            ) from exc

        vectors = payload.get("embeddings") if isinstance(payload, dict) else None
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingError("Ollama returned an unexpected embedding count.")
        dimension = None
        normalized: list[list[float]] = []
        for vector in vectors:
            if not isinstance(vector, list) or not vector:
                raise EmbeddingError("Ollama returned an empty or malformed embedding.")
            try:
                values = [float(value) for value in vector]
            except (TypeError, ValueError) as exc:
                raise EmbeddingError("Ollama returned a non-numeric embedding value.") from exc
            if not all(math.isfinite(value) for value in values):
                raise EmbeddingError("Ollama returned a non-finite embedding value.")
            if dimension is None:
                dimension = len(values)
            elif len(values) != dimension:
                raise EmbeddingError("Ollama returned vectors with inconsistent dimensions.")
            normalized.append(values)
        return normalized
