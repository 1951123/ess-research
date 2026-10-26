"""Small frozen-schedule, audit-gate, and ESS diagnostic parser tests."""
from __future__ import annotations

import json
import unittest

import run_issue105 as runner


class Issue105PreflightTests(unittest.TestCase):
    def test_schedule_matches_frozen_nominal_b5_sets_and_overlap_counts(self) -> None:
        protocol = runner.issue101.read_protocol()
        schedule = runner.frozen_schedule(protocol)
        self.assertEqual(set(schedule), set(runner.DATASETS))
        for dataset, record in schedule.items():
            canonical = record["orders"]["canonical"]
            reverse = record["orders"]["reverse"]
            self.assertEqual(canonical, sorted(canonical))
            self.assertEqual(reverse, list(reversed(canonical)))
            self.assertEqual(len(canonical), 5)
        self.assertEqual(
            {dataset: (record["endpoint_conflict_pair_count"],
                       len(record["distinct_conflict_endpoints"]))
             for dataset, record in schedule.items()},
            {"forest10": (3, 3), "census13": (3, 3), "dmv11": (3, 3), "power7": (4, 4)},
        )

    def test_catalog_audit_rejects_wrong_oid_order(self) -> None:
        selected = [f"e00_{index:02d}" for index in range(1, 6)]
        candidates = {
            candidate_id: {
                "statistic_name": f"s_{candidate_id}",
                "catalog_columns": [f"a{index}", f"b{index}"],
            }
            for index, candidate_id in enumerate(selected, start=1)
        }
        good = []
        ledger = []
        for index, candidate_id in enumerate(selected, start=1):
            name = candidates[candidate_id]["statistic_name"]
            columns = candidates[candidate_id]["catalog_columns"]
            oid = index + 9
            keys = f"{index} {index + 5}"
            good.append({
                "oid": oid, "statistic_name": name, "stxkeys": keys,
                "stxkind": "{m}", "statistics_target": 300,
                "attnames": columns, "kinds": ["m"],
                "mcv_payload_present": True, "mcv_item_count": 2,
                "mcv_content_sha256": "a" * 64,
            })
            ledger.append({
                "statistic_name": name, "oid": oid, "stxkeys": keys,
                "statistics_target": 300, "mcv_payload_present": True,
                "mcv_item_count": 2,
            })
        self.assertEqual(
            runner.validate_catalog_rows("forest10", "canonical", selected,
                                         candidates, good, ledger),
            {index + 9: candidate_id for index, candidate_id in enumerate(selected, start=1)},
        )
        with self.assertRaises(RuntimeError):
            runner.validate_catalog_rows("forest10", "canonical", selected,
                                         candidates, list(reversed(good)), ledger)

    def test_explain_parser_maps_selection_and_estimate_oids(self) -> None:
        document = [{
            "Plan": {"Node Type": "Seq Scan", "Plan Rows": 17},
            "ESS Diagnostics": {
                "Status": "complete", "Event Count": 3,
                "Events": [
                    {"sequence": 1, "type": "mcv_selection", "relation_oid": 42,
                     "stat_oid": 1001, "key_count": 2},
                    {"sequence": 2, "type": "mcv_clause", "relation_oid": 42,
                     "stat_oid": 1001, "clause_index": 0},
                    {"sequence": 3, "type": "mcv_estimate", "relation_oid": 42,
                     "stat_oid": 1001, "clause_count": 2, "mcv_sel": 0.25},
                ],
            },
        }]
        parsed = runner.explain_payload(json.dumps(document), {1001: "e00_01"})
        self.assertEqual(parsed["plan_rows"], 17)
        self.assertEqual(parsed["diagnostics_status"], "complete")
        self.assertEqual(parsed["mcv_selection_ids"], ["e00_01"])
        self.assertEqual(parsed["mcv_estimate_ids"], ["e00_01"])
        self.assertEqual(len(parsed["mcv_events"]), 3)
        self.assertEqual(parsed["mcv_events"][-1]["mcv_sel"], 0.25)

    def test_explain_parser_marks_inconsistent_event_count(self) -> None:
        document = [{
            "Plan": {"Node Type": "Seq Scan", "Plan Rows": 17},
            "ESS Diagnostics": {"Status": "complete", "Event Count": 2, "Events": []},
        }]
        parsed = runner.explain_payload(json.dumps(document), {})
        self.assertEqual(parsed["diagnostics_status"], "INVALID_ESS_DIAGNOSTICS_EVENT_COUNT")


if __name__ == "__main__":
    unittest.main()
