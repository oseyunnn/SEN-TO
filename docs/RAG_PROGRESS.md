# RAG progress — 26 November 2026

**Qdrant update:** The owner has created a Qdrant Cloud cluster and supplied its endpoint. Qdrant retrieval, publication and health tools are implemented, with offline tests using local Qdrant and fake embeddings. A private settings template is ready for the owner to enter the read-only key. No authenticated cloud connection or publication has been performed. See [QDRANT_SETUP.md](QDRANT_SETUP.md).

The Chat path connects frontend, backend and injectable retrieval/generation/validation services. Local Ollama/Chroma development remains supported. Cloud code now supports OpenAI embeddings, Chroma Cloud and the existing Responses generator. Cloud runtime is read-only and checks release identity, cosine schema and publication state. Verification results are recorded in [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md).

The original-document manifest remains empty. The 24 Markdown profiles are separate research inputs; importer eligibility does not establish independent source review. Initial deployment targets a reviewed two-senator pilot. No current pair has been approved and no cloud collection has been populated. The starter register intentionally has no approvals.

Release tooling validates exact profile checksums, human decisions, source locators, normalized periods, approved IDs and expanded row counts. It creates new collections and verifies uploaded payloads before marking publication ready. It does not approve claims or automatically promote deployments. Runtime separately checks senator and period after retrieval; incomplete generated responses are rejected and every cited marker retains its source locator.

The UI supports explicit senator handoffs and surname clarification without model calls. Session histories remain isolated and are not generation memory. Coverage and review dates come from the configured release. Comparison remains a placeholder.

Remaining work: original-source and current-bloc verification; human claim/answer review; account and spending controls; live retrieval/model evaluation; hosting promotion; other-device, laptop-off, restart and sleep/wake checks. Follow [RAG_SETUP.md](RAG_SETUP.md) and the original [deployment plan](DEPLOYMENT_PLAN.md).
