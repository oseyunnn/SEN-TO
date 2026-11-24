"""Build normalized, provenance-preserving JSONL chunks from a local manifest."""

import argparse
from pathlib import Path
import sys

from ai.ingestion import IngestionError, ingest, write_jsonl_atomic


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data/corpus/manifest.json")
    parser.add_argument("--source-root", type=Path, default=PROJECT_ROOT / "data/corpus/originals")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/corpus/processed/chunks.jsonl")
    args = parser.parse_args()
    try:
        records = ingest(args.manifest, args.source_root)
        write_jsonl_atomic(records, args.output)
    except IngestionError as exc:
        print(f"Ingestion stopped: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {len(records)} chunks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
