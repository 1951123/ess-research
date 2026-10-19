#!/usr/bin/env python3
"""Run the frozen, exact Stage 0A pilot and write auditable evidence."""

from __future__ import annotations

import hashlib
import itertools
import json
import platform
import random
import sys
import time
from fractions import Fraction
from pathlib import Path

from bounds import evaluate_bounds, witness_bound
from reference import Edge, Instance, Task, all_subsets, exact_completion_optimum, global_floor, is_maximal

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "pilot-manifest.json"
RUN_DIR = ROOT / "runs" / "20261019-issue30-v1"


def make_task(name: str, weight: int, alpha: int, edges: tuple[Edge, ...], coefficients: dict[str, int]) -> Task:
    return Task(
        name,
        Fraction(weight),
        Fraction(alpha),
        edges,
        {label: Fraction(value) for label, value in coefficients.items()},
    )


def deterministic_instances() -> list[tuple[str, Instance]]:
    path = (("ab", "a", "b"), ("bc", "b", "c"), ("cd", "c", "d"))
    parallel = (("p1", "a", "b"), ("p2", "a", "b"), ("d1", "c", "d"), ("d2", "e", "f"))
    star = tuple((f"s{i}", "c", leaf) for i, leaf in enumerate(("a", "b", "d", "e", "f", "g")))
    cycle = (
        ("ca", "a", "b"), ("cb", "b", "c"), ("cc", "c", "d"),
        ("cd", "d", "a"), ("ce", "a", "c"), ("cf", "b", "d"),
    )
    return [
        (
            "path3_mixed_signs",
            Instance(
                tuple(edge[0] for edge in path),
                (make_task("t_path", 2, -1, path, {"ab": 2, "bc": -3, "cd": 1}),),
                {"ab": Fraction(1), "bc": Fraction(2), "cd": Fraction(1)},
                Fraction(2),
            ),
        ),
        (
            "parallel_disconnected",
            Instance(
                tuple(edge[0] for edge in parallel),
                (
                    make_task("t_parallel", 1, 0, parallel, {"p1": 2, "p2": -2, "d1": 1, "d2": 0}),
                    make_task("t_scope", 3, 2, parallel[:2] + parallel[3:], {"p1": -1, "p2": 1, "d2": 2}),
                ),
                {"p1": Fraction(1), "p2": Fraction(1), "d1": Fraction(2), "d2": Fraction(0)},
                Fraction(2),
            ),
        ),
        (
            "star_zero_cost",
            Instance(
                tuple(edge[0] for edge in star),
                (
                    make_task("t_star", 1, 3, star, {edge[0]: (-1) ** i * (i + 1) for i, edge in enumerate(star)}),
                    make_task("t_star_sub", 2, -2, star[:4], {edge[0]: i - 2 for i, edge in enumerate(star[:4])}),
                ),
                {label: Fraction(0 if index % 3 == 0 else 1) for index, label in enumerate(edge[0] for edge in star)},
                Fraction(2),
            ),
        ),
        (
            "cycle_conflict",
            Instance(
                tuple(edge[0] for edge in cycle),
                (
                    make_task("t_cycle", 2, -2, cycle, {edge[0]: value for edge, value in zip(cycle, (2, -1, 0, 3, -2, 1))}),
                    make_task("t_cycle_sparse", 1, 1, cycle[::2], {edge[0]: value for edge, value in zip(cycle[::2], (-3, 2, 1))}),
                ),
                {label: Fraction((index + 1) % 3) for index, label in enumerate(edge[0] for edge in cycle)},
                Fraction(4),
            ),
        ),
    ]


def random_instance(seed: int) -> tuple[str, Instance]:
    rng = random.Random(seed)
    n_resources = rng.randint(4, 8)
    resources = tuple(f"e{i}" for i in range(n_resources))
    base_pairs = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "a"), ("a", "c"), ("b", "d"), ("c", "e")]
    tasks: list[Task] = []
    for task_index in range(rng.randint(1, 4)):
        edges: list[Edge] = []
        for index, label in enumerate(resources):
            if rng.random() <= 0.70 or (not edges and index == n_resources - 1):
                if rng.random() < 0.18 and edges:
                    left, right = edges[-1][1:]
                else:
                    left, right = base_pairs[rng.randrange(len(base_pairs))]
                edges.append((label, left, right))
        tasks.append(
            make_task(
                f"t{task_index}",
                rng.randint(1, 3),
                rng.randint(-3, 3),
                tuple(edges),
                {label: rng.randint(-3, 3) for label, _, _ in edges},
            )
        )
    maintenance = {label: Fraction(rng.randint(0, 2)) for label in resources}
    budget = Fraction(rng.randint(0, int(min(8, sum(maintenance.values(), Fraction(0)) + 2))))
    return f"random_seed_{seed}", Instance(resources, tuple(tasks), maintenance, budget)


def instance_json(name: str, instance: Instance) -> dict[str, object]:
    return {
        "name": name,
        "resources": list(instance.resources),
        "maintenance": {label: str(instance.maintenance[label]) for label in instance.resources},
        "budget": str(instance.budget),
        "tasks": [
            {
                "name": task.name,
                "weight": str(task.weight),
                "alpha": str(task.alpha),
                "edges": [list(edge) for edge in task.edges],
                "coefficients": {label: str(task.coefficients[label]) for label, _, _ in task.edges},
            }
            for task in instance.tasks
        ],
    }


def branch_states(instance: Instance, maximum: int) -> list[tuple[set[str], set[str], set[str]]]:
    labels = tuple(instance.resources)
    states = [(set(), set(labels), set())]
    for status in itertools.product(range(3), repeat=len(labels)):
        state = (
            {label for label, value in zip(labels, status) if value == 2},
            {label for label, value in zip(labels, status) if value == 1},
            {label for label, value in zip(labels, status) if value == 0},
        )
        if state[1] == set(labels):
            continue
        states.append(state)
        if len(states) >= maximum:
            break
    return states


def completion_values(instance: Instance, forced: set[str], undecided: set[str]) -> list[tuple[frozenset[str], Fraction]]:
    remaining = instance.budget - instance.cost(forced)
    return [
        (completion, instance.objective(forced | set(completion)))
        for completion in all_subsets(tuple(sorted(undecided)))
        if instance.cost(completion) <= remaining
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    started = time.monotonic()
    timeout = float(manifest["limits"]["wall_time_seconds"])
    instances = deterministic_instances() + [random_instance(seed) for seed in manifest["corpus"]["random_seeds"]]
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    write_json(RUN_DIR / "environment.json", {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "command": "python3 experiments/pess-bound-stage0a/run_stage0a.py",
        "manifest_sha256": sha256(MANIFEST_PATH),
    })
    write_json(RUN_DIR / "frozen-instances.json", [instance_json(name, instance) for name, instance in instances])

    observations: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    aggregate = {
        label: {"nodes": 0, "exact": 0, "positive_gap": 0, "prunable": 0}
        for label in (
            "A_global_floor", "B_exact_sensitivity", "B_fractional_sensitivity",
            "C_greedy_witness", "C_exact_witness",
        )
    }
    timing = {
        "f_forced_seconds": 0.0,
        "witness_greedy_seconds": 0.0,
        "witness_exact_seconds": 0.0,
        "q_extrema_calls_greedy": 0,
        "q_extrema_calls_exact": 0,
    }
    ordinary_extrema = {"global_floor_precomputation": 0, "per_node_q_extrema": 0, "total": 0}
    pairwise = {"C_greedy_gt_A": 0, "C_greedy_gt_B_exact": 0, "C_exact_gt_C_greedy": 0}
    rejected = 0
    timed_out = False

    for instance_name, instance in instances:
        instance_floor = global_floor(instance)
        ordinary_extrema["global_floor_precomputation"] += len(instance.tasks)
        feasible_subsets = [selected for selected in all_subsets(instance.resources) if instance.feasible(selected)]
        incumbent = min(instance.objective(set(selected)) for selected in feasible_subsets)
        for forced, undecided, excluded in branch_states(instance, int(manifest["branch_states"]["max_nodes_per_instance"])):
            if time.monotonic() - started > timeout:
                timed_out = True
                break
            base = {
                "instance": instance_name,
                "forced": sorted(forced),
                "undecided": sorted(undecided),
                "excluded": sorted(excluded),
            }
            if not instance.feasible(forced):
                rejected += 1
                observations.append({**base, "status": "rejected_infeasible_forced"})
                continue
            completions = completion_values(instance, forced, undecided)
            exact_opt = min(value for _, value in completions)
            oracle_opt = exact_completion_optimum(instance, forced, undecided)
            if oracle_opt != exact_opt:
                failures.append({**base, "kind": "reference_completion_mismatch", "enumerated": str(exact_opt), "oracle": str(oracle_opt)})
            snapshot = evaluate_bounds(instance, forced, undecided, floor_override=instance_floor)
            for strategy in ("greedy", "exact"):
                _, witnesses, _ = witness_bound(instance, forced, undecided, strategy)
                for task in instance.tasks:
                    if not is_maximal(task.selected_edges(forced), witnesses[task.name]):
                        failures.append({**base, "kind": "nonmaximal_witness", "strategy": strategy, "task": task.name, "witness": list(witnesses[task.name])})
            bounds = {
                "A_global_floor": snapshot.floor,
                "B_exact_sensitivity": snapshot.sensitivity_exact,
                "B_fractional_sensitivity": snapshot.sensitivity_fractional,
                "C_greedy_witness": snapshot.witness_greedy,
                "C_exact_witness": snapshot.witness_exact,
            }
            for label, bound in bounds.items():
                aggregate[label]["nodes"] += 1
                gap = exact_opt - bound
                if gap < 0:
                    failures.append({**base, "kind": "bound_exceeds_exact_branch_optimum", "bound": label, "value": str(bound), "optimum": str(exact_opt)})
                elif gap == 0:
                    aggregate[label]["exact"] += 1
                else:
                    aggregate[label]["positive_gap"] += 1
                if bound >= incumbent:
                    aggregate[label]["prunable"] += 1
            for completion, objective in completions:
                for label in ("C_greedy_witness", "C_exact_witness"):
                    if bounds[label] > objective:
                        failures.append({**base, "kind": "pointwise_witness_failure", "bound": label, "completion": sorted(completion), "value": str(bounds[label]), "objective": str(objective)})
            pairwise["C_greedy_gt_A"] += int(bounds["C_greedy_witness"] > bounds["A_global_floor"])
            pairwise["C_greedy_gt_B_exact"] += int(bounds["C_greedy_witness"] > bounds["B_exact_sensitivity"])
            pairwise["C_exact_gt_C_greedy"] += int(bounds["C_exact_witness"] > bounds["C_greedy_witness"])
            timing["f_forced_seconds"] += snapshot.f_forced_seconds
            timing["witness_greedy_seconds"] += snapshot.witness_greedy_seconds
            timing["witness_exact_seconds"] += snapshot.witness_exact_seconds
            timing["q_extrema_calls_greedy"] += snapshot.q_calls_greedy
            timing["q_extrema_calls_exact"] += snapshot.q_calls_exact
            ordinary_extrema["per_node_q_extrema"] += snapshot.q_calls_greedy + snapshot.q_calls_exact
            observations.append({
                **base,
                "status": "evaluated",
                "branch_optimum": str(exact_opt),
                "incumbent": str(incumbent),
                "bounds": {label: str(value) for label, value in bounds.items()},
                "gaps": {label: str(exact_opt - value) for label, value in bounds.items()},
                "completion_count": len(completions),
                "timings_seconds": {
                    "f_forced": snapshot.f_forced_seconds,
                    "witness_greedy": snapshot.witness_greedy_seconds,
                    "witness_exact": snapshot.witness_exact_seconds,
                },
            })
        if timed_out:
            break

    write_json(RUN_DIR / "raw-observations.json", observations)
    write_json(RUN_DIR / "counterexamples.json", failures)
    summary = {
        "status": "TIMEOUT" if timed_out else ("FAIL" if failures else "PASS"),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "instance_count": len(instances),
        "evaluated_nodes": sum(item["nodes"] for item in aggregate.values()) // 5,
        "rejected_infeasible_forced_nodes": rejected,
        "timed_out": timed_out,
        "failures": len(failures),
        "aggregate": aggregate,
        "pairwise": pairwise,
        "timing": timing,
        "ordinary_matching_extrema_calls": {
            **ordinary_extrema,
            "total": ordinary_extrema["global_floor_precomputation"] + ordinary_extrema["per_node_q_extrema"],
        },
        "restricted_master": {
            "status": "not_executed",
            "reason": "Issue #30 forbids modifying ess-advisor or building a new solver for this bounded experiment.",
        },
    }
    write_json(RUN_DIR / "summary.json", summary)

    total_nodes = summary["evaluated_nodes"]
    greedy_exact_rate = aggregate["C_greedy_witness"]["exact"] / total_nodes if total_nodes else 0.0
    if failures or timed_out:
        recommendation = "NO-GO"
        recommendation_reason = "Correctness evidence is incomplete or a bound failed; preserve the counterexample/timeout and do not make speed claims."
    elif greedy_exact_rate < 0.25:
        recommendation = "NO-GO"
        recommendation_reason = "The cheap greedy witness was exact at fewer than 25% of evaluated nodes in this pilot; a larger solver study is not justified by this result alone."
    else:
        recommendation = "INCONCLUSIVE"
        recommendation_reason = "The exact reference passed, but the tiny corpus and lack of a fair restricted-master comparator cannot establish end-to-end value."
    report = f"""# Stage 0A pilot report

This report is an experimentally observed result from the frozen Issue #30
pilot, not a theorem or a novelty claim.

## Scope and provenance

- Manifest: pilot-manifest.json (SHA-256 {summary["manifest_sha256"]}).
- Instances: {summary["instance_count"]} (four deterministic strata and four frozen seeds).
- Evaluated feasible branch states: {summary["evaluated_nodes"]}; rejected forced-infeasible states: {summary["rejected_infeasible_forced_nodes"]}.
- Arithmetic: exact Fraction for objectives, matching extrema, bounds and feasibility; timings are diagnostic floating-point measurements only.
- Independent branch optimum: exhaustive completions, cross-checked through reference.exact_completion_optimum.
- Run status: **{summary["status"]}**; counterexamples: {summary["failures"]}.

## Correctness

The exact reference enumerates labeled ordinary matchings and filters maximal
matchings directly from the definitions. The runner checked both witness
bounds pointwise for every feasible completion and against the exact branch
optimum. A rejected forced set is recorded as rejected, never assigned a
fictitious objective. See counterexamples.json for any preserved failures.
The formalized statement and proof under the tested assumptions are in
../../lemma.md.

## Bound comparison

| Bound | Nodes | Exact branch optimum | Positive gap | Prunable by fixed exact incumbent |
|---|---:|---:|---:|---:|
""" + "\n".join(
        f"| {label} | {row['nodes']} | {row['exact']} | {row['positive_gap']} | {row['prunable']} |"
        for label, row in aggregate.items()
    ) + f"""

The fixed incumbent is the exact minimum over all feasible resource subsets
of each frozen instance. Pruning counts therefore mean only that the bound
certifies a node cannot beat that common incumbent; they are not end-to-end
branch-and-bound speed measurements.

Pairwise nonzero-strength counts were: greedy witness > A floor =
{pairwise["C_greedy_gt_A"]}, greedy witness > B exact sensitivity =
{pairwise["C_greedy_gt_B_exact"]}, and exact-prefix witness > greedy witness =
{pairwise["C_exact_gt_C_greedy"]}.

## Cost observations

The runner separately accumulated exact F(M) time ({timing["f_forced_seconds"]:.6f}s),
greedy witness/q-extrema time ({timing["witness_greedy_seconds"]:.6f}s), exact
worst-prefix witness/q-extrema time ({timing["witness_exact_seconds"]:.6f}s),
and q-extrema calls ({timing["q_extrema_calls_greedy"]} greedy,
{timing["q_extrema_calls_exact"]} exact). These are tiny-instance local
measurements, not a system performance claim.

Ordinary-matching extrema calls were separated into {ordinary_extrema["global_floor_precomputation"]}
global-floor precomputation calls, {ordinary_extrema["per_node_q_extrema"]} per-node
q-extrema calls, and {ordinary_extrema["global_floor_precomputation"] + ordinary_extrema["per_node_q_extrema"]}
total. Every reported witness was independently checked to be maximal in its
forced selected task graph.

## Comparator D

The existing restricted-master comparator was not executed. Issue #30 requires
the same node restrictions and a solver-proven or explicitly qualified bound,
while its authorized scope forbids modifying ess-advisor or building a new
solver. It is a separately scoped follow-up, not silently approximated here.

## Recommendation

**{recommendation}.** {recommendation_reason}

The result supports only the bounded mathematical diagnostic. It does not
prove theorem novelty, PostgreSQL behavior, or end-to-end optimizer speedup.
"""
    (RUN_DIR / "report.md").write_text(report, encoding="utf-8")
    files = sorted(path for path in RUN_DIR.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (RUN_DIR / "SHA256SUMS").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(RUN_DIR)}\n" for path in files),
        encoding="utf-8",
    )
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

