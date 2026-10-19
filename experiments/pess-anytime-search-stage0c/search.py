"""Bounded anytime controls, neighborhood search, and the v1 PESS treatment."""

from __future__ import annotations

import time
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable

from reference import (
    feasible,
    frac,
    maintenance,
    objective,
    signed_extrema_objective_bound,
)


CHECKPOINTS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)


@dataclass
class SearchState:
    selected: frozenset[str]
    value: Fraction
    details: dict[str, tuple[Fraction, frozenset[str]]]
    evaluations: int = 0
    cache_hits: int = 0
    cache_lookups: int = 0
    cache_entries: int = 0
    bound_evaluations: int = 0
    candidate_moves: int = 0
    accepted_moves: int = 0
    preprocessing_seconds: float = 0.0


def _record_checkpoint(trace: list[dict[str, Any]], state: SearchState, elapsed: float, checkpoint: float) -> None:
    trace.append({
        "checkpoint_seconds": checkpoint,
        "observed_elapsed_seconds": elapsed,
        "selected": sorted(state.selected),
        "maintenance": str(state.value * 0 + maintenance(_CURRENT_INSTANCE, state.selected)),
        "objective": str(state.value),
        "evaluated_incumbent": True,
    })


_CURRENT_INSTANCE: dict[str, Any]


def _neighbors(instance: dict[str, Any], selected: frozenset[str]) -> list[frozenset[str]]:
    ids = tuple(sorted(item["id"] for item in instance["candidates"]))
    candidates: set[frozenset[str]] = set()
    for item in ids:
        if item not in selected:
            candidate = frozenset(set(selected) | {item})
            if feasible(instance, candidate):
                candidates.add(candidate)
    for item in selected:
        candidate = frozenset(set(selected) - {item})
        if feasible(instance, candidate):
            candidates.add(candidate)
    for removed in selected:
        for added in ids:
            if added in selected:
                continue
            candidate = frozenset((set(selected) - {removed}) | {added})
            if feasible(instance, candidate):
                candidates.add(candidate)
    return sorted(candidates, key=lambda value: tuple(sorted(value)))


def _evaluate(instance: dict[str, Any], selected: frozenset[str], state: SearchState, cache: dict[frozenset[str], tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]] | None) -> tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]:
    if cache is not None:
        state.cache_lookups += 1
        cached = cache.get(selected)
        if cached is not None:
            state.cache_hits += 1
            return cached
    value, details = objective(instance, selected)
    state.evaluations += 1
    if cache is not None:
        cache[selected] = (value, details)
        state.cache_entries = len(cache)
    return value, details


def _ordered_neighbors(instance: dict[str, Any], current: frozenset[str], neighbors: list[frozenset[str]], ordering: str, state: SearchState) -> list[frozenset[str]]:
    if ordering == "lexicographic":
        return neighbors
    if ordering != "signed_extrema":
        raise ValueError(ordering)
    current_bound = signed_extrema_objective_bound(instance, current)
    state.bound_evaluations += 1
    scored: list[tuple[Fraction, tuple[str, ...], frozenset[str]]] = []
    for neighbor in neighbors:
        bound = signed_extrema_objective_bound(instance, neighbor)
        state.bound_evaluations += 1
        scored.append((current_bound - bound, tuple(sorted(neighbor)), neighbor))
    return [item[2] for item in sorted(scored, key=lambda item: (-item[0], item[1]))]


def run_local(instance: dict[str, Any], *, cache_enabled: bool, ordering: str, wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS) -> dict[str, Any]:
    global _CURRENT_INSTANCE
    _CURRENT_INSTANCE = instance
    started = time.perf_counter()
    cache = {} if cache_enabled else None
    initial = frozenset()
    state = SearchState(initial, Fraction(), {})
    value, details = _evaluate(instance, initial, state, cache)
    state.value = value
    state.details = details
    trace: list[dict[str, Any]] = []
    next_checkpoint = 0
    terminated = "local optimum"
    while True:
        elapsed = time.perf_counter() - started
        while next_checkpoint < len(checkpoints) and elapsed >= checkpoints[next_checkpoint]:
            _record_checkpoint(trace, state, elapsed, checkpoints[next_checkpoint])
            next_checkpoint += 1
        if elapsed >= wall_cap:
            terminated = "wall-clock cap"
            break
        neighbors = _neighbors(instance, state.selected)
        state.candidate_moves += len(neighbors)
        ordered = _ordered_neighbors(instance, state.selected, neighbors, ordering, state)
        improved = False
        for neighbor in ordered:
            if time.perf_counter() - started >= wall_cap:
                terminated = "wall-clock cap"
                break
            candidate_value, candidate_details = _evaluate(instance, neighbor, state, cache)
            if candidate_value < state.value:
                state.selected = neighbor
                state.value = candidate_value
                state.details = candidate_details
                state.accepted_moves += 1
                improved = True
                break
        if terminated == "wall-clock cap":
            break
        if not improved:
            break
    elapsed = time.perf_counter() - started
    while next_checkpoint < len(checkpoints):
        _record_checkpoint(trace, state, elapsed, checkpoints[next_checkpoint])
        next_checkpoint += 1
    return {
        "method_family": "neighborhood",
        "ordering": ordering,
        "cache_enabled": cache_enabled,
        "selected": sorted(state.selected),
        "maintenance": str(maintenance(instance, state.selected)),
        "objective": str(state.value),
        "task_details": {key: {"loss": str(val), "witness": sorted(wit)} for key, (val, wit) in state.details.items()},
        "termination": terminated,
        "wall_seconds": elapsed,
        "trace": trace,
        "metrics": {
            "objective_evaluations": state.evaluations,
            "cache_lookups": state.cache_lookups,
            "cache_hits": state.cache_hits,
            "cache_entries": state.cache_entries,
            "cache_hit_rate": state.cache_hits / state.cache_lookups if state.cache_lookups else 0.0,
            "signed_extrema_bound_evaluations": state.bound_evaluations,
            "candidate_moves_generated": state.candidate_moves,
            "accepted_moves": state.accepted_moves,
            "preprocessing_seconds": state.preprocessing_seconds,
        },
    }


def run_empty(instance: dict[str, Any], wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS) -> dict[str, Any]:
    selected = frozenset()
    value, details = objective(instance, selected)
    return _control_record(instance, "empty", selected, value, details, 1, 0, wall_cap, checkpoints)


def run_singleton(instance: dict[str, Any], wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS) -> dict[str, Any]:
    ids = tuple(sorted(item["id"] for item in instance["candidates"]))
    evaluations = 0
    best = frozenset()
    best_value, best_details = objective(instance, best)
    evaluations += 1
    for item in ids:
        selected = frozenset({item})
        if not feasible(instance, selected):
            continue
        value, details = objective(instance, selected)
        evaluations += 1
        if value < best_value:
            best, best_value, best_details = selected, value, details
    return _control_record(instance, "singleton", best, best_value, best_details, evaluations, 0, wall_cap, checkpoints)


def run_greedy(instance: dict[str, Any], wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS) -> dict[str, Any]:
    started = time.perf_counter()
    selected = frozenset()
    value, details = objective(instance, selected)
    evaluations = 1
    accepted = 0
    while time.perf_counter() - started < wall_cap:
        best_move: tuple[Fraction, frozenset[str], dict[str, tuple[Fraction, frozenset[str]]]] | None = None
        for item in sorted(candidate["id"] for candidate in instance["candidates"]):
            if item in selected:
                continue
            candidate = frozenset(set(selected) | {item})
            if not feasible(instance, candidate):
                continue
            candidate_value, candidate_details = objective(instance, candidate)
            evaluations += 1
            if candidate_value < value and (best_move is None or (candidate_value, tuple(sorted(candidate))) < (best_move[0], tuple(sorted(best_move[1])))):
                best_move = (candidate_value, candidate, candidate_details)
        if best_move is None:
            break
        value, selected, details = best_move
        accepted += 1
    elapsed = time.perf_counter() - started
    return _control_record(instance, "greedy", selected, value, details, evaluations, accepted, wall_cap, checkpoints, elapsed)


def _control_record(instance: dict[str, Any], name: str, selected: frozenset[str], value: Fraction, details: dict[str, tuple[Fraction, frozenset[str]]], evaluations: int, accepted: int, wall_cap: float, checkpoints: tuple[float, ...], elapsed: float | None = None) -> dict[str, Any]:
    elapsed = elapsed if elapsed is not None else min(wall_cap, 0.0)
    trace = [{
        "checkpoint_seconds": checkpoint,
        "observed_elapsed_seconds": elapsed,
        "selected": sorted(selected),
        "maintenance": str(maintenance(instance, selected)),
        "objective": str(value),
        "evaluated_incumbent": True,
    } for checkpoint in checkpoints]
    return {
        "method_family": "control",
        "method": name,
        "selected": sorted(selected),
        "maintenance": str(maintenance(instance, selected)),
        "objective": str(value),
        "task_details": {key: {"loss": str(val), "witness": sorted(wit)} for key, (val, wit) in details.items()},
        "termination": "completed",
        "wall_seconds": elapsed,
        "trace": trace,
        "metrics": {"objective_evaluations": evaluations, "accepted_moves": accepted, "cache_lookups": 0, "cache_hits": 0, "cache_entries": 0, "cache_hit_rate": 0.0, "signed_extrema_bound_evaluations": 0, "candidate_moves_generated": evaluations - 1, "preprocessing_seconds": 0.0},
    }


def run_method(instance: dict[str, Any], method: str, wall_cap: float) -> dict[str, Any]:
    if method == "empty":
        return run_empty(instance, wall_cap)
    if method == "singleton":
        return run_singleton(instance, wall_cap)
    if method == "greedy":
        return run_greedy(instance, wall_cap)
    config = {
        "basic": (False, "lexicographic"),
        "cache_only": (True, "lexicographic"),
        "pess_order": (False, "signed_extrema"),
        "pess_order_cache": (True, "signed_extrema"),
    }
    if method not in config:
        raise ValueError(method)
    row = run_local(instance, cache_enabled=config[method][0], ordering=config[method][1], wall_cap=wall_cap)
    row["method"] = method
    return row
