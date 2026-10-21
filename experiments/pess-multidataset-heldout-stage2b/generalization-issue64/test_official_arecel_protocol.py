from __future__ import annotations

import json
import hashlib
import unittest
from pathlib import Path


CONFIG = json.loads(Path(__file__).with_name("official-arecel-protocol-v1.json").read_text())


class OfficialArecelProtocolTests(unittest.TestCase):
    def test_scope_source_metrics_and_execution_firewall_are_explicit(self) -> None:
        self.assertEqual(CONFIG["official_inputs"]["split_counts_per_dataset"]["valid"], 10000)
        self.assertEqual(CONFIG["official_inputs"]["split_counts_per_dataset"]["test"], 10000)
        self.assertEqual(CONFIG["selection"]["budgets_proxy_units"], [0, 2, 3, 5])
        self.assertEqual(CONFIG["evaluation"]["primary_estimator"].split()[0], "integer")
        self.assertFalse(CONFIG["phase_boundary"]["postgresql_execution_authorized"])
        self.assertFalse(CONFIG["phase_boundary"]["test_outcome_access_authorized"])
        self.assertEqual(CONFIG["scope_reset"]["self_generated_cohort_route"].split(";")[0], "SUPERSEDED_FOR_THIS_QUESTION")

    def test_full_split_plan_count_matches_frozen_assumptions(self) -> None:
        counts = CONFIG["outcome_free_plan_count"]
        candidate_path = (
            Path(__file__).parents[3]
            / "experiments/workload-structure-audit-issue59/protocol-v1.json"
        )
        candidate_bytes = candidate_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(candidate_bytes).hexdigest(),
            CONFIG["selection"]["candidate_protocol_sha256"],
        )
        candidate_protocol = json.loads(candidate_bytes)
        candidate_counts = {
            dataset: len(candidate_protocol["candidate_universe"][dataset]["candidates"])
            for dataset in ("forest10", "census13", "dmv11", "power7")
        }
        self.assertEqual(candidate_counts, {"forest10": 6, "census13": 6, "dmv11": 10, "power7": 6})
        expected_calibration = {
            dataset: 10000 * (candidate_count + 1)
            for dataset, candidate_count in candidate_counts.items()
        }
        self.assertEqual(counts["calibration_query_plans"], expected_calibration)
        unique_test_sets = 1 + 2 * (len(CONFIG["selection"]["budgets_proxy_units"]) - 1)
        self.assertEqual(unique_test_sets, 7)
        self.assertEqual(
            counts["test_query_plans_max"],
            {dataset: 10000 * unique_test_sets for dataset in candidate_counts},
        )
        calibration = sum(counts["calibration_query_plans"].values())
        test = sum(counts["test_query_plans_max"].values())
        self.assertEqual(calibration, 320000)
        self.assertEqual(test, 280000)
        self.assertEqual(calibration + test, counts["total_max"])
        self.assertEqual(
            counts["per_dataset_total_max"],
            {"forest10": 140000, "census13": 140000, "dmv11": 180000, "power7": 140000},
        )
        self.assertTrue(
            all(value > counts["existing_issue48_cap_per_dataset"]
                for value in counts["per_dataset_total_max"].values())
        )

    def test_reported_correctness_blockers_are_nonempty(self) -> None:
        self.assertGreaterEqual(len(CONFIG["genuine_correctness_blockers_before_execution"]), 3)
        self.assertEqual(CONFIG["execution_pins_to_reverify"]["postgresql_target"]["version"], "16.14")
        self.assertIn("Q1", CONFIG["evaluation"]["primary_metric"])
        self.assertIn("valid-only", CONFIG["genuine_correctness_blockers_before_execution"][0])


if __name__ == "__main__":
    unittest.main()
