from __future__ import annotations

import json
import gzip
import hashlib
import itertools
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
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import SOURCE_COLUMNS
from test_pr7_structured_explain import explain_payload
import run_forest10_full_calibration_collector as full_collector


class Forest10TraceProbeTests(unittest.TestCase):
    def test_full_schedule_reproduces_frozen_call_and_candidate_counts(self):
        subsets = list(itertools.combinations(SOURCE_COLUMNS, 6))
        seven_subsets = list(itertools.combinations(SOURCE_COLUMNS, 7))
        sizes = [6] * 6000 + [7] * 3528 + [0] * 472
        queries = []
        for index, size in enumerate(sizes):
            columns = () if size == 0 else (subsets[index % len(subsets)] if size == 6
                                            else seven_subsets[index % len(seven_subsets)])
            queries.append({
                "query_id": f"arecel:forest10:valid:{index:06d}", "source_index": index,
                "sql": "SELECT * FROM public.forest10 WHERE synthetic = 1",
                "predicates": [{"column": column, "operator": "=", "value": 1} for column in columns],
            })
        discovery = discover_candidates(queries, SOURCE_COLUMNS)
        ordered, candidates, per_candidate = full_collector.build_schedule(
            {"dataset": "forest10", "split": "valid", "queries": queries}, discovery)
        self.assertEqual((len(ordered), len(candidates), sum(map(len, per_candidate.values()))),
                         (10_000, 45, 164_088))
        self.assertEqual(len(per_candidate), 45)
        self.assertEqual(len(ordered) + sum(map(len, per_candidate.values())), 174_088)

    def test_segmented_gzip_writer_fsyncs_and_hashes_bounded_parts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "observations"
            output.mkdir()
            plan = json.loads(full_collector.PLAN.read_text())
            manifest = full_collector._initial_manifest(root, plan)
            calls = []

            def save():
                calls.append(manifest["committed_observation_count"])
                full_collector.atomic_json(root / full_collector.MANIFEST, manifest)

            writer = full_collector.SegmentedJsonl(output, manifest, save)
            for i in range(full_collector.PART_RECORD_LIMIT + 3):
                manifest["attempted_calls"] = i + 1
                manifest["completed_calls"] = i + 1
                writer.write({"sequence": i + 1, "query_id": f"q{i}", "status": "SUCCESS"})
            writer.close()
            self.assertEqual([part["rows"] for part in manifest["parts"]], [2048, 3])
            self.assertTrue(all(part["compressed_bytes"] < 10_000_000 for part in manifest["parts"]))
            self.assertGreaterEqual(len(calls), 2048 // full_collector.FSYNC_BATCH)
            self.assertGreaterEqual(len(manifest["durable_blocks"]), 2048 // full_collector.FSYNC_BATCH)
            self.assertTrue(all(block["gzip_member_sha256"] and block["uncompressed_sha256"]
                                for block in manifest["durable_blocks"]))
            lines = []
            for part in manifest["parts"]:
                path = output / part["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), part["sha256"])
                lines.extend(gzip.open(path, "rt", encoding="utf-8").read().splitlines())
            self.assertEqual(len(lines), full_collector.PART_RECORD_LIMIT + 3)
            self.assertEqual(manifest["committed_observation_count"], len(lines))

    def test_segmented_writer_rotates_at_the_smaller_byte_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "observations"
            output.mkdir()
            manifest = full_collector._initial_manifest(root, json.loads(full_collector.PLAN.read_text()))
            writer = full_collector.SegmentedJsonl(output, manifest,
                                                   lambda: full_collector.atomic_json(root / full_collector.MANIFEST, manifest))
            payload = "x" * 180_000
            for index in range(100):
                manifest["attempted_calls"] += 1
                manifest["completed_calls"] += 1
                writer.write({"sequence": index, "payload": payload})
            writer.close()
            self.assertGreater(len(manifest["parts"]), 2)
            self.assertTrue(all(part["uncompressed_bytes"] <= full_collector.PART_BYTES_LIMIT
                                for part in manifest["parts"]))
            self.assertTrue(all(part["compressed_bytes"] < 10_000_000 for part in manifest["parts"]))
            self.assertTrue(all(len(gzip.open(output / part["path"], "rt").read().splitlines()) == part["rows"]
                                for part in manifest["parts"]))

    def test_handled_interruption_leaves_explicit_incomplete_run_and_no_append_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "observations"
            output.mkdir()
            plan = json.loads(full_collector.PLAN.read_text())
            manifest = full_collector._initial_manifest(root, plan)
            writer = full_collector.SegmentedJsonl(output, manifest,
                                                   lambda: full_collector.atomic_json(root / full_collector.MANIFEST, manifest))
            for index in range(17):
                manifest["attempted_calls"] += 1
                manifest["completed_calls"] += 1
                writer.write({"sequence": index + 1, "status": "SUCCESS"})
            manifest["status"] = "INCOMPLETE"
            manifest["completion"] = "PREFIX_ONLY; NOT ELIGIBLE FOR MODEL FITTING OR SELECTION"
            manifest["unattempted_calls"] -= 17
            writer.close()
            self.assertEqual(manifest["status"], "INCOMPLETE")
            part = output / manifest["parts"][0]["path"]
            with self.assertRaises(FileExistsError):
                part.open("xb")
            self.assertEqual(len(gzip.open(part, "rt").read().splitlines()), 17)

    def test_researcher_approved_plan_and_budget_are_consistent_and_pinned(self):
        plan = json.loads(full_collector.PLAN.read_text())
        digest = full_collector.sha256_file(full_collector.PLAN)
        full_collector.validate_approved_plan(plan, digest)
        for key, value, message in (
            ("status", "CODE_ONLY_REVIEW", "plan is not researcher-approved"),
            ("approved_limits", {"status": "PROPOSED_ONLY_NOT_APPROVED"}, "limits do not match"),
            ("retention", {"status": "NOT_APPROVED"}, "retention does not match"),
        ):
            changed = dict(plan)
            changed[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, message):
                full_collector.validate_approved_plan(changed, digest)
        with self.assertRaisesRegex(RuntimeError, "plan hash mismatch"):
            full_collector.validate_approved_plan(plan, "0" * 64)

    def test_worker_refuses_plan_hash_mismatch_before_runtime_or_build(self):
        with tempfile.TemporaryDirectory() as temporary, unittest.mock.patch.object(
            full_collector, "PLAN", Path(temporary) / "missing-plan.json"
        ), unittest.mock.patch.object(pilot, "_prepare_owned_postgresql") as build:
            root = Path(temporary) / "run"
            root.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, "missing-plan"):
                full_collector._worker(root)
            self.assertFalse((root / full_collector.MANIFEST).exists())
            build.assert_not_called()

    def test_cli_requires_explicit_run_command_before_creating_directory(self):
        with unittest.mock.patch.object(sys, "argv", ["collector"]), \
             unittest.mock.patch.object(full_collector, "runtime_runs") as runtime:
            with self.assertRaisesRegex(SystemExit, "explicit --researcher-approved"):
                full_collector.main()
            runtime.assert_not_called()

    def test_supervisor_nonzero_exit_cannot_leave_success_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = full_collector._initial_manifest(root, json.loads(full_collector.PLAN.read_text()))
            manifest.update({"status": "SUCCESS", "committed_observation_count": 174_088,
                            "attempted_calls": 174_088, "unattempted_calls": 0})
            full_collector.atomic_json(root / full_collector.MANIFEST, manifest)
            full_collector._mark_supervisor_exit(root, 137)
            updated = json.loads((root / full_collector.MANIFEST).read_text())
            self.assertEqual(updated["status"], "INCOMPLETE")
            self.assertEqual(updated["terminal_error"]["return_code"], 137)
            self.assertEqual(updated["unattempted_calls"], 0)

    def run_synthetic_worker(self, *, invalid_json=False, changed_plan=False,
                             fail_after=0, bad_estimate=None, interrupt=False,
                             singleton_config_failure=False):
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
                if selected and singleton_config_failure:
                    raise RuntimeError("synthetic singleton replay failure")
                return [{"oid": 42002, "statistic_name": candidates[e]["statistic_name"]} for e in selected]

            calls = 0

            def explain(*args, **kwargs):
                nonlocal calls
                index = calls
                calls += 1
                if index == fail_after:
                    if interrupt:
                        raise KeyboardInterrupt("synthetic graceful interruption")
                    if invalid_json:
                        return "SET\n[]"
                    if bad_estimate is not None:
                        return explain_payload(include_estimate=False, estimate=bad_estimate)
                return explain_payload(include_estimate=False)

            fake = SimpleNamespace(owned_cluster=owned_cluster, bootstrap_cluster=bootstrap,
                                   sample_header=lambda p: dict(header), sha256_file=probe._sha256,
                                   configure_statistics=configure, os=os,
                                   psql=explain)
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

    def test_failure_after_empty_preserves_prefix_and_stops_singleton(self):
        code, summary, rows, configurations, closed = self.run_synthetic_worker(
            invalid_json=True, fail_after=20)
        self.assertEqual(code, 2)
        self.assertEqual(configurations, [(), ("e00_01",)])
        self.assertEqual(closed, [True])
        self.assertEqual(len(rows), 21)
        self.assertTrue(all(row["status"] == "SUCCESS" and row["config_id"] == "Empty" for row in rows[:20]))
        self.assertEqual((rows[-1]["config_id"], rows[-1]["status"]), ("e00_01", "ERROR"))
        counts = summary["calibration_observations"]
        self.assertEqual((counts["completed_calls"], counts["failed_calls"]), (20, 1))

    def test_invalid_preclamp_never_clamps_or_continues(self):
        for value in (0, -1, "NaN", "Infinity", "-Infinity"):
            with self.subTest(estimate=value):
                code, summary, rows, _, closed = self.run_synthetic_worker(bad_estimate=value, fail_after=2)
                self.assertEqual(code, 2)
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[-1]["status"], "ERROR")
                self.assertIsNone(rows[-1]["nrows_preclamp"])
                self.assertEqual(summary["calibration_observations"]["completed_calls"], 2)
                self.assertEqual(closed, [True])

    def test_graceful_interrupt_retains_prefix_and_closes_cluster(self):
        code, summary, rows, _, closed = self.run_synthetic_worker(interrupt=True, fail_after=3)
        self.assertEqual(code, 2)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[-1]["error_class"], "KeyboardInterrupt")
        self.assertEqual(summary["calibration_observations"]["completed_calls"], 3)
        self.assertEqual(summary["postgresql_shutdown"], "PASS")
        self.assertEqual(closed, [True])

    def test_configuration_failure_is_not_a_fabricated_query_failure(self):
        code, summary, rows, configurations, closed = self.run_synthetic_worker(singleton_config_failure=True)
        self.assertEqual(code, 2)
        self.assertEqual(configurations, [(), ("e00_01",)])
        self.assertEqual(len(rows), 20)
        self.assertTrue(all(row["status"] == "SUCCESS" for row in rows))
        counts = summary["calibration_observations"]
        self.assertEqual((counts["attempted_calls"], counts["completed_calls"], counts["failed_calls"]), (20, 20, 0))
        self.assertEqual(summary["status"], "FAILED")
        self.assertEqual(closed, [True])

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

    def test_full_collector_source_has_no_truth_selection_or_test_path(self):
        collector_path = Path(__file__).parent / "run_forest10_full_calibration_collector.py"
        source = collector_path.read_text()
        for forbidden in ("valid_truth", "test_truth", "calibrate_and_select(", "exact_select_many(",
                          "evaluate_frozen_selections(", "test_workload"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("mkdir(exist_ok=True)", source)

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
