# SEN’TO RAG progress

**Status as of 25 November 2026**

## Implementation status

The RAG software path is connected from local source files to the Streamlit chat:

1. **Ingestion:** Developers curate source files and metadata in a manifest or a per-senator Markdown file. The importers parse PDFs, local HTML, and the fixed 13-section senator format, preserve source provenance and locators, and write JSONL chunks. They do not crawl or download web pages.
2. **Indexing:** The indexer reads reviewed chunks and stores embeddings in a persistent local Chroma collection. Ollama is the default embedding provider. Chunks without a verified senator association, a verified citation, or verified status are excluded.
3. **Retrieval and generation:** Retrieval filters to the selected senator and verified records, with an optional period filter and configurable cosine-distance cutoff. The pipeline checks the selected senator again before generation. The default generator uses local Ollama; an optional OpenAI Responses adapter targets `gpt-6-luna`.
4. **Validation and interface:** The pipeline checks that generated evidence markers resolve to retrieved chunks and safe, verified source metadata. Chat displays citations, source title, publisher, type, relevant period, locator, and available dates. It distinguishes no evidence from provider failure and withholds answers that fail citation checks.

The implementation uses Python and Streamlit with ChromaDB and Ollama adapters. It does not add FastAPI or LangChain because they are not needed by the existing Streamlit application. Embedding, generation, and retrieval seams remain replaceable.

## Current corpus and limits

The source manifest has no records. `data/senator_records/francis-escudero.md` is a reference-only format example and is intentionally skipped. Therefore, the current index contains no usable evidence and the chat abstains on factual questions. The seven entries in `data/senators.json` remain design examples, not a verified current roster. The planned 24-seat scope for the 20th Congress still needs a dated roster check and should not be implied by this UI directory.

Citation validation is a mechanical integrity check: markers must point to retrieved passages, whose source metadata and HTTPS links pass checks. It does not verify that every generated claim is semantically supported by its cited passage. A human review set is required before presenting the system as factually validated. Missing evidence means this dataset could not confirm a point; it does not show that no record exists.

## Run the local pipeline

Follow [RAG_SETUP.md](RAG_SETUP.md) to configure Ollama, ingest reviewed source files, and build the index:

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

Until this work is completed, describe SEN’TO as having a connected RAG implementation with an empty research corpus, not as having comprehensive or fully verified coverage of Senate records.
