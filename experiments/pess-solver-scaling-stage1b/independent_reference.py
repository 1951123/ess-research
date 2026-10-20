"""Independent Fraction verifier for selected original PESS objectives.

This module deliberately does not import pess_ess.reference or
pess_ess.matchings. It enumerates labeled candidate identities itself and is
used for both tiny exhaustive optima and every returned solver incumbent.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from pess_ess.model import Instance, Task


def _all_matchings(ids: tuple[str, ...], endpoints: dict[str, tuple[str, str]]) -> tuple[frozenset[str], ...]:
    result: list[frozenset[str]] = []

    def visit(index: int, chosen: tuple[str, ...], occupied: frozenset[str]) -> None:
        if index == len(ids):
            result.append(frozenset(chosen))
            return
        candidate_id = ids[index]
        visit(index + 1, chosen, occupied)
        edge = frozenset(endpoints[candidate_id])
        if not occupied.intersection(edge):
            visit(index + 1, chosen + (candidate_id,), occupied | edge)

    visit(0, (), frozenset())
    return tuple(sorted(result, key=lambda item: tuple(sorted(item))))


def _is_maximal(matching: frozenset[str], selected: frozenset[str], endpoints: dict[str, tuple[str, str]]) -> bool:
    occupied: set[str] = set()
    for candidate_id in matching:
        edge = set(endpoints[candidate_id])
        if occupied.intersection(edge):
            return False
        occupied.update(edge)
    return all(occupied.intersection(endpoints[candidate_id]) for candidate_id in selected - matching)


def maximal_matchings(selected: frozenset[str], task: Task, instance: Instance) -> tuple[frozenset[str], ...]:
    candidate_map = instance.candidate_map
    local = tuple(sorted(selected.intersection(task.eligible_candidates)))
    endpoints = {candidate_id: candidate_map[candidate_id].endpoints for candidate_id in local}
    matchings = tuple(item for item in _all_matchings(local, endpoints) if _is_maximal(item, frozenset(local), endpoints))
    if not matchings:
        raise AssertionError(f"no maximal matching for task={task.id} selected={sorted(selected)}")
    return matchings


def task_loss(instance: Instance, task: Task, selected: frozenset[str]) -> tuple[Fraction, frozenset[str]]:
    values = {
        matching: abs(task.alpha + sum((task.corrections[item] for item in matching), Fraction()))
        for matching in maximal_matchings(selected, task, instance)
    }
    value = max(values.values())
    witness = min((matching for matching, loss in values.items() if loss == value), key=lambda item: tuple(sorted(item)))
    return value, witness


def objective(instance: Instance, selected: frozenset[str]) -> tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]:
    if instance.maintenance_cost(selected) > instance.budget:
        raise AssertionError("selected set exceeds frozen maintenance budget")
    details = {task.id: task_loss(instance, task, selected) for task in instance.tasks}
    total = sum((task.weight * details[task.id][0] for task in instance.tasks), Fraction())
    return total, details


@dataclass(frozen=True)
class ExhaustiveResult:
    objective: Fraction
    optimal_sets: tuple[frozenset[str], ...]
    evaluated_subsets: int
    feasible_subsets: int


def exhaustive(instance: Instance) -> ExhaustiveResult:
    best: Fraction | None = None
    optimal: list[frozenset[str]] = []
    evaluated = feasible = 0
    for size in range(len(instance.candidates) + 1):
        for selected_tuple in combinations(instance.candidate_ids, size):
            evaluated += 1
            selected = frozenset(selected_tuple)
            if instance.maintenance_cost(selected) > instance.budget:
                continue
            feasible += 1
            value, _ = objective(instance, selected)
            if best is None or value < best:
                best, optimal = value, [selected]
            elif value == best:
                optimal.append(selected)
    if best is None:
        raise AssertionError("empty selection should be feasible")
    return ExhaustiveResult(best, tuple(sorted(optimal, key=lambda item: tuple(sorted(item)))), evaluated, feasible)
