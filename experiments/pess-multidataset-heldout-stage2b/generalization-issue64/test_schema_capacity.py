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
    "forest10": {"calibration": {"1": 31, "2": 200, "3-4": 257, "5-7": 256, "8-10": 256},
                 "heldout": {"1": 29, "2": 200, "3-4": 257, "5-7": 257, "8-10": 257}},
    "census13": {"calibration": {"1": 14, "2": 200, "3-4": 262, "5-7": 262, "8-13": 262},
                 "heldout": {"1": 24, "2": 200, "3-4": 259, "5-7": 259, "8-13": 258}},
    "dmv11": {"calibration": {"1": 5, "2": 60, "3-4": 312, "5-7": 312, "8-11": 311},
              "heldout": {"1": 11, "2": 45, "3-4": 315, "5-7": 315, "8-11": 314}},
    "power7": {"calibration": {"1": 19, "2": 250, "3-4": 366, "5-7": 365},
               "heldout": {"1": 23, "2": 250, "3-4": 364, "5-7": 363}},
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
        frozen = json.loads((HERE / "schema-capacity-report.json").read_text(encoding="utf-8"))
        self.assertEqual(frozen, build_report())

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
                self.assertGreaterEqual(sum(v for b, v in split_quotas.items() if b not in ("1", "2")), 500)
            for bin_name, capacity in table["predicate_bin_capacity_upper_bound"].items():
                self.assertLessEqual(sum(quotas[split][bin_name] for split in quotas), capacity)

    def test_candidate_endpoint_outside_pinned_schema_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            capacity_table("forest10", ["bad:unknown/Aspect"])


if __name__ == "__main__":
    unittest.main()
