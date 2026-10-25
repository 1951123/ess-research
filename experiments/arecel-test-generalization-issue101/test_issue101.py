"""Small synthetic checks for Issue #101 parsing, metrics and frozen schedule."""
from __future__ import annotations

import unittest
import math

import run_issue101 as runner


class Issue101ProtocolTests(unittest.TestCase):
    def test_frozen_case_map_deduplicates_to_25_sets_and_250000_calls(self) -> None:
        protocol = runner.read_protocol()
        self.assertEqual(protocol["execution"]["configuration_count"], 25)
        self.assertEqual(protocol["execution"]["planned_explain_calls"], 250_000)
        self.assertEqual(protocol["execution"]["parallel_clients_per_configuration"], 6)

    def test_top_level_plan_rows_are_read_without_searching_child_plans(self) -> None:
        self.assertEqual(
            runner.parse_top_level_plan_rows('[{"Plan":{"Node Type":"Seq Scan","Plan Rows":17}}]'),
            17,
        )
        with self.assertRaisesRegex(ValueError, "MISSING_TOP_LEVEL_PLAN_ROWS"):
            runner.parse_top_level_plan_rows(
                '[{"Plan":{"Plans":[{"Plan Rows":99}]}}]'
            )
        for output in ('{}', '[]', '[{"Plan":{"Plan Rows":true}}]', 'not-json'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                runner.parse_top_level_plan_rows(output)

    def test_arecel_zero_aware_qerror_and_r_equals_one_rounding(self) -> None:
        self.assertEqual(runner.qerror(0, 0), 1.0)
        self.assertEqual(runner.qerror(0, 7), 7.0)
        self.assertEqual(runner.qerror(9, 0), 9.0)
        self.assertEqual(runner.qerror(12, 3), 4.0)
        self.assertEqual(runner.qerror_for_plan_rows(4, 3), (4.0 / 3.0, 4))
        with self.assertRaises(ValueError):
            runner.qerror_for_plan_rows(-1, 0)

    def test_batch_parser_maps_one_plan_and_keeps_missing_plan_status(self) -> None:
        output = (
            "__ISSUE101_BEGIN_00000__\n"
            '[{"Plan":{"Plan Rows":23}}]\n'
            "__ISSUE101_END_00000__\n"
            "__ISSUE101_BEGIN_00001__\n"
            "__ISSUE101_END_00001__\n"
        )
        rows = runner.parse_batch_output(output, 2)
        self.assertEqual(rows[0], {"status": "VALID", "plan_rows": 23})
        self.assertEqual(rows[1], {"status": "MISSING_EXPLAIN_OUTPUT", "plan_rows": None})

    def test_arecel_numpy_summary_uses_default_percentile_semantics(self) -> None:
        summary = runner.summarize_errors([1.0, 2.0, 3.0, 4.0])
        for key, expected in {"p50": 2.5, "p95": 3.85, "p99": 3.97, "max": 4.0}.items():
            self.assertTrue(math.isclose(summary[key], expected, rel_tol=1e-14))


if __name__ == "__main__":
    unittest.main()
