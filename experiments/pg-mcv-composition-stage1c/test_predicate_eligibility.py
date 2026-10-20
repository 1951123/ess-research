import unittest

from predicate_eligibility import eligible_candidate_edges, extract_supported_clauses


class PredicateEligibilityTests(unittest.TestCase):
    def test_between_expands_in_planner_clause_order(self):
        sql = (
            'SELECT COUNT(*) FROM t WHERE "Aspect" BETWEEN -1 AND 2 '
            'AND "Slope" >= 3'
        )
        clauses = extract_supported_clauses(sql)
        self.assertEqual([(item.column, item.operator, item.clause_index) for item in clauses], [
            ("Aspect", ">=", 0),
            ("Aspect", "<=", 1),
            ("Slope", ">=", 2),
        ])

    def test_built_mcv_does_not_make_missing_endpoint_eligible(self):
        sql = 'SELECT COUNT(*) FROM t WHERE "Slope" BETWEEN 3 AND 4'
        clauses, ledger = eligible_candidate_edges(sql, [{
            "id": "e12",
            "columns": ["Aspect", "Slope"],
            "built_mcv": True,
        }])
        self.assertEqual([item.column for item in clauses], ["Slope", "Slope"])
        self.assertFalse(ledger["e12"]["eligible"])
        self.assertEqual(ledger["e12"]["reason"], "missing_supported_predicate")
        self.assertEqual(ledger["e12"]["missing_columns"], ["Aspect"])
        self.assertEqual(ledger["e12"]["endpoint_clause_indices"], {"Aspect": [], "Slope": [0, 1]})

    def test_unsupported_quoted_predicate_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported or unparsed"):
            extract_supported_clauses('SELECT COUNT(*) FROM t WHERE "Aspect" LIKE \'x%\'')


if __name__ == "__main__":
    unittest.main()
