"""Offline regression tests for the Issue #14 decision experiment."""

from __future__ import annotations

import json
import gzip
import hashlib
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


def test_runner_preserves_exact_regret_and_feasibility(tmp_path: Path) -> None:
    payload = experiment.run(tmp_path, report_path=tmp_path / "report.md", include_runtime=False)
    assert len(payload["fixtures"]) == 5
    raw = gzip.decompress((tmp_path / "decision-value-observations.jsonl.gz").read_bytes())
    observations = [json.loads(line) for line in raw.splitlines()]
    assert len(observations) == payload["metadata"]["raw_record_count"]
    assert observations
    for observation in observations:
        if observation["record_type"] != "shared_order_observation":
            continue
        limit = Fraction(next(
            budget["budget"]
            for fixture in payload["fixtures"]
            if fixture["instance_id"] == observation["fixture_id"]
            for budget in fixture["budgets"]
            if budget["budget"] == observation["budget"]
        ))
        for method in observation["methods"]:
            cost = Fraction(method["maintenance_cost"])
            assert cost <= limit
            assert Fraction(method["scenario_regret"]) >= 0
    for fixture in payload["fixtures"]:
        for budget in fixture["budgets"]:
            assert budget["method_summary"]["pessimistic"]["all_scenario_regrets_nonnegative"]
            assert budget["method_summary"]["nominal"]["all_scenario_regrets_nonnegative"]


def test_fixed_matrix_contains_difference_and_coincidence_controls(tmp_path: Path) -> None:
    payload = experiment.run(tmp_path, report_path=tmp_path / "report.md", include_runtime=False)
    rows = [row for fixture in payload["fixtures"] for row in fixture["budgets"]]
    assert any(not row["pessimistic_equals_nominal"] for row in rows)
    assert any(row["pessimistic_equals_nominal"] for row in rows)
    assert any(Fraction(row["nominal_price_of_pessimism"]) > 0 for row in rows)


def test_conflict_probe_has_positive_shared_order_gap(tmp_path: Path) -> None:
    payload = experiment.run(tmp_path, report_path=tmp_path / "report.md", include_runtime=False)
    probe_fixture = next(item for item in payload["fixtures"] if item["instance_id"] == "conflict_shared_order")
    probe = probe_fixture["conflict_probe"]
    assert probe["independent_taskwise_bound"] == "5"
    assert probe["max_shared_order_loss"] == "4"
    assert probe["gap"] == "1"
    assert probe["no_shared_order_realizes_all_taskwise_witnesses"]


def test_canonical_outputs_are_byte_stable(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    experiment.run(first, report_path=first / "report.md", include_runtime=False)
    experiment.run(second, report_path=second / "report.md", include_runtime=False)
    for name in (
        "decision-value-summary.json",
        "decision-value-observations.jsonl.gz",
        "SHA256SUMS",
        "report.md",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_report_records_canonical_artifact_hashes(tmp_path: Path) -> None:
    experiment.run(tmp_path, report_path=tmp_path / "report.md", include_runtime=False)
    report = (tmp_path / "report.md").read_text()
    for name in ("decision-value-summary.json", "decision-value-observations.jsonl.gz"):
        digest = hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
        assert digest in report
