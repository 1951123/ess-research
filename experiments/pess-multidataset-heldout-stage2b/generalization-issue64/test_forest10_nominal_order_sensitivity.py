import unittest
from fractions import Fraction

from forest10_exact_selection import TaskModel, exact_select_many, model_loss
from forest10_nominal_order_sensitivity import seeded_orders


class OrderSensitivityTests(unittest.TestCase):
    def test_fixed_orders_are_reproducible_and_not_rerolled(self):
        candidates = ("e00_01", "e00_02", "e01_02", "e01_03")
        first = seeded_orders(candidates)
        second = seeded_orders(candidates)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        self.assertEqual([item["seed"] for item in first[2:]], list(range(8)))
        # No uniqueness constraint is imposed by resampling; analysis reports any collision.

    def test_reordered_nominal_exact_optimum_and_pess_loss_are_fraction_exact(self):
        edges = (("ab", ("a", "b")), ("ac", ("a", "c")), ("bd", ("b", "d")))
        task = TaskModel(Fraction(-3), {"ab": Fraction(2), "ac": Fraction(1), "bd": Fraction(4)}, ("ab", "ac", "bd"))
        original = exact_select_many((task,), edges, (0, 2, 3))["Nominal"]
        reverse = exact_select_many((task,), tuple(reversed(edges)), (0, 2, 3))["Nominal"]
        self.assertEqual(original["2"]["objective_fraction"], reverse["2"]["objective_fraction"])
        self.assertNotEqual(original["2"]["selected"], reverse["2"]["selected"])
        self.assertNotEqual(original["2"]["tie_count"], reverse["2"]["tie_count"])
        self.assertEqual(model_loss(task, ("ab", "ac"), "PESS", dict(edges), tuple(edge for edge, _ in edges)), 2)


if __name__ == "__main__":
    unittest.main()

