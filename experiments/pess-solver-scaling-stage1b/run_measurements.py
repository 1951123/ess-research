"""Run the frozen endpoint-at-budget matrix in deterministic randomized blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_job(instance: Path, method: str, budget: float, repetition_seed: int, run_id: str, timeout: float) -> dict[str, object]:
    command = [
        sys.executable,
        str(ROOT / "run_one.py"),
        "--instance", str(instance),
        "--method", method,
        "--budget-seconds", str(budget),
        "--inner-budget-seconds", str(min(5.0, budget)),
        "--repetition-seed", str(repetition_seed),
        "--run-id", run_id,
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        lines = completed.stdout.strip().splitlines()
        record = json.loads(lines[-1]) if lines else {"outcome": "empty_stdout"}
        record["wrapper_wall_seconds"] = time.perf_counter() - started
        record["command"] = command
        record["returncode"] = completed.returncode
        if completed.stderr:
            record["stderr"] = completed.stderr
        return record
    except subprocess.TimeoutExpired as exc:
        return {
            "outcome": "timeout",
            "run_id": run_id,
            "instance": str(instance),
            "method": method,
            "budget_seconds": budget,
            "repetition_seed": repetition_seed,
            "command": command,
            "timeout_seconds": timeout,
            "stdout_tail": (exc.stdout or "")[-2000:],
            "stderr_tail": (exc.stderr or "")[-2000:],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--budgets", default="5,20,60")
    parser.add_argument("--repetitions", default="7101,7102,7103")
    parser.add_argument("--tiers", default="small,medium,large")
    parser.add_argument("--per-instance-cap", type=float, default=65.0)
    parser.add_argument("--hard-total-budget", type=float, default=1800.0)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    budgets = tuple(float(item) for item in args.budgets.split(","))
    repetition_seeds = tuple(int(item) for item in args.repetitions.split(","))
    tiers = frozenset(args.tiers.split(","))
    manifest = json.loads((ROOT / "manifest-v1.json").read_text(encoding="utf-8"))
    instances = []
    for item in manifest["instances"]:
        if item["tier"] not in tiers:
            continue
        path = ROOT / item["file"]
        if sha256(path) != item["sha256"]:
            raise SystemExit(f"manifest hash mismatch: {path}")
        instances.append((item, path))
    jobs = []
    for repetition_seed in repetition_seeds:
        block = [
            (item, path, method, budget, repetition_seed)
            for item, path in instances
            for method in ("static", "master_oracle")
            for budget in budgets
        ]
        random.Random(repetition_seed).shuffle(block)
        jobs.extend(block)
    raw_path = output_dir / "raw-runs.jsonl"
    started = time.perf_counter()
    completed_count = timeout_count = error_count = 0
    with raw_path.open("x", encoding="utf-8") as handle:
        for index, (item, path, method, budget, repetition_seed) in enumerate(jobs):
            elapsed = time.perf_counter() - started
            if elapsed >= args.hard_total_budget:
                record = {
                    "outcome": "not_run_hard_total_budget",
                    "job_index": index,
                    "run_id": f"{path.stem}-{method}-b{budget:g}-r{repetition_seed}",
                    "instance": str(path),
                    "method": method,
                    "budget_seconds": budget,
                    "repetition_seed": repetition_seed,
                    "hard_total_budget_seconds": args.hard_total_budget,
                    "elapsed_before_skip_seconds": elapsed,
                }
            else:
                record = run_job(path, method, budget, repetition_seed, f"{path.stem}-{method}-b{budget:g}-r{repetition_seed}", args.per_instance_cap)
                record["job_index"] = index
                record["manifest_metadata"] = item
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            if record.get("outcome") == "completed":
                completed_count += 1
            elif record.get("outcome") == "timeout":
                timeout_count += 1
            else:
                error_count += 1
    summary = {
        "protocol": "protocol-v1.json",
        "manifest": "manifest-v1.json",
        "jobs_planned": len(jobs),
        "records_written": sum(1 for _ in raw_path.open(encoding="utf-8")),
        "completed": completed_count,
        "timeouts": timeout_count,
        "errors_or_not_run": error_count,
        "elapsed_seconds": time.perf_counter() - started,
        "hard_total_budget_seconds": args.hard_total_budget,
        "per_instance_cap_seconds": args.per_instance_cap,
        "budgets_seconds": budgets,
        "repetition_seeds": repetition_seeds,
        "tiers": sorted(tiers),
        "endpoint_observation_warning": "Each endpoint is an independent fresh process; no continuous incumbent trace is reconstructed.",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sums = "\n".join(f"{sha256(path)}  {path.name}" for path in (raw_path, output_dir / "summary.json")) + "\n"
    (output_dir / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if timeout_count == 0 and error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
