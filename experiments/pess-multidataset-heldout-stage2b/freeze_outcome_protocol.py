"""Freeze the Stage 2B outcome protocol from workload-only inputs.

This command deliberately reads only archive-first ``workload.json`` files.
It does not open ``truth.json`` and cannot use test cardinalities, estimates,
MCV payloads, or PostgreSQL measurements for eligibility or cohort selection.
The generated protocol is the required pre-outcome boundary for the formal
Stage 2B runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ess_research.arecel import prepare

HERE = Path(__file__).resolve().parent
DATASETS = ("forest10", "census13")
SPLITS = ("train", "valid", "test")
ALLOWED_OPERATORS = ("=", "<", "<=", ">", ">=", "[]")
SELECTION_SEED = "ess-issue48-stage2b-formal-v1"
STAGE1A_PROTOCOL = HERE.parent / "forest10-heldout-decision-stage1a" / "protocol.json"
V3_PROTOCOL = HERE / "protocol-v3.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=HERE.parents[2], text=True).strip()


def workload_fingerprint(query: dict[str, Any], *, include_values: bool) -> str:
    fields = []
    for predicate in query["predicates"]:
        value = predicate["value"] if include_values else (
            "range" if predicate["operator"] == "[]" else "scalar"
        )
        fields.append((predicate["column"], predicate["operator"], value))
    return json.dumps(sorted(fields), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def query_digest(query: dict[str, Any], *, include_values: bool) -> str:
    return sha256_bytes(workload_fingerprint(query, include_values=include_values).encode())


def strict_eligible(query: dict[str, Any], spec: dict[str, Any]) -> tuple[bool, list[str]]:
    predicates = query.get("predicates")
    if not isinstance(predicates, list) or len(predicates) != 2:
        return False, []
    columns = [item.get("column") for item in predicates]
    if len(set(columns)) != 2 or any(item.get("operator") not in ALLOWED_OPERATORS for item in predicates):
        return False, []
    constrained = set(columns)
    covered = [
        candidate["id"]
        for candidate in spec["candidates"]
        if set(candidate["source_columns"]) == constrained
    ]
    return bool(covered), covered


def calibration_eligible(query: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    predicates = query.get("predicates")
    if not isinstance(predicates, list) or not predicates:
        return []
    if any(item.get("operator") not in ALLOWED_OPERATORS for item in predicates):
        return []
    constrained = {item.get("column") for item in predicates}
    return [
        candidate["id"]
        for candidate in spec["candidates"]
        if set(candidate["source_columns"]) <= constrained
    ]


def load_split(data_root: Path, dataset: str, split: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    with prepare(issue=48, dataset=dataset) as prepared:
        source = prepared.dataset_root / split / "workload.json"
        payload = source.read_bytes()
        workload = json.loads(payload)
        return workload["queries"], {
            "sha256": sha256_bytes(payload),
            "bytes": str(len(payload)),
            "format": workload.get("format", ""),
        }


def stage1a_ids() -> set[str]:
    protocol = json.loads(STAGE1A_PROTOCOL.read_text(encoding="utf-8"))
    return {item["query_id"] for item in protocol["heldout_selection"]["selected"]}


def select_validation_calibration(
    split_queries: list[dict[str, Any]], spec: dict[str, Any]
) -> list[dict[str, Any]]:
    """Choose one distinct source-order valid query per candidate, shape-only."""

    chosen: list[dict[str, Any]] = []
    used: set[str] = set()
    for candidate in spec["candidates"]:
        for query in split_queries:
            if query["query_id"] in used:
                continue
            if candidate["id"] in calibration_eligible(query, spec):
                chosen.append(
                    {
                        "query_id": query["query_id"],
                        "source_index": query["source_index"],
                        "source_sql_sha256": sha256_bytes(query["source_sql"].encode()),
                        "covered_candidates": calibration_eligible(query, spec),
                        "candidate_id": candidate["id"],
                        "selection_reason": "first_unused_valid_query_in_source_order_with_candidate_endpoint_coverage",
                    }
                )
                used.add(query["query_id"])
                break
    return chosen


def select_test_cohort(
    dataset: str,
    split_queries: list[dict[str, Any]],
    spec: dict[str, Any],
    legacy_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for query in split_queries:
        is_eligible, covered = strict_eligible(query, spec)
        if not is_eligible:
            continue
        eligible.append(
            {
                "query_id": query["query_id"],
                "source_index": query["source_index"],
                "source_sql_sha256": sha256_bytes(query["source_sql"].encode()),
                "candidate_id": covered[0],
                "template_fingerprint_sha256": query_digest(query, include_values=False),
                "exact_fingerprint_sha256": query_digest(query, include_values=True),
                "legacy_stage1a_excluded": query["query_id"] in legacy_ids,
            }
        )
    eligible = [item for item in eligible if not item["legacy_stage1a_excluded"]]
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in eligible:
        by_candidate[item["candidate_id"]].append(item)

    if dataset == "forest10":
        selected = []
        quota = 10
        for candidate in spec["candidates"]:
            candidates = sorted(
                by_candidate[candidate["id"]],
                key=lambda item: sha256_bytes(
                    f"{SELECTION_SEED}|{item['query_id']}|{item['source_sql_sha256']}|{candidate['id']}".encode()
                ) + item["query_id"],
            )
            selected.extend(candidates[:quota])
        selection_rule = "10 per candidate; digest rank then query ID"
    else:
        selected = sorted(eligible, key=lambda item: item["source_index"])
        selection_rule = "all eligible records because the eligible count is within the 30-100 target"

    selected.sort(key=lambda item: item["source_index"])
    if not 30 <= len(selected) <= 100:
        raise ValueError(f"{dataset}: selected cohort size {len(selected)} is outside [30,100]")
    counts = {candidate["id"]: len(by_candidate[candidate["id"]]) for candidate in spec["candidates"]}
    selected_counts = Counter(item["candidate_id"] for item in selected)
    return selected, {
        "screen": "exactly two predicates, two distinct source columns, allowed operator, and exact endpoint match to one predeclared pairwise candidate",
        "allowed_operators": list(ALLOWED_OPERATORS),
        "legacy_stage1a_ids_excluded_before_selection": len(legacy_ids),
        "eligible_counts_by_candidate_after_legacy_exclusion": counts,
        "selected_counts_by_candidate": dict(selected_counts),
        "selection_seed": SELECTION_SEED,
        "selection_rule": selection_rule,
        "selected_count": len(selected),
    }


def group_overlap(
    by_split: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> dict[str, Any]:
    template_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    exact_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    strict_records = 0
    strict_by_split: Counter[str] = Counter()
    strict_template_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    strict_exact_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for split, queries in by_split.items():
        for query in queries:
            template = query_digest(query, include_values=False)
            exact = query_digest(query, include_values=True)
            template_groups[template].append((split, query["query_id"]))
            exact_groups[exact].append((split, query["query_id"]))
            eligible, _ = strict_eligible(query, spec)
            if eligible:
                strict_records += 1
                strict_by_split[split] += 1
                strict_template_groups[template].append((split, query["query_id"]))
                strict_exact_groups[exact].append((split, query["query_id"]))

    def overlap(groups: dict[str, list[tuple[str, str]]]) -> dict[str, Any]:
        shared = {key: values for key, values in groups.items() if len({split for split, _ in values}) > 1}
        pair_counts = Counter(
            "+".join(sorted({split for split, _ in values}))
            for values in shared.values()
        )
        return {
            "group_count": len(groups),
            "shared_group_count": len(shared),
            "shared_record_count": sum(len(values) for values in shared.values()),
            "shared_groups_by_split_pair": dict(sorted(pair_counts.items())),
        }

    ledger = []
    for split, queries in by_split.items():
        for query in queries:
            eligible, covered = strict_eligible(query, spec)
            ledger.append(
                "|".join(
                    [
                        split,
                        query["query_id"],
                        sha256_bytes(query["source_sql"].encode()),
                        query_digest(query, include_values=False),
                        query_digest(query, include_values=True),
                        str(eligible),
                        ",".join(covered),
                    ]
                )
            )
    return {
        "all_queries": {
            "template": overlap(template_groups),
            "exact": overlap(exact_groups),
        },
        "strict_pairwise_queries": {
            "records": strict_records,
            "records_by_split": dict(strict_by_split),
            "template": overlap(strict_template_groups),
            "exact": overlap(strict_exact_groups),
        },
        "interpretation": "shared normalized template groups are flagged as leakage; selected query IDs remain descriptive and are not treated as group-independent population samples",
        "ledger_sha256": sha256_bytes("\n".join(sorted(ledger)).encode()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v3 = json.loads(V3_PROTOCOL.read_text(encoding="utf-8"))
    legacy = stage1a_ids()
    datasets: dict[str, Any] = {}
    for dataset in DATASETS:
        spec = v3["datasets"][dataset]
        split_queries: dict[str, list[dict[str, Any]]] = {}
        split_hashes: dict[str, dict[str, str]] = {}
        for split in SPLITS:
            split_queries[split], split_hashes[split] = load_split(Path("."), dataset, split)
        selected, selection = select_test_cohort(dataset, split_queries["test"], spec, legacy)
        calibration = select_validation_calibration(split_queries["valid"], spec)
        if len(calibration) != len(spec["candidates"]):
            raise ValueError(f"{dataset}: missing validation calibration task")
        datasets[dataset] = {
            "benchmark_id": spec["benchmark_id"],
            "relation": spec["relation"],
            "source_relation": spec["source_relation"],
            "source_columns": spec["source_columns"],
            "catalog_columns": spec["catalog_columns"],
            "source_rows": spec["source_rows"],
            "split_counts": {split: len(split_queries[split]) for split in SPLITS},
            "workload_sha256": {split: split_hashes[split]["sha256"] for split in SPLITS},
            "candidates": spec["candidates"],
            "cross_split_fingerprint_audit": group_overlap(split_queries, spec),
            "validation_calibration": {
                "split": "valid",
                "truth_allowed_after_freeze": True,
                "selection_does_not_read": ["valid truth values", "PG estimates", "MCV payloads", "latency"],
                "records": calibration,
            },
            "test_cohort": {
                **selection,
                "split": "test",
                "stage1a_legacy_ids_excluded": True,
                "records": selected,
            },
        }

    protocol = {
        "format": "ess-issue48-stage2b-formal-outcome-protocol-v4",
        "issue": 48,
        "status": "FROZEN_BEFORE_HELDOUT_OUTCOME_COLLECTION_V4",
        "evidence_label": "outcome_free_input_protocol",
        "supersedes": "protocol-v3.json only for the formal outcome runner; protocol-v3 and all Gate A evidence remain immutable",
        "source_contract": {
            "archive_sha256": v3["etl_contract"]["archive_sha256"],
            "upstream_commit": v3["etl_contract"]["upstream_commit"],
            "etl_source_tree_objects": {
                "arecel": git_value("rev-parse", "HEAD:src/ess_research/arecel"),
                "task_paths": git_value("rev-parse", "HEAD:src/ess_research/task_paths.py"),
            },
            "prepare_api": "from ess_research.arecel import prepare",
            "required_environment": ["ESS_DATA_ROOT", "ESS_RUNTIME_PARENT", "ESS_WORKTREE_PARENT"],
            "raw_archive_only_shared_cache": True,
            "derived_inputs_run_scoped": True,
        },
        "independence_contract": {
            "test_truth_values_read_before_this_freeze": False,
            "test_truth_values_allowed_for_selection": False,
            "test_estimates_allowed_for_selection": False,
            "test_mcv_payload_allowed_for_selection": False,
            "test_latency_allowed_for_selection": False,
            "stage1a_forest10_ids_excluded": True,
            "cross_split_template_overlap_is_flagged": True,
            "query_ids_are_not_claimed_group_independent": True,
        },
        "datasets": datasets,
        "model_selection": {
            "validation_only": True,
            "calibration_order": "calibrate all candidates and Empty on the frozen validation records before opening the test workload",
            "positive_preclamp_required": True,
            "target": "T=max(1,N); preserve N=0",
            "coefficient_definition": "alpha=ln(n0/T), b_e=ln(n_e/n0) from validation-only positive pre-clamp estimates; model arithmetic is exact only after explicitly recorded rationalization",
            "methods": {
                "Empty": "M=empty",
                "Nominal": "minimize validation task-wise loss under the fixed candidate creation order greedy maximal-matching policy",
                "PESS": "minimize sum of validation task-wise maxima over all maximal matchings permitted by the frozen candidate graph",
            },
            "tie_policy": "retain every optimal set; selected execution set is lexicographically smallest only as a deterministic representative, and duplicate selected sets across budgets remain separate aliases",
            "solver_boundary": "Fraction reference certificates are exact for recorded rationalized inputs; floating-point solver optimality is not upgraded to exact certification",
        },
        "measurement_contract": {
            "methods": ["Empty", "Nominal", "PESS"],
            "budgets_proxy_units": [0, 2, 3, 5],
            "candidate_costs": "1 proxy unit per predeclared pairwise MCV object",
            "maximum_statistics_objects": 6,
            "statistics_target": 300,
            "repetitions": 2,
            "sample": "one Issue-48-owned fixed sample per dataset, exported after import and replayed before every statistics ANALYZE; hash and relation identity recorded before held-out measurements",
            "creation_order": "protocol candidate order, unchanged for every set",
            "query_order": "dataset order forest10 then census13; within each dataset calibration first, then budget ascending and method order Empty/Nominal/PESS, then frozen test source_index order",
            "preclamp_metric": "|ln(estimate/max(1,N))| only when measured positive pre-clamp estimate is positive",
            "secondary_metrics": ["median", "P90 nearest-rank ceiling", "max", "signed estimate-minus-T direction", "zero-truth stratum", "query-level paired harms/ties/benefits", "tail diagnostics only if predeclared from validation-free test truth after measurement", "repetition spread", "requested/payload-present/trace-selected ledgers", "model-vs-PG residuals where available"],
            "paired_comparisons": ["PESS vs Empty", "Nominal vs Empty", "PESS vs Nominal when both are defined"],
            "invalid_policy": "missing/ambiguous trace, nonpositive pre-clamp estimate, unmapped selected OID, missing catalog ledger, sample identity mismatch, or hash mismatch makes the affected run INVALID and blocks a GO claim; never silently drop a query",
            "latency": "not collected; no latency or physical maintenance-cost claim",
        },
        "resource_budget": {
            "maximum_wall_minutes_per_dataset": 90,
            "maximum_query_measurements_per_dataset": 1800,
            "maximum_statistics_setup_events_per_dataset": 40,
            "maximum_external_raw_trace_bytes_per_dataset": 2_000_000_000,
            "maximum_runtime_disk_bytes_per_dataset": 10_000_000_000,
            "memory_budget_bytes": 8_000_000_000,
            "fail_closed_on_exceedance": True,
        },
        "decision": {
            "GO": "at least two datasets have valid matched Empty/Nominal/PESS held-out measurements and reproducible nontrivial descriptive decision differences or effective-MCV mechanisms, without universal dominance claims",
            "NO-GO": "the tested physical contrast is falsified or no nontrivial contrast is observed under the supported workloads, with valid measurement fidelity",
            "INCONCLUSIVE": "required data, cohort size, group independence, source trace, sample identity, or measurement validity is insufficient; also applies to any fail-closed run",
            "scientific_boundary": ["descriptive real-PG behavior only", "no universal PESS-vs-Nominal ranking", "no PostgreSQL scheme-containment guarantee", "no population-level significance claim", "proxy budget is not generic or physical maintenance"],
        },
        "provenance": {
            "v3_protocol_sha256": sha256_file(V3_PROTOCOL),
            "stage1a_protocol_sha256": sha256_file(STAGE1A_PROTOCOL),
            "stage1a_unique_selected_ids": len(legacy),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output), "datasets": {d: len(protocol["datasets"][d]["test_cohort"]["records"]) for d in DATASETS}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
