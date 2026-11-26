# RAG setup and publication

**Selected deployment:** Qdrant Cloud. Follow [QDRANT_SETUP.md](QDRANT_SETUP.md) for the cluster, Streamlit Secrets, publishing credentials and release steps. The hosted Chat path is Qdrant-only; local Chroma and the Chroma Cloud adapter remain maintenance alternatives. Evidence-review requirements apply to every backend.

Use Python 3.12 and install requirements.txt. The hosted Chat runtime reads its settings directly from root-level Streamlit Secrets and requires hosted embeddings/generation plus an existing Qdrant Cloud collection. It never reads a local secrets file or process environment, publishes evidence, or falls back to a local service. Local development and maintenance CLI configuration remain separate.

## Cloud settings

Enter root-level TOML values in the existing Streamlit app's Settings → Secrets. Never commit or create a local runtime secrets file. Collection and release values stay blank until an approved release has been published and checked:

```toml
SENTO_VECTOR_BACKEND = "qdrant_cloud"
SENTO_QDRANT_URL = "https://d9b16d6d-d989-4240-9c8c-cecffb5f36e1.ap-northeast-2-0.aws.cloud.qdrant.io"
SENTO_QDRANT_COLLECTION = "<published collection>"
SENTO_RELEASE_ID = "<published release>"
SENTO_QDRANT_READ_ONLY_API_KEY = "<sento-app read-only key>"
SENTO_EMBEDDING_PROVIDER = "openai"
SENTO_EMBEDDING_MODEL = "text-embedding-3-small"
SENTO_EMBEDDING_DIMENSIONS = "1536"
SENTO_EMBEDDING_BASE_URL = "https://api.openai.com/v1"
SENTO_GENERATOR_PROVIDER = "openai"
OPENAI_API_KEY = "<private OpenAI credential>"
OPENAI_BASE_URL = "https://api.openai.com/v1"
SENTO_OPENAI_MODEL = "gpt-6-luna"
SENTO_OPENAI_REASONING_EFFORT = "low"
SENTO_RETRIEVAL_TOP_K = "5"
SENTO_MAX_COSINE_DISTANCE = "0.65"
SENTO_GLOBAL_REQUEST_LIMIT = "30"
SENTO_GLOBAL_REQUEST_WINDOW_SECONDS = "60"
```

Model access must be checked before rollout. An existing gateway credential is not assumed to work at OpenAI. Embedding and generation endpoints are configured separately. A model or dimension change requires a newly embedded collection. Missing cloud settings, incompatible collections or service failures never fall back to local storage or Ollama.

The UI allows eight submitted questions per session per rolling minute. The cloud RAG pipeline also allows thirty retrieval requests per app process per rolling minute, shared across users on that process. Exact repeat answers are cached only in the current session for up to ten minutes and 32 entries, keyed by the question, subject, period, release, model, style and prompt version. Cache hits skip query embedding, Qdrant search and generation. The app-process limit resets on restart and is not a monthly spending cap; configure OpenAI usage limits and alerts separately.

The runtime uses OpenAI-supplied vectors in Qdrant Cloud with cosine search, schema/release checks and read-only query methods. `SENTO_QDRANT_READ_ONLY_API_KEY` is the only Qdrant credential name accepted from app Secrets. Confirm it has the Read Cluster role in the Qdrant dashboard; runtime naming cannot verify a key's server-side permissions. Keep publisher credentials in a separate maintainer environment. The app reads Streamlit Secrets directly through `st.secrets`; see [Streamlit Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Review and prepare a release

The pilot is one majority and one minority senator, selected only after current dated authoritative checks. All 24 research profiles remain available for future work. VERIFIED in a profile means importer eligibility, not independent verification.

Run the importer and inspect original sources. Fill data/releases/demo-r1/review.json with subjects, reviewed_at and decisions. Each approval needs:

Also supply a scope_review array with exactly two entries. Each entry needs senator_id, bloc (majority or minority), reviewer, reviewed_at, as_of, and source. The source object needs title, issuing_body, source_url, publication_date when available, retrieved_at, relevant_period, locator and verification_status=verified. This records the dated original-source basis for pilot selection; it is distinct from the claim approvals below.

```json
{
  "senator_id": "<directory ID>",
  "claim_id": "<exact CLM ID>",
  "decision": "approved",
  "reviewer": "<human reviewer>",
  "reviewed_at": "YYYY-MM-DD",
  "source_sha256": "<SHA-256 of exact profile bytes>",
  "congress_id": "20",
  "period_basis": "<original record and locator establishing Congress>",
  "sources": [{"source_url": "<original HTTPS URL>", "locator": "<exact locator>"}]
}
```

Use 19, 20, or historical for the normalized field. Preserve the raw period in citations. Record excluded/conflicting/stale decisions separately; only explicit approvals export. The profile checksum is not an original-webpage checksum. Retain archived-original checksums separately. A changed profile requires review again.

```sh
python tools/ingest_senator_records.py
python tools/prepare_corpus_release.py --chunks data/corpus/processed/senator_chunks.jsonl --review-register data/releases/demo-r1/review.json --output-dir data/releases/demo-r1
```

Output includes chunks, review register and manifest with approved IDs, source/importer identity, checksums and expanded per-subject counts. Export refuses missing approvals, changed bytes, incomplete provenance and out-of-scope associations. The committed starter register approves nothing and deliberately fails this gate. Never substitute a fictitious reviewer to make it pass.

## Publish a new candidate

In the maintainer environment, use matching Qdrant deployment settings and set `SENTO_ACTIVE_COLLECTION` to the serving collection, or `NONE` for first publication. Set `SENTO_QDRANT_COLLECTION` to a new candidate name. Do not change the running app yet. See [QDRANT_SETUP.md](QDRANT_SETUP.md) for the separate publisher settings and exact commands.

```sh
python tools/index_corpus.py --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json --dry-run
python tools/index_corpus.py --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json --apply
python tools/check_rag.py --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json
```

Dry run validates local hashes, approved IDs, counts and provider identity without connecting or embedding. Apply creates a Qdrant collection; it cannot overwrite an existing name or the declared active collection. Writes use batches of 32. Failed uploads remain building, which runtime rejects. Retry with a new candidate name and matching manifest; never refresh a live collection with one senator's subset. The checker paginates IDs and verifies complete metadata without paid model calls. Ready means upload verification passed, not human answer review.

Run five supported and three unsupported questions per enabled senator, covering English, Filipino and Taglish. Record sentence-by-sentence human support checks in questions.json. Tune retrieval against these reviewed questions. Verify isolation, stale/current distinctions, citations, outages and injection handling. Only then select the new collection/release in app settings. Retain the prior collection for rollback and restore its matching collection, release and model settings together if needed.

## Local development

Local indexing remains available to maintainers through the CLI and Ollama. The Streamlit Chat adapter intentionally does not use local settings or indexes; it requires Streamlit Secrets and Qdrant/OpenAI cloud services.

```sh
ollama pull embeddinggemma
python tools/index_corpus.py
```

Bare indexing is a local maintenance command that replaces stale rows. Generated files are ignored by Git and are not deployed with the repository.

## Data flow and operation

Questions go to the hosted OpenAI embedding API; vectors and subject/period filters go to Qdrant Cloud. Publication sends reviewed passages, vectors and citation metadata to Qdrant. Generation sends the current question, selected subject and bounded evidence to the OpenAI Responses endpoint with store=False, a 45-second timeout, no retries and a 700-token output cap. This does not guarantee zero provider retention. Earlier session messages are not sent; questions must stand on their own. No transcript, account, analytics or telemetry storage was added.

Cached services share clients/connections only. Histories and answer-cache entries remain session-local, separate per senator in chat history, and may reset on disconnect or restart. Explicit handoffs make no embedding/generation call and do not transfer history or resubmit questions. Uncovered subjects show zero reviewed passages; missing evidence is not proof of inactivity. Citation validation verifies marker/provenance integrity, not semantic entailment.

Configure spending limits and alerts privately and name a maintenance/correction owner. Test cloud wake, restart and another-device access with the laptop off before declaring deployment complete. See [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for outstanding gates.
