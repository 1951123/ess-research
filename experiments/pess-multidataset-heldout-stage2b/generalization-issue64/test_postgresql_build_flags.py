from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(HERE))
import run_forest10_setup_pilot as pilot


class PostgreSQLTraceBuildFlagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_appends_trace_macro_and_preserves_configured_flags(self) -> None:
        build = self.root / "build"
        makefile = build / "src" / "Makefile.global"
        makefile.parent.mkdir(parents=True)
        makefile.write_text("CFLAGS = -O2 -fno-strict-aliasing\n", encoding="utf-8")

        pilot._enable_legacy_trace_build_flag(build)
        pilot._enable_legacy_trace_build_flag(build)

        result = makefile.read_text(encoding="utf-8")
        self.assertIn("CFLAGS = -O2 -fno-strict-aliasing", result)
        self.assertEqual(result.count(f"CFLAGS += {pilot.LEGACY_TRACE_CFLAG}"), 1)

    def test_missing_or_unconfigured_makefile_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "missing a regular"):
            pilot._enable_legacy_trace_build_flag(self.root / "absent")

        build = self.root / "unconfigured"
        (build / "src").mkdir(parents=True)
        (build / "src/Makefile.global").write_text("CC = cc\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "no configured CFLAGS"):
            pilot._enable_legacy_trace_build_flag(build)

    def test_private_build_applies_flag_after_configure_before_compile(self) -> None:
        run_root = self.root / "run"
        run_root.mkdir()
        source = run_root / "pinned-source"
        source.mkdir()
        observed_phases: list[str] = []

        def fake_build(command, *, cwd, env, log_path, phase, phase_sink, phase_times, timeout):
            observed_phases.append(phase)
            if phase == "postgresql_configure":
                makefile = cwd / "src/Makefile.global"
                makefile.parent.mkdir(parents=True)
                makefile.write_text("CFLAGS = -O2\n", encoding="utf-8")
            elif phase == "postgresql_compile":
                self.assertIn(
                    f"CFLAGS += {pilot.LEGACY_TRACE_CFLAG}",
                    (cwd / "src/Makefile.global").read_text(encoding="utf-8"),
                )
            elif phase == "postgresql_install":
                bin_dir = run_root / "postgresql/install/bin"
                bin_dir.mkdir(parents=True)
                for name in ("postgres", "initdb", "pg_ctl", "psql", "pg_config"):
                    (bin_dir / name).write_bytes(b"synthetic binary")

        version_result = subprocess.CompletedProcess([], 0, stdout="PostgreSQL 16.14\n", stderr="")
        with (
            patch.object(pilot, "_materialize_pinned_postgresql_source", return_value=(source, "a" * 40)),
            patch.object(pilot, "_run_build_command", side_effect=fake_build),
            patch.object(pilot.subprocess, "run", return_value=version_result),
        ):
            _prefix, returned_source, build_summary = pilot._prepare_owned_postgresql(
                run_root, phase_sink=lambda phase: None, phase_times={},
            )

        self.assertEqual(returned_source, source)
        self.assertEqual(
            observed_phases,
            ["postgresql_configure", "postgresql_compile", "postgresql_install"],
        )
        self.assertEqual(build_summary["legacy_trace_compile_definition"], pilot.LEGACY_TRACE_CFLAG)


if __name__ == "__main__":
    unittest.main()
