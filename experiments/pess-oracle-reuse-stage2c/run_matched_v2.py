"""Run matched methods in fresh processes with deterministic randomized order."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from evidence_io import write_text_exclusive

METHODS = (
    "static",
    "master_oracle_uncached",
    "master_oracle_existing_task_cache",
)
ORDER_SCHEDULE = tuple(itertools.permutations(METHODS))
RUNNER = Path(__file__).with_name("run_matched_variants.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_name(path: Path) -> str:
    return path.stem


def run_one_method(instance: Path, method: str, endpoint_seconds: float) -> dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="stage2c-worker-"))
    output = temp_dir / "worker.json"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--instance",
                str(instance),
                "--output",
                str(output),
                "--endpoint-seconds",
                str(endpoint_seconds),
                "--method",
                method,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if not output.exists():
            raise RuntimeError(
                f"worker did not produce evidence for {method}: "
                f"returncode={completed.returncode}, stderr={completed.stderr[-2000:]}"
            )
        record = json.loads(output.read_text(encoding="utf-8"))
        method_record = record["methods"][0]
        method_record["worker_process"] = {
            "pid": record["process"]["pid"],
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        return method_record
    finally:
        shutil.rmtree(temp_dir)


def run_case(instance: Path, endpoint_seconds: float, repetition: int, seed: int) -> dict[str, Any]:
    order_index = (seed + repetition - 1) % len(ORDER_SCHEDULE)
    order = list(ORDER_SCHEDULE[order_index])
    methods = [run_one_method(instance, method, endpoint_seconds) for method in order]
    return {
        "experiment": "stage2c-matched-existing-cache-v2",
        "instance": str(instance.resolve()),
        "input_sha256": sha256(instance),
        "endpoint_seconds": endpoint_seconds,
        "repetition": repetition,
        "method_order": order,
        "fresh_process_per_method": True,
        "order_schedule": "balanced_permutation",
        "order_index": order_index,
        "methods": methods,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", nargs="+", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--endpoint-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.repetitions < 1:
        raise ValueError("--repetitions must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for instance in sorted(args.instance):
        for repetition in range(1, args.repetitions + 1):
            output = args.output_dir / f"{case_name(instance)}-r{repetition}.jsonl"
            record = run_case(instance, args.endpoint_seconds, repetition, args.seed)
            write_text_exclusive(output, json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps({"output": str(output), "method_order": record["method_order"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
