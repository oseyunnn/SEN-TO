"""Embedding provider interfaces and the local Ollama adapter."""

from __future__ import annotations

import json
import math
import os
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmbeddingError(RuntimeError):
    """Embedding provider failed or returned invalid vectors."""


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


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
