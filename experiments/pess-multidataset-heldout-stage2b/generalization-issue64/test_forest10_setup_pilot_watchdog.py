from __future__ import annotations

import errno
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_forest10_setup_pilot as pilot


class _FakeProcess:
    pid = 12345

    def poll(self):
        return None

    def wait(self, timeout=None):
        return 0


class Forest10SetupPilotWatchdogTests(unittest.TestCase):
    def test_disk_scan_retries_a_disappearing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vanishing = root / "vanishing"
            vanishing.write_bytes(b"temporary")
            original_lstat = Path.lstat
            injected = False

            def lstat_with_one_disappearance(path):
                nonlocal injected
                if path == vanishing and not injected:
                    injected = True
                    path.unlink()
                    raise FileNotFoundError(errno.ENOENT, "disappeared", str(path))
                return original_lstat(path)

            with patch.object(Path, "lstat", lstat_with_one_disappearance):
                measured = pilot._allocated_bytes(root)

            self.assertTrue(injected)
            self.assertFalse(vanishing.exists())
            self.assertEqual(measured, original_lstat(root).st_blocks * 512)

    def test_real_scan_failure_fails_closed_with_unknown_peak_and_errno(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            runs = base / "runs"
            root = runs / "pilot"
            root.mkdir(parents=True)
            denied = root / "inaccessible"
            denied.write_bytes(b"data")
            original_lstat = Path.lstat

            def lstat_with_permission_failure(path):
                if path == denied:
                    raise PermissionError(errno.EACCES, "synthetic inaccessible entry", str(path))
                return original_lstat(path)

            with patch.object(Path, "lstat", lstat_with_permission_failure):
                with self.assertRaises(PermissionError) as caught:
                    pilot._allocated_bytes(root)
            self.assertEqual(caught.exception.errno, errno.EACCES)

            runtime = base / "runtime"
            runtime.mkdir()
            process = _FakeProcess()

            with (
                patch.object(pilot, "runtime_runs", return_value=runs),
                patch.object(pilot, "configured_root", return_value=runtime),
                patch.object(pilot.subprocess, "Popen", return_value=process),
                patch.object(pilot.os, "killpg") as killpg,
                patch.object(pilot.time, "sleep"),
                patch("builtins.print"),
                patch.object(
                    pilot,
                    "_allocated_bytes",
                    side_effect=PermissionError(errno.EACCES, "synthetic inaccessible entry"),
                ),
            ):
                exit_code = pilot._supervise(root)

            summary = json.loads((root / "pilot-supervisor-summary.json").read_text())
            self.assertEqual(exit_code, 2)
            self.assertEqual(summary["status"], "ABORTED")
            self.assertEqual(summary["stop_reason"], "disk_monitor_unavailable")
            self.assertIsNone(summary["peak_allocated_disk_bytes"])
            self.assertEqual(summary["peak_disk_measurement"], "UNKNOWN")
            self.assertEqual(summary["disk_monitor_error"], {"error_class": "PermissionError", "errno": errno.EACCES})
            self.assertEqual(killpg.call_count, 1)

    def test_existing_disk_and_wall_safety_thresholds_are_unchanged(self):
        self.assertEqual(pilot.HARD_WALL_SECONDS, 30 * 60)
        self.assertEqual(pilot.HARD_DISK_BYTES, 2 * 1024**3)
        self.assertIsNone(pilot._watchdog_stop_reason(pilot.SOFT_STOP_DISK_BYTES - 1, 0))
        self.assertEqual(
            pilot._watchdog_stop_reason(pilot.SOFT_STOP_DISK_BYTES, 0),
            "disk_safety_abort_1.5_GiB",
        )
        self.assertEqual(
            pilot._watchdog_stop_reason(0, pilot.SOFT_STOP_SECONDS),
            "wall_safety_abort_28_minutes",
        )

    def test_disk_threshold_still_aborts_and_reports_measured_peak(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            runs = base / "runs"
            root = runs / "pilot"
            root.mkdir(parents=True)
            runtime = base / "runtime"
            runtime.mkdir()
            process = _FakeProcess()
            threshold = pilot.SOFT_STOP_DISK_BYTES

            with (
                patch.object(pilot, "runtime_runs", return_value=runs),
                patch.object(pilot, "configured_root", return_value=runtime),
                patch.object(pilot.subprocess, "Popen", return_value=process),
                patch.object(pilot.os, "killpg"),
                patch.object(pilot.time, "sleep"),
                patch("builtins.print"),
                patch.object(pilot, "_allocated_bytes", return_value=threshold),
            ):
                exit_code = pilot._supervise(root)

            summary = json.loads((root / "pilot-supervisor-summary.json").read_text())
            self.assertEqual(exit_code, 2)
            self.assertEqual(summary["stop_reason"], "disk_safety_abort_1.5_GiB")
            self.assertEqual(summary["peak_allocated_disk_bytes"], threshold)
            self.assertEqual(summary["peak_disk_measurement"], "MEASURED")

    def test_worker_command_failure_keeps_only_sanitized_cause(self):
        error = RuntimeError(
            "command failed: /pg/bin/psql -c 'secret query'\n"
            "stdout=secret result\nstderr=ERROR: secret detail"
        )
        record = pilot._worker_error_record(error, "bootstrap")
        self.assertEqual(record["postgresql_command"], {"cause": "postgresql_reported_error", "exit_code": None})
        self.assertNotIn("secret", json.dumps(record))

    def test_pg_bootstrap_commands_have_distinct_fixed_phase_labels(self):
        cases = (
            (["/pg/bin/initdb", "-D", "/private/pgdata"], "initdb"),
            (["/pg/bin/pg_ctl", "-D", "/private/pgdata", "-w", "start"], "pg_ctl_start"),
            (["/pg/bin/psql", "-c", "SELECT current_setting('data_directory'), current_database();"], "psql_identity_check"),
            (["/pg/bin/psql", "-c", "CREATE TABLE public.forest10 (id integer);"], "schema_create"),
            (["/pg/bin/psql", "-c", "\\copy public.forest10 FROM '/private/input.csv' WITH (FORMAT csv, HEADER true);"], "csv_import"),
            (["/pg/bin/psql", "-c", "SET ess.analyze_sample_export='/private/sample'; ANALYZE public.forest10; RESET ess.analyze_sample_export;"], "sample_export_analyze"),
            (["/pg/bin/psql", "-c", "SET ess.analyze_sample_import='/private/sample'; ANALYZE public.forest10; RESET ess.analyze_sample_import;"], "sample_replay_analyze"),
        )
        for command, expected_phase in cases:
            with self.subTest(expected_phase=expected_phase):
                phase, _program = pilot._classify_pg_command(command)
                self.assertEqual(phase, expected_phase)

    def test_injected_pg_command_failure_keeps_phase_exit_code_and_no_raw_output(self):
        command = ["/pg/bin/psql", "-c", "\\copy public.forest10 FROM '/private/secret.csv' WITH (FORMAT csv, HEADER true);"]
        completed = pilot.subprocess.CompletedProcess(
            command, 23, "secret stdout", "ERROR: secret server diagnostic"
        )
        failures = []
        phases = []
        with patch.object(pilot.subprocess, "run", return_value=completed):
            with self.assertRaises(pilot.PilotPostgreSQLFailure) as caught:
                pilot._run_diagnostic_pg_command(
                    command,
                    env={},
                    phase_sink=phases.append,
                    failure_sink=failures,
                )
        expected = {
            "phase": "csv_import",
            "type": "PostgreSQLCommandError",
            "message": "PostgreSQL command failed; SQL and command output omitted",
            "postgresql_command": {
                "program": "psql",
                "cause": "postgresql_reported_error",
                "exit_code": 23,
            },
        }
        self.assertEqual(caught.exception.record(), expected)
        self.assertEqual(pilot._worker_error_record(caught.exception, "coarse_fallback"), expected)
        self.assertEqual(failures, [expected])
        self.assertEqual(phases, ["csv_import"])
        self.assertNotIn("secret", json.dumps(expected))

    def test_pg_stderr_is_reduced_to_fixed_safe_categories(self):
        cases = (
            ("could not start server; secret path", "server_start_failure"),
            ("could not bind address; address already in use", "port_bind_failure"),
            ("ERROR: could not write file: No space left on device", "no_space_left"),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(pilot._safe_pg_cause(message), expected)
                self.assertNotIn("secret", json.dumps({"cause": pilot._safe_pg_cause(message)}))

    def test_pinned_helper_instrumentation_restores_original_functions(self):
        original_runner = lambda *args, **kwargs: None
        helpers = SimpleNamespace(
            run_command=original_runner,
            validate_cluster_identity=lambda *args: None,
        )
        failures = []
        phases = []
        command = ["/pg/bin/initdb", "-D", "/private/pgdata"]
        completed = pilot.subprocess.CompletedProcess(command, 4, "", "secret initdb output")

        with patch.object(pilot.subprocess, "run", return_value=completed):
            restore = pilot._install_pinned_pg_diagnostics(
                helpers,
                phase_sink=phases.append,
                failure_sink=failures,
            )
            with self.assertRaises(pilot.PilotPostgreSQLFailure):
                helpers.run_command(command, env={})
            restore()

        self.assertIs(helpers.run_command, original_runner)
        self.assertEqual(phases, ["initdb"])
        self.assertEqual(failures[0]["phase"], "initdb")
        self.assertEqual(failures[0]["postgresql_command"]["exit_code"], 4)
        self.assertNotIn("secret", json.dumps(failures))

    def test_identity_mismatch_is_separately_labeled_and_redacted(self):
        def reject_identity(*args):
            raise RuntimeError("identity mismatch at /private/pgdata; secret fields")

        helpers = SimpleNamespace(run_command=lambda *args, **kwargs: None, validate_cluster_identity=reject_identity)
        failures = []
        phases = []
        restore = pilot._install_pinned_pg_diagnostics(
            helpers,
            phase_sink=phases.append,
            failure_sink=failures,
        )
        with self.assertRaises(pilot.PilotPostgreSQLFailure) as caught:
            helpers.validate_cluster_identity([], Path("/private/pgdata"), 5432)
        restore()

        self.assertEqual(phases, ["psql_identity_check"])
        self.assertEqual(caught.exception.record()["postgresql_command"], {
            "program": "psql",
            "cause": "identity_mismatch",
            "exit_code": None,
        })
        self.assertNotIn("private", json.dumps(failures))

    def test_primary_startup_failure_and_cleanup_failure_remain_separate(self):
        primary = pilot.PilotPostgreSQLFailure(
            "psql_identity_check", "psql", "connection_failure", 2
        ).record()
        cleanup = pilot.PilotPostgreSQLFailure(
            "pg_ctl_stop", "pg_ctl", "timeout", None, error_class="TimeoutExpired"
        ).record()
        # A context manager's finally block may surface the cleanup exception last.
        summary = {"status": "FAILED", "error": cleanup}

        pilot._merge_pg_failures(summary, [primary, cleanup])

        self.assertEqual(summary["error"], primary)
        self.assertEqual(summary["cleanup_errors"], [cleanup])

    def test_supervisor_cleanup_failure_keeps_safe_cause_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            runs = base / "runs"
            root = runs / "pilot"
            (root / "cluster" / "pgdata").mkdir(parents=True)
            runtime = base / "runtime"
            runtime.mkdir()
            process = _FakeProcess()
            results = iter(
                (
                    pilot.subprocess.CompletedProcess(["pg_ctl", "status"], 0, "", ""),
                    pilot.subprocess.CompletedProcess(
                        ["pg_ctl", "stop"], 7, "", "pg_ctl: permission denied: secret path"
                    ),
                )
            )

            with (
                patch.object(pilot, "runtime_runs", return_value=runs),
                patch.object(pilot, "configured_root", return_value=runtime),
                patch.object(pilot.subprocess, "Popen", return_value=process),
                patch.object(pilot.subprocess, "run", side_effect=lambda *args, **kwargs: next(results)),
                patch.object(pilot.os, "killpg"),
                patch.object(pilot.time, "sleep"),
                patch("builtins.print"),
                patch.object(pilot, "_allocated_bytes", return_value=pilot.SOFT_STOP_DISK_BYTES),
            ):
                exit_code = pilot._supervise(root)

            summary = json.loads((root / "pilot-supervisor-summary.json").read_text())
            self.assertEqual(exit_code, 2)
            self.assertEqual(
                summary["postgresql_cleanup"],
                {
                    "program": "pg_ctl",
                    "operation": "stop",
                    "exit_code": 7,
                    "cause": "permission_denied",
                },
            )
            self.assertNotIn("secret", json.dumps(summary["postgresql_cleanup"]))


if __name__ == "__main__":
    unittest.main()
