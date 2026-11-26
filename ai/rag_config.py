"""Validated deployment settings. Never loads .env or includes secrets in repr."""
from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


@dataclass(frozen=True)
class RAGConfig:
    backend: str
    collection: str
    release: str
    embedding_provider: str
    embedding_model: str
    dimensions: int
    embedding_base_url: str
    tenant: str
    database: str
    host: str
    path: str
    top_k: int
    max_distance: float
    qdrant_url: str = ''

    @classmethod
    def load(cls, *, require_credentials=True):
        env = os.environ
        backend = env.get('SENTO_VECTOR_BACKEND', 'local')
        if backend not in {'local', 'chroma_cloud', 'qdrant_cloud'}:
            raise ValueError('SENTO_VECTOR_BACKEND must be local, chroma_cloud or qdrant_cloud.')
        cloud = backend != 'local'
        qdrant = backend == 'qdrant_cloud'
        collection_key = 'SENTO_QDRANT_COLLECTION' if qdrant else 'SENTO_CHROMA_COLLECTION'
        provider = env.get('SENTO_EMBEDDING_PROVIDER', 'openai' if cloud else 'ollama')
        if provider not in {'openai', 'ollama'}:
            raise ValueError('SENTO_EMBEDDING_PROVIDER must be openai or ollama.')
        model = env.get('SENTO_EMBEDDING_MODEL', 'text-embedding-3-small' if provider == 'openai' else env.get('SENTO_OLLAMA_EMBED_MODEL', 'embeddinggemma'))
        try:
            dimensions = int(env.get('SENTO_EMBEDDING_DIMENSIONS', '1536' if provider == 'openai' else '0'))
            top_k = int(env.get('SENTO_RETRIEVAL_TOP_K', '5'))
            distance = float(env.get('SENTO_MAX_COSINE_DISTANCE', '.65'))
        except ValueError:
            raise ValueError('Embedding dimensions, top K and cosine distance must be numeric.') from None
        if not 1 <= top_k <= 5 or not math.isfinite(distance) or not 0 <= distance <= 2:
            raise ValueError('Top K must be 1–5 and cosine distance must be 0–2.')
        if provider == 'openai' and (model != 'text-embedding-3-small' or dimensions != 1536):
            raise ValueError('This release requires text-embedding-3-small with 1536 dimensions.')
        embedding_url = env.get('SENTO_EMBEDDING_BASE_URL', 'https://api.openai.com/v1')
        if provider == 'openai':
            parsed = urlsplit(embedding_url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Hosted embeddings require an explicit HTTPS base URL without credentials or query parameters.')
        if cloud:
            required = [collection_key, 'SENTO_RELEASE_ID']
            required += ['SENTO_QDRANT_URL'] if qdrant else ['CHROMA_TENANT', 'CHROMA_DATABASE']
            if require_credentials:
                required += ['QDRANT_API_KEY' if qdrant else 'CHROMA_API_KEY', 'OPENAI_API_KEY']
            if any(not env.get(key, '').strip() for key in required):
                raise ValueError('Cloud configuration is incomplete. Check collection, release, connection settings and private credentials.')
            if provider != 'openai' or env.get('SENTO_GENERATOR_PROVIDER') != 'openai':
                raise ValueError('Cloud mode requires hosted OpenAI embeddings and generation; no local fallback is allowed.')
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{1,125}[a-zA-Z0-9]', env[collection_key]):
                raise ValueError('Invalid cloud collection name.')
        qdrant_url = env.get('SENTO_QDRANT_URL', '').rstrip('/')
        if qdrant:
            try:
                parsed = urlsplit(qdrant_url)
                safe = (parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
                        and not parsed.query and not parsed.fragment and not parsed.path and parsed.port in (None, 443, 6333))
            except ValueError:
                safe = False
            if not safe:
                raise ValueError('SENTO_QDRANT_URL must be an HTTPS endpoint without credentials, path or query.')
        return cls(backend, env.get(collection_key, ''), env.get('SENTO_RELEASE_ID', ''),
                   provider, model, dimensions, embedding_url,
                   env.get('CHROMA_TENANT', ''), env.get('CHROMA_DATABASE', ''), env.get('CHROMA_HOST', 'api.trychroma.com'),
                   env.get('SENTO_CHROMA_PATH', str(Path(__file__).resolve().parents[1] / 'data/corpus/processed/chroma')),
                   top_k, distance, qdrant_url)

    def embedder(self):
        from ai.embeddings import OpenAIEmbeddingProvider, OllamaEmbeddingProvider
        if self.embedding_provider == 'openai':
            return OpenAIEmbeddingProvider(api_key=os.environ.get('OPENAI_API_KEY'), base_url=self.embedding_base_url,
                                           model=self.embedding_model, dimensions=self.dimensions)
        return OllamaEmbeddingProvider(model=self.embedding_model)

    def cloud_client(self):
        if self.backend == 'qdrant_cloud':
            from qdrant_client import QdrantClient
            return QdrantClient(url=self.qdrant_url, api_key=os.environ.get('QDRANT_API_KEY'),
                                port=443 if urlsplit(self.qdrant_url).port is None else urlsplit(self.qdrant_url).port,
                                timeout=45, prefer_grpc=False, check_compatibility=False)
        import chromadb
        from chromadb.config import Settings
        return chromadb.CloudClient(tenant=self.tenant, database=self.database,
                                    api_key=os.environ.get('CHROMA_API_KEY'), cloud_host=self.host,
                                    settings=Settings(anonymized_telemetry=False))

    def metadata(self):
        return {'schema_version': '2', 'embedding_provider': self.embedding_provider,
                'embedding_model': self.embedding_model, 'embedding_dimensions': self.dimensions,
                'release_id': self.release, 'distance_metric': 'cosine'}
