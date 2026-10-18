"""Small exact checks for the star reductions in notes/constant-factor-star-hardness.md.

The oracle enumerates matchings explicitly; it does not assume the desired
coverage formula when constructing each task's worst loss.
The log loss is normalized by ln(2), so coefficients are alpha=1, b=-1.
"""

from __future__ import annotations

import itertools
import random


def maximal_matchings(active: tuple[tuple[int, int], ...]):
    """Enumerate maximal matchings, including the empty graph's empty matching."""
    for size in range(len(active) + 1):
        for p in itertools.combinations(active, size):
            if any(set(a) & set(b) for a, b in itertools.combinations(p, 2)):
                continue
            if any(not any(set(f) & set(e) for e in p) for f in active):
                continue
            yield p


def normalized_star_loss(
    eligible: tuple[int, ...], selected: set[int]
) -> int:
    # All candidate edges share center attribute 0, with unique leaves.
    active = tuple((0, j + 1) for j in eligible if j in selected)
    scores = [abs(1 - len(p)) for p in maximal_matchings(active)]
    assert scores  # even an edgeless graph has its empty maximal matching
    return max(scores)


def test_vertex_cover_reduction_exhaustive_random() -> None:
    rng = random.Random(18)
    checked_instances = 0
    checked_selections = 0
    for _ in range(600):
        n = rng.randint(2, 9)
        edges = [
            (u, v) for u in range(n) for v in range(u + 1, n)
            if rng.randrange(3) == 0
        ]
        budget = rng.randrange(n + 1)
        model_zero_at_budget = False
        covered_at_budget = False
        for mask in range(1 << n):
            selected = {j for j in range(n) if mask & (1 << j)}
            loss = sum(normalized_star_loss((u, v), selected) for u, v in edges)
            uncovered = sum(not (u in selected or v in selected) for u, v in edges)
            assert loss == uncovered
            checked_selections += 1
            if len(selected) <= budget:
                model_zero_at_budget |= loss == 0
                covered_at_budget |= uncovered == 0
        assert model_zero_at_budget == covered_at_budget
        checked_instances += 1
    assert (checked_instances, checked_selections) == (600, 74692)


def test_max_coverage_reduction_exhaustive_random() -> None:
    rng = random.Random(20261018)
    checked_instances = 0
    checked_selections = 0
    for _ in range(600):
        num_sets = rng.randint(1, 7)
        num_elements = rng.randint(1, 7)
        sets = [
            {i for i in range(num_elements) if rng.randrange(2)}
            for _ in range(num_sets)
        ]
        budget = rng.randint(0, num_sets)
        best_loss = num_elements + 1
        best_covered = -1
        for mask in range(1 << num_sets):
            selected = {j for j in range(num_sets) if mask & (1 << j)}
            model_loss = sum(
                normalized_star_loss(
                    tuple(j for j in range(num_sets) if i in sets[j]),
                    selected,
                )
                for i in range(num_elements)
            )
            covered = set().union(*(sets[j] for j in selected))
            assert model_loss == num_elements - len(covered)
            checked_selections += 1
            if len(selected) <= budget:
                best_loss = min(best_loss, model_loss)
                best_covered = max(best_covered, len(covered))
        assert best_loss == num_elements - best_covered
        checked_instances += 1
    assert (checked_instances, checked_selections) == (600, 21438)
