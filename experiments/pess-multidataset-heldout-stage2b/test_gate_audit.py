"""Offline checks for the Stage 2B protocol and recorded Gate A audit."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


HERE = Path(__file__).parent


class Stage2BProtocolTests(unittest.TestCase):
    def test_protocol_is_outcome_free_and_declares_scope(self) -> None:
        protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "FROZEN_BEFORE_GATE_A_OR_OUTCOME_COLLECTION")
        self.assertEqual(protocol["dataset_gate"]["required_pass_count"], 2)
        self.assertEqual(protocol["selection_and_model"]["budgets"], [0, 2, 3, 5])
        self.assertEqual(set(protocol["selection_and_model"]["methods"]), {"Empty", "PESS", "Nominal", "Joint-Robust"})
        self.assertNotIn("e05", {candidate["id"] for candidate in protocol["datasets"]["forest10"]["candidates"]})

    def test_gate_a_report_preserves_blocker(self) -> None:
        report_path = HERE / "runs/gate-a-20261020-v4/gate-audit.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        statuses = {item["dataset"]: item["status"] for item in report["datasets"]}
        self.assertEqual(report["overall_status"], "BLOCKED")
        self.assertEqual(statuses, {"forest10": "AVAILABLE", "census13": "MISSING", "dmv11": "MISSING", "power7": "MISSING"})
        self.assertEqual(report["postgresql_source"]["status"], "AVAILABLE")
        self.assertEqual(report["issue_runtime_root"]["status"], "BLOCKED")
        forest = next(item for item in report["datasets"] if item["dataset"] == "forest10")
        self.assertTrue(forest["checks"]["hashes_match"])
        self.assertTrue(forest["checks"]["canonical"]["split_counts_match"])


if __name__ == "__main__":
    unittest.main()
