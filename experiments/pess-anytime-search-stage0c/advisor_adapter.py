"""Read-only adapter to the pinned ess-advisor APIs for Gate A and baselines."""

from __future__ import annotations

import dataclasses
import json
import platform
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import networkx
import numpy
import scipy
from pess_ess.model import read_instance
from pess_ess.solvers_v2 import MasterOracleOptions, solve_master_oracle, solve_static

ADVISOR_SHA = "1052ff4a46270c90414d76b32d6f6b37e5908f6a"


def jsonable(value: Any) -> Any:
    if isinstance(value, Fraction):
        return str(value)
    if dataclasses.is_dataclass(value):
        return {key: jsonable(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, frozenset | set | tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "networkx": networkx.__version__,
        "advisor_sha": ADVISOR_SHA,
        "highs": "SciPy 1.18.1 bundled HiGHS; standalone HiGHS version is not exposed by the SciPy Python API",
    }


def _compact_attempt(attempt: dict[str, Any] | None) -> dict[str, Any] | None:
    if attempt is None:
        return None
    fields = (
        "status", "message", "primal_objective", "dual_bound", "mip_gap",
        "mip_node_count", "duration_seconds", "invocation_performed",
        "presolve", "incumbent_returned", "optimality_reported",
    )
    return {key: attempt.get(key) for key in fields}


def _compact_solver_status(status: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "status", "message", "primal_objective", "dual_bound", "mip_gap",
        "mip_node_count", "total_duration_seconds", "highs_invocations",
        "presolve_fallback_attempted", "presolve_fallback_successes",
        "selected_attempt",
    )
    compact = {key: status.get(key) for key in fields}
    compact["initial_attempt"] = _compact_attempt(status.get("initial_attempt"))
    compact["retry_attempt"] = _compact_attempt(status.get("retry_attempt"))
    return compact


def compact_result(result: Any) -> dict[str, Any]:
    """Keep every decision/validation/timing field, omitting solver value vectors."""
    raw = jsonable(result)
    fields = (
        "status", "termination_reason", "selected", "maintenance_cost", "objective",
        "lower_bound", "upper_bound", "task_details", "master_iterations",
        "distinct_cuts", "inner_oracle_calls", "exact_oracle_invocations",
        "certified_early_exits", "scenario_count", "solver_reported_optimal",
        "validated_feasible", "reference_agreement", "master_primal_bound",
        "master_dual_bound", "master_mip_gap", "numerical_warnings",
        "numerical_violation_count", "existing_cut_violation_count",
        "total_runtime_seconds", "validation_seconds", "master_phase_seconds",
        "exact_inner_seconds", "cut_construction_seconds", "cache_management_seconds",
        "invariant_precomputation_seconds", "ordinary_matching_seconds",
        "task_evaluation_requests", "task_evaluation_computations", "task_evaluations",
        "task_local_ordinary_matching_bound_computations",
        "full_graph_ordinary_matching_extrema_computations",
        "ordinary_matching_bound_evaluations", "distinct_task_local_configurations",
        "inner_mip_solve_calls", "highs_invocations", "cache_entries", "cache_lookups",
        "cache_hits", "cache_misses", "cache_hit_rate", "presolve_fallback_attempts",
        "presolve_fallback_successes",
    )
    compact = {key: raw.get(key) for key in fields if key in raw}
    compact["solver_statuses"] = [_compact_solver_status(item) for item in raw.get("solver_statuses", [])]
    return compact


def run_solver(
    instance_path: str | Path,
    method: str,
    total_time_limit: float,
    inner_time_limit: float | None = None,
    options: MasterOracleOptions | None = None,
) -> dict[str, Any]:
    instance = read_instance(instance_path)
    started = time.perf_counter()
    if method == "static":
        result = solve_static(instance, total_time_limit=total_time_limit)
    elif method == "master_oracle":
        result = solve_master_oracle(
            instance,
            total_time_limit=total_time_limit,
            inner_time_limit=inner_time_limit,
            certification_tolerance=0.0,
            cut_tolerance=1e-6,
            options=options or MasterOracleOptions(),
        )
    else:
        raise ValueError(f"unknown advisor method: {method}")
    wall = time.perf_counter() - started
    return {
        "instance": str(instance_path),
        "method": method,
        "options": jsonable(options or MasterOracleOptions()) if method == "master_oracle" else {},
        "limits": {
            "total_time_limit": total_time_limit,
            "inner_time_limit": inner_time_limit,
            "certification_tolerance": 0.0,
            "cut_tolerance": 1e-6,
        },
        "wall_seconds": wall,
        "within_total_limit": wall <= total_time_limit + 0.25,
        "environment": environment(),
        "result": compact_result(result),
    }


def write_result(path: str | Path, record: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")
