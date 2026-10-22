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
                         relation_oid=oid) for q in self.queries]
        report = compare_smoke_observations(rows(101), rows(207), expected)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["compared_pairs"], 4)


if __name__ == "__main__":
    unittest.main()
