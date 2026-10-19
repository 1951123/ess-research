"""Deterministic, explicitly bounded approximate rounded-model selection."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from time import perf_counter
from typing import Mapping

from reference import Instance, OptimizationResult, exact_outer_optimum


@dataclass(frozen=True)
class ApproximationResult:
    engine: str
    complete_global_search: bool
    rounded_value: Fraction | None
    selection: frozenset[str] | None
    states: int
    elapsed_seconds: float
    stop_reason: str | None


def _greedy(
    instance: Instance,
    rounded_by_task: Mapping[str, Mapping[str, Fraction]],
    *,
    time_limit_seconds: float,
    state_cap: int,
) -> ApproximationResult:
    start = perf_counter()
    selected: frozenset[str] = frozenset()
    value = instance.objective(selected, rounded_by_task)
    states = 1
    stop_reason: str | None = None
    while True:
        if perf_counter() - start >= time_limit_seconds:
            stop_reason = "TIMEOUT"
            break
        if states >= state_cap:
            stop_reason = "STATE_CAP"
            break
        candidates = []
        for label in instance.resources:
            if label in selected:
                continue
            candidate = frozenset(set(selected) | {label})
            if not instance.feasible(candidate):
                continue
            candidate_value = instance.objective(candidate, rounded_by_task)
            candidates.append((candidate_value, tuple(sorted(candidate)), candidate))
        if not candidates:
            stop_reason = "NO_FEASIBLE_EXTENSION"
            break
        candidates.sort(key=lambda row: (row[0], row[1]))
        candidate_value, _, candidate = candidates[0]
        states += 1
        if candidate_value >= value:
            stop_reason = "LOCAL_MINIMUM"
            break
        selected, value = candidate, candidate_value
    return ApproximationResult(
        engine="deterministic_greedy",
        complete_global_search=False,
        rounded_value=value,
        selection=selected,
        states=states,
        elapsed_seconds=perf_counter() - start,
        stop_reason=stop_reason,
    )


def solve_rounded(
    instance: Instance,
    rounded_by_task: Mapping[str, Mapping[str, Fraction]],
    *,
    exact_tiny: bool,
    time_limit_seconds: float,
    state_cap: int,
) -> ApproximationResult:
    if exact_tiny:
        result: OptimizationResult = exact_outer_optimum(
            instance,
            rounded_by_task,
            time_limit_seconds=time_limit_seconds,
            state_cap=state_cap,
        )
        return ApproximationResult(
            engine="exhaustive_rounded_tiny",
            complete_global_search=result.complete,
            rounded_value=result.best_value,
            selection=result.best_selection,
            states=result.states,
            elapsed_seconds=result.elapsed_seconds,
            stop_reason=result.stop_reason,
        )
    return _greedy(
        instance,
        rounded_by_task,
        time_limit_seconds=time_limit_seconds,
        state_cap=state_cap,
    )
