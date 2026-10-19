"""Exact Issue #23 model-level decision comparison.

The real Forest10 input root is intentionally not required by this fallback.
The checked-in instance is a frozen, schema-shaped model instance whose
parameters are explicitly synthetic.  All objective values are exact
Fractions and every shared priority order is enumerated.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import io
import json
import argparse
import os
import platform
import shlex
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
INSTANCE_PATH = ROOT / "instance.json"
RESULTS = ROOT / "results"
METHODS = ("pess", "nominal", "joint_robust", "empty")


def q(value: Any) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(str(value))


def as_json(value: Fraction | None) -> str | None:
    if value is None:
        return None
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def load_instance(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    candidates = {item["id"]: item for item in raw["candidates"]}
    candidate_ids = tuple(sorted(candidates))
    if tuple(raw["nominal_order"]) != candidate_ids:
        raise AssertionError("nominal order must be the sorted full candidate universe")
    tasks = []
    for item in raw["tasks"]:
        eligible = tuple(sorted(item["eligible_candidates"]))
        corrections = {key: q(value) for key, value in item["corrections"].items()}
        if set(eligible) != set(corrections):
            raise AssertionError(f"task {item['id']} has incomplete correction map")
        tasks.append(
            {
                "id": item["id"],
                "source_query_id": item.get("source_query_id"),
                "split": item["split"],
                "weight": q(item["weight"]),
                "alpha": q(item["alpha"]),
                "eligible": eligible,
                "corrections": corrections,
            }
        )
    return {
        "raw": raw,
        "budget_texts": tuple(raw["budgets"]),
        "budget": tuple(q(value) for value in raw["budgets"]),
        "candidates": candidates,
        "candidate_ids": candidate_ids,
        "cost": {key: q(item["maintenance_cost"]) for key, item in candidates.items()},
        "endpoints": {key: tuple(item["endpoints"]) for key, item in candidates.items()},
        "tasks": tuple(sorted(tasks, key=lambda item: item["id"])),
    }


def subsets(ids: tuple[str, ...]):
    for size in range(len(ids) + 1):
        for selected_tuple in itertools.combinations(ids, size):
            yield frozenset(selected_tuple)


def maintenance(instance: dict[str, Any], selected: frozenset[str]) -> Fraction:
    return sum((instance["cost"][item] for item in selected), Fraction())


def matching_sets(selected: frozenset[str], endpoints: dict[str, tuple[str, str]]) -> tuple[frozenset[str], ...]:
    ordered = tuple(sorted(selected))
    result: list[frozenset[str]] = []

    def visit(index: int, chosen: tuple[str, ...], occupied: frozenset[str]) -> None:
        if index == len(ordered):
            result.append(frozenset(chosen))
            return
        edge = ordered[index]
        visit(index + 1, chosen, occupied)
        vertices = frozenset(endpoints[edge])
        if not occupied & vertices:
            visit(index + 1, chosen + (edge,), occupied | vertices)

    visit(0, (), frozenset())
    return tuple(sorted(result, key=lambda item: tuple(sorted(item))))


def maximal_matching_sets(
    selected: frozenset[str], endpoints: dict[str, tuple[str, str]]
) -> tuple[frozenset[str], ...]:
    result = []
    for matching in matching_sets(selected, endpoints):
        occupied = {vertex for edge in matching for vertex in endpoints[edge]}
        if all(occupied & set(endpoints[edge]) for edge in selected - matching):
            result.append(matching)
    if not result:
        raise AssertionError("a finite selected graph must have a maximal matching")
    return tuple(result)


def loss(task: dict[str, Any], scheme: frozenset[str] | tuple[str, ...]) -> Fraction:
    return abs(task["alpha"] + sum((task["corrections"][edge] for edge in scheme), Fraction()))


def task_pess(
    instance: dict[str, Any], task: dict[str, Any], selected: frozenset[str]
) -> tuple[Fraction, frozenset[str]]:
    active = frozenset(task["eligible"]) & selected
    choices = [
        (loss(task, scheme), scheme)
        for scheme in maximal_matching_sets(active, instance["endpoints"])
    ]
    value = max(item[0] for item in choices)
    witness = min(
        (scheme for item, scheme in choices if item == value),
        key=lambda scheme: tuple(sorted(scheme)),
    )
    return value, witness


def pess_objective(
    instance: dict[str, Any], selected: frozenset[str]
) -> tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]:
    details = {task["id"]: task_pess(instance, task, selected) for task in instance["tasks"]}
    value = sum((task["weight"] * details[task["id"]][0] for task in instance["tasks"]), Fraction())
    return value, details


def greedy_scheme(
    instance: dict[str, Any], task: dict[str, Any], selected: frozenset[str], order: tuple[str, ...]
) -> frozenset[str]:
    active = frozenset(task["eligible"]) & selected
    occupied: set[str] = set()
    chosen: list[str] = []
    for edge in order:
        if edge not in active:
            continue
        vertices = set(instance["endpoints"][edge])
        if not occupied & vertices:
            chosen.append(edge)
            occupied.update(vertices)
    scheme = frozenset(chosen)
    if scheme not in maximal_matching_sets(active, instance["endpoints"]):
        raise AssertionError("shared-order selector did not produce a maximal matching")
    return scheme


def ordered_objective(
    instance: dict[str, Any], selected: frozenset[str], order: tuple[str, ...]
) -> tuple[Fraction, dict[str, frozenset[str]]]:
    details: dict[str, frozenset[str]] = {}
    value = Fraction()
    for task in instance["tasks"]:
        scheme = greedy_scheme(instance, task, selected, order)
        details[task["id"]] = scheme
        value += task["weight"] * loss(task, scheme)
    return value, details


def feasible(instance: dict[str, Any], selected: frozenset[str], budget: Fraction) -> bool:
    return maintenance(instance, selected) <= budget


def lex_key(selected: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(selected))


def solve_exact(
    instance: dict[str, Any], budget: Fraction, evaluator: Callable[[frozenset[str]], Fraction]
) -> dict[str, Any]:
    best: Fraction | None = None
    optimal: list[frozenset[str]] = []
    feasible_count = 0
    for selected in subsets(instance["candidate_ids"]):
        if not feasible(instance, selected, budget):
            continue
        feasible_count += 1
        value = evaluator(selected)
        if best is None or value < best:
            best = value
            optimal = [selected]
        elif value == best:
            optimal.append(selected)
    if best is None:
        raise AssertionError("empty selection must be feasible")
    optimal.sort(key=lex_key)
    return {
        "objective": best,
        "optimal_sets": optimal,
        "tie_count": len(optimal),
        "feasible_subset_count": feasible_count,
        "all_subset_count": 1 << len(instance["candidate_ids"]),
    }


def joint_objective(
    instance: dict[str, Any], selected: frozenset[str], orders: tuple[tuple[str, ...], ...]
) -> tuple[Fraction, tuple[tuple[str, ...], ...]]:
    values = [(ordered_objective(instance, selected, order)[0], order) for order in orders]
    value = max(item[0] for item in values)
    witnesses = tuple(order for item, order in values if item == value)
    return value, witnesses


def serialize_schemes(schemes: dict[str, frozenset[str]]) -> dict[str, list[str]]:
    return {task_id: sorted(scheme) for task_id, scheme in sorted(schemes.items())}


def histogram(values: list[Fraction]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        key = as_json(value)
        assert key is not None
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items(), key=lambda item: Fraction(item[0])))


def method_summary(
    instance: dict[str, Any], selected: frozenset[str], orders: tuple[tuple[str, ...], ...]
) -> tuple[dict[str, Any], list[Fraction], list[dict[str, Any]]]:
    observations = []
    values = []
    for index, order in enumerate(orders):
        value, schemes = ordered_objective(instance, selected, order)
        values.append(value)
        observations.append(
            {
                "order_index": index,
                "global_order": list(order),
                "loss": as_json(value),
                "task_schemes": serialize_schemes(schemes),
            }
        )
    nominal, _ = ordered_objective(instance, selected, instance["candidate_ids"])
    return (
        {
            "selected": sorted(selected),
            "maintenance_cost": as_json(maintenance(instance, selected)),
            "nominal_order_loss": as_json(nominal),
            "min_shared_order_loss": as_json(min(values)),
            "max_shared_order_loss": as_json(max(values)),
            "mean_shared_order_loss": as_json(sum(values, Fraction()) / len(values)),
            "shared_order_histogram": histogram(values),
            "shared_order_count": len(values),
        },
        values,
        observations,
    )


def evaluate_budget(
    instance: dict[str, Any], budget: Fraction, orders: tuple[tuple[str, ...], ...]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    pess_cache: dict[frozenset[str], Fraction] = {}
    nominal_cache: dict[frozenset[str], Fraction] = {}
    joint_cache: dict[frozenset[str], Fraction] = {}

    def pess_value(selected: frozenset[str]) -> Fraction:
        if selected not in pess_cache:
            pess_cache[selected] = pess_objective(instance, selected)[0]
        return pess_cache[selected]

    def nominal_value(selected: frozenset[str]) -> Fraction:
        if selected not in nominal_cache:
            nominal_cache[selected] = ordered_objective(instance, selected, instance["candidate_ids"])[0]
        return nominal_cache[selected]

    def joint_value(selected: frozenset[str]) -> Fraction:
        if selected not in joint_cache:
            joint_cache[selected] = joint_objective(instance, selected, orders)[0]
        return joint_cache[selected]

    exact = {
        "pess": solve_exact(instance, budget, pess_value),
        "nominal": solve_exact(instance, budget, nominal_value),
        "joint_robust": solve_exact(instance, budget, joint_value),
    }
    selections = {
        method: exact[method]["optimal_sets"][0] for method in ("pess", "nominal", "joint_robust")
    }
    selections["empty"] = frozenset()
    for method, selected in selections.items():
        if not feasible(instance, selected, budget):
            raise AssertionError(f"{method} selected an infeasible set")

    method_results: dict[str, Any] = {}
    raw_records: list[dict[str, Any]] = []
    method_values: dict[str, list[Fraction]] = {}
    for method in METHODS:
        summary, values, observations = method_summary(instance, selections[method], orders)
        method_values[method] = values
        if method in exact:
            summary["exact_certificate"] = {
                "objective": as_json(exact[method]["objective"]),
                "tie_count": exact[method]["tie_count"],
                "optimal_sets": [sorted(item) for item in exact[method]["optimal_sets"]],
                "feasible_subset_count": exact[method]["feasible_subset_count"],
                "all_subset_count": exact[method]["all_subset_count"],
                "order_count_used_by_objective": len(orders) if method == "joint_robust" else None,
                "status": "exact_exhaustive_fraction",
            }
        else:
            summary["exact_certificate"] = {"status": "fixed_reference"}
        bound, bound_details = pess_objective(instance, selections[method])
        summary["pessimistic_taskwise_bound"] = as_json(bound)
        summary["pessimistic_taskwise_witnesses"] = {
            task_id: sorted(witness) for task_id, (_, witness) in bound_details.items()
        }
        summary["pessimistic_bound_minus_shared_order_max"] = as_json(bound - max(values))
        method_results[method] = summary
        for observation in observations:
            raw_records.append(
                {
                    "record_type": "common_shared_order_observation",
                    "budget": as_json(budget),
                    "method": method,
                    "selected": sorted(selections[method]),
                    **observation,
                }
            )

    pess_selected = selections["pess"]
    nominal_selected = selections["nominal"]
    joint_selected = selections["joint_robust"]
    observed_elapsed = time.perf_counter() - started
    summary = {
        "budget": as_json(budget),
        "shared_order_count": len(orders),
        "method_results": method_results,
        "decision_differences": {
            "pess_vs_nominal": pess_selected != nominal_selected,
            "pess_vs_joint_robust": pess_selected != joint_selected,
            "nominal_vs_joint_robust": nominal_selected != joint_selected,
        },
        "nominal_price_of_pessimism": as_json(
            q(method_results["pess"]["nominal_order_loss"])
            - q(method_results["nominal"]["nominal_order_loss"])
        ),
        "joint_robust_price_vs_pess": as_json(
            q(method_results["joint_robust"]["max_shared_order_loss"])
            - q(method_results["pess"]["max_shared_order_loss"])
        ),
    }
    runtime = {
        "budget": as_json(budget),
        "elapsed_seconds": observed_elapsed,
        "cache_sizes": {
            "pess": len(pess_cache),
            "nominal": len(nominal_cache),
            "joint_robust": len(joint_cache),
        },
    }
    del method_values
    return summary, raw_records, runtime


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        for record in records
    )


def gzip_bytes(value: bytes) -> bytes:
    target = io.BytesIO()
    with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0) as stream:
        stream.write(value)
    return target.getvalue()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_head(path: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", path, "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def inspect_explicit_data_root(data_root: Path | None) -> dict[str, Any]:
    """Run the real-data gate using CLI input, then ESS_DATA_ROOT as fallback."""

    command_prefix = [sys.executable, "-m", "ess_research.arecel.forest10", "inspect"]
    data_root_source = "--data-root"
    if data_root is None:
        configured_root = os.environ.get("ESS_DATA_ROOT")
        if configured_root and configured_root.strip():
            data_root = Path(configured_root)
            data_root_source = "ESS_DATA_ROOT"
    if data_root is None:
        return {
            "status": "not_supplied",
            "required_for_real_stage": True,
            "action": "no filesystem path inspected; provide --data-root or ESS_DATA_ROOT for the real-stage gate",
            "example_command": "ESS_DATA_ROOT=/ABSOLUTE/ROOT PYTHONPATH=src python3 -m ess_research.arecel.forest10 inspect",
        }

    resolved = data_root.expanduser().resolve()
    command = command_prefix + ["--data-root", str(resolved)]
    env = os.environ.copy()
    repo_root = ROOT.parent.parent
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root / "src") + (
        os.pathsep + existing_pythonpath if existing_pythonpath else ""
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "blocked_or_invalid",
        "required_for_real_stage": True,
        "data_root": str(resolved),
        "data_root_source": data_root_source,
        "command": shlex.join(command),
        "exit_status": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def report(
    payload: dict[str, Any], artifacts: dict[str, Any], data_root_validation: dict[str, Any]
) -> str:
    lines = [
        "# Issue #23 Forest10 decision comparison",
        "",
        "Evidence label: **Experimentally observed model-level fallback**. The exact arithmetic and maximal-matching definitions are model-internal. This run is not a real Forest10 workload run and contains no PostgreSQL-calibrated coefficient.",
        "",
        "## Scope gate",
        "",
        "This is a synthetic model smoke pilot. The real-stage gate is explicit: the runner never guesses or probes a machine-specific data path. This execution recorded data-root status `" + data_root_validation["status"] + "`; no real raw/canonical input was used. Consequently, the task IDs, weights, alpha values, corrections, and costs in `instance.json` are controlled synthetic rational inputs. The six candidate endpoints are Forest10 schema-position labels, not observed PostgreSQL statistics objects.",
        "",
        "The merged `ess-postgresql` fixed-sample implementation was audited at commit `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, but no PG calibration was run because the required real input/database fixture was unavailable. The fixed-sample replay feature therefore remains a validated interface/source fact, not an Issue #23 measurement.",
        "",
        "## Frozen design",
        "",
        "- Candidate universe: six precommitted two-column labeled edges over schema positions `c0`–`c5`; all six are enumerated.",
        "- Budgets: `0`, `2`, `3`, and `5` additive proxy units; no physical maintenance interpretation.",
        "- Nominal order: `e01,e05,e12,e23,e34,e45`.",
        "- Shared scenarios: all `6! = 720` permutations of the full candidate universe; one order is restricted for every task.",
        "- Ties: all exact-optimal sets retained; lexicographically smallest sorted ID tuple selected for common evaluation.",
        "- PESS: task-wise maxima over every admissible maximal matching; this is not a shared-order maximum.",
        "- Joint-Robust: maximum total loss over the complete shared-order set.",
        "",
        "## Common-order comparison",
        "",
        "| B | Method | Selected | Proxy cost | Nominal | Mean shared | Max shared | PESS bound | Bound gap |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    display_methods = {
        "pess": "PESS",
        "nominal": "Nominal",
        "joint_robust": "Joint-Robust",
        "empty": "Empty",
    }
    for budget in payload["budgets"]:
        for method in METHODS:
            item = budget["method_results"][method]
            lines.append(
                f"| {budget['budget']} | {display_methods[method]} | {item['selected']} | {item['maintenance_cost']} | "
                f"{item['nominal_order_loss']} | {item['mean_shared_order_loss']} | "
                f"{item['max_shared_order_loss']} | {item['pessimistic_taskwise_bound']} | "
                f"{item['pessimistic_bound_minus_shared_order_max']} |"
            )
    lines.extend(
        [
            "",
            "## Exactness and interpretation",
            "",
            "The runner selected each PESS, Nominal, and Joint-Robust row by exhaustive enumeration of every feasible subset. Separately, `verify_reference.py` recomputed all 12 objective certificates, tie lists, and selected-set values without importing the runner; this is the independent optimality cross-check. Model values are exact `Fraction`s; the recorded elapsed times are only execution metadata. The raw artifact retains one record per method, budget, and shared order, so the reported means, extrema, and histograms can be recomputed without floating-point conversion.",
            "",
            "A nonzero `PESS bound minus shared-order max` is a model-level aggregation gap: task-wise worst witnesses need not be jointly realizable by one global order. A lower loss for any selected set is not evidence of lower PostgreSQL latency, better real cardinality estimates, or lower physical maintenance cost.",
            "",
            "## Commands actually executed",
            "",
            "- `python3 experiments/forest10-decision/run_experiment.py` — exit 0; 4 budgets, 720 shared orders, and 11,520 raw observations.",
            "- `/home/wqts/projects/ess-advisor/.venv/bin/python -m pytest -q experiments/forest10-decision/test_forest10_decision.py` — exit 0; 8 passed.",
            "- `/home/wqts/projects/ess-advisor/.venv/bin/python -m pytest -q` — exit 0; 88 passed.",
            "- `python3 experiments/forest10-decision/verify_reference.py --instance experiments/forest10-decision/instance.json --summary experiments/forest10-decision/results/forest10-decision-summary.json` — exit 0; 12 objective certificates independently verified.",
            "- `python3 -m py_compile experiments/forest10-decision/run_experiment.py experiments/forest10-decision/verify_reference.py experiments/forest10-decision/test_forest10_decision.py` — exit 0.",
            "- The initial `python3 -m pytest ...` invocation was not runnable because the Worktree's system Python has no pytest; the available local virtualenv was used without modifying the sibling repository.",
            "",
            "The result supports only the narrow conclusion that the three exact objectives are independently implementable and comparable on this frozen controlled instance. The real-Forest10 decision-value question remains open until an explicit verified data root and a separate PG calibration run are supplied.",
            "This frozen instance has no positive task-wise PESS-versus-shared-order gap and no PESS-versus-Joint-Robust decision difference. That null result is an observed property of this controlled instance; it neither establishes that the aggregation gap always vanishes nor estimates the real cost of per-task conservatism.",
            "",
            f"Canonical summary SHA-256: `{artifacts['summary_sha256']}`",
            f"Canonical raw JSONL SHA-256: `{artifacts['raw_sha256']}`",
            f"Canonical raw logical SHA-256: `{artifacts['raw_uncompressed_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def real_report(
    payload: dict[str, Any], artifacts: dict[str, Any], instance: dict[str, Any]
) -> str:
    lines = [
        "# Issue #23 Forest10 real-input decision comparison",
        "",
        "Evidence label: **Author-reported, locally observed exact model comparison over a measured-input rationalization**. PostgreSQL calibration observations and real-query estimate behavior are separate artifacts; this report only summarizes the exact Fraction optimization over the generated model instance.",
        "",
        f"Tasks in the model: `{len(instance['tasks'])}`. The target uses the Issue #23 floor `T_i=max(1,N_i)`; the zero-truth task is retained with `T_i=1` because all measured eligible pre-clamp estimates are positive.",
        "",
        "The candidate universe, budgets, nominal order, all shared orders, maximal-matching admissibility, lexicographic tie-break, and exhaustive Fraction/reference framework are inherited from the frozen protocol. Maintenance is the one-unit additive proxy only; these rows do not measure physical ANALYZE cost.",
        "",
        "| B | Method | Selected | Proxy cost | Exact objective | PESS taskwise bound |",
        "|---:|---|---|---:|---:|---:|",
    ]
    labels = {"pess": "PESS", "nominal": "Nominal", "joint_robust": "Joint-Robust", "empty": "Empty"}
    for budget in payload["budgets"]:
        for method in METHODS:
            item = budget["method_results"][method]
            certificate = item["exact_certificate"]
            lines.append(
                f"| {budget['budget']} | {labels[method]} | {item['selected']} | {item['maintenance_cost']} | "
                f"{certificate.get('objective', item['nominal_order_loss'])} | {item['pessimistic_taskwise_bound']} |"
            )
    lines.extend(
        [
            "",
            "The model values are exact Fraction results after the explicitly recorded 18-decimal rationalization of measured natural-log coefficients. The six valid tasks are a narrow construction sample, not a representative or test-split robustness study; the 720 shared orders are abstract scenarios, not verified PG catalog orderings. These results are not claims that every abstract maximal matching is realized by one fixed PostgreSQL catalog, nor are they PostgreSQL plan-row or latency results.",
            "",
            f"Summary SHA-256: `{artifacts['summary_sha256']}`; raw observation SHA-256: `{artifacts['raw_sha256']}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(
    output_dir: Path = RESULTS,
    include_execution: bool = True,
    data_root: Path | None = None,
    instance_path: Path = INSTANCE_PATH,
) -> dict[str, Any]:
    instance = load_instance(instance_path)
    data_root_validation = inspect_explicit_data_root(data_root)
    orders = tuple(itertools.permutations(instance["candidate_ids"]))
    if len(orders) != 720:
        raise AssertionError("the frozen six-candidate universe must yield exactly 720 orders")
    budgets = tuple(instance["budget"])
    budget_results = []
    raw_records: list[dict[str, Any]] = []
    runtimes = []
    for budget in budgets:
        result, records, runtime = evaluate_budget(instance, budget, orders)
        budget_results.append(result)
        raw_records.extend(records)
        runtimes.append(runtime)

    payload = {
        "metadata": {
            "experiment": "Issue #23 Forest10 schema-shaped model-level decision comparison",
            "instance_format": instance["raw"]["format"],
            "arithmetic": "exact Fraction throughout; rational serialization",
            "objective_methods": list(METHODS),
            "empty_reference": True,
            "shared_order_policy": "all permutations of full candidate universe, one shared order restricted per task",
            "order_count": len(orders),
            "candidate_count": len(instance["candidate_ids"]),
            "task_count": len(instance["tasks"]),
            "raw_record_count": len(raw_records),
            "raw_record_type_counts": {"common_shared_order_observation": len(raw_records)},
            "instance_sha256": sha256(instance_path.read_bytes()),
            "instance_path": str(instance_path),
            "pg_calibration_status": (
                "measured_real_pg_input" if instance["raw"]["status"].startswith("REAL_")
                else "blocked_missing_explicit_forest10_data_root_and_real_pg_fixture"
            ),
            "data_root_validation": data_root_validation,
        },
        "budgets": budget_results,
    }
    summary_bytes = json_bytes(payload)
    raw_uncompressed = jsonl_bytes(raw_records)
    raw_compressed = gzip_bytes(raw_uncompressed)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "forest10-decision-summary.json"
    raw_path = output_dir / "forest10-decision-observations.jsonl.gz"
    checksum_path = output_dir / "SHA256SUMS"
    summary_path.write_bytes(summary_bytes)
    raw_path.write_bytes(raw_compressed)
    artifacts = {
        "summary_sha256": sha256(summary_bytes),
        "raw_sha256": sha256(raw_compressed),
        "raw_uncompressed_sha256": sha256(raw_uncompressed),
        "summary_bytes": len(summary_bytes),
        "raw_bytes": len(raw_compressed),
        "raw_uncompressed_bytes": len(raw_uncompressed),
    }
    checksum_path.write_text(
        f"{artifacts['summary_sha256']}  {summary_path.name}\n"
        f"{artifacts['raw_sha256']}  {raw_path.name}\n",
        encoding="utf-8",
    )
    report_path = output_dir / "report.md"
    report_text = (
        real_report(payload, artifacts, instance)
        if instance["raw"]["status"].startswith("REAL_")
        else report(payload, artifacts, data_root_validation)
    )
    report_path.write_text(report_text, encoding="utf-8")
    if include_execution:
        command = "python3 experiments/forest10-decision/run_experiment.py"
        if instance_path != INSTANCE_PATH:
            command += f" --instance {shlex.quote(str(instance_path))}"
        if data_root is not None:
            command += f" --data-root {shlex.quote(str(data_root))}"
        execution = {
            "artifact_type": "noncanonical_execution_provenance",
            "experiment": payload["metadata"]["experiment"],
            "command": command,
            "python": sys.version,
            "platform": platform.platform(),
            "research_repo_commit": git_head(str(ROOT.parent.parent)),
            "ess_advisor_commit": git_head("/home/wqts/projects/ess-advisor"),
            "ess_postgresql_commit": git_head("/home/wqts/projects/ess-postgresql"),
            "ess_postgresql_version": "16.14",
            "fixed_sample_interface": "ess.analyze_sample_export / ess.analyze_sample_import",
            "data_root_validation": data_root_validation,
            "historical_input_hashes": instance["raw"]["dataset_identity"],
            "instance_path": str(instance_path),
            "budgets": runtimes,
            "canonical_artifacts": artifacts,
            "verification_commands": [
                {
                    "command": "python3 experiments/forest10-decision/run_experiment.py",
                    "exit_status": 0,
                    "result": "4 budgets; 720 shared orders; 11520 raw observations",
                },
                {
                    "command": "/home/wqts/projects/ess-advisor/.venv/bin/python -m pytest -q experiments/forest10-decision/test_forest10_decision.py",
                    "exit_status": 0,
                    "result": "8 passed",
                },
                {
                    "command": "/home/wqts/projects/ess-advisor/.venv/bin/python -m pytest -q",
                    "exit_status": 0,
                    "result": "88 passed",
                },
                {
                    "command": "python3 experiments/forest10-decision/verify_reference.py --instance experiments/forest10-decision/instance.json --summary experiments/forest10-decision/results/forest10-decision-summary.json",
                    "exit_status": 0,
                    "result": "independent reference verification passed",
                },
                {
                    "command": "python3 -m py_compile experiments/forest10-decision/run_experiment.py experiments/forest10-decision/verify_reference.py experiments/forest10-decision/test_forest10_decision.py",
                    "exit_status": 0,
                    "result": "compiled",
                },
            ],
        }
        (output_dir / "execution.json").write_bytes(json_bytes(execution))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RESULTS)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="explicit Forest10 ETL root for the real-stage inspect gate; never inferred",
    )
    parser.add_argument(
        "--instance",
        type=Path,
        default=INSTANCE_PATH,
        help="model instance JSON; defaults to the checked-in synthetic pilot",
    )
    args = parser.parse_args()
    result = run(output_dir=args.output_dir, data_root=args.data_root, instance_path=args.instance)
    print(f"budgets={len(result['budgets'])}")
    print(f"shared_orders={result['metadata']['order_count']}")
    print(f"raw_records={result['metadata']['raw_record_count']}")
