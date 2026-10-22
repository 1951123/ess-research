import unittest
from decimal import Decimal

from run_census13_smoke import census13_adapter_overlay
from verify_census13_full_valid import raw_preclamp
from fit_census13_valid_and_freeze import clamp_fit_estimate, clamp_fit_truth


class Census13ZeroPolicyTests(unittest.TestCase):
    def test_adapter_overlay_changes_only_positive_guard(self):
        source = b"if not preclamp.is_finite() or preclamp <= 0:\n    raise ValueError('positive')\n"
        patched = census13_adapter_overlay(source)
        self.assertIn(b"or preclamp < 0:", patched)
        self.assertNotIn(b"<= 0", patched)
        compile(patched.decode(), "pinned-forest10-runner.py", "exec")

    def test_adapter_overlay_fails_closed_on_unexpected_source(self):
        with self.assertRaisesRegex(RuntimeError, "guard differs"):
            census13_adapter_overlay(b"if preclamp <= 0: pass\n")

    def test_raw_zero_and_positive_subunit_are_preserved(self):
        self.assertEqual(raw_preclamp("0", query_id="q", config_id="Empty"), Decimal("0"))
        self.assertEqual(raw_preclamp("0.25", query_id="q", config_id="e00_01"), Decimal("0.25"))

    def test_clamped_log_transform_is_applied_at_fit_only(self):
        self.assertEqual(clamp_fit_estimate("0"), Decimal(1))
        self.assertEqual(clamp_fit_estimate("0.25"), Decimal(1))
        self.assertEqual(clamp_fit_estimate("1"), Decimal(1))
        self.assertEqual(clamp_fit_estimate("1.25"), Decimal("1.25"))
        self.assertEqual(clamp_fit_truth(0), 1)
        self.assertEqual(clamp_fit_truth(1), 1)
        self.assertEqual(clamp_fit_truth(7), 7)
        with self.assertRaises(ValueError):
            clamp_fit_truth(-1)

    def test_negative_nonfinite_missing_and_malformed_are_rejected(self):
        for value in ("-0.1", "NaN", "Infinity", None, "not-a-number", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                raw_preclamp(value, query_id="q", config_id="Empty")


if __name__ == "__main__":
    unittest.main()
