# RAG setup and publication

**Selected deployment:** Qdrant Cloud. Follow [QDRANT_SETUP.md](QDRANT_SETUP.md) for the owner's cluster, private credential check, settings and publication commands. The Chroma-specific configuration below remains an alternative; the evidence-review requirements apply to both backends.

Use Python 3.12 and install requirements.txt. Local development remains available; cloud mode uses hosted embeddings and generation plus a persistent Chroma Cloud collection. Runtime opens an existing collection and never publishes evidence. The protected .env is not loaded by the app or tooling.

## Cloud settings

Enter root-level TOML values in the existing Streamlit app's Settings → Secrets. Never commit a real secrets file. Replace placeholders privately:

```toml
SENTO_VECTOR_BACKEND = "chroma_cloud"
SENTO_CHROMA_COLLECTION = "sento_demo_r1_openai_te3small_1536"
SENTO_RELEASE_ID = "demo-r1"
SENTO_EMBEDDING_PROVIDER = "openai"
SENTO_EMBEDDING_MODEL = "text-embedding-3-small"
SENTO_EMBEDDING_DIMENSIONS = "1536"
SENTO_EMBEDDING_BASE_URL = "https://api.openai.com/v1"
CHROMA_HOST = "api.trychroma.com"
CHROMA_TENANT = "<tenant>"
CHROMA_DATABASE = "sento-demo"
CHROMA_API_KEY = "<private database credential>"
SENTO_GENERATOR_PROVIDER = "openai"
OPENAI_API_KEY = "<private OpenAI credential>"
OPENAI_BASE_URL = "https://api.openai.com/v1"
SENTO_OPENAI_MODEL = "gpt-6-luna"
SENTO_OPENAI_REASONING_EFFORT = "low"
SENTO_RETRIEVAL_TOP_K = "5"
SENTO_MAX_COSINE_DISTANCE = "0.65"
```

Model access must be checked before rollout. An existing gateway credential is not assumed to work at OpenAI. Embedding and generation endpoints are configured separately. A model or dimension change requires a newly embedded collection. Missing cloud settings, incompatible collections or service failures never fall back to local storage or Ollama.

The backend uses [Chroma CloudClient](https://docs.trychroma.com/docs/run-chroma/clients), an explicit [cosine vector schema](https://docs.trychroma.com/cloud/schema/schema-basics), and application-supplied vectors with embedding_function=None. Read-only behavior is enforced by runtime code; verify actual credential permissions in the provider dashboard. Keep publisher credentials with the maintainer. Streamlit exposes root secrets as environment variables; see [secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

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

In the maintainer environment, use matching deployment settings and set SENTO_ACTIVE_COLLECTION to the serving collection, or NONE for first publication. Set SENTO_CHROMA_COLLECTION to a new candidate name. Do not change the running app yet.

```sh
python tools/index_corpus.py --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json --dry-run
python tools/index_corpus.py --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json --apply
python tools/check_rag.py --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json
```

Dry run validates local hashes, approved IDs, counts, provider identity, destination and [Cloud size limits](https://docs.trychroma.com/cloud/quotas-limits) without connecting or embedding. Apply creates a collection; it cannot overwrite an existing name or the declared active collection. Writes use batches of 32. Failed uploads remain building, which runtime rejects. Retry with a new candidate name and matching manifest; never refresh a live collection with one senator's subset. The checker paginates IDs and verifies complete metadata without paid model calls. Ready means upload verification passed, not human answer review.

Run five supported and three unsupported questions per enabled senator, covering English, Filipino and Taglish. Record sentence-by-sentence human support checks in questions.json. Tune retrieval against these reviewed questions. Verify isolation, stale/current distinctions, citations, outages and injection handling. Only then select the new collection/release in app settings. Retain the prior collection for rollback and restore its matching collection, release and model settings together if needed.

## Local development

Set SENTO_VECTOR_BACKEND=local, SENTO_EMBEDDING_PROVIDER=ollama and SENTO_GENERATOR_PROVIDER=ollama; unset cloud collection/release/model overrides. Default Ollama URL is http://127.0.0.1:11434, embedding model embeddinggemma, chat model gemma4.

```sh
ollama pull embeddinggemma
ollama pull gemma4
python tools/index_corpus.py
streamlit run app.py
```

Bare indexing is a local maintenance command that replaces stale rows. Runtime reads a local index only if it exists. Generated files are ignored by Git and are not deployed with the repository.

## Data flow and operation

Questions go to the hosted embedding API; vectors and subject/period filters go to Chroma. Publication sends reviewed passages, vectors and citation metadata to Chroma. Generation sends the current question, selected subject and bounded evidence to the configured Responses endpoint with store=False, a 45-second timeout, no retries and a 700-token output cap. This does not guarantee zero provider retention. Earlier session messages are not sent; questions must stand on their own. No transcript, account, analytics or telemetry storage was added.

Cached services share clients/connections only. Histories remain separate per senator in each session and may reset on disconnect or restart. Explicit handoffs make no embedding/generation call and do not transfer history or resubmit questions. Uncovered subjects show zero reviewed passages; missing evidence is not proof of inactivity. Citation validation verifies marker/provenance integrity, not semantic entailment.

Configure spending limits and alerts privately and name a maintenance/correction owner. Test cloud wake, restart and another-device access with the laptop off before declaring deployment complete. See [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for outstanding gates.
