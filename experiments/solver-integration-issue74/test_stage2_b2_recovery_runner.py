"""Solver-free checks for the proposed Issue #74 recovery runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_stage2_b2_recovery as runner


class RecoveryRunnerTests(unittest.TestCase):
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
        self.assertIn("--setenv=ESS_ISSUE74_B2_RECOVERY_SCOPE=1", command)
        self.assertIn("/usr/bin/time", command)

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
