# Local RAG setup

The current local stack uses ChromaDB for persistent vector storage and Ollama for embeddings. It does not call a hosted embedding service. The Chroma `PersistentClient` writes under `data/corpus/processed/chroma/`; that directory is generated data and stays out of Git.

The Streamlit Chat page now calls the RAG pipeline through `frontend/api.py`. The current corpus is empty, so the pipeline abstains before generation and makes no LLM request until reviewed passages are indexed. See [SECURITY_ASSESSMENT.md](SECURITY_ASSESSMENT.md) for input, prompt, context, rate, and output controls and their limitations.

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

## Configure answer generation

Generation defaults to the local Ollama chat endpoint. Install the configured model with `ollama pull gemma4`. The provider is replaceable independently from the embedder and vector store.

To select OpenAI GPT-6 Luna, set these process environment variables:

```text
SENTO_GENERATOR_PROVIDER=openai
OPENAI_API_KEY=<your key, supplied through your local secrets manager>
OPENAI_BASE_URL=https://aiki-labs.up.railway.app/api/v1
SENTO_OPENAI_MODEL=gpt-6-luna
SENTO_OPENAI_REASONING_EFFORT=low
```

The adapter passes `OPENAI_BASE_URL` (or `SENTO_OPENAI_BASE_URL`) to the OpenAI SDK and sends Responses API requests to `{base_url}/responses`. The configured gateway must support the OpenAI Responses API and the model name in `SENTO_OPENAI_MODEL`; if its API supports only Chat Completions, this adapter will need a compatible provider implementation. The current default model remains `gpt-6-luna`; set it to a model name supported by your gateway. Ollama remains the separate embedding provider.

The app reads process environment variables and does not load `.env` itself. If your values are stored in a standard shell-compatible `.env`, make them available to the launch process from the project directory, then start Streamlit:

```sh
set -a
source .env
set +a
streamlit run app.py
```

This loads the variables into that shell session; it does not change the file. On another operating system, use that environment's standard way to export the variables before launching the app.

When OpenAI is selected and evidence is retrieved, SEN’TO sends the current question, selected senator name, retrieved passage text, and passage citation metadata to the configured API base URL. It does not send the rest of the session history. The request sets `store=false`, but this does not control retention by a third-party gateway; check that provider's data policy before sending records. Do not commit API keys. `.env.example` contains variable names only, and the app does not read `.env` automatically. Make the variables available in the process environment before starting Streamlit.

The generator sends only the current question and bounded retrieved evidence; it does not receive Streamlit's prior chat history. Local generation is configured with an 8,192-token context and a 700-token output ceiling; a conservative tokenizer-independent estimate rejects inputs that appear to exceed the prompt budget. OpenAI requests set a 700-token output ceiling and a 45-second client timeout. These values bound resource use but do not verify factual support. The UI currently limits a session to eight questions per rolling minute; a future server endpoint must apply its own shared rate limit because per-session limits can be bypassed by creating another session.

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
