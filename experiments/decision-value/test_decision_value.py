"""Offline regression tests for the Issue #14 decision experiment."""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_experiment as experiment  # noqa: E402


def test_every_global_order_scheme_is_maximal_and_shared() -> None:
    fixture = experiment.load_instance(SCRIPT_DIR / "instances" / "hand_mixed_hurts.json")
    selected = frozenset(fixture["candidate_ids"])
    order = fixture["candidate_ids"]
    for task in fixture["tasks"]:
        scheme = experiment.greedy_scheme(fixture, task, selected, order)
        active = frozenset(task["eligible"]) & selected
        assert scheme in experiment.maximal_matching_sets(active, fixture["endpoints"])


def test_taskwise_bound_dominates_each_shared_order() -> None:
    fixture = experiment.load_instance(SCRIPT_DIR / "instances" / "hand_mixed_hurts.json")
    selected = frozenset({"e0", "e2"})
    bound, _ = experiment.robust_objective(fixture, selected)
    tested = [
        experiment.ordered_objective(fixture, selected, order)[0]
        for order in __import__("itertools").permutations(fixture["candidate_ids"])
    ]
    assert all(value <= bound for value in tested)


def test_greedy_rejects_nonpositive_gain_and_respects_budget() -> None:
    fixture = experiment.load_instance(SCRIPT_DIR / "instances" / "positive_sign.json")
    selected = experiment.greedy_nominal(fixture, Fraction("2"), fixture["candidate_ids"])
    assert experiment.maintenance(fixture, selected) <= 2
    current = experiment.ordered_objective(fixture, frozenset(), fixture["candidate_ids"])[0]
    proposed = experiment.ordered_objective(fixture, selected, fixture["candidate_ids"])[0]
    assert proposed <= current


def test_runner_preserves_exact_regret_and_feasibility() -> None:
    payload = experiment.run()
    assert len(payload["fixtures"]) == 4
    for fixture in payload["fixtures"]:
        for budget in fixture["budgets"]:
            limit = Fraction(budget["budget"])
            assert budget["method_summary"]["pessimistic"]["all_scenario_regrets_nonnegative"]
            assert budget["method_summary"]["nominal"]["all_scenario_regrets_nonnegative"]
            for observation in budget["scenario_observations"]:
                for method in observation["methods"]:
                    cost = Fraction(method["maintenance_cost"])
                    assert cost <= limit
                    assert Fraction(method["scenario_regret"]) >= 0


def test_fixed_matrix_contains_difference_and_coincidence_controls() -> None:
    payload = experiment.run()
    rows = [row for fixture in payload["fixtures"] for row in fixture["budgets"]]
    assert any(not row["pessimistic_equals_nominal"] for row in rows)
    assert any(row["pessimistic_equals_nominal"] for row in rows)
    assert any(Fraction(row["nominal_price_of_pessimism"]) > 0 for row in rows)


def test_result_is_valid_json_after_runner() -> None:
    experiment.run()
    result = json.loads((SCRIPT_DIR / "results" / "decision-value-results.json").read_text())
    assert result["metadata"]["arithmetic"].startswith("exact Fraction")
