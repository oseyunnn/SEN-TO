"""Embed reviewed JSONL chunks with Ollama and persist them in local Chroma."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai.embeddings import OllamaEmbeddingProvider
from ai.vector_store import ChromaVectorStore, VectorStoreError, read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chunks", type=Path, action="append",
        help="Chunk JSONL file; may be passed more than once. Defaults to both corpus chunk files.",
    )
    parser.add_argument(
        "--index", type=Path, default=None,
        help="Chroma persistence directory (defaults to SENTO_CHROMA_PATH or the project corpus path).",
    )
    args = parser.parse_args()
    chunk_paths = args.chunks or [
        PROJECT_ROOT / "data/corpus/processed/chunks.jsonl",
        PROJECT_ROOT / "data/corpus/processed/senator_chunks.jsonl",
    ]
    try:
        chunks = read_jsonl(chunk_paths)
        if not chunks:
            raise VectorStoreError("No chunk records found. Run an ingestion command after adding reviewed sources.")
        store = ChromaVectorStore(
            embedder=OllamaEmbeddingProvider(),
            persist_directory=args.index,
        )
        stats = store.index_documents(chunks)
    except VectorStoreError as exc:
        print(f"Indexing stopped: {exc}", file=sys.stderr)
        return 2
    print(
        f"Indexed {stats['indexed']} chunks in local Chroma; removed {stats['removed']} stale chunks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
