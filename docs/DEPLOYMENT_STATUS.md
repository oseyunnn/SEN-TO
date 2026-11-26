# Deployment status — 27 November 2026

## Qdrant update (supersedes Chroma provisioning steps below)

The owner reported Chroma signup blocking and created Qdrant Cloud cluster `sento-demo`. Their screenshot shows a healthy free cluster, an active `sento-publisher` manage key and an active `sento-app` read key. They supplied the endpoint recorded in [QDRANT_SETUP.md](QDRANT_SETUP.md). No keys were shared or inspected.

Qdrant support now covers validated settings, read-only runtime retrieval, cosine score conversion, subject/period/release filters, a reserved release control point, create-only publication with payload indexes, full payload/count checks and a read-only connection/health command. Existing Chroma support and source review gates remain. The deployed Chat adapter reads root-level configuration directly from Streamlit Secrets. No live database/model calls, cloud writes or deployments were performed while implementing this adapter.

The original Chroma plan remains archived below; the current next steps are private Qdrant authentication, reviewed evidence preparation, live evaluation and hosting rollout.

## Hosted Chat runtime and cost-control update — 27 November 2026

- The Streamlit Chat path now requires `qdrant_cloud`, OpenAI embeddings and OpenAI Responses generation. It reads configuration directly from `st.secrets`; it does not use `.env`, local TOML files, or process-environment fallback.
- The runtime accepts only the separately named `SENTO_QDRANT_READ_ONLY_API_KEY`. The Qdrant publisher/manage key remains outside the app. The read-only key's actual role still needs confirmation in the Qdrant dashboard.
- The configured generation target remains `gpt-6-luna` with low reasoning. The owner reports paid OpenAI usage, but no API key or Streamlit Secrets were available in this workspace, so account/model access could not be called and the model was not changed.
- Exact repeat responses are cached per session for ten minutes (up to 32 entries); eight submissions per session/minute and thirty cloud RAG requests per running app process/minute are enforced. The process limiter resets on restart and does not replace OpenAI project spending controls.
- `data/releases/demo-r1/review.json` still has no subjects, scope review, or approved decisions; there is no published release manifest. The runtime will continue to return a configuration error until the collection/release settings are populated after a real review and publication. No records were approved or invented.
- This change is local only. It has not been pushed or redeployed. Live cloud query embedding, Qdrant search, and generation have not been exercised.

The owner ran `tools/check_rag.py --connection-only --secrets-file .streamlit/secrets.qdrant.toml` successfully and reported `connection_ok`, zero model calls and zero writes. This confirms endpoint/API-key authentication for a read request. The screenshot labels `sento-app` as Read Cluster; no write-permission probe was attempted. It does not establish collection readiness, evidence publication or model access.

Qdrant verification: `qdrant-client==1.20.0`; full suite `.venv/Scripts/python.exe -m pytest -q --basetemp=test-results/qdrant-full` — **170 passed**. Dependency check reports no broken requirements; `git diff --check` reports no whitespace errors. Qdrant tests used in-memory local collections and fake embeddings, including publication, duplicate/active release protection, incomplete uploads, identity checks, filter isolation, score conversion, offline preflight and credential-safe connection checks. Hosted authentication, server-specific index enforcement, cloud persistence and model quality remain untested.

Target app: https://sentogit-xuoaad9kce29ixwvg2ahmd.streamlit.app/

The owner confirmed this URL and that no Chroma Cloud database exists. The hosting branch, account access, model access, billing controls and secret settings have not been verified. Current changes are in the `main` working tree and have not been committed, pushed or deployed. The protected `.env` was not accessed.

## Implemented locally

- Explicit local/cloud settings; hosted OpenAI embeddings; named, read-only runtime collections; release/model/dimension/schema/cosine checks; no cloud-to-Ollama fallback.
- Human-reviewed claim allowlist export bound to local input checksums, provenance and periods; offline preflight; new-collection publication; payload/count verification; no live collection replacement.
- Subject handoffs, surname clarification, explicit switch actions, separate session histories, normalized congressional filters, complete citation marker/locator mappings and incomplete-response rejection.
- Cached stateless services, selected-subject release coverage, controlled configuration/outage messages and a read-only release checker.

## Evidence and rollout gates still open

1. **Pilot selection and original-source review.** Preserve all 24 research inputs. The release register intentionally approves zero claims. Importer eligibility is not human verification. No current bloc label has been added. Searches found recent reporting but the Senate homepage returned no readable content through the research tool; the DBM government directory exceeded that tool's download limit. Those results do not establish a reviewed current pair. Verify authoritative dated records and record exact locators before approval.
2. **Human review.** A reviewer must check original documents, subject associations, normalized Congress and every sentence in the live question set. Populate five supported and three unsupported questions per enabled subject, including English, Filipino and Taglish. No human decisions have been fabricated.
3. **Accounts.** Qdrant cluster `sento-demo` and separate manage/read keys were reported created. Confirm the `sento-app` key is Read Cluster, add it only as `SENTO_QDRANT_READ_ONLY_API_KEY` in Streamlit Secrets, add the OpenAI key and usage limits, and verify model access. The configured model name alone does not establish account availability.
4. **Publication.** Prepare a reviewed package, run offline preflight, publish a new candidate collection, run read-only health checks and the live question set. Keep the old collection for rollback. A failed build stays inactive.
5. **Hosting.** Confirm the watched repository/branch, `app.py` and Python 3.12; add root-level settings in Streamlit Settings → Secrets. Only promote a validated collection. The public URL could not be opened by the research tool, so its current deployment has not been verified.
6. **External acceptance.** Open the app on another device with the laptop off; test both subjects and unsupported questions; restart and sleep/wake the cloud app and repeat. These physical/device checks have not been performed.

No paid model request, cloud provisioning, publication, or deployment was performed during local implementation. See [RAG_SETUP.md](RAG_SETUP.md) for commands and [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) for the original requested plan.

## Verification performed

- Python 3.12.14 on Windows; pinned Streamlit 1.67.0, Chroma 1.5.9, OpenAI 2.54.0, pypdf 7.1.1 and pytest 9.2.0. Dependency compatibility check: no broken requirements. Linux hosting has not been exercised.
- Full suite: `.venv/Scripts/python.exe -m pytest -q --basetemp=test-results/cloud-final` — **147 passed**. Includes real temporary local Chroma publication/schema roundtrip with fake embeddings, failed publication, existing-name/active-release protection, offline preflight with forbidden provider access, malformed hosted responses, period/subject isolation, policy precedence, citation mappings and Streamlit handoff/history tests.
- Senator importer: **971 chunks**, **202 importer-eligible**, **769 candidate/unverified**. This differs from the attachment's older 954/200 baseline. No research input was modified and none of these counts establishes human approval.
- Running release preparation against the committed empty review register correctly failed. No chunks/manifest were published as an approved release.
- Live model quality, cloud permissions, cloud persistence, human sentence support and laptop independence remain untested.
