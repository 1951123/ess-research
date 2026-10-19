"""Causally timed anytime controls and PESS-structured local search."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from reference import feasible, maintenance, objective, signed_extrema_objective_bound

CHECKPOINTS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)


@dataclass
class SearchState:
    selected: frozenset[str] | None = None
    value: Fraction | None = None
    details: dict[str, tuple[Fraction, frozenset[str]]] = field(default_factory=dict)
    best_evaluated_selected: frozenset[str] | None = None
    best_evaluated_value: Fraction | None = None
    best_evaluated_details: dict[str, tuple[Fraction, frozenset[str]]] = field(default_factory=dict)
    evaluations: int = 0
    cache_hits: int = 0
    cache_lookups: int = 0
    cache_entries: int = 0
    bound_evaluations: int = 0
    candidate_moves: int = 0
    accepted_moves: int = 0
    late_evaluations: int = 0
    overshoot_seconds: float = 0.0
    timed_out: bool = False
    incumbent_history: list[dict[str, Any]] = field(default_factory=list)


def _elapsed(started: float) -> float:
    return time.perf_counter() - started


def _deadline(started: float, wall_cap: float) -> bool:
    return _elapsed(started) >= wall_cap


def _history_entry(instance: dict[str, Any], selected: frozenset[str], value: Fraction, details: dict[str, tuple[Fraction, frozenset[str]]], completed_elapsed_seconds: float) -> dict[str, Any]:
    return {
        "completed_elapsed_seconds": completed_elapsed_seconds,
        "selected": sorted(selected),
        "maintenance": str(maintenance(instance, selected)),
        "objective": str(value),
        "task_details": {key: {"loss": str(loss), "witness": sorted(witness)} for key, (loss, witness) in details.items()},
        "accepted_by_search": False,
    }


def _consider_evaluated(instance: dict[str, Any], state: SearchState, selected: frozenset[str], value: Fraction, details: dict[str, tuple[Fraction, frozenset[str]]], completed: float) -> dict[str, Any] | None:
    if state.best_evaluated_value is not None and value >= state.best_evaluated_value:
        return None
    state.best_evaluated_selected = selected
    state.best_evaluated_value = value
    state.best_evaluated_details = details
    entry = _history_entry(instance, selected, value, details, completed)
    state.incumbent_history.append(entry)
    return entry


def _adopt_best_evaluated(state: SearchState) -> None:
    if state.best_evaluated_selected is None or state.best_evaluated_value is None:
        return
    state.selected = state.best_evaluated_selected
    state.value = state.best_evaluated_value
    state.details = state.best_evaluated_details


def _trace_from_history(history: list[dict[str, Any]], checkpoints: tuple[float, ...]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for checkpoint in checkpoints:
        available = [item for item in history if item["completed_elapsed_seconds"] <= checkpoint]
        if available:
            incumbent = available[-1]
            trace.append({
                "checkpoint_seconds": checkpoint,
                "available": True,
                "completion_elapsed_seconds": incumbent["completed_elapsed_seconds"],
                "selected": incumbent["selected"],
                "maintenance": incumbent["maintenance"],
                "objective": incumbent["objective"],
                "evaluated_incumbent": True,
            })
        else:
            trace.append({
                "checkpoint_seconds": checkpoint,
                "available": False,
                "completion_elapsed_seconds": None,
                "selected": None,
                "maintenance": None,
                "objective": None,
                "evaluated_incumbent": False,
            })
    return trace


def _evaluate(instance: dict[str, Any], selected: frozenset[str], state: SearchState, cache: dict[frozenset[str], tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]] | None, started: float, wall_cap: float, objective_delay: float) -> tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]], float] | None:
    if _deadline(started, wall_cap):
        state.timed_out = True
        return None
    if cache is not None:
        state.cache_lookups += 1
        cached = cache.get(selected)
        if cached is not None:
            state.cache_hits += 1
            completed = _elapsed(started)
            if completed > wall_cap:
                state.timed_out = True
                state.overshoot_seconds = max(state.overshoot_seconds, completed - wall_cap)
                return None
            return cached[0], cached[1], completed
    if objective_delay > 0:
        time.sleep(objective_delay)
    value, details = objective(instance, selected)
    state.evaluations += 1
    completed = _elapsed(started)
    if completed > wall_cap:
        state.late_evaluations += 1
        state.timed_out = True
        state.overshoot_seconds = max(state.overshoot_seconds, completed - wall_cap)
        return None
    if cache is not None:
        cache[selected] = (value, details)
        state.cache_entries = len(cache)
    return value, details, completed


def _initialize(instance: dict[str, Any], state: SearchState, cache: dict[frozenset[str], tuple[Fraction, dict[str, tuple[Fraction, frozenset[str]]]]] | None, started: float, wall_cap: float, objective_delay: float) -> bool:
    result = _evaluate(instance, frozenset(), state, cache, started, wall_cap, objective_delay)
    if result is None:
        return False
    value, details, completed = result
    state.selected = frozenset()
    state.value = value
    state.details = details
    entry = _consider_evaluated(instance, state, state.selected, value, details, completed)
    assert entry is not None
    entry["accepted_by_search"] = True
    return True


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


def _ordered_neighbors(instance: dict[str, Any], current: frozenset[str], neighbors: list[frozenset[str]], ordering: str, state: SearchState, started: float, wall_cap: float) -> tuple[list[frozenset[str]], bool]:
    if ordering == "lexicographic":
        return neighbors, False
    if ordering != "signed_extrema":
        raise ValueError(ordering)
    current_bound = signed_extrema_objective_bound(instance, current)
    state.bound_evaluations += 1
    scored: list[tuple[Fraction, tuple[str, ...], frozenset[str]]] = []
    for neighbor in neighbors:
        if _deadline(started, wall_cap):
            state.timed_out = True
            state.overshoot_seconds = max(state.overshoot_seconds, _elapsed(started) - wall_cap)
            return [], True
        bound = signed_extrema_objective_bound(instance, neighbor)
        state.bound_evaluations += 1
        scored.append((current_bound - bound, tuple(sorted(neighbor)), neighbor))
    return [item[2] for item in sorted(scored, key=lambda item: (-item[0], item[1]))], False


def _finish(instance: dict[str, Any], state: SearchState, method: str, ordering: str | None, cache_enabled: bool, started: float, wall_cap: float, checkpoints: tuple[float, ...]) -> dict[str, Any]:
    if state.timed_out:
        _adopt_best_evaluated(state)
    elapsed = _elapsed(started)
    return {
        "method_family": "neighborhood" if ordering is not None else "control",
        "method": method,
        "ordering": ordering,
        "cache_enabled": cache_enabled,
        "selected": sorted(state.selected) if state.selected is not None else None,
        "maintenance": str(maintenance(instance, state.selected)) if state.selected is not None else None,
        "objective": str(state.value) if state.value is not None else None,
        "task_details": {key: {"loss": str(loss), "witness": sorted(witness)} for key, (loss, witness) in state.details.items()},
        "termination": "wall-clock cap" if state.timed_out else "completed",
        "wall_seconds": elapsed,
        "wall_cap_seconds": wall_cap,
        "overshoot_seconds": state.overshoot_seconds,
        "incumbent_history": state.incumbent_history,
        "trace": _trace_from_history(state.incumbent_history, checkpoints),
        "metrics": {
            "objective_evaluations": state.evaluations,
            "cache_lookups": state.cache_lookups,
            "cache_hits": state.cache_hits,
            "cache_entries": state.cache_entries,
            "cache_hit_rate": state.cache_hits / state.cache_lookups if state.cache_lookups else 0.0,
            "signed_extrema_bound_evaluations": state.bound_evaluations,
            "candidate_moves_generated": state.candidate_moves,
            "accepted_moves": state.accepted_moves,
            "late_evaluations": state.late_evaluations,
        },
    }


def run_local(instance: dict[str, Any], *, cache_enabled: bool, ordering: str, wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS, objective_delay: float = 0.0) -> dict[str, Any]:
    started = time.perf_counter()
    state = SearchState()
    cache = {} if cache_enabled else None
    if not _initialize(instance, state, cache, started, wall_cap, objective_delay):
        return _finish(instance, state, "neighborhood", ordering, cache_enabled, started, wall_cap, checkpoints)
    while not state.timed_out and state.selected is not None and state.value is not None:
        if _deadline(started, wall_cap):
            state.timed_out = True
            break
        neighbors = _neighbors(instance, state.selected)
        state.candidate_moves += len(neighbors)
        ordered, timed_out = _ordered_neighbors(instance, state.selected, neighbors, ordering, state, started, wall_cap)
        if timed_out:
            break
        improved = False
        for neighbor in ordered:
            result = _evaluate(instance, neighbor, state, cache, started, wall_cap, objective_delay)
            if result is None:
                break
            value, details, completed = result
            if value < state.value:
                state.selected = neighbor
                state.value = value
                state.details = details
                state.accepted_moves += 1
                entry = _consider_evaluated(instance, state, neighbor, value, details, completed)
                assert entry is not None
                entry["accepted_by_search"] = True
                improved = True
                break
        if state.timed_out or not improved:
            break
    return _finish(instance, state, "neighborhood", ordering, cache_enabled, started, wall_cap, checkpoints)


def run_empty(instance: dict[str, Any], wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS, objective_delay: float = 0.0) -> dict[str, Any]:
    started = time.perf_counter()
    state = SearchState()
    _initialize(instance, state, None, started, wall_cap, objective_delay)
    return _finish(instance, state, "empty", None, False, started, wall_cap, checkpoints)


def run_singleton(instance: dict[str, Any], wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS, objective_delay: float = 0.0) -> dict[str, Any]:
    started = time.perf_counter()
    state = SearchState()
    if not _initialize(instance, state, None, started, wall_cap, objective_delay):
        return _finish(instance, state, "singleton", None, False, started, wall_cap, checkpoints)
    for item in sorted(candidate["id"] for candidate in instance["candidates"]):
        if _deadline(started, wall_cap):
            state.timed_out = True
            break
        selected = frozenset({item})
        if not feasible(instance, selected):
            continue
        result = _evaluate(instance, selected, state, None, started, wall_cap, objective_delay)
        if result is None:
            break
        value, details, completed = result
        if state.value is not None and value < state.value:
            state.selected = selected
            state.value = value
            state.details = details
            entry = _consider_evaluated(instance, state, selected, value, details, completed)
            assert entry is not None
            entry["accepted_by_search"] = True
    return _finish(instance, state, "singleton", None, False, started, wall_cap, checkpoints)


def run_greedy(instance: dict[str, Any], wall_cap: float, checkpoints: tuple[float, ...] = CHECKPOINTS, objective_delay: float = 0.0) -> dict[str, Any]:
    started = time.perf_counter()
    state = SearchState()
    if not _initialize(instance, state, None, started, wall_cap, objective_delay):
        return _finish(instance, state, "greedy", None, False, started, wall_cap, checkpoints)
    while not state.timed_out and state.selected is not None and state.value is not None:
        if _deadline(started, wall_cap):
            state.timed_out = True
            break
        best_move: tuple[Fraction, frozenset[str], dict[str, tuple[Fraction, frozenset[str]]], float, dict[str, Any] | None] | None = None
        for item in sorted(candidate["id"] for candidate in instance["candidates"]):
            if item in state.selected:
                continue
            candidate = frozenset(set(state.selected) | {item})
            if not feasible(instance, candidate):
                continue
            result = _evaluate(instance, candidate, state, None, started, wall_cap, objective_delay)
            if result is None:
                break
            candidate_value, candidate_details, completed = result
            entry = _consider_evaluated(instance, state, candidate, candidate_value, candidate_details, completed)
            if candidate_value < state.value and (best_move is None or (candidate_value, tuple(sorted(candidate))) < (best_move[0], tuple(sorted(best_move[1])))):
                best_move = (candidate_value, candidate, candidate_details, completed, entry)
        if state.timed_out or best_move is None:
            break
        value, selected, details, _completed, entry = best_move
        state.selected = selected
        state.value = value
        state.details = details
        state.accepted_moves += 1
        if entry is not None:
            entry["accepted_by_search"] = True
    return _finish(instance, state, "greedy", None, False, started, wall_cap, checkpoints)


def run_method(instance: dict[str, Any], method: str, wall_cap: float, *, checkpoints: tuple[float, ...] = CHECKPOINTS, objective_delay: float = 0.0) -> dict[str, Any]:
    if method == "empty":
        return run_empty(instance, wall_cap, checkpoints, objective_delay)
    if method == "singleton":
        return run_singleton(instance, wall_cap, checkpoints, objective_delay)
    if method == "greedy":
        return run_greedy(instance, wall_cap, checkpoints, objective_delay)
    config = {"basic": (False, "lexicographic"), "cache_only": (True, "lexicographic"), "pess_order": (False, "signed_extrema"), "pess_order_cache": (True, "signed_extrema")}
    if method not in config:
        raise ValueError(method)
    return run_local(instance, cache_enabled=config[method][0], ordering=config[method][1], wall_cap=wall_cap, checkpoints=checkpoints, objective_delay=objective_delay) | {"method": method}
