from __future__ import annotations

import random
import unittest
from fractions import Fraction

from bounds import evaluate_bounds, exact_worst_prefix_witness, greedy_witness, witness_bound
from reference import Edge, Instance, Task, exact_completion_optimum, global_floor, is_maximal, maximal_matching_labels


def task(name: str, edges: tuple[Edge, ...], coefficients: dict[str, int], alpha: int = 0) -> Task:
    return Task(name, Fraction(1), Fraction(alpha), edges, {k: Fraction(v) for k, v in coefficients.items()})


class Stage0AReferenceTests(unittest.TestCase):
    def test_maximal_is_not_maximum_cardinality(self) -> None:
        edges = (("ab", "a", "b"), ("bc", "b", "c"), ("cd", "c", "d"))
        maximal = maximal_matching_labels(edges)
        self.assertIn(("bc",), maximal)
        self.assertIn(("ab", "cd"), maximal)
        self.assertNotEqual(len(("bc",)), len(("ab", "cd")))
        self.assertTrue(all(is_maximal(edges, m) for m in maximal))

    def test_parallel_labels_remain_distinct(self) -> None:
        edges = (("e1", "a", "b"), ("e2", "a", "b"))
        self.assertEqual(maximal_matching_labels(edges), (("e2",), ("e1",)))

    def test_root_floor_special_case(self) -> None:
        edges = (("ab", "a", "b"), ("bc", "b", "c"), ("cd", "c", "d"))
        t = task("t", edges, {"ab": 2, "bc": -3, "cd": 1}, alpha=-1)
        instance = Instance(("ab", "bc", "cd"), (t,), {x: Fraction(1) for x in ("ab", "bc", "cd")}, Fraction(3))
        root, _, _ = witness_bound(instance, set(), set(instance.resources), "greedy")
        self.assertEqual(root, global_floor(instance))

    def test_zero_cost_fractional_knapsack_is_safe(self) -> None:
        edges = (("zero", "a", "b"), ("paid", "c", "d"))
        t = task("t", edges, {"zero": 5, "paid": 1})
        instance = Instance(("zero", "paid"), (t,), {"zero": Fraction(0), "paid": Fraction(2)}, Fraction(0))
        snapshot = evaluate_bounds(instance, set(), set(instance.resources))
        self.assertEqual(snapshot.sensitivity_fractional, Fraction(0))

    def test_randomized_pointwise_bound(self) -> None:
        rng = random.Random(3019)
        for trial in range(40):
            resources = tuple(f"e{i}" for i in range(4))
            vertex_pairs = (("a", "b"), ("b", "c"), ("c", "d"), ("d", "a"))
            edges = tuple((label, *vertex_pairs[i]) for i, label in enumerate(resources))
            tasks = []
            for ti in range(1 + trial % 3):
                chosen = tuple(edges[i] for i in range(4) if rng.random() < 0.75)
                if not chosen:
                    chosen = (edges[trial % 4],)
                tasks.append(task(f"t{ti}", chosen, {e[0]: rng.randint(-2, 2) for e in chosen}, rng.randint(-2, 2)))
            instance = Instance(resources, tuple(tasks), {x: Fraction(rng.randint(0, 2)) for x in resources}, Fraction(3))
            forced = {x for x in resources if rng.random() < 0.4}
            undecided = set(resources) - forced
            if not instance.feasible(forced):
                continue
            for strategy in ("greedy", "exact", "pooled"):
                bound, _, _ = witness_bound(instance, forced, undecided, strategy)
                for completion in range(1 << len(undecided)):
                    picked = {label for index, label in enumerate(sorted(undecided)) if completion & (1 << index)}
                    if instance.cost(picked) <= instance.budget - instance.cost(forced):
                        self.assertLessEqual(bound, instance.objective(forced | picked), (trial, strategy, forced, picked))


if __name__ == "__main__":
    unittest.main()

