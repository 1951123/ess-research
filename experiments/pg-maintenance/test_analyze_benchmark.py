#!/usr/bin/env python3
"""Negative regression checks for the Issue #7 raw-evidence validator."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import analyze_benchmark
import fixture_metrics


RAW = Path(__file__).parent / "runs/20261017-issue7-v5-target300-20rep/measurement/raw-observations.json"


class RawEvidenceValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(RAW.read_text(encoding="utf-8"))
        cls.conditions = {row["condition_id"]: row for row in cls.payload["conditions"]}

    def assert_rejected(self, payload: dict) -> None:
        with self.assertRaises(SystemExit):
            analyze_benchmark.validate_payload(payload, self.conditions)

    def test_duplicate_timed_cell_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["observations"].append(copy.deepcopy(payload["observations"][0]))
        self.assert_rejected(payload)

    def test_wrong_statistics_target_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        for row in payload["metadata_observations"]:
            if row["name"] is not None:
                row["statistics_target"] += 1
                break
        self.assert_rejected(payload)

    def test_duplicate_oid_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        nonempty = [
            row for row in payload["metadata_observations"] if row["name"] is not None
        ]
        nonempty[1]["oid"] = nonempty[0]["oid"]
        self.assert_rejected(payload)

    def test_cramers_v_includes_zero_frequency_cells(self) -> None:
        # Two diagonal cells are observed and the two off-diagonal cells are
        # absent.  Perfect dependence must still yield V=1.
        rows = [(0, 0, 50), (1, 1, 50)]
        value = fixture_metrics.cramers_v(rows, 100)
        self.assertAlmostEqual(value, 1.0, places=12)

    def test_four_value_median_averages_the_middle_pair(self) -> None:
        self.assertEqual(analyze_benchmark.median([1.0, 2.0, 3.0, 4.0]), 2.5)

    def test_aggregate_summary_uses_four_value_median(self) -> None:
        rows = [
            {
                "regime": "r",
                "target_mode": "t",
                "absolute_additivity_error_ms": value,
                "error_bootstrap": {
                    "error_to_uncertainty_ratio": value,
                    "includes_zero": False,
                },
            }
            for value in [1.0, 2.0, 3.0, 4.0]
        ]
        aggregate = analyze_benchmark.aggregate_summaries(rows)
        self.assertEqual(len(aggregate), 1)
        self.assertEqual(aggregate[0]["median_absolute_additivity_error_ms"], 2.5)
        self.assertEqual(aggregate[0]["median_error_to_uncertainty_ratio"], 2.5)


if __name__ == "__main__":
    unittest.main()
