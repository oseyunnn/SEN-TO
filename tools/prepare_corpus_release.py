"""Export an explicit human-reviewed claim allowlist; never approve research automatically."""
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from ai.releases import prepare_release, checksum
from ai.vector_store import read_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chunks', type=Path, required=True)
    parser.add_argument('--review-register', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=PROJECT_ROOT / 'data/senator_records')
    args = parser.parse_args()
    try:
        review = json.loads(args.review_register.read_text(encoding='utf-8'))
        chunks, manifest = prepare_release(read_jsonl([args.chunks]), review, args.source_root)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / 'chunks.jsonl'
        if output.exists() or (args.output_dir / 'manifest.json').exists():
            raise ValueError('Use a new output directory; release artifacts are immutable.')
        output.write_text(''.join(json.dumps(c, ensure_ascii=False, sort_keys=True) + '\n' for c in chunks), encoding='utf-8')
        manifest['chunks_sha256'] = checksum(output)
        review_output = args.output_dir / 'review.json'
        if args.review_register.resolve() != review_output.resolve():
            review_output.write_bytes(args.review_register.read_bytes())
        manifest['review_sha256'] = checksum(review_output)
        (args.output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    except (ValueError, OSError, RuntimeError):
        print('Release preparation failed: check approval decisions, exact source checksums, provenance and destination. No approval was inferred.', file=sys.stderr)
        return 2
    print(f"Prepared {len(chunks)} reviewed chunks; {manifest['expected_rows']} indexed rows.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
