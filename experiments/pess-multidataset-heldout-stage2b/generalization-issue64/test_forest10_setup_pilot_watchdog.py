from __future__ import annotations

import errno
import json
import sys
import tempfile
import unittest
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
