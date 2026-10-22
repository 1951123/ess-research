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


class PostgreSQLJSONOnlyBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_private_build_has_no_legacy_trace_macro_phase_or_prerequisite(self) -> None:
        run_root = self.root / "run"
        run_root.mkdir()
        source = run_root / "pinned-source"
        source.mkdir()
        observed_phases: list[str] = []

        def fake_build(command, *, cwd, env, log_path, phase, phase_sink, phase_times, timeout):
            observed_phases.append(phase)
            if phase == "postgresql_install":
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
        self.assertEqual(
            build_summary["calibration_interface"],
            "PR7StructuredExplainAdapter; ESS_DIAGNOSTICS JSON",
        )
        self.assertFalse(hasattr(pilot, "LEGACY_TRACE_CFLAG"))

    def test_authoritative_json_config_preserves_frozen_science_and_transport(self) -> None:
        config = Path(__file__).with_name("forest10-json-only-v2.json")
        document = __import__("json").loads(config.read_text(encoding="utf-8"))
        self.assertEqual(document["scope"]["candidate_universe_count"], 45)
        self.assertEqual(document["scope"]["budgets_preserved_for_later_selection"], [0, 2, 3])
        self.assertEqual(document["active_calibration_interface"]["adapter"], "PR7StructuredExplainAdapter")
        self.assertIn("nrows_preclamp", document["active_calibration_interface"]["estimate_field"])
        self.assertEqual(document["phase_b_integration_pilot"]["legacy_server_log_calls"], 0)
        self.assertTrue(document["phase_c_observation_smoke"]["run_only_if_phase_b_success"])


if __name__ == "__main__":
    unittest.main()
