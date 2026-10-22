"""Outcome-free checks of the frozen Forest10 test execution schedule."""
from __future__ import annotations

import unittest
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import run_forest10_frozen_test_evaluation as evaluation
from forest10_runner import PR58Forest10Backend


class FrozenTestEvaluationPlanTests(unittest.TestCase):
    def test_plan_and_selection_pins_load_and_deduplicate_to_three_sets(self) -> None:
        _plan, frozen = evaluation._frozen_inputs()
        selected = evaluation._selected_sets(frozen)
        self.assertEqual(len(selected), 6)
        self.assertEqual(len(set(selected.values())), 3)
        self.assertEqual(selected["Nominal_B2"], ("e01_06", "e02_07"))
        self.assertEqual(selected["PESS_B3"], ("e01_06", "e02_07", "e03_04"))

    def test_candidate_map_is_full_frozen_forest10_universe(self) -> None:
        frozen = json.loads(evaluation.SELECTION_PATH.read_text(encoding="utf-8"))
        edges = evaluation._candidate_edges(frozen["inputs"]["candidate_order"])
        self.assertEqual(len(edges), 45)
        self.assertEqual(edges[0], ("e00_01", ("Elevation", "Aspect")))
        self.assertEqual(edges[-1][0], "e08_09")

    def test_plan_rows_uses_one_tuples_only_json_explain_with_startup_gucs(self) -> None:
        response = '[{"Plan":{"Node Type":"Seq Scan","Plan Rows":17}}]\n'
        psql = Mock(return_value=response)
        backend = object.__new__(PR58Forest10Backend)
        backend.helpers = SimpleNamespace(os=SimpleNamespace(environ={"PGOPTIONS": "-c jit=off"}), psql=psql)
        backend.prefix = Path("/private/pg")
        backend.cluster = {"socket_dir": Path("/private/socket"), "port": 5432}
        query = {"sql": "SELECT * FROM public.forest10 WHERE elevation = 1"}

        self.assertEqual(backend.plan_rows(query), 17)
        args, kwargs = psql.call_args
        self.assertEqual(args[3], "EXPLAIN (FORMAT JSON, SUMMARY OFF) " + query["sql"])
        self.assertTrue(kwargs["tuples"])
        self.assertIn("-c jit=off", args[4]["PGOPTIONS"])
        self.assertIn("-c plan_cache_mode=force_custom_plan", args[4]["PGOPTIONS"])
        self.assertIn("-c max_parallel_workers_per_gather=0", args[4]["PGOPTIONS"])
        self.assertNotIn("SET ", args[3])


if __name__ == "__main__":
    unittest.main()
