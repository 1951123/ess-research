"""Run the first fixed-seed synthetic PESS-ESS comparison."""

# The legacy report helper uses deliberate adjacent string literals.
# ruff: noqa: ISC004

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from fractions import Fraction
from pathlib import Path

import networkx
import numpy
import scipy
from pess_ess.generate import generate_instance
from pess_ess.matchings import enumerate_matchings
from pess_ess.model import Instance, fraction_to_json, read_instance, write_instance
from pess_ess.reference import solve_exhaustive
from pess_ess.solvers import OuterResult, solve_master_oracle, solve_static

ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = ROOT / "instances"
RESULT_DIR = ROOT / "results"
RESULT_PATH = RESULT_DIR / "suite-results.json"
REPORT_PATH = ROOT / "report.md"
REPETITIONS = 5
MASTER_TIME_LIMIT = 10.0
INNER_TIME_LIMIT = 5.0


CONFIGS = (
    {
        "instance_id": "tiny_mixed",
        "seed": 101,
        "candidate_count": 5,
        "task_count": 3,
        "attribute_count": 4,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": True,
    },
    {
        "instance_id": "small_shared",
        "seed": 202,
        "candidate_count": 7,
        "task_count": 4,
        "attribute_count": 5,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": True,
    },
    {
        "instance_id": "parallel_zero_cost",
        "seed": 303,
        "candidate_count": 8,
        "task_count": 4,
        "attribute_count": 4,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": True,
        "tight_budget": False,
        "exhaustive": True,
    },
    {
        "instance_id": "positive_sign",
        "seed": 404,
        "candidate_count": 8,
        "task_count": 4,
        "attribute_count": 5,
        "mixed_sign": False,
        "sign_mode": "positive",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": True,
    },
    {
        "instance_id": "medium_dense",
        "seed": 505,
        "candidate_count": 12,
        "task_count": 6,
        "attribute_count": 5,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": False,
    },
)


def _fraction(value: Fraction | None) -> str | None:
    return fraction_to_json(value) if value is not None else None


def _solver_statuses(result: OuterResult) -> list[dict[str, object]]:
    return [
        {
            "status": item.status,
            "message": item.message,
            "primal_objective": item.primal_objective,
            "dual_bound": item.dual_bound,
            "mip_gap": item.mip_gap,
            "mip_node_count": item.mip_node_count,
            "selected_attempt": item.selected_attempt,
            "highs_invocations": item.highs_invocations,
            "presolve_fallback_attempted": item.presolve_fallback_attempted,
            "presolve_fallback_successes": item.presolve_fallback_successes,
            "initial_attempt": {
                "status": item.initial_attempt.status,
                "message": item.initial_attempt.message,
                "duration_seconds": item.initial_attempt.duration_seconds,
                "primal_objective": item.initial_attempt.primal_objective,
                "dual_bound": item.initial_attempt.dual_bound,
                "incumbent_returned": item.initial_attempt.incumbent_returned,
            },
            "retry_attempt": (
                {
                    "status": item.retry_attempt.status,
                    "message": item.retry_attempt.message,
                    "duration_seconds": item.retry_attempt.duration_seconds,
                    "primal_objective": item.retry_attempt.primal_objective,
                    "dual_bound": item.retry_attempt.dual_bound,
                    "incumbent_returned": item.retry_attempt.incumbent_returned,
                }
                if item.retry_attempt is not None
                else None
            ),
        }
        for item in result.solver_statuses
    ]


def _outer_record(
    instance_id: str,
    solver: str,
    result: OuterResult,
    elapsed: float,
    repetition: int,
) -> dict[str, object]:
    return {
        "kind": "solver",
        "instance_id": instance_id,
        "solver": solver,
        "repetition": repetition,
        "status": result.status,
        "termination_reason": result.termination_reason,
        "selected": sorted(result.selected) if result.selected is not None else None,
        "maintenance_cost": _fraction(result.maintenance_cost),
        "objective": _fraction(result.objective),
        "lower_bound": result.lower_bound,
        "upper_bound": result.upper_bound,
        "master_primal_bound": result.master_primal_bound,
        "master_dual_bound": result.master_dual_bound,
        "master_mip_gap": result.master_mip_gap,
        "solver_reported_optimal": result.solver_reported_optimal,
        "validated_feasible": result.validated_feasible,
        "reference_agreement": result.reference_agreement,
        "numerical_warnings": list(result.numerical_warnings),
        "numerical_violation_count": result.numerical_violation_count,
        "existing_cut_violation_count": result.existing_cut_violation_count,
        "master_iterations": result.master_iterations,
        "distinct_cuts": result.distinct_cuts,
        "inner_oracle_calls": result.inner_oracle_calls,
        "certified_early_exits": result.certified_early_exits,
        "task_evaluations": result.task_evaluations,
        "ordinary_matching_bound_evaluations": (
            result.ordinary_matching_bound_evaluations
        ),
        "exact_oracle_invocations": result.exact_oracle_invocations,
        "inner_mip_solve_calls": result.inner_mip_solve_calls,
        "highs_invocations": result.highs_invocations,
        "presolve_fallback_attempts": result.presolve_fallback_attempts,
        "presolve_fallback_successes": result.presolve_fallback_successes,
        "scenario_count": result.scenario_count,
        "runtime_seconds": elapsed,
        "phase_seconds": {
            "master": result.master_phase_seconds,
            "ordinary_matching": result.ordinary_matching_seconds,
            "exact_inner": result.exact_inner_seconds,
            "cut_construction": result.cut_construction_seconds,
            "validation": result.validation_seconds,
            "outer_internal_total": result.total_runtime_seconds,
        },
        "solver_statuses": _solver_statuses(result),
        "task_details": {
            task_id: {
                "loss": _fraction(loss),
                "witness": sorted(witness),
            }
            for task_id, (loss, witness) in sorted(result.task_details.items())
        },
    }


def _reference_record(
    instance_id: str,
    result,
    elapsed: float,
    repetition: int,
) -> dict[str, object]:
    return {
        "kind": "solver",
        "instance_id": instance_id,
        "solver": "exhaustive_reference",
        "repetition": repetition,
        "status": "optimal",
        "termination_reason": "complete finite enumeration",
        "selected": [sorted(item) for item in result.optimal_sets],
        "maintenance_cost": None,
        "objective": _fraction(result.objective),
        "lower_bound": float(result.objective),
        "upper_bound": float(result.objective),
        "master_iterations": 0,
        "distinct_cuts": 0,
        "inner_oracle_calls": 0,
        "certified_early_exits": 0,
        "scenario_count": None,
        "runtime_seconds": elapsed,
        "evaluated_subsets": result.evaluated_subsets,
        "feasible_subsets": result.feasible_subsets,
    }


def measure_reference(
    instance_id: str,
    instance: Instance,
    repetition: int,
    *,
    solver=solve_exhaustive,
    clock=time.perf_counter,
) -> dict[str, object]:
    started = clock()
    reference_result = solver(instance)
    elapsed = clock() - started
    return _reference_record(
        instance_id,
        reference_result,
        elapsed,
        repetition,
    )


def _task_graph_stats(instance: Instance) -> list[dict[str, object]]:
    candidate_map = instance.candidate_map
    rows = []
    for task in instance.tasks:
        endpoints = {
            candidate_id: candidate_map[candidate_id].endpoints
            for candidate_id in task.eligible_candidates
        }
        scenario_count = len(enumerate_matchings(task.eligible_candidates, endpoints))
        rows.append(
            {
                "task_id": task.id,
                "eligible_candidates": len(task.eligible_candidates),
                "distinct_attributes": len(
                    {
                        endpoint
                        for candidate_id in task.eligible_candidates
                        for endpoint in candidate_map[candidate_id].endpoints
                    }
                ),
                "full_matching_scenarios": scenario_count,
            }
        )
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _summary(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for record in records:
        if record.get("kind") != "solver":
            continue
        grouped.setdefault(
            (str(record["instance_id"]), str(record["solver"])),
            [],
        ).append(record)
    summaries = []
    counter_fields = (
        "master_iterations",
        "distinct_cuts",
        "inner_mip_solve_calls",
        "exact_oracle_invocations",
        "certified_early_exits",
        "presolve_fallback_attempts",
    )
    for (instance_id, solver), values in sorted(grouped.items()):
        runtimes = [float(item["runtime_seconds"]) for item in values]
        ordered = sorted(runtimes)
        quartiles = (
            statistics.quantiles(ordered, n=4, method="inclusive")
            if len(ordered) >= 2
            else [ordered[0]] * 3
        )
        summaries.append(
            {
                "kind": "summary",
                "instance_id": instance_id,
                "solver": solver,
                "repetitions": len(values),
                "runtime_seconds": {
                    "median": statistics.median(runtimes),
                    "minimum": min(runtimes),
                    "maximum": max(runtimes),
                    "iqr": quartiles[2] - quartiles[0],
                },
                "status_counts": {
                    status: sum(item["status"] == status for item in values)
                    for status in sorted({str(item["status"]) for item in values})
                },
                "counter_medians": {
                    field: statistics.median(
                        float(item.get(field, 0)) for item in values
                    )
                    for field in counter_fields
                },
                "objectives": sorted(
                    {
                        str(item["objective"])
                        for item in values
                        if item.get("objective") is not None
                    }
                ),
                "all_validated_feasible": all(
                    bool(item.get("validated_feasible", item["status"] == "optimal"))
                    for item in values
                    if solver != "exhaustive_reference"
                ),
            }
        )
    return summaries


def run() -> tuple[list[dict[str, object]], dict[str, object]]:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    metadata = {
        "python": sys.version,
        "platform": platform.platform(),
        "dependency_versions": {
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "networkx": networkx.__version__,
        },
        "installation_commands": [
            "python3 -m venv .venv",
            ".venv/bin/python -m pip install -r requirements.txt",
            ".venv/bin/python -m pip install -e /home/wqts/projects/ess-advisor",
        ],
        "configs": CONFIGS,
        "repetitions": REPETITIONS,
        "warmup_policy": "none; all recorded runs are cold-start benchmark observations",
        "execution_order": "configuration order in CONFIGS, then repetition, then reference/static/master",
        "time_limit_seconds": MASTER_TIME_LIMIT,
        "inner_time_limit_seconds": INNER_TIME_LIMIT,
        "historical_exhaustive_runtime_valid": False,
        "timing_convention": (
            "runtime_seconds is an external monotonic interval around one "
            "solver/reference invocation. It includes that algorithm's Python "
            "work and backend call, excludes JSON/report serialization, and "
            "does not include other solver invocations. Phase fields are "
            "internal diagnostics and may not sum exactly to the external interval."
        ),
    }
    for config in CONFIGS:
        instance_id = str(config["instance_id"])
        instance_path = INSTANCE_DIR / f"{instance_id}.json"
        if instance_path.exists():
            instance = read_instance(instance_path)
        else:
            instance = generate_instance(
                seed=int(config["seed"]),
                candidate_count=int(config["candidate_count"]),
                task_count=int(config["task_count"]),
                attribute_count=int(config["attribute_count"]),
                mixed_sign=bool(config["mixed_sign"]),
                sign_mode=str(config["sign_mode"]),
                zero_cost=bool(config["zero_cost"]),
                tight_budget=bool(config["tight_budget"]),
            )
            write_instance(instance_path, instance)
        stats = {
            "kind": "instance",
            "instance_id": instance_id,
            "seed": config["seed"],
            "candidate_count": len(instance.candidates),
            "task_count": len(instance.tasks),
            "budget": fraction_to_json(instance.budget),
            "task_graphs": _task_graph_stats(instance),
            "instance_sha256": _sha256(instance_path),
        }
        records.append(stats)
        for repetition in range(REPETITIONS):
            if bool(config["exhaustive"]):
                records.append(
                    measure_reference(
                        instance_id,
                        instance,
                        repetition,
                    )
                )
            started = time.perf_counter()
            static = solve_static(
                instance,
                time_limit=MASTER_TIME_LIMIT,
                total_time_limit=MASTER_TIME_LIMIT,
            )
            records.append(
                _outer_record(
                    instance_id,
                    "static_full_conditional",
                    static,
                    time.perf_counter() - started,
                    repetition,
                )
            )
            started = time.perf_counter()
            master = solve_master_oracle(
                instance,
                time_limit=MASTER_TIME_LIMIT,
                inner_time_limit=INNER_TIME_LIMIT,
                total_time_limit=MASTER_TIME_LIMIT,
            )
            records.append(
                _outer_record(
                    instance_id,
                    "master_oracle",
                    master,
                    time.perf_counter() - started,
                    repetition,
                )
            )
    reference_objectives = {
        str(record["instance_id"]): record["objective"]
        for record in records
        if record.get("solver") == "exhaustive_reference"
    }
    for record in records:
        if (
            record.get("kind") != "solver"
            or record.get("solver") == "exhaustive_reference"
        ):
            continue
        reference = reference_objectives.get(str(record["instance_id"]))
        if reference is not None:
            record["reference_agreement"] = (
                record["status"] == "optimal"
                and bool(record.get("validated_feasible"))
                and record.get("objective") == reference
            )
    payload = {
        "metadata": metadata,
        "records": records,
        "summaries": _summary(records),
    }
    RESULT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return records, metadata


def write_report(records: list[dict[str, object]], metadata: dict[str, object]) -> None:
    instances = [record for record in records if record["kind"] == "instance"]
    by_instance: dict[str, list[dict[str, object]]] = {}
    for record in records:
        by_instance.setdefault(str(record["instance_id"]), []).append(record)
    lines = [
        "# First synthetic PESS-ESS study",
        "",
        "This report is generated from suite-results.json; unresolved solver "
        "statuses are not interpreted as optimal results.",
        "",
        f"- Python: {metadata['python'].splitlines()[0]}",
        f"- Platform: {metadata['platform']}",
        f"- Library versions: {metadata['dependency_versions']}",
        "- Solver backend: SciPy optimize.milp with HiGHS",
        "- Master/inner limits: 10 s / 5 s",
        "- Installation: python3 -m venv .venv; pip install -r requirements.txt; "
        "pip install -e /home/wqts/projects/ess-advisor",
        "",
        "## Results",
        "",
        "| Instance | Candidates | Tasks | Solver | Status | Objective | Runtime (s) | LB | UB | Scenarios/cuts | Inner calls | Early exits |",
        "|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for instance in instances:
        instance_id = str(instance["instance_id"])
        for record in by_instance[instance_id]:
            if record["kind"] == "instance":
                continue
            objective = record.get("objective")
            lines.append(
                f"| {instance_id} | {instance['candidate_count']} | "
                f"{instance['task_count']} | {record['solver']} | "
                f"{record['status']} | {objective or '—'} | "
                f"{record['runtime_seconds']:.4f} | "
                f"{record.get('lower_bound', '—')} | "
                f"{record.get('upper_bound', '—')} | "
                f"{record.get('scenario_count', record.get('distinct_cuts', '—'))} | "
                f"{record.get('inner_oracle_calls', '—')} | "
                f"{record.get('certified_early_exits', '—')} |"
            )
    lines.extend(["", "## Exhaustive agreement", ""])
    for instance in instances:
        instance_id = str(instance["instance_id"])
        records_for_instance = by_instance[instance_id]
        reference = next(
            (
                record
                for record in records_for_instance
                if record.get("solver") == "exhaustive_reference"
            ),
            None,
        )
        if reference is None:
            lines.append(
                f"- {instance_id}: no exhaustive reference; solver objectives "
                "are reported only with their MIP statuses."
            )
            continue
        reference_objective = reference["objective"]
        checked = [
            record
            for record in records_for_instance
            if record.get("solver")
            in {
                "static_full_conditional",
                "master_oracle",
            }
        ]
        agreement = all(
            record["status"] == "optimal" and record["objective"] == reference_objective
            for record in checked
        )
        lines.append(
            f"- {instance_id}: reference objective {reference_objective}; "
            f"static and Master--Oracle exact agreement: {agreement}."
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "For exhaustive instances, the test suite compares both MIP-based "
            "outer methods against an independent Fraction-based reference. "
            "Static formulation scenario counts measure the complete matching "
            "index, while Master–Oracle cut counts measure only generated "
            "conditional scenarios. A non-optimal status, if present, is an "
            "unresolved computational result rather than evidence of an "
            "algorithmic failure.",
            "",
            "These are synthetic measurements only. They do not establish "
            "PostgreSQL behavior, algorithmic superiority, or asymptotic "
            "performance guarantees.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_report_repeated(
    records: list[dict[str, object]],
    metadata: dict[str, object],
) -> None:
    instances = {
        str(record["instance_id"]): record
        for record in records
        if record["kind"] == "instance"
    }
    summaries = _summary(records)
    lines = [
        "# Synthetic PESS-ESS benchmark integrity rerun",
        "",
        "This report is generated from the repeated fixed-seed benchmark. "
        "Historical exhaustive-reference runtimes were invalid because the "
        "old runner started its timer before an empty wrapper rather than "
        "around solve_exhaustive; they are replaced by the measurements below.",
        "",
        f"- Python: {metadata['python'].splitlines()[0]}",
        f"- Platform: {metadata['platform']}",
        f"- Libraries: {metadata['dependency_versions']}",
        "- Backend: SciPy optimize.milp with HiGHS",
        f"- Repetitions: {metadata['repetitions']}; warm-up: {metadata['warmup_policy']}",
        "- Timing: external monotonic interval around one solver invocation; "
        "serialization and report generation are excluded.",
        f"- Limits: master {metadata['time_limit_seconds']} s; "
        f"inner {metadata['inner_time_limit_seconds']} s; "
        "the same total wall-clock limit is applied to each outer invocation.",
        "",
        "## Repeated runtime summaries",
        "",
        "| Instance | Solver | Reps | Median (s) | Min (s) | Max (s) | IQR (s) | Status counts | Median iterations | Median cuts | Median inner MIP calls | Median early exits | Fallbacks |",
        "|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        runtime = summary["runtime_seconds"]
        counters = summary["counter_medians"]
        fallback = counters["presolve_fallback_attempts"]
        lines.append(
            f"| {summary['instance_id']} | {summary['solver']} | "
            f"{summary['repetitions']} | {runtime['median']:.6f} | "
            f"{runtime['minimum']:.6f} | {runtime['maximum']:.6f} | "
            f"{runtime['iqr']:.6f} | {summary['status_counts']} | "
            f"{counters['master_iterations']:.1f} | "
            f"{counters['distinct_cuts']:.1f} | "
            f"{counters['inner_mip_solve_calls']:.1f} | "
            f"{counters['certified_early_exits']:.1f} | {fallback:.1f} |"
        )
    lines.extend(["", "## Correctness and certification", ""])
    for instance_id, instance in sorted(instances.items()):
        reference_records = [
            record
            for record in records
            if record.get("instance_id") == instance_id
            and record.get("solver") == "exhaustive_reference"
        ]
        if not reference_records:
            lines.append(
                f"- **{instance_id}** ({instance['candidate_count']} candidates, "
                f"{instance['task_count']} tasks): no exhaustive reference; "
                "MIP results are not independently globally certified."
            )
            continue
        reference_objective = reference_records[0]["objective"]
        lines.append(
            f"- **{instance_id}** reference objective: '{reference_objective}'."
        )
        for solver in ("static_full_conditional", "master_oracle"):
            solver_records = [
                record
                for record in records
                if record.get("instance_id") == instance_id
                and record.get("solver") == solver
            ]
            agreement = all(
                item["status"] == "optimal"
                and item.get("validated_feasible")
                and item["objective"] == reference_objective
                for item in solver_records
            )
            warnings = sum(
                len(item.get("numerical_warnings", [])) for item in solver_records
            )
            lines.append(
                f"  - {solver}: reference agreement '{agreement}' over "
                f"{len(solver_records)} repetitions; numerical warnings '{warnings}'."
            )
    lines.extend(
        [
            "",
            "## Phase and numerical interpretation",
            "",
            "The static formulation enumerates all matching scenarios; its "
            "scenario count is a formulation-size diagnostic. Master--Oracle "
            "cut counts are generated conditional scenarios, not a proof of "
            "runtime superiority. Exact inner-oracle invocations and inner "
            "MIP solves are separate counters; one exact oracle may use two "
            "MIP solves. Ordinary matching bounds and witness construction "
            "are timed separately from exact inner MIP work.",
            "",
            "The result schema records a MIP primal incumbent separately from "
            "the HiGHS dual bound. A solver-reported optimal status is not "
            "treated as an exact-arithmetic proof. Near-tolerance violations "
            "are retained as warnings. A failed validation, unresolved "
            "inner solve, or global deadline is not interpreted as an optimum.",
            "",
            "These are synthetic measurements only. They do not establish "
            "PostgreSQL behavior, asymptotic guarantees, or algorithmic "
            "superiority. Small runtimes can be dominated by process and "
            "backend noise; medians and ranges should be interpreted accordingly.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    records, metadata = run()
    write_report_repeated(records, metadata)
    print(f"wrote {RESULT_PATH}")
    print(f"wrote {REPORT_PATH}")
