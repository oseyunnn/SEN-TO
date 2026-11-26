"""Build reviewed chunks from one sectioned Markdown file per senator."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai.ingestion import write_jsonl_atomic
from ai.senator_markdown import SenatorRecordError, ingest_senator_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=PROJECT_ROOT / "data/senator_records")
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT_ROOT / "data/corpus/processed/senator_chunks.jsonl",
    )
    args = parser.parse_args()
    try:
        records = ingest_senator_records(args.records)
        write_jsonl_atomic(records, args.output)
    except SenatorRecordError as exc:
        print(f"Senator record ingestion stopped: {exc}", file=sys.stderr)
        return 2
    verified = sum(record.get("verification_status") == "verified" for record in records)
    candidates = len(records) - verified
    print(
        f"Wrote {len(records)} claim chunks to {args.output} "
        f"({verified} indexable; {candidates} candidate or unverified)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
