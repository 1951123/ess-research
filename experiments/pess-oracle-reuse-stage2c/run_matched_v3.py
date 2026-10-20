"""Run the preregistered cyclic-balanced Stage 2C matched schedule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evidence_io import write_text_exclusive
from run_matched_v2 import run_one_method, sha256

ORDER_SCHEDULE = (
    ("static", "master_oracle_uncached", "master_oracle_existing_task_cache"),
    ("master_oracle_uncached", "master_oracle_existing_task_cache", "static"),
    ("master_oracle_existing_task_cache", "static", "master_oracle_uncached"),
)


def case_name(path: Path) -> str:
    return path.stem


def run_case(instance: Path, endpoint_seconds: float, repetition: int) -> dict:
    order_index = (repetition - 1) % len(ORDER_SCHEDULE)
    order = list(ORDER_SCHEDULE[order_index])
    methods = [run_one_method(instance, method, endpoint_seconds) for method in order]
    return {
        "experiment": "stage2c-matched-existing-cache-v3",
        "instance": str(instance.resolve()),
        "input_sha256": sha256(instance),
        "endpoint_seconds": endpoint_seconds,
        "repetition": repetition,
        "method_order": order,
        "fresh_process_per_method": True,
        "order_schedule": "cyclic-balanced-v3",
        "order_index": order_index,
        "methods": methods,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", nargs="+", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--endpoint-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.repetitions != len(ORDER_SCHEDULE):
        raise ValueError("v3 requires exactly three repetitions for the cyclic-balanced schedule")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for instance in sorted(args.instance):
        for repetition in range(1, args.repetitions + 1):
            output = args.output_dir / f"{case_name(instance)}-r{repetition}.jsonl"
            record = run_case(instance, args.endpoint_seconds, repetition)
            write_text_exclusive(output, json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps({"output": str(output), "method_order": record["method_order"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
