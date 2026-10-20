"""Offline contract tests for the archive-first Stage 2B Gate A verifier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from gate_audit_v2 import (
    audit_pg_binary,
    aggregate_claimed_clause_coverage,
    capture_query_trace,
    collect_dataset_inputs,
    compute_overall_status,
    evaluate_trace,
    parse_schema_sql,
    sample_header,
    select_validation_queries,
    sha256_file,
    validate_cluster_identity,
    owned_cluster,
    write_exclusive_json,
)


HERE = Path(__file__).parent


class Stage2BGateAV2Tests(unittest.TestCase):
    def test_protocol_freezes_archive_first_crosswalk_and_truth_boundary(self) -> None:
        protocol = json.loads((HERE / "protocol-v3.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "FROZEN_BEFORE_GATE_A_OUTCOME_COLLECTION_V3")
        self.assertEqual(protocol["etl_contract"]["archive_sha256"], "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79")
        self.assertFalse(protocol["scope"]["formal_heldout_outcomes_authorized"])
        forest = protocol["datasets"]["forest10"]
        self.assertEqual(forest["relation"], "public.forest10")
        self.assertEqual(forest["candidates"][0]["source_columns"], ["Elevation", "Aspect"])
        self.assertEqual(forest["candidates"][0]["catalog_columns"], ["elevation", "aspect"])
        self.assertTrue(protocol["fixed_sample_contract"]["old_issue38_sample_reuse"] is False)
        self.assertEqual(sha256_file(HERE / "protocol-v2.json"), "80ea2bfbdbb2a1b2a8e13c2d540c9afe9114cadd55c53a05ddfc9fd9d0476281")
        self.assertEqual(sha256_file(HERE / "protocol-v2-amendment.json"), "94791c70f7ed2e1c3efc56beba758da4a851afd19fdee1517b0849619e1f094b")
        self.assertEqual(protocol["pg_readiness_contract"]["claimed_clause_rule"].split(";")[0], "a probe with no selected MCV OIDs is NOT_APPLICABLE")

    def test_schema_parser_preserves_catalog_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "schema.sql"
            path.write_text(
                'CREATE TABLE public.census13 (\n  "age" DOUBLE PRECISION,\n  "workclass" VARCHAR(64)\n);\n',
                encoding="utf-8",
            )
            self.assertEqual(parse_schema_sql(path), {"age": "DOUBLE PRECISION", "workclass": "VARCHAR(64)"})

    def test_readiness_is_fail_closed_until_all_verified(self) -> None:
        inputs = [{"status": "VERIFIED"}, {"status": "VERIFIED"}]
        source = {"status": "VERIFIED"}
        binary = {"status": "VERIFIED"}
        probes = [{"status": "VERIFIED"}, {"status": "BLOCKED"}]
        self.assertEqual(compute_overall_status(inputs, source, binary, probes, "UNVERIFIED"), "BLOCKED")
        with self.assertRaises(TypeError):
            compute_overall_status(inputs, source, binary, [{"status": "VERIFIED"}, {"status": "VERIFIED"}])
        self.assertEqual(
            compute_overall_status(inputs, source, binary, [{"status": "VERIFIED"}, {"status": "VERIFIED"}], "VERIFIED"),
            "GATE_A_READY",
        )
        self.assertEqual(
            compute_overall_status(inputs, source, binary, [{"status": "VERIFIED"}, {"status": "VERIFIED"}], "UNVERIFIED"),
            "BLOCKED",
        )

    def test_provenance_failure_prevents_runtime_probe(self) -> None:
        protocol = json.loads((HERE / "protocol-v3.json").read_text(encoding="utf-8"))
        with patch("gate_audit_v2.prepare") as prepare, patch(
            "gate_audit_v2.validate_prepared_dataset", return_value={"status": "VERIFIED"}
        ), patch("gate_audit_v2.run_dataset_probe", side_effect=AssertionError("cluster must not start")) as probe:
            prepared = Mock()
            prepare.return_value.__enter__.return_value = prepared
            prepare.return_value.__exit__.return_value = False
            inputs, probes = collect_dataset_inputs(
                protocol, pg_runtime_allowed=False, pg_prefix=Path("/not-used")
            )
        self.assertEqual(len(inputs), 2)
        self.assertEqual(probes, [])
        probe.assert_not_called()

    def test_cluster_identity_and_sample_validation_fail_closed(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_cluster_identity(["/wrong", "5432", "postgres", "PostgreSQL 16.14"], Path("/expected"), 5432)
        with tempfile.TemporaryDirectory() as temporary:
            sample = Path(temporary) / "sample"
            sample.write_bytes(b"ESSANL01")
            with self.assertRaises(ValueError):
                sample_header(sample)
            sample.write_bytes(b"wrong!!!")
            with self.assertRaises(ValueError):
                sample_header(sample)
            with patch("gate_audit_v2.run_command", side_effect=RuntimeError("startup failed")):
                with self.assertRaises(RuntimeError):
                    with owned_cluster(Path(temporary) / "cluster-prefix", Path(temporary) / "cluster", {}):
                        pass

    def test_missing_or_wrong_binary_manifest_cannot_pass(self) -> None:
        self.assertEqual(audit_pg_binary(None, None)["status"], "BLOCKED")
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.json"
            manifest.write_text(json.dumps({"pg_source_commit": "wrong", "pg_source_worktree_clean": True}), encoding="utf-8")
            self.assertEqual(audit_pg_binary(Path(temporary), manifest)["status"], "INCOMPATIBLE")

    def test_trace_contract_failures_are_independent_and_fail_closed(self) -> None:
        ledger = [
            {
                "statistic_name": "candidate",
                "oid": 42,
                "mcv_payload_present": True,
                "mcv_item_count": 3,
            },
            {
                "statistic_name": "empty_candidate",
                "oid": 43,
                "mcv_payload_present": False,
                "mcv_item_count": 0,
            },
        ]
        good = evaluate_trace(
            ["ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1"],
            ledger,
            label="coverage",
            query_id="q",
            expected_statistic_name="candidate",
        )
        self.assertEqual(good["status"], "VERIFIED")
        self.assertEqual(good["claimed_clause_coverage"]["status"], "UNVERIFIED")

        empty_control = evaluate_trace(
            ["ESS_MCV_NUMERIC_TRACE: nrows_preclamp=1"],
            ledger,
            label="control",
            query_id="control",
        )
        fully_claimed = evaluate_trace(
            [
                "ESS_MCV_TRACE: selected_stat_oid=42 claimed_clause_index=0",
                "ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1",
            ],
            ledger,
            label="coverage",
            query_id="q-full",
            expected_statistic_name="candidate",
        )
        partial = evaluate_trace(
            [
                "ESS_MCV_TRACE: selected_stat_oid=42 claimed_clause_index=0",
                "ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1",
                "ESS_MCV_NUMERIC_TRACE: selected_stat_oid=43 nrows_preclamp=1",
            ],
            ledger + [{"statistic_name": "second", "oid": 43, "mcv_payload_present": True, "mcv_item_count": 2}],
            label="coverage",
            query_id="q-partial",
        )
        self.assertEqual(empty_control["claimed_clause_coverage"]["status"], "NOT_APPLICABLE")
        self.assertEqual(fully_claimed["claimed_clause_coverage"]["status"], "VERIFIED")
        self.assertEqual(partial["claimed_clause_coverage"]["status"], "UNVERIFIED")
        self.assertEqual(aggregate_claimed_clause_coverage([empty_control, fully_claimed]), "VERIFIED")
        self.assertEqual(aggregate_claimed_clause_coverage([empty_control, partial]), "UNVERIFIED")

        duplicate = evaluate_trace(
            [
                "ESS_MCV_TRACE: selected_stat_oid=42 claimed_clause_index=0",
                "ESS_MCV_TRACE: selected_stat_oid=42 claimed_clause_index=0",
                "ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1",
            ],
            ledger,
            label="duplicate",
            query_id="q-duplicate",
        )
        self.assertEqual(duplicate["status"], "INCOMPATIBLE")
        self.assertTrue(any("duplicate" in error for error in duplicate["errors"]))

        mismatched = evaluate_trace(
            [
                "ESS_MCV_TRACE: selected_stat_oid=43 claimed_clause_index=0",
                "ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1",
            ],
            ledger,
            label="mismatched",
            query_id="q-mismatched",
        )
        self.assertEqual(mismatched["status"], "INCOMPATIBLE")
        self.assertTrue(any("unselected statistic" in error for error in mismatched["errors"]))

        cases = [
            ([], None, "positive pre-clamp"),
            (["ESS_MCV_NUMERIC_TRACE: selected_stat_oid=99 nrows_preclamp=1"], None, "unmapped"),
            (["ESS_MCV_NUMERIC_TRACE: selected_stat_oid=43 nrows_preclamp=1"], "empty_candidate", "positive MCV"),
        ]
        for lines, expected, fragment in cases:
            with self.subTest(fragment=fragment):
                result = evaluate_trace(
                    lines,
                    ledger,
                    label="negative",
                    query_id="q",
                    expected_statistic_name=expected,
                )
                self.assertEqual(result["status"], "INCOMPATIBLE")
                self.assertTrue(any(fragment.lower() in error.lower() for error in result["errors"]))

    def test_pid_scoped_capture_keeps_marker_free_mcv_and_filters_foreign_backend(self) -> None:
        marker = "issue56-probe-one"
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "server.log"
            log.write_text(
                "2026-10-20 00:00:00 [101] w@p DEBUG: ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1 query=/* "
                + marker
                + " */\n"
                "2026-10-20 00:00:00 [202] w@p DEBUG: ESS_MCV_TRACE: selected_stat_oid=99 claimed_clause_index=7\n"
                "2026-10-20 00:00:00 [101] w@p DEBUG: ESS_MCV_TRACE: selected_stat_oid=42 claimed_clause_index=0\n",
                encoding="utf-8",
            )
            capture = capture_query_trace(log, 0, marker, quiet_period=0)
        self.assertEqual(capture["backend_pid"], "101")
        self.assertEqual(len(capture["raw_numeric_trace_lines"]), 1)
        self.assertEqual(len(capture["raw_mcv_trace_lines"]), 2)
        self.assertEqual(len(capture["associated_mcv_trace_lines"]), 1)
        self.assertEqual(len(capture["foreign_mcv_trace_lines"]), 1)
        self.assertEqual(len(capture["associated_trace_lines"]), 2)

    def test_pid_capture_supports_disjoint_probes_on_same_backend(self) -> None:
        first = "issue56-probe-first"
        second = "issue56-probe-second"
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "server.log"
            log.write_text(
                f"2026-10-20 00:00:00 [303] w@p DEBUG: ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1 query=/* {first} */\n",
                encoding="utf-8",
            )
            first_capture = capture_query_trace(log, 0, first, quiet_period=0)
            log.write_text(
                log.read_text(encoding="utf-8")
                + f"2026-10-20 00:00:01 [303] w@p DEBUG: ESS_MCV_NUMERIC_TRACE: selected_stat_oid=43 nrows_preclamp=2 query=/* {second} */\n"
                + "2026-10-20 00:00:01 [303] w@p DEBUG: ESS_MCV_TRACE: selected_stat_oid=43 claimed_clause_index=1\n",
                encoding="utf-8",
            )
            second_capture = capture_query_trace(
                log,
                first_capture["end_offset"],
                second,
                previous_markers={first},
                quiet_period=0,
            )
        self.assertEqual(first_capture["backend_pid"], second_capture["backend_pid"])
        self.assertEqual(len(second_capture["associated_trace_lines"]), 2)
        self.assertTrue(all(second not in line or "[303]" in line for line in second_capture["associated_trace_lines"]))

    def test_pid_capture_fails_closed_for_missing_or_ambiguous_pid_and_absent_raw_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing-pid.log"
            missing.write_text(
                "DEBUG: ESS_MCV_NUMERIC_TRACE: selected_stat_oid=42 nrows_preclamp=1 query=/* marker */\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "backend PID"):
                capture_query_trace(missing, 0, "marker", quiet_period=0)

            ambiguous = root / "ambiguous.log"
            ambiguous.write_text(
                "2026-10-20 00:00:00 [1] w@p DEBUG: ESS_MCV_NUMERIC_TRACE: nrows_preclamp=1 query=/* marker */\n"
                "2026-10-20 00:00:00 [2] w@p DEBUG: ESS_MCV_NUMERIC_TRACE: nrows_preclamp=2 query=/* marker */\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                capture_query_trace(ambiguous, 0, "marker", quiet_period=0)

            with self.assertRaisesRegex(RuntimeError, "absent"):
                capture_query_trace(root / "absent.log", 0, "marker", quiet_period=0)

    def test_validation_probe_selection_is_shape_and_catalog_only(self) -> None:
        protocol = json.loads((HERE / "protocol-v3.json").read_text(encoding="utf-8"))
        spec = protocol["datasets"]["forest10"]
        queries = [
            {"query_id": "q0", "predicates": [{"column": "Elevation"}, {"column": "Aspect"}], "sql": "SELECT *"},
            {"query_id": "q1", "predicates": [{"column": "Aspect"}, {"column": "Slope"}], "sql": "SELECT *"},
        ]
        ledger = [
            {"statistic_name": "ess2b_forest10_e01", "oid": 1, "mcv_payload_present": False},
            {"statistic_name": "ess2b_forest10_e12", "oid": 2, "mcv_payload_present": True},
        ]
        selected = select_validation_queries(queries, spec, ledger)
        self.assertEqual(selected["control"]["query_id"], "q0")
        self.assertEqual(selected["mcv_coverage"]["candidate_id"], "e12")
        self.assertEqual(selected["mcv_coverage"]["query"]["query_id"], "q1")

    def test_evidence_write_is_exclusive_and_does_not_follow_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "result.json"
            write_exclusive_json(output, {"value": 1})
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                write_exclusive_json(output, {"value": 2})
            self.assertEqual(output.read_bytes(), original)

            dangling = root / "dangling.json"
            os.symlink(root / "missing.json", dangling)
            with self.assertRaises(FileExistsError):
                write_exclusive_json(dangling, {"value": 3})
            self.assertTrue(dangling.is_symlink())


if __name__ == "__main__":
    unittest.main()
