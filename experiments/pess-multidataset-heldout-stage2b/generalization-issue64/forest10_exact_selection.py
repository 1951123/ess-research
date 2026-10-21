"""Exact bounded-cardinality selection for the Issue #64 Forest10 milestone.

This module contains no data loading, PostgreSQL access, or outcome access.
It scores caller-supplied validation-only model inputs with Fraction arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
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
    """Globally minimize the frozen validation objective over all |S| <= B."""
    candidate_ids = tuple(edge for edge, _ in candidates)
    candidate_endpoints = {edge: tuple(endpoints) for edge, endpoints in candidates}
    if len(candidate_endpoints) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    subsets = feasible_subsets(candidate_ids, budget)
    scored = [
        (
            sum(
                (model_loss(task, subset, method, candidate_endpoints, candidate_ids) for task in task_models),
                Fraction(0),
            ),
            subset,
        )
        for subset in subsets
    ]
    optimum = min(score for score, _ in scored)
    # combinations() emits candidate-order lexicographic order; retain every tie.
    tied = [list(subset) for score, subset in scored if score == optimum]
    return {
        "method": method,
        "budget_at_most": budget,
        "feasible_subset_count": len(subsets),
        "task_count": len(task_models),
        "objective_fraction": str(optimum),
        "tie_count": len(tied),
        "all_optimal_sets": tied,
        "selected": tied[0],
        "objective_arithmetic": "exact Fraction over frozen rational model inputs",
        "search": "complete enumeration of every subset with cardinality <= budget",
    }
