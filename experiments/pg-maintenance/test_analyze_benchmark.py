#!/usr/bin/env python3
"""Negative regression checks for the Issue #7 raw-evidence validator."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import analyze_benchmark


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


if __name__ == "__main__":
    unittest.main()
