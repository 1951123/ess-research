"""Execute the authorized frozen Issue #107 sampled PostgreSQL Test."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/arecel-test-generalization-issue101"))
sys.path.insert(0, str(ROOT / "experiments/oid-order-stress-test-issue105"))

import run_issue101 as issue101
import run_issue105 as issue105
from ess_research.arecel.oid_sampling import (
    IncompletePermutationSample,
    PermutationValue,
    build_issue107_schedule,
    canonical_json_bytes,
    confidence_interval_95,
    difference_estimate,
    estimate_population_variance,
    estimate_stratified_mean,
    schedule_arm_index,
    validate_scheduled_arm,
)
from ess_research.task_paths import runtime_runs

SAMPLE_PATH = HERE / "permutation-sample-v1.json"
FROZEN_RESOURCES = ROOT / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
ISSUE107_ROOT_SEED = 17_770_611_677_888_985_956
ISSUE107_SAMPLE_SHA256 = "0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73"
ISSUE107_APPROVED_HEAD = "7f618759844f820062965afe373e7a3da8ebcc21"
ISSUE107_AUTH_COMMENT = 6409021549
ISSUE105_RUN_ID = "20261025T130222Z-issue105-official-v2"
ISSUE105_SOURCE_COMMIT = "5fb8053e1d9717a543a45a2bf19d4adc2c6bdb65"
ISSUE105_RAW_SHA256 = "ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2"
ISSUE101_PROTOCOL_SHA256 = "7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787"
ISSUE101_RUNNER_SHA256 = "894b8276f58d36d7d513138e574a9832aa03b8e8a21f3dd84494dbc0367b9244"
POSTGRESQL_COMMIT = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
ISSUE99_HELPER_COMMIT = "76106024611ae91505f1f05bdc35aed44d9c38c4"
PARALLEL_CLIENTS = 6
EARLY_STOP_SECONDS = 2 * 60 * 60
HARD_STOP_SECONDS = 3 * 60 * 60
EARLY_STOP_BYTES = 4 * 1024**3
HARD_STOP_BYTES = 5 * 1024**3
MAX_NEW_EXPLAINS = 1_560_000
METRICS = ("mean", "p50", "p95", "p99")
VALID_DIAGNOSTIC_STATUSES = {"complete", "empty"}


class StopBeforeNextArm(RuntimeError):
    """The approved early-stop line was reached at an arm boundary."""


def _refresh_reuse_plan(manifest: dict[str, Any], reuse_audit: dict[str, Any]) -> None:
    reused = len(reuse_audit["eligible_arms"])
    reuse_audit["eligible_reuse_count"] = reused
    manifest["eligible_reuse_count_after_row_and_input_validation"] = reused
    manifest["planned_new_configurations_after_reuse_validation"] = 156 - reused
    manifest["planned_explain_calls_after_reuse_validation"] = (156 - reused) * 10_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False).encode("utf-8") + b"\n"
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def checked_frozen_schedule() -> tuple[dict[str, Any], dict[tuple[str, str, tuple[str, ...]], dict[str, Any]]]:
    if sha256_file(SAMPLE_PATH) != ISSUE107_SAMPLE_SHA256:
        raise RuntimeError("frozen Issue #107 permutation sample SHA-256 mismatch")
    schedule = build_issue107_schedule(FROZEN_RESOURCES)
    if schedule["root_seed"] != ISSUE107_ROOT_SEED:
        raise RuntimeError("frozen Issue #107 root seed changed")
    if SAMPLE_PATH.read_bytes() != canonical_json_bytes(schedule):
        raise RuntimeError("checked-in permutation schedule differs from regenerated frozen sample")
    index = schedule_arm_index(schedule)
    counts = {kind: sum(row["selection"] == kind
                        for stratum in schedule["schedules"]
                        for row in stratum["permutations"])
              for kind in ("fixed", "srswor", "enumerated")}
    if counts != {"fixed": 8, "srswor": 136, "enumerated": 12} or len(index) != 156:
        raise RuntimeError(f"frozen arm counts/strata mismatch: {counts}")
    return schedule, index


def _fixed_orders(schedule: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    fixed: dict[tuple[str, str], dict[str, Any]] = {}
    for stratum in schedule["schedules"]:
        for arm in stratum["permutations"]:
            if arm["selection"] == "fixed":
                key = (stratum["dataset"], tuple(arm["permutation"]))
                fixed[key] = {
                    "dataset": stratum["dataset"],
                    "policy": stratum["policy"],
                    "case_id": stratum["case_id"],
                    "resource_ids": list(stratum["resource_ids"]),
                    "candidate_map_sha256": stratum["candidate_map_sha256"],
                    "sample_sha256": stratum["sample_sha256"],
                    **arm,
                }
    if len(fixed) != 8:
        raise RuntimeError("sample must contain exactly eight fixed #105 arms")
    return fixed


def _member_bytes(raw_path: Path, offset: int, size: int) -> bytes:
    with raw_path.open("rb") as stream:
        stream.seek(offset)
        value = stream.read(size)
    if len(value) != size:
        raise ValueError("#105 raw member is truncated")
    return value


def audit_issue105_reuse(schedule: dict[str, Any], protocol101: dict[str, Any]) -> dict[str, Any]:
    """Check provenance and hashes without decompressing or parsing Q-error rows."""
    source_root = runtime_runs("ess-research", 105) / ISSUE105_RUN_ID
    manifest_path = source_root / "run-manifest.json"
    raw_path = source_root / "raw-observations.jsonl.gz"
    fixed = _fixed_orders(schedule)
    outcome: dict[str, Any] = {
        "source_run_id": ISSUE105_RUN_ID,
        "source_manifest": str(manifest_path),
        "source_archive": str(raw_path),
        "archive_sha256_expected": ISSUE105_RAW_SHA256,
        "eligible_arms": {},
        "arms": {},
        "global_integrity_status": "FAIL",
    }
    if not manifest_path.is_file() or not raw_path.is_file():
        for key, frozen in fixed.items():
            outcome["arms"][frozen["dataset"] + "/" + ",".join(key[1])] = {
                "eligible": False, "reason": "source manifest or archive is missing"}
        return outcome

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_digest = sha256_file(raw_path)
    global_checks = {
        "manifest_status": manifest.get("status") == "COMPLETE",
        "run_id": manifest.get("run_id") == ISSUE105_RUN_ID,
        "source_commit": manifest.get("source_commit") == ISSUE105_SOURCE_COMMIT,
        "postgresql_source_commit": manifest.get("postgresql_source_commit") == POSTGRESQL_COMMIT,
        "issue101_protocol_sha256": manifest.get("issue101_protocol_sha256") == ISSUE101_PROTOCOL_SHA256,
        "issue101_runner_sha256": manifest.get("issue101_runner_sha256") == ISSUE101_RUNNER_SHA256,
        "issue99_helper_commit": manifest.get("issue99_helper_commit") == ISSUE99_HELPER_COMMIT,
        "train_resources_sha256": manifest.get("train_resources_sha256") == protocol101["source_pins"]["train_resources_sha256"],
        "planned_calls": manifest.get("planned_explain_calls") == 80_000,
        "attempted_calls": manifest.get("attempted_explain_calls") == 80_000,
        "archive_manifest_sha256": manifest.get("raw_observations_sha256") == ISSUE105_RAW_SHA256,
        "archive_sha256": archive_digest == ISSUE105_RAW_SHA256,
        "archive_size": manifest.get("raw_observations_bytes") == raw_path.stat().st_size,
        "postgresql_build": (manifest.get("postgresql_build", {}).get("source_commit") == POSTGRESQL_COMMIT
                             and manifest.get("postgresql_build", {}).get("version") == "PostgreSQL 16.14"),
    }
    offsets = []
    member_checks: dict[str, bool] = {}
    pair_checks: dict[str, bool] = {}
    for dataset in issue101.DATASETS:
        result = manifest.get("datasets", {}).get(dataset, {})
        arms = result.get("configurations", [])
        if len(arms) != 2:
            member_checks[f"{dataset}/configuration_count"] = False
            continue
        by_order = {row.get("order"): row for row in arms}
        canonical = by_order.get("canonical", {})
        reverse = by_order.get("reverse", {})
        pair_checks[f"{dataset}/ordinary_stats_match"] = (
            bool(canonical.get("ordinary_column_stats", {}).get("sha256"))
            and canonical.get("ordinary_column_stats", {}).get("sha256")
            == reverse.get("ordinary_column_stats", {}).get("sha256")
        )
        pair_checks[f"{dataset}/mcv_hashes_match"] = (
            bool(canonical.get("mcv_content_sha256_by_candidate"))
            and canonical.get("mcv_content_sha256_by_candidate")
            == reverse.get("mcv_content_sha256_by_candidate")
        )
        pair_checks[f"{dataset}/table_identity_match"] = (
            bool(canonical.get("table_identity"))
            and canonical.get("table_identity") == reverse.get("table_identity")
            and canonical.get("table_identity") == result.get("postgresql_table", {}).get("identity")
        )
        for arm in arms:
            label = f"{dataset}/{arm.get('order')}"
            offset, size = arm.get("raw_member_offset"), arm.get("raw_member_bytes")
            if not isinstance(offset, int) or not isinstance(size, int) or offset < 0 or size <= 0:
                member_checks[f"{label}/member_extent"] = False
                continue
            offsets.append((offset, offset + size, label))
            try:
                member = _member_bytes(raw_path, offset, size)
                member_checks[f"{label}/member_sha256"] = hashlib.sha256(member).hexdigest() == arm.get("raw_member_sha256")
            except OSError:
                member_checks[f"{label}/member_sha256"] = False
    offsets.sort()
    contiguous = bool(offsets) and offsets[0][0] == 0
    for left, right in zip(offsets, offsets[1:]):
        contiguous = contiguous and left[1] == right[0]
    contiguous = contiguous and offsets[-1][1] == raw_path.stat().st_size if offsets else False
    global_checks["all_member_offsets_contiguous"] = contiguous
    global_checks["all_member_hashes"] = len(member_checks) == 8 and all(member_checks.values())
    global_checks.update(pair_checks)
    global_ok = all(global_checks.values())
    outcome["global_checks"] = global_checks
    outcome["member_checks"] = member_checks
    outcome["archive_sha256_observed"] = archive_digest

    # Validate each fixed-order identity separately. Any failed arm is rerun at
    # that same scheduled order; a bad global archive invalidates all reuse.
    for (dataset, permutation), frozen in fixed.items():
        arm_key = f"{dataset}/{','.join(permutation)}"
        failures: list[str] = []
        if not global_ok:
            failures.append("global #105 archive/provenance integrity check failed")
        dataset_result = manifest.get("datasets", {}).get(dataset, {})
        order_name = "canonical" if permutation == tuple(frozen["resource_ids"]) else "reverse"
        candidates = issue101.candidate_map(dataset)
        selected = list(permutation)
        arm = next((row for row in dataset_result.get("configurations", [])
                    if row.get("order") == order_name), None)
        checks = {
            "dataset_complete": dataset_result.get("status") == "COMPLETE",
            "arm_present": arm is not None,
        }
        if arm is not None:
            sample_spec = protocol101["datasets"][dataset]["sample"]
            expected_names = [candidates[value]["statistic_name"] for value in selected]
            catalog_rows = arm.get("catalog", [])
            actual_names = [row.get("statistic_name") for row in catalog_rows]
            candidate_by_name = {
                candidate["statistic_name"]: candidate
                for candidate in candidates.values()
            }
            sample_header = arm.get("sample_header", {})
            expected_header = dataset_result.get("sample_identity", {}).get("header", {})
            table = dataset_result.get("postgresql_table", {}).get("identity", {})
            checks.update({
                "configuration_id": arm.get("configuration_id") == f"{dataset}-{order_name}",
                "selected_ids": arm.get("selected_ids") == selected,
                "create_order": arm.get("create_statement_candidate_ids") == selected,
                "catalog_oid_order": arm.get("catalog_oid_order_candidate_ids") == selected,
                "candidate_map_sha256": arm.get("candidate_map_sha256") == frozen["candidate_map_sha256"],
                "sample_sha256": arm.get("sample_sha256") == sample_spec["sha256"],
                "sample_replay": arm.get("sample_replay_status") == "PASS",
                "sample_header": (
                    sample_header.get("server_version") == "16.14"
                    and sample_header.get("sample_target") == 90_000
                    and sample_header.get("tuple_count") == expected_header.get("tuple_count")
                    and sample_header.get("natts") == expected_header.get("natts")
                    and sample_header.get("relation_identity") == expected_header.get("relation_identity")
                    and int(sample_header.get("relation_oid", -1)) == int(table.get("relation_oid", -2))
                ),
                "catalog_definition": arm.get("catalog_definition_status") == "PASS",
                "row_count": (arm.get("metrics", {}).get("query_count") == 10_000
                              and arm.get("metrics", {}).get("valid_count") == 10_000
                              and arm.get("metrics", {}).get("status") == "COMPLETE"),
                "diagnostics": (sum(arm.get("metrics", {}).get("diagnostics_status_counts", {}).get(s, 0)
                                     for s in VALID_DIAGNOSTIC_STATUSES) == 10_000),
                "plan_batch": (arm.get("plan_batch", {}).get("valid_plan_rows") == 10_000
                               and arm.get("plan_batch", {}).get("unresolved_or_unstarted") == 0),
                "table_identity": arm.get("table_identity") == dataset_result.get("postgresql_table", {}).get("identity"),
                "ordinary_stats": bool(arm.get("ordinary_column_stats", {}).get("sha256")),
                "mcv_hashes": (set(arm.get("mcv_content_sha256_by_candidate", {})) == set(selected)
                               and all(arm.get("mcv_content_sha256_by_candidate", {}).values())),
                "ordinary_stats_complete": arm.get("ordinary_column_stats", {}).get("column_count") == len(issue101.issue99.dataset_spec(dataset)[1]),
                "catalog_name_order": actual_names == expected_names,
                "catalog_exact": (
                    len(catalog_rows) == 5
                    and all(
                        row.get("kinds") == ["m"]
                        and row.get("statistics_target") == 300
                        and row.get("mcv_payload_present")
                        and int(row.get("mcv_item_count", 0)) > 0
                        and row.get("stxkind") == "{m}"
                        and bool(row.get("mcv_content_sha256"))
                        and candidate_by_name.get(row.get("statistic_name"), {}).get("catalog_columns") == row.get("attnames")
                        and arm.get("mcv_content_sha256_by_candidate", {}).get(
                            next((candidate_id for candidate_id, candidate in candidates.items()
                                  if candidate["statistic_name"] == row.get("statistic_name")), "")
                        ) == row.get("mcv_content_sha256")
                        for row in catalog_rows
                    )
                ),
                "member_hash": member_checks.get(f"{dataset}/{order_name}/member_sha256", False),
            })
        failures.extend(name for name, passed in checks.items() if not passed)
        outcome["arms"][arm_key] = {
            "eligible": not failures,
            "issue105_order": order_name,
            "checks": checks,
            "reasons": failures,
        }
        if not failures:
            outcome["eligible_arms"][arm_key] = {
                "dataset": dataset,
                "permutation": list(permutation),
                "selection": "fixed",
                "configuration_id": arm["configuration_id"],
                "raw_member_offset": arm["raw_member_offset"],
                "raw_member_bytes": arm["raw_member_bytes"],
                "raw_member_sha256": arm["raw_member_sha256"],
                "ordinary_stats_sha256": arm["ordinary_column_stats"]["sha256"],
                "mcv_content_sha256_by_candidate": arm["mcv_content_sha256_by_candidate"],
                "source_dataset_status": dataset_result["status"],
            }
    outcome["global_integrity_status"] = "PASS" if global_ok else "FAIL"
    outcome["eligible_reuse_count"] = len(outcome["eligible_arms"])
    outcome["raw_archive_bytes_were_decompressed_during_audit"] = False
    outcome["query_level_qerror_was_read_during_audit"] = False
    return outcome


def _reused_rows(
    raw_path: Path,
    old_arm: dict[str, Any],
    *,
    dataset: str,
    old_order: str,
    permutation: list[str],
    queries: list[dict[str, Any]],
    truths: list[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    member = _member_bytes(raw_path, old_arm["raw_member_offset"], old_arm["raw_member_bytes"])
    if hashlib.sha256(member).hexdigest() != old_arm["raw_member_sha256"]:
        raise ValueError("#105 fixed arm member changed after the preflight hash audit")
    decoded = gzip.decompress(member)
    rows = [json.loads(line) for line in decoded.splitlines() if line]
    if len(rows) != 10_000 or len(queries) != 10_000 or len(truths) != 10_000:
        raise ValueError("reused #105 arm must contain exactly 10,000 observations")
    for index, (row, query, truth) in enumerate(zip(rows, queries, truths, strict=True)):
        if (row.get("dataset") != dataset
                or row.get("order") != old_order
                or row.get("configuration_id") != f"{dataset}-{old_order}"
                or row.get("selected_ids") != permutation
                or row.get("query_id") != query["query_id"]
                or row.get("source_index") != index
                or row.get("true_cardinality") != truth
                or row.get("status") != "VALID"
                or row.get("diagnostics_status") not in VALID_DIAGNOSTIC_STATUSES
                or isinstance(row.get("estimate_plan_rows"), bool)
                or not isinstance(row.get("estimate_plan_rows"), int)
                or row["estimate_plan_rows"] < 0):
            raise ValueError(f"reused #105 observation failed row identity/status at index {index}")
        qerror, rounded = issue101.qerror_for_plan_rows(row["estimate_plan_rows"], truth)
        if row.get("estimate_rounded_r1") != rounded or row.get("qerror") != qerror:
            raise ValueError(f"reused #105 Q-error does not reproduce the pinned definition at row {index}")
    metrics = issue105.metrics_for_rows(rows)
    if metrics["status"] != "COMPLETE" or metrics["valid_count"] != 10_000:
        raise ValueError("reused #105 arm does not have a complete valid Test outcome")
    return rows, metrics


def _test_input_matches_prior(dataset: str, identity: dict[str, Any], prior: dict[str, Any]) -> bool:
    keys = (
        "dataset", "split", "query_count", "truth_count", "workload_pickle_sha256",
        "labels_pickle_sha256", "test_truth_canonical_sha256", "csv_sha256", "csv_rows",
        "schema_columns", "catalog_columns",
    )
    return all(identity.get(key) == prior.get(key) for key in keys)


def _new_arm_record_base(dataset: str, stratum: dict[str, Any], arm: dict[str, Any], arm_id: str) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "policy": stratum["policy"],
        "case_id": stratum["case_id"],
        "configuration_id": arm_id,
        "resource_ids": list(stratum["resource_ids"]),
        "permutation": list(arm["permutation"]),
        "selection": arm["selection"],
        "draw_index": arm.get("draw_index"),
        "inclusion_probability": arm["inclusion_probability"],
        "sample_sha256": stratum["sample_sha256"],
        "candidate_map_sha256": stratum["candidate_map_sha256"],
    }


def _record_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = issue105.metrics_for_rows(rows)
    diagnostics_valid = sum(row.get("diagnostics_status") in VALID_DIAGNOSTIC_STATUSES for row in rows)
    metrics["diagnostics_valid_count"] = diagnostics_valid
    metrics["statistical_status"] = (
        "COMPLETE" if metrics["valid_count"] == 10_000 and diagnostics_valid == 10_000
        else "INCOMPLETE"
    )
    metrics["diagnostics_status_counts"] = {
        key: sum(row.get("diagnostics_status") == key for row in rows)
        for key in sorted({row.get("diagnostics_status", "NOT_AVAILABLE") for row in rows})
    }
    return metrics


def _arm_value(arm: dict[str, Any], metric: str) -> PermutationValue:
    metrics = arm.get("metrics", {})
    qerror = metrics.get("qerror") or {}
    return PermutationValue(
        permutation=tuple(arm["permutation"]),
        value=qerror.get(metric),
        plan_status=metrics.get("statistical_status", "INCOMPLETE"),
        diagnostics_status=("complete" if metrics.get("statistical_status") == "COMPLETE"
                            else "incomplete"),
    )


def _estimate_set(stratum: dict[str, Any], arms: list[dict[str, Any]]) -> dict[str, Any]:
    selection_lookup = {tuple(row["permutation"]): row for row in stratum["permutations"]}
    orders = [tuple(row["permutation"]) for row in arms]
    if len(set(orders)) != len(orders):
        return {
            "status": "INCOMPLETE",
            "expected_arm_count": len(selection_lookup),
            "observed_arm_count": len(orders),
            "failure": "duplicate permutation arm",
        }
    by_order = {tuple(row["permutation"]): row for row in arms}
    expected_orders = set(selection_lookup)
    present_orders = set(by_order)
    if present_orders != expected_orders:
        return {
            "status": "INCOMPLETE",
            "expected_arm_count": len(expected_orders),
            "observed_arm_count": len(present_orders),
            "missing_permutations": [list(order) for order in sorted(expected_orders - present_orders)],
            "unexpected_permutations": [list(order) for order in sorted(present_orders - expected_orders)],
        }
    for order, observed in by_order.items():
        frozen = selection_lookup[order]
        if (any(observed.get(key) != frozen.get(key) for key in (
                "selection", "draw_index", "inclusion_probability"
            )) or observed.get("sample_sha256") != stratum["sample_sha256"]):
            return {
                "status": "INCOMPLETE",
                "expected_arm_count": len(selection_lookup),
                "observed_arm_count": len(by_order),
                "failure": f"selection-stratum identity mismatch for {order}",
            }
    fixed_orders = [order for order, record in selection_lookup.items() if record["selection"] == "fixed"]
    residual_orders = [order for order, record in selection_lookup.items() if record["selection"] != "fixed"]
    fixed_count = stratum["fixed_count"]
    sample_size = len(residual_orders)
    residual_population = stratum["residual_population_size"]
    result: dict[str, Any] = {
        "status": "COMPLETE",
        "population_size": stratum["permutation_population_size"],
        "fixed_count": fixed_count,
        "residual_population_size": residual_population,
        "residual_sample_size": sample_size,
        "sample_selection_counts": {
            kind: sum(row["selection"] == kind for row in stratum["permutations"])
            for kind in ("fixed", "srswor", "enumerated")
        },
        "estimates": {},
    }
    for metric in METRICS:
        fixed = [_arm_value(by_order[order], metric) for order in fixed_orders]
        sampled = [_arm_value(by_order[order], metric) for order in residual_orders]
        try:
            estimate = estimate_stratified_mean(
                fixed,
                sampled,
                expected_fixed_count=fixed_count,
                expected_sample_size=sample_size,
                residual_population_size=residual_population,
            )
        except IncompletePermutationSample as exc:
            return {**result, "status": "INCOMPLETE", "failure": str(exc)}
        low, high = confidence_interval_95(estimate.estimate, estimate.standard_error)
        item = {
            "estimate": estimate.estimate,
            "design_variance_estimate": estimate.variance_estimate,
            "design_standard_error": estimate.standard_error,
            "approximate_95_ci": [low, high],
            "confidence_method": "estimate +/- t(0.975,21) * design SE; approximate, permutation sampling only",
            "degenerate_zero_sample_variance": estimate.degenerate_interval,
        }
        if metric == "p95":
            spread = estimate_population_variance(
                fixed,
                sampled,
                expected_fixed_count=fixed_count,
                expected_sample_size=sample_size,
                residual_population_size=residual_population,
            )
            observed = [value.value for value in fixed + sampled]
            item["permutation_population_sd_estimate"] = spread.standard_deviation_estimate
            item["permutation_population_variance_raw_estimate"] = spread.raw_variance_estimate
            item["permutation_population_sd_truncated_at_zero"] = spread.truncated_at_zero
            item["observed_sample_min_p95"] = min(observed)
            item["observed_sample_max_p95"] = max(observed)
            item["sample_extrema_are_global"] = sample_size == residual_population
        result["estimates"][metric] = item
    return result


def analyze_results(schedule: dict[str, Any], arm_records: list[dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for dataset in issue101.DATASETS:
        dataset_strata = [row for row in schedule["schedules"] if row["dataset"] == dataset]
        results[dataset] = {"dataset": dataset, "policies": {}, "contrast_pess_minus_nominal": None}
        arms_for_dataset = [row for row in arm_records if row["dataset"] == dataset]
        for stratum in dataset_strata:
            selected_arms = [row for row in arms_for_dataset
                             if row["policy"] == stratum["policy"]
                             and row["case_id"] == stratum["case_id"]]
            results[dataset]["policies"][stratum["policy"]] = {
                "case_id": stratum["case_id"],
                "selected_ids": list(stratum["resource_ids"]),
                "selected_object_count": len(stratum["resource_ids"]),
                "permutation_population_size": stratum["permutation_population_size"],
                "arms": selected_arms,
                "expectation": _estimate_set(stratum, selected_arms),
            }
        nominal = results[dataset]["policies"].get("nominal", {}).get("expectation", {})
        pess = results[dataset]["policies"].get("pess", {}).get("expectation", {})
        if nominal.get("status") != "COMPLETE" or pess.get("status") != "COMPLETE":
            results[dataset]["contrast_pess_minus_nominal"] = {"status": "INCOMPLETE"}
            continue
        contrast: dict[str, Any] = {"status": "COMPLETE", "direction": "PESS - Nominal", "estimates": {}}
        for metric in METRICS:
            n_item = nominal["estimates"][metric]
            p_item = pess["estimates"][metric]
            n_est = PermutationValue((), n_item["estimate"], "COMPLETE", "complete")
            p_est = PermutationValue((), p_item["estimate"], "COMPLETE", "complete")
            n_mean = issue107_mean_from_set(n_est, n_item)
            p_mean = issue107_mean_from_set(p_est, p_item)
            delta = difference_estimate(p_mean, n_mean)
            low, high = confidence_interval_95(delta.estimate, delta.standard_error)
            contrast["estimates"][metric] = {
                "estimate": delta.estimate,
                "design_variance_estimate": delta.variance_estimate,
                "design_standard_error": delta.standard_error,
                "approximate_95_ci": [low, high],
                "confidence_method": "estimate +/- t(0.975,21) * combined design SE; approximate",
            }
        results[dataset]["contrast_pess_minus_nominal"] = contrast
    return results


def issue107_mean_from_set(value: PermutationValue, item: dict[str, Any]):
    """Rehydrate only the estimate and its already-computed design variance."""
    from ess_research.arecel.oid_sampling import MeanEstimate

    return MeanEstimate(
        estimate=float(value.value),
        variance_estimate=float(item["design_variance_estimate"]),
        sample_variance=None,
        fixed_count=0,
        residual_population_size=0,
        sample_size=0,
    )


def _write_findings(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Issue #107 — sampled uniform relative-OID Test evaluation", "",
        f"- Evidence label: **{manifest.get('evidence_label', 'experimentally observed PostgreSQL measurements')}**.",
        f"- Run ID: `{manifest['run_id']}`; source commit: `{manifest['source_commit']}`.",
        f"- Status: **{manifest['status']}**; attempted new EXPLAIN calls: {manifest.get('attempted_explain_calls', 0)}.",
        f"- Raw new-arm observations SHA-256: `{manifest.get('raw_observations_sha256', 'not available')}`.",
        "- Estimand: uniform-permutation expectation of the per-order Test P95; intervals cover only order sampling.",
        "- One global OID order applied to all 10,000 Test queries per arm; six planner clients; serial configurations.",
        "",
    ]
    if manifest.get("failure"):
        lines.extend([f"- Stop/failure: `{manifest['failure']['error_class']}` — {manifest['failure']['message']}.", ""])
    lines += ["## Per-dataset estimates", ""]
    for dataset in issue101.DATASETS:
        result = manifest.get("analysis", {}).get(dataset)
        if not result:
            lines.extend([f"### {dataset}", "", "Status: not analyzed.", ""])
            continue
        lines.extend([f"### {dataset}", "", "| Policy | Set size | Arms | Mean Q | P50 | Expected P95 | P99 |", "|---|---:|---:|---:|---:|---:|---:|"])
        for policy in ("nominal", "pess"):
            policy_result = result["policies"].get(policy, {})
            expectation = policy_result.get("expectation", {})
            if expectation.get("status") != "COMPLETE":
                lines.append(f"| {policy} | {policy_result.get('selected_object_count', '—')} | INCOMPLETE | — | — | — | — |")
                continue
            estimates = expectation["estimates"]
            values = [estimates[name]["estimate"] for name in ("mean", "p50", "p95", "p99")]
            lines.append(f"| {policy} | {policy_result['selected_object_count']} | {len(policy_result['arms'])} | "
                         + " | ".join(f"{value:.7g}" for value in values) + " |")
            p95 = estimates["p95"]
            lines.append("")
            lines.append(f"{policy} expected P95: `{p95['estimate']:.9g}`; design SE `{p95['design_standard_error']:.6g}`; "
                         f"approximate 95% interval `[{p95['approximate_95_ci'][0]:.9g}, {p95['approximate_95_ci'][1]:.9g}]`; "
                         f"permutation SD estimate `{p95['permutation_population_sd_estimate']:.7g}`; "
                         f"observed sample P95 range `[{p95['observed_sample_min_p95']:.7g}, {p95['observed_sample_max_p95']:.7g}]`.")
        contrast = result.get("contrast_pess_minus_nominal", {})
        if contrast.get("status") == "COMPLETE":
            p95 = contrast["estimates"]["p95"]
            lines.extend(["", f"PESS − Nominal expected P95: `{p95['estimate']:.9g}`; design SE `{p95['design_standard_error']:.6g}`; "
                          f"approximate 95% interval `[{p95['approximate_95_ci'][0]:.9g}, {p95['approximate_95_ci'][1]:.9g}]`."])
        else:
            lines.extend(["", "PESS − Nominal contrast: **INCOMPLETE**."])
        lines.append("")
    lines += [
        "## Limits and interpretation", "",
        "The confidence intervals use the frozen finite-population SRSWOR variance estimates and an approximate df=21 t critical value. They do not cover query/workload uncertainty, and are not exact coverage guarantees for skewed or heavy-tailed order outcomes. The sampled schedule is not full-permutation enumeration; sample extrema are not global extrema except for a complete census.",
        "",
        "A configuration with missing Plan Rows or any diagnostics status other than `complete`/`empty` is invalid. No order was dropped, replaced, or added in response to its outcome. A set or contrast with any incomplete arm is reported incomplete.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _pre_arm_guard(root: Path, guard: Any) -> None:
    elapsed = time.monotonic() - guard.started
    used = issue101.issue99.legacy.allocated_bytes(root)
    if elapsed >= HARD_STOP_SECONDS or used >= HARD_STOP_BYTES:
        raise RuntimeError("hard runtime/disk cap reached at an arm boundary")
    if elapsed >= EARLY_STOP_SECONDS or used >= EARLY_STOP_BYTES:
        raise StopBeforeNextArm(
            f"early stop before next arm: elapsed={elapsed:.1f}s, allocated={used} bytes"
        )


def _expected_columns(dataset: str) -> list[list[Any]]:
    return [
        [index + 1, name, re.sub(r"^varchar", "character varying", type_name.lower())]
        for index, (name, type_name) in enumerate(issue101.issue99.dataset_spec(dataset)[1])
    ]


def _input_is_pinned(dataset: str, identity: dict[str, Any]) -> bool:
    source_columns, pg_columns, row_count, csv_hash, _table = issue101.issue99.dataset_spec(dataset)
    return (
        identity.get("dataset") == dataset
        and identity.get("split") == "test"
        and identity.get("query_count") == 10_000
        and identity.get("truth_count") == 10_000
        and identity.get("csv_sha256") == csv_hash
        and identity.get("csv_rows") == row_count
        and identity.get("schema_columns") == list(source_columns)
        and identity.get("catalog_columns") == [name for name, _ in pg_columns]
        and identity.get("explicitly_dereferenced_label_split") == "test"
        and identity.get("non_test_label_values_indexed_serialized_or_used") is False
    )


def _collect_dataset(
    dataset: str,
    schedule: dict[str, Any],
    schedule_index: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]],
    protocol101: dict[str, Any],
    reuse_audit: dict[str, Any],
    root: Path,
    prefix: Path,
    helpers: Any,
    run_formal: Any,
    guard: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    input_root = root / "input" / dataset
    csv_path, queries, truths, identity = issue101.extract_test_inputs(dataset, input_root)
    if not _input_is_pinned(dataset, identity):
        raise RuntimeError(f"{dataset} extracted Test inputs differ from the pinned Issue #101 contract")
    sample, sample_identity = issue101.load_frozen_sample(dataset, root, helpers, protocol101)
    candidates = issue101.candidate_map(dataset)
    strata = [row for row in schedule["schedules"] if row["dataset"] == dataset]
    reuse_run_root = runtime_runs("ess-research", 105) / ISSUE105_RUN_ID
    reuse_manifest_path = reuse_run_root / "run-manifest.json"
    reuse_manifest = (json.loads(reuse_manifest_path.read_text(encoding="utf-8"))
                      if reuse_manifest_path.is_file() else {"datasets": {}})
    prior_dataset = reuse_manifest.get("datasets", {}).get(dataset, {})
    source_identity_matches = _test_input_matches_prior(
        dataset, identity, prior_dataset.get("source_input_identity", {})
    )
    if not source_identity_matches:
        for arm_key, source in list(reuse_audit["eligible_arms"].items()):
            if source["dataset"] == dataset:
                reuse_audit["eligible_arms"].pop(arm_key)
                reuse_audit["arms"][arm_key]["eligible"] = False
                reuse_audit["arms"][arm_key]["reasons"].append(
                    "current pinned Test input identity differs from #105"
                )
        reuse_audit["eligible_reuse_count"] = len(reuse_audit["eligible_arms"])
        _refresh_reuse_plan(manifest, reuse_audit)
    dataset_result: dict[str, Any] = {
        "dataset": dataset,
        "status": "INCOMPLETE",
        "source_input_identity": identity,
        "sample_identity": sample_identity,
        "strata": [],
        "arms": [],
        "physical_configuration_count": 0,
        "reused_configuration_count": 0,
        "new_configuration_count": 0,
        "reuse_input_identity_status": "PASS" if source_identity_matches else "FAIL_REMEASURE_FIXED_ARMS",
    }
    manifest["datasets"][dataset] = dataset_result
    atomic_json(root / "run-manifest.json", manifest)
    baseline_prior = reuse_audit["eligible_arms"]
    base_ordinary: str | None = None
    base_mcv: dict[str, str] = {}
    for arm_key, source in baseline_prior.items():
        if source["dataset"] == dataset:
            if base_ordinary is None:
                base_ordinary = source["ordinary_stats_sha256"]
            elif base_ordinary != source["ordinary_stats_sha256"]:
                raise RuntimeError(f"{dataset} reusable #105 ordinary-statistics fingerprints disagree")
            for candidate_id, digest in source["mcv_content_sha256_by_candidate"].items():
                previous = base_mcv.setdefault(candidate_id, digest)
                if previous != digest:
                    raise RuntimeError(f"{dataset}/{candidate_id} reusable #105 MCV fingerprints disagree")

    raw_path = root / "raw-observations.jsonl.gz"
    with issue101.issue99.legacy.owned_cluster(
        helpers, prefix, root / "clusters" / dataset, os.environ.copy(), guard
    ) as cluster:
        cluster["dataset"] = dataset
        table_load = issue101.configure_source_table(helpers, prefix, cluster, dataset, csv_path, sample)
        initial_table = issue105.table_identity(helpers, prefix, cluster, dataset)
        if (int(initial_table["relation_oid"]) != int(table_load["relation_oid"])
                or int(initial_table["row_count"]) != int(identity["csv_rows"])
                or initial_table["columns"] != _expected_columns(dataset)):
            raise RuntimeError(f"{dataset} full source table failed identity/schema/row-count checks")
        dataset_result["postgresql_table"] = {
            **table_load,
            "identity": initial_table,
            "source_csv_sha256": identity["csv_sha256"],
        }
        manifest["datasets"][dataset] = dataset_result
        atomic_json(root / "run-manifest.json", manifest)
        for stratum in strata:
            arm_results: list[dict[str, Any]] = []
            for sample_index, schedule_arm in enumerate(stratum["permutations"]):
                scheduled = validate_scheduled_arm(
                    schedule_index,
                    dataset=dataset,
                    policy=stratum["policy"],
                    case_id=stratum["case_id"],
                    resource_ids=stratum["resource_ids"],
                    permutation=schedule_arm["permutation"],
                    selection=schedule_arm["selection"],
                )
                if any(scheduled.get(key) != schedule_arm.get(key) for key in (
                    "permutation", "selection", "draw_index", "inclusion_probability", "sample_sha256")
                ):
                    raise RuntimeError("arm selection-stratum identity differs from frozen schedule record")
                arm_id = f"{dataset}-{stratum['policy']}-{sample_index:03d}-{schedule_arm['selection']}"
                base_record = _new_arm_record_base(dataset, stratum, schedule_arm, arm_id)
                reuse_key = f"{dataset}/{','.join(schedule_arm['permutation'])}"
                reusable = schedule_arm["selection"] == "fixed" and reuse_key in reuse_audit["eligible_arms"]
                attempt: dict[str, Any] = {
                    **base_record,
                    "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "REUSE_PENDING" if reusable else "PENDING",
                }
                manifest["current_arm"] = {key: attempt[key] for key in (
                    "dataset", "policy", "case_id", "configuration_id", "permutation", "selection", "status")}
                atomic_json(root / "run-manifest.json", manifest)
                if reusable:
                    manifest["current_arm"]["status"] = "REUSING_RAW_MEMBER"
                    atomic_json(root / "run-manifest.json", manifest)
                    old = reuse_audit["eligible_arms"][reuse_key]
                    old_dataset = reuse_manifest["datasets"][dataset]
                    old_arm = next(item for item in old_dataset["configurations"]
                                   if item["configuration_id"] == old["configuration_id"])
                    try:
                        old_rows, _metrics = _reused_rows(
                            runtime_runs("ess-research", 105) / ISSUE105_RUN_ID / "raw-observations.jsonl.gz",
                            old_arm,
                            dataset=dataset,
                            old_order=old["issue105_order"],
                            permutation=schedule_arm["permutation"],
                            queries=queries,
                            truths=truths,
                        )
                    except Exception as exc:
                        reusable = False
                        attempt["reuse_fallback_reason"] = f"{type(exc).__name__}: {str(exc)[:400]}"
                        reuse_audit["arms"][reuse_key]["eligible"] = False
                        reuse_audit["arms"][reuse_key]["reasons"].append("raw observation identity/recomputation failed")
                        reuse_audit["eligible_arms"].pop(reuse_key, None)
                        _refresh_reuse_plan(manifest, reuse_audit)
                    else:
                        record = {
                            **base_record,
                            "status": "REUSED_COMPLETE",
                            "metrics": _record_metrics(old_rows),
                            "source_run_id": ISSUE105_RUN_ID,
                            "source_configuration_id": old["configuration_id"],
                            "source_raw_member": {
                                "archive": str(runtime_runs("ess-research", 105) / ISSUE105_RUN_ID / "raw-observations.jsonl.gz"),
                                "archive_sha256": ISSUE105_RAW_SHA256,
                                "offset": old["raw_member_offset"],
                                "bytes": old["raw_member_bytes"],
                                "sha256": old["raw_member_sha256"],
                            },
                            "recomputed_from_source_rows": True,
                            "physical_audit_summary": {
                                "create_order": old_arm["create_statement_candidate_ids"],
                                "oid_order": old_arm["catalog_oid_order_candidate_ids"],
                                "ordinary_stats_sha256": old_arm["ordinary_column_stats"]["sha256"],
                                "mcv_content_sha256_by_candidate": old_arm["mcv_content_sha256_by_candidate"],
                                "table_identity": old_arm["table_identity"],
                            },
                        }
                        arm_results.append(record)
                        dataset_result["arms"].append(record)
                        dataset_result["reused_configuration_count"] += 1
                        dataset_result["physical_configuration_count"] += 1
                        manifest["arms_completed"] += 1
                        manifest["attempts"].append({**base_record, "status": "REUSED_COMPLETE"})
                        manifest["current_arm"] = None
                        manifest["datasets"][dataset] = dataset_result
                        atomic_json(root / "run-manifest.json", manifest)
                        print(
                            f"[{manifest['run_id']}] {manifest['arms_completed']}/156 "
                            f"reused {dataset}/{stratum['policy']} {sample_index + 1}/{len(stratum['permutations'])}; "
                            f"new EXPLAIN={manifest['attempted_explain_calls']}; "
                            f"disk={issue101.issue99.legacy.allocated_bytes(root)} bytes",
                            flush=True,
                        )
                        del old_rows
                        continue

                _pre_arm_guard(root, guard)
                physical_status = "INCOMPLETE"
                attempted_calls = 0
                plan_diagnostics: dict[str, Any] | None = None
                try:
                    manifest["current_arm"]["status"] = "CONFIGURING"
                    atomic_json(root / "run-manifest.json", manifest)
                    physical = issue105.configure_and_audit_arm(
                        dataset,
                        arm_id,
                        list(schedule_arm["permutation"]),
                        candidates,
                        sample,
                        protocol101["datasets"][dataset]["sample"],
                        csv_path,
                        identity,
                        helpers,
                        run_formal,
                        prefix,
                        cluster,
                        initial_table,
                        expected_ordinary_digest=base_ordinary,
                    )
                    ordinary_sha = physical["ordinary_column_stats"]["sha256"]
                    if base_ordinary is not None and ordinary_sha != base_ordinary:
                        raise RuntimeError("ordinary-column-statistics fingerprint differs from #105/reused baseline")
                    base_ordinary = base_ordinary or ordinary_sha
                    mcv_by_candidate = physical["mcv_content_sha256_by_candidate"]
                    for candidate_id, digest in mcv_by_candidate.items():
                        if candidate_id in base_mcv and base_mcv[candidate_id] != digest:
                            raise RuntimeError(f"{candidate_id} MCV fingerprint differs across configurations")
                    base_mcv.update(mcv_by_candidate)
                    sql_root = root / "sql" / arm_id
                    sql_root.mkdir(parents=True, exist_ok=False)
                    log_root = root / "logs" / arm_id
                    log_root.mkdir(parents=True, exist_ok=False)
                    manifest["current_arm"]["status"] = "EXPLAIN_RUNNING"
                    atomic_json(root / "run-manifest.json", manifest)
                    observations, plan_diagnostics = issue105.run_plan_batch(
                        prefix, cluster, queries, sql_root, physical["oid_to_candidate_id"], log_root
                    )
                    attempted_calls = plan_diagnostics["attempted_markers"]
                    manifest["attempted_explain_calls"] += attempted_calls
                    if manifest["attempted_explain_calls"] > MAX_NEW_EXPLAINS:
                        raise RuntimeError("new EXPLAIN count exceeded the authorization's 1.56M absolute maximum")
                    shutil.rmtree(sql_root, ignore_errors=True)
                    rows = issue105.rows_for_config(
                        dataset,
                        arm_id,
                        list(schedule_arm["permutation"]),
                        queries,
                        truths,
                        observations,
                    )
                    raw_member = issue105.append_raw_member(raw_path, rows)
                    metrics = _record_metrics(rows)
                    physical_status = metrics["statistical_status"]
                    record = {
                        **base_record,
                        **{key: value for key, value in physical.items() if key != "oid_to_candidate_id"},
                        "status": physical_status,
                        "metrics": metrics,
                        "plan_batch": plan_diagnostics,
                        "raw_member": raw_member,
                        "source_run_id": manifest["run_id"],
                        "recomputed_from_source_rows": False,
                    }
                    dataset_result["new_configuration_count"] += 1
                    dataset_result["physical_configuration_count"] += 1
                    physical_status = metrics["statistical_status"]
                    if physical_status != "COMPLETE":
                        record["validity_failure"] = "one or more Plan Rows or ESS diagnostics were incomplete"
                except StopBeforeNextArm:
                    raise
                except Exception as exc:
                    call_count_unknown = (
                        manifest.get("current_arm", {}).get("status") == "EXPLAIN_RUNNING"
                        and plan_diagnostics is None
                    )
                    record = {
                        **base_record,
                        "status": "CONFIGURATION_INVALID",
                        "error": {"class": type(exc).__name__, "message": str(exc)[:800]},
                        "metrics": {"statistical_status": "INCOMPLETE"},
                        "source_run_id": manifest["run_id"],
                        "attempted_explain_calls": None if call_count_unknown else attempted_calls,
                        "attempted_call_count_unknown": call_count_unknown,
                    }
                    if call_count_unknown:
                        manifest["attempted_explain_calls_is_lower_bound"] = True
                    if plan_diagnostics is not None:
                        record["plan_batch"] = plan_diagnostics
                    dataset_result["new_configuration_count"] += 1
                    dataset_result["physical_configuration_count"] += 1
                arm_results.append(record)
                dataset_result["arms"].append(record)
                manifest["arms_completed"] += 1
                manifest["attempts"].append({**base_record, "status": record["status"],
                                             "attempted_explain_calls": record.get("attempted_explain_calls", attempted_calls),
                                             "attempted_call_count_unknown": record.get("attempted_call_count_unknown", False)})
                manifest["current_arm"] = None
                manifest["attempted_explain_calls_total"] = manifest["attempted_explain_calls"]
                manifest["datasets"][dataset] = dataset_result
                atomic_json(root / "run-manifest.json", manifest)
                print(
                    f"[{manifest['run_id']}] {manifest['arms_completed']}/156 {record['status']} "
                    f"{dataset}/{stratum['policy']} {sample_index + 1}/{len(stratum['permutations'])}; "
                    f"new EXPLAIN={manifest['attempted_explain_calls']}; "
                    f"disk={issue101.issue99.legacy.allocated_bytes(root)} bytes",
                    flush=True,
                )
            stratum_result = {
                "dataset": dataset,
                "policy": stratum["policy"],
                "case_id": stratum["case_id"],
                "resource_ids": list(stratum["resource_ids"]),
                "sample_sha256": stratum["sample_sha256"],
                "arm_count": len(arm_results),
                "complete_arm_count": sum(arm.get("metrics", {}).get("statistical_status") == "COMPLETE"
                                           for arm in arm_results),
                "reused_arm_count": sum(arm.get("status") == "REUSED_COMPLETE" for arm in arm_results),
                "arms": arm_results,
            }
            stratum_result["status"] = "COMPLETE" if stratum_result["complete_arm_count"] == len(stratum["permutations"]) else "INCOMPLETE"
            stratum_result["expectation"] = _estimate_set(stratum, arm_results)
            dataset_result["strata"].append(stratum_result)
            manifest["current_arm"] = None
            manifest["datasets"][dataset] = dataset_result
            atomic_json(root / "run-manifest.json", manifest)
        dataset_result["cluster_identity"] = [str(value) for value in cluster["identity"]]
        manifest["datasets"][dataset] = dataset_result
        atomic_json(root / "run-manifest.json", manifest)
    pgdata = root / "clusters" / dataset / "pgdata"
    if pgdata.exists():
        shutil.rmtree(pgdata)
    shutil.rmtree(input_root, ignore_errors=True)
    dataset_result["status"] = "COMPLETE" if all(row["status"] == "COMPLETE" for row in dataset_result["strata"]) else "INCOMPLETE"
    return dataset_result


def execute(run_id: str | None = None) -> Path:
    if platform.python_version() != "3.12.3" or np.__version__ != "2.3.4":
        raise RuntimeError("Issue #107 execution requires the Issue #101 Python 3.12.3 / NumPy 2.3.4 environment")
    protocol101 = issue101.read_protocol()
    if issue101.sha256_file(issue101.PROTOCOL_PATH) != ISSUE101_PROTOCOL_SHA256:
        raise RuntimeError("Issue #101 protocol hash differs from the approved source pin")
    if issue101.sha256_file(issue101.PROTOCOL_PATH.parent / "run_issue101.py") != ISSUE101_RUNNER_SHA256:
        raise RuntimeError("Issue #101 runner hash differs from the approved source pin")
    if issue105.sha256_file(issue105.HERE / "protocol-v1.md") != issue105.ISSUE105_PROTOCOL_SHA256:
        raise RuntimeError("Issue #105 protocol changed from its frozen run reference")
    if issue105.sha256_file(issue105.HERE / "protocol-amendment-v1.md") != issue105.ISSUE105_AMENDMENT_SHA256:
        raise RuntimeError("Issue #105 execution amendment changed from its frozen run reference")
    schedule, schedule_index = checked_frozen_schedule()
    clean = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           check=True, capture_output=True, text=True).stdout
    if clean.strip():
        raise RuntimeError("Issue #107 official Test access requires a clean committed Worktree")
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.strip()
    if branch != "research/issue107-uniform-oid-protocol":
        raise RuntimeError(f"Issue #107 execution is pinned to its task branch, not {branch!r}")
    source_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  check=True, capture_output=True, text=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise RuntimeError("could not pin the clean source commit")
    subprocess.run(["git", "merge-base", "--is-ancestor", ISSUE107_APPROVED_HEAD, "HEAD"],
                   cwd=ROOT, check=True, capture_output=True)

    reuse_audit = audit_issue105_reuse(schedule, protocol101)
    reused = reuse_audit["eligible_reuse_count"]
    planned_new = 156 - reused
    run_id = run_id or f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-issue107-{uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be one safe path component")
    runs = runtime_runs("ess-research", 107)
    runs.mkdir(parents=True, exist_ok=True)
    root = runs / run_id
    root.mkdir(exist_ok=False)
    for directory in ("logs", "clusters", "input", "samples", "sql"):
        (root / directory).mkdir()
    manifest: dict[str, Any] = {
        "format": "ess-issue107-sampled-test-run-v1",
        "issue": 107,
        "run_id": run_id,
        "status": "INCOMPLETE",
        "phase": "preflight_complete",
        "authorization_comment_id": ISSUE107_AUTH_COMMENT,
        "authorized_protocol_head_sha": ISSUE107_APPROVED_HEAD,
        "source_commit": source_commit,
        "protocol_v2_sha256": sha256_file(HERE / "protocol-v2.md"),
        "sample_sha256": ISSUE107_SAMPLE_SHA256,
        "root_seed": ISSUE107_ROOT_SEED,
        "rng_version": schedule["rng_version"],
        "frozen_schedule": schedule,
        "schedule_index_count": len(schedule_index),
        "issue101_protocol_sha256": ISSUE101_PROTOCOL_SHA256,
        "issue101_runner_sha256": ISSUE101_RUNNER_SHA256,
        "issue105_run_id": ISSUE105_RUN_ID,
        "issue105_archive_sha256": ISSUE105_RAW_SHA256,
        "issue105_reuse_audit": reuse_audit,
        "planned_configurations": 156,
        "planned_new_configurations_after_preflight": planned_new,
        "planned_explain_calls_after_preflight": planned_new * 10_000,
        "maximum_new_explain_calls": MAX_NEW_EXPLAINS,
        "attempted_explain_calls": 0,
        "arms_completed": 0,
        "attempts": [],
        "parallel_clients_per_configuration": PARALLEL_CLIENTS,
        "wall_early_stop_seconds": EARLY_STOP_SECONDS,
        "wall_hard_limit_seconds": HARD_STOP_SECONDS,
        "disk_early_stop_bytes": EARLY_STOP_BYTES,
        "disk_hard_limit_bytes": HARD_STOP_BYTES,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "available_cpu_affinity_count": len(os.sched_getaffinity(0)),
        "available_disk_bytes_at_start": shutil.disk_usage(root).free,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "datasets": {},
        "failure": None,
    }
    _refresh_reuse_plan(manifest, reuse_audit)
    atomic_json(root / "run-manifest.json", manifest)
    guard = issue101.issue99.legacy.AggregateGuard(
        root,
        early_seconds=HARD_STOP_SECONDS,
        hard_seconds=HARD_STOP_SECONDS,
        early_bytes=HARD_STOP_BYTES,
        hard_bytes=HARD_STOP_BYTES,
    )
    try:
        with issue101.fixed_pgoptions(), guard:
            manifest["phase"] = "pinned_postgresql_build"
            atomic_json(root / "run-manifest.json", manifest)
            prefix, pg_build = issue101.issue99.legacy.build_pg(root)
            if pg_build.get("source_commit") != POSTGRESQL_COMMIT or pg_build.get("version") != "PostgreSQL 16.14":
                raise RuntimeError("fresh PostgreSQL build differs from the frozen 16.14 source")
            manifest["postgresql_build"] = pg_build
            helpers, run_formal, helper_hashes = issue101.load_pinned_helpers(root)
            manifest["issue99_helper_commit"] = ISSUE99_HELPER_COMMIT
            manifest["helper_sha256"] = helper_hashes
            atomic_json(root / "run-manifest.json", manifest)

            for dataset in issue101.DATASETS:
                manifest["phase"] = f"sampled_test_{dataset}"
                manifest["current_dataset"] = dataset
                atomic_json(root / "run-manifest.json", manifest)
                result = _collect_dataset(
                    dataset,
                    schedule,
                    schedule_index,
                    protocol101,
                    reuse_audit,
                    root,
                    prefix,
                    helpers,
                    run_formal,
                    guard,
                    manifest,
                )
                manifest["datasets"][dataset] = result
                manifest["attempted_explain_calls"] = sum(
                    arm.get("plan_batch", {}).get("attempted_markers", 0)
                    for dataset_result in manifest["datasets"].values()
                    for arm in dataset_result.get("arms", [])
                )
                if manifest["attempted_explain_calls"] > MAX_NEW_EXPLAINS:
                    raise RuntimeError("new EXPLAIN calls exceeded the authorized absolute maximum")
                atomic_json(root / "run-manifest.json", manifest)

            manifest["analysis"] = analyze_results(schedule, [
                arm for dataset_result in manifest["datasets"].values()
                for arm in dataset_result.get("arms", [])
            ])
            complete = (
                len(manifest["attempts"]) == 156
                and all(result.get("status") == "COMPLETE" for result in manifest["datasets"].values())
                and all(result.get("contrast_pess_minus_nominal", {}).get("status") == "COMPLETE"
                        for result in manifest["analysis"].values())
            )
            manifest["status"] = "COMPLETE" if complete else "INCOMPLETE"
            manifest["phase"] = "complete" if complete else "completed_with_invalid_or_incomplete_arms"
            manifest["evidence_label"] = "experimentally observed PostgreSQL measurements"
            manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    except StopBeforeNextArm as exc:
        manifest["status"] = "STOPPED_AT_EARLY_LIMIT"
        manifest["phase"] = "early_stop_before_next_arm"
        manifest["failure"] = {"error_class": type(exc).__name__, "message": str(exc)}
        pending = manifest.get("current_arm")
        if pending:
            manifest["attempts"].append({**pending, "status": "NOT_STARTED_EARLY_LIMIT",
                                         "attempted_explain_calls": 0})
            manifest["stopped_before_arm"] = pending
    except BaseException as exc:
        manifest["status"] = "INCOMPLETE"
        manifest["phase"] = manifest.get("phase", "unknown")
        interrupted = manifest.get("current_arm")
        manifest["failure"] = {
            "error_class": type(exc).__name__,
            "message": str(exc)[:1000],
            "current_arm": interrupted,
            "guard_stop_reason": guard.stop_reason,
        }
        if interrupted:
            manifest["attempts"].append({
                **interrupted,
                "status": "INTERRUPTED_IN_FLIGHT",
                "attempted_explain_calls": None,
                "attempted_call_count_unknown": interrupted.get("status") == "EXPLAIN_RUNNING",
            })
            if interrupted.get("status") == "EXPLAIN_RUNNING":
                manifest["attempted_explain_calls_is_lower_bound"] = True
        if isinstance(exc, KeyboardInterrupt):
            manifest["stop_origin"] = "hard_resource_guard_or_external_interrupt"
    finally:
        manifest["current_arm"] = None
        manifest["peak_allocated_disk_bytes"] = guard.peak
        manifest["elapsed_wall_seconds"] = round(time.monotonic() - guard.started, 3)
        manifest["raw_observations_path"] = str(root / "raw-observations.jsonl.gz")
        raw_path = root / "raw-observations.jsonl.gz"
        if raw_path.is_file():
            manifest["raw_observations_bytes"] = raw_path.stat().st_size
            manifest["raw_observations_sha256"] = sha256_file(raw_path)
        if "analysis" not in manifest:
            manifest["analysis"] = analyze_results(
                schedule,
                [arm for dataset_result in manifest["datasets"].values()
                 for arm in dataset_result.get("arms", [])],
            )
        manifest["recovery_note"] = (
            "Each completed arm has an fsynced gzip member and an atomic manifest checkpoint. "
            "After interruption, verify the last manifest and member hashes; ignore/truncate any unreferenced raw tail. "
            "Do not resume or exceed the approved caps without renewed authorization."
        )
        atomic_json(root / "run-manifest.json", manifest)
        _write_findings(root / "findings.md", manifest)
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    root = execute(args.run_id)
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "run_root": str(root),
        "status": manifest["status"],
        "source_commit": manifest["source_commit"],
        "arms_completed": manifest["arms_completed"],
        "attempted_explain_calls": manifest["attempted_explain_calls"],
        "peak_allocated_disk_bytes": manifest.get("peak_allocated_disk_bytes"),
        "raw_observations_sha256": manifest.get("raw_observations_sha256"),
    }, sort_keys=True))
    return 0 if manifest["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
