"""Exact coefficient quantization and matching-aware perturbation bounds."""

from __future__ import annotations

from fractions import Fraction
from typing import Mapping

from stage0b_reference import Edge, Instance, Task, matching_labels


def nearest_multiple_ties_to_zero(value: Fraction, delta: Fraction) -> Fraction:
    if delta <= 0:
        raise ValueError("delta must be positive")
    sign = -1 if value < 0 else 1
    magnitude = abs(value) / delta
    lower = magnitude.numerator // magnitude.denominator
    remainder = magnitude - lower
    units = lower + (1 if remainder > Fraction(1, 2) else 0)
    return sign * delta * units


def quantize_coefficients(task: Task, delta: Fraction | None) -> dict[str, Fraction]:
    if delta is None:
        return dict(task.coefficients)
    return {
        label: nearest_multiple_ties_to_zero(value, delta)
        for label, value in task.coefficients.items()
    }


def quantized_coefficients(
    instance: Instance, deltas: Mapping[str, Fraction | None]
) -> dict[str, dict[str, Fraction]]:
    return {task.name: quantize_coefficients(task, deltas[task.name]) for task in instance.tasks}


def ordinary_matching_max_weight_recursive(
    edges: tuple[Edge, ...], weights: Mapping[str, Fraction]
) -> tuple[Fraction, tuple[str, ...]]:
    """A separate include/skip recursion, not the reference matching enumerator."""

    best_value = Fraction(0)
    best_matching: tuple[str, ...] = ()

    def visit(index: int, used: frozenset[str], chosen: tuple[str, ...], value: Fraction) -> None:
        nonlocal best_value, best_matching
        if value > best_value or (value == best_value and chosen < best_matching):
            best_value = value
            best_matching = chosen
        for next_index in range(index, len(edges)):
            label, left, right = edges[next_index]
            if left in used or right in used:
                continue
            visit(
                next_index + 1,
                used | {left, right},
                chosen + (label,),
                value + weights[label],
            )

    visit(0, frozenset(), (), Fraction(0))
    return best_value, best_matching


def rho_exhaustive(task: Task, rounded: Mapping[str, Fraction]) -> tuple[Fraction, tuple[str, ...]]:
    errors = {label: abs(task.coefficients[label] - rounded[label]) for label in task.coefficients}
    best = Fraction(0)
    witness: tuple[str, ...] = ()
    for matching in matching_labels(task.edges):
        value = sum((errors[label] for label in matching), Fraction(0))
        if value > best or (value == best and matching < witness):
            best = value
            witness = matching
    return best, witness


def rho_independent(task: Task, rounded: Mapping[str, Fraction]) -> tuple[Fraction, tuple[str, ...]]:
    errors = {label: abs(task.coefficients[label] - rounded[label]) for label in task.coefficients}
    return ordinary_matching_max_weight_recursive(task.edges, errors)


def certify_matching_errors(
    instance: Instance,
    rounded_by_task: Mapping[str, Mapping[str, Fraction]],
    deltas: Mapping[str, Fraction | None] | None = None,
) -> dict[str, object]:
    rows = []
    eta = Fraction(0)
    for task in instance.tasks:
        rho_a, witness_a = rho_exhaustive(task, rounded_by_task[task.name])
        rho_b, witness_b = rho_independent(task, rounded_by_task[task.name])
        if rho_a != rho_b:
            raise AssertionError(f"independent rho mismatch for {task.name}: {rho_a} != {rho_b}")
        nu, nu_matching = ordinary_matching_max_weight_recursive(
            task.edges, {label: Fraction(1) for label in task.coefficients}
        )
        eta += task.weight * rho_a
        delta = None if deltas is None else deltas[task.name]
        corollary_rhs = None if delta is None else Fraction(nu) * delta / 2
        rows.append(
            {
                "task": task.name,
                "rho": rho_a,
                "rho_witness": witness_a,
                "rho_independent_witness": witness_b,
                "nu": nu,
                "nu_matching": nu_matching,
                "delta": delta,
                "corollary_rhs": corollary_rhs,
                "corollary_holds": None if corollary_rhs is None else rho_a <= corollary_rhs,
            }
        )
    return {"eta": eta, "tasks": rows}


def transfer_interval(
    rounded_lower: Fraction | None,
    rounded_upper: Fraction | None,
    eta: Fraction,
    original_incumbent: Fraction | None,
    *,
    rounded_lower_is_global: bool,
) -> dict[str, object]:
    if original_incumbent is None:
        return {
            "lower": None,
            "upper": None,
            "gap": None,
            "certified": False,
            "status": "UNCERTIFIED",
        }
    lower = Fraction(0)
    upper = original_incumbent
    if rounded_lower_is_global and rounded_lower is not None:
        lower = max(Fraction(0), rounded_lower - eta)
        if rounded_upper is not None:
            upper = min(upper, rounded_upper + eta)
    return {
        "lower": lower,
        "upper": upper,
        "gap": upper - lower if rounded_lower_is_global else None,
        "certified": rounded_lower_is_global and lower <= upper,
        "status": "CERTIFIED" if rounded_lower_is_global else "UNCERTIFIED",
    }
