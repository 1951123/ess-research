"""Run unchanged Static, unchanged Master--Oracle, and existing cache option."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import time
import traceback
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from independent_reference import objective
from pess_ess.model import read_instance
from pess_ess.solvers_v2 import MasterOracleOptions, solve_master_oracle, solve_static

ADVISOR_SHA = "1052ff4a46270c90414d76b32d6f6b37e5908f6a"


def jsonable(value: Any) -> Any:
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, frozenset | set | tuple):
        return [jsonable(item) for item in value]
    if is_dataclass(value):
        return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value


def compact(result: Any) -> dict[str, Any]:
    raw = jsonable(result)
    fields = (
        "status", "termination_reason", "selected", "maintenance_cost", "objective",
        "lower_bound", "upper_bound", "validated_feasible", "solver_reported_optimal",
        "task_evaluations", "task_evaluation_requests", "task_evaluation_computations",
        "exact_oracle_invocations", "cache_lookups", "cache_hits", "cache_misses",
        "cache_entries", "cache_hit_rate", "distinct_task_local_configurations",
        "total_runtime_seconds", "master_iterations", "distinct_cuts",
        "inner_mip_solve_calls", "exact_inner_seconds", "ordinary_matching_seconds",
    )
    return {field: raw.get(field) for field in fields}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_one(label: str, fn: Callable[[], Any], instance: Any) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = fn()
        elapsed = time.perf_counter() - started
        raw = compact(result)
        verification = None
        if result.selected is not None:
            value, details = objective(instance, result.selected)
            verification = {
                "status": "PASS",
                "objective": str(value),
                "solver_objective": raw.get("objective"),
                "objective_agreement": raw.get("objective") == str(value),
                "witnesses": {task_id: sorted(witness) for task_id, (_loss, witness) in details.items()},
            }
        return {
            "method": label,
            "outcome": "completed",
            "wall_seconds": elapsed,
            "solver_result": raw,
            "independent_verification": verification,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "method": label,
            "outcome": "error",
            "wall_seconds": time.perf_counter() - started,
            "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
        }


def environment() -> dict[str, Any]:
    names = ("numpy", "scipy", "networkx", "pandas", "pytest", "ruff")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "uname": list(platform.uname()),
        "advisor_sha": ADVISOR_SHA,
        "packages": {name: importlib.metadata.version(name) for name in names},
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
    }


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value * 1024 if platform.system() == "Linux" else value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--endpoint-seconds", type=float, default=5.0)
    args = parser.parse_args()
    instance = read_instance(args.instance)
    common = {
        "total_time_limit": args.endpoint_seconds,
        "inner_time_limit": args.endpoint_seconds,
        "certification_tolerance": 0.0,
        "cut_tolerance": 1e-6,
    }
    records = [
        run_one(
            "static",
            lambda: solve_static(instance, total_time_limit=args.endpoint_seconds),
            instance,
        ),
        run_one(
            "master_oracle_uncached",
            lambda: solve_master_oracle(instance, **common, options=MasterOracleOptions(task_local_cache=False)),
            instance,
        ),
        run_one(
            "master_oracle_existing_task_cache",
            lambda: solve_master_oracle(instance, **common, options=MasterOracleOptions(task_local_cache=True)),
            instance,
        ),
    ]
    record = {
        "experiment": "stage2c-matched-existing-cache-v1",
        "instance": str(args.instance.resolve()),
        "input_sha256": sha256(args.instance),
        "endpoint_seconds": args.endpoint_seconds,
        "configuration": common,
        "environment": environment(),
        "methods": records,
        "peak_rss_bytes": peak_rss_bytes(),
        "process": {"pid": os.getpid(), "cwd": os.getcwd()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"instance": record["instance"], "methods": [{"method": item["method"], "outcome": item["outcome"]} for item in records]}, sort_keys=True))
    return 0 if all(item["outcome"] == "completed" for item in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
