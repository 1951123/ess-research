import unittest
from fractions import Fraction

from exact_nominal_selection import exact_select_nominal_many
from forest10_exact_selection import TaskModel, exact_select_many


class ExactNominalSpecializationTests(unittest.TestCase):
    def setUp(self):
        self.candidates = (
            ("ab", ("a", "b")),
            ("bc", ("b", "c")),
            ("cd", ("c", "d")),
            ("ad", ("a", "d")),
        )
        self.models = (
            TaskModel(Fraction(3, 7), {"ab": Fraction(-2, 7), "bc": Fraction(1, 3),
                                      "cd": Fraction(-1, 5)}, ("ab", "bc", "cd")),
            TaskModel(Fraction(-4, 9), {"bc": Fraction(2, 9), "cd": Fraction(1, 6),
                                       "ad": Fraction(5, 8)}, ("bc", "cd", "ad")),
        )

    def test_nominal_specialization_matches_pinned_exact_selector(self):
        orders = (
            self.candidates,
            tuple(reversed(self.candidates)),
            (self.candidates[1], self.candidates[3], self.candidates[0], self.candidates[2]),
        )
        for candidates in orders:
            with self.subTest(order=[edge for edge, _ in candidates]):
                expected = exact_select_many(self.models, candidates, (0, 2, 3))["Nominal"]
                actual = exact_select_nominal_many(self.models, candidates, (0, 2, 3))
                self.assertEqual(actual, expected)

    def test_exact_ties_follow_candidate_enumeration_order(self):
        zero_models = (TaskModel(Fraction(0), {}, ()),)
        forward = exact_select_nominal_many(zero_models, self.candidates, (2,))
        reverse = exact_select_nominal_many(zero_models, tuple(reversed(self.candidates)), (2,))
        self.assertEqual(forward["2"]["tie_count"], 11)
        self.assertEqual(reverse["2"]["tie_count"], 11)
        self.assertEqual(forward["2"]["selected"], [])
        self.assertEqual(reverse["2"]["selected"], [])


if __name__ == "__main__":
    unittest.main()
