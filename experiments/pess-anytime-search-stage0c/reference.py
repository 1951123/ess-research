"""Independent exact Fraction reference for the frozen Stage 0C inputs."""

from __future__ import annotations

import json
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Any


def frac(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(str(value))


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def candidate_map(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in instance["candidates"]}


def endpoints(instance: dict[str, Any], ids: list[str] | tuple[str, ...]) -> dict[str, tuple[str, str]]:
    mapping = candidate_map(instance)
    return {item: tuple(mapping[item]["endpoints"]) for item in ids}


def enumerate_matchings(ids: list[str] | tuple[str, ...], edge_ends: dict[str, tuple[str, str]]) -> tuple[frozenset[str], ...]:
    ordered = tuple(sorted(ids))
    result: list[frozenset[str]] = []

    def visit(position: int, chosen: tuple[str, ...], occupied: frozenset[str]) -> None:
        if position == len(ordered):
            result.append(frozenset(chosen))
            return
        item = ordered[position]
        visit(position + 1, chosen, occupied)
        edge = frozenset(edge_ends[item])
        if not occupied & edge:
            visit(position + 1, chosen + (item,), occupied | edge)

    visit(0, (), frozenset())
    return tuple(sorted(result, key=lambda value: tuple(sorted(value))))


def is_maximal(matching: frozenset[str], selected: frozenset[str], edge_ends: dict[str, tuple[str, str]]) -> bool:
    occupied: set[str] = set()
    for item in matching:
        edge = set(edge_ends[item])
        if occupied & edge:
            return False
        occupied |= edge
    if not matching <= selected:
        return False
    return all(occupied & set(edge_ends[item]) for item in selected - matching)


def maximal_matchings(selected: frozenset[str], edge_ends: dict[str, tuple[str, str]]) -> tuple[frozenset[str], ...]:
    return tuple(
        matching
        for matching in enumerate_matchings(tuple(selected), edge_ends)
        if is_maximal(matching, selected, edge_ends)
    )


def task_loss(instance: dict[str, Any], task: dict[str, Any], selected: frozenset[str]) -> tuple[Fraction, frozenset[str]]:
    eligible = tuple(task["eligible_candidates"])
    selected_eligible = frozenset(item for item in eligible if item in selected)
    edge_ends = endpoints(instance, eligible)
    losses: list[tuple[Fraction, frozenset[str]]] = []
    for matching in maximal_matchings(selected_eligible, edge_ends):
        value = abs(
            frac(task["alpha"])
            + sum((frac(task["corrections"][item]) for item in matching), Fraction())
        )
        losses.append((value, matching))
    if not losses:
        raise AssertionError("selected finite graph has no maximal matching")
    return max(losses, key=lambda item: (item[0], tuple(sorted(item[1]))))


def objective(instance: dict[str, Any], selected: frozenset[str]) -> tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]:
    details = {task["id"]: task_loss(instance, task, selected) for task in instance["tasks"]}
    value = sum(
        (frac(task["weight"]) * details[task["id"]][0] for task in instance["tasks"]),
        Fraction(),
    )
    return value, details


def maintenance(instance: dict[str, Any], selected: frozenset[str]) -> Fraction:
    mapping = candidate_map(instance)
    return sum((frac(mapping[item]["maintenance_cost"]) for item in selected), Fraction())


def feasible(instance: dict[str, Any], selected: frozenset[str]) -> bool:
    return maintenance(instance, selected) <= frac(instance["budget"])


def exhaustive(instance: dict[str, Any]) -> dict[str, Any]:
    ids = tuple(sorted(item["id"] for item in instance["candidates"]))
    best: Fraction | None = None
    optimal: list[frozenset[str]] = []
    feasible_count = 0
    for size in range(len(ids) + 1):
        for values in combinations(ids, size):
            selected = frozenset(values)
            if not feasible(instance, selected):
                continue
            feasible_count += 1
            value, _ = objective(instance, selected)
            if best is None or value < best:
                best = value
                optimal = [selected]
            elif value == best:
                optimal.append(selected)
    assert best is not None
    return {
        "objective": best,
        "optimal_sets": tuple(sorted(optimal, key=lambda item: tuple(sorted(item)))),
        "feasible_subsets": feasible_count,
        "evaluated_subsets": 2 ** len(ids),
    }


def verify_selected(instance: dict[str, Any], selected_ids: list[str] | tuple[str, ...], expected_objective: str | None = None) -> dict[str, Any]:
    selected = frozenset(selected_ids)
    if not feasible(instance, selected):
        raise AssertionError(f"infeasible selection: {sorted(selected)}")
    value, details = objective(instance, selected)
    if expected_objective is not None and value != frac(expected_objective):
        raise AssertionError(f"objective mismatch: expected {expected_objective}, actual {value}")
    return {
        "selected": sorted(selected),
        "maintenance": str(maintenance(instance, selected)),
        "objective": str(value),
        "task_details": {
            task_id: {"loss": str(loss), "witness": sorted(witness)}
            for task_id, (loss, witness) in details.items()
        },
    }


def signed_extrema_bound(instance: dict[str, Any], task: dict[str, Any], selected: frozenset[str]) -> Fraction:
    """Cheap PESS-specific ordering signal, not a replacement objective.

    The ordinary matching sum interval gives a valid upper bound on the
    maximal-matching adversary.  The search treatment uses changes in this
    two-sided signed-extrema envelope only to order neighbors; every accepted
    incumbent is evaluated by ``objective`` above.
    """
    eligible = tuple(item for item in task["eligible_candidates"] if item in selected)
    edge_ends = endpoints(instance, tuple(task["eligible_candidates"]))
    sums = [
        sum((frac(task["corrections"][item]) for item in matching), Fraction())
        for matching in enumerate_matchings(eligible, edge_ends)
    ]
    low = min(sums, default=Fraction())
    high = max(sums, default=Fraction())
    return max(abs(frac(task["alpha"]) + low), abs(frac(task["alpha"]) + high))


def signed_extrema_objective_bound(instance: dict[str, Any], selected: frozenset[str]) -> Fraction:
    return sum(
        (frac(task["weight"]) * signed_extrema_bound(instance, task, selected) for task in instance["tasks"]),
        Fraction(),
    )
