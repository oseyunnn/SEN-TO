# SEN’TO RAG progress

**Status as of 26 November 2026**

## Implementation status

The RAG backend path is connected to the Streamlit Chat page through `frontend/api.py::send_chat_message`. It calls retrieval, generation when usable evidence exists, citation validation, and source display. The source manifest is empty, so the current chat abstains before any model request:

1. **Ingestion:** Developers curate source files and metadata in a manifest or a per-senator Markdown file. The importers parse PDFs, local HTML, the current claim-based senator research profiles, and the earlier fixed-section format. Senator claims retain their evidence status and `SRC-*` provenance; only explicitly verified claims with complete safe sources are indexable. The importers do not crawl or download web pages.
2. **Indexing:** The indexer reads reviewed chunks and stores embeddings in a persistent local Chroma collection. Ollama is the default embedding provider. Chunks without a verified senator association, a verified citation, or verified status are excluded.
3. **Retrieval and generation:** Retrieval filters to the selected senator and verified records, with an optional period filter and configurable cosine-distance cutoff. The pipeline checks the selected senator again before generation. The default generator uses local Ollama; an optional OpenAI Responses adapter targets `gpt-6-luna`.
4. **Validation and interface:** The pipeline checks that generated evidence markers resolve to retrieved chunks and safe, verified source metadata. The Chat UI displays citations returned by the pipeline.

5. **Security controls:** Current backend checks normalize and bound questions, refuse targeted private-prompt and bulk-retrieval requests, serialize user/retrieved content as JSON data, cap retrieved context and provider output, preserve senator/source filters, validate citations, and withhold overlong or malformed outputs. The UI applies an eight-requests-per-minute session limit and caps rendered history. These controls are not a guarantee against novel prompt injections or semantic hallucinations.

The implementation uses Python and Streamlit with ChromaDB and Ollama adapters. It does not add FastAPI or LangChain because they are not needed by the existing Streamlit application. Embedding, generation, and retrieval seams remain replaceable.

## Current corpus and limits

The source manifest has no records. The profiles in `data/senator_records/` use the current claim-based format. The latest senator-record ingestion wrote 954 claim chunks: 200 are eligible for indexing and 754 remain candidates or unverified because of their claim status or incomplete source provenance. These generated chunks have not yet been indexed in Chroma. `data/senator_records/francis-escudero.md` is a reference-only format example and is intentionally skipped. The Chat UI abstains until usable records are indexed. The 24 names are based on the Senate's dated group-photo roster, not a live membership check. Profile facts and Minority Bloc membership remain unverified.

Citation validation is a mechanical integrity check: markers must point to retrieved passages, whose source metadata and HTTPS links pass checks. It does not verify that every generated claim is semantically supported by its cited passage. A human review set is required before presenting the system as factually validated. Missing evidence means this dataset could not confirm a point; it does not show that no record exists.

## Run the local pipeline

Follow [RAG_SETUP.md](RAG_SETUP.md) to configure Ollama/OpenAI generation, ingest reviewed source files, and build the index. Running Streamlit invokes this pipeline when a question is submitted:

```sh
python tools/ingest_documents.py
python tools/ingest_senator_records.py
python tools/index_corpus.py
streamlit run app.py
```

The code never fetches the bibliography URLs. Keep the original files, provenance manifest, reviewed Markdown, and derived chunks distinct. Inspect extracted text and source locators before indexing.

### Optional OpenAI generation

Local Ollama generation is the default. To use OpenAI, configure `SENTO_GENERATOR_PROVIDER=openai`, provide `OPENAI_API_KEY` through a secrets manager, and select `gpt-6-luna` with `SENTO_OPENAI_MODEL`. Only the current question and retrieved passage context are sent; chat history is not sent. The adapter sets `store=false`. Consult [OpenAI’s model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) and [API data controls](https://developers.openai.com/api/docs/guides/your-data) for current availability and handling details. No credential belongs in the repository.

## Remaining work before a factual release

1. Verify the intended roster and choose a small, comparable set of source types and time periods for the 24-seat research target.
2. Add a few manually reviewed official records with complete provenance. Include original URLs, publisher, publication and retrieval dates, relevant period, exact page or section, and verification status.
3. Inspect every extracted chunk against its source, especially names, bill numbers, dates, tables, and vote marks. Decide separately whether scanned PDFs need a reviewed OCR process; OCR is not included.
4. Evaluate supported questions, deliberate no-evidence questions, senator isolation, optional period filtering, conflicting or stale passages, and prompt injection in source text. Tune retrieval only against reviewed examples.
5. Review answers for claim-to-source support and distinctions such as author vs sponsor, filed vs enacted, vote vs abstention/absence, and allegation vs official finding. The current automatic validator does not check semantic entailment.

Until the corpus and answer-review work is completed, describe SEN’TO as a connected RAG prototype with an empty evidence corpus, not as a comprehensive Senate-record service.
