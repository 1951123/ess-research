"""Definition-driven, Fraction-only reference for Stage 0B.

This module intentionally does not import the approximate solver or its
certificate code.  It enumerates labeled ordinary matchings directly and
uses the definition of maximality on the selected graph.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from time import perf_counter

Edge = tuple[str, str, str]
Matching = tuple[str, ...]


def _edge_map(edges: Sequence[Edge]) -> dict[str, Edge]:
    result = {label: (label, left, right) for label, left, right in edges}
    if len(result) != len(edges):
        raise ValueError("resource labels must be unique within a task")
    if any(left == right for _, left, right in edges):
        raise ValueError("loops are outside the pairwise model")
    return result


def matching_labels(edges: Sequence[Edge]) -> Iterator[Matching]:
    """Enumerate every labeled ordinary matching, including the empty one."""

    edge_map = _edge_map(edges)
    labels = tuple(edge_map)

    def visit(index: int, used: frozenset[str], chosen: tuple[str, ...]) -> Iterator[Matching]:
        if index == len(labels):
            yield chosen
            return
        label = labels[index]
        yield from visit(index + 1, used, chosen)
        _, left, right = edge_map[label]
        if left not in used and right not in used:
            yield from visit(index + 1, used | {left, right}, chosen + (label,))

    yield from visit(0, frozenset(), ())


def is_matching(edges: Sequence[Edge], matching: Matching) -> bool:
    edge_map = _edge_map(edges)
    used: set[str] = set()
    for label in matching:
        if label not in edge_map:
            return False
        _, left, right = edge_map[label]
        if left in used or right in used:
            return False
        used.update((left, right))
    return True


def is_maximal(edges: Sequence[Edge], matching: Matching) -> bool:
    edge_map = _edge_map(edges)
    if not is_matching(edges, matching):
        return False
    used: set[str] = set()
    chosen = set(matching)
    for label in matching:
        _, left, right = edge_map[label]
        used.update((left, right))
    return all(
        label in chosen or left in used or right in used
        for label, left, right in edges
    )


def maximal_matching_labels(edges: Sequence[Edge]) -> tuple[Matching, ...]:
    return tuple(m for m in matching_labels(edges) if is_maximal(edges, m))


def matching_sum(matching: Matching, coefficients: Mapping[str, Fraction]) -> Fraction:
    return sum((coefficients[label] for label in matching), Fraction(0))


def matching_loss(alpha: Fraction, matching: Matching, coefficients: Mapping[str, Fraction]) -> Fraction:
    return abs(alpha + matching_sum(matching, coefficients))


def task_loss(alpha: Fraction, edges: Sequence[Edge], coefficients: Mapping[str, Fraction]) -> Fraction:
    maximal = maximal_matching_labels(edges)
    if not maximal:
        raise AssertionError("the empty graph must have an empty maximal matching")
    return max(matching_loss(alpha, m, coefficients) for m in maximal)


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

    def selected_edges(self, selected: Iterable[str]) -> tuple[Edge, ...]:
        selected_set = set(selected)
        return tuple(edge for edge in self.edges if edge[0] in selected_set)

    def objective(self, selected: Iterable[str], coefficients: Mapping[str, Fraction] | None = None) -> Fraction:
        coeffs = self.coefficients if coefficients is None else coefficients
        return task_loss(self.alpha, self.selected_edges(selected), coeffs)


@dataclass(frozen=True)
class Instance:
    name: str
    resources: tuple[str, ...]
    tasks: tuple[Task, ...]
    maintenance: dict[str, Fraction]
    budget: Fraction
    tier: str = "small"

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

    def feasible(self, selected: Iterable[str]) -> bool:
        return self.cost(selected) <= self.budget

    def objective(
        self,
        selected: Iterable[str],
        coefficients_by_task: Mapping[str, Mapping[str, Fraction]] | None = None,
    ) -> Fraction:
        return sum(
            (
                task.weight
                * task.objective(
                    selected,
                    None if coefficients_by_task is None else coefficients_by_task[task.name],
                )
                for task in self.tasks
            ),
            Fraction(0),
        )


def all_subsets(labels: Sequence[str]) -> Iterator[frozenset[str]]:
    for size in range(len(labels) + 1):
        for picked in combinations(labels, size):
            yield frozenset(picked)


@dataclass(frozen=True)
class OptimizationResult:
    complete: bool
    best_value: Fraction | None
    best_selection: frozenset[str] | None
    states: int
    elapsed_seconds: float
    stop_reason: str | None


def exact_outer_optimum(
    instance: Instance,
    coefficients_by_task: Mapping[str, Mapping[str, Fraction]] | None = None,
    *,
    time_limit_seconds: float | None = None,
    state_cap: int | None = None,
) -> OptimizationResult:
    """Exhaustively solve the feasible outer subsets, with fail-closed caps."""

    start = perf_counter()
    best_value: Fraction | None = None
    best_selection: frozenset[str] | None = None
    states = 0
    stop_reason: str | None = None
    for selected in all_subsets(instance.resources):
        if state_cap is not None and states >= state_cap:
            stop_reason = "STATE_CAP"
            break
        if time_limit_seconds is not None and perf_counter() - start >= time_limit_seconds:
            stop_reason = "TIMEOUT"
            break
        if not instance.feasible(selected):
            continue
        states += 1
        value = instance.objective(selected, coefficients_by_task)
        if best_value is None or value < best_value or (
            value == best_value
            and (best_selection is None or (len(selected), tuple(sorted(selected))) > (len(best_selection), tuple(sorted(best_selection))))
        ):
            best_value = value
            best_selection = selected
    complete = stop_reason is None
    return OptimizationResult(
        complete=complete,
        best_value=best_value,
        best_selection=best_selection,
        states=states,
        elapsed_seconds=perf_counter() - start,
        stop_reason=stop_reason,
    )


def maximum_weight_matching_exhaustive(
    edges: Sequence[Edge], weights: Mapping[str, Fraction]
) -> tuple[Fraction, Matching]:
    """Independent ordinary-matching check used by certificate tests."""

    best = Fraction(0)
    best_matching: Matching = ()
    for matching in matching_labels(edges):
        value = sum((weights[label] for label in matching), Fraction(0))
        if value > best or (value == best and matching < best_matching):
            best = value
            best_matching = matching
    return best, best_matching
