import unittest

from predicate_eligibility import eligible_candidate_edges, extract_supported_clauses
from run_stage1c import Runner


class PredicateEligibilityTests(unittest.TestCase):
    @staticmethod
    def _runner_for_single_predicate():
        runner = Runner.__new__(Runner)
        runner.candidates = {
            "e12": {"id": "e12", "columns": ["Aspect", "Slope"]},
        }
        runner.tasks = {
            "task": {"record": {"sql": 'SELECT COUNT(*) FROM t WHERE "Slope" BETWEEN 3 AND 4'}}
        }
        return runner

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

    def test_live_graph_check_fails_closed_on_selected_outside_eligibility(self):
        runner = self._runner_for_single_predicate()
        observation = {
            "task_id": "task",
            "selected_candidate_ids": ["e12"],
            "unmapped_selected_stat_oids": [],
            "ledger": [{"candidate_id": "e12", "built_mcv": True}],
        }
        result = runner.graph_checks(observation, ["e12"])[0]
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["eligibility_status"], "INCONCLUSIVE_SELECTED_OUTSIDE_ELIGIBILITY")
        self.assertEqual(result["selected_candidate_ids"], ["e12"])
        self.assertEqual(result["selected_outside_restricted_gate_candidate_ids"], ["e12"])

    def test_live_graph_check_fails_closed_on_unmapped_oid(self):
        runner = self._runner_for_single_predicate()
        observation = {
            "task_id": "task",
            "selected_candidate_ids": [],
            "unmapped_selected_stat_oids": [99999],
            "ledger": [{"candidate_id": "e12", "built_mcv": True}],
        }
        result = runner.graph_checks(observation, ["e12"])[0]
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["eligibility_status"], "INCONCLUSIVE_UNMAPPED_SELECTED_OID")
        self.assertEqual(result["unmapped_selected_stat_oids"], [99999])


if __name__ == "__main__":
    unittest.main()
