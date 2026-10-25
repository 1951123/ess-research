from __future__ import annotations

import unittest
from fractions import Fraction

from run_issue103 import (
    SCALE,
    maximal_matching_masks,
    priority_matching_masks,
    summarize_totals,
    task_loss_units,
)


class MatchingAndDistributionTests(unittest.TestCase):
    def test_path_priority_matchings_are_inclusion_maximal(self) -> None:
        # e0--e1--e2 is a path; the outer edges can be selected together.
        endpoints = [("a", "b"), ("b", "c"), ("c", "d")]
        orders = ((0, 1, 2), (1, 0, 2), (2, 1, 0))
        outcomes = priority_matching_masks(0b111, orders, endpoints)
        maximal = set(maximal_matching_masks(0b111, endpoints))
        self.assertEqual(outcomes, (0b101, 0b010, 0b101))
        self.assertTrue(set(outcomes) <= maximal)
        self.assertEqual(maximal, {0b101, 0b010})

    def test_permutation_multiplicity_is_retained(self) -> None:
        endpoints = [("a", "b"), ("b", "c"), ("c", "d")]
        from itertools import permutations

        orders = tuple(permutations(range(3)))
        outcomes = priority_matching_masks(0b111, orders, endpoints)
        counts = {matching: outcomes.count(matching) for matching in set(outcomes)}
        self.assertEqual(counts, {0b010: 2, 0b101: 4})
        self.assertNotEqual(len(counts), len(orders))

    def test_policy_order_is_deterministic_when_priorities_are_tied_in_loss(self) -> None:
        endpoints = [("a", "b"), ("b", "c")]
        # Equal losses do not randomize the matching: the supplied order decides.
        low_id_first = priority_matching_masks(0b11, ((0, 1),), endpoints)
        high_id_first = priority_matching_masks(0b11, ((1, 0),), endpoints)
        self.assertEqual(low_id_first, priority_matching_masks(0b11, ((0, 1),), endpoints))
        self.assertEqual(low_id_first, (0b01,))
        self.assertEqual(high_id_first, (0b10,))

    def test_shared_global_maximum_can_be_below_taskwise_pess(self) -> None:
        endpoints = [("a", "b"), ("b", "c")]
        orders = ((0, 1), (1, 0))
        outcomes = priority_matching_masks(0b11, orders, endpoints)
        # Two tasks prefer opposite matchings. Each task's maximum loss is 5,
        # while one common global order incurs total loss 5 in either case.
        task_a = [task_loss_units(0, (5, 0), mask) for mask in outcomes]
        task_b = [task_loss_units(0, (0, 5), mask) for mask in outcomes]
        shared = [left + right for left, right in zip(task_a, task_b)]
        taskwise = max(task_a) + max(task_b)
        self.assertEqual(shared, [5, 5])
        self.assertEqual(max(shared), 5)
        self.assertEqual(taskwise, 10)

    def test_empty_set_has_one_zero_correction_matching(self) -> None:
        outcomes = priority_matching_masks(0, ((),), [])
        maximal = maximal_matching_masks(0, [])
        self.assertEqual(outcomes, (0,))
        self.assertEqual(maximal, (0,))
        self.assertEqual(task_loss_units(-7, (), outcomes[0]), 7)

    def test_exact_mean_variance_and_extrema(self) -> None:
        result = summarize_totals([SCALE, 3 * SCALE])
        self.assertEqual(result["mean_fraction"], "2")
        self.assertEqual(result["variance_fraction"], "1")
        self.assertEqual(result["standard_deviation_decimal"], "1.00000000")
        self.assertEqual(result["minimum_fraction"], "1")
        self.assertEqual(result["maximum_fraction"], "3")
        self.assertEqual(result["range_fraction"], "2")
        self.assertEqual(Fraction(result["mean_fraction"]), Fraction(2))


if __name__ == "__main__":
    unittest.main()
