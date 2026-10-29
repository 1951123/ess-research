import gzip
import math
import unittest

import numpy as np

import recompute_issue133 as audit


class RecomputeIssue133Tests(unittest.TestCase):
    def test_issue101_zero_aware_qerror_cases(self):
        self.assertEqual(audit.qerror_for_plan_rows(0, 0), (1.0, 0))
        self.assertEqual(audit.qerror_for_plan_rows(0, 7), (7.0, 0))
        self.assertEqual(audit.qerror_for_plan_rows(9, 0), (9.0, 9))
        self.assertEqual(audit.qerror_for_plan_rows(8, 2), (4.0, 8))
        self.assertEqual(audit.qerror_for_plan_rows(2, 8), (4.0, 2))

    def test_numpy_percentile_semantics_are_default_linear_method(self):
        summary = audit.summarize_errors([1.0, 2.0, 3.0, 4.0])
        self.assertTrue(math.isclose(summary["p50"], 2.5))
        self.assertTrue(math.isclose(summary["p95"], 3.85))
        self.assertTrue(math.isclose(summary["p99"], 3.97))
        self.assertEqual(summary["mean"], 2.5)
        self.assertEqual(summary["max"], 4.0)
        self.assertEqual(np.__version__, audit.np.__version__)

    def test_concatenated_gzip_member_boundaries_and_hashes(self):
        first = gzip.compress(b'{"row":1}\n')
        second = gzip.compress(b'{"row":2}\n')
        members = audit.split_gzip_members(first + second)
        self.assertEqual(len(members), 2)
        self.assertEqual([member["offset"] for member in members], [0, len(first)])
        self.assertEqual([member["payload"] for member in members], [b'{"row":1}\n', b'{"row":2}\n'])
        self.assertTrue(all(member["eof"] for member in members))

    def test_truncated_gzip_member_is_rejected(self):
        with self.assertRaises(ValueError):
            audit.split_gzip_members(gzip.compress(b"data")[:-2])

    def test_json_string_oid_key_maps_numeric_event_oid(self):
        row = {
            "mcv_events": [
                {"type": "mcv_selection", "stat_oid": 16390},
                {"type": "mcv_estimate", "stat_oid": 16390},
            ]
        }
        selection, estimates, issues = audit.event_sequences(
            row, {"16390": "e00_01"}, {"e00_01"}
        )
        self.assertEqual(selection, ("e00_01",))
        self.assertEqual(estimates, ("e00_01",))
        self.assertEqual(issues, [])

    def test_unknown_oid_is_preserved_as_mapping_issue(self):
        row = {"mcv_events": [{"type": "mcv_selection", "stat_oid": 99999}]}
        selection, estimates, issues = audit.event_sequences(row, {"16390": "e00_01"}, {"e00_01"})
        self.assertEqual(selection, ())
        self.assertEqual(estimates, ())
        self.assertEqual(issues, ["unmapped_stat_oid:99999"])

    def test_incomplete_configuration_cannot_be_summarized(self):
        row = {
            "configuration_id": "forest10-all-random-01",
            "dataset": "forest10",
            "status": "VALID",
            "query_id": "arecel:forest10:test:000000",
            "source_index": 0,
            "true_cardinality": 1,
            "estimate_plan_rows": 1,
            "estimate_rounded_r1": 1,
            "qerror": 1.0,
        }
        with self.assertRaisesRegex(ValueError, "incomplete row count"):
            audit.validate_records(
                [row], "forest10-all-random-01", expected_count=2
            )


if __name__ == "__main__":
    unittest.main()
