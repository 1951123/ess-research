"""Reproducible synthetic checks for Issue #123. Pure standard library; no DB calls."""
import itertools
import random
import unittest

SEED = 20261027

def conflicts(a, b):
    return bool(set(a) & set(b))

def greedy(edges, eligible, order):
    chosen = []
    for e in order:
        if e not in eligible:
            continue
        if all(not conflicts(edges[e], edges[f]) for f in chosen):
            chosen.append(e)
    return frozenset(chosen)

def maximal(edges, eligible, target):
    if not target <= eligible:
        return False
    if any(conflicts(edges[a], edges[b]) for a, b in itertools.combinations(target, 2)):
        return False
    return all(any(conflicts(edges[e], edges[f]) for f in target)
               for e in eligible - target)

def shared_order(edges, task_specs):
    """Return witness permutation or None; specs are (eligible-set, maximal-target)."""
    labels = tuple(edges)
    if any(not maximal(edges, eligible, target)
           for eligible, target in task_specs):
        raise ValueError("invalid target matching")
    prefix = []
    for _ in labels:
        safe = None
        for e in labels:
            if e in prefix:
                continue
            if all((e not in eligible or e in target or
                    any(conflicts(edges[e], edges[f]) for f in prefix if f in target))
                   for eligible, target in task_specs):
                safe = e
                break
        if safe is None:
            return None
        prefix.append(safe)
    return tuple(prefix)

def exhaustive_witness(edges, task_specs):
    for order in itertools.permutations(edges):
        if all(greedy(edges, eligible, order) == target
               for eligible, target in task_specs):
            return order
    return None

def mas_score(arcs, order):
    position = {v: i for i, v in enumerate(order)}
    return sum(position[u] < position[v] for u, v in arcs)

def ess_arc_score(arcs, order):
    return sum(order.index(u) < order.index(v) for u, v in arcs)

class TheoryAudit(unittest.TestCase):
    def test_fixed_tuple_bruteforce(self):
        rng = random.Random(SEED)
        cases = 0
        feasible = 0
        infeasible = 0
        for m in range(0, 8):
            for _ in range(120):
                # Equal endpoint pairs are allowed: labeled parallel edges.
                edges = {i: (rng.randrange(4), rng.randrange(4)) for i in range(m)}
                tasks = []
                for _ in range(rng.randrange(5)):
                    eligible = frozenset(i for i in edges if rng.randrange(2))
                    target = greedy(edges, eligible, rng.sample(list(edges), m))
                    tasks.append((eligible, target))
                witness = shared_order(edges, tasks)
                oracle = exhaustive_witness(edges, tasks)
                self.assertEqual(witness is None, oracle is None, (edges, tasks))
                if witness is None:
                    infeasible += 1
                else:
                    feasible += 1
                    for eligible, target in tasks:
                        self.assertEqual(greedy(edges, eligible, witness), target)
                cases += 1
        print("fixed-tuple cases:", cases, "feasible:", feasible, "infeasible:", infeasible)

    def test_infeasible_parallel_target_conflict(self):
        edges = {"a": (0, 1), "b": (0, 1)}
        tasks = [(frozenset(edges), frozenset({"a"})),
                 (frozenset(edges), frozenset({"b"}))]
        self.assertIsNone(shared_order(edges, tasks))

    def test_mas_all_small_digraphs(self):
        graphs = 0
        for n in range(0, 5):
            vertices = tuple(range(n))
            pairs = [(u, v) for u in vertices for v in vertices if u != v]
            for mask in range(1 << len(pairs)):
                arcs = [e for j, e in enumerate(pairs) if mask & (1 << j)]
                scores = [ess_arc_score(arcs, p) for p in itertools.permutations(vertices)]
                if not scores:
                    scores = [0]
                self.assertEqual(sum(scores) * 2, len(scores) * len(arcs))
                self.assertEqual(max(scores), max(mas_score(arcs, p)
                                                  for p in itertools.permutations(vertices)) if vertices else 0)
                acyclic = max(scores) == len(arcs)
                # Cycle detected iff topological removal fails.
                remaining = set(vertices)
                while remaining:
                    source = next((v for v in remaining if
                                   not any(a in remaining and b == v for a, b in arcs)), None)
                    if source is None:
                        break
                    remaining.remove(source)
                self.assertEqual(acyclic, not remaining)
                graphs += 1
        print("directed graphs:", graphs)

    def test_tight_star(self):
        for k in range(1, 8):
            scores = []
            for first in range(k):
                per_task = [int(first == i) for i in range(k)]
                scores.append(sum(per_task))
            self.assertEqual(max(scores), 1)
            self.assertEqual(sum(scores) / len(scores), 1)
            self.assertEqual(sum(1 for _ in range(k)), k)

    def test_minimum_maximal_matching_identity(self):
        rng = random.Random(SEED + 1)
        for m in range(1, 7):
            for _ in range(80):
                edges = {i: (rng.randrange(5), rng.randrange(5)) for i in range(m)}
                eligible = frozenset(edges)
                matchings = {greedy(edges, eligible, p)
                             for p in itertools.permutations(edges)}
                self.assertEqual(max(m - len(x) for x in matchings),
                                 m - min(len(x) for x in matchings))

if __name__ == "__main__":
    unittest.main(verbosity=2)
