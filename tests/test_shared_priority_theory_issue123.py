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

def acyclic(vertices, arcs):
    """Independent subset oracle: repeatedly remove vertices of indegree zero."""
    remaining = set(vertices)
    while remaining:
        source = next((v for v in remaining if
                       not any(u in remaining and w == v for u, w in arcs)), None)
        if source is None:
            return False
        remaining.remove(source)
    return True

def mas_subset_oracle(vertices, arcs):
    """Enumerate acyclic ARC SUBSETS, not resource priorities."""
    best = 0
    for mask in range(1 << len(arcs)):
        selected = [arc for j, arc in enumerate(arcs) if mask & (1 << j)]
        if len(selected) > best and acyclic(vertices, selected):
            best = len(selected)
    return best

def ess_order_score(vertices, arcs, order):
    """Build actual ESS two-edge task graphs and execute matching greedy."""
    resources = {v: (len(vertices), v) for v in vertices}
    loss = 0
    for u, v in arcs:
        selected = greedy(resources, frozenset((u, v)), order)
        # Normalized log loss: base=1; factor 2 for u, factor 1 for v.
        loss += int(selected == frozenset((u,)))
    return loss

def independently_maximal(edges, selected):
    """Explicit edge-subset maximality oracle, without invoking greedy."""
    for x, y in itertools.combinations(selected, 2):
        if conflicts(edges[x], edges[y]):
            return False
    return all(any(conflicts(edges[x], edges[y]) for y in selected)
               for x in edges if x not in selected)

class TheoryAudit(unittest.TestCase):
    def test_fixed_tuple_bruteforce(self):
        rng = random.Random(SEED)
        cases = 0
        feasible = 0
        infeasible = 0
        for m in range(0, 8):
            for _ in range(120):
                # Equal endpoint pairs are allowed: labeled parallel edges.
                edges = {i: tuple(rng.sample(range(4), 2)) for i in range(m)}
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
        # Exhaust all simple digraphs up to three vertices; larger cases are sampled.
        rng = random.Random(SEED + 2)
        count = 0
        for n in range(0, 5):
            vertices = tuple(range(n))
            pairs = [(u, v) for u in vertices for v in vertices if u != v]
            masks = (range(1 << len(pairs)) if n <= 3 else
                     [rng.getrandbits(len(pairs)) for _ in range(160)])
            for mask in masks:
                arcs = [a for j, a in enumerate(pairs) if mask & (1 << j)]
                observed = [ess_order_score(vertices, arcs, p)
                            for p in itertools.permutations(vertices)]
                self.assertEqual(max(observed), mas_subset_oracle(vertices, arcs))
                self.assertEqual(sum(observed) * 2, len(observed) * len(arcs))
                self.assertEqual(max(observed) == len(arcs), acyclic(vertices, arcs))
                count += 1
        # Explicit antiparallel and repeated-arc fixtures.
        for vertices, arcs in [
            ((0, 1), [(0, 1), (1, 0)]),
            ((0, 1), [(0, 1), (0, 1)]),
            ((0, 1, 2), [(0, 1), (1, 2), (2, 0)]),
        ]:
            observed = [ess_order_score(vertices, arcs, p)
                        for p in itertools.permutations(vertices)]
            self.assertEqual(max(observed), mas_subset_oracle(vertices, arcs))
        print("independent MAS subset-oracle graphs:", count)

    def test_tight_star(self):
        # All edges share hub 0, and task i has correction factor 2 only on e_i.
        for k in range(1, 8):
            edges = {i: (0, i + 1) for i in range(k)}
            orders = itertools.permutations(edges)
            totals = []
            for order in orders:
                task_losses = []
                for i in edges:
                    result = greedy(edges, frozenset(edges), order)
                    task_losses.append(int(result == frozenset((i,))))
                totals.append(sum(task_losses))
            self.assertEqual(min(totals), 1)
            self.assertEqual(max(totals), 1)
            self.assertEqual(sum(totals), len(totals))
            self.assertEqual(sum(max(int(j == i) for j in edges)
                                 for i in edges), k)

    def test_minimum_maximal_matching_identity(self):
        rng = random.Random(SEED + 1)
        cases = 0
        for m in range(0, 7):
            for _ in range(70):
                edges = {i: tuple(rng.sample(range(5), 2)) for i in range(m)}
                by_subset = {frozenset(s) for n in range(m + 1)
                             for s in itertools.combinations(edges, n)
                             if independently_maximal(edges, frozenset(s))}
                by_priority = {greedy(edges, frozenset(edges), p)
                               for p in itertools.permutations(edges)}
                self.assertEqual(by_subset, by_priority)
                self.assertEqual(
                    max(m - len(s) for s in by_priority),
                    m - min(len(s) for s in by_subset)
                )
                cases += 1
        print("independent MMM subset-oracle cases:", cases)

if __name__ == "__main__":
    unittest.main(verbosity=2)
