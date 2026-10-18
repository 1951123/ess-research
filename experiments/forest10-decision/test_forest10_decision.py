"""Regression checks for the exact Issue #23 fallback experiment."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "issue23_forest10_decision_runner", SCRIPT_DIR / "run_experiment.py"
)
assert _SPEC is not None and _SPEC.loader is not None
experiment = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(experiment)
_REFERENCE_SPEC = importlib.util.spec_from_file_location(
    "issue23_forest10_decision_reference", SCRIPT_DIR / "verify_reference.py"
)
assert _REFERENCE_SPEC is not None and _REFERENCE_SPEC.loader is not None
reference = importlib.util.module_from_spec(_REFERENCE_SPEC)
_REFERENCE_SPEC.loader.exec_module(reference)


def test_frozen_instance_is_explicitly_model_only() -> None:
    instance = experiment.load_instance(SCRIPT_DIR / "instance.json")
    assert instance["raw"]["status"] == "MODEL_ONLY_SYNTHETIC_PARAMETERS"
    assert instance["raw"]["dataset_identity"]["real_input_available_in_this_worktree"] is False
    assert all(task["source_query_id"] is None for task in instance["tasks"])
    assert len(instance["candidate_ids"]) == 6


def test_shared_order_generates_admissible_maximal_matchings() -> None:
    instance = experiment.load_instance(SCRIPT_DIR / "instance.json")
    selected = frozenset(instance["candidate_ids"])
    order = instance["candidate_ids"]
    for task in instance["tasks"]:
        scheme = experiment.greedy_scheme(instance, task, selected, order)
        active = frozenset(task["eligible"]) & selected
        assert scheme in experiment.maximal_matching_sets(active, instance["endpoints"])


def test_pessimistic_bound_dominates_every_shared_order() -> None:
    instance = experiment.load_instance(SCRIPT_DIR / "instance.json")
    orders = tuple(__import__("itertools").permutations(instance["candidate_ids"]))
    selected = frozenset({"e01", "e12", "e23", "e34"})
    bound, _ = experiment.pess_objective(instance, selected)
    observed = [experiment.ordered_objective(instance, selected, order)[0] for order in orders]
    assert len(orders) == 720
    assert all(value <= bound for value in observed)


def test_exact_joint_objective_matches_external_evaluation() -> None:
    instance = experiment.load_instance(SCRIPT_DIR / "instance.json")
    orders = tuple(__import__("itertools").permutations(instance["candidate_ids"]))
    for selected in (frozenset(), frozenset({"e01", "e23"}), frozenset(instance["candidate_ids"])):
        objective, witnesses = experiment.joint_objective(instance, selected, orders)
        observed = [experiment.ordered_objective(instance, selected, order)[0] for order in orders]
        assert objective == max(observed)
        assert witnesses


def test_runner_has_three_exact_certificates_and_empty_reference(tmp_path: Path) -> None:
    payload = experiment.run(tmp_path, include_execution=False)
    assert len(payload["budgets"]) == 4
    assert payload["metadata"]["raw_record_count"] == 4 * 4 * 720
    for budget in payload["budgets"]:
        for method in ("pess", "nominal", "joint_robust"):
            certificate = budget["method_results"][method]["exact_certificate"]
            assert certificate["status"] == "exact_exhaustive_fraction"
            assert certificate["tie_count"] >= 1
            assert certificate["feasible_subset_count"] <= certificate["all_subset_count"]
        assert budget["method_results"]["empty"]["exact_certificate"]["status"] == "fixed_reference"
        for method in experiment.METHODS:
            item = budget["method_results"][method]
            assert Fraction(item["pessimistic_taskwise_bound"]) >= Fraction(
                item["max_shared_order_loss"]
            )


def test_canonical_outputs_are_byte_stable(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    experiment.run(first, include_execution=False)
    experiment.run(second, include_execution=False)
    for name in (
        "forest10-decision-summary.json",
        "forest10-decision-observations.jsonl.gz",
        "SHA256SUMS",
        "report.md",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_raw_artifact_is_lossless_and_reported_hashes_match(tmp_path: Path) -> None:
    payload = experiment.run(tmp_path, include_execution=False)
    raw_path = tmp_path / "forest10-decision-observations.jsonl.gz"
    records = [json.loads(line) for line in gzip.decompress(raw_path.read_bytes()).splitlines()]
    assert len(records) == payload["metadata"]["raw_record_count"]
    assert all(record["record_type"] == "common_shared_order_observation" for record in records)
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() in (tmp_path / "report.md").read_text()


def test_independent_reference_recomputes_all_objective_certificates(tmp_path: Path) -> None:
    output = tmp_path / "results"
    experiment.run(output, include_execution=False)
    assert reference.verify_summary(
        SCRIPT_DIR / "instance.json", output / "forest10-decision-summary.json"
    ) == 12
