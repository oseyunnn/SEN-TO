"""Publish a project-curated Markdown cloud release or maintain a local Chroma index."""

import argparse
from pathlib import Path
import sys
import json
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai.embeddings import OllamaEmbeddingProvider
from ai.vector_store import ChromaVectorStore, VectorStoreError, read_jsonl
from ai.rag_config import RAGConfig
from ai.releases import checksum, validate_package, publish_release, require
from tools.runtime_settings import load_settings


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
    parser.add_argument('--release-manifest', type=Path)
    parser.add_argument('--secrets-file', type=Path, help='Explicit private TOML settings; never loads .env.')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--dry-run', action='store_true')
    action.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    chunk_paths = args.chunks or [
        PROJECT_ROOT / "data/corpus/processed/chunks.jsonl",
        PROJECT_ROOT / "data/corpus/processed/senator_chunks.jsonl",
    ]
    try:
        load_settings(args.secrets_file)
        config = RAGConfig.load(require_credentials=not args.dry_run)
        chunks = read_jsonl(chunk_paths)
        if not chunks:
            raise VectorStoreError("No chunk records found. Run the senator Markdown importer first.")
        if args.release_manifest:
            require(args.dry_run or args.apply, 'Choose --dry-run or --apply for a release.')
            require(len(chunk_paths) == 1, 'A release requires exactly one chunk file.')
            manifest = json.loads(args.release_manifest.read_text(encoding='utf-8'))
            require(checksum(chunk_paths[0]) == manifest.get('chunks_sha256'), 'Release chunk checksum mismatch.')
            rows = validate_package(chunks, manifest, config)
            active = os.environ.get('SENTO_ACTIVE_COLLECTION')
            require(active and active != config.collection, 'Explicitly identify the active collection, or NONE; destination must differ.')
            if args.dry_run:
                print(json.dumps({'status': 'offline_preflight_passed', 'rows': len(rows), 'counts': manifest['expected_counts'], 'collection': config.collection}))
                return 0
            stats = publish_release(rows, manifest, config)
            print(json.dumps(stats))
            return 0
        require(config.backend == 'local', 'Cloud indexing requires a Markdown release manifest.')
        require(not args.apply and not args.dry_run, 'Release flags require --release-manifest.')
        store = ChromaVectorStore(embedder=config.embedder(), persist_directory=args.index or config.path,
                                  collection_name=config.collection or None)
        stats = store.index_documents(chunks)
    except (VectorStoreError, ValueError, OSError) as exc:
        print(f"Indexing stopped: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print('Publication failed. The active collection was not modified. Inspect provider status privately; use a new candidate collection for retry.', file=sys.stderr)
        return 2
    print(
        f"Indexed {stats['indexed']} chunks in local Chroma; removed {stats['removed']} stale chunks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
