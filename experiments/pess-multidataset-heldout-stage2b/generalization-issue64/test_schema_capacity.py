"""Schema-only combinatorial feasibility tests; no rows or outcomes are read."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from schema_capacity import (
    ARECEL_GENERATOR_PIN,
    GRAPH_CLASSES,
    FAMILIES,
    capacity_table,
    revised_predicate_quota,
    verify_schema_source_pins,
)
from build_schema_capacity_report import build_report


HERE = Path(__file__).parent
ROOT = HERE.parents[2]
PROTOCOL = json.loads((HERE / "protocol-v1.json").read_text(encoding="utf-8"))
EXPECTED_LOW_BIN_SPLITS = {
    "forest10": {"1": {"calibration": 31, "heldout": 29}, "2": {"calibration": 774, "heldout": 846}},
    "census13": {"1": {"calibration": 14, "heldout": 24}, "2": {"calibration": 303, "heldout": 325}},
    "dmv11": {"1": {"calibration": 5, "heldout": 11}, "2": {"calibration": 60, "heldout": 45}},
    "power7": {"1": {"calibration": 19, "heldout": 23}, "2": {"calibration": 379, "heldout": 377}},
}
EXPECTED_QUOTAS = {
    "forest10": {"calibration": {"1": 0, "2": 200, "3-4": 267, "5-7": 267, "8-10": 266},
                 "heldout": {"1": 0, "2": 200, "3-4": 267, "5-7": 267, "8-10": 266}},
    "census13": {"calibration": {"1": 0, "2": 151, "3-4": 283, "5-7": 283, "8-13": 283},
                 "heldout": {"1": 0, "2": 162, "3-4": 280, "5-7": 279, "8-13": 279}},
    "dmv11": {"calibration": {"1": 0, "2": 30, "3-4": 324, "5-7": 323, "8-11": 323},
              "heldout": {"1": 0, "2": 22, "3-4": 326, "5-7": 326, "8-11": 326}},
    "power7": {"calibration": {"1": 0, "2": 189, "3-4": 406, "5-7": 405},
               "heldout": {"1": 0, "2": 188, "3-4": 406, "5-7": 406}},
}


class SchemaCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = {
            dataset: capacity_table(dataset, PROTOCOL["candidate_universe"][dataset])
            for dataset in EXPECTED_QUOTAS
        }

    def test_schema_operator_and_candidate_sources_are_hash_pinned(self) -> None:
        verify_schema_source_pins(ROOT)
        self.assertEqual(ARECEL_GENERATOR_PIN["commit"], "aa52da7768023270bad884232972e0b77ec6534a")
        self.assertEqual(ARECEL_GENERATOR_PIN["git_blob_sha"], "72b2123a70922abc91a3d4d8455b44bb81f4223c")

    def test_checked_in_capacity_evidence_matches_schema_enumerator(self) -> None:
        frozen = json.loads((HERE / "schema-capacity-report-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(frozen, build_report())
        prior = json.loads((HERE / "schema-capacity-report.json").read_text(encoding="utf-8"))
        self.assertEqual(prior["format"], "issue64-schema-capacity-report-v1")
        self.assertIn("frozen_split_quota", prior["datasets"]["dmv11"])

    def test_exact_low_bin_split_capacities_match_frozen_hash_split(self) -> None:
        for dataset, expected in EXPECTED_LOW_BIN_SPLITS.items():
            low = self.tables[dataset]["low_predicate_exact_template_capacity_by_split"]
            self.assertEqual(low, expected)
            self.assertEqual(sum(low["2"].values()), self.tables[dataset]["predicate_bin_capacity_upper_bound"]["2"])

    def test_joint_stratum_capacity_marginals_conserve_bin_capacity(self) -> None:
        for table in self.tables.values():
            for bin_name, total in table["predicate_bin_capacity_upper_bound"].items():
                joint_total = sum(
                    table["joint_bin_operator_graph_capacity_upper_bound"][f"{bin_name}|{family}|{graph}"]
                    for family in FAMILIES for graph in GRAPH_CLASSES
                )
                self.assertEqual(joint_total, total)
            self.assertTrue(all(value == 0 for key, value in table["graph_class_capacity_upper_bound"].items()
                                if key.endswith("|conflict-one-maximal-matching")))

    def test_attainable_quotas_fit_both_disjoint_splits(self) -> None:
        for dataset, table in self.tables.items():
            quotas = revised_predicate_quota(table)
            self.assertEqual(quotas, EXPECTED_QUOTAS[dataset])
            for split_quotas in quotas.values():
                self.assertEqual(sum(split_quotas.values()), 1000)
                self.assertEqual(split_quotas["1"], 0)
                self.assertGreaterEqual(sum(v for b, v in split_quotas.items() if b not in ("1", "2")), 500)
            for split in ("calibration", "heldout"):
                self.assertLessEqual(
                    quotas[split]["2"],
                    table["low_predicate_exact_template_capacity_by_split"]["2"][split] // 2,
                )
            for bin_name, capacity in table["predicate_bin_capacity_upper_bound"].items():
                self.assertLessEqual(sum(quotas[split][bin_name] for split in quotas), capacity)

    def test_singleton_headroom_and_quarantine_are_not_misrepresented_as_run(self) -> None:
        recipe = PROTOCOL["cohort_generation_recipe"]
        gate = recipe["selection_and_size"]["schema_capacity_gate"]
        self.assertTrue(gate["quota_status"].startswith("PROVISIONAL_SCHEMA_ONLY_TARGETS_NOT_FINAL"))
        self.assertIn("BLOCKED_INCOMPLETE_HISTORICAL_FINGERPRINT_LEDGER", recipe["historical_fingerprint_gate"]["phase0_check_result"])
        self.assertIn("No complete historical fingerprint ledger", recipe["selection_and_size"]["implementation"])

    def test_candidate_endpoint_outside_pinned_schema_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            capacity_table("forest10", ["bad:unknown/Aspect"])


if __name__ == "__main__":
    unittest.main()
