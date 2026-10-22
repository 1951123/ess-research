"""Unit tests for static Phase 0 protocol checks; no data/outcomes are loaded."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_protocol import PROTOCOL, validate


class ProtocolValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def test_checked_in_protocol_passes(self) -> None:
        self.assertEqual(validate(self.document), [])

    def test_rejects_permission_for_heldout_measurements(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["authorization"]["new_postgresql_heldout_measurements"] = True
        self.assertTrue(any("new_postgresql_heldout_measurements" in e for e in validate(changed)))

    def test_rejects_reading_test_outcomes_for_design(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["authorization"]["test_truth_or_test_estimates_read_for_design"] = True
        self.assertTrue(any("test_truth_or_test_estimates_read_for_design" in e for e in validate(changed)))

    def test_rejects_budget_or_metric_drift(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["calibration_and_selection"]["resource_budget"]["budgets"] = [0, 1, 2]
        self.assertTrue(any("budgets" in e for e in validate(changed)))
        changed = copy.deepcopy(self.document)
        changed["metrics"]["primary"]["formula"] = "raw q-error"
        self.assertTrue(any("Q1 floor formula" in e for e in validate(changed)))

    def test_rejects_unpinned_candidate_universe(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["candidate_universe"]["source_protocol_sha256"] = "0" * 64
        self.assertTrue(any("Issue #59 protocol hash" in e for e in validate(changed)))

    def test_rejects_legacy_test_reuse(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["cohort_and_independence"]["legacy_arecel_test"] = "reuse old test"
        self.assertTrue(any("legacy test exposure" in e for e in validate(changed)))

    def test_rejects_mismatched_pairwise_estimand(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["metrics"]["primary"]["contrast"] = "arithmetic mean Q1 only"
        self.assertTrue(any("paired estimand" in e for e in validate(changed)))

    def test_rejects_unbounded_query_plan_design(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["prospective_caps"]["queries_per_group"] = 2
        self.assertTrue(any("query/group ratio" in e for e in validate(changed)))
        changed = copy.deepcopy(self.document)
        changed["prospective_caps"]["max_count_query_plans"] += 1
        self.assertTrue(any("query-plan hard cap" in e for e in validate(changed)))

    def test_rejects_missing_sample_or_trace_boundary(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["postgresql_physical_evaluation"]["sample_block_definition"] = ""
        self.assertTrue(any("sample-block" in e for e in validate(changed)))
        changed = copy.deepcopy(self.document)
        changed["postgresql_physical_evaluation"]["coverage"] = "trace missing means drop query"
        self.assertTrue(any("trace completeness" in e for e in validate(changed)))

    def test_rejects_physical_cost_claim_or_missing_history_gate(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["calibration_and_selection"]["resource_budget"]["meaning"] = "physical cost"
        self.assertTrue(any("count-based" in e for e in validate(changed)))
        changed = copy.deepcopy(self.document)
        changed["cohort_generation_recipe"]["historical_fingerprint_gate"]["coverage_required"] = []
        self.assertTrue(any("historical fingerprint coverage" in e for e in validate(changed)))

    def test_rejects_schema_infeasible_or_underfilled_predicate_quotas(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["cohort_generation_recipe"]["selection_and_size"]["schema_capacity_gate"]["quota_by_dataset_split"]["dmv11"]["calibration"]["1"] = 200
        self.assertTrue(any("predicate-bin quotas must sum" in e for e in validate(changed)))
        changed = copy.deepcopy(self.document)
        changed["cohort_generation_recipe"]["selection_and_size"]["schema_capacity_gate"]["source_pins"] = {}
        self.assertTrue(any("source pins" in e for e in validate(changed)))


if __name__ == "__main__":
    unittest.main()
