import unittest

from matching_verifier import MatchingVerificationError, verify_maximal_matching
from source_ledger import (
    LedgerError,
    build_source_ledger,
    parse_equality_clauses,
    verify_trace_against_ledger,
)


EDGES = [
    {"id": "e01", "columns": ["a", "b"]},
    {"id": "p01", "columns": ["a", "b"]},
    {"id": "e12", "columns": ["b", "c"]},
    {"id": "e23", "columns": ["c", "d"]},
]


class Stage2ATests(unittest.TestCase):
    def test_maximal_is_not_maximum_cardinality(self):
        result = verify_maximal_matching(EDGES, ["e12", "e23"], ["e12"])
        self.assertTrue(result["is_inclusion_wise_maximal"])

    def test_nonmaximal_set_is_rejected(self):
        with self.assertRaisesRegex(MatchingVerificationError, "not inclusion-wise maximal"):
            verify_maximal_matching(EDGES, ["e01", "e12", "e23"], ["e01"])

    def test_parallel_labels_remain_distinct(self):
        result = verify_maximal_matching(EDGES, ["e01", "p01"], ["p01"])
        self.assertEqual(result["selected_ids"], ["p01"])

    def test_equality_parser_rejects_range(self):
        with self.assertRaisesRegex(LedgerError, "equality-only"):
            parse_equality_clauses(
                "SELECT count(*) FROM t WHERE a = 1 AND b BETWEEN 2 AND 3;",
                ["a", "b"],
            )

    def test_source_ledger_reconstructs_oid_tie_order(self):
        clauses = parse_equality_clauses(
            "SELECT count(*) FROM t WHERE a = 1 AND b = 1 AND c = 1 AND d = 1;",
            ["a", "b", "c", "d"],
        )
        rows = [
            {"id": "e01", "oid": 10, "keys": [1, 2], "columns": ["a", "b"], "kind": "{m}", "inherit": False, "mcv_item_count": 4},
            {"id": "e12", "oid": 11, "keys": [2, 3], "columns": ["b", "c"], "kind": "{m}", "inherit": False, "mcv_item_count": 4},
            {"id": "e23", "oid": 12, "keys": [3, 4], "columns": ["c", "d"], "kind": "{m}", "inherit": False, "mcv_item_count": 4},
        ]
        ledger = build_source_ledger(rows, clauses)
        self.assertEqual(ledger["expected_selected_ids"], ["e01", "e23"])
        self.assertEqual(ledger["expected_claimed_clause_indices"], [0, 1, 2, 3])

    def test_trace_omission_fails_closed(self):
        clauses = parse_equality_clauses("SELECT count(*) FROM t WHERE a = 1 AND b = 1;", ["a", "b"])
        rows = [{"id": "e01", "oid": 10, "keys": [1, 2], "columns": ["a", "b"], "kind": "{m}", "inherit": False, "mcv_item_count": 4}]
        ledger = build_source_ledger(rows, clauses)
        result = verify_trace_against_ledger(ledger, rows, {"selected_stat_oids": [10], "claimed_clause_indices": [0, 1], "candidate_none": False})
        self.assertEqual(result["status"], "INCONCLUSIVE")

    def test_no_mcv_selected_control_is_outside_gate(self):
        clauses = parse_equality_clauses("SELECT count(*) FROM t WHERE e = 1 AND f = 1;", ["e", "f"])
        rows = [{"id": "e45", "oid": 10, "keys": [5, 6], "columns": ["e", "f"], "kind": "{m}", "inherit": False, "mcv_item_count": 0}]
        ledger = build_source_ledger(rows, clauses)
        result = verify_trace_against_ledger(ledger, rows, {"selected_stat_oids": [10], "claimed_clause_indices": [0, 1], "candidate_none": False, "query_error": "not yet built"})
        self.assertEqual(result["status"], "OUTSIDE_GATE")


if __name__ == "__main__":
    unittest.main()
