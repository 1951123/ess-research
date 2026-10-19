from __future__ import annotations

import json
import sys
import unittest
from fractions import Fraction
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from analyze_v1 import analyze
from run_pilot import setup_deltas
from stage0b_approx import solve_rounded
from stage0b_quantization import (
    certify_matching_errors,
    quantized_coefficients,
    rho_exhaustive,
    rho_independent,
)
from stage0b_reference import (
    Instance,
    Task,
    exact_outer_optimum,
    maximal_matching_labels,
    task_loss,
)
from stage0b_serialization import instance_from_json, read_json


def one_task(name, alpha, edges, coefficients, budget=1):
    task = Task(
        "t0",
        Fraction(1),
        Fraction(alpha),
        tuple(edges),
        {edge[0]: Fraction(value) for edge, value in zip(edges, coefficients)},
    )
    resources = tuple(dict.fromkeys(edge[0] for edge in edges))
    return Instance(name, resources, (task,), {label: Fraction(1) for label in resources}, Fraction(budget))


class ReferenceAndCertificateTests(unittest.TestCase):
    def test_labeled_maximal_matching_and_parallel_edges(self):
        edges = (("e0", "a", "b"), ("e1", "b", "c"), ("e2", "c", "d"))
        maximal = maximal_matching_labels(edges)
        self.assertIn(("e1",), maximal)
        self.assertIn(("e0", "e2"), maximal)
        parallel = (("e0", "a", "b"), ("e1", "a", "b"))
        self.assertEqual(set(maximal_matching_labels(parallel)), {("e0",), ("e1",)})

    def test_rho_has_independent_ordinary_matching_cross_check(self):
        instance = one_task("rho", "0", (("e0", "a", "b"), ("e1", "c", "d"), ("e2", "e", "f")), ("1/3", "-1/2", "1"))
        rounded = {"t0": {label: Fraction(0) for label in ("e0", "e1", "e2")}}
        a = rho_exhaustive(instance.tasks[0], rounded["t0"])
        b = rho_independent(instance.tasks[0], rounded["t0"])
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[0], Fraction(11, 6))
        self.assertEqual(certify_matching_errors(instance, rounded)["eta"], Fraction(11, 6))

    def test_pointwise_bound_for_every_feasible_small_selection_and_setup(self):
        paths = sorted((HERE / "instances").glob("*.json"))
        loaded = [instance_from_json(read_json(path)) for path in paths]
        small = [instance for instance in loaded if instance.tier == "small"]
        # Keep this definition-driven: enumerate every outer feasible M and compare
        # the original/rounded task-wise objectives directly with eta.
        for instance in small:
            for setup_id in ("coarse_uniform_delta_1", "matching_aware_eta_1_2", "matching_aware_eta_1_4"):
                rounded = quantized_coefficients(instance, setup_deltas(instance, setup_id))
                eta = certify_matching_errors(instance, rounded)["eta"]
                labels = instance.resources
                for size in range(len(labels) + 1):
                    for picked in combinations(labels, size):
                        selected = frozenset(picked)
                        if not instance.feasible(selected):
                            continue
                        original = instance.objective(selected)
                        perturbed = instance.objective(selected, rounded)
                        self.assertLessEqual(-eta, original - perturbed, (instance.name, setup_id, selected))
                        self.assertLessEqual(original - perturbed, eta, (instance.name, setup_id, selected))

    def test_certificate_interval_contains_independent_original_truth(self):
        path = HERE / "instances" / "rounded_zero_selected_edge.json"
        instance = instance_from_json(read_json(path))
        setup = "coarse_uniform_delta_1"
        rounded = quantized_coefficients(instance, setup_deltas(instance, setup))
        perturbation = certify_matching_errors(instance, rounded)
        approx = solve_rounded(instance, rounded, exact_tiny=True, time_limit_seconds=30, state_cap=4096)
        truth = exact_outer_optimum(instance, time_limit_seconds=30, state_cap=4096)
        self.assertTrue(approx.complete_global_search)
        self.assertTrue(truth.complete)
        original_incumbent = instance.objective(approx.selection)
        lower = max(Fraction(0), approx.rounded_value - perturbation["eta"])
        upper = min(original_incumbent, approx.rounded_value + perturbation["eta"])
        self.assertLessEqual(lower, truth.best_value)
        self.assertLessEqual(truth.best_value, upper)
        self.assertEqual(approx.selection.intersection({"e0"}), {"e0"})
        self.assertEqual(rounded["t0"]["e0"], Fraction(0))
        self.assertEqual(perturbation["eta"], Fraction(1, 3))
        self.assertEqual(original_incumbent, Fraction(0))
        self.assertEqual(truth.best_value, Fraction(0))

    def test_nearest_grid_corollary_is_checked_when_delta_is_known(self):
        instance = one_task("corollary", "0", (("e0", "a", "b"), ("e1", "c", "d")), ("1/3", "-1/2"))
        rounded = {"t0": {"e0": Fraction(0), "e1": Fraction(0)}}
        result = certify_matching_errors(instance, rounded, {"t0": Fraction(1)})
        row = result["tasks"][0]
        self.assertEqual(row["nu"], Fraction(2))
        self.assertEqual(row["corollary_rhs"], Fraction(1))
        self.assertTrue(row["corollary_holds"])

    def test_rounded_zero_conflict_edge_must_remain_eligible(self):
        # Both selected edges share b.  Keeping the rounded-zero e0 preserves
        # maximal singleton outcomes; deleting it changes the admissible family.
        edges = (("e0", "a", "b"), ("e1", "b", "c"))
        original = {"e0": Fraction(1, 3), "e1": Fraction(-2)}
        rounded = {"e0": Fraction(0), "e1": Fraction(-2)}
        kept = task_loss(Fraction(2), edges, rounded)
        dropped = task_loss(Fraction(2), (edges[1],), {"e1": rounded["e1"]})
        self.assertEqual(kept, Fraction(2))
        self.assertEqual(dropped, Fraction(0))
        self.assertNotEqual(original["e0"], rounded["e0"])


class DerivedV1AnalysisTests(unittest.TestCase):
    def test_tiny_timing_columns_match_labeled_tier(self):
        run_dir = HERE / "runs" / "20261019-issue33-v1"
        result = analyze(run_dir)
        for summary in result["by_setup"].values():
            self.assertEqual(summary["tiny_rows"], 12)
            self.assertEqual(summary["rounded_solver_core_time"]["count"], 12)
            self.assertEqual(summary["recorded_partial_core_plus_certificate_time"]["count"], 12)

    def test_matching_aware_bound_is_never_looser_on_same_rounded_coefficients(self):
        run_dir = HERE / "runs" / "20261019-issue33-v1"
        result = analyze(run_dir)
        expected_strict_counts = {
            "unrounded": 0,
            "coarse_uniform_delta_1": 6,
            "matching_aware_eta_1_2": 2,
            "matching_aware_eta_1_4": 0,
        }
        ablation = result["same_rounded_bound_ablation"]
        for setup, summary in ablation["by_setup"].items():
            self.assertEqual(summary["rows"], 15)
            self.assertEqual(summary["strictly_tighter_count"], expected_strict_counts[setup])
            self.assertEqual(
                summary["equal_count"], 15 - expected_strict_counts[setup]
            )
            for row in summary["strictly_tighter_rows"] + summary["zero_gain_rows"]:
                self.assertLessEqual(
                    Fraction(row["matching_aware_eta"]),
                    Fraction(row["naive_all_edge_eta"]),
                )

    def test_empty_task_and_zero_sum_are_well_defined(self):
        task = Task("empty", Fraction(1), Fraction(-2), (), {})
        self.assertEqual(task_loss(task.alpha, task.edges, task.coefficients), Fraction(2))
        instance = Instance("empty", ("e0",), (task,), {"e0": Fraction(0)}, Fraction(0))
        self.assertEqual(instance.objective(frozenset()), Fraction(2))


class CounterexampleTests(unittest.TestCase):
    def test_counterexample_records_are_live(self):
        counterexamples = json.loads((HERE / "counterexamples.json").read_text(encoding="utf-8"))
        self.assertEqual({row["id"] for row in counterexamples}, {
            "naive_signed_cancellation",
            "nonmonotonicity",
            "maximum_cardinality_not_maximum_weight",
            "matching_witness_is_not_upper_bound",
            "rounded_optimum_is_not_original_optimum",
            "no_multiplicative_ratio_at_zero_optimum",
        })

    def test_naive_signed_cancellation_fails(self):
        instance = one_task("signed", "0", (("e0", "a", "b"), ("e1", "b", "c")), ("1", "-1"))
        self.assertEqual(instance.objective({"e0", "e1"}), Fraction(1))
        self.assertEqual(abs((Fraction(1) - 0) + (Fraction(-1) - 0)), Fraction(0))

    def test_addition_can_worsen_maximal_matching_objective(self):
        instance = one_task("nonmono", "0", (("e0", "a", "b"), ("e1", "b", "c")), ("0", "3"))
        self.assertEqual(instance.objective({"e0"}), Fraction(0))
        self.assertEqual(instance.objective({"e0", "e1"}), Fraction(3))

    def test_maximum_cardinality_is_not_maximum_weight(self):
        edges = (("e0", "a", "b"), ("e1", "b", "c"), ("e2", "c", "d"))
        weights = {"e0": Fraction(1), "e1": Fraction(100), "e2": Fraction(1)}
        from stage0b_reference import matching_labels
        ordinary_best = max(sum((weights[label] for label in matching), Fraction(0)) for matching in matching_labels(edges))
        maximum_cardinality_value = sum(weights[label] for label in ("e0", "e2"))
        self.assertEqual(ordinary_best, Fraction(100))
        self.assertEqual(maximum_cardinality_value, Fraction(2))

    def test_witness_is_not_an_original_objective_upper_bound(self):
        instance = one_task("witness", "0", (("e0", "a", "b"), ("e1", "b", "c")), ("1", "10"))
        self.assertEqual(abs(Fraction(1)), Fraction(1))
        self.assertEqual(instance.objective({"e0", "e1"}), Fraction(10))

    def test_rounded_optimum_can_differ_from_original_optimum(self):
        instance = one_task("rounding", "1/3", (("e0", "a", "b"),), ("-1/3",))
        rounded = {"t0": {"e0": Fraction(0)}}
        result = solve_rounded(instance, rounded, exact_tiny=True, time_limit_seconds=30, state_cap=4096)
        self.assertEqual(result.selection, frozenset({"e0"}))
        self.assertEqual(result.rounded_value, Fraction(1, 3))
        self.assertEqual(instance.objective(result.selection), Fraction(0))

    def test_multiplicative_ratio_is_undefined_at_zero_optimum(self):
        instance = one_task("ratio", "0", (("e0", "a", "b"),), ("1",))
        self.assertEqual(instance.objective(set()), Fraction(0))
        self.assertEqual(instance.objective({"e0"}), Fraction(1))


if __name__ == "__main__":
    unittest.main()
