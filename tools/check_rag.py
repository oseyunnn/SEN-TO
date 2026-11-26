"""Read-only release health check. No embedding or generation calls."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.rag_config import RAGConfig
from ai.rag_factory import build_retriever
from ai.releases import validate_package, verify_collection, checksum, require
from ai.vector_store import read_jsonl
from tools.runtime_settings import load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-manifest', type=Path)
    parser.add_argument('--chunks', type=Path)
    parser.add_argument('--secrets-file', type=Path)
    parser.add_argument('--connection-only', action='store_true', help='Check Qdrant authentication without a published release or model credentials.')
    args = parser.parse_args()
    try:
        load_settings(args.secrets_file)
        config = RAGConfig.load(require_credentials=False)
        require(config.backend != 'local', 'Health check requires cloud mode.')
        if args.connection_only:
            import os
            require(config.backend == 'qdrant_cloud' and bool(os.environ.get('QDRANT_API_KEY')), 'Qdrant credentials are required.')
            client = config.cloud_client()
            try:
                client.get_collections()
            finally:
                client.close()
            print(json.dumps({'status': 'connection_ok', 'model_calls': 0, 'writes': 0,
                              'note': 'Authentication succeeded; this does not verify a populated release or key write restrictions.'}))
            return 0
        require(args.release_manifest and args.chunks, 'Supply a release manifest and chunks, or --connection-only.')
        manifest = json.loads(args.release_manifest.read_text(encoding='utf-8'))
        require(checksum(args.chunks) == manifest.get('chunks_sha256'), 'Chunk checksum mismatch.')
        rows = validate_package(read_jsonl([args.chunks]), manifest, config)
        store = build_retriever(config)._get_store()
        if config.backend == 'qdrant_cloud':
            from ai.qdrant_store import verify_qdrant_collection
            verify_qdrant_collection(store.client, config.collection, rows)
        else:
            verify_collection(store.collection, rows)
    except Exception:
        print('Release health check failed. Check settings, connection and release identity privately; no model calls were made.', file=sys.stderr)
        return 2
    print(json.dumps({'status': 'healthy', 'release_id': config.release, 'rows': len(rows), 'model_calls': 0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
