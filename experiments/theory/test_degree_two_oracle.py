"""Brute-force cross-checks for the exact maximal-matching path/cycle/star DP."""

from __future__ import annotations

import random

import pytest

from experiments.theory.degree_two_oracle import (
    maximal_matching_weight_extrema,
    worst_absolute_loss,
)


def brute_extrema(edges: list[tuple[int, int, int]]) -> tuple[int, int]:
    weights: list[int] = []
    for mask in range(1 << len(edges)):
        endpoints: set[int] = set()
        chosen: list[tuple[int, int, int]] = []
        valid = True
        for index, edge in enumerate(edges):
            if mask & (1 << index):
                u, v, _ = edge
                if u in endpoints or v in endpoints:
                    valid = False
                    break
                endpoints.update((u, v))
                chosen.append(edge)
        if not valid:
            continue
        if any(u not in endpoints and v not in endpoints for u, v, _ in edges):
            continue
        weights.append(sum(w for _, _, w in chosen))
    assert weights, "every finite graph has a maximal matching"
    return min(weights), max(weights)


def make_graph(rng: random.Random, kind: str) -> list[tuple[int, int, int]]:
    length = rng.randint(1, 6)
    if kind == "path":
        pairs = [(i, i + 1) for i in range(length)]
    elif kind == "cycle":
        length = max(3, length)
        pairs = [(i, (i + 1) % length) for i in range(length)]
    elif kind == "star":
        pairs = [(0, i + 1) for i in range(length)]
    else:
        raise AssertionError(kind)
    edges = []
    for u, v in pairs:
        edges.append((u, v, rng.randrange(-8, 9)))
        if rng.randrange(3) == 0:
            edges.append((v, u, rng.randrange(-8, 9)))  # parallel label
    return edges


@pytest.mark.parametrize("kind", ["path", "cycle", "star"])
def test_all_selected_subsets_match_brute_force(kind: str) -> None:
    rng = random.Random({"path": 100, "cycle": 200, "star": 300}[kind])
    checked = 0
    for _ in range(65):
        graph = make_graph(rng, kind)
        for mask in range(1 << len(graph)):
            selected = [edge for j, edge in enumerate(graph) if mask & (1 << j)]
            expected = brute_extrema(selected)
            actual = maximal_matching_weight_extrema(selected)
            assert actual == expected, (kind, selected, actual, expected)
            for alpha in (-7, 0, 6):
                assert worst_absolute_loss(selected, alpha) == max(
                    abs(alpha + expected[0]),
                    abs(alpha + expected[1]),
                )
            checked += 1
    assert checked >= 65


def test_disconnected_mixed_components_and_isolated_empty() -> None:
    edges = [
        (0, 1, -7), (1, 2, 4), (2, 3, 1), (3, 0, -2),  # cycle
        (10, 11, 9), (11, 12, -5), (12, 13, 2),         # path
        (20, 21, -3), (20, 22, 4), (20, 23, 0),         # star
        (30, 31, -4), (31, 30, 6),                      # two labeled parallel edges
    ]
    assert maximal_matching_weight_extrema(edges) == brute_extrema(edges)
    assert maximal_matching_weight_extrema([]) == (0, 0)
    assert worst_absolute_loss([], -5) == 5


def test_reject_unsupported_branching_and_self_loop() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        maximal_matching_weight_extrema(
            [(0, 1, 1), (0, 2, 2), (0, 3, 3), (3, 4, -4)]
        )
    with pytest.raises(ValueError, match="loops"):
        maximal_matching_weight_extrema([(0, 0, 1)])
