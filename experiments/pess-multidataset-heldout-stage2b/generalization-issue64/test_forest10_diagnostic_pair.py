from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_forest10_setup_pilot as pilot


class FixedPilotQueryTests(unittest.TestCase):
    def test_resolves_only_the_predeclared_valid_query(self) -> None:
        queries = [object() for _ in range(10_000)]
        with (
            patch.object(pilot, "_query", return_value={"sql": "SELECT * FROM public.forest10 WHERE elevation = 1"}) as parse,
            patch.object(pilot, "_valid_candidate", return_value=True) as eligible,
        ):
            result = pilot._fixed_valid_query(queries)
        self.assertEqual(result["query_id"], "arecel:forest10:valid:000005")
        self.assertEqual(result["source_index"], 5)
        parse.assert_called_once_with(queries[5], "forest10")
        eligible.assert_called_once()

    def test_does_not_substitute_when_fixed_query_is_ineligible(self) -> None:
        queries = [object() for _ in range(10_000)]
        with (
            patch.object(pilot, "_query", return_value={"sql": "SELECT * FROM public.forest10 WHERE elevation = 1"}) as parse,
            patch.object(pilot, "_valid_candidate", return_value=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "fixed official valid query"):
                pilot._fixed_valid_query(queries)
        parse.assert_called_once_with(queries[5], "forest10")


class DiagnosticPairTests(unittest.TestCase):
    def test_legacy_trace_summary_keeps_only_required_oid_clause_and_numeric_fields(self) -> None:
        numeric = {name: "0.25" for name in pilot.MCV_NUMERIC_FIELDS}
        trace = {
            "status": "VERIFIED",
            "numeric": [
                {"base_relation_oid": "42", "nrows_preclamp": "123.000"},
                {"relid": "42", "selected_stat_oid": "9001", **numeric},
            ],
            "selected_stat_oids": ["9001"],
            "claimed_clause_coverage": {
                "claimed_clauses_by_stat_oid": {"9001": ["1", "0"]},
            },
        }
        helpers = SimpleNamespace(evaluate_trace=lambda *_args, **_kwargs: trace)
        result = pilot._legacy_trace_summary(
            helpers,
            {"raw_associated_trace_lines": ["raw secret trace"], "estimate_preclamp": "123"},
            [{"oid": 9001}],
            {"query_id": pilot.PILOT_QUERY_ID},
            "fixed-marker",
        )
        self.assertEqual(result["relation_oid"], 42)
        self.assertEqual(result["mcv_records"][0]["stat_oid"], 9001)
        self.assertEqual(result["mcv_records"][0]["clause_indexes"], [0, 1])
        self.assertEqual(set(result["mcv_records"][0]["numeric_terms"]), set(pilot.MCV_NUMERIC_FIELDS))
        self.assertNotIn("raw_associated_trace_lines", result)
        self.assertNotIn("raw secret trace", repr(result))

    def test_base_decimal_formatting_is_compared_numerically_and_empty_mcv_is_unverified(self) -> None:
        result = pilot._compare_diagnostic_summaries(
            {"diagnostics_status": "VERIFIED", "relation_oid": 42, "estimate_preclamp": "123.000", "mcv_records": []},
            {"diagnostics_status": "complete", "relation_oid": 42, "estimate_preclamp": "123", "mcv_records": []},
        )
        self.assertEqual(result["status"], "BASE_MATCH_MCV_NOT_VERIFIED")
        self.assertEqual(result["preclamp_delta_legacy_minus_structured"], "0.000")
        self.assertEqual(result["mcv_hit_parity"], "NOT_VERIFIED_NO_MCV_EVENTS")

    def test_compares_mcv_oid_clause_indexes_and_all_five_numeric_terms(self) -> None:
        terms = {name: "0.125" for name in pilot.MCV_NUMERIC_FIELDS}
        legacy_mcv = [{"relation_oid": 42, "stat_oid": 9001, "clause_indexes": [0, 1], "numeric_terms": terms}]
        structured_mcv = [{"relation_oid": 42, "stat_oid": 9001, "clause_indexes": [0, 1], **terms}]
        result = pilot._compare_diagnostic_summaries(
            {"diagnostics_status": "VERIFIED", "relation_oid": 42, "estimate_preclamp": "10", "mcv_records": legacy_mcv},
            {"diagnostics_status": "complete", "relation_oid": 42, "estimate_preclamp": "10.0", "mcv_records": structured_mcv},
        )
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["mcv_hit_parity"], "MATCH")
        self.assertEqual(set(result["mcv_records"][0]["numeric_terms"]), set(pilot.MCV_NUMERIC_FIELDS))

    def test_mcv_presence_mismatch_fails_comparison(self) -> None:
        mcv = [{"relation_oid": 42, "stat_oid": 9001, "clause_indexes": [0], "numeric_terms": {name: "0.1" for name in pilot.MCV_NUMERIC_FIELDS}}]
        result = pilot._compare_diagnostic_summaries(
            {"diagnostics_status": "VERIFIED", "relation_oid": 42, "estimate_preclamp": "10", "mcv_records": mcv},
            {"diagnostics_status": "complete", "relation_oid": 42, "estimate_preclamp": "10", "mcv_records": []},
        )
        self.assertEqual(result["status"], "MISMATCH_MCV_EVENT_PRESENCE")

    def test_base_mismatch_is_reported_with_exact_decimal_delta(self) -> None:
        result = pilot._compare_diagnostic_summaries(
            {"diagnostics_status": "VERIFIED", "relation_oid": 42, "estimate_preclamp": "10.01", "mcv_records": []},
            {"diagnostics_status": "complete", "relation_oid": 42, "estimate_preclamp": "10.00", "mcv_records": []},
        )
        self.assertEqual(result["status"], "MISMATCH_PRECLAMP")
        self.assertEqual(result["preclamp_delta_legacy_minus_structured"], "0.01")

    def test_classifies_only_the_two_authorized_explain_forms(self) -> None:
        prefix = ["/pg/bin/psql", "-c"]
        legacy = "SET client_min_messages=debug1; SET plan_cache_mode=force_custom_plan; SET max_parallel_workers_per_gather=0; EXPLAIN (FORMAT JSON, SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE marker */ SELECT * FROM public.forest10 WHERE elevation=1"
        structured = "SET client_min_messages=warning; SET plan_cache_mode=force_custom_plan; SET max_parallel_workers_per_gather=0; EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF) SELECT * FROM public.forest10 WHERE elevation=1"
        self.assertEqual(pilot._classify_pg_command([*prefix, legacy])[0], "legacy_trace_valid_explain")
        self.assertEqual(pilot._classify_pg_command([*prefix, structured])[0], "structured_valid_explain")


if __name__ == "__main__":
    unittest.main()
