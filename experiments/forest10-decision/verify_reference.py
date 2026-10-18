"""Independent exact reference check for the Issue #23 model pilot.

This module deliberately does not import ``run_experiment``.  It recomputes
the feasible subsets, maximal matchings, three objective values, optimal-set
ties, and selected-set evaluation from the JSON inputs and canonical summary.
It is a small audit oracle, not another optimizer implementation.
"""

from __future__ import annotations

import argparse
import itertools
import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable


def fraction(value: Any) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(str(value))


def load(path: Path) -> tuple[dict[str, Any], tuple[str, ...], tuple[dict[str, Any], ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    candidate_ids = tuple(sorted(item["id"] for item in raw["candidates"]))
    endpoints = {item["id"]: tuple(item["endpoints"]) for item in raw["candidates"]}
    tasks = []
    for item in raw["tasks"]:
        tasks.append(
            {
                "id": item["id"],
                "weight": fraction(item["weight"]),
                "alpha": fraction(item["alpha"]),
                "eligible": frozenset(item["eligible_candidates"]),
                "corrections": {
                    key: fraction(value) for key, value in item["corrections"].items()
                },
            }
        )
    return {
        "candidate_ids": candidate_ids,
        "nominal_order": tuple(raw["nominal_order"]),
        "budgets": tuple(fraction(value) for value in raw["budgets"]),
        "cost": {item["id"]: fraction(item["maintenance_cost"]) for item in raw["candidates"]},
        "endpoints": endpoints,
    }, candidate_ids, tuple(sorted(tasks, key=lambda item: item["id"]))


def selected_sets(candidate_ids: tuple[str, ...]):
    for size in range(len(candidate_ids) + 1):
        yield from (frozenset(items) for items in itertools.combinations(candidate_ids, size))


def all_matchings(active: frozenset[str], endpoints: dict[str, tuple[str, str]]) -> tuple[frozenset[str], ...]:
    ordered = tuple(sorted(active))
    result: list[frozenset[str]] = []

    def visit(index: int, chosen: frozenset[str], used: frozenset[str]) -> None:
        if index == len(ordered):
            result.append(chosen)
            return
        edge = ordered[index]
        visit(index + 1, chosen, used)
        vertices = frozenset(endpoints[edge])
        if not used.intersection(vertices):
            visit(index + 1, chosen.union({edge}), used.union(vertices))

    visit(0, frozenset(), frozenset())
    return tuple(result)


def maximal_matchings(
    active: frozenset[str], endpoints: dict[str, tuple[str, str]]
) -> tuple[frozenset[str], ...]:
    result = []
    for matching in all_matchings(active, endpoints):
        used = frozenset(vertex for edge in matching for vertex in endpoints[edge])
        if all(used.intersection(endpoints[edge]) for edge in active.difference(matching)):
            result.append(matching)
    return tuple(result)


def scheme_loss(task: dict[str, Any], scheme: frozenset[str]) -> Fraction:
    return abs(task["alpha"] + sum((task["corrections"][edge] for edge in scheme), Fraction()))


def task_worst(
    task: dict[str, Any], selected: frozenset[str], endpoints: dict[str, tuple[str, str]]
) -> Fraction:
    active = task["eligible"].intersection(selected)
    return max(scheme_loss(task, scheme) for scheme in maximal_matchings(active, endpoints))


def greedy_loss(
    task: dict[str, Any],
    selected: frozenset[str],
    order: tuple[str, ...],
    endpoints: dict[str, tuple[str, str]],
) -> Fraction:
    active = task["eligible"].intersection(selected)
    used: set[str] = set()
    chosen: list[str] = []
    for edge in order:
        if edge not in active:
            continue
        vertices = set(endpoints[edge])
        if not used.intersection(vertices):
            chosen.append(edge)
            used.update(vertices)
    return scheme_loss(task, frozenset(chosen))


def sum_loss(
    tasks: tuple[dict[str, Any], ...], selected: frozenset[str], evaluator: Callable[[dict[str, Any]], Fraction]
) -> Fraction:
    return sum((task["weight"] * evaluator(task) for task in tasks), Fraction())


def nominal_value(
    tasks: tuple[dict[str, Any], ...], selected: frozenset[str], order: tuple[str, ...], endpoints: dict[str, tuple[str, str]]
) -> Fraction:
    return sum_loss(tasks, selected, lambda task: greedy_loss(task, selected, order, endpoints))


def pess_value(
    tasks: tuple[dict[str, Any], ...], selected: frozenset[str], endpoints: dict[str, tuple[str, str]]
) -> Fraction:
    return sum_loss(tasks, selected, lambda task: task_worst(task, selected, endpoints))


def joint_value(
    tasks: tuple[dict[str, Any], ...], selected: frozenset[str], orders: tuple[tuple[str, ...], ...], endpoints: dict[str, tuple[str, str]]
) -> Fraction:
    return max(nominal_value(tasks, selected, order, endpoints) for order in orders)


def certify(
    candidate_ids: tuple[str, ...],
    budget: Fraction,
    costs: dict[str, Fraction],
    evaluator: Callable[[frozenset[str]], Fraction],
) -> dict[str, Any]:
    feasible = [
        selection
        for selection in selected_sets(candidate_ids)
        if sum((costs[item] for item in selection), Fraction()) <= budget
    ]
    values = {selection: evaluator(selection) for selection in feasible}
    best = min(values.values())
    optimal = sorted(
        (selection for selection, value in values.items() if value == best),
        key=lambda selection: tuple(sorted(selection)),
    )
    return {
        "objective": best,
        "optimal_sets": [sorted(selection) for selection in optimal],
        "tie_count": len(optimal),
        "feasible_subset_count": len(feasible),
        "all_subset_count": 1 << len(candidate_ids),
    }


def verify_summary(instance_path: Path, summary_path: Path) -> int:
    model, candidate_ids, tasks = load(instance_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    orders = tuple(itertools.permutations(candidate_ids))
    methods = {
        "pess": lambda selection: pess_value(tasks, selection, model["endpoints"]),
        "nominal": lambda selection: nominal_value(
            tasks, selection, model["nominal_order"], model["endpoints"]
        ),
        "joint_robust": lambda selection: joint_value(
            tasks, selection, orders, model["endpoints"]
        ),
    }
    checked = 0
    for budget_item, budget in zip(summary["budgets"], model["budgets"]):
        if fraction(budget_item["budget"]) != budget:
            raise AssertionError("summary budget order/value differs from instance")
        for method, evaluator in methods.items():
            expected = certify(candidate_ids, budget, model["cost"], evaluator)
            actual = budget_item["method_results"][method]
            certificate = actual["exact_certificate"]
            if fraction(certificate["objective"]) != expected["objective"]:
                raise AssertionError(f"{method} objective mismatch at budget {budget}")
            if certificate["optimal_sets"] != expected["optimal_sets"]:
                raise AssertionError(f"{method} optimal-set certificate mismatch at budget {budget}")
            if certificate["tie_count"] != expected["tie_count"]:
                raise AssertionError(f"{method} tie count mismatch at budget {budget}")
            if certificate["feasible_subset_count"] != expected["feasible_subset_count"]:
                raise AssertionError(f"{method} feasible-subset count mismatch at budget {budget}")
            selected = frozenset(actual["selected"])
            if actual["selected"] != expected["optimal_sets"][0]:
                raise AssertionError(f"{method} selected tie-break mismatch at budget {budget}")
            nominal = nominal_value(tasks, selected, model["nominal_order"], model["endpoints"])
            shared = [nominal_value(tasks, selected, order, model["endpoints"]) for order in orders]
            bound = pess_value(tasks, selected, model["endpoints"])
            if fraction(actual["nominal_order_loss"]) != nominal:
                raise AssertionError(f"nominal evaluation mismatch for {method} at budget {budget}")
            if fraction(actual["max_shared_order_loss"]) != max(shared):
                raise AssertionError(f"shared-order maximum mismatch for {method} at budget {budget}")
            if fraction(actual["pessimistic_taskwise_bound"]) != bound:
                raise AssertionError(f"PESS bound mismatch for {method} at budget {budget}")
            checked += 1
    if checked != 12:
        raise AssertionError(f"expected 12 objective certificates, checked {checked}")
    return checked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    print(f"verified_objective_certificates={verify_summary(args.instance, args.summary)}")


if __name__ == "__main__":
    main()
