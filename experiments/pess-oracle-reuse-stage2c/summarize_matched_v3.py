"""Summarize v3 matched evidence and verify the cyclic-balanced order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evidence_io import write_text_exclusive
from summarize_matched_v2 import summarize, write_hashes

METHODS = (
    "static",
    "master_oracle_uncached",
    "master_oracle_existing_task_cache",
)


def position_counts(paths: list[Path]) -> dict[str, list[int]]:
    counts = {method: [0, 0, 0] for method in METHODS}
    for path in paths:
        row = json.loads(path.read_text(encoding="utf-8"))
        for position, method in enumerate(row["method_order"]):
            counts[method][position] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--hashes", required=True, type=Path)
    args = parser.parse_args()
    paths = sorted(args.raw_dir.glob("*.jsonl"))
    summary = summarize(paths)
    summary["balanced_method_order"] = True
    summary["order_schedule"] = "cyclic-balanced-v3"
    summary["method_position_counts"] = position_counts(paths)
    expected = {method: [8, 8, 8] for method in METHODS}
    if summary["method_position_counts"] != expected:
        raise ValueError(f"unexpected method position counts: {summary['method_position_counts']}")
    write_text_exclusive(args.summary, json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_hashes(args.raw_dir, args.hashes)
    print(
        json.dumps(
            {
                "raw_record_count": len(paths),
                "case_count": summary["case_count"],
                "method_position_counts": summary["method_position_counts"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
