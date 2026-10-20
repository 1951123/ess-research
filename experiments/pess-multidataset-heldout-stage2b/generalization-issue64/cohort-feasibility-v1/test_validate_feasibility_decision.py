from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_feasibility_decision import validate


HERE = Path(__file__).parent
ROOT = HERE.parent
PROTOCOL = json.loads((ROOT / "protocol-v1.json").read_text(encoding="utf-8"))
DECISION = json.loads((HERE / "cohort-feasibility-decision-v1.json").read_text(encoding="utf-8"))


class FeasibilityDecisionTests(unittest.TestCase):
    def test_frozen_decision_is_consistent(self) -> None:
        self.assertEqual(validate(PROTOCOL, DECISION), [])

    def test_changed_quota_or_candidate_count_fails(self) -> None:
        changed = copy.deepcopy(DECISION)
        changed["datasets"]["forest10"]["calibration"]["predicate_bin_targets"]["2"] += 1
        self.assertTrue(validate(PROTOCOL, changed))
        changed = copy.deepcopy(DECISION)
        changed["datasets"]["forest10"]["heldout"]["actual_groups"] = 1
        self.assertTrue(validate(PROTOCOL, changed))


if __name__ == "__main__":
    unittest.main()
