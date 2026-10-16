"""Deterministic regression tests for benchmark orchestration."""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from pess_ess.reference import ReferenceResult
from run_suite import measure_reference


def test_reference_timer_surrounds_actual_exhaustive_call() -> None:
    instance = object()
    calls = []
    clock_values = iter((10.0, 10.375))

    def fake_clock() -> float:
        return next(clock_values)

    def fake_solver(received) -> ReferenceResult:
        calls.append(received)
        return ReferenceResult(
            objective=Fraction(7),
            optimal_sets=(frozenset(),),
            evaluated_subsets=1,
            feasible_subsets=1,
        )

    record = measure_reference(
        "timing-regression",
        instance,
        0,
        solver=fake_solver,
        clock=fake_clock,
    )
    assert calls == [instance]
    assert record["runtime_seconds"] == pytest.approx(0.375)
    assert record["evaluated_subsets"] == 1
