"""Execute one isolated baseline endpoint and emit one JSON record to stdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

from pess_ess.model import read_instance

from adapter import compact_result, environment, invoke, peak_rss_bytes
from graph_metrics import signatures
from independent_reference import objective


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True)
    parser.add_argument("--method", choices=("static", "master_oracle"), required=True)
    parser.add_argument("--budget-seconds", type=float, required=True)
    parser.add_argument("--inner-budget-seconds", type=float, default=None)
    parser.add_argument("--repetition-seed", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    path = Path(args.instance).resolve()
    base = {
        "run_id": args.run_id,
        "instance": str(path),
        "input_sha256": sha256(path),
        "method": args.method,
        "repetition_seed": args.repetition_seed,
        "limits": {
            "total_time_limit": args.budget_seconds,
            "inner_time_limit": args.inner_budget_seconds,
            "certification_tolerance": 0.0,
            "cut_tolerance": 1e-6,
        },
        "process": {"pid": os.getpid(), "cwd": os.getcwd()},
        "environment": environment(),
    }
    try:
        instance = read_instance(path)
        base["input_signature"] = {
            "candidate_count": len(instance.candidates),
            "task_count": len(instance.tasks),
            "budget": str(instance.budget),
            "graph_signatures": signatures(instance),
        }
        result, adapter_wall = invoke(path, args.method, args.budget_seconds, args.inner_budget_seconds)
        compact = compact_result(result)
        base["adapter_solver_wall_seconds"] = adapter_wall
        base["solver_result"] = compact
        selected_raw = compact.get("selected")
        if selected_raw is None:
            base["independent_verification"] = {
                "status": "NO_VALID_INCUMBENT",
                "feasible": False,
                "objective": None,
                "witnesses": None,
            }
        else:
            selected = frozenset(selected_raw)
            value, details = objective(instance, selected)
            solver_objective = compact.get("objective")
            base["independent_verification"] = {
                "status": "PASS",
                "feasible": True,
                "objective": str(value),
                "solver_objective": solver_objective,
                "objective_agreement": solver_objective == str(value),
                "maintenance_cost": str(instance.maintenance_cost(selected)),
                "witnesses": {task_id: str(witness) for task_id, (_loss, witness) in details.items()},
            }
        base["outcome"] = "completed"
    except Exception as exc:  # noqa: BLE001  # fail closed and preserve the error in raw output
        base["outcome"] = "error"
        base["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    base["full_invocation_wall_seconds"] = time.perf_counter() - started
    base["peak_rss_bytes"] = peak_rss_bytes()
    print(json.dumps(base, sort_keys=True))
    return 0 if base["outcome"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
