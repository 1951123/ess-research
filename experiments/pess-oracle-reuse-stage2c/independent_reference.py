"""Independent Fraction checks for the Stage 2C task-local reuse audit.

The inner enumeration here is intentionally separate from
``pess_ess.matchings`` and ``pess_ess.reference``. It validates labeled
inclusion-wise maximal matchings and the original task-wise objective only.
"""

from __future__ import annotations

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
    local = tuple(sorted(selected.intersection(task.eligible_candidates)))
    candidate_map = instance.candidate_map
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


def exhaustive(instance: Instance) -> Fraction:
    best: Fraction | None = None
    for size in range(len(instance.candidates) + 1):
        for selected_tuple in combinations(instance.candidate_ids, size):
            selected = frozenset(selected_tuple)
            if instance.maintenance_cost(selected) > instance.budget:
                continue
            value, _details = objective(instance, selected)
            if best is None or value < best:
                best = value
    if best is None:
        raise AssertionError("empty selection should be feasible")
    return best
