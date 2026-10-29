"""Synthetic and frozen-input checks for the Issue #133 DMV11 runner."""
from __future__ import annotations

import json
import unittest

import run_minimal_dmv11 as runner
import analyze_minimal_dmv11 as analyzer


class FrozenDesignTests(unittest.TestCase):
    def test_frozen_three_arm_universe_orders_and_nominal_projection(self) -> None:
        protocol = json.loads(runner.PROTOCOL_PATH.read_text(encoding="utf-8"))
        _inventory, candidates, orders, frozen = runner.read_frozen_inputs(protocol)
        self.assertEqual(len(candidates), 55)
        self.assertEqual(len(orders[runner.ALL01]), 55)
        self.assertEqual(len(orders[runner.ALL02]), 55)
        self.assertEqual(len(orders[runner.B5]), 5)
        self.assertEqual(orders[runner.B5], protocol["order_pins"]["b5_order"])
        self.assertEqual(
            [candidate for candidate in orders[runner.ALL01]
             if candidate in set(protocol["frozen_nominal_b5"]["selected_candidate_ids"])],
            orders[runner.B5],
        )
        self.assertEqual(frozen["projection_random02"], protocol["order_pins"]["random02_b5_projection"])
        self.assertNotEqual(frozen["projection_random02"], orders[runner.B5])


class OidAndDiagnosticsTests(unittest.TestCase):
    def test_normalizes_numeric_and_json_string_oid_keys(self) -> None:
        self.assertEqual(runner.normalize_oid_map({16387: "e02_08"}), {16387: "e02_08"})
        self.assertEqual(runner.normalize_oid_map({"16387": "e02_08"}), {16387: "e02_08"})

    def test_rejects_oid_key_collisions_after_normalization(self) -> None:
        with self.assertRaisesRegex(runner.Inconclusive, "duplicate OID"):
            runner.normalize_oid_map({16387: "e02_08", "16387": "e03_04"})

    def test_numeric_event_oid_maps_with_json_string_key_and_preserves_extension_status(self) -> None:
        raw_event = {
            "sequence": 1,
            "type": "mcv_selection",
            "stat_oid": 16387,
            "clause_index": 2,
            "custom_extension_field": "kept",
        }
        payload = json.dumps([{
            "Plan": {"Plan Rows": 7},
            "ESS Diagnostics": {
                "Status": "complete",
                "Event Count": 1,
                "Events": [raw_event],
            },
        }])
        parsed = runner.parse_explain_payload(payload, {"16387": "e02_08"})
        self.assertEqual(parsed["plan_rows"], 7)
        self.assertEqual(parsed["plan_rows_integrity_status"], "VALID")
        self.assertEqual(parsed["extension_diagnostics_status"], "complete")
        self.assertEqual(parsed["diagnostics_status"], "complete")
        self.assertEqual(parsed["diagnostics_integrity_status"], "PASS")
        self.assertEqual(parsed["candidate_id_attribution_status"], "PASS")
        self.assertEqual(parsed["mcv_selection_ids"], ["e02_08"])
        self.assertEqual(parsed["mcv_events"][0]["custom_extension_field"], "kept")
        self.assertEqual(parsed["raw_ess_diagnostics"]["Events"][0], raw_event)

    def test_unknown_oid_retains_event_and_does_not_overwrite_extension_status(self) -> None:
        raw_event = {
            "sequence": 9,
            "type": "mcv_estimate",
            "stat_oid": 99999,
            "mcv_sel": 0.25,
        }
        payload = json.dumps([{
            "Plan": {"Plan Rows": 11},
            "ESS Diagnostics": {
                "Status": "complete",
                "Event Count": 1,
                "Events": [raw_event],
            },
        }])
        parsed = runner.parse_explain_payload(payload, {16387: "e02_08"})
        self.assertEqual(parsed["extension_diagnostics_status"], "complete")
        self.assertEqual(parsed["diagnostics_status"], "complete")
        self.assertEqual(parsed["diagnostics_integrity_status"], "PASS")
        self.assertEqual(parsed["candidate_id_attribution_status"], "UNKNOWN_STAT_OID")
        self.assertEqual(parsed["unknown_stat_oids"], [99999])
        self.assertIsNone(parsed["mcv_events"][0]["candidate_id"])
        self.assertEqual(parsed["mcv_events"][0]["stat_oid"], 99999)
        self.assertEqual(parsed["raw_ess_diagnostics"]["Events"][0], raw_event)

    def test_missing_and_malformed_diagnostics_are_separate_from_plan_rows(self) -> None:
        payload = json.dumps([{"Plan": {"Plan Rows": 3}}])
        parsed = runner.parse_explain_payload(payload, {})
        self.assertEqual(parsed["status"], "VALID")
        self.assertEqual(parsed["plan_rows_integrity_status"], "VALID")
        self.assertIsNone(parsed["extension_diagnostics_status"])
        self.assertEqual(parsed["diagnostics_integrity_status"], "MISSING_ESS_DIAGNOSTICS")
        self.assertEqual(parsed["candidate_id_attribution_status"], "PASS_EMPTY")

    def test_batch_parser_keeps_unknown_event_and_raw_status(self) -> None:
        payload = json.dumps([{
            "Plan": {"Plan Rows": 5},
            "ESS Diagnostics": {
                "Status": "complete",
                "Event Count": 1,
                "Events": [{"sequence": 1, "type": "mcv_selection", "stat_oid": 88888}],
            },
        }])
        stdout = "\n".join([
            "__ISSUE105_BEGIN_00000__",
            payload,
            "__ISSUE105_END_00000__",
        ])
        row = runner.parse_batch_output(stdout, 1, {"16387": "e02_08"})[0]
        self.assertTrue(row["explain_begin_seen"])
        self.assertTrue(row["explain_end_seen"])
        self.assertEqual(row["extension_diagnostics_status"], "complete")
        self.assertEqual(row["candidate_id_attribution_status"], "UNKNOWN_STAT_OID")
        self.assertEqual(row["mcv_events"][0]["stat_oid"], 88888)


class PairedAnalysisTests(unittest.TestCase):
    def test_pairwise_direction_and_candidate_use_counts(self) -> None:
        left = [{
            "query_id": "q1", "estimate_plan_rows": 20, "qerror": 2.0,
            "mcv_selection_ids": ["extra", "shared"],
        }]
        right = [{
            "query_id": "q1", "estimate_plan_rows": 10, "qerror": 1.0,
            "mcv_selection_ids": ["shared"],
        }]
        paired = analyzer.paired(
            left, right, "all", "b5", all_only_ids={"extra"}, shared_ids={"shared"}
        )
        self.assertEqual(paired["left_minus_right"], "all - b5")
        self.assertEqual(paired["plan_rows_changed_count"], 1)
        self.assertEqual(paired["qerror_changed_count"], 1)
        self.assertEqual(paired["left_qerror_worse_count"], 1)
        self.assertEqual(paired["left_queries_using_any_all_only_candidate_count"], 1)
        self.assertEqual(paired["left_all_only_candidate_event_count"], 1)
        self.assertEqual(paired["shared_candidate_query_usage_counts"]["shared"], {"all": 1, "b5": 1})


if __name__ == "__main__":
    unittest.main()
