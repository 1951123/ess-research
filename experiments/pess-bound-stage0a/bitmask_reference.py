"""Second, bitmask-based tiny reference used to cross-check branch optima."""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations

from reference import Instance


def _edge_bits(edges: tuple[tuple[str, str, str], ...]) -> tuple[dict[str, int], dict[str, int]]:
    vertices = {vertex for _, left, right in edges for vertex in (left, right)}
    vertex_bits = {vertex: 1 << index for index, vertex in enumerate(sorted(vertices))}
    edge_bits = {label: vertex_bits[left] | vertex_bits[right] for label, left, right in edges}
    return edge_bits, vertex_bits


def _matching_masks(edges: tuple[tuple[str, str, str], ...]) -> list[int]:
    edge_bits, _ = _edge_bits(edges)
    labels = tuple(label for label, _, _ in edges)
    masks: list[int] = []
    for selected in range(1 << len(labels)):
        occupied = 0
        valid = True
        for index, label in enumerate(labels):
            if selected & (1 << index):
                endpoints = edge_bits[label]
                if occupied & endpoints:
                    valid = False
                    break
                occupied |= endpoints
        if valid:
            masks.append(selected)
    return masks


def _maximal_masks(edges: tuple[tuple[str, str, str], ...]) -> list[int]:
    edge_bits, _ = _edge_bits(edges)
    labels = tuple(label for label, _, _ in edges)
    maximal: list[int] = []
    for selected in _matching_masks(edges):
        occupied = 0
        for index, label in enumerate(labels):
            if selected & (1 << index):
                occupied |= edge_bits[label]
        if all(
            selected & (1 << index) or occupied & edge_bits[label]
            for index, label in enumerate(labels)
        ):
            maximal.append(selected)
    return maximal


def _task_value(task, selected: set[str]) -> Fraction:
    edges = tuple(edge for edge in task.edges if edge[0] in selected)
    labels = tuple(label for label, _, _ in edges)
    values = []
    for mask in _maximal_masks(edges):
        correction = sum(
            (task.coefficients[label] for index, label in enumerate(labels) if mask & (1 << index)),
            Fraction(0),
        )
        values.append(abs(task.alpha + correction))
    return max(values, default=abs(task.alpha))


def objective(instance: Instance, selected: set[str]) -> Fraction:
    return sum((task.weight * _task_value(task, selected) for task in instance.tasks), Fraction(0))


def exact_completion_optimum(instance: Instance, forced: set[str], undecided: set[str]) -> Fraction | None:
    remaining = instance.budget - instance.cost(forced)
    if remaining < 0:
        return None
    labels = tuple(sorted(undecided))
    values = []
    for mask in range(1 << len(labels)):
        completion = {label for index, label in enumerate(labels) if mask & (1 << index)}
        if instance.cost(completion) <= remaining:
            values.append(objective(instance, forced | completion))
    return min(values) if values else None

