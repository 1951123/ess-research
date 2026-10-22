"""Outcome-free checks of the frozen Forest10 test execution schedule."""
from __future__ import annotations

import unittest

import run_forest10_frozen_test_evaluation as evaluation


class FrozenTestEvaluationPlanTests(unittest.TestCase):
    def test_plan_and_selection_pins_load_and_deduplicate_to_three_sets(self) -> None:
        _plan, frozen = evaluation._frozen_inputs()
        selected = evaluation._selected_sets(frozen)
        self.assertEqual(len(selected), 6)
        self.assertEqual(len(set(selected.values())), 3)
        self.assertEqual(selected["Nominal_B2"], ("e01_06", "e02_07"))
        self.assertEqual(selected["PESS_B3"], ("e01_06", "e02_07", "e03_04"))

    def test_candidate_map_is_full_frozen_forest10_universe(self) -> None:
        import json
        from pathlib import Path

        frozen = json.loads(evaluation.SELECTION_PATH.read_text(encoding="utf-8"))
        edges = evaluation._candidate_edges(frozen["inputs"]["candidate_order"])
        self.assertEqual(len(edges), 45)
        self.assertEqual(edges[0], ("e00_01", ("Elevation", "Aspect")))
        self.assertEqual(edges[-1][0], "e08_09")


if __name__ == "__main__":
    unittest.main()
