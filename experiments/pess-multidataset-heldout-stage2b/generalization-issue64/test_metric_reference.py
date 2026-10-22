"""Formula-level tests; synthetic integers only, no data or outcomes loaded."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
import unittest

from metric_reference import (
    natural_qerror,
    paired_classification,
    paired_log_q1_delta,
    per_query_log_q1,
    q1,
)


class MetricReferenceTests(unittest.TestCase):
    def test_q1_floor_and_natural_positive_domain(self) -> None:
        self.assertEqual(q1(0, 0), Fraction(1))
        self.assertEqual(q1(9, 0), Fraction(9))
        self.assertEqual(q1(0, 9), Fraction(9))
        self.assertEqual(q1(20, 4), Fraction(5))
        self.assertEqual(natural_qerror(0, 9), None)
        self.assertEqual(natural_qerror(0, 0), None)
        self.assertEqual(natural_qerror(20, 4), Fraction(5))

    def test_invalid_and_missing_counts_fail_closed(self) -> None:
        for bad in (-1, 1.0, True):
            with self.assertRaises(ValueError):
                q1(bad, 10)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            natural_qerror(10, -1)

    def test_two_replicate_log_aggregation_is_paired_and_quantized(self) -> None:
        q_pess = [Fraction(2), Fraction(2)]
        q_nominal = [Fraction(4), Fraction(4)]
        delta = paired_log_q1_delta(q_pess, q_nominal)
        self.assertEqual(delta, Decimal("-0.69314718055994530941723212145817656807550013436026"))
        self.assertEqual(paired_classification(delta), "benefit")
        self.assertEqual(
            paired_log_q1_delta(q_nominal, q_pess),
            Decimal("0.69314718055994530941723212145817656807550013436026"),
        )
        self.assertEqual(paired_classification(paired_log_q1_delta(q_pess, q_pess)), "tie")
        self.assertEqual(per_query_log_q1(q_pess), Decimal("0.69314718055994530941723212145817656807550013436026"))

    def test_missing_replicates_cannot_be_silently_averaged(self) -> None:
        with self.assertRaises(ValueError):
            per_query_log_q1([Fraction(2)])
        with self.assertRaises(ValueError):
            paired_log_q1_delta([Fraction(2)], [Fraction(4), Fraction(4)])


if __name__ == "__main__":
    unittest.main()
