from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_issue87 as runner


class Issue87RunnerTests(unittest.TestCase):
    def test_case_order_and_systemd_limits_are_frozen(self) -> None:
        self.assertIs(runner.protocol()["execution_authorized"], True)
        self.assertEqual(
            runner.sha256_file(runner.PROTOCOL_PATH), runner.PROTOCOL_SHA256
        )
        plan = runner.case_plan()
        self.assertEqual(len(plan), 20)
        self.assertEqual(plan[0]["case_id"], "forest10-nominal-b0")
        self.assertEqual(plan[1]["case_id"], "forest10-pess-b0")
        self.assertEqual(plan[-2]["case_id"], "census13-nominal-b5")
        self.assertEqual(plan[-1]["case_id"], "census13-pess-b5")

        command = runner.scope_command(
            "test.scope", Path("time.txt"), ["_case", "--help"]
        )
        self.assertIn("MemoryMax=12884901888", command)
        self.assertIn("RuntimeMaxSec=900", command)
        self.assertIn("--setenv=OMP_NUM_THREADS=1", command)
        self.assertIn("--setenv=ESS_ISSUE87_SYSTEMD_SCOPE=1", command)
        self.assertEqual(runner.systemd_seconds("15min"), 900)
        self.assertEqual(runner.systemd_seconds("15min 0s"), 900)
        self.assertIsNone(runner.systemd_seconds("infinity"))
        self.assertEqual(
            runner.scope_errors(
                {
                    "returncode": 0,
                    "wall_seconds": 0.1,
                    "time_report": {"wall_seconds": 0.1, "peak_rss_bytes": 1024},
                    "systemd_status": {
                        "available": True,
                        "properties": {
                            "Result": "success",
                            "MemoryMax": "12884901888",
                            "RuntimeMaxUSec": "15min",
                            "MemoryPeak": "1024",
                        },
                    },
                    "live_scope_enforcement": {
                        "verified": True,
                        "properties": {
                            "ActiveState": "active",
                            "MemoryMax": "12884901888",
                            "RuntimeMaxUSec": "15min",
                        },
                        "control_group": "/user.slice/test.scope",
                        "process_control_group": "/user.slice/test.scope",
                        "cgroup_memory_max_bytes": 12884901888,
                    },
                },
                runner.protocol(),
            ),
            [],
        )

    def test_post_exit_properties_alone_do_not_verify_scope_limits(self) -> None:
        errors = runner.scope_errors(
            {
                "returncode": 0,
                "wall_seconds": 0.1,
                "time_report": {"wall_seconds": 0.1, "peak_rss_bytes": 1024},
                "systemd_status": {
                    "available": True,
                    "properties": {
                        "Result": "success",
                        "MemoryMax": "12884901888",
                        "RuntimeMaxUSec": "15min",
                    },
                },
            },
            runner.protocol(),
        )
        self.assertIn("active_scope_limit_verification_missing_or_failed", errors)

    def test_jsonl_records_are_one_compact_json_object_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "results.jsonl"
            runner.append_jsonl(path, {"nested": {"values": [1, 2]}, "ok": True})
            raw = path.read_bytes()
            self.assertEqual(raw.count(b"\n"), 1)
            self.assertFalse(raw.lstrip().startswith(b"{\n"))
            self.assertEqual(
                json.loads(raw.splitlines()[0]),
                {"nested": {"values": [1, 2]}, "ok": True},
            )

    def test_live_systemd_scope_limits_for_true_and_false(self) -> None:
        if shutil.which("systemctl") is None or shutil.which("systemd-run") is None:
            self.skipTest("systemd commands are unavailable")
        try:
            manager = subprocess.run(
                ["systemctl", "--user", "show-environment"],
                check=False,
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            self.skipTest("user systemd manager is unavailable")
        if manager.returncode != 0:
            self.skipTest("user systemd manager is unavailable")

        for child, expected_returncode in (("/bin/true", 0), ("/bin/false", 1)):
            with self.subTest(child=child), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                unit = runner.systemd_unit_name("review", Path(child).name)
                evidence = directory / "scope-enforcement.json"
                command = runner.scope_command(
                    unit,
                    directory / "time.txt",
                    [
                        "_scope_probe",
                        "--scope-unit",
                        unit,
                        "--evidence",
                        str(evidence),
                        "--child",
                        child,
                    ],
                )
                completed = subprocess.run(
                    command,
                    cwd=runner.ROOT,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(completed.returncode, expected_returncode)
                record = runner.read_json(evidence)
                self.assertTrue(record["verified"], record["verification_errors"])
                self.assertEqual(record["properties"]["ActiveState"], "active")
                self.assertEqual(record["cgroup_memory_max_bytes"], 12884901888)
                self.assertEqual(record["probe_child_returncode"], expected_returncode)

    def test_execution_gate_refuses_before_creating_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            unauthorized = runner.protocol() | {"execution_authorized": False}
            with (
                patch.object(runner, "protocol", return_value=unauthorized),
                self.assertRaisesRegex(
                    PermissionError, "execution_authorized is false"
                ),
            ):
                runner.run(runner.ROOT, "gate-test", runtime)
            self.assertEqual(list(runtime.iterdir()), [])

    def test_hidden_worker_commands_also_obey_execution_gate(self) -> None:
        unauthorized = runner.protocol() | {"execution_authorized": False}
        with (
            patch.dict(runner.os.environ, {runner.SCOPE_ENV: "1"}),
            patch.object(runner, "protocol", return_value=unauthorized),
        ):
            args = SimpleNamespace(
                repo=runner.ROOT,
                case_dir=Path("unused"),
                dataset="forest10",
                budget=0,
                objective="nominal",
                build_frozen_input=True,
                base_request=None,
            )
            with self.assertRaisesRegex(
                PermissionError, "execution_authorized is false"
            ):
                runner._worker_case(args)
            with self.assertRaisesRegex(
                PermissionError, "execution_authorized is false"
            ):
                runner._worker_cross(SimpleNamespace())

    def test_serial_runner_stops_after_first_incomplete_case(self) -> None:
        planned_protocol = runner.protocol()
        self.assertIs(planned_protocol["execution_authorized"], True)
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(runner, "protocol", return_value=planned_protocol),
                patch.object(runner, "require_execution_authorized"),
                patch.object(runner, "verify_source_checkout", return_value="a" * 40),
                patch.object(runner, "verify_run_environment", return_value={}),
                patch.object(
                    runner,
                    "_case_attempt",
                    return_value=(
                        {
                            "status": "INCOMPLETE",
                            "termination_reason": "fixture_failure",
                        },
                        Path("unused-request.json"),
                    ),
                ) as attempt,
            ):
                exit_code = runner.run(runner.ROOT, "stop-test", Path(temporary))

            self.assertEqual(exit_code, 2)
            attempt.assert_called_once()
            summary = runner.read_json(
                Path(temporary) / "ess-research/issue87/runs/stop-test/run-summary.json"
            )
            self.assertEqual(summary["status"], "STOPPED_INCOMPLETE")
            self.assertEqual(summary["attempted_cases"], 1)
            self.assertEqual(len(summary["not_started_case_ids"]), 19)
            metadata = runner.read_json(
                Path(temporary)
                / "ess-research/issue87/runs/stop-test/run-metadata.json"
            )
            self.assertEqual(metadata["status"], summary["status"])
            self.assertEqual(metadata["attempted_cases"], summary["attempted_cases"])
            self.assertEqual(metadata["failure_reason"], summary["failure_reason"])
            self.assertEqual(metadata["terminal_status_source"], "run-summary.json")

    def test_incomplete_response_cannot_become_a_selected_set(self) -> None:
        p = runner.protocol()
        case = runner.case_plan(p)[0]
        request = {
            "objective": "nominal",
            "priority_order": ["a"],
            "instance": {
                "budget": "0",
                "candidates": [
                    {"id": "a", "maintenance_cost": "1", "endpoints": ["x", "y"]}
                ],
                "tasks": [],
            },
        }
        response = {
            "status": "heuristic_incomplete",
            "incumbent": {
                "selected": ["a"],
                "maintenance_cost": "0",
                "unused_budget": "0",
                "objective_value": "0",
            },
            "greedy": {"addition_order": ["a"], "steps": []},
        }
        record = runner.case_record(
            case,
            p,
            "a" * 40,
            request,
            b"request",
            response,
            b"response",
            {"returncode": 1, "wall_seconds": 1.0},
            [],
        )
        self.assertEqual(record["status"], "INCOMPLETE")
        self.assertIsNone(record["selected_ids"])
        self.assertEqual(record["last_completed_prefix"], ["a"])

    def test_full_frozen_input_builder_in_ci_without_solver(self) -> None:
        for dataset, candidates in (("forest10", 45), ("census13", 78)):
            with self.subTest(dataset=dataset):
                payload = runner.adapter.build_frozen_dataset_payload(
                    runner.ROOT, dataset, 0, "nominal"
                )
                self.assertEqual(len(payload["instance"]["tasks"]), 10_000)
                self.assertEqual(len(payload["instance"]["candidates"]), candidates)
                self.assertTrue(
                    all(
                        candidate["maintenance_cost"] == "1"
                        for candidate in payload["instance"]["candidates"]
                    )
                )
                self.assertEqual(payload["backend"], "add_only_greedy")
                self.assertEqual(payload["objective"], "nominal")
                self.assertEqual(payload["instance"]["budget"], "0")
                nominal_case = next(
                    case
                    for case in runner.case_plan()
                    if case["case_id"] == f"{dataset}-nominal-b0"
                )
                pess_case = next(
                    case
                    for case in runner.case_plan()
                    if case["case_id"] == f"{dataset}-pess-b5"
                )
                self.assertEqual(
                    runner.request_errors(nominal_case, payload, runner.protocol()), []
                )
                self.assertEqual(
                    runner.request_errors(
                        pess_case,
                        runner.request_for_case(payload, 5, "pess"),
                        runner.protocol(),
                    ),
                    [],
                )


if __name__ == "__main__":
    unittest.main()
