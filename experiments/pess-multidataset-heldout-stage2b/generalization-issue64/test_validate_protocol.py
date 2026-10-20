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

    def test_rejects_legacy_test_reuse(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["cohort_and_independence"]["legacy_arecel_test"] = "reuse old test"
        self.assertTrue(any("legacy test exposure" in e for e in validate(changed)))


if __name__ == "__main__":
    unittest.main()
