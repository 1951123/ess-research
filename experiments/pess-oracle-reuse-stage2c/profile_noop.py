"""Profile unchanged Master--Oracle through a research-side no-op wrapper.

The wrapper patches only the imported ``evaluate_task`` reference in the
pinned ``pess_ess.solvers_v2`` module for the lifetime of one process. It
delegates every call unchanged and never returns a cached value. The output is
one immutable JSON record for one input and one endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from evidence_io import write_text_exclusive
from pess_ess import solvers_v2
from pess_ess.model import Instance, Task, read_instance
from pess_ess.solvers_v2 import MasterOracleOptions, solve_master_oracle

ADVISOR_SHA = "1052ff4a46270c90414d76b32d6f6b37e5908f6a"
PROFILE_VERSION = "stage2c-noop-profiler-v1"


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_instance(instance: Instance) -> dict[str, Any]:
    return {
        "budget": str(instance.budget),
        "candidates": [
            {
                "id": candidate.id,
                "table": candidate.table,
                "endpoints": list(candidate.endpoints),
                "maintenance_cost": str(candidate.maintenance_cost),
            }
            for candidate in instance.candidates
        ],
        "tasks": [
            {
                "id": task.id,
                "table": task.table,
                "weight": str(task.weight),
                "alpha": str(task.alpha),
                "eligible_candidates": list(task.eligible_candidates),
                "corrections": {
                    key: str(task.corrections[key]) for key in sorted(task.corrections)
                },
            }
            for task in instance.tasks
        ],
    }


def canonical_call(
    instance: Instance,
    task: Task,
    selected: frozenset[str],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Return the strict full-key payload used for equivalence accounting.

    The pinned public API passes no fractional master point, claimed-cut
    collection, or persisted solver state into ``evaluate_task``. Those
    absent semantic inputs are represented explicitly as empty/fresh-state
    fields rather than silently omitted. The absolute deadline is retained,
    because it can change whether the inner MIP completes.
    """

    candidate_map = instance.candidate_map
    local_ids = sorted(set(selected) & set(task.eligible_candidates))
    local_graph = [
        {
            "id": candidate_id,
            "endpoints": list(candidate_map[candidate_id].endpoints),
            "maintenance_cost": str(candidate_map[candidate_id].maintenance_cost),
            "correction": str(task.corrections[candidate_id]),
        }
        for candidate_id in local_ids
    ]
    return {
        "profile_version": PROFILE_VERSION,
        "advisor_sha": ADVISOR_SHA,
        "instance": canonical_instance(instance),
        "task_id": task.id,
        "task_weight": str(task.weight),
        "task_alpha": str(task.alpha),
        "task_eligible_edges": [
            {
                "id": candidate_id,
                "endpoints": list(candidate_map[candidate_id].endpoints),
                "maintenance_cost": str(candidate_map[candidate_id].maintenance_cost),
                "correction": str(task.corrections[candidate_id]),
            }
            for candidate_id in task.eligible_candidates
        ],
        "selected_global_labels": sorted(selected),
        "selected_task_graph": local_graph,
        "fractional_master_point": None,
        "claimed_clauses": [],
        "tolerances_and_limits": {
            key: canonical_argument(value) for key, value in sorted(kwargs.items())
        },
        "objective_and_witness_meaning": "signed maximal-matching absolute affine loss; exact Fraction value and labeled maximal witness",
        "solver_state_identity": "fresh-public-evaluate_task-call; no persisted substate",
    }


def key_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def canonical_argument(value: Any) -> Any:
    if callable(value):
        return {
            "callable": f"{getattr(value, '__module__', '')}.{getattr(value, '__qualname__', repr(value))}"
        }
    return jsonable(value)


def package_versions() -> dict[str, str | None]:
    names = ("numpy", "scipy", "networkx", "pandas", "pytest", "ruff")
    return {name: importlib.metadata.version(name) for name in names}


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "uname": list(platform.uname()),
        "advisor_sha": ADVISOR_SHA,
        "packages": package_versions(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
    }


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value * 1024 if platform.system() == "Linux" else value)


def compact_result(result: Any) -> dict[str, Any]:
    raw = jsonable(result)
    fields = (
        "status",
        "termination_reason",
        "selected",
        "maintenance_cost",
        "objective",
        "lower_bound",
        "upper_bound",
        "validated_feasible",
        "solver_reported_optimal",
        "task_details",
        "task_evaluations",
        "task_evaluation_requests",
        "task_evaluation_computations",
        "exact_oracle_invocations",
        "ordinary_matching_bound_evaluations",
        "distinct_task_local_configurations",
        "total_runtime_seconds",
        "master_iterations",
        "distinct_cuts",
        "inner_mip_solve_calls",
        "exact_inner_seconds",
        "ordinary_matching_seconds",
        "cache_hits",
        "cache_misses",
        "cache_entries",
    )
    return {field: raw.get(field) for field in fields}


def run(path: Path, endpoint_seconds: float, inner_seconds: float) -> dict[str, Any]:
    instance = read_instance(path)
    calls: list[dict[str, Any]] = []
    original = solvers_v2.evaluate_task

    def wrapped(instance_arg: Instance, task: Task, selected: frozenset[str], *args: Any, **kwargs: Any) -> Any:
        call_started = time.perf_counter()
        key_payload = canonical_call(instance_arg, task, selected, kwargs)
        digest = key_digest(key_payload)
        record: dict[str, Any] = {
            "sequence": len(calls),
            "task_id": task.id,
            "selected_global_labels": sorted(selected),
            "selected_task_labels": sorted(set(selected) & set(task.eligible_candidates)),
            "key_digest": digest,
            "key_payload": key_payload,
            "start_monotonic": call_started,
        }
        try:
            result = original(instance_arg, task, selected, *args, **kwargs)
            record.update(
                {
                    "outcome": "returned",
                    "source": result.source,
                    "value": str(result.value),
                    "lower_bound": str(result.lower_bound),
                    "upper_bound": str(result.upper_bound),
                    "worst_matching": sorted(result.worst_matching),
                    "solver_status_count": len(result.solver_statuses),
                }
            )
            return result
        except Exception as exc:
            record.update(
                {
                    "outcome": "error",
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                }
            )
            raise
        finally:
            record["end_monotonic"] = time.perf_counter()
            record["duration_seconds"] = record["end_monotonic"] - call_started
            calls.append(record)

    solvers_v2.evaluate_task = wrapped
    try:
        started = time.perf_counter()
        result = solve_master_oracle(
            instance,
            total_time_limit=endpoint_seconds,
            inner_time_limit=inner_seconds,
            certification_tolerance=0.0,
            cut_tolerance=1e-6,
            options=MasterOracleOptions(),
        )
        elapsed = time.perf_counter() - started
        outcome = "completed"
        error = None
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        result = None
        outcome = "error"
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        solvers_v2.evaluate_task = original

    by_digest: dict[str, list[dict[str, Any]]] = {}
    by_local: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for call in calls:
        by_digest.setdefault(call["key_digest"], []).append(call)
        local_key = (call["task_id"], tuple(call["selected_task_labels"]))
        by_local.setdefault(local_key, []).append(call)
    duplicate_calls = [
        call
        for group in by_digest.values()
        for call in group[1:]
    ]
    local_repeats = [
        {
            "task_id": task_id,
            "selected_task_labels": list(labels),
            "count": len(group),
            "distinct_full_keys": len({call["key_digest"] for call in group}),
            "key_digests": [call["key_digest"] for call in group],
        }
        for (task_id, labels), group in sorted(by_local.items())
        if len(group) > 1
    ]
    task_oracle_seconds = sum((call["duration_seconds"] for call in calls), 0.0)
    repeated_seconds = sum((call["duration_seconds"] for call in duplicate_calls), 0.0)
    return {
        "profile_version": PROFILE_VERSION,
        "outcome": outcome,
        "error": error,
        "instance": str(path.resolve()),
        "input_sha256": sha256(path),
        "endpoint_seconds": endpoint_seconds,
        "inner_seconds": inner_seconds,
        "environment": environment(),
        "advisor_api": "solve_master_oracle + MasterOracleOptions() with evaluate_task no-op wrapper",
        "solver_result": compact_result(result) if result is not None else None,
        "full_invocation_wall_seconds": elapsed,
        "task_oracle_call_count": len(calls),
        "task_oracle_wall_seconds": task_oracle_seconds,
        "full_key_unique_count": len(by_digest),
        "full_key_duplicate_call_count": len(duplicate_calls),
        "full_key_duplicate_wall_seconds": repeated_seconds,
        "full_key_duplicate_fraction_of_task_oracle_wall": repeated_seconds / task_oracle_seconds if task_oracle_seconds else 0.0,
        "local_semantic_repeats": local_repeats,
        "calls": calls,
        "peak_rss_bytes": peak_rss_bytes(),
        "process": {"pid": os.getpid(), "cwd": os.getcwd()},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--endpoint-seconds", type=float, default=5.0)
    parser.add_argument("--inner-seconds", type=float, default=5.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    record = run(args.instance, args.endpoint_seconds, args.inner_seconds)
    write_text_exclusive(args.output, json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps({key: record[key] for key in ("instance", "outcome", "task_oracle_call_count", "full_key_duplicate_call_count", "full_key_duplicate_fraction_of_task_oracle_wall")}, sort_keys=True))
    return 0 if record["outcome"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
