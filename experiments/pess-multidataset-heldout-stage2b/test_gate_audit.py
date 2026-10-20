"""Offline checks for the Stage 2B protocol and recorded Gate A audit."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from gate_audit import compute_overall_status, runtime_validation, write_exclusive_json


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
        report_path = HERE / "runs/gate-a-20261020-v7/gate-audit.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        statuses = {item["dataset"]: item["status"] for item in report["datasets"]}
        self.assertEqual(report["overall_status"], "BLOCKED")
        self.assertEqual(statuses, {"forest10": "INPUT_AVAILABLE", "census13": "MISSING", "dmv11": "MISSING", "power7": "MISSING"})
        self.assertEqual(report["postgresql_source"]["status"], "SOURCE_MARKERS_PRESENT")
        self.assertEqual(report["runtime_validation"]["validator_status"], "NOT_IMPLEMENTED_BLOCKED")
        self.assertEqual(report["runtime_validation"]["issue_cluster_ready"]["status"], "BLOCKED")
        forest = next(item for item in report["datasets"] if item["dataset"] == "forest10")
        self.assertTrue(forest["checks"]["hashes_match"])
        self.assertTrue(forest["checks"]["canonical"]["split_counts_match"])

    def test_two_inputs_and_empty_runtime_cannot_pass(self) -> None:
        datasets = [{"status": "INPUT_AVAILABLE"}, {"status": "INPUT_AVAILABLE"}]
        runtime = runtime_validation(None, None, None, Path(tempfile.gettempdir()))
        self.assertEqual(compute_overall_status(datasets, {"status": "SOURCE_MARKERS_PRESENT"}, runtime), "BLOCKED")
        self.assertEqual(runtime["runtime_root_presence"]["status"], "PRESENT")
        self.assertEqual(runtime["fixed_sample_manifest_verified"]["status"], "BLOCKED")

    def test_output_is_exclusive_and_refuses_dangling_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "result.json"
            write_exclusive_json(output, {"value": 1})
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                write_exclusive_json(output, {"value": 2})
            self.assertEqual(output.read_bytes(), original)

            dangling = root / "dangling.json"
            os.symlink(root / "missing-target.json", dangling)
            with self.assertRaises(FileExistsError):
                write_exclusive_json(dangling, {"value": 3})
            self.assertTrue(dangling.is_symlink())


if __name__ == "__main__":
    unittest.main()
