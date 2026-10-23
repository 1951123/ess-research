"""Solver-free tests for the Issue #74 Stage 2 execution runner."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import run_stage2_b23 as runner

HERE = Path(__file__).resolve().parent


class Stage2B23RunnerTests(unittest.TestCase):
    def test_config_pins_merged_protocol_and_exact_case_order(self) -> None:
        config = json.loads((HERE / "stage2-b23-runner-config-v1.json").read_text())
        protocol = json.loads((HERE / "stage2-b23-protocol-v1.json").read_text())
        self.assertEqual(config["protocol_merge_commit"], runner.PROTOCOL_MERGE)
        self.assertEqual(runner.sha256_file(HERE / "stage2-b23-protocol-v1.json"),
                         config["protocol_sha256"])
        self.assertEqual(config["case_order"], [case["case_id"] for case in protocol["case_order"]])
        self.assertEqual(config["stage1_adapter_base_commit"], runner.STAGE1_COMMIT)
        self.assertEqual(config["advisor_source_commit"], runner.ADVISOR_COMMIT)

    def test_case_command_has_frozen_limits_and_invokes_single_child(self) -> None:
        case = {"index": 3, "case_id": "forest10-nominal-b3"}
        command = runner.build_case_command(Path("/repo"), case, Path("/runtime/run"),
                                            python="/venv/bin/python")
        self.assertEqual(command[:4], ["systemd-run", "--user", "--scope", "--quiet"])
        self.assertIn("MemoryMax=12884901888", command)
        self.assertIn("RuntimeMaxSec=900", command)
        self.assertIn("--setenv=ESS_ISSUE74_B23_SCOPE_GUARD=1", command)
        self.assertIn("/usr/bin/time", command)
        self.assertIn("/venv/bin/python", command)
        self.assertEqual(command.count("_case"), 1)
        self.assertIn("--case-index", command)
        self.assertEqual(command[command.index("--case-index") + 1], "3")

    def test_sequence_stops_after_first_nonpass_without_retry(self) -> None:
        cases = [{"index": index} for index in range(1, 9)]
        invoked: list[int] = []

        def invoke(case: dict[str, int]) -> dict[str, str]:
            invoked.append(case["index"])
            outcome = "PASS" if case["index"] == 1 else "STOP_FOR_REVIEW"
            return {"outcome": outcome}

        results = runner.run_sequence(cases, invoke)
        self.assertEqual(invoked, [1, 2])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[-1]["outcome"], "STOP_FOR_REVIEW")

    def test_solver_acceptance_rejects_incomplete_or_fallback_statuses(self) -> None:
        status = {
            "status_code": 0, "message": "optimal", "solver_reported_optimal": True,
            "incumbent_returned": True, "primal_objective": 1.0, "dual_bound": 1.0,
            "mip_gap": 0.0, "duration_seconds": 1.0, "highs_invocations": 1,
            "selected_attempt": "initial",
        }
        response = {
            "status": "optimal", "optimality": {"solver_reported_optimal": True},
            "solver_statuses": [status], "diagnostics": {"numerical_warnings": []},
        }
        self.assertEqual(runner.check_solver_status(response), (True, []))
        fallback = {**status, "highs_invocations": 2}
        ok, errors = runner.check_solver_status({**response, "solver_statuses": [fallback]})
        self.assertFalse(ok)
        self.assertIn("fallback_attempt_evidence_incomplete_0", errors)
        ok, errors = runner.check_solver_status({**response, "solver_statuses": []})
        self.assertFalse(ok)
        self.assertIn("missing_solver_statuses", errors)

    def test_response_contract_checks_schema_backend_and_provenance(self) -> None:
        payload = {
            "schema_version": "1", "objective": "pess", "backend": "master_oracle",
            "input_provenance": {"advisor_source_commit": runner.ADVISOR_COMMIT},
        }
        protocol = {
            "immutable_software": {
                "advisor_schema_version": "1", "pess_ess_version": "0.1.0",
                "scipy_version": "1.18.1",
            },
            "objectives": {"pess": {"backend": "master_oracle"}},
        }
        response = {
            "schema_version": "1", "objective": "pess", "backend": "master_oracle",
            "input_provenance": payload["input_provenance"],
            "provenance": {"package_version": "0.1.0", "scipy_version": "1.18.1"},
        }
        self.assertEqual(runner.check_response_contract(response, payload, protocol), [])
        bad_response = {**response, "backend": "static"}
        self.assertIn("response_backend_mismatch",
                      runner.check_response_contract(bad_response, payload, protocol))

    def test_input_pin_check_rejects_hash_and_provenance_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            frozen_path = Path("frozen.json")
            coefficient_path = Path("coefficients.jsonl.gz")
            (repo / frozen_path).write_bytes(b"frozen")
            (repo / coefficient_path).write_bytes(b"coefficients")
            model = {
                "model_version": "forest10-positive-preclamp-v1",
                "model_source_commit": "model-source",
                "frozen_selection_path": str(frozen_path),
                "frozen_selection_sha256": hashlib.sha256(b"frozen").hexdigest(),
                "coefficient_artifact_path": str(coefficient_path),
                "coefficient_artifact_sha256": hashlib.sha256(b"coefficients").hexdigest(),
                "valid_truth_sha256": "truth-sha",
                "arecel_archive_sha256": "archive-sha",
            }
            protocol = {"frozen_inputs": {"forest10": model}}
            provenance = {
                "model_version": model["model_version"],
                "model_source_commit": model["model_source_commit"],
                "frozen_reference_sha256": model["frozen_selection_sha256"],
                "coefficient_artifact_sha256": model["coefficient_artifact_sha256"],
                "valid_truth_values_sha256": model["valid_truth_sha256"],
                "arecel_archive_sha256": model["arecel_archive_sha256"],
            }
            source = {"input_provenance": provenance}
            checked = runner.verify_model_inputs(repo, source, protocol, "forest10")
            self.assertEqual(set(checked), {str(frozen_path), str(coefficient_path)})
            provenance["valid_truth_values_sha256"] = "wrong"
            with self.assertRaisesRegex(RuntimeError, "provenance mismatch"):
                runner.verify_model_inputs(repo, source, protocol, "forest10")


if __name__ == "__main__":
    unittest.main()
