"""Nominal-only specialization of the pinned complete exact subset enumerator.

It preserves the pinned selector's candidate-order greedy rule, common integer
denominator, complete subset enumeration, and tie order. PESS matching tables
and scores are omitted because the exact PESS result is already frozen.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from math import lcm
from typing import Mapping, Sequence


def exact_select_nominal_many(
    task_models: Sequence[object],
    candidates: Sequence[tuple[str, Sequence[str]]],
    budgets: Sequence[int],
) -> dict[str, dict[str, object]]:
    candidate_ids = tuple(edge for edge, _ in candidates)
    endpoints = {edge: tuple(vertices) for edge, vertices in candidates}
    if len(endpoints) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    if any(len(vertices) != 2 or vertices[0] == vertices[1] for vertices in endpoints.values()):
        raise ValueError("each candidate must join two distinct endpoints")
    if (not budgets or len(set(budgets)) != len(budgets)
            or any(isinstance(b, bool) or not isinstance(b, int) or b < 0 for b in budgets)):
        raise ValueError("budgets must be unique nonnegative integers")

    max_budget = min(max(budgets), len(candidate_ids))
    subsets = tuple(subset for size in range(max_budget + 1)
                    for subset in combinations(candidate_ids, size))
    scale = 1
    for task in task_models:
        scale = lcm(scale, task.alpha.denominator)
        for value in task.b.values():
            scale = lcm(scale, value.denominator)

    edge_index = {edge: index for index, edge in enumerate(candidate_ids)}
    compiled: list[tuple[int, tuple[int, ...], int]] = []
    for task in task_models:
        if len(task.available_edges) != len(set(task.available_edges)):
            raise ValueError("task available_edges must be unique")
        if set(task.available_edges) - set(edge_index) or set(task.available_edges) - set(task.b):
            raise ValueError("task model contains an unknown edge or missing coefficient")
        values = tuple(int(task.b.get(edge, Fraction(0)) * scale) for edge in candidate_ids)
        mask = sum(1 << edge_index[edge] for edge in task.available_edges)
        compiled.append((int(task.alpha * scale), values, mask))

    # For each subset and each possible task-availability intersection, cache
    # exactly the same greedy maximal matching implied by candidate order.
    subset_data: list[tuple[tuple[int, ...], dict[int, tuple[int, ...]]]] = []
    for subset in subsets:
        indices = tuple(edge_index[edge] for edge in subset)
        patterns: dict[int, tuple[int, ...]] = {}
        for local_mask in range(1 << len(indices)):
            chosen: list[int] = []
            used: set[str] = set()
            for local_index, candidate_index in enumerate(indices):
                if not (local_mask & (1 << local_index)):
                    continue
                edge_vertices = set(endpoints[candidate_ids[candidate_index]])
                if used.isdisjoint(edge_vertices):
                    chosen.append(candidate_index)
                    used.update(edge_vertices)
            patterns[local_mask] = tuple(chosen)
        subset_data.append((indices, patterns))

    scores = [0] * len(subsets)
    for alpha, values, available_mask in compiled:
        for position, (indices, patterns) in enumerate(subset_data):
            local_mask = sum(1 << local_index for local_index, candidate_index in enumerate(indices)
                             if available_mask & (1 << candidate_index))
            chosen = patterns[local_mask]
            scores[position] += abs(alpha + sum(values[index] for index in chosen))

    result: dict[str, dict[str, object]] = {}
    for budget in budgets:
        feasible = [i for i, subset in enumerate(subsets) if len(subset) <= budget]
        optimum = min(scores[i] for i in feasible)
        tied = [list(subsets[i]) for i in feasible if scores[i] == optimum]
        result[str(budget)] = {
            "method": "Nominal",
            "budget_at_most": budget,
            "feasible_subset_count": len(feasible),
            "task_count": len(task_models),
            "objective_fraction": str(Fraction(optimum, scale)),
            "tie_count": len(tied),
            "all_optimal_sets": tied,
            "selected": tied[0],
            "objective_arithmetic": "exact common-denominator integer sum; equivalent Fraction over rationalized inputs",
            "search": "complete enumeration of every subset with cardinality <= budget",
        }
    return result
