"""Solver-free checks for the proposed Issue #74 recovery runner."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_stage2_b2_recovery as runner


class RecoveryRunnerTests(unittest.TestCase):
    def test_separate_authorization_request_is_bound_to_locked_base(self) -> None:
        request_path = runner.HERE / "stage2-b2-recovery-authorization-request-v1.json"
        request = json.loads(request_path.read_text())
        base_path = runner.HERE / "stage2-b2-recovery-protocol-v1.json"
        base_sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
        self.assertEqual(request["base_protocol"]["sha256"], base_sha)
        self.assertEqual(request["scope"]["cases"], ["forest10-nominal-b2"])
        self.assertEqual(request["scope"]["retries"], 0)
        self.assertFalse(request["execution_authorized"])
        self.assertFalse(
            request["authorization_gate"]["merge_alone_authorizes_execution"]
        )
        self.assertFalse(request["authorization_gate"]["current_execution_authorized"])
        self.assertTrue(base_path.exists())

    def test_protocol_is_single_case_pinned_and_locked(self) -> None:
        protocol = runner.protocol()
        self.assertEqual(protocol["scope"]["cases"], ["forest10-nominal-b2"])
        self.assertFalse(protocol["execution_authorized"])
        self.assertEqual(
            protocol["immutable_software"]["advisor_source_commit"],
            "369d90217e931c7d1b0cd6e82c88527a25cc7129",
        )

    def test_runner_refuses_before_launch_without_new_authorization(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict("os.environ", {"ESS_RUNTIME_PARENT": temporary}),
            patch.object(runner.subprocess, "run") as launch,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "separate researcher execution authorization"
            ):
                runner.run(Path("/repo"), "test", True)
            launch.assert_not_called()

    def test_scope_command_carries_frozen_resource_limits(self) -> None:
        command = runner.scope_command(
            Path("/repo"), Path("/runtime/case"), python="/venv/python"
        )
        self.assertIn("MemoryMax=12884901888", command)
        self.assertIn("RuntimeMaxSec=900", command)
        self.assertIn("--unit=ess-issue74-b2-recovery.scope", command)
        self.assertIn("--setenv=ESS_ISSUE74_B2_RECOVERY_SCOPE=1", command)
        self.assertIn("/usr/bin/time", command)

    def test_systemd_status_retains_raw_result_and_memory_properties(self) -> None:
        completed = type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": "Id=ess-issue74-b2-run1.scope\nResult=oom-kill\nMemoryPeak=1234\nExecMainStatus=0\n",
                "stderr": "",
            },
        )()
        with patch.object(runner.subprocess, "run", return_value=completed) as query:
            status = runner.collect_systemd_status("ess-issue74-b2-run1.scope")
        self.assertTrue(status["available"])
        self.assertEqual(status["properties"]["Result"], "oom-kill")
        self.assertEqual(status["properties"]["MemoryPeak"], "1234")
        self.assertIn("Result=oom-kill", status["raw_properties"])
        self.assertIn("ess-issue74-b2-run1.scope", query.call_args.args[0])

    def test_systemd_status_unavailable_is_explicitly_unknown(self) -> None:
        completed = type(
            "Completed", (), {"returncode": 1, "stdout": "", "stderr": "not found"}
        )()
        with patch.object(runner.subprocess, "run", return_value=completed):
            status = runner.collect_systemd_status("missing.scope")
        self.assertFalse(status["available"])
        self.assertEqual(status["state"], "unknown")
        self.assertEqual(status["raw_properties"], "")
        self.assertEqual(status["query_stderr"], "not found")

    def test_systemd_query_error_does_not_infer_failure_cause(self) -> None:
        with patch.object(
            runner.subprocess, "run", side_effect=FileNotFoundError("systemctl")
        ):
            status = runner.collect_systemd_status("missing.scope")
        self.assertFalse(status["available"])
        self.assertEqual(status["state"], "unknown")
        self.assertIn("FileNotFoundError", status["error"])

    def test_frozen_file_hashes_are_read_and_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            frozen = repo / "selection.json"
            coefficients = repo / "coefficients.jsonl.gz"
            frozen.write_bytes(b"frozen selection")
            coefficients.write_bytes(b"coefficients")
            p = {
                "frozen_input": {
                    "frozen_selection_path": "selection.json",
                    "frozen_selection_sha256": hashlib.sha256(
                        frozen.read_bytes()
                    ).hexdigest(),
                    "coefficient_artifact_path": "coefficients.jsonl.gz",
                    "coefficient_artifact_sha256": hashlib.sha256(
                        coefficients.read_bytes()
                    ).hexdigest(),
                }
            }
            hashes = runner.verify_frozen_file_hashes(repo, p)
            self.assertEqual(
                hashes["frozen_selection"], p["frozen_input"]["frozen_selection_sha256"]
            )
            coefficients.write_bytes(b"mutated coefficients")
            with self.assertRaisesRegex(
                RuntimeError, "coefficient_artifact SHA-256 mismatch"
            ):
                runner.verify_frozen_file_hashes(repo, p)

    def test_phase_event_is_journaled_and_checkpointed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            runner.event(run_dir, "request_prepared", request_sha256="abc")
            event = json.loads(
                (run_dir / "phase-events.jsonl").read_text().splitlines()[0]
            )
            checkpoint = runner.checkpoint(run_dir)
            self.assertEqual(event["phase"], "request_prepared")
            self.assertEqual(checkpoint["request_sha256"], "abc")

    def test_interrupted_child_result_preserves_last_solver_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            runner.event(run_dir, "solver_invocation_started", invocation=1)
            result = runner.record_missing_child_result(run_dir, -15)
            self.assertEqual(
                result["last_child_checkpoint"]["phase"], "solver_invocation_started"
            )
            self.assertEqual(result["outcome"], "STOP_FOR_REVIEW")
            events = [
                json.loads(line)
                for line in (run_dir / "phase-events.jsonl").read_text().splitlines()
            ]
            self.assertEqual(events[-1]["phase"], "child_missing_result")
            self.assertEqual(events[-1]["last_child_checkpoint"]["invocation"], 1)

    def test_nonzero_outer_exit_cannot_leave_case_as_pass(self) -> None:
        result = runner.reconcile_scope_exit({"outcome": "PASS"}, 1)
        self.assertEqual(result["outcome"], "STOP_FOR_REVIEW")
        self.assertEqual(result["systemd_exit_code"], 1)


if __name__ == "__main__":
    unittest.main()
