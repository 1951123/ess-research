"""Correctness regressions for the Stage 2C no-op and existing cache paths."""

from __future__ import annotations

import os
from fractions import Fraction
from pathlib import Path

import pytest
from evidence_io import write_text_exclusive
from independent_reference import maximal_matchings, objective
from pess_ess import solvers_v2
from pess_ess.model import Candidate, Instance, Task, read_instance
from pess_ess.solvers_v2 import MasterOracleOptions, solve_master_oracle
from profile_noop import canonical_call

ROOT = Path(__file__).resolve().parent
TINY = ROOT / "inputs" / "independent"
TINY_CASES = (
    TINY / "path_signed_cancel_4901.json",
    ROOT / "inputs" / "original-stage1b" / "small_star_single_3901.json",
    ROOT / "inputs" / "original-stage1b" / "small_sharing_cycle_3904.json",
)


def make_instance(alpha: str, correction: str, *, parallel: bool = False) -> Instance:
    candidates = [
        Candidate("e0", "t0", ("a", "b"), Fraction(1)),
        Candidate("e1", "t0", ("b", "c"), Fraction(0)),
    ]
    if parallel:
        candidates.append(Candidate("e2", "t0", ("a", "b"), Fraction(1)))
        eligible = ("e0", "e1", "e2")
        corrections = {"e0": Fraction(correction), "e1": Fraction(0), "e2": Fraction(correction)}
    else:
        eligible = ("e0", "e1")
        corrections = {"e0": Fraction(correction), "e1": Fraction(0)}
    return Instance(
        candidates=tuple(candidates),
        tasks=(Task("i0", "t0", Fraction(1), Fraction(alpha), eligible, corrections),),
        budget=Fraction(2),
    )


def test_empty_selection_and_changed_maximality() -> None:
    instance = make_instance("2", "-2")
    task = instance.tasks[0]
    assert maximal_matchings(frozenset(), task, instance) == (frozenset(),)
    assert maximal_matchings(frozenset({"e0"}), task, instance) == (frozenset({"e0"}),)
    assert maximal_matchings(frozenset({"e0", "e1"}), task, instance) == (frozenset({"e0"}), frozenset({"e1"}))


def test_signed_cancellation_equal_extrema_parallel_and_zero_cost() -> None:
    instance = make_instance("-2", "2", parallel=True)
    task = instance.tasks[0]
    matchings = maximal_matchings(frozenset({"e0", "e1", "e2"}), task, instance)
    assert frozenset({"e0"}) in matchings and frozenset({"e2"}) in matchings
    value, details = objective(instance, frozenset({"e0", "e1", "e2"}))
    assert value == Fraction(2)
    assert details["i0"][1] in matchings
    assert instance.candidate_map["e1"].maintenance_cost == 0


def test_naive_task_subset_key_collision_is_not_full_key_equivalence() -> None:
    first = make_instance("1", "1")
    second = make_instance("3", "-2")
    selected = frozenset({"e0"})
    assert ("i0", frozenset({"e0"})) == ("i0", frozenset({"e0"}))
    first_key = canonical_call(first, first.tasks[0], selected, {"time_limit": 5.0, "certification_tolerance": 0.0, "reuse_bounds": False, "deadline": 10.0, "clock": __import__("time").perf_counter})
    second_key = canonical_call(second, second.tasks[0], selected, {"time_limit": 5.0, "certification_tolerance": 0.0, "reuse_bounds": False, "deadline": 10.0, "clock": __import__("time").perf_counter})
    assert first_key != second_key
    assert objective(first, selected)[0] != objective(second, selected)[0]


def test_cache_on_off_preserves_original_objective_on_tiny_inputs() -> None:
    for path in TINY_CASES:
        instance = read_instance(path)
        uncached = solve_master_oracle(
            instance,
            total_time_limit=5.0,
            inner_time_limit=5.0,
            certification_tolerance=0.0,
            cut_tolerance=1e-6,
            options=MasterOracleOptions(task_local_cache=False),
        )
        cached = solve_master_oracle(
            instance,
            total_time_limit=5.0,
            inner_time_limit=5.0,
            certification_tolerance=0.0,
            cut_tolerance=1e-6,
            options=MasterOracleOptions(task_local_cache=True),
        )
        assert uncached.validated_feasible and cached.validated_feasible, path
        uncached_value, _ = objective(instance, uncached.selected)
        cached_value, _ = objective(instance, cached.selected)
        assert uncached.objective == uncached_value
        assert cached.objective == cached_value
        assert uncached_value == cached_value


def test_noop_wrapper_delegates_same_semantics() -> None:
    path = min(TINY.glob("*.json"))
    instance = read_instance(path)
    direct = solve_master_oracle(
        instance,
        total_time_limit=5.0,
        inner_time_limit=5.0,
        certification_tolerance=0.0,
        cut_tolerance=1e-6,
        options=MasterOracleOptions(),
    )
    original = solvers_v2.evaluate_task
    calls = 0

    def no_op(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    solvers_v2.evaluate_task = no_op
    try:
        wrapped = solve_master_oracle(
            instance,
            total_time_limit=5.0,
            inner_time_limit=5.0,
            certification_tolerance=0.0,
            cut_tolerance=1e-6,
            options=MasterOracleOptions(),
        )
    finally:
        solvers_v2.evaluate_task = original
    assert calls > 0
    assert wrapped.validated_feasible and direct.validated_feasible
    assert wrapped.objective == direct.objective


def test_evidence_writer_refuses_existing_files_and_symlinks(tmp_path: Path) -> None:
    existing = tmp_path / "existing.txt"
    existing.write_text("old", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_text_exclusive(existing, "new")
    assert existing.read_text(encoding="utf-8") == "old"

    target = tmp_path / "target.txt"
    link = tmp_path / "link.txt"
    target.write_text("target", encoding="utf-8")
    os.symlink(target, link)
    with pytest.raises(FileExistsError):
        write_text_exclusive(link, "new")
    assert target.read_text(encoding="utf-8") == "target"
