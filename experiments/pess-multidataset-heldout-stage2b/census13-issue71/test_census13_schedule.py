import unittest

from census13_schedule import assign_configurations, calls_for_worker, compare_smoke_observations


class CensusScheduleTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [{"id": f"e{i}", "eligible_valid_query_count": 1} for i in range(4)]
        self.queries = [f"q{i}" for i in range(4)]
        self.eligible = {query: [f"e{i}" for i in range(4) if (i + int(query[1:])) % 2 == 0]
                         for query in self.queries}

    def test_empty_once_and_single_owner_per_candidate(self):
        workers = assign_configurations(self.candidates, 2)
        self.assertEqual([config for worker in workers for config, _ in worker].count("Empty"), 1)
        self.assertEqual(sorted(config for worker in workers for config, _ in worker),
                         ["Empty", "e0", "e1", "e2", "e3"])
        self.assertEqual(sum(len(calls_for_worker(worker, self.queries, self.eligible))
                             for worker in workers), 4 + sum(map(len, self.eligible.values())))

    def test_smoke_pair_comparison_is_exact_and_ignores_oid_equality(self):
        expected = [(q, "Empty") for q in self.queries]
        def rows(oid):
            return [dict(query_id=q, config_id="Empty", status="SUCCESS",
                         diagnostics_status="complete", mcv_diagnostics_status="NO_MCV_EVENTS",
                         mcv_candidate_ids=[], clause_indexes=[], nrows_preclamp="0.25",
                         relation_oid=oid, mcv_events=[]) for q in self.queries]
        report = compare_smoke_observations(rows(101), rows(207), expected)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["compared_pairs"], 4)

    def test_normalized_mcv_values_compare_but_oids_do_not(self):
        key = [("q", "e0")]
        numeric = dict(simple_sel="0.1", mcv_sel="0.2", mcv_basesel="0.3",
                       mcv_totalsel="0.4", stat_sel="0.5")
        def row(relid, statid, stat_sel="0.5"):
            event = dict(relation_oid=relid, stat_oid=statid, statistic_id="e0",
                         clause_indexes=[0, 1], clause_count=2, **{**numeric, "stat_sel": stat_sel})
            return dict(query_id="q", config_id="e0", status="SUCCESS",
                        diagnostics_status="complete", mcv_diagnostics_status="VERIFIED",
                        nrows_preclamp="2.5", relation_oid=relid, mcv_candidate_ids=["e0"],
                        clause_indexes=[0, 1], mcv_events=[event])
        result = compare_smoke_observations([row(10, 20)], [row(11, 21)], key)
        self.assertTrue(result["normalized_mcv_values_equal"])
        with self.assertRaisesRegex(ValueError, "normalized MCV values differ"):
            compare_smoke_observations([row(10, 20)], [row(11, 21, "0.6")], key)


if __name__ == "__main__":
    unittest.main()
