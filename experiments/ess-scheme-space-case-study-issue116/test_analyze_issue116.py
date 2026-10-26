from __future__ import annotations

import unittest
from fractions import Fraction

from analyze_issue116 import (
    MAX_COMPACT_GAMMA,
    exact_units,
    mask_ids,
    primary_eligible,
    scheme_changed,
)


class CaseStudyHelpersTests(unittest.TestCase):
    def test_exact_units_requires_frozen_quantization(self) -> None:
        self.assertEqual(exact_units(Fraction(3, 10**18)), 3)
        with self.assertRaises(ValueError):
            exact_units(Fraction(1, 3))

    def test_matching_mask_keeps_stable_resource_labels(self) -> None:
        self.assertEqual(mask_ids(0b101, ("ab", "bc", "cd")), ("ab", "cd"))
        self.assertEqual(mask_ids(0, ("ab",)), ())

    def test_scheme_change_detects_family_or_loss_change(self) -> None:
        gamma = {("ab",): 4, ("bc",): 7}
        self.assertFalse(scheme_changed(gamma, dict(gamma)))
        self.assertTrue(scheme_changed(gamma, {("ab",): 4}))
        self.assertTrue(scheme_changed(gamma, {("ab",): 5, ("bc",): 7}))

    def test_primary_rule_requires_every_condition_and_compact_gamma(self) -> None:
        self.assertTrue(primary_eligible(True, True, True, MAX_COMPACT_GAMMA))
        self.assertFalse(primary_eligible(False, True, True, 2))
        self.assertFalse(primary_eligible(True, False, True, 2))
        self.assertFalse(primary_eligible(True, True, False, 2))
        self.assertFalse(primary_eligible(True, True, True, MAX_COMPACT_GAMMA + 1))


if __name__ == "__main__":
    unittest.main()
