"""Exact worst-case maximal-matching oracle on selected paths, cycles and stars.

Mathematical test artifact for notes/degree-two-exact-inner-oracle.md.
Input edges are (attribute_u, attribute_v, signed_weight), with integer
weights. Parallel labeled edges are distinct and are collapsed to min/max
weight bundles *only after* validating their shared endpoints.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

Edge = tuple[int, int, int]
Bundle = list[int]


def _best(values: Iterable[int], maximize: bool) -> int:
    return max(values) if maximize else min(values)


def _path_extreme(weights: list[int], maximize: bool) -> int:
    """One bit per selected edge bundle, two-bit automaton + final zero sentinel."""
    states = {(0, 0): 0}
    for pos in range(1, len(weights) + 2):
        next_states: dict[tuple[int, int], int] = {}
        for (prevprev, prev), value in states.items():
            for choose in ((0,) if pos > len(weights) else (0, 1)):
                if prev + choose > 1:
                    continue  # matching: adjacent bundles cannot both be chosen
                if pos >= 2 and prevprev + prev + choose == 0:
                    continue  # previous bundle is not dominated
                key = (prev, choose)
                candidate = value + (weights[pos - 1] if choose else 0)
                if key not in next_states:
                    next_states[key] = candidate
                else:
                    next_states[key] = _best((next_states[key], candidate), maximize)
        states = next_states
    assert states
    return _best(states.values(), maximize)


def _cycle_extreme(weights: list[int], maximize: bool) -> int:
    """Enumerate the first two bits, DP through the cycle, check wrap-around."""
    count = len(weights)
    if count < 3:
        raise ValueError("a simple cycle requires at least three edge bundles")
    feasible: list[int] = []
    for first in (0, 1):
        for second in (0, 1):
            if first + second > 1:
                continue
            states = {(first, second): first * weights[0] + second * weights[1]}
            for pos in range(2, count):
                next_states: dict[tuple[int, int], int] = {}
                for (prevprev, prev), value in states.items():
                    for choose in (0, 1):
                        if prev + choose > 1 or prevprev + prev + choose == 0:
                            continue
                        key = (prev, choose)
                        candidate = value + choose * weights[pos]
                        if key not in next_states:
                            next_states[key] = candidate
                        else:
                            next_states[key] = _best((next_states[key], candidate), maximize)
                states = next_states
            for (penultimate, last), value in states.items():
                if last + first > 1:  # closing adjacency
                    continue
                if penultimate + last + first == 0:  # last edge dominated?
                    continue
                if last + first + second == 0:  # first edge dominated?
                    continue
                feasible.append(value)
    assert feasible
    return _best(feasible, maximize)


def maximal_matching_weight_extrema(selected_edges: Iterable[Edge]) -> tuple[int, int]:
    """Return (minimum, maximum) matching weight among ALL maximal matchings.

    The selected simple graph, formed by ignoring parallel labeled edges,
    must be a vertex-disjoint union of paths, cycles and stars. Components
    with isolated vertices do not matter. Raises ValueError for unsupported
    topology (rather than silently giving a wrong bound).
    """
    bundles: dict[frozenset[int], Bundle] = defaultdict(list)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for u, v, weight in selected_edges:
        if u == v:
            raise ValueError("loops are not two-attribute candidates")
        pair = frozenset((u, v))
        bundles[pair].append(weight)
        adjacency[u].add(v)
        adjacency[v].add(u)

    if not bundles:
        return 0, 0

    seen: set[int] = set()
    total_min = 0
    total_max = 0

    for start in adjacency:
        if start in seen:
            continue
        vertices: set[int] = set()
        todo = [start]
        seen.add(start)
        while todo:
            u = todo.pop()
            vertices.add(u)
            for v in adjacency[u]:
                if v not in seen:
                    seen.add(v)
                    todo.append(v)

        # A connected star has exactly one high-degree center; single edges
        # and two-edge paths are also valid stars.
        center = next(
            (v for v in vertices
             if len(adjacency[v]) == len(vertices) - 1
             and all(len(adjacency[w]) == 1 for w in vertices if w != v)),
            None,
        )
        if center is not None:
            component_weights = [
                weight for leaf in adjacency[center]
                for weight in bundles[frozenset((center, leaf))]
            ]
            total_min += min(component_weights)
            total_max += max(component_weights)
            continue

        if any(len(adjacency[u]) > 2 for u in vertices):
            raise ValueError("unsupported component: not a star or degree-two graph")

        leaf = next((v for v in vertices if len(adjacency[v]) == 1), None)
        ordered_bundles: list[Bundle] = []

        if leaf is not None:  # path
            previous: int | None = None
            current = leaf
            while True:
                next_nodes = [v for v in adjacency[current] if v != previous]
                if not next_nodes:
                    break
                successor = next_nodes[0]
                ordered_bundles.append(bundles[frozenset((current, successor))])
                previous, current = current, successor
            if len(ordered_bundles) != len(vertices) - 1:
                raise ValueError("path traversal did not cover the component")
            solver = _path_extreme
        else:  # a connected simple graph with all degrees 2 is a cycle
            previous = None
            current = start
            for _ in vertices:
                successor = next(v for v in adjacency[current] if v != previous)
                ordered_bundles.append(bundles[frozenset((current, successor))])
                previous, current = current, successor
            if current != start or len(ordered_bundles) != len(vertices):
                raise ValueError("cycle traversal did not close")
            solver = _cycle_extreme

        total_min += solver([min(group) for group in ordered_bundles], maximize=False)
        total_max += solver([max(group) for group in ordered_bundles], maximize=True)

    return total_min, total_max


def worst_absolute_loss(selected_edges: Iterable[Edge], alpha: int) -> int:
    """Integer-coefficient stand-in for |alpha + sum selected b_e|."""
    low, high = maximal_matching_weight_extrema(selected_edges)
    return max(abs(alpha + low), abs(alpha + high))
