"""Run the task-local-cache and invariant-precomputation ablation study."""

from __future__ import annotations

import json
import platform
import statistics
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import networkx
import numpy
import scipy
from pess_ess.model import Candidate, Instance, Task, read_instance, write_instance
from pess_ess.reference import solve_exhaustive
from pess_ess.solvers import MasterOracleOptions, solve_master_oracle, solve_static
from run_suite import (
    _outer_record,
    _sha256,
    _task_graph_stats,
)

ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = ROOT / "instances"
TARGET_DIR = INSTANCE_DIR / "cache-ablation"
RESULT_DIR = ROOT / "results"
RESULT_PATH = RESULT_DIR / "cache-ablation-results.json"
REPORT_PATH = ROOT / "cache-ablation-report.md"

REPETITIONS = 7
MASTER_TIME_LIMIT = 10.0
INNER_TIME_LIMIT = 5.0

VARIANTS = (
    ("master_oracle_baseline", MasterOracleOptions()),
    (
        "master_oracle_precompute",
        MasterOracleOptions(precompute_invariants=True),
    ),
    ("master_oracle_cache", MasterOracleOptions(task_local_cache=True)),
    (
        "master_oracle_combined",
        MasterOracleOptions(precompute_invariants=True, task_local_cache=True),
    ),
)


def _git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _targeted_instance(high_reuse: bool) -> Instance:
    endpoints = (
        ("a0", "a1"),
        ("a0", "a1"),
        ("a0", "a2"),
        ("a1", "a3"),
        ("a2", "a3"),
        ("a2", "a4"),
        ("a3", "a4"),
        ("a0", "a4"),
    )
    costs = (1, 1, 2, 1, 2, 1, 2, 1)
    candidates = tuple(
        Candidate(f"e{index:03d}", "t0", pair, Fraction(cost))
        for index, (pair, cost) in enumerate(zip(endpoints, costs, strict=True))
    )
    if high_reuse:
        scopes = (
            ("e000", "e001", "e002", "e003"),
            ("e000", "e001", "e002", "e003"),
            ("e000", "e002", "e004"),
            ("e000", "e001", "e002", "e003"),
            ("e001", "e003", "e005", "e007"),
            ("e000", "e002", "e004"),
            ("e001", "e003", "e005", "e007"),
            ("e000", "e001", "e002", "e003"),
        )
    else:
        scopes = (
            ("e000", "e002"),
            ("e001", "e003"),
            ("e002", "e004"),
            ("e003", "e005"),
            ("e004", "e006"),
            ("e005", "e007"),
            ("e006", "e000"),
            ("e007", "e001"),
        )
    tasks = []
    for index, scope in enumerate(scopes):
        alpha = Fraction((-3 + 2 * index) % 7 - 3, 1)
        corrections = {
            candidate_id: Fraction(((index + 3 * position) % 9) - 4, 2)
            for position, candidate_id in enumerate(scope)
        }
        tasks.append(
            Task(
                id=f"i{index:03d}",
                table="t0",
                weight=Fraction(1 + index % 3),
                alpha=alpha,
                eligible_candidates=scope,
                corrections=corrections,
            )
        )
    return Instance(candidates, tuple(tasks), Fraction(5))


def _ensure_targeted_instances() -> tuple[tuple[str, Path, Instance], ...]:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    specs = (
        ("targeted_high_reuse", True),
        ("targeted_low_reuse", False),
    )
    output = []
    for instance_id, high_reuse in specs:
        path = TARGET_DIR / f"{instance_id}.json"
        if path.exists():
            instance = read_instance(path)
        else:
            instance = _targeted_instance(high_reuse)
            write_instance(path, instance)
        output.append((instance_id, path, instance))
    return tuple(output)


def _reference_record(instance_id: str, path: Path, instance: Instance) -> dict[str, object]:
    started = time.perf_counter()
    result = solve_exhaustive(instance)
    elapsed = time.perf_counter() - started
    return {
        "kind": "reference",
        "instance_id": instance_id,
        "instance_sha256": _sha256(path),
        "status": "complete",
        "runtime_seconds": elapsed,
        "objective": str(result.objective),
        "optimal_sets": [sorted(item) for item in result.optimal_sets],
        "evaluated_subsets": result.evaluated_subsets,
        "feasible_subsets": result.feasible_subsets,
    }


def _run_solver(
    instance_id: str,
    instance: Instance,
    solver_name: str,
    repetition: int,
    options: MasterOracleOptions | None,
) -> dict[str, object]:
    started = time.perf_counter()
    if solver_name == "static_full_conditional":
        result = solve_static(
            instance,
            time_limit=MASTER_TIME_LIMIT,
            total_time_limit=MASTER_TIME_LIMIT,
        )
    else:
        assert options is not None
        result = solve_master_oracle(
            instance,
            time_limit=MASTER_TIME_LIMIT,
            inner_time_limit=INNER_TIME_LIMIT,
            total_time_limit=MASTER_TIME_LIMIT,
            options=options,
        )
    return _outer_record(
        instance_id,
        solver_name,
        result,
        time.perf_counter() - started,
        repetition,
    )


def _summary(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for record in records:
        if record.get("kind") != "solver":
            continue
        grouped.setdefault(
            (str(record["instance_id"]), str(record["solver"])), []
        ).append(record)
    counters = (
        "master_iterations",
        "distinct_cuts",
        "task_evaluation_requests",
        "task_evaluation_computations",
        "distinct_task_local_configurations",
        "cache_hits",
        "cache_misses",
        "ordinary_matching_bound_evaluations",
        "full_graph_ordinary_matching_extrema_computations",
        "inner_mip_solve_calls",
        "highs_invocations",
        "presolve_fallback_attempts",
    )
    summaries = []
    for (instance_id, solver), values in sorted(grouped.items()):
        runtimes = [float(item["runtime_seconds"]) for item in values]
        quartiles = statistics.quantiles(runtimes, n=4, method="inclusive")
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
                    field: statistics.median(float(item.get(field, 0)) for item in values)
                    for field in counters
                },
                "cache_hit_rate_median": statistics.median(
                    float(item.get("cache_hit_rate", 0.0)) for item in values
                ),
                "objectives": sorted(
                    {
                        str(item["objective"])
                        for item in values
                        if item.get("objective") is not None
                    }
                ),
                "all_validated_feasible": all(
                    bool(item.get("validated_feasible")) for item in values
                ),
            }
        )
    return summaries


def run() -> dict[str, object]:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    fixed_ids = (
        "tiny_mixed",
        "small_shared",
        "parallel_zero_cost",
        "positive_sign",
        "medium_dense",
    )
    instances: list[tuple[str, Path, Instance]] = []
    for instance_id in fixed_ids:
        path = INSTANCE_DIR / f"{instance_id}.json"
        instances.append((instance_id, path, read_instance(path)))
    instances.extend(_ensure_targeted_instances())

    records: list[dict[str, object]] = []
    references: dict[str, dict[str, object]] = {}
    for instance_id, path, instance in instances:
        reference = _reference_record(instance_id, path, instance)
        references[instance_id] = reference
        records.append(
            {
                "kind": "instance",
                "instance_id": instance_id,
                "instance_sha256": _sha256(path),
                "candidate_count": len(instance.candidates),
                "task_count": len(instance.tasks),
                "budget": str(instance.budget),
                "task_graphs": _task_graph_stats(instance),
            }
        )
        records.append(reference)

    solver_specs = (("static_full_conditional", None),) + VARIANTS
    for instance_id, _path, instance in instances:
        for repetition in range(REPETITIONS):
            rotated = solver_specs[repetition % len(solver_specs) :] + solver_specs[
                : repetition % len(solver_specs)
            ]
            for solver_name, options in rotated:
                record = _run_solver(
                    instance_id,
                    instance,
                    solver_name,
                    repetition,
                    options,
                )
                reference = references[instance_id]
                record["reference_agreement"] = (
                    record["status"] == "optimal"
                    and bool(record.get("validated_feasible"))
                    and record.get("objective") == reference["objective"]
                )
                records.append(record)

    metadata = {
        "python": sys.version,
        "platform": platform.platform(),
        "dependency_versions": {
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "networkx": networkx.__version__,
        },
        "advisor_source_commit": _git_head(Path("/home/wqts/projects/ess-advisor")),
        "research_source_commit": _git_head(Path("/home/wqts/projects/ess-research")),
        "installation_commands": [
            "python3 -m venv .venv",
            ".venv/bin/python -m pip install -r requirements.txt",
            ".venv/bin/python -m pip install -e /home/wqts/projects/ess-advisor",
        ],
        "repetitions": REPETITIONS,
        "warmup_policy": "none",
        "execution_order": (
            "for each instance and repetition, rotate the static and four "
            "Master--Oracle variants by repetition modulo five"
        ),
        "master_time_limit_seconds": MASTER_TIME_LIMIT,
        "inner_time_limit_seconds": INNER_TIME_LIMIT,
        "timing_convention": (
            "runtime_seconds is an external monotonic interval around one "
            "solver invocation; serialization and report generation are excluded. "
            "Phase timings are internal diagnostics and can differ from the "
            "external interval because of nesting and backend overhead."
        ),
        "medium_dense_reference_is_complete": True,
        "historical_suite_results_preserved": True,
    }
    payload = {
        "metadata": metadata,
        "references": references,
        "records": records,
        "summaries": _summary(records),
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_report(payload)
    return payload


def write_report(payload: dict[str, object]) -> None:
    summaries = payload["summaries"]
    references = payload["references"]
    lines = [
        "# Task-local cache and invariant-precomputation ablation",
        "",
        (
            "This report is generated from `cache-ablation-results.json`. It is a "
            "synthetic study of the Advisor implementation; it is not evidence "
            "about PostgreSQL estimation quality."
        ),
        "",
        f"- Python: {payload['metadata']['python'].splitlines()[0]}",
        f"- Platform: {payload['metadata']['platform']}",
        f"- Libraries: {payload['metadata']['dependency_versions']}",
        f"- Repetitions per solver/instance: {REPETITIONS}",
        f"- Limits: {MASTER_TIME_LIMIT}s complete invocation, {INNER_TIME_LIMIT}s per inner solve",
        "- Static baseline: unchanged full conditional MILP.",
        "- Master variants: baseline, precompute-only, cache-only, and combined.",
        "- The fixed-seed instance files are loaded without regeneration.",
        "- Targeted instances are deterministic and their hashes are recorded below.",
        "",
        "## Independent Fraction references",
        "",
        "| Instance | SHA-256 | Evaluated subsets | Feasible subsets | Objective | Runtime (s) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for instance_id, reference in sorted(references.items()):
        lines.append(
            f"| {instance_id} | `{reference['instance_sha256']}` | "
            f"{reference['evaluated_subsets']} | {reference['feasible_subsets']} | "
            f"{reference['objective']} | {reference['runtime_seconds']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Repeated solver summaries",
            "",
            (
                "| Instance | Solver | Statuses | Objective(s) | Median s | IQR s | "
                "Cuts | Task computations | Cache hits | Hit rate | Inner MIP solves |"
            ),
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in summaries:
        runtime = summary["runtime_seconds"]
        counters = summary["counter_medians"]
        lines.append(
            f"| {summary['instance_id']} | {summary['solver']} | "
            f"{summary['status_counts']} | {summary['objectives']} | "
            f"{runtime['median']:.6f} | {runtime['iqr']:.6f} | "
            f"{counters['distinct_cuts']:.1f} | "
            f"{counters['task_evaluation_computations']:.1f} | "
            f"{counters['cache_hits']:.1f} | "
            f"{summary['cache_hit_rate_median']:.3f} | "
            f"{counters['inner_mip_solve_calls']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The references certify the exact objective for every listed small "
                "instance, including `medium_dense` (12 candidates, 4096 possible "
                "subsets). Each solver record also retains its solver status, primal "
                "and dual information, validation flags, witnesses, and fallback "
                "diagnostics. A cache hit reuses a completed task-local result and "
                "does not increment inner MIP or HiGHS invocation counters."
            ),
            "",
            (
                "Runtime differences are descriptive measurements only. In particular, "
                "fewer inner solves do not by themselves establish lower end-to-end "
                "runtime; cache management and repeated master solves remain part of "
                "the measured invocation interval."
            ),
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
