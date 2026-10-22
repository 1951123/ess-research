"""Exact bounded-cardinality selection for the Issue #64 Forest10 milestone.

This module contains no data loading, PostgreSQL access, or outcome access.
It scores caller-supplied validation-only model inputs with Fraction arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import lcm
from typing import Literal, Mapping, Sequence

Method = Literal["Nominal", "PESS"]


@dataclass(frozen=True)
class TaskModel:
    alpha: Fraction
    b: Mapping[str, Fraction]
    available_edges: tuple[str, ...]


def ordered_candidates(
    source_columns: Sequence[str], support_counts: Mapping[tuple[str, str], int]
) -> tuple[tuple[str, tuple[str, str]], ...]:
    """Build stable edge IDs in source-schema pair order from pinned support counts."""
    columns = tuple(source_columns)
    if len(columns) != len(set(columns)):
        raise ValueError("source columns must be unique")
    valid_pairs = tuple(combinations(columns, 2))
    if set(support_counts) - set(valid_pairs):
        raise ValueError("support counts contain a pair outside the source schema")
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in support_counts.values()):
        raise ValueError("candidate support counts must be nonnegative integers")
    return tuple(
        (f"e{left_index:02}_{right_index:02}", (left, right))
        for left_index, left in enumerate(columns)
        for right_index, right in enumerate(columns[left_index + 1 :], start=left_index + 1)
        if support_counts.get((left, right), 0) > 0
    )


def feasible_subsets(candidate_ids: Sequence[str], budget: int) -> tuple[tuple[str, ...], ...]:
    """Enumerate every subset with size <= budget in the frozen candidate order."""
    ids = tuple(candidate_ids)
    if len(ids) != len(set(ids)):
        raise ValueError("candidate IDs must be unique")
    if budget < 0:
        raise ValueError("budget must be nonnegative")
    return tuple(
        subset
        for size in range(min(budget, len(ids)) + 1)
        for subset in combinations(ids, size)
    )


def maximal_matchings(
    available_edges: Sequence[str], candidate_endpoints: Mapping[str, Sequence[str]]
) -> tuple[tuple[str, ...], ...]:
    """Return all inclusion-maximal pairwise-disjoint edge sets."""
    edges = tuple(available_edges)
    if len(edges) != len(set(edges)):
        raise ValueError("available edges must be unique")
    for edge in edges:
        if edge not in candidate_endpoints or len(candidate_endpoints[edge]) != 2:
            raise ValueError(f"edge must have exactly two declared endpoints: {edge}")

    results: list[tuple[str, ...]] = []

    def disjoint(left: str, right: str) -> bool:
        return set(candidate_endpoints[left]).isdisjoint(candidate_endpoints[right])

    def visit(position: int, chosen: list[str]) -> None:
        if position == len(edges):
            chosen_set = set(chosen)
            if all(
                edge in chosen_set or any(not disjoint(edge, kept) for kept in chosen)
                for edge in edges
            ):
                results.append(tuple(chosen))
            return
        edge = edges[position]
        visit(position + 1, chosen)
        if all(disjoint(edge, kept) for kept in chosen):
            chosen.append(edge)
            visit(position + 1, chosen)
            chosen.pop()

    visit(0, [])
    return tuple(sorted(set(results)))


def model_loss(
    task: TaskModel,
    selected: Sequence[str],
    method: Method,
    candidate_endpoints: Mapping[str, Sequence[str]],
    candidate_order: Sequence[str],
) -> Fraction:
    selected_set = set(selected)
    available = tuple(edge for edge in task.available_edges if edge in selected_set)
    if any(edge not in task.b for edge in available):
        raise ValueError("validation model is missing b_e for an available selected edge")

    if method == "Nominal":
        chosen: list[str] = []
        for edge in candidate_order:
            if edge not in available:
                continue
            endpoints = set(candidate_endpoints[edge])
            if all(endpoints.isdisjoint(candidate_endpoints[kept]) for kept in chosen):
                chosen.append(edge)
        schemes = (tuple(chosen),)
    elif method == "PESS":
        schemes = maximal_matchings(available, candidate_endpoints)
    else:
        raise ValueError(f"unsupported method: {method}")

    return max(
        (abs(task.alpha + sum((task.b[edge] for edge in scheme), Fraction(0))) for scheme in schemes),
        default=abs(task.alpha),
    )


def exact_select(
    task_models: Sequence[TaskModel],
    candidates: Sequence[tuple[str, Sequence[str]]],
    budget: int,
    method: Method,
) -> dict[str, object]:
    """Globally minimize one method's frozen validation objective over |S| <= B."""
    return exact_select_many(task_models, candidates, (budget,))[method][str(budget)]


def exact_select_many(
    task_models: Sequence[TaskModel],
    candidates: Sequence[tuple[str, Sequence[str]]],
    budgets: Sequence[int] = (0, 2, 3),
) -> dict[str, dict[str, dict[str, object]]]:
    """Score all subsets once for both methods; retain exact ties for each budget.

    Coefficients share a common integer scale, so the hot loop uses Python ints
    while preserving the exact rational objective. Matching schemes are cached
    once per selected-set/availability pattern. Only compact objective integers
    are retained; no per-task/per-set Fraction result table is materialized.
    """
    candidate_ids = tuple(edge for edge, _ in candidates)
    candidate_endpoints = {edge: tuple(endpoints) for edge, endpoints in candidates}
    if len(candidate_endpoints) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    if any(len(endpoints) != 2 or endpoints[0] == endpoints[1] for endpoints in candidate_endpoints.values()):
        raise ValueError("each candidate must join two distinct endpoints")
    if not budgets or any(isinstance(budget, bool) or not isinstance(budget, int) or budget < 0 for budget in budgets):
        raise ValueError("budgets must be a nonempty sequence of nonnegative integers")
    if len(set(budgets)) != len(budgets):
        raise ValueError("budgets must be unique")
    max_budget = min(max(budgets), len(candidate_ids))
    subsets = feasible_subsets(candidate_ids, max_budget)

    scale = 1
    for task in task_models:
        scale = lcm(scale, task.alpha.denominator)
        for value in task.b.values():
            scale = lcm(scale, value.denominator)
    edge_index = {edge: index for index, edge in enumerate(candidate_ids)}
    compiled_tasks: list[tuple[int, tuple[int, ...], int]] = []
    for task in task_models:
        if len(task.available_edges) != len(set(task.available_edges)):
            raise ValueError("task available_edges must be unique")
        if set(task.available_edges) - set(edge_index):
            raise ValueError("task model refers to an unknown candidate edge")
        if set(task.available_edges) - set(task.b):
            raise ValueError("validation model is missing b_e for an available edge")
        values = tuple(int(task.b.get(edge, Fraction(0)) * scale) for edge in candidate_ids)
        available_mask = sum(1 << edge_index[edge] for edge in task.available_edges)
        compiled_tasks.append((int(task.alpha * scale), values, available_mask))

    endpoints = {edge: tuple(ends) for edge, ends in candidate_endpoints.items()}
    # Cache each resource subset's matching schemes for all possible query-
    # availability intersections (at most 2^3 patterns for this milestone).
    subset_data: list[tuple[tuple[str, ...], tuple[int, ...], int, dict[int, tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]]]] = []
    for subset in subsets:
        indices = tuple(edge_index[edge] for edge in subset)
        global_mask = sum(1 << index for index in indices)
        patterns = {}
        for local_mask in range(1 << len(indices)):
            active_indices = tuple(indices[i] for i in range(len(indices)) if local_mask & (1 << i))
            active_edges = tuple(candidate_ids[i] for i in active_indices)
            nominal: list[int] = []
            used_vertices: set[str] = set()
            for index, edge in zip(active_indices, active_edges):
                edge_vertices = set(endpoints[edge])
                if used_vertices.isdisjoint(edge_vertices):
                    nominal.append(index)
                    used_vertices.update(edge_vertices)
            pess_names = maximal_matchings(active_edges, endpoints)
            pess = tuple(tuple(edge_index[edge] for edge in matching) for matching in pess_names)
            patterns[local_mask] = (tuple(nominal), pess)
        subset_data.append((subset, indices, global_mask, patterns))

    nominal_scores = [0] * len(subsets)
    pess_scores = [0] * len(subsets)
    for alpha, values, available_mask in compiled_tasks:
        for position, (_subset, indices, _global_mask, patterns) in enumerate(subset_data):
            local_mask = 0
            for local_index, candidate_index in enumerate(indices):
                if available_mask & (1 << candidate_index):
                    local_mask |= 1 << local_index
            nominal_scheme, pess_schemes = patterns[local_mask]
            nominal_scores[position] += abs(alpha + sum(values[index] for index in nominal_scheme))
            pess_scores[position] += max(
                abs(alpha + sum(values[index] for index in scheme)) for scheme in pess_schemes
            )

    result: dict[str, dict[str, dict[str, object]]] = {"Nominal": {}, "PESS": {}}
    for budget in budgets:
        feasible_positions = [position for position, subset in enumerate(subsets) if len(subset) <= budget]
        for method, scores in (("Nominal", nominal_scores), ("PESS", pess_scores)):
            optimum_integer = min(scores[position] for position in feasible_positions)
            tied = [
                list(subsets[position])
                for position in feasible_positions
                if scores[position] == optimum_integer
            ]
            objective = Fraction(optimum_integer, scale)
            result[method][str(budget)] = {
                "method": method,
                "budget_at_most": budget,
                "feasible_subset_count": len(feasible_positions),
                "task_count": len(task_models),
                "objective_fraction": str(objective),
                "tie_count": len(tied),
                "all_optimal_sets": tied,
                "selected": tied[0],
                "objective_arithmetic": "exact common-denominator integer sum; equivalent Fraction over rationalized inputs",
                "search": "complete enumeration of every subset with cardinality <= budget",
            }
    return result
