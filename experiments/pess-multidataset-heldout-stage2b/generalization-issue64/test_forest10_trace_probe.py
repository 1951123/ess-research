from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_forest10_setup_pilot as pilot
import run_forest10_trace_probe as probe
from ess_research.arecel.forest10 import SOURCE_COLUMNS
from test_pr7_structured_explain import explain_payload


class Forest10TraceProbeTests(unittest.TestCase):
    def run_synthetic_worker(self, *, invalid_json=False, changed_plan=False):
        """Exercise the real orchestration/adapter; only external I/O is fake."""
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary) / "run"
            root.mkdir()
            queries = [{"query_id": f"arecel:forest10:valid:{i:06d}", "source_index": i,
                        "sql": "SELECT * FROM public.forest10 WHERE synthetic = 1",
                        "predicates": [{"column": c, "operator": "=", "value": 1}
                                       for c in SOURCE_COLUMNS[:2]]} for i in range(10_000)]
            workload = {"dataset": "forest10", "split": "valid", "queries": queries}
            discovery = {"candidate_count": 45, "candidates": [
                {"column_a": a, "column_b": b, "eligible_valid_query_count": 164_044 if i == 0 else 1}
                for i, (a, b) in enumerate(combinations(SOURCE_COLUMNS, 2))]}
            original_discover = probe.discover_candidates
            stack.enter_context(patch.object(probe, "discover_candidates", side_effect=lambda qs, cs:
                discovery if len(qs) == 10_000 else original_discover(qs, cs)))
            plan = probe._call_plan(workload, discovery, "synthetic-archive")
            self.assertEqual(plan["expected_structured_explain_calls"], 40)
            self.assertEqual(plan["configuration_order"], ["Empty", "e00_01"])
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(plan))
            if changed_plan:
                queries[0]["sql"] += " /* changed identity */"
            workload_path = root / "workload.json"
            workload_path.write_text(json.dumps(workload))

            @contextmanager
            def prepare(**kwargs):
                yield SimpleNamespace(workload_path=workload_path,
                                      manifest={"labels_loaded": False, "archive_sha256": "synthetic-archive"})

            closed = []

            @contextmanager
            def owned_cluster(*args):
                try:
                    yield {"socket_dir": root / "socket", "port": 12345}
                finally:
                    closed.append(True)

            header = {"relation_identity": "6:public8:forest10", "server_version": "16.14",
                      "natts": 10, "relation_oid": 42001}
            configurations = []

            def bootstrap(*args):
                # Real bootstrap owns results already; the runner must tolerate it.
                (root / "results").mkdir()
                sample = root / "results" / "sample.bin"
                sample.write_bytes(b"synthetic sample")
                return sample, {"table": "public.forest10", "header": header,
                                "sha256": probe._sha256(sample), "bytes": sample.stat().st_size}

            def configure(prefix, cluster, dataset, candidates, selected, sample):
                configurations.append(selected)
                return [{"oid": 42002, "statistic_name": candidates[e]["statistic_name"]} for e in selected]

            fake = SimpleNamespace(owned_cluster=owned_cluster, bootstrap_cluster=bootstrap,
                                   sample_header=lambda p: dict(header), sha256_file=probe._sha256,
                                   configure_statistics=configure, os=os,
                                   psql=lambda *args, **kwargs: "SET\n[]" if invalid_json else explain_payload(include_estimate=False))
            for name, value in {"FROZEN_PLAN": plan_path, "runtime_runs": lambda *a: root.parent,
                                "configured_root": lambda *a: root.parent,
                                "prepare_valid_workload": prepare}.items():
                stack.enter_context(patch.object(probe, name, value))
            stack.enter_context(patch.object(pilot, "_validate_socket_path"))
            stack.enter_context(patch.object(pilot, "_load_pinned_pr58_modules", return_value=(fake, fake, {})))
            stack.enter_context(patch.object(pilot, "_extract_csv"))
            build = stack.enter_context(patch.object(pilot, "_prepare_owned_postgresql",
                                                     return_value=(root / "install", root / "source", {})))
            stack.enter_context(patch.object(pilot, "_install_pinned_pg_diagnostics", return_value=lambda: None))
            code = probe._worker(root)
            summary = json.loads((root / probe.SUMMARY_NAME).read_text())
            path = root / "results" / probe.OBSERVATIONS_NAME
            rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
            if changed_plan:
                build.assert_not_called()
            return code, summary, rows, configurations, closed

    def test_complete_synthetic_worker_validates_sample_and_existing_results_directory(self):
        code, summary, rows, configurations, closed = self.run_synthetic_worker()
        self.assertEqual(code, 0, summary)
        self.assertEqual(configurations, [(), ("e00_01",)])
        self.assertEqual(closed, [True])
        self.assertEqual(summary["postgresql_shutdown"], "PASS")
        self.assertEqual(summary["sample"]["header"]["relation_oid"], 42001)
        self.assertEqual(summary["calibration_observations"]["completed_calls"], 40)
        self.assertEqual(len(rows), 40)
        self.assertTrue(all(row["mcv_diagnostics_status"] == "NO_MCV_EVENTS" for row in rows))
        self.assertEqual([row["query_id"] for row in rows[:20]],
                         [f"arecel:forest10:valid:{i:06d}" for i in range(20)])

    def test_worker_retains_first_error_and_stops_without_retry(self):
        code, summary, rows, configurations, closed = self.run_synthetic_worker(invalid_json=True)
        self.assertEqual(code, 2)
        self.assertEqual(configurations, [()])
        self.assertEqual(closed, [True])
        counts = summary["calibration_observations"]
        self.assertEqual((counts["attempted_calls"], counts["completed_calls"], counts["failed_calls"]), (1, 0, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "ERROR")
        self.assertIsNone(rows[0]["nrows_preclamp"])

    def test_changed_identity_is_rejected_before_postgresql_build(self):
        code, summary, rows, configurations, closed = self.run_synthetic_worker(changed_plan=True)
        self.assertEqual(code, 2)
        self.assertEqual(summary["error"]["phase"], "valid_workload_and_candidate_preflight")
        self.assertEqual((rows, configurations, closed), ([], [], []))

    def test_executable_runners_do_not_reference_issue38_runtime_artifacts(self):
        for name in ("run_forest10_setup_pilot.py", "run_forest10_trace_probe.py"):
            source = (Path(__file__).parent / name).read_text(encoding="utf-8")
            for legacy in ("issue38/pg-prefix", "issue38/pg-src", "issue38/results/heldout-v1", "replay-sample.bin"):
                with self.subTest(script=name, legacy=legacy):
                    self.assertNotIn(legacy, source)

    def test_active_calibration_paths_are_json_only(self):
        pilot_source = (Path(__file__).parent / "run_forest10_setup_pilot.py").read_text(encoding="utf-8")
        smoke_source = (Path(__file__).parent / "run_forest10_trace_probe.py").read_text(encoding="utf-8")
        runner_source = (Path(__file__).parent / "forest10_runner.py").read_text(encoding="utf-8")
        self.assertNotIn("ESS_MCV_NUMERIC_TRACE", pilot_source)
        self.assertNotIn("run_formal.run_query(", pilot_source)
        self.assertNotIn("run_formal.run_query", smoke_source)
        self.assertIn("PR7StructuredExplainAdapter", runner_source)
        self.assertIn("adapter.explain(query)", runner_source)
        self.assertNotIn("Plan Rows", smoke_source)

    def test_fixed_valid_query_schedule_and_maximum_calls(self):
        indices = probe._selected_source_indices()
        self.assertEqual(len(indices), 20)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 19)
        self.assertEqual(indices, tuple(range(20)))
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
        record = probe._safe_probe_error(RuntimeError("estimate=999 SQL=secret"), "structured_json")
        self.assertEqual(record["phase"], "structured_json")
        self.assertNotIn("999", json.dumps(record))
        self.assertNotIn("secret", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
