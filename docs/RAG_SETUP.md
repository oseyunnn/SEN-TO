# Local RAG setup

The current local stack uses ChromaDB for persistent vector storage and Ollama for embeddings. It does not call a hosted embedding service. The Chroma `PersistentClient` writes under `data/corpus/processed/chroma/`; that directory is generated data and stays out of Git.

## Configure Ollama embeddings

Install and start Ollama, then download the configured embedding model:

```sh
ollama pull embeddinggemma
```

The local API defaults to `http://127.0.0.1:11434`. Configure these environment variables when needed:

```text
SENTO_OLLAMA_BASE_URL=http://127.0.0.1:11434
SENTO_OLLAMA_EMBED_MODEL=embeddinggemma
SENTO_CHROMA_PATH=data/corpus/processed/chroma
SENTO_MAX_COSINE_DISTANCE=0.65
```

The Ollama embedding model name is part of the Chroma collection name. Changing it creates a separate collection rather than mixing vectors from different models. Tune the cosine-distance cutoff using reviewed questions; an empty retrieval is safer than passing weak matches to the generator. See the [Ollama embedding API](https://docs.ollama.com/api/embed) and [Chroma persistent client](https://docs.trychroma.com/docs/run-chroma/clients) documentation.

## Build the index

After adding and reviewing source records, create normalized chunks and build the local index:

```sh
python tools/ingest_documents.py
python tools/ingest_senator_records.py
python tools/index_corpus.py
```

Either chunk JSONL file may be empty; the index command combines both and fails clearly if there are no chunks. It indexes only verified chunks with a verified senator association and at least one verified citation. It skips unverified, unassociated, and uncited material.

To select a different index path or chunk file:

```sh
python tools/index_corpus.py --index /path/to/local/chroma --chunks data/corpus/processed/senator_chunks.jsonl
```

Do not put API keys in these local-index settings. The model-generation provider is selected separately by `SENTO_GENERATOR_PROVIDER`; see the RAG progress document for provider and data-flow status.
