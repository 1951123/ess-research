from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_issue87 as runner


class Issue87RunnerTests(unittest.TestCase):
    def test_case_order_and_systemd_limits_are_frozen(self) -> None:
        self.assertIs(runner.protocol()["execution_authorized"], False)
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
                },
                runner.protocol(),
            ),
            [],
        )

    def test_execution_gate_refuses_before_creating_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            with self.assertRaisesRegex(
                PermissionError, "execution_authorized is false"
            ):
                runner.run(runner.ROOT, "gate-test", runtime)
            self.assertEqual(list(runtime.iterdir()), [])

    def test_hidden_worker_commands_also_obey_execution_gate(self) -> None:
        with patch.dict(runner.os.environ, {runner.SCOPE_ENV: "1"}):
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
        self.assertIs(planned_protocol["execution_authorized"], False)
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
