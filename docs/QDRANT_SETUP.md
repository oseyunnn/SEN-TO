# Qdrant deployment for SEN’TO

Qdrant replaces Chroma Cloud for the selected deployment. Local Chroma development and the Chroma Cloud adapter remain available. The user supplied a healthy `sento-demo` cluster and active `sento-publisher` (manage) and `sento-app` (read) keys in a dashboard screenshot. This is account-setup evidence, not an authenticated application check.

Endpoint: `https://d9b16d6d-d989-4240-9c8c-cecffb5f36e1.ap-northeast-2-0.aws.cloud.qdrant.io`

## Next: privately check the app key

The repository includes [a settings template](qdrant.secrets.example.toml) with this endpoint and empty credentials. Copy it to `.streamlit/secrets.qdrant.toml` if that file does not already exist. Enter the full `sento-app` read-only key as `QDRANT_API_KEY` in your local editor. The masked dashboard value and key ID cannot be used as the credential. Do not paste the key into chat or a shell command. This file is ignored by Git. Leave `OPENAI_API_KEY` empty for the connection-only check.

From the SEN’TO project folder, run:

```powershell
.\.venv\Scripts\python.exe tools/check_rag.py --connection-only --secrets-file .streamlit/secrets.qdrant.toml
```

Expected output includes `"status": "connection_ok"`, `"model_calls": 0`, and `"writes": 0`. This checks database authentication through a read operation, not whether a release exists or whether the credential forbids writes. No evidence is uploaded, no model is contacted, and no credential is printed. A failed check returns a generic message; check key expiration, endpoint and cluster status privately. The command reads only the explicitly named TOML settings file and never auto-loads `.env`.

## Review evidence before publication

Complete the pilot's current majority/minority verification, original-source review and approval register under `data/releases/demo-r1/`. The starter register approves zero claims. Importer eligibility is not human review. Follow the provenance and checksum requirements in [RAG_SETUP.md](RAG_SETUP.md), then run:

```powershell
.\.venv\Scripts\python.exe tools/ingest_senator_records.py
.\.venv\Scripts\python.exe tools/prepare_corpus_release.py --chunks data/corpus/processed/senator_chunks.jsonl --review-register data/releases/demo-r1/review.json --output-dir data/releases/demo-r1
```

The second command must fail until real approvals are entered. Do not create a fictitious reviewer or publish all importer-eligible chunks automatically.

## Publish using the maintenance key

Prepare a separate ignored file `.streamlit/secrets.publisher.toml` from the template. Enter the `sento-publisher` manage key as `QDRANT_API_KEY` and your OpenAI credential as `OPENAI_API_KEY`. Add `SENTO_ACTIVE_COLLECTION = "NONE"` for the first publication; for future releases use the actual serving collection name. Set the candidate collection/release to the manifest's matching values. Keep the read-only app key in the runtime settings file.

```powershell
.\.venv\Scripts\python.exe tools/index_corpus.py --secrets-file .streamlit/secrets.publisher.toml --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json --dry-run
.\.venv\Scripts\python.exe tools/index_corpus.py --secrets-file .streamlit/secrets.publisher.toml --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json --apply
.\.venv\Scripts\python.exe tools/check_rag.py --secrets-file .streamlit/secrets.qdrant.toml --chunks data/releases/demo-r1/chunks.jsonl --release-manifest data/releases/demo-r1/manifest.json
```

Dry run is offline and does not require model or database credentials. Apply sends approved text to OpenAI for paid embeddings and uploads vectors and evidence to Qdrant. It creates a new collection only; an existing name fails. Never use `recreate_collection` or replace the active release. Failed uploads stay inactive; retry with a new candidate collection and matching package. The full health check compares saved IDs and complete payloads against the reviewed package, with no model calls.

## Storage and retrieval contract

- One cosine collection per release, using 1,536-dimensional `text-embedding-3-small` vectors supplied by the application. Qdrant inference is not used.
- Deterministic UUIDs map the existing `chunk_id::senator_id` row IDs to Qdrant points. Original IDs remain in each payload, along with complete text, citation sources, raw periods and normalized Congress.
- Keyword indexes are created before upload for `record_kind`, `senator_id`, `verification_status`, `congress_id`, `relevant_period`, and `release_id`.
- One reserved control point stores release/model/schema identity, review date, counts and `building`/`ready` state. It is excluded from every evidence query and from displayed coverage counts. The dashboard's total point count is therefore **expected evidence rows plus one**.
- Runtime opens existing collections and validates identity, dimensions, cosine metric, ready state and total count. It has no write methods. Every query filters evidence kind, verified status, release and selected senator, plus the requested period. Returned payloads are checked again; the pipeline independently checks subject and Congress.
- Qdrant cosine similarity is converted to SEN’TO's distance as `1 - similarity`; the existing maximum distance of 0.65 corresponds to a minimum similarity of 0.35. Evaluate the cutoff against reviewed questions before release.
- Provider connections are cached without histories. Read/write requests are bounded by a 45-second client timeout. Maintenance scans use pagination; uploads use batches of 32. Existing conservative application payload limits remain in force; these are not advertised as Qdrant service quotas.

## Deploy only after live review

Add a valid OpenAI credential to the private runtime configuration for generation/embeddings. Verify the configured Responses model and reasoning option are available to that account. Complete the supported/unsupported question set and human sentence-support review. Then deploy the tested code to the branch watched by the existing Streamlit app, using `app.py` and Python 3.12. Enter the runtime template's values in Streamlit Settings → Secrets using the **read-only** key and the approved collection/release. Do not enter the publisher key there.

Test another device with the laptop off, cloud restart, and sleep/wake behavior. Keep the previous release and matching settings for rollback. Free Qdrant clusters can suspend after one week without activity and be deleted after four weeks without reactivation, so retain the versioned reviewed package for recovery. No account signup or current cloud retention promise replaces those acceptance checks.

References: [Qdrant authentication](https://qdrant.tech/documentation/cloud/authentication/), [payload indexing](https://qdrant.tech/documentation/manage-data/indexing/), [cluster lifecycle](https://qdrant.tech/documentation/cloud/create-cluster/), [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
