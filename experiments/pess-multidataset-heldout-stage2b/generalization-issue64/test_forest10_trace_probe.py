from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_forest10_setup_pilot as pilot
import run_forest10_trace_probe as probe
from ess_research.arecel.forest10 import SOURCE_COLUMNS


class Forest10TraceProbeTests(unittest.TestCase):
    def test_executable_runners_do_not_reference_issue38_runtime_artifacts(self):
        for name in ("run_forest10_setup_pilot.py", "run_forest10_trace_probe.py"):
            source = (Path(__file__).parent / name).read_text(encoding="utf-8")
            for legacy in ("issue38/pg-prefix", "issue38/pg-src", "issue38/results/heldout-v1", "replay-sample.bin"):
                with self.subTest(script=name, legacy=legacy):
                    self.assertNotIn(legacy, source)

    def test_fixed_valid_query_schedule_and_maximum_calls(self):
        indices = probe._selected_source_indices()
        self.assertEqual(len(indices), 20)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 9500)
        self.assertEqual(indices, tuple(range(0, 10_000, 500)))
        self.assertEqual(probe._bounded_call_count({index: () for index in indices}), 20)
        self.assertEqual(
            probe._bounded_call_count({index: tuple(f"e{i:02d}" for i in range(45)) for index in indices}),
            920,
        )
        with self.assertRaises(ValueError):
            probe._selected_source_indices(9_999)
        with self.assertRaises(ValueError):
            probe._bounded_call_count({0: ()})

    def test_candidate_ids_follow_pinned_schema_order(self):
        discovery = {
            "candidates": [
                {"column_a": SOURCE_COLUMNS[0], "column_b": SOURCE_COLUMNS[1], "eligible_valid_query_count": 12},
                {"column_a": SOURCE_COLUMNS[1], "column_b": SOURCE_COLUMNS[9], "eligible_valid_query_count": 7},
            ]
        }
        candidates, support_sum = probe._candidate_rows(discovery)
        self.assertEqual(candidates, [("e00_01", (SOURCE_COLUMNS[0], SOURCE_COLUMNS[1])),
                                      ("e01_09", (SOURCE_COLUMNS[1], SOURCE_COLUMNS[9]))])
        self.assertEqual(support_sum, 19)

    def test_custom_watchdog_thresholds_are_independent_of_setup_pilot_defaults(self):
        self.assertIsNone(pilot._watchdog_stop_reason(100, 100, disk_threshold_bytes=200, wall_threshold_seconds=200))
        self.assertEqual(
            pilot._watchdog_stop_reason(200, 1, disk_threshold_bytes=200, wall_threshold_seconds=200),
            "disk_safety_abort_custom",
        )
        self.assertEqual(
            pilot._watchdog_stop_reason(1, 200, disk_threshold_bytes=200, wall_threshold_seconds=200),
            "wall_safety_abort_custom",
        )
        self.assertEqual(
            pilot._watchdog_stop_reason(0, pilot.SOFT_STOP_SECONDS),
            "wall_safety_abort_28_minutes",
        )

    def test_non_postgresql_failure_does_not_retain_error_text(self):
        record = probe._safe_probe_error(RuntimeError("estimate=999 SQL=secret"), "trace")
        self.assertEqual(record["phase"], "trace")
        self.assertNotIn("999", json.dumps(record))
        self.assertNotIn("secret", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
