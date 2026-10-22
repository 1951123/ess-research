"""Exploratory Forest10 valid-only Nominal priority-order sensitivity analysis."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import random
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from forest10_exact_selection import TaskModel, exact_select_many, model_loss


FORMAT = "ess-issue64-forest10-nominal-order-sensitivity-v1"
SEEDS = tuple(range(8))
BUDGETS = (0, 2, 3)


def seeded_orders(candidate_ids: tuple[str, ...]) -> list[dict[str, object]]:
    """Return frozen, reverse, and Python Random(seed).shuffle permutations."""
    orders: list[dict[str, object]] = [
        {"label": "frozen_original", "seed": None, "candidate_order": list(candidate_ids)},
        {"label": "complete_reverse", "seed": None, "candidate_order": list(reversed(candidate_ids))},
    ]
    for seed in SEEDS:
        permutation = list(candidate_ids)
        random.Random(seed).shuffle(permutation)
        orders.append({"label": f"python_random_seed_{seed}", "seed": seed, "candidate_order": permutation})
    return orders


def read_models(path: Path, candidates: tuple[str, ...]) -> tuple[TaskModel, ...]:
    models: list[TaskModel] = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            record = json.loads(line)
            alpha = Fraction(record["alpha_fraction"])
            b = {edge: Fraction(value) for edge, value in record["b_fraction"].items()}
            if set(b) - set(candidates):
                raise ValueError(f"unknown edge in coefficient row {line_number}")
            if not all(value == 0 or isinstance(value, Fraction) for value in b.values()):
                raise ValueError(f"invalid exact coefficient in row {line_number}")
            models.append(TaskModel(alpha, b, tuple(record["b_fraction"])))
    if len(models) != 10_000:
        raise ValueError(f"expected 10000 frozen valid coefficient rows, got {len(models)}")
    return tuple(models)


def candidate_endpoints(candidate_ids: tuple[str, ...]) -> tuple[tuple[str, tuple[str, str]], ...]:
    result = []
    for edge in candidate_ids:
        left, right = edge.removeprefix("e").split("_")
        result.append((edge, (f"v{left}", f"v{right}")))
    return tuple(result)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def analyze(frozen_path: Path, coefficient_path: Path) -> dict[str, object]:
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    candidate_ids = tuple(frozen["inputs"]["candidate_order"])
    if len(candidate_ids) != 45 or len(set(candidate_ids)) != 45:
        raise ValueError("frozen Forest10 candidate universe is not 45 unique edges")
    candidates = candidate_endpoints(candidate_ids)
    endpoints = dict(candidates)
    models = read_models(coefficient_path, candidate_ids)
    orders = seeded_orders(candidate_ids)
    encodings = [tuple(item["candidate_order"]) for item in orders]
    duplicate_groups: dict[str, list[str]] = {}
    for item in orders:
        key = hashlib.sha256("\n".join(item["candidate_order"]).encode()).hexdigest()
        duplicate_groups.setdefault(key, []).append(item["label"])
    duplicates = [labels for labels in duplicate_groups.values() if len(labels) > 1]

    reference_pess = frozen["selection"]["results"]["PESS"]
    reference_pess_objectives = {
        budget: Fraction(reference_pess[str(budget)]["objective_fraction"]) for budget in BUDGETS
    }
    results: list[dict[str, object]] = []
    all_selected_sets: dict[str, set[tuple[str, ...]]] = {str(b): set() for b in BUDGETS}
    for order in orders:
        ordered_candidates = tuple((edge, endpoints[edge]) for edge in order["candidate_order"])
        nominal = exact_select_many(models, ordered_candidates, BUDGETS)["Nominal"]
        budgets_result: dict[str, object] = {}
        for budget in BUDGETS:
            row = nominal[str(budget)]
            ties = [tuple(sorted(item)) for item in row["all_optimal_sets"]]
            all_selected_sets[str(budget)].update(ties)
            pess_by_tie = {
                ",".join(items): str(sum((model_loss(model, items, "PESS", endpoints,
                                                       candidate_ids) for model in models), Fraction(0)))
                for items in sorted(set(ties))
            }
            chosen = tuple(row["selected"])
            budgets_result[str(budget)] = {
                "nominal_objective_fraction": row["objective_fraction"],
                "tie_count": row["tie_count"],
                "all_optimal_sets": row["all_optimal_sets"],
                "deterministic_representative": row["selected"],
                "representative_pess_worst_case_fraction": pess_by_tie[",".join(sorted(chosen))],
                "pess_worst_case_fraction_for_each_nominal_minimizer": pess_by_tie,
                "frozen_pess_global_optimum_fraction": str(reference_pess_objectives[budget]),
                "representative_pess_gap_to_frozen_global_optimum_fraction": str(
                    Fraction(pess_by_tie[",".join(sorted(chosen))]) - reference_pess_objectives[budget]
                ),
                "representative_edges_pairwise_vertex_disjoint": all(
                    set(endpoints[left]).isdisjoint(endpoints[right])
                    for i, left in enumerate(chosen) for right in chosen[i + 1 :]
                ),
            }
        results.append({**order, "budgets": budgets_result})

    summary: dict[str, object] = {}
    for budget in BUDGETS:
        rows = [Fraction(item["budgets"][str(budget)]["nominal_objective_fraction"]) for item in results]
        representative_sets = [
            tuple(item["budgets"][str(budget)]["deterministic_representative"]) for item in results
        ]
        freq = Counter(edge for selected in representative_sets for edge in selected)
        summary[str(budget)] = {
            "distinct_nominal_optimal_sets_across_10_orders": len(all_selected_sets[str(budget)]),
            "distinct_deterministic_representatives_across_10_orders": len(set(representative_sets)),
            "union_of_all_order_minimizers": [list(items) for items in sorted(all_selected_sets[str(budget)])],
            "nominal_objective_min_fraction": str(min(rows)),
            "nominal_objective_max_fraction": str(max(rows)),
            "nominal_objective_range_fraction": str(max(rows) - min(rows)),
            "representative_edge_frequency": dict(sorted(freq.items())),
            "all_representatives_pairwise_vertex_disjoint": all(
                item["budgets"][str(budget)]["representative_edges_pairwise_vertex_disjoint"]
                for item in results
            ),
        }

    return {
        "format": FORMAT,
        "evidence_label": "EXPLORATORY VALID-ONLY / NOT HELD-OUT EVIDENCE",
        "method": {
            "coefficients": "reused exact alpha_fraction and b_fraction from frozen artifact; no refit",
            "nominal_matching": "existing exact selector greedy maximal matching in supplied priority order",
            "objective_arithmetic": "exact Fraction comparisons over frozen rationalized coefficients",
            "randomization": "Python random.Random(seed).shuffle; seeds 0 through 7; no rerolls",
            "budgets": list(BUDGETS),
        },
        "inputs": {
            "frozen_selection_sha256": sha256(frozen_path),
            "coefficient_artifact_sha256": sha256(coefficient_path),
            "analysis_script_sha256": sha256(Path(__file__).resolve()),
            "exact_selector_sha256": sha256(HERE / "forest10_exact_selection.py"),
            "candidate_count": len(candidate_ids),
            "coefficient_task_count": len(models),
            "candidate_ids": list(candidate_ids),
            "candidate_endpoints": {edge: list(ends) for edge, ends in candidates},
        },
        "order_count": len(orders),
        "distinct_order_count": len(set(encodings)),
        "duplicate_order_groups": duplicates,
        "runtime": {"python_implementation": platform.python_implementation(), "python_version": platform.python_version()},
        "orders": results,
        "summary_by_budget": summary,
        "frozen_pess_global_results": {
            str(b): {
                "objective_fraction": str(reference_pess_objectives[b]),
                "all_optimal_sets": reference_pess[str(b)]["all_optimal_sets"],
                "selected": reference_pess[str(b)]["selected"],
            }
            for b in BUDGETS
        },
        "scope_limits": [
            "No PostgreSQL was run; priority orders are model inputs, not observed OID assignments.",
            "No test truth, estimates, outcomes, or test evaluation were read or used.",
            "Nominal and PESS objective values are different criteria; their numerical difference is not a PostgreSQL gain.",
            "PESS global optimum and minimizers are cited from the previously frozen exact selection artifact.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, default=HERE / "forest10-valid-frozen-selection-v1.json")
    parser.add_argument("--coefficients", type=Path, default=HERE / "coefficients.jsonl.gz")
    args = parser.parse_args()
    result = analyze(args.frozen, args.coefficients)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
