"""Solver-free structural checks for the proposed Stage 2 protocol."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROTOCOL = json.loads((HERE / "stage2-b23-protocol-v1.json").read_text())


def read_repo_json(relative_path: str) -> dict:
    return json.loads((REPO / relative_path).read_text(encoding="utf-8"))


def file_sha256(relative_path: str) -> str:
    return hashlib.sha256((REPO / relative_path).read_bytes()).hexdigest()


def candidate_order_sha256(candidate_ids: list[str]) -> str:
    canonical = json.dumps(candidate_ids, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


class Stage2B23ProtocolTests(unittest.TestCase):
    def test_protocol_is_proposed_and_does_not_authorize_solver_jobs(self) -> None:
        self.assertEqual(PROTOCOL["status"], "PROPOSED_NOT_FROZEN_NOT_EXECUTED")
        self.assertFalse(PROTOCOL["solver_jobs_authorized"])
        self.assertFalse(PROTOCOL["execution_gate"]["this_protocol_pr_may_execute_solver"])
        self.assertEqual(PROTOCOL["budgets"], [2, 3])
        self.assertEqual(PROTOCOL["acceptance_and_reporting"]["max_concurrent_cases"], 1)
        self.assertEqual(PROTOCOL["acceptance_and_reporting"]["case_retry_count"], 0)

    def test_immutable_pins_and_fixed_case_order(self) -> None:
        software = PROTOCOL["immutable_software"]
        self.assertEqual(software["stage1_adapter_baseline_commit"],
                         "6c0d82d258faaa817f2bc977ff99b04971550aa0")
        self.assertEqual(software["advisor_source_commit"],
                         "d40a57d4704345fef85298dd97192b2d998dc6eb")
        cases = PROTOCOL["case_order"]
        self.assertEqual([c["index"] for c in cases], list(range(1, 9)))
        self.assertEqual(
            [(c["dataset"], c["objective"], c["budget"]) for c in cases],
            [
                ("forest10", "nominal", 2),
                ("forest10", "pess", 2),
                ("forest10", "nominal", 3),
                ("forest10", "pess", 3),
                ("census13", "nominal", 2),
                ("census13", "pess", 2),
                ("census13", "nominal", 3),
                ("census13", "pess", 3),
            ],
        )
        self.assertTrue(all(c["budget"] in PROTOCOL["budgets"] for c in cases))

    def test_resource_limits_and_fail_closed_policy_are_complete(self) -> None:
        settings = PROTOCOL["solver_settings"]
        self.assertEqual(settings["outer_memory_max_bytes"], 12 * 1024**3)
        self.assertEqual(settings["outer_runtime_max_seconds"], 900)
        self.assertEqual(settings["case_time_seconds"], 600)
        self.assertEqual(settings["total_time_seconds"], 600)
        self.assertEqual(settings["pess_inner_time_seconds"], 120)
        self.assertIn("first case", PROTOCOL["acceptance_and_reporting"]["first_failure_policy"])
        self.assertIn("retry any case", PROTOCOL["acceptance_and_reporting"]["first_failure_policy"])

    def test_frozen_file_hashes_task_universes_orders_and_exact_ties(self) -> None:
        models = PROTOCOL["frozen_inputs"]
        refs = PROTOCOL["frozen_exact_references"]
        forest = models["forest10"]
        forest_data = read_repo_json(forest["frozen_selection_path"])
        self.assertEqual(file_sha256(forest["frozen_selection_path"]),
                         forest["frozen_selection_sha256"])
        forest_order = forest_data["inputs"]["candidate_order"]
        self.assertEqual(len(forest_order), 45)
        self.assertEqual(candidate_order_sha256(forest_order), forest["candidate_order_sha256"])
        self.assertEqual(forest_data["inputs"]["valid_workload_count"], 10000)
        self.assertEqual(forest_data["model"]["coefficient_artifact_sha256"],
                         forest["coefficient_artifact_sha256"])
        self.assertEqual(forest_data["inputs"]["valid_truth_values_sha256"],
                         forest["valid_truth_sha256"])
        self.assertEqual(forest_data["inputs"]["arecel_archive_sha256"],
                         forest["arecel_archive_sha256"])
        for objective, frozen_key in (("nominal", "Nominal"), ("pess", "PESS")):
            for budget in ("2", "3"):
                source = forest_data["selection"]["results"][frozen_key][budget]
                expected = refs["forest10"][objective][budget]
                self.assertEqual(source["objective_fraction"], expected["objective_fraction"])
                self.assertEqual(source["all_optimal_sets"], expected["all_optimal_sets"])

        census = models["census13"]
        census_data = read_repo_json(census["frozen_selection_path"])
        self.assertEqual(file_sha256(census["frozen_selection_path"]),
                         census["frozen_selection_sha256"])
        census_plan = read_repo_json(census["plan_path"])
        self.assertEqual(file_sha256(census["plan_path"]), census["plan_sha256"])
        self.assertEqual(census_data["plan_sha256"], census["plan_sha256"])
        self.assertEqual(census_data["model_coefficient_sha256"], census["coefficient_sha256"])
        self.assertEqual(census_data["observation_sha256"], census["observation_sha256"])
        self.assertEqual(census_data["valid_truth_sha256"], census["valid_truth_sha256"])
        census_order = census_plan["nominal_priority_orders"]["orders"][0]["candidate_ids"]
        self.assertEqual(len(census_order), 78)
        self.assertEqual(candidate_order_sha256(census_order), census["candidate_order_sha256"])
        self.assertEqual(len(census_data["candidate_ids"]), 78)
        self.assertEqual(len(census_data["nominal_by_order"][0]["budgets"]), 3)
        for budget in ("2", "3"):
            expected_nominal = refs["census13"]["nominal"][budget]
            frozen_nominal = census_data["nominal_by_order"][0]["budgets"][budget]
            self.assertEqual(frozen_nominal["objective_fraction"],
                             expected_nominal["objective_fraction"])
            self.assertEqual(frozen_nominal["all_optimal_sets"],
                             expected_nominal["all_optimal_sets"])
            expected_pess = refs["census13"]["pess"][budget]
            frozen_pess = census_data["pess_global"][budget]
            self.assertEqual(frozen_pess["objective_fraction"], expected_pess["objective_fraction"])
            self.assertEqual(frozen_pess["all_optimal_sets"], expected_pess["all_optimal_sets"])


if __name__ == "__main__":
    unittest.main()
