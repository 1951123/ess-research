"""Run the self-contained model-level Issue #14 decision study.

The implementation intentionally uses only the Python standard library.  All
model inputs and reported objective values are exact Fractions; this is an
exhaustive reference experiment, not a floating-point MILP claim.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INSTANCE_DIR = ROOT / "instances"
RESULT_PATH = ROOT / "results" / "decision-value-results.json"
REPORT_PATH = ROOT / "report.md"

FIXTURES = (
    ("hand_mixed_hurts", ("0", "2", "4"), "hand-constructed mixed-sign stress case"),
    ("hand_mixed_coincides", ("0", "2", "5"), "hand-constructed mixed-sign neutral case"),
    ("positive_sign", ("0", "2", "4"), "hand-constructed nonnegative-sign case"),
    ("negative_sign", ("0", "2", "4"), "hand-constructed nonpositive-sign case"),
)
METHODS = ("pessimistic", "nominal", "greedy_nominal", "empty")


def q(value: Any) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(str(value))


def as_json(value: Fraction | None) -> str | None:
    if value is None:
        return None
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def load_instance(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    candidates = {item["id"]: item for item in raw["candidates"]}
    tasks = []
    for item in raw["tasks"]:
        tasks.append(
            {
                "id": item["id"],
                "weight": q(item["weight"]),
                "alpha": q(item["alpha"]),
                "eligible": tuple(sorted(item["eligible_candidates"])),
                "corrections": {key: q(value) for key, value in item["corrections"].items()},
            }
        )
    return {
        "budget": q(raw["budget"]),
        "candidates": candidates,
        "candidate_ids": tuple(sorted(candidates)),
        "cost": {key: q(item["maintenance_cost"]) for key, item in candidates.items()},
        "endpoints": {key: tuple(item["endpoints"]) for key, item in candidates.items()},
        "tasks": tuple(sorted(tasks, key=lambda item: item["id"])),
    }


def subsets(ids: tuple[str, ...]):
    for mask in range(1 << len(ids)):
        yield frozenset(ids[index] for index in range(len(ids)) if mask & (1 << index))


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
        edge_vertices = frozenset(endpoints[edge])
        if not occupied & edge_vertices:
            visit(index + 1, chosen + (edge,), occupied | edge_vertices)

    visit(0, (), frozenset())
    return tuple(sorted(result, key=lambda item: tuple(sorted(item))))


def maximal_matching_sets(selected: frozenset[str], endpoints: dict[str, tuple[str, str]]) -> tuple[frozenset[str], ...]:
    result = []
    for matching in matching_sets(selected, endpoints):
        occupied = {vertex for edge in matching for vertex in endpoints[edge]}
        if all(occupied & set(endpoints[edge]) for edge in selected - matching):
            result.append(matching)
    if not result:
        raise AssertionError("a finite selected graph must have a maximal matching")
    return tuple(result)


def loss(task: dict[str, Any], matching: frozenset[str] | tuple[str, ...]) -> Fraction:
    return abs(task["alpha"] + sum((task["corrections"][edge] for edge in matching), Fraction()))


def task_worst(instance: dict[str, Any], task: dict[str, Any], selected: frozenset[str]) -> tuple[Fraction, frozenset[str]]:
    active = frozenset(task["eligible"]) & selected
    choices = [(loss(task, matching), matching) for matching in maximal_matching_sets(active, instance["endpoints"])]
    value = max(item[0] for item in choices)
    witness = min((matching for item, matching in choices if item == value), key=lambda item: tuple(sorted(item)))
    return value, witness


def robust_objective(instance: dict[str, Any], selected: frozenset[str]) -> tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]:
    details = {task["id"]: task_worst(instance, task, selected) for task in instance["tasks"]}
    value = sum((task["weight"] * details[task["id"]][0] for task in instance["tasks"]), Fraction())
    return value, details


def greedy_scheme(instance: dict[str, Any], task: dict[str, Any], selected: frozenset[str], order: tuple[str, ...]) -> frozenset[str]:
    active = frozenset(task["eligible"]) & selected
    occupied: set[str] = set()
    chosen: list[str] = []
    for edge in order:
        if edge not in active:
            continue
        endpoints = set(instance["endpoints"][edge])
        if not occupied & endpoints:
            chosen.append(edge)
            occupied.update(endpoints)
    scheme = frozenset(chosen)
    if scheme not in maximal_matching_sets(active, instance["endpoints"]):
        raise AssertionError("global-order selector did not produce a maximal matching")
    return scheme


def ordered_objective(instance: dict[str, Any], selected: frozenset[str], order: tuple[str, ...]) -> tuple[Fraction, dict[str, frozenset[str]]]:
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


def choose_best(instance: dict[str, Any], budget: Fraction, evaluator) -> tuple[frozenset[str], Fraction, int]:
    candidates = []
    for selected in subsets(instance["candidate_ids"]):
        if feasible(instance, selected, budget):
            candidates.append((evaluator(selected), lex_key(selected), selected))
    if not candidates:
        raise AssertionError("empty set must be feasible")
    value, _, selected = min(candidates, key=lambda item: (item[0], item[1]))
    return selected, value, len(candidates)


def greedy_nominal(instance: dict[str, Any], budget: Fraction, order: tuple[str, ...]) -> frozenset[str]:
    selected = frozenset()
    while True:
        current, _ = ordered_objective(instance, selected, order)
        options = []
        for edge in instance["candidate_ids"]:
            if edge in selected:
                continue
            proposal = selected | {edge}
            if not feasible(instance, proposal, budget):
                continue
            proposed, _ = ordered_objective(instance, proposal, order)
            benefit = current - proposed
            if benefit <= 0:
                continue
            cost = instance["cost"][edge]
            ratio = None if cost == 0 else benefit / cost
            options.append((ratio, benefit, cost, edge, proposal))
        if not options:
            return selected
        options.sort(
            key=lambda item: (
                item[0] is not None,
                -(item[0] if item[0] is not None else Fraction()),
                -item[1],
                item[2],
                item[3],
            )
        )
        selected = options[0][4]


def serialize_schemes(schemes: dict[str, frozenset[str]]) -> dict[str, list[str]]:
    return {task_id: sorted(scheme) for task_id, scheme in sorted(schemes.items())}


def evaluate_fixture(name: str, budget_texts: tuple[str, ...], description: str, path: Path) -> dict[str, Any]:
    instance = load_instance(path)
    theta0 = instance["candidate_ids"]
    orders = tuple(itertools.permutations(instance["candidate_ids"]))
    budgets = tuple(q(item) for item in budget_texts)
    budget_results = []

    for budget in budgets:
        feasible_sets = tuple(selected for selected in subsets(instance["candidate_ids"]) if feasible(instance, selected, budget))
        started = time.perf_counter()
        pess_selected, pess_bound, evaluated = choose_best(instance, budget, lambda selected: robust_objective(instance, selected)[0])
        pess_runtime = time.perf_counter() - started
        started = time.perf_counter()
        nominal_selected, nominal_loss, _ = choose_best(instance, budget, lambda selected: ordered_objective(instance, selected, theta0)[0])
        nominal_runtime = time.perf_counter() - started
        started = time.perf_counter()
        greedy_selected = greedy_nominal(instance, budget, theta0)
        greedy_runtime = time.perf_counter() - started
        selections = {
            "pessimistic": pess_selected,
            "nominal": nominal_selected,
            "greedy_nominal": greedy_selected,
            "empty": frozenset(),
        }
        for method, selected in selections.items():
            if not feasible(instance, selected, budget):
                raise AssertionError(f"{method} selected an infeasible set")

        scenario_observations = []
        method_losses = {method: [] for method in METHODS}
        method_regrets = {method: [] for method in METHODS}
        for order_index, order in enumerate(orders):
            scenario_optimal, scenario_value, _ = choose_best(
                instance,
                budget,
                lambda selected, order=order: ordered_objective(instance, selected, order)[0],
            )
            methods_for_order = []
            for method in METHODS:
                selected = selections[method]
                value, schemes = ordered_objective(instance, selected, order)
                regret = value - scenario_value
                method_losses[method].append(value)
                method_regrets[method].append(regret)
                methods_for_order.append(
                    {
                        "method": method,
                        "selected": sorted(selected),
                        "maintenance_cost": as_json(maintenance(instance, selected)),
                        "loss": as_json(value),
                        "scenario_regret": as_json(regret),
                        "task_schemes": serialize_schemes(schemes),
                    }
                )
            scenario_observations.append(
                {
                    "order_index": order_index,
                    "global_order": list(order),
                    "scenario_optimum": {"selected": sorted(scenario_optimal), "loss": as_json(scenario_value)},
                    "methods": methods_for_order,
                }
            )

        method_summary = {}
        for method in METHODS:
            losses = method_losses[method]
            method_summary[method] = {
                "selected": sorted(selections[method]),
                "maintenance_cost": as_json(maintenance(instance, selections[method])),
                "nominal_order_loss": as_json(ordered_objective(instance, selections[method], theta0)[0]),
                "tested_order_count": len(losses),
                "min_tested_loss": as_json(min(losses)),
                "max_tested_loss": as_json(max(losses)),
                "mean_tested_loss": as_json(sum(losses, Fraction()) / len(losses)),
                "max_scenario_regret": as_json(max(method_regrets[method])),
                "all_scenario_regrets_nonnegative": all(value >= 0 for value in method_regrets[method]),
            }
        method_summary["pessimistic"].update(
            {"solver_status": "exact_exhaustive", "optimizer_runtime_seconds": pess_runtime, "feasible_sets_evaluated": evaluated}
        )
        method_summary["nominal"].update(
            {"solver_status": "exact_exhaustive", "optimizer_runtime_seconds": nominal_runtime, "feasible_sets_evaluated": evaluated}
        )
        method_summary["greedy_nominal"].update(
            {"solver_status": "deterministic_complete", "optimizer_runtime_seconds": greedy_runtime}
        )
        method_summary["empty"].update(
            {"solver_status": "fixed", "optimizer_runtime_seconds": 0.0}
        )

        empty_max = max(method_losses["empty"])
        pess_max = max(method_losses["pessimistic"])
        nominal_max = max(method_losses["nominal"])
        greedy_max = max(method_losses["greedy_nominal"])
        nominal_at_theta0 = ordered_objective(instance, nominal_selected, theta0)[0]
        pess_at_theta0 = ordered_objective(instance, pess_selected, theta0)[0]
        gap = pess_bound - pess_max
        if gap < 0:
            raise AssertionError("task-wise PESS bound must dominate every tested shared order")
        budget_results.append(
            {
                "budget": as_json(budget),
                "feasible_set_count": len(feasible_sets),
                "exhaustive_subset_evaluations": 1 << len(instance["candidate_ids"]),
                "pessimistic_bound": as_json(pess_bound),
                "pessimistic_bound_witnesses": {
                    task_id: sorted(witness) for task_id, (_, witness) in robust_objective(instance, pess_selected)[1].items()
                },
                "method_summary": method_summary,
                "nominal_price_of_pessimism": as_json(pess_at_theta0 - nominal_at_theta0),
                "independent_vs_joint_conservatism_gap": as_json(gap),
                "worst_tested_delta_vs_nominal": {
                    "pessimistic_benefit": as_json(nominal_max - pess_max),
                    "greedy_benefit": as_json(nominal_max - greedy_max),
                },
                "relative_worst_tested_improvement_vs_empty": {
                    method: as_json((empty_max - max(method_losses[method])) / empty_max) if empty_max else None
                    for method in METHODS
                },
                "pessimistic_equals_nominal": pess_selected == nominal_selected,
                "scenario_observations": scenario_observations,
            }
        )

    return {
        "instance_id": name,
        "description": description,
        "instance_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "candidate_ids": list(instance["candidate_ids"]),
        "candidate_count": len(instance["candidate_ids"]),
        "task_count": len(instance["tasks"]),
        "global_order_coverage": "exact: all permutations of the full candidate universe; one shared order per scenario",
        "global_order_count": len(orders),
        "budgets": list(budget_results),
    }


def report(payload: dict[str, Any]) -> str:
    lines = [
        "# Issue #14 model-level decision value study",
        "",
        "Evidence label: **Experimentally observed** for the executed fixed JSON matrix below; the mathematical definitions and exact Fraction computations are model-internal. This study does not use PostgreSQL or real data.",
        "",
        f"- Python: `{payload['metadata']['python'].splitlines()[0]}`",
        f"- Platform: `{payload['metadata']['platform']}`",
        "- Arithmetic: exact `Fraction` inputs and objective calculations; no MILP solver was used.",
        "- Policy scenarios: exact enumeration of every permutation of the full candidate universe, with one shared order restricted to every task.",
        "- Nominal order: sorted candidate IDs.",
        "- Maintenance: additive proxy from the instance JSON; no claim about generic nonadditive `Maint(M)` or physical ANALYZE cost.",
        "",
        "## Method definitions",
        "",
        "`pessimistic` minimizes the exact task-wise maximal-matching objective. `nominal` minimizes the exact loss under the sorted-ID order. `greedy_nominal` starts from the empty set and repeatedly chooses the feasible positive nominal marginal-benefit-per-cost candidate; zero-cost positive gains have infinite ratio, and nonpositive gains are rejected. `empty` always selects the empty set. Ties are resolved lexicographically by candidate IDs.",
        "",
        "## Budget-level results",
        "",
        "| Fixture | B | PESS set | Nominal set | Greedy set | Empty max | PESS max | Nominal max | Greedy max | PESS max regret | Nominal price | PESS bound gap |",
        "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for fixture in payload["fixtures"]:
        for budget in fixture["budgets"]:
            summary = budget["method_summary"]
            lines.append(
                f"| {fixture['instance_id']} | {budget['budget']} | "
                f"{summary['pessimistic']['selected']} | {summary['nominal']['selected']} | "
                f"{summary['greedy_nominal']['selected']} | {summary['empty']['max_tested_loss']} | "
                f"{summary['pessimistic']['max_tested_loss']} | {summary['nominal']['max_tested_loss']} | "
                f"{summary['greedy_nominal']['max_tested_loss']} | {summary['pessimistic']['max_scenario_regret']} | "
                f"{budget['nominal_price_of_pessimism']} | {budget['independent_vs_joint_conservatism_gap']} |"
            )
    lines.extend(
        [
            "",
            "## Controlled outcome counts",
            "",
            "The matrix has one row per fixture/budget. A nontrivial decision difference means the PESS and nominal selected sets differ. A large conservatism gap is predefined as at least 1 exact loss unit.",
            "",
            "| Quantity | Count | Denominator |",
            "|---|---:|---:|",
        ]
    )
    rows = []
    for fixture in payload["fixtures"]:
        rows.extend(fixture["budgets"])
    lines.extend(
        [
            f"| PESS and nominal sets coincide | {sum(row['pessimistic_equals_nominal'] for row in rows)} | {len(rows)} |",
            f"| PESS and nominal sets differ | {sum(not row['pessimistic_equals_nominal'] for row in rows)} | {len(rows)} |",
            f"| Empty set selected by PESS | {sum(not row['method_summary']['pessimistic']['selected'] for row in rows)} | {len(rows)} |",
            f"| PESS improves worst tested loss vs empty | {sum(Fraction(row['method_summary']['empty']['max_tested_loss']) > Fraction(row['method_summary']['pessimistic']['max_tested_loss']) for row in rows)} | {len(rows)} |",
            f"| Conservatism gap at least 1 | {sum(Fraction(row['independent_vs_joint_conservatism_gap']) >= 1 for row in rows)} | {len(rows)} |",
            "",
            "## Interpretation and limits",
            "",
            "The raw JSON preserves each shared-order observation, selected set, task scheme, tested loss, and scenario regret. Scenario regret is certified here because the comparator is exhaustively solved for each tested order and budget. The PESS bound is the independent task-wise maximum over all maximal matchings; it is not asserted to be achievable by one shared policy. The observed gap therefore measures conservatism of this model-level aggregation over the enumerated shared orders.",
            "",
            "The hand cases intentionally include a PESS/nominal decision difference, a coincidence case, positive-sign and negative-sign controls, and multiple budgets. They are stress cases, not PostgreSQL-calibrated measurements. In particular, a lower modeled loss is not evidence of query-latency benefit, real PostgreSQL policy coverage, or physical maintenance-cost additivity. The next validation step is independent review of the instance matrix and, only if warranted, a separately scoped coupling to already recorded PostgreSQL snapshots.",
            "",
        ]
    )
    return "\n".join(lines)


def run() -> dict[str, Any]:
    fixtures = []
    for name, budgets, description in FIXTURES:
        fixtures.append(evaluate_fixture(name, budgets, description, INSTANCE_DIR / f"{name}.json"))
    payload = {
        "metadata": {
            "experiment": "Issue #14 decision value and price of pessimism",
            "python": sys.version,
            "platform": platform.platform(),
            "arithmetic": "exact Fraction throughout; serialized rational values",
            "execution_command": "python3 experiments/decision-value/run_experiment.py",
            "external_dependencies": "none; standard library only",
            "model_scope": "pairwise labeled-edge maximal-matching instantiation with additive maintenance proxy",
            "policy_scope": "all globally consistent candidate permutations, one shared order per scenario",
            "nominal_order": "lexicographically sorted candidate IDs",
            "tie_break": "lexicographically smallest sorted selected-set tuple",
            "large_conservatism_gap_threshold": "1",
            "pessimism_definition": "sum of task-wise maxima over all maximal matchings; not a shared-policy global maximum",
            "fixture_count": len(fixtures),
        },
        "fixtures": fixtures,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(report(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(f"wrote {RESULT_PATH}")
    print(f"wrote {REPORT_PATH}")
    print(f"fixtures={len(result['fixtures'])}")
