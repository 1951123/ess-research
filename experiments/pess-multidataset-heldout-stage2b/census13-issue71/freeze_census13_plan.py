"""Freeze the outcome-free Census13 valid calibration and order plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ess_research.arecel.archive import SPECS, _schema, prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.real import ARCHIVE_SHA256, UPSTREAM_COMMIT

PG_SOURCE_COMMIT = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
PR58_HELPER_COMMIT = "76106024611ae91505f1f05bdc35aed44d9c38c4"
SEEDS = tuple(range(8))
BUDGETS = (0, 2, 3)
FIRST_VALID_COUNT = 20


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def _orders(candidate_ids: list[str]) -> list[dict[str, object]]:
    orders = [
        {"label": "schema_order", "seed": None, "candidate_ids": list(candidate_ids)},
        {"label": "complete_reverse", "seed": None, "candidate_ids": list(reversed(candidate_ids))},
    ]
    for seed in SEEDS:
        order = list(candidate_ids)
        random.Random(seed).shuffle(order)
        orders.append({"label": f"python_random_seed_{seed}", "seed": seed, "candidate_ids": order})
    fingerprints = [tuple(item["candidate_ids"]) for item in orders]
    return orders + [{"duplicate_orders": [i for i, value in enumerate(fingerprints) if value == key]}
                     for key in sorted(set(fingerprints)) if fingerprints.count(key) > 1]


def build_plan() -> dict[str, object]:
    dataset = "census13"
    source_columns, _columns, _relation = _schema(dataset)
    spec = SPECS[dataset]
    with prepare_valid_workload(issue=71, dataset=dataset) as prepared:
        workload_path = prepared.workload_path
        workload = json.loads(workload_path.read_text(encoding="utf-8"))
        queries = workload["queries"]
        discovery = discover_candidates(queries, source_columns)
        support_by_pair = {
            (row["column_a"], row["column_b"]): row["eligible_valid_query_count"]
            for row in discovery["candidates"]
        }
        expected_pairs = list(combinations(source_columns, 2))
        if len(queries) != 10_000 or set(support_by_pair) != set(expected_pairs):
            raise ValueError("Census13 valid split or complete 78-pair candidate universe changed")
        candidates = [
            {
                "id": f"e{left_index:02}_{right_index:02}",
                "endpoints": [left, right],
                "eligible_valid_query_count": support_by_pair[(left, right)],
            }
            for left_index, left in enumerate(source_columns)
            for right_index, right in enumerate(source_columns[left_index + 1 :], start=left_index + 1)
        ]
        candidate_ids = [row["id"] for row in candidates]
        pairs_per_query = [
            discover_candidates([query], source_columns)["candidate_count"] for query in queries
        ]
        first_queries = queries[:FIRST_VALID_COUNT]
        first_pairs = [
            discover_candidates([query], source_columns)["candidate_count"]
            for query in first_queries
        ]
        schema_hash = hashlib.sha256(
            json.dumps(list(source_columns), separators=(",", ":")).encode()
        ).hexdigest()
        candidate_support_sha = hashlib.sha256(
            json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        valid_workload_sha = digest_file(workload_path)
        manifest = prepared.manifest

    if sum(pairs_per_query) != sum(row["eligible_valid_query_count"] for row in candidates):
        raise ValueError("pairwise support sum does not equal singleton schedule size")
    if any(row["eligible_valid_query_count"] <= 0 for row in candidates):
        raise ValueError("every frozen candidate must have at least one eligible valid query")
    orders = _orders(candidate_ids)
    duplicate_groups = [row["duplicate_orders"] for row in orders if "duplicate_orders" in row]
    actual_orders = [row for row in orders if "candidate_ids" in row]
    if len(actual_orders) != 10 or duplicate_groups:
        raise ValueError(f"expected ten distinct predeclared orders, duplicates={duplicate_groups}")

    first_ids = [row["query_id"] for row in first_queries]
    full_eligible = sum(row["eligible_valid_query_count"] for row in candidates)
    small_eligible = sum(first_pairs)
    return {
        "format": "ess-issue71-census13-stage2b-plan-v1",
        "status": "FROZEN_OUTCOME_FREE_PLAN",
        "dataset": dataset,
        "scientific_scope": "Census13 official valid-only model calibration and Nominal priority-order sensitivity; no test evaluation",
        "source": {
            "arecel_upstream_commit": UPSTREAM_COMMIT,
            "arecel_archive_sha256": ARCHIVE_SHA256,
            "valid_workload_json_sha256": valid_workload_sha,
            "plan_generator_sha256": digest_file(Path(__file__).resolve()),
            "etl_code_commit": manifest["etl"]["git_commit"],
            "etl_worktree_dirty": manifest["etl"]["worktree_dirty"],
            "candidate_discovery_code_sha256": digest_file(REPO_ROOT / "src/ess_research/arecel/candidates.py"),
            "python_version": platform.python_version(),
            "labels_loaded": manifest["labels_loaded"],
            "test_truth_loaded": False,
            "postgresql_source_commit": PG_SOURCE_COMMIT,
            "pr58_corrected_log_helper_commit": PR58_HELPER_COMMIT,
        },
        "dataset_shape": {
            "official_relation": spec.relation,
            "source_row_count": spec.expected_rows,
            "source_columns_in_order": list(source_columns),
            "source_schema_sha256": schema_hash,
            "official_split_counts_from_pinned_inventory": {"train": 100_000, "valid": 10_000, "test": 10_000},
        },
        "candidate_policy": {
            "rule": "Issue #67 supported restriction screen over distinct source columns; keep each positively supported unordered pair in schema-column order",
            "candidate_count": len(candidates),
            "candidate_support_sha256": candidate_support_sha,
            "candidates": candidates,
            "valid_queries_by_eligible_pair_count": {
                str(k): v for k, v in sorted(Counter(pairs_per_query).items())
            },
            "minimum_support": min(row["eligible_valid_query_count"] for row in candidates),
            "maximum_support": max(row["eligible_valid_query_count"] for row in candidates),
        },
        "nominal_priority_orders": {
            "algorithm": "Python random.Random(seed).shuffle over schema-order candidate IDs; CPython version recorded above",
            "seed_set": list(SEEDS),
            "order_count": 10,
            "duplicate_groups": duplicate_groups,
            "orders": actual_orders,
        },
        "selection": {
            "budgets_at_most": list(BUDGETS),
            "feasible_subset_counts": {"0": 1, "2": 3_082, "3": 79_158},
            "nominal": "frozen corrected-log sum absolute residual; exact Fraction enumeration for each listed priority order; preserve all ties and existing deterministic first-in-enumeration representative",
            "pess": "frozen task-wise maximum over all inclusion-maximal matchings; compute global exact optimum once; report PESS loss for each Nominal minimizer",
            "coefficient_source": "Census13 official valid truth and valid-only Empty/singleton nrows_preclamp; positive finite pre-clamp values only; preserve NO_MCV_EVENTS rows",
        },
        "acquisition": {
            "interface": "EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF); nrows_preclamp only",
            "full_valid_queries": 10_000,
            "empty_calls": 10_000,
            "eligible_singleton_calls": full_eligible,
            "total_calls": 10_000 + full_eligible,
            "configuration_count": 1 + len(candidates),
            "parallel_worker_count": 2,
            "configuration_assignment": "Empty on worker-0; candidate configurations round-robin by frozen candidate index; one owner per configuration; query loop serial within worker",
            "each_worker": "independent PGDATA, socket, log/output, and cluster; same pinned installed binaries, table bytes, and SHA-256-verified fixed ANALYZE sample",
            "sample": "one freshly exported sample from the run-local public.census13 relation; replay identical sample bytes in every worker; require matching header/table identity and SHA-256",
            "hard_limits": {"elapsed_hours": 8, "run_directory_gib": 4, "early_stop_elapsed_hours": 7.5, "early_stop_run_directory_gib": 3},
        },
        "serial_parallel_smoke": {
            "valid_query_ids": first_ids,
            "selection_rule": "source_index 0 through 19, fixed before measurements and using valid workload structure only",
            "singleton_calls_per_mode": small_eligible,
            "empty_calls_per_mode": FIRST_VALID_COUNT,
            "calls_per_mode": FIRST_VALID_COUNT + small_eligible,
            "modes": ["serial_one_cluster", "two_workers_two_clusters"],
            "planned_calls_total": 2 * (FIRST_VALID_COUNT + small_eligible),
            "same_sample_across_modes": True,
            "parallel_configuration_owner": "same deterministic round-robin policy as full acquisition; Empty assigned only once",
            "comparison": "require exact Decimal pre-clamp equality and equal normalized diagnostic status/MCV candidate/clause evidence for every (query_id, config_id); retain actual OIDs in raw records and verify each maps to its worker's configured catalog ledger",
        },
        "execution_code_commit": _git_commit(),
        "claim_limits": [
            "This plan has no PostgreSQL observations yet.",
            "Static eligibility is not actual PostgreSQL MCV selection or benefit.",
            "No test truth, test estimates, or test outcomes may influence acquisition, fitting, or resource choice.",
            "Official test evaluation is outside this Issue's current authorization.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_plan()
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
