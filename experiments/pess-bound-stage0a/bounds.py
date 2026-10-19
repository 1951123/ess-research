"""Candidate witness-completion and sensitivity bounds for Issue #30."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from time import perf_counter
from typing import Iterable

from reference import Edge, Instance, Matching, Task, lambda_floor, matching_labels, ordinary_extrema


def endpoint_set(task: Task, matching: Matching) -> frozenset[str]:
    edge_map = {label: edge for edge in task.edges for label in (edge[0],)}
    endpoints: set[str] = set()
    for label in matching:
        _, left, right = edge_map[label]
        endpoints.update((left, right))
    return frozenset(endpoints)


def greedy_witness(task: Task, forced: set[str]) -> Matching:
    """Deterministic legal maximal witness: task edge order, then label."""
    selected_edges = [edge for edge in task.edges if edge[0] in forced]
    used: set[str] = set()
    chosen: list[str] = []
    for label, left, right in selected_edges:
        if left not in used and right not in used:
            chosen.append(label)
            used.update((left, right))
    # The construction is maximal by the same order-independent definition,
    # but keep a direct check here so a future change fails closed.
    for label, left, right in selected_edges:
        if label not in chosen and left not in used and right not in used:
            raise AssertionError("greedy witness is not maximal")
    return tuple(chosen)


def exact_worst_prefix_witness(task: Task, forced: set[str]) -> Matching:
    selected_edges = tuple(edge for edge in task.edges if edge[0] in forced)
    maximal = tuple(matching_labels(selected_edges))
    maximal = tuple(
        m for m in maximal
        if all(
            label in m or left in endpoint_set(task, m) or right in endpoint_set(task, m)
            for label, left, right in selected_edges
        )
    )
    return max(
        maximal,
        key=lambda m: (abs(task.alpha + sum((task.coefficients[label] for label in m), Fraction(0))), tuple(m)),
    )


def q_extrema(task: Task, witness: Matching, undecided: set[str]) -> tuple[Fraction, Fraction]:
    occupied = endpoint_set(task, witness)
    remaining = tuple(edge for edge in task.edges if edge[0] in undecided and not ({edge[1], edge[2]} & occupied))
    return ordinary_extrema(remaining, task.coefficients)


def witness_d(task: Task, witness: Matching, undecided: set[str]) -> Fraction:
    a = task.alpha + sum((task.coefficients[label] for label in witness), Fraction(0))
    q_minus, q_plus = q_extrema(task, witness, undecided)
    return max(Fraction(0), a + q_minus, -a - q_plus)


def witness_bound(instance: Instance, forced: set[str], undecided: set[str], strategy: str) -> tuple[Fraction, dict[str, Matching], dict[str, int]]:
    if strategy not in {"greedy", "exact", "pooled"}:
        raise ValueError(strategy)
    total = Fraction(0)
    witnesses: dict[str, Matching] = {}
    q_calls = 0
    for task in instance.tasks:
        candidates = [greedy_witness(task, forced)]
        if strategy in {"exact", "pooled"}:
            candidates.append(exact_worst_prefix_witness(task, forced))
        if strategy == "pooled":
            # A small deterministic legal pool: all maximal witnesses for the
            # forced graph, capped only by the pilot's tiny-graph scope.
            selected_edges = tuple(edge for edge in task.edges if edge[0] in forced)
            candidates.extend(
                m for m in matching_labels(selected_edges)
                if all(
                    label in m or left in endpoint_set(task, m) or right in endpoint_set(task, m)
                    for label, left, right in selected_edges
                )
            )
        unique = tuple(dict.fromkeys(candidates))
        values = [(witness_d(task, witness, undecided), witness) for witness in unique]
        q_calls += len(values)
        best_value, best_witness = max(values, key=lambda pair: (pair[0], pair[1]))
        total += task.weight * best_value
        witnesses[task.name] = best_witness
    return total, witnesses, {"q_extrema_calls": q_calls}


def knapsack_exact(instance: Instance, undecided: set[str], remaining_budget: Fraction, values: dict[str, Fraction]) -> Fraction:
    best = Fraction(0)
    labels = tuple(sorted(undecided))
    for mask in range(1 << len(labels)):
        chosen = [labels[index] for index in range(len(labels)) if mask & (1 << index)]
        cost = sum((instance.maintenance[label] for label in chosen), Fraction(0))
        if cost <= remaining_budget:
            value = sum((values[label] for label in chosen), Fraction(0))
            best = max(best, value)
    return best


def knapsack_fractional(instance: Instance, undecided: set[str], remaining_budget: Fraction, values: dict[str, Fraction]) -> Fraction:
    value = Fraction(0)
    budget = remaining_budget
    for label in sorted(undecided):
        if instance.maintenance[label] == 0 and values[label] > 0:
            value += values[label]
    positive = [
        label for label in undecided
        if instance.maintenance[label] > 0 and values[label] > 0
    ]
    positive.sort(key=lambda label: (values[label] / instance.maintenance[label], label), reverse=True)
    for label in positive:
        if budget <= 0:
            break
        take = min(instance.maintenance[label], budget)
        value += values[label] * take / instance.maintenance[label]
        budget -= take
    return value


@dataclass(frozen=True)
class BoundSnapshot:
    floor: Fraction
    sensitivity_exact: Fraction
    sensitivity_fractional: Fraction
    witness_greedy: Fraction
    witness_exact: Fraction
    exact_prefix_optimum: Fraction
    f_forced: Fraction
    q_calls_greedy: int
    q_calls_exact: int
    witness_greedy_seconds: float
    witness_exact_seconds: float
    f_forced_seconds: float


def evaluate_bounds(
    instance: Instance,
    forced: set[str],
    undecided: set[str],
    floor_override: Fraction | None = None,
) -> BoundSnapshot:
    floor = floor_override
    if floor is None:
        floor = sum((task.weight * lambda_floor(task) for task in instance.tasks), Fraction(0))
    start = perf_counter()
    f_forced = instance.objective(forced)
    f_seconds = perf_counter() - start
    remaining_budget = instance.budget - instance.cost(forced)
    values = {
        label: sum((task.weight * abs(task.coefficients[label]) for task in instance.tasks if label in task.resources), Fraction(0))
        for label in undecided
    }
    if remaining_budget < 0:
        raise ValueError("infeasible forced set")
    exact_k = knapsack_exact(instance, undecided, remaining_budget, values)
    fractional_k = knapsack_fractional(instance, undecided, remaining_budget, values)
    start = perf_counter()
    greedy, _, greedy_meta = witness_bound(instance, forced, undecided, "greedy")
    greedy_seconds = perf_counter() - start
    start = perf_counter()
    exact, _, exact_meta = witness_bound(instance, forced, undecided, "exact")
    exact_seconds = perf_counter() - start
    return BoundSnapshot(
        floor=Fraction(floor),
        sensitivity_exact=max(Fraction(0), f_forced - exact_k),
        sensitivity_fractional=max(Fraction(0), f_forced - fractional_k),
        witness_greedy=greedy,
        witness_exact=exact,
        exact_prefix_optimum=instance.objective(forced),
        f_forced=f_forced,
        q_calls_greedy=greedy_meta["q_extrema_calls"],
        q_calls_exact=exact_meta["q_extrema_calls"],
        witness_greedy_seconds=greedy_seconds,
        witness_exact_seconds=exact_seconds,
        f_forced_seconds=f_seconds,
    )

