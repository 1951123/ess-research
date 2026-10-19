"""Independent exact reference for the Issue #30 maximal-matching model.

This module intentionally contains no witness-bound implementation.  It is a
small, Fraction-only definition-level oracle used by the tests and runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Iterable, Iterator, Sequence


Edge = tuple[str, str, str]  # (resource label, endpoint 1, endpoint 2)
Matching = tuple[str, ...]


def _edge_map(edges: Sequence[Edge]) -> dict[str, Edge]:
    result = {label: (label, left, right) for label, left, right in edges}
    if len(result) != len(edges):
        raise ValueError("resource labels must be unique within a task")
    if any(left == right for _, left, right in edges):
        raise ValueError("loops are outside the Stage 0A pairwise model")
    return result


def matching_labels(edges: Sequence[Edge]) -> Iterator[Matching]:
    """Enumerate every labeled ordinary matching, including the empty one."""

    edge_map = _edge_map(edges)
    labels = tuple(edge_map)

    def visit(position: int, used: frozenset[str], chosen: tuple[str, ...]) -> Iterator[Matching]:
        if position == len(labels):
            yield chosen
            return
        label = labels[position]
        yield from visit(position + 1, used, chosen)
        _, left, right = edge_map[label]
        if left not in used and right not in used:
            yield from visit(position + 1, used | {left, right}, chosen + (label,))

    yield from visit(0, frozenset(), ())


def is_matching(edge_map: dict[str, Edge], matching: Matching) -> bool:
    used: set[str] = set()
    for label in matching:
        _, left, right = edge_map[label]
        if left in used or right in used:
            return False
        used.update((left, right))
    return True


def is_maximal(edges: Sequence[Edge], matching: Matching) -> bool:
    edge_map = _edge_map(edges)
    if not is_matching(edge_map, matching):
        return False
    used: set[str] = set()
    for label in matching:
        _, left, right = edge_map[label]
        used.update((left, right))
    return all(
        label in matching or left in used or right in used
        for label, left, right in edges
    )


def maximal_matching_labels(edges: Sequence[Edge]) -> tuple[Matching, ...]:
    return tuple(m for m in matching_labels(edges) if is_maximal(edges, m))


def sum_coefficients(matching: Matching, coefficients: dict[str, Fraction]) -> Fraction:
    return sum((coefficients[label] for label in matching), Fraction(0))


def loss(alpha: Fraction, matching: Matching, coefficients: dict[str, Fraction]) -> Fraction:
    return abs(alpha + sum_coefficients(matching, coefficients))


def task_loss(
    alpha: Fraction,
    edges: Sequence[Edge],
    coefficients: dict[str, Fraction],
) -> Fraction:
    return max(
        (loss(alpha, matching, coefficients) for matching in maximal_matching_labels(edges)),
        default=abs(alpha),
    )


@dataclass(frozen=True)
class Task:
    name: str
    weight: Fraction
    alpha: Fraction
    edges: tuple[Edge, ...]
    coefficients: dict[str, Fraction]

    def __post_init__(self) -> None:
        labels = {label for label, _, _ in self.edges}
        if set(self.coefficients) != labels:
            raise ValueError(f"task {self.name}: coefficients and edges disagree")
        if self.weight <= 0:
            raise ValueError("task weights must be positive")

    @property
    def resources(self) -> frozenset[str]:
        return frozenset(label for label, _, _ in self.edges)

    def selected_edges(self, selected: set[str] | frozenset[str]) -> tuple[Edge, ...]:
        return tuple(edge for edge in self.edges if edge[0] in selected)

    def objective(self, selected: set[str] | frozenset[str]) -> Fraction:
        edges = self.selected_edges(selected)
        return task_loss(self.alpha, edges, self.coefficients)


@dataclass(frozen=True)
class Instance:
    resources: tuple[str, ...]
    tasks: tuple[Task, ...]
    maintenance: dict[str, Fraction]
    budget: Fraction

    def __post_init__(self) -> None:
        resource_set = set(self.resources)
        if len(resource_set) != len(self.resources):
            raise ValueError("resource labels must be unique")
        if set(self.maintenance) != resource_set:
            raise ValueError("maintenance coefficients and resources disagree")
        if any(value < 0 for value in self.maintenance.values()):
            raise ValueError("maintenance coefficients must be nonnegative")
        if self.budget < 0:
            raise ValueError("budget must be nonnegative")

    def cost(self, selected: Iterable[str]) -> Fraction:
        return sum((self.maintenance[label] for label in selected), Fraction(0))

    def objective(self, selected: set[str] | frozenset[str]) -> Fraction:
        return sum((task.weight * task.objective(selected) for task in self.tasks), Fraction(0))

    def feasible(self, selected: Iterable[str]) -> bool:
        return self.cost(selected) <= self.budget


def ordinary_extrema(
    edges: Sequence[Edge], coefficients: dict[str, Fraction]
) -> tuple[Fraction, Fraction]:
    values = [sum_coefficients(m, coefficients) for m in matching_labels(edges)]
    return min(values, default=Fraction(0)), max(values, default=Fraction(0))


def lambda_floor(task: Task) -> Fraction:
    lower, upper = ordinary_extrema(task.edges, task.coefficients)
    return max(Fraction(0), task.alpha + lower, -task.alpha - upper)


def global_floor(instance: Instance) -> Fraction:
    return sum((task.weight * lambda_floor(task) for task in instance.tasks), Fraction(0))


def all_subsets(labels: Sequence[str]) -> Iterator[frozenset[str]]:
    for size in range(len(labels) + 1):
        for picked in combinations(labels, size):
            yield frozenset(picked)


def exact_completion_optimum(instance: Instance, forced: set[str], undecided: set[str]) -> Fraction | None:
    remaining_budget = instance.budget - instance.cost(forced)
    if remaining_budget < 0:
        return None
    values = [
        instance.objective(set(forced) | set(completion))
        for completion in all_subsets(tuple(sorted(undecided)))
        if instance.cost(completion) <= remaining_budget
    ]
    return min(values) if values else None

