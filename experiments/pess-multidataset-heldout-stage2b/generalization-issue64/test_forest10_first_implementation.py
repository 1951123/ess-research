from __future__ import annotations

import itertools
import json
import unittest
from fractions import Fraction
from pathlib import Path

from forest10_exact_selection import (
    TaskModel,
    exact_select,
    exact_select_many,
    feasible_subsets,
    maximal_matchings,
    model_loss,
    ordered_candidates,
)
from forest10_q1 import parse_top_level_plan_rows, q1
from forest10_runner import (
    build_task_models,
    calibrate_and_select,
    evaluate_frozen_selections,
    rational_log_ratio,
)


class ExactSelectionTests(unittest.TestCase):
    def test_candidate_ids_follow_frozen_schema_pair_order(self) -> None:
        columns = tuple(f"c{i}" for i in range(10))
        supports = {(left, right): 1 for left, right in itertools.combinations(columns, 2)}
        candidates = ordered_candidates(columns, supports)
        self.assertEqual(len(candidates), 45)
        self.assertEqual(candidates[0], ("e00_01", ("c0", "c1")))
        self.assertEqual(candidates[-1], ("e08_09", ("c8", "c9")))
        self.assertEqual(len({candidate_id for candidate_id, _ in candidates}), 45)

    def test_bounded_subset_counts_and_order(self) -> None:
        ids = [f"e{i:02}" for i in range(45)]
        self.assertEqual(len(feasible_subsets(ids, 0)), 1)
        self.assertEqual(len(feasible_subsets(ids, 2)), 1036)
        self.assertEqual(len(feasible_subsets(ids, 3)), 15226)
        self.assertEqual(feasible_subsets(["a", "b", "c"], 2)[:4], ((), ("a",), ("b",), ("c",)))
        self.assertEqual(feasible_subsets(["a", "b"], 5), ((), ("a",), ("b",), ("a", "b")))

    def test_rejects_duplicate_ids_and_negative_budget(self) -> None:
        with self.assertRaises(ValueError):
            feasible_subsets(["a", "a"], 1)
        with self.assertRaises(ValueError):
            feasible_subsets(["a"], -1)

    def test_maximal_matchings_against_independent_mask_oracle(self) -> None:
        endpoints = {"ab": ("a", "b"), "bc": ("b", "c"), "cd": ("c", "d")}
        actual = maximal_matchings(tuple(endpoints), endpoints)
        independent = []
        edges = tuple(endpoints)
        for mask in range(1 << len(edges)):
            chosen = tuple(edge for i, edge in enumerate(edges) if mask & (1 << i))
            if any(
                not set(endpoints[left]).isdisjoint(endpoints[right])
                for left, right in itertools.combinations(chosen, 2)
            ):
                continue
            if all(
                edge in chosen or any(not set(endpoints[edge]).isdisjoint(endpoints[kept]) for kept in chosen)
                for edge in edges
            ):
                independent.append(chosen)
        self.assertEqual(set(actual), set(independent))
        self.assertEqual(set(actual), {("ab", "cd"), ("bc",)})

    def test_nominal_order_and_pess_worst_case_are_distinct(self) -> None:
        endpoints = {"ab": ("a", "b"), "bc": ("b", "c"), "cd": ("c", "d")}
        task = TaskModel(Fraction(0), {"ab": Fraction(3), "bc": Fraction(-1), "cd": Fraction(-3)}, tuple(endpoints))
        chosen = ("ab", "bc", "cd")
        self.assertEqual(model_loss(task, chosen, "Nominal", endpoints, tuple(endpoints)), Fraction(0))
        self.assertEqual(model_loss(task, chosen, "PESS", endpoints, tuple(endpoints)), Fraction(1))

    def test_exact_global_selection_retains_all_ties(self) -> None:
        candidates = (("ab", ("a", "b")), ("bc", ("b", "c")))
        tasks = (
            TaskModel(Fraction(2), {"ab": Fraction(-2), "bc": Fraction(-2)}, ("ab", "bc")),
        )
        result = exact_select(tasks, candidates, 1, "Nominal")
        self.assertEqual(result["feasible_subset_count"], 3)
        self.assertEqual(result["objective_fraction"], "0")
        self.assertEqual(result["all_optimal_sets"], [["ab"], ["bc"]])
        self.assertEqual(result["selected"], ["ab"])
        self.assertEqual(exact_select(tasks, candidates, 0, "PESS")["selected"], [])

    def test_multi_budget_exact_search_matches_single_budget_api(self) -> None:
        candidates = (("ab", ("a", "b")), ("bc", ("b", "c")), ("de", ("d", "e")))
        tasks = (
            TaskModel(Fraction(3, 7), {"ab": Fraction(-1, 4), "bc": Fraction(2, 5)}, ("ab", "bc")),
            TaskModel(Fraction(-2, 3), {"bc": Fraction(1, 2), "de": Fraction(-1, 7)}, ("bc", "de")),
        )
        all_results = exact_select_many(tasks, candidates, (0, 2, 3))
        for method in ("Nominal", "PESS"):
            for budget in (0, 2, 3):
                self.assertEqual(all_results[method][str(budget)], exact_select(tasks, candidates, budget, method))
        with self.assertRaisesRegex(ValueError, "unique"):
            exact_select_many(
                (TaskModel(Fraction(0), {"ab": Fraction(0)}, ("ab", "ab")),),
                candidates,
                (1,),
            )

    def test_complete_selection_matches_independent_small_oracle(self) -> None:
        candidates = (
            ("ab", ("a", "b")),
            ("bc", ("b", "c")),
            ("cd", ("c", "d")),
            ("de", ("d", "e")),
        )
        endpoints = dict(candidates)
        tasks = (
            TaskModel(
                Fraction(3, 2),
                {"ab": Fraction(-2), "bc": Fraction(-1), "cd": Fraction(1), "de": Fraction(-1, 2)},
                ("ab", "bc", "cd"),
            ),
            TaskModel(
                Fraction(-1),
                {"ab": Fraction(1, 2), "bc": Fraction(2), "cd": Fraction(-1, 2), "de": Fraction(1)},
                ("bc", "cd", "de"),
            ),
        )

        def oracle_loss(task: TaskModel, selected: tuple[str, ...], method: str) -> Fraction:
            available = tuple(edge for edge in selected if edge in task.available_edges)
            if method == "Nominal":
                schemes = []
                chosen: list[str] = []
                for edge, _ in candidates:
                    if edge in available and all(
                        set(endpoints[edge]).isdisjoint(endpoints[kept]) for kept in chosen
                    ):
                        chosen.append(edge)
                schemes = [tuple(chosen)]
            else:
                schemes = []
                for mask in range(1 << len(available)):
                    scheme = tuple(edge for i, edge in enumerate(available) if mask & (1 << i))
                    if any(
                        not set(endpoints[left]).isdisjoint(endpoints[right])
                        for left, right in itertools.combinations(scheme, 2)
                    ):
                        continue
                    if all(
                        edge in scheme or any(
                            not set(endpoints[edge]).isdisjoint(endpoints[kept]) for kept in scheme
                        )
                        for edge in available
                    ):
                        schemes.append(scheme)
            return max(
                abs(task.alpha + sum((task.b[edge] for edge in scheme), Fraction(0)))
                for scheme in schemes
            )

        for budget in (0, 2, 3):
            subsets = feasible_subsets([edge for edge, _ in candidates], budget)
            for method in ("Nominal", "PESS"):
                scored = [
                    (sum((oracle_loss(task, subset, method) for task in tasks), Fraction(0)), subset)
                    for subset in subsets
                ]
                optimum = min(score for score, _ in scored)
                tied = [list(subset) for score, subset in scored if score == optimum]
                result = exact_select(tasks, candidates, budget, method)
                self.assertEqual(result["objective_fraction"], str(optimum))
                self.assertEqual(result["all_optimal_sets"], tied)


class PlanRowsQ1Tests(unittest.TestCase):
    def test_protocol_pins_scope_and_plan_count_arithmetic(self) -> None:
        protocol = json.loads(Path(__file__).with_name("forest10-first-implementation-v1.json").read_text())
        preflight = protocol["preflight"]
        self.assertEqual(protocol["scope"]["dataset"], "Forest10")
        self.assertEqual(protocol["selection"]["budgets"], [0, 2, 3])
        self.assertEqual(
            preflight["calibration_explain_count_exact"],
            protocol["scope"]["valid_queries"] + protocol["candidate_universe"]["support_sum_eligible_query_candidate_pairs"],
        )
        self.assertEqual(
            preflight["total_plan_attempt_upper_bound"],
            preflight["calibration_explain_count_exact"] + preflight["test_explain_count_upper_bound"],
        )
        self.assertFalse(protocol["phase_boundary"]["postgresql_execution_authorized"])

    def test_parses_top_level_plan_rows_only(self) -> None:
        payload = '[{"Plan":{"Node Type":"Seq Scan","Plan Rows":17,"Plans":[{"Plan Rows":99}]}}]'
        self.assertEqual(parse_top_level_plan_rows(payload), 17)

    def test_accepts_zero_plan_rows(self) -> None:
        self.assertEqual(parse_top_level_plan_rows({"Plan": {"Plan Rows": 0}}), 0)

    def test_rejects_malformed_or_noninteger_estimates(self) -> None:
        invalid = (
            "not json",
            "[]",
            '[{"Plan":{"Plans":[{"Plan Rows":3}]}}]',
            '[{"Plan":{"Plan Rows":-1}}]',
            '[{"Plan":{"Plan Rows":1.5}}]',
            '[{"Plan":{"Plan Rows":true}}]',
            '[{"Plan":{"Plan Rows":1}},{"Plan":{"Plan Rows":2}}]',
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_top_level_plan_rows(payload)

    def test_q1_floor_and_positive_domain(self) -> None:
        self.assertEqual(q1(0, 0), Fraction(1))
        self.assertEqual(q1(0, 7), Fraction(7))
        self.assertEqual(q1(9, 0), Fraction(9))
        self.assertEqual(q1(12, 3), Fraction(4))
        with self.assertRaises(ValueError):
            q1(-1, 4)


class SyntheticBackend:
    def __init__(self, failing_query: str | None = None) -> None:
        self.configured: list[tuple[str, ...]] = []
        self.plan_calls = 0
        self.failing_query = failing_query

    def configure(self, selected: tuple[str, ...]) -> tuple[str, ...]:
        self.configured.append(selected)
        return selected

    def preclamp_estimate(self, query, ledger, marker):
        query_index = int(query["query_id"].split("-")[-1])
        if not ledger:
            return (10 + query_index) * 100
        return (10 + query_index) * (100 + 10 * (candidate_number(ledger[0])))

    def plan_rows(self, query):
        self.plan_calls += 1
        if query["query_id"] == self.failing_query:
            raise RuntimeError("synthetic unavailable plan")
        return int(query["plan_rows"])


def candidate_number(edge: str) -> int:
    return int(edge[1:])


class Forest10RunnerTests(unittest.TestCase):
    def test_rational_log_ratio_domain_and_quantization(self) -> None:
        self.assertEqual(rational_log_ratio(1, 1), 0)
        self.assertLess(rational_log_ratio(1, 2), 0)
        self.assertGreater(rational_log_ratio(2, 1), 0)
        self.assertEqual(rational_log_ratio(1000000000001, 1000000000000), rational_log_ratio(1000000000001, 1000000000000))
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                rational_log_ratio(bad, 1)

    def test_task_models_use_only_eligible_positive_preclamp_inputs(self) -> None:
        models = build_task_models(
            ("q-0", "q-1"),
            {"q-0": 10, "q-1": 0},
            {"q-0": 20, "q-1": 30},
            {"e0": {"q-0": 40}, "e1": {"q-1": 60}},
            {"q-0": ("e0",), "q-1": ("e1",)},
        )
        self.assertEqual(models[0].alpha, rational_log_ratio(20, 10))
        self.assertEqual(models[0].b, {"e0": rational_log_ratio(40, 20)})
        self.assertEqual(models[1].alpha, rational_log_ratio(30, 1))
        with self.assertRaisesRegex(ValueError, "positive"):
            build_task_models(("q",), {"q": 1}, {"q": 0}, {"e0": {"q": 1}}, {"q": ("e0",)})

    def test_valid_calibration_and_full_test_runner_wiring_with_synthetic_backend(self) -> None:
        backend = SyntheticBackend()
        candidates = (("e0", ("a", "b")), ("e1", ("b", "c")))
        valid = ({"query_id": "q-0", "sql": "SELECT 1"}, {"query_id": "q-1", "sql": "SELECT 2"})
        selection = calibrate_and_select(
            valid,
            {"q-0": 10, "q-1": 20},
            candidates,
            {"q-0": ("e0",), "q-1": ("e1",)},
            backend,
            budgets=(0, 1),
            expected_query_count=2,
        )
        self.assertEqual(backend.configured, [(), ("e0",), ("e1",)])
        self.assertEqual(selection["selection"]["Nominal"]["0"]["selected"], [])

        test_backend = SyntheticBackend()
        result = evaluate_frozen_selections(
            ({"query_id": "t-0", "sql": "SELECT 1", "plan_rows": 10},
             {"query_id": "t-1", "sql": "SELECT 2", "plan_rows": 0}),
            {"t-0": 10, "t-1": 3},
            {"Nominal_B2": (), "PESS_B2": ()},
            test_backend,
            expected_query_count=2,
        )
        self.assertEqual(test_backend.configured, [()])
        self.assertEqual(test_backend.plan_calls, 2)
        self.assertEqual(result["metrics"]["Nominal_B2"]["p95_q1"], "3")
        self.assertEqual(result["paired_q1"]["B2"]["tie_count"], 2)

    def test_unresolved_test_observation_is_retained_and_makes_summary_inconclusive(self) -> None:
        backend = SyntheticBackend(failing_query="t-1")
        result = evaluate_frozen_selections(
            ({"query_id": "t-0", "sql": "SELECT 1", "plan_rows": 10},
             {"query_id": "t-1", "sql": "SELECT 2", "plan_rows": 3}),
            {"t-0": 10, "t-1": 3},
            {"Nominal_B2": ()},
            backend,
            expected_query_count=2,
        )
        self.assertEqual(result["query_observations"][1]["status"], "UNRESOLVED")
        summary = result["metrics"]["Nominal_B2"]
        self.assertEqual(summary["status"], "INCONCLUSIVE_UNRESOLVED_ROWS")
        self.assertEqual(summary["unresolved_count"], 1)
        self.assertIsNone(summary["p95_q1"])


if __name__ == "__main__":
    unittest.main()
