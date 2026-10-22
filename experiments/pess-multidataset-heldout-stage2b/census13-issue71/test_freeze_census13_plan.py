import unittest
from itertools import combinations

from freeze_census13_plan import BUDGETS, SEEDS, _orders


class CensusPlanTests(unittest.TestCase):
    def test_seeded_orders_are_ten_distinct_full_permutations(self):
        candidates = [f"e{i:02}_{j:02}" for i in range(13) for j in range(i + 1, 13)]
        rows = _orders(candidates)
        actual = [row for row in rows if "candidate_ids" in row]
        self.assertEqual(len(actual), 10)
        self.assertEqual(len({tuple(row["candidate_ids"]) for row in actual}), 10)
        self.assertEqual([row["seed"] for row in actual[2:]], list(SEEDS))
        self.assertTrue(all(len(row["candidate_ids"]) == 78 for row in actual))
        self.assertTrue(all(set(row["candidate_ids"]) == set(candidates) for row in actual))

    def test_exact_census_budget_counts(self):
        self.assertEqual(BUDGETS, (0, 2, 3))
        self.assertEqual(1 + 78, 79)
        self.assertEqual(1 + 78 + len(list(combinations(range(78), 2))), 3_082)
        self.assertEqual(1 + 78 + len(list(combinations(range(78), 2))) + len(list(combinations(range(78), 3))), 79_158)


if __name__ == "__main__":
    unittest.main()
