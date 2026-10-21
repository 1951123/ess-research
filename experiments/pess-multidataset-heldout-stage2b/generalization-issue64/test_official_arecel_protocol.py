from __future__ import annotations

import json
import hashlib
import re
import subprocess
import unittest
from pathlib import Path


CONFIG = json.loads(Path(__file__).with_name("official-arecel-protocol-v1.json").read_text())


class OfficialArecelProtocolTests(unittest.TestCase):
    def test_scope_source_metrics_and_execution_firewall_are_explicit(self) -> None:
        self.assertEqual(CONFIG["official_inputs"]["split_counts_per_dataset"]["valid"], 10000)
        self.assertEqual(CONFIG["official_inputs"]["split_counts_per_dataset"]["test"], 10000)
        self.assertEqual(CONFIG["selection"]["budgets_proxy_units"], [0, 2, 3, 5])
        self.assertEqual(
            CONFIG["selection"]["candidate_counts"],
            {"forest10": 45, "census13": 78, "dmv11": 55, "power7": 21},
        )
        self.assertEqual(CONFIG["evaluation"]["primary_estimator"].split()[0], "integer")
        self.assertFalse(CONFIG["phase_boundary"]["postgresql_execution_authorized"])
        self.assertFalse(CONFIG["phase_boundary"]["test_outcome_access_authorized"])
        self.assertEqual(CONFIG["scope_reset"]["self_generated_cohort_route"].split(";")[0], "SUPERSEDED_FOR_THIS_QUESTION")

    def test_full_split_plan_count_matches_frozen_assumptions(self) -> None:
        counts = CONFIG["outcome_free_plan_count"]
        repo = Path(__file__).parents[3]
        pins = CONFIG["selection"]["candidate_source_pins"]

        source_match = re.search(
            r"merge commit ([0-9a-f]{40})",
            CONFIG["selection"]["candidate_universe_source"],
        )
        self.assertIsNotNone(source_match, "candidate source must identify its immutable merge commit")
        source_commit = source_match.group(1)

        def source_sha256(path: str) -> str:
            content = subprocess.run(
                ["git", "-C", str(repo), "show", f"{source_commit}:{path}"],
                check=True,
                capture_output=True,
            ).stdout
            return hashlib.sha256(content).hexdigest()

        self.assertEqual(
            source_sha256("src/ess_research/arecel/candidates.py"),
            pins["candidate_module_sha256"],
        )
        self.assertEqual(
            source_sha256("experiments/arecel/issue67-candidate-discovery.md"),
            pins["discovery_report_sha256"],
        )
        self.assertEqual(
            source_sha256("src/ess_research/arecel/archive.py"),
            pins["archive_module_sha256_at_merge"],
        )
        candidate_counts = CONFIG["selection"]["candidate_counts"]
        expected_calibration = {
            dataset: 10000 * (candidate_count + 1)
            for dataset, candidate_count in candidate_counts.items()
        }
        self.assertEqual(counts["calibration_query_plans_max"], expected_calibration)
        unique_test_sets = 1 + 2 * (len(CONFIG["selection"]["budgets_proxy_units"]) - 1)
        self.assertEqual(unique_test_sets, 7)
        self.assertEqual(
            counts["test_query_plans_max"],
            {dataset: 10000 * unique_test_sets for dataset in candidate_counts},
        )
        calibration = sum(counts["calibration_query_plans_max"].values())
        test = sum(counts["test_query_plans_max"].values())
        self.assertEqual(calibration, 2030000)
        self.assertEqual(test, 280000)
        self.assertEqual(calibration + test, counts["total_max"])
        self.assertEqual(
            counts["per_dataset_total_max"],
            {"forest10": 530000, "census13": 860000, "dmv11": 630000, "power7": 290000},
        )
        self.assertTrue(
            all(value > counts["existing_issue48_cap_per_dataset"]
                for value in counts["per_dataset_total_max"].values())
        )

    def test_reported_correctness_blockers_are_nonempty(self) -> None:
        self.assertGreaterEqual(len(CONFIG["genuine_correctness_blockers_before_execution"]), 3)
        self.assertEqual(CONFIG["execution_pins_to_reverify"]["postgresql_target"]["version"], "16.14")
        self.assertIn("Q1", CONFIG["evaluation"]["primary_metric"])
        self.assertIn("valid-only truth", CONFIG["genuine_correctness_blockers_before_execution"][0])
        self.assertIn("2^78", CONFIG["genuine_correctness_blockers_before_execution"][1])


if __name__ == "__main__":
    unittest.main()
