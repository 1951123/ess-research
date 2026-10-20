"""Freeze the Issue #38 Forest10 held-out evaluation protocol.

This phase reads only versioned query shape/coverage metadata for selecting the
held-out IDs.  It deliberately does not inspect source labels, PostgreSQL
estimates, or model losses while choosing the test subset.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SOURCE_COLUMNS = {
    "Elevation",
    "Aspect",
    "Slope",
    "Horizontal_Distance_To_Hydrology",
    "Vertical_Distance_To_Hydrology",
    "Horizontal_Distance_To_Roadways",
    "Hillshade_9am",
    "Hillshade_Noon",
    "Hillshade_3pm",
    "Horizontal_Distance_To_Fire_Points",
}
SUPPORTED_OPERATORS = {"=", "<", "<=", ">", ">=", "[]"}
SELECTION_SEED = "ess-issue38-heldout-v1"
QUOTA_PER_CANDIDATE = 10
TARGET_QUERY_COUNT = 60


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_lines(lines: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def candidate_rank(seed: str, query_id: str, query_hash: str, candidate_id: str) -> str:
    value = f"{seed}|{query_id}|{query_hash}|{candidate_id}".encode()
    return hashlib.sha256(value).hexdigest()


def is_pairwise_eligible(record: dict[str, Any]) -> tuple[bool, set[str]]:
    source_query = record.get("source_query")
    predicates = source_query.get("predicates") if isinstance(source_query, dict) else None
    if not (
        isinstance(source_query, dict)
        and source_query.get("format") == "arecel-source-query-v1"
        and source_query.get("table") == "forest10_original"
        and isinstance(predicates, list)
    ):
        return False, set()
    columns: set[str] = set()
    for predicate in predicates:
        if not isinstance(predicate, dict):
            return False, set()
        if predicate.get("column") not in SOURCE_COLUMNS:
            return False, set()
        if predicate.get("operator") not in SUPPORTED_OPERATORS:
            return False, set()
        columns.add(predicate["column"])
    return len(columns) >= 2, columns


def read_records(path: Path) -> list[tuple[dict[str, Any], str]]:
    records: list[tuple[dict[str, Any], str]] = []
    with gzip.open(path, "rb") as stream:
        for line_number, raw in enumerate(stream, start=1):
            if not raw.endswith(b"\n"):
                raise ValueError(f"canonical line {line_number} lacks newline")
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise TypeError(f"canonical line {line_number} is not an object")
            records.append((record, hashlib.sha256(raw[:-1]).hexdigest()))
    return records


def frozen_sets(evidence: dict[str, Any]) -> dict[str, Any]:
    methods = ("pess", "nominal", "joint_robust")
    all_sets: set[tuple[str, ...]] = {()}
    by_method_budget: dict[str, dict[str, Any]] = {}
    for row in evidence["objective_results"]:
        budget = row["budget"]
        by_method_budget[budget] = {}
        for method in methods:
            result = row["methods"][method]
            optimal = [tuple(item) for item in result["optimal_sets"]]
            selected = tuple(result["selected"])
            all_sets.update(optimal)
            by_method_budget[budget][method] = {
                "selected": list(selected),
                "optimal_sets": [list(item) for item in optimal],
                "tie_count": result["tie_count"],
                "objective": result["objective"],
            }
    return {
        "by_budget_and_method": by_method_budget,
        "all_distinct_selected_sets": [list(item) for item in sorted(all_sets)],
        "greedy": {
            "status": "NOT_DEFINED_IN_ISSUE23_REFERENCE",
            "included": False,
            "reason": "No legitimate greedy decision set exists in the frozen Issue #23 evidence; no post-hoc greedy set is introduced.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"refusing to overwrite {args.output}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    canonical = args.data_root / "arecel" / "audit-v1" / "forest10.canonical.jsonl.gz"
    if not canonical.is_file():
        raise FileNotFoundError(canonical)
    expected = {
        "archive": args.data_root / "arecel" / "incoming" / "arecel-data.tar.gz",
        "csv": args.data_root / "arecel" / "raw" / "data" / "forest10" / "original.csv",
        "workload_pickle": args.data_root / "arecel" / "raw" / "data" / "forest10" / "workload" / "base.pkl",
        "truth_pickle": args.data_root / "arecel" / "raw" / "data" / "forest10" / "workload" / "base-original-label.pkl",
        "canonical": canonical,
        "audit": args.data_root / "arecel" / "audit-v1" / "audit.json",
    }
    expected_hashes = {
        "archive": manifest["source"]["archive_sha256"],
        "csv": manifest["source"]["csv_sha256"],
        "workload_pickle": manifest["source"]["workload_pickle_sha256"],
        "truth_pickle": manifest["source"]["label_pickle_sha256"],
        "canonical": manifest["source"]["derived_canonical_sha256"],
        "audit": "8f17118b7e64089974b3a438b87667990f98393231c13c3366d110eac61610a9",
    }
    actual_hashes = {name: sha256_file(path) for name, path in expected.items()}
    if actual_hashes != expected_hashes:
        raise RuntimeError(json.dumps({"expected": expected_hashes, "actual": actual_hashes}, sort_keys=True))
    if sha256_file(args.manifest) != "bae9202b1807c05932f17e62acaec4e09121fa5a58c994862323562f44e0c71b":
        raise RuntimeError("the Issue #23 input manifest SHA does not match its frozen report")
    if sha256_file(args.evidence) != "6085e8f7f2f140120033477b219fdb15288cd108a8f400161764eb5582afbc1f":
        raise RuntimeError("the provided evidence path is not the frozen Issue #23 model evidence SHA")

    candidates = manifest["candidate_rule"]["candidates"]
    candidate_endpoints = {item["id"]: set(item["columns"]) for item in candidates}
    candidate_ids = [item["id"] for item in candidates]
    records = read_records(canonical)
    test_records = [(record, raw_hash) for record, raw_hash in records if record.get("split") == "test"]
    pairwise_records: list[dict[str, Any]] = []
    for index, (record, raw_hash) in enumerate(test_records):
        eligible, columns = is_pairwise_eligible(record)
        if not eligible:
            continue
        covered = sorted(
            candidate_id
            for candidate_id in candidate_ids
            if candidate_endpoints[candidate_id].issubset(columns)
        )
        if not covered:
            continue
        pairwise_records.append(
            {
                "record": record,
                "record_sha256": raw_hash,
                "source_index_within_test_split": index,
                "covered_candidates": covered,
                "rank": min(
                    candidate_rank(SELECTION_SEED, record["query_id"], record["source_query_sha256"], candidate_id)
                    for candidate_id in covered
                ),
            }
        )
    by_candidate = {
        candidate_id: sorted(
            (item for item in pairwise_records if candidate_id in item["covered_candidates"]),
            key=lambda item: (
                candidate_rank(SELECTION_SEED, item["record"]["query_id"], item["record"]["source_query_sha256"], candidate_id),
                item["record"]["query_id"],
            ),
        )
        for candidate_id in candidate_ids
    }
    selected_ids: set[str] = set()
    quota_winners: dict[str, list[str]] = {}
    for candidate_id in candidate_ids:
        winners = by_candidate[candidate_id][:QUOTA_PER_CANDIDATE]
        quota_winners[candidate_id] = [item["record"]["query_id"] for item in winners]
        selected_ids.update(quota_winners[candidate_id])
    for item in sorted(pairwise_records, key=lambda item: (item["rank"], item["record"]["query_id"])):
        if len(selected_ids) >= TARGET_QUERY_COUNT:
            break
        selected_ids.add(item["record"]["query_id"])
    selected = [item for item in pairwise_records if item["record"]["query_id"] in selected_ids]
    selected.sort(key=lambda item: item["source_index_within_test_split"])
    selected_rows = [
        {
            "query_id": item["record"]["query_id"],
            "source_query_sha256": item["record"]["source_query_sha256"],
            "canonical_record_sha256": item["record_sha256"],
            "covered_candidates": item["covered_candidates"],
            "source_index_within_test_split": item["source_index_within_test_split"],
        }
        for item in selected
    ]
    selected_ids_ordered = [item["query_id"] for item in selected_rows]
    output = {
        "format": "ess-issue38-forest10-heldout-protocol-v1",
        "status": "FROZEN_BEFORE_POSTGRESQL_HELDOUT_OUTCOME_COLLECTION",
        "evidence_label": "protocol_and_input_audit_only",
        "data_root_contract": str(args.data_root.resolve()),
        "source_provenance": {
            "upstream_repository": manifest["source"]["upstream_repository"],
            "upstream_commit": manifest["source"]["upstream_commit"],
            "artifact_sha256": actual_hashes,
            "canonical_record_count": len(records),
            "test_record_count": len(test_records),
        },
        "reference_issue23": {
            "input_manifest_sha256": sha256_file(args.manifest),
            "model_evidence_sha256": sha256_file(args.evidence),
            "candidate_rule": manifest["candidate_rule"],
            "budgets": manifest["decision_protocol"]["budgets"],
            "frozen_selection_sets": frozen_sets(evidence),
            "truth_floor": "T=max(1,N); preserve N=0 as a separate stratum",
        },
        "heldout_selection": {
            "split": "test",
            "selection_seed": SELECTION_SEED,
            "screen": "the same read-only syntactic pairwise screen: source_query format/table valid, every predicate column/operator supported, and at least two distinct constrained attributes",
            "coverage": "a query is candidate-covered when both endpoint source columns of at least one frozen candidate occur among constrained attributes",
            "ranking": "SHA256(seed|query_id|source_query_sha256|candidate_id), lexicographic digest then query_id",
            "quota_per_candidate": QUOTA_PER_CANDIDATE,
            "target_distinct_queries": TARGET_QUERY_COUNT,
            "quota_winners_by_candidate": quota_winners,
            "selection_does_not_read": ["source_label.cardinality", "weight", "PostgreSQL estimates", "model losses", "latency"],
            "counts": {
                "all_test_records": len(test_records),
                "pairwise_screen_eligible_test_records": sum(1 for record, _ in test_records if is_pairwise_eligible(record)[0]),
                "candidate_covered_test_records": len(pairwise_records),
                "selected_test_records": len(selected_rows),
                "excluded_candidate_covered_records": len(pairwise_records) - len(selected_rows),
                "target_shortfall": max(0, TARGET_QUERY_COUNT - len(selected_rows)),
            },
            "selected_query_ids_sha256": digest_lines(selected_ids_ordered),
            "selected_record_hashes_sha256": digest_lines(
                f"{item['query_id']}:{item['canonical_record_sha256']}" for item in selected_rows
            ),
            "selected": selected_rows,
        },
        "postgresql_protocol": {
            "server_version": "16.14",
            "source_repository_commit": "23c7c2fdd4bfb561f3257d947fee956a2999fdb6",
            "numeric_trace_ancestor": "2891af8ade29a9b584d6c0fb969e311a10230282",
            "fixed_sample_sha256": "1fd69245a27283a431ff73704aa25096fc39dcea7f6be33be4d5d4eb1e5a4993",
            "table": "public.forest10_original",
            "table_load": "create the ten-column double-precision table first in the disposable database, then client-side COPY the hash-verified Forest10 CSV with its header and original row order",
            "cluster_bootstrap": "initdb with PostgreSQL 16.14, then set the disposable cluster next OID to 16384 before creating the first user table so the approved sample relation identity can be checked exactly",
            "statistics_target": 300,
            "statistics_creation_order": "candidate-id order e01,e12,e23,e34,e45,e56 for every selected set; Empty creates none",
            "analyze_strategy": "replay the same approved fixed sample before every ANALYZE; one fresh matched catalog snapshot per selected set and repetition",
            "repetitions": 2,
            "preclamp_trace_required": True,
            "plan_rows_are_secondary": True,
            "latency_collection": False,
            "maximum_query_measurements": 2 * len({tuple(item) for item in frozen_sets(evidence)["all_distinct_selected_sets"]}) * len(selected_rows),
            "raw_data_and_pgdata": "external ESS_ISSUE_ROOT only; never committed",
        },
        "metrics_frozen_before_collection": {
            "primary": ["mean absolute pre-clamp log-error", "median absolute pre-clamp log-error", "P90 absolute pre-clamp log-error", "maximum observed absolute pre-clamp log-error"],
            "paired": ["per-query delta versus Empty", "per-query delta versus Nominal selected set when defined", "paired common-query denominators"],
            "strata": ["N=0 with T=max(1,N)", "positive-truth signed estimate-minus-T direction", "top decile of true N within selected cohort, ties by query_id"],
            "diagnostics": ["statistics/catalog existence", "MCV payload presence and item count", "trace-selected statistic identities", "trace completeness", "repetition instability", "model-vs-real discrepancy", "no-statistics and proxy-budget mapping"],
            "invalid_handling": "nonpositive pre-clamp estimate, missing final trace, stale/mismatched snapshot, or hash mismatch is INVALID and blocks a GO claim; no silent clamping or replacement",
            "ties": "retain every Issue #23 optimal set; never choose among tied sets using held-out outcomes",
            "generalization_limit": "20-100 rows are a bounded cohort and do not establish population-level generalization",
        },
        "decision_and_gate": {
            "gate_a": "PASS only after all hashes, build provenance, fixed sample replay, and trace completeness are verified; otherwise BLOCKED",
            "recommendations": ["GO", "NO-GO", "INCONCLUSIVE"],
            "go_definition": "reproducible nontrivial paired decision-quality difference on the frozen cohort with valid PG measurement fidelity; benefit or meaningful harmful overconservatism is admissible",
            "no_go_definition": "documented falsification or unsupported practical advantage of the tested decision hypothesis",
            "inconclusive_definition": "missing input/tracing, small or unrepresentative eligible slice, incomparable snapshots, or unresolved statistic composition",
            "no_universal_pess_claim": True,
            "no_latency_or_physical_maintenance_claim": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output), "selected": len(selected_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
