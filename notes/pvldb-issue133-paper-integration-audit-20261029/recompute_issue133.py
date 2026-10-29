#!/usr/bin/env python3
"""Read-only independent recomputation of Issue #133 Test observations.

Reads only the retained runtime manifests, catalog audits and gzip JSONL archives.
It never connects to PostgreSQL and writes only the two compact JSON summaries
in the caller-specified output directory.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import zlib
from collections import Counter
from typing import Any, Iterable

import numpy as np


RUN_SPECS = {
    "forest10_all": {
        "run_id": "20261028T1408Z-issue133-forest10-random01-02",
        "expected_sha256": "d088a9b8cb33d62a507dc9cef0fb8e7cc73c12f8116e91ce528a9123d98b7318",
        "expected_rows": 20_000,
        "expected_configs": ["forest10-all-random-01", "forest10-all-random-02"],
        "dataset": "forest10",
    },
    "forest10_b5": {
        "run_id": "20261029Tissue133-forest10-b5-nominal-matched",
        "expected_sha256": "43a4ee6e53106768cef26fefa2b797ed948199451f2ac431f9040cde881ef0b4",
        "expected_rows": 10_000,
        "expected_configs": ["forest10-b5-nominal-matched-random01"],
        "dataset": "forest10",
    },
    "dmv11": {
        "run_id": "20261029T0300Z-issue133-dmv11-three-arm",
        "expected_sha256": "69a2202d815c1db991ffdfbfc431d2fa447ddeffc31de898d4ae87d3f5101dbe",
        "expected_rows": 30_000,
        "expected_configs": [
            "dmv11-all-random-01",
            "dmv11-all-random-02",
            "dmv11-b5-nominal-matched",
        ],
        "dataset": "dmv11",
    },
}

EXECUTION_SOURCE = {
    "forest10_all": {
        "commit": "55a5188fa4d08904d26114330c215596a0266b0e",
        "protocol": "experiments/all-pairwise-oid-issue133/minimal-forest10/protocol-v1.json",
        "runner": "experiments/all-pairwise-oid-issue133/minimal-forest10/run_minimal_forest10.py",
    },
    "forest10_b5": {
        "commit": "537f88073587535018dc84e38456c2608e491b7f",
        "protocol": "experiments/all-pairwise-oid-issue133/minimal-forest10-b5-control/protocol-v1.json",
        "runner": "experiments/all-pairwise-oid-issue133/minimal-forest10-b5-control/run_b5_control.py",
    },
    "dmv11": {
        "commit": "45f55a02244294a8cb6c1b25ba8b3c01b9676c02",
        "protocol": "experiments/all-pairwise-oid-issue133/minimal-dmv11/protocol-v1.json",
        "runner": "experiments/all-pairwise-oid-issue133/minimal-dmv11/run_minimal_dmv11.py",
    },
}

FROZEN_SOURCE_COMMIT = "110c676e1c6f15746198534f5c65b146625304ec"
FROZEN_SOURCE_FILES = {
    "all-order-sample-v1.json": (
        "experiments/all-pairwise-oid-issue133/all-order-sample-v1.json",
        "6e53e60083426a0f6fedb7147eae418ceb69aa826e01484d8794b95a80546d9c",
    ),
    "candidate-universe-manifest.json": (
        "experiments/all-pairwise-oid-issue133/candidate-universe-manifest.json",
        "20fd045a1391e6b0308d36ec581e128db185b892bc6e7384540e77c483572104",
    ),
    "frozen-train-resources-issue96-v1.json": (
        "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json",
        "2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca",
    ),
}

CONFIG_EXPECTED_OBJECTS = {
    "forest10-all-random-01": 45,
    "forest10-all-random-02": 45,
    "forest10-b5-nominal-matched-random01": 5,
    "dmv11-all-random-01": 55,
    "dmv11-all-random-02": 55,
    "dmv11-b5-nominal-matched": 5,
}


def canonical_json_bytes(value: Any) -> bytes:
    """Issue #101 canonical JSON digest convention."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_show_bytes(repository: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def split_gzip_members(compressed: bytes) -> list[dict[str, Any]]:
    """Validate and split a concatenated gzip stream without rewriting it."""
    members: list[dict[str, Any]] = []
    offset = 0
    while offset < len(compressed):
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        payload = decoder.decompress(compressed[offset:])
        payload += decoder.flush()
        if not decoder.eof:
            raise ValueError(f"truncated gzip member at byte {offset}")
        consumed = len(compressed[offset:]) - len(decoder.unused_data)
        if consumed <= 0:
            raise ValueError(f"empty or invalid gzip member at byte {offset}")
        member_bytes = compressed[offset : offset + consumed]
        members.append(
            {
                "offset": offset,
                "bytes": consumed,
                "sha256": sha256_bytes(member_bytes),
                "payload": payload,
                "eof": decoder.eof,
            }
        )
        offset += consumed
    if offset != len(compressed):
        raise ValueError("unconsumed trailing bytes after gzip members")
    return members


def qerror_for_plan_rows(plan_rows: int, truth: int) -> tuple[float, int]:
    """Reproduce Issue #101 rounding and zero-aware Q-error semantics."""
    if (
        isinstance(plan_rows, bool)
        or not isinstance(plan_rows, int)
        or plan_rows < 0
        or isinstance(truth, bool)
        or not isinstance(truth, int)
        or truth < 0
    ):
        raise ValueError("Plan Rows and truth must be nonnegative integers")
    rounded = int(np.round(1.0 * plan_rows))
    estimate = float(rounded)
    actual = float(truth)
    if estimate == 0 and actual == 0:
        error = 1.0
    elif estimate == 0:
        error = actual
    elif actual == 0:
        error = estimate
    elif estimate > actual:
        error = estimate / actual
    else:
        error = actual / estimate
    return float(error), rounded


def summarize_errors(values: list[float]) -> dict[str, float]:
    errors = np.asarray(values, dtype=np.float64)
    if errors.size == 0:
        raise ValueError("cannot summarize an empty error vector")
    return {
        "p50": float(np.median(errors)),
        "p95": float(np.percentile(errors, 95)),
        "p99": float(np.percentile(errors, 99)),
        "mean": float(np.mean(errors)),
        "max": float(np.max(errors)),
    }


def descriptor_for(spec_key: str, manifest: dict[str, Any], index: int) -> dict[str, Any]:
    if spec_key == "forest10_all":
        raw = manifest["arms"][index]["raw_member"]
        return {
            "offset": raw["raw_member_offset"],
            "bytes": raw["raw_member_bytes"],
            "sha256": raw["raw_member_sha256"],
        }
    if spec_key == "forest10_b5":
        raw = manifest["raw_member"]
        return {
            "offset": raw["raw_member_offset"],
            "bytes": raw["raw_member_bytes"],
            "sha256": raw["raw_member_sha256"],
        }
    raw = manifest["raw_archive"]["members"][index]
    return {
        "offset": raw["offset"],
        "bytes": raw["bytes"],
        "sha256": raw["sha256"],
    }


def expected_config_for(spec_key: str, manifest: dict[str, Any], index: int) -> str | None:
    if spec_key == "forest10_all":
        return manifest["arms"][index]["configuration_id"]
    if spec_key == "dmv11":
        return manifest["arms"][index]["configuration_id"]
    return None


def catalog_arms(catalog_audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    arms = catalog_audit.get("arms")
    if isinstance(arms, list):
        return {item["configuration_id"]: item for item in arms}
    return {catalog_audit["configuration_id"]: catalog_audit}


def make_oid_map(arm: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    entries = arm.get("catalog", [])
    by_oid: dict[str, str] = {}
    by_candidate: dict[str, str] = {}
    for entry in entries:
        candidate = entry.get("candidate_id")
        oid = entry.get("oid")
        if not isinstance(candidate, str) or isinstance(oid, bool) or not isinstance(oid, int):
            raise ValueError("malformed catalog entry: candidate ID or OID")
        if candidate in by_candidate or str(oid) in by_oid:
            raise ValueError("duplicate candidate ID or OID in catalog")
        by_candidate[candidate] = str(oid)
        by_oid[str(oid)] = candidate
    return by_oid, by_candidate


def verify_catalog_arm(
    arm: dict[str, Any], configuration_id: str, execution_metadata: dict[str, Any]
) -> dict[str, Any]:
    entries = arm.get("catalog", [])
    requested = arm.get("create_statement_candidate_ids", [])
    actual = arm.get("catalog_oid_order_candidate_ids", [])
    oid_sorted = [
        item["candidate_id"] for item in sorted(entries, key=lambda item: int(item["oid"]))
    ]
    expected_n = CONFIG_EXPECTED_OBJECTS[configuration_id]
    errors: list[str] = []
    if len(entries) != expected_n:
        errors.append(f"catalog_count={len(entries)} expected={expected_n}")
    candidates = [item.get("candidate_id") for item in entries]
    if len(set(candidates)) != len(candidates):
        errors.append("duplicate_candidate_id")
    if requested != actual or actual != oid_sorted:
        errors.append("requested_create_order_vs_actual_oid_order_mismatch")
    for entry in entries:
        if entry.get("kinds") != ["m"]:
            errors.append(f"{entry.get('candidate_id')}:not_plain_mcv")
        if len(entry.get("attnames", [])) != 2 or len(set(entry.get("attnames", []))) != 2:
            errors.append(f"{entry.get('candidate_id')}:not_two_distinct_attributes")
        if entry.get("statistics_target") != 300:
            errors.append(f"{entry.get('candidate_id')}:target_not_300")
        state = entry.get("payload_state")
        populated = entry.get("mcv_payload_present")
        if (state == "POPULATED") != bool(populated):
            errors.append(f"{entry.get('candidate_id')}:payload_state_disagreement")
        if state == "NULL" and entry.get("mcv_item_count") != 0:
            errors.append(f"{entry.get('candidate_id')}:NULL_payload_item_count_not_zero")
        if state == "POPULATED" and not (entry.get("mcv_item_count", 0) > 0):
            errors.append(f"{entry.get('candidate_id')}:populated_payload_empty")
    payload_counts = dict(Counter(item.get("payload_state", "MISSING") for item in entries))
    return {
        "configuration_id": configuration_id,
        "expected_object_count": expected_n,
        "catalog_object_count": len(entries),
        "candidate_ids_unique": len(set(candidates)) == len(candidates),
        "requested_create_order_matches_actual_ascending_oid_order": not any(
            "order" in error for error in errors
        ),
        "payload_state_counts": payload_counts,
        "ordinary_stats_sha256": execution_metadata.get(
            "ordinary_stats_sha256", arm.get("ordinary_stats_sha256")
        ),
        "sample_sha256": execution_metadata.get("sample_sha256", arm.get("sample_sha256")),
        "table_logical_identity": execution_metadata.get(
            "table_logical_identity", arm.get("table_logical_identity")
        ),
        "requested_create_order_candidate_ids": requested,
        "actual_oid_order_candidate_ids": actual,
        "permutation_sha256": execution_metadata.get(
            "permutation_sha256", execution_metadata.get("b5_order_sha256")
        ),
        "create_count": execution_metadata.get("create_count", arm.get("create_count")),
        "target_count": execution_metadata.get(
            "target_count", execution_metadata.get(
                "statistics_target_count",
                arm.get("target_count", arm.get("statistics_target_count")),
            )
        ),
        "analyze_count": execution_metadata.get("analyze_count", arm.get("analyze_count")),
        "catalog_status": arm.get("status", arm.get("catalog_status")),
        "errors": errors,
    }


def event_sequences(
    row: dict[str, Any], oid_to_candidate: dict[str, str], catalog_candidates: set[str]
) -> tuple[tuple[str, ...], tuple[str, ...], list[str]]:
    selection: list[str] = []
    estimate: list[str] = []
    issues: list[str] = []
    for event in row.get("mcv_events", []):
        kind = event.get("type")
        if kind not in {"mcv_selection", "mcv_estimate"}:
            continue
        raw_oid = event.get("stat_oid")
        mapped = oid_to_candidate.get(str(raw_oid)) if raw_oid is not None else None
        direct = event.get("candidate_id")
        if direct is not None and direct not in catalog_candidates:
            issues.append(f"unknown_direct_candidate:{direct}")
        if direct is not None and mapped is not None and direct != mapped:
            issues.append(f"candidate_oid_disagreement:{direct}:{mapped}")
        candidate = direct or mapped
        if candidate is None:
            issues.append(f"unmapped_stat_oid:{raw_oid}")
            continue
        (selection if kind == "mcv_selection" else estimate).append(candidate)
    return tuple(selection), tuple(estimate), issues


def parse_member_records(payload: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(io.StringIO(payload.decode("utf-8")), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL record at member line {line_no}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"JSONL record at member line {line_no} is not an object")
        records.append(record)
    return records


def validate_records(
    records: list[dict[str, Any]],
    configuration_id: str,
    expected_count: int = 10_000,
    expected_row_configuration_id: str | None = None,
) -> dict[str, Any]:
    if len(records) != expected_count:
        raise ValueError(
            f"{configuration_id}: incomplete row count {len(records)} != {expected_count}"
        )
    ids: list[str] = []
    truth_digest = hashlib.sha256()
    values: list[float] = []
    plan_rows: list[int] = []
    zero_both = zero_estimate = zero_truth = 0
    seqs: list[tuple[str, ...]] = []
    estimate_seqs: list[tuple[str, ...]] = []
    raw_diag = Counter()
    raw_diag_integrity = Counter()
    raw_extension_diag = Counter()
    raw_plan_status = Counter()
    raw_attr_status = Counter()
    raw_unknown_oids = 0
    event_map_issues = Counter()
    for index, row in enumerate(records):
        expected_row_id = expected_row_configuration_id or configuration_id
        if row.get("configuration_id") != expected_row_id:
            raise ValueError(f"{configuration_id}: row configuration ID mismatch")
        if row.get("dataset") not in (None, configuration_id.split("-")[0]):
            # DMV11 configuration IDs begin with dmv11; Forest10 likewise.
            raise ValueError(f"{configuration_id}: dataset field mismatch")
        if row.get("status") != "VALID":
            raise ValueError(f"{configuration_id}: invalid query status at row {index}")
        query_id = row.get("query_id")
        if not isinstance(query_id, str):
            raise ValueError(f"{configuration_id}: missing string query ID")
        ids.append(query_id)
        truth = row.get("true_cardinality")
        estimate = row.get("estimate_plan_rows")
        error, rounded = qerror_for_plan_rows(estimate, truth)
        if row.get("estimate_rounded_r1") != rounded:
            raise ValueError(f"{configuration_id}: rounded estimate mismatch at {query_id}")
        stored = row.get("qerror")
        if not isinstance(stored, (int, float)) or not math.isfinite(float(stored)):
            raise ValueError(f"{configuration_id}: missing/nonfinite stored qerror")
        if not math.isclose(float(stored), error, rel_tol=1e-14, abs_tol=1e-14):
            raise ValueError(f"{configuration_id}: stored qerror mismatch at {query_id}")
        values.append(error)
        plan_rows.append(estimate)
        truth_digest.update(
            canonical_json_bytes({"query_id": query_id, "true_cardinality": truth})
        )
        if rounded == 0 and truth == 0:
            zero_both += 1
        elif rounded == 0:
            zero_estimate += 1
        elif truth == 0:
            zero_truth += 1
        raw_diag[row.get("diagnostics_status", row.get("diagnostics_integrity_status", "MISSING"))] += 1
        raw_diag_integrity[row.get("diagnostics_integrity_status", "NOT_RECORDED")] += 1
        raw_extension_diag[row.get("extension_diagnostics_status", "NOT_RECORDED")] += 1
        raw_plan_status[row.get("plan_rows_integrity_status", "NOT_RECORDED")] += 1
        raw_attr_status[row.get("candidate_id_attribution_status", "NOT_RECORDED")] += 1
        unknown = row.get("unknown_stat_oids", [])
        raw_unknown_oids += len(unknown) if isinstance(unknown, list) else int(bool(unknown))
        selection = row.get("_audit_selection_sequence", ())
        estimate_sequence = row.get("_audit_estimate_sequence", ())
        seqs.append(tuple(selection))
        estimate_seqs.append(tuple(estimate_sequence))
        event_map_issues.update(row.get("_audit_event_map_issues", []))
    if len(set(ids)) != expected_count:
        raise ValueError(f"{configuration_id}: query IDs are not unique")
    if any(row.get("source_index") != i for i, row in enumerate(records)):
        raise ValueError(f"{configuration_id}: query source order is incomplete")
    metric_values = summarize_errors(values)
    return {
        "configuration_id": configuration_id,
        "valid_query_count": len(records),
        "query_ids_sha256": sha256_json(ids),
        "test_truth_canonical_sha256": truth_digest.hexdigest(),
        "metric_summary": metric_values,
        "zero_cases": {
            "estimate_zero_and_truth_zero": zero_both,
            "estimate_zero_truth_positive": zero_estimate,
            "truth_zero_estimate_positive": zero_truth,
            "either_zero": zero_both + zero_estimate + zero_truth,
        },
        "plan_rows": plan_rows,
        "qerrors": values,
        "query_ids": ids,
        "selection_sequences": seqs,
        "estimate_sequences": estimate_seqs,
        "diagnostics_status_counts_preserved_from_raw": dict(raw_diag),
        "diagnostics_integrity_status_counts": dict(raw_diag_integrity),
        "extension_diagnostics_status_counts": dict(raw_extension_diag),
        "plan_rows_integrity_status_counts": dict(raw_plan_status),
        "candidate_id_attribution_status_counts": dict(raw_attr_status),
        "unknown_stat_oid_count": raw_unknown_oids,
        "event_mapping_issues": dict(event_map_issues),
    }


def compare_pair(
    left: dict[str, Any],
    right: dict[str, Any],
    left_label: str,
    right_label: str,
) -> dict[str, Any]:
    if left["query_ids"] != right["query_ids"]:
        raise ValueError(f"query ID order differs for {left_label} vs {right_label}")
    plan_diff = q_diff = seq_diff = est_seq_diff = 0
    left_better = left_worse = equal = 0
    pair_deltas: list[float] = []
    changed_ids: list[str] = []
    for i, query_id in enumerate(left["query_ids"]):
        lp, rp = left["plan_rows"][i], right["plan_rows"][i]
        lq, rq = left["qerrors"][i], right["qerrors"][i]
        if lp != rp:
            plan_diff += 1
        if lq != rq:
            q_diff += 1
            changed_ids.append(query_id)
        if left["selection_sequences"][i] != right["selection_sequences"][i]:
            seq_diff += 1
        if left["estimate_sequences"][i] != right["estimate_sequences"][i]:
            est_seq_diff += 1
        pair_deltas.append(lq - rq)
        if lq < rq:
            left_better += 1
        elif lq > rq:
            left_worse += 1
        else:
            equal += 1
    lmetrics, rmetrics = left["metric_summary"], right["metric_summary"]
    return {
        "left_configuration": left_label,
        "right_configuration": right_label,
        "p95_left_minus_right": lmetrics["p95"] - rmetrics["p95"],
        "plan_rows_different_queries": plan_diff,
        "qerror_different_queries": q_diff,
        "selection_sequence_different_queries": seq_diff,
        "estimate_sequence_different_queries": est_seq_diff,
        "left_qerror_better_queries": left_better,
        "left_qerror_worse_queries": left_worse,
        "qerror_equal_queries": equal,
        "paired_qerror_delta_left_minus_right": {
            "mean": float(np.mean(np.asarray(pair_deltas, dtype=np.float64))),
            "median": float(np.median(np.asarray(pair_deltas, dtype=np.float64))),
            "min": float(np.min(np.asarray(pair_deltas, dtype=np.float64))),
            "max": float(np.max(np.asarray(pair_deltas, dtype=np.float64))),
        },
        "changed_qerror_query_ids_first_20": changed_ids[:20],
    }


def remap_records(
    records: list[dict[str, Any]], oid_to_candidate: dict[str, str], candidates: set[str]
) -> None:
    for row in records:
        selection, estimates, issues = event_sequences(row, oid_to_candidate, candidates)
        row["_audit_selection_sequence"] = selection
        row["_audit_estimate_sequence"] = estimates
        row["_audit_event_map_issues"] = issues


def inspect_run(
    runtime_parent: Path, spec_key: str, source_repository: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = RUN_SPECS[spec_key]
    run_dir = runtime_parent / "ess-research" / "issue133" / "runs" / spec["run_id"]
    archive_path = run_dir / "raw-observations.jsonl.gz"
    manifest_path = run_dir / "run-manifest.json"
    catalog_path = run_dir / "catalog-audit.json"
    preflight_path = run_dir / "input-preflight.json"
    environment_path = run_dir / "environment.json"
    for path in (archive_path, manifest_path, catalog_path, preflight_path, environment_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog_doc = json.loads(catalog_path.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    source = EXECUTION_SOURCE[spec_key]
    if manifest.get("source_commit_before_test") != source["commit"]:
        raise ValueError(f"{spec_key}: frozen execution source commit mismatch")
    protocol_bytes = git_show_bytes(source_repository, source["commit"], source["protocol"])
    runner_bytes = git_show_bytes(source_repository, source["commit"], source["runner"])
    observed_protocol_sha = sha256_bytes(protocol_bytes)
    if observed_protocol_sha != manifest.get("protocol_sha256"):
        raise ValueError(f"{spec_key}: execution protocol does not match run manifest")
    source_checks = {
        "execution_source_commit": source["commit"],
        "protocol_path_at_execution_commit": source["protocol"],
        "protocol_sha256_from_git_object": observed_protocol_sha,
        "protocol_sha256_matches_run_manifest": True,
        "runner_path_at_execution_commit": source["runner"],
        "runner_sha256_from_git_object": sha256_bytes(runner_bytes),
    }
    actual_sha = sha256_file(archive_path)
    if actual_sha != spec["expected_sha256"]:
        raise ValueError(f"{spec_key}: archive SHA mismatch: {actual_sha}")
    manifest_sha = manifest.get("raw_observations_sha256")
    if manifest_sha is None and manifest.get("raw_archive"):
        manifest_sha = manifest["raw_archive"].get("sha256")
    if manifest_sha is None and manifest.get("raw_member"):
        manifest_sha = manifest["raw_member"].get("raw_member_sha256")
    if manifest_sha != actual_sha:
        raise ValueError(f"{spec_key}: manifest archive SHA does not match bytes")
    compressed = archive_path.read_bytes()
    members = split_gzip_members(compressed)
    if len(members) != len(spec["expected_configs"]):
        raise ValueError(f"{spec_key}: unexpected gzip member count {len(members)}")
    arm_docs = catalog_arms(catalog_doc)
    arms_in_manifest = manifest.get("arms")
    if isinstance(arms_in_manifest, list):
        metadata_by_config = {
            item["configuration_id"]: item for item in arms_in_manifest
        }
    else:
        only_config = (
            catalog_doc.get("configuration_id")
            or spec["expected_configs"][0]
        )
        metadata_by_config = {only_config: manifest}
    manifest_input = manifest.get("input_identity", {})
    manifest_sample = manifest_input.get("sample_identity", {})
    input_identity_consistency = {}
    for key in (
        "dataset",
        "query_count",
        "csv_sha256",
        "query_ids_sha256",
        "test_truth_canonical_sha256",
        "rendered_test_sql_sha256",
        "candidate_universe_sha256",
        "order_sample_sha256",
    ):
        if key in manifest_input and key in preflight:
            input_identity_consistency[key] = manifest_input[key] == preflight[key]
    if manifest_sample and preflight.get("sample_identity"):
        input_identity_consistency["sample_sha256"] = (
            manifest_sample.get("sha256")
            == preflight["sample_identity"].get("sha256")
        )
    identities: list[dict[str, Any]] = []
    recomputed: dict[str, Any] = {}
    arm_by_configuration: dict[str, dict[str, Any]] = {}
    member_reports: list[dict[str, Any]] = []
    config_ids_seen: list[str] = []
    manifest_catalog_consistency: dict[str, Any] = {}
    for i, member in enumerate(members):
        descriptor = descriptor_for(spec_key, manifest, i)
        for key in ("offset", "bytes", "sha256"):
            if member[key] != descriptor[key]:
                raise ValueError(
                    f"{spec_key}: gzip member {i} {key} mismatch "
                    f"{member[key]} != {descriptor[key]}"
                )
        if spec_key == "forest10_b5":
            rows = parse_member_records(member["payload"])
            if not rows:
                raise ValueError("Forest10 B5 archive member is empty")
            config_id = rows[0].get("configuration_id")
        else:
            config_id = expected_config_for(spec_key, manifest, i)
            rows = parse_member_records(member["payload"])
        if config_id not in spec["expected_configs"]:
            raise ValueError(f"{spec_key}: unexpected configuration ID {config_id}")
        config_ids_seen.append(config_id)
        cat = arm_docs.get(config_id)
        if cat is None:
            raise ValueError(f"{spec_key}: missing catalog audit for {config_id}")
        execution_metadata = metadata_by_config.get(config_id, manifest)
        comparisons = {}
        for meta_key, catalog_key in (
            ("create_count", "create_count"),
            ("analyze_count", "analyze_count"),
            ("sample_sha256", "sample_sha256"),
            ("ordinary_stats_sha256", "ordinary_stats_sha256"),
            ("catalog_fingerprint_sha256", "catalog_fingerprint_sha256"),
            ("catalog_oid_order_candidate_ids", "catalog_oid_order_candidate_ids"),
            ("create_statement_candidate_ids", "create_statement_candidate_ids"),
        ):
            if meta_key in execution_metadata and catalog_key in cat:
                comparisons[meta_key] = (
                    execution_metadata[meta_key] == cat[catalog_key]
                )
        # Some audit formats represent target counts under different keys.
        if "target_count" in execution_metadata and "target_count" in cat:
            comparisons["target_count"] = (
                execution_metadata["target_count"] == cat["target_count"]
            )
        if "statistics_target_count" in execution_metadata and "statistics_target_count" in cat:
            comparisons["statistics_target_count"] = (
                execution_metadata["statistics_target_count"]
                == cat["statistics_target_count"]
            )
        manifest_catalog_consistency[config_id] = comparisons
        oid_map, candidate_to_oid = make_oid_map(cat)
        candidates = set(candidate_to_oid)
        remap_records(rows, oid_map, candidates)
        raw_config_id = (
            f"forest10-{config_id}" if spec_key == "forest10_all" else config_id
        )
        per_config = validate_records(
            rows, config_id, expected_row_configuration_id=raw_config_id
        )
        per_config["mcv_selection_event_candidate_frequency"] = dict(
            Counter(
                candidate
                for sequence in per_config["selection_sequences"]
                for candidate in sequence
            )
        )
        per_config["mcv_selection_event_query_frequency"] = dict(
            Counter(
                candidate
                for sequence in per_config["selection_sequences"]
                for candidate in set(sequence)
            )
        )
        per_config["mcv_estimate_event_candidate_frequency"] = dict(
            Counter(
                candidate
                for sequence in per_config["estimate_sequences"]
                for candidate in sequence
            )
        )
        per_config["diagnostic_event_mapped_queries"] = sum(
            1 for row in rows if row["_audit_selection_sequence"]
        )
        per_config["diagnostic_event_mapping_issue_count"] = sum(
            len(row["_audit_event_map_issues"]) for row in rows
        )
        per_config["catalog_check"] = verify_catalog_arm(
            cat, config_id, execution_metadata
        )
        arm_by_configuration[config_id] = per_config
        member_reports.append(
            {
                "index": i,
                "offset": member["offset"],
                "compressed_bytes": member["bytes"],
                "compressed_sha256": member["sha256"],
                "gzip_eof_crc_checked": member["eof"],
                "row_count": len(rows),
                "configuration_id": config_id,
            }
        )
        identity = {
            "dataset": preflight["dataset"],
            "csv_sha256": preflight.get("csv_sha256"),
            "sample_sha256": preflight.get("sample_identity", {}).get("sha256"),
            "query_ids_sha256": preflight.get("query_ids_sha256"),
            "test_truth_canonical_sha256": preflight.get("test_truth_canonical_sha256"),
            "rendered_test_sql_sha256": preflight.get("rendered_test_sql_sha256"),
            "source_csv_sha256": preflight.get("source_csv_sha256"),
        }
        if per_config["query_ids_sha256"] != identity["query_ids_sha256"]:
            raise ValueError(f"{config_id}: raw query-ID hash mismatches preflight")
        if per_config["test_truth_canonical_sha256"] != identity["test_truth_canonical_sha256"]:
            raise ValueError(f"{config_id}: raw truth hash mismatches preflight")
        identities.append(identity)
        recomputed[config_id] = per_config
    if config_ids_seen != spec["expected_configs"]:
        raise ValueError(f"{spec_key}: configuration identity/order mismatch {config_ids_seen}")
    if len(identities) > 1 and any(item != identities[0] for item in identities[1:]):
        raise ValueError(f"{spec_key}: input identities differ across arms")
    if sum(m["row_count"] for m in member_reports) != spec["expected_rows"]:
        raise ValueError(f"{spec_key}: aggregate row count mismatch")

    catalog_checks = {
        configuration_id: item["catalog_check"]
        for configuration_id, item in arm_by_configuration.items()
    }
    control_comparisons: dict[str, Any] = {}
    configs = list(arm_by_configuration)
    for left_id, right_id in zip(configs, configs[1:]):
        left, right = catalog_checks[left_id], catalog_checks[right_id]
        left_catalog = arm_docs[left_id]["catalog"]
        right_catalog = arm_docs[right_id]["catalog"]
        left_map = {item["candidate_id"]: item for item in left_catalog}
        right_map = {item["candidate_id"]: item for item in right_catalog}
        shared = sorted(set(left_map) & set(right_map))
        content_equal = all(
            (
                left_map[c].get("payload_state"),
                left_map[c].get("mcv_item_count"),
                left_map[c].get("mcv_content_sha256"),
                left_map[c].get("statistics_target"),
                left_map[c].get("attnames"),
                left_map[c].get("kinds"),
            )
            == (
                right_map[c].get("payload_state"),
                right_map[c].get("mcv_item_count"),
                right_map[c].get("mcv_content_sha256"),
                right_map[c].get("statistics_target"),
                right_map[c].get("attnames"),
                right_map[c].get("kinds"),
            )
            for c in shared
        )
        control_comparisons[f"{left_id}__vs__{right_id}"] = {
            "shared_candidate_count": len(shared),
            "candidate_id_keyed_mcv_state_itemcount_fingerprint_target_attrs_match": content_equal,
            "sample_sha256_equal": left["sample_sha256"] == right["sample_sha256"],
            "ordinary_stats_sha256_equal": (
                left["ordinary_stats_sha256"] == right["ordinary_stats_sha256"]
            ),
        }

    candidate_catalogs = {}
    arm_metadata = {}
    for config_id, cat in arm_docs.items():
        candidate_catalogs[config_id] = {
            item["candidate_id"]: {
                key: item.get(key)
                for key in (
                    "oid", "statistic_name", "attnames", "kinds",
                    "statistics_target", "payload_state", "mcv_item_count",
                    "mcv_content_sha256",
                )
            }
            for item in cat.get("catalog", [])
        }
        meta = metadata_by_config.get(config_id, manifest)
        arm_metadata[config_id] = {
            "create_count": meta.get("create_count", cat.get("create_count")),
            "target_count": meta.get(
                "target_count", meta.get(
                    "statistics_target_count",
                    cat.get("target_count", cat.get("statistics_target_count")),
                )
            ),
            "analyze_count": meta.get("analyze_count", cat.get("analyze_count")),
            "sample_sha256": meta.get("sample_sha256", cat.get("sample_sha256")),
            "ordinary_stats_sha256": meta.get(
                "ordinary_stats_sha256", cat.get("ordinary_stats_sha256")
            ),
            "table_logical_identity": meta.get(
                "table_logical_identity", cat.get("table_logical_identity")
            ),
            "requested_create_order_candidate_ids": cat.get(
                "create_statement_candidate_ids",
                meta.get("b5_create_order", meta.get("create_statement_candidate_ids", [])),
            ),
            "actual_oid_order_candidate_ids": cat.get("catalog_oid_order_candidate_ids", []),
            "permutation_sha256": meta.get(
                "permutation_sha256", meta.get("b5_order_sha256")
            ),
        }
    archive_report = {
        "run_id": spec["run_id"],
        "dataset": spec["dataset"],
        "archive_path_relative_to_runtime_parent": (
            Path("ess-research") / "issue133" / "runs" / spec["run_id"] / archive_path.name
        ).as_posix(),
        "archive_bytes": len(compressed),
        "expected_archive_sha256": spec["expected_sha256"],
        "observed_archive_sha256": actual_sha,
        "archive_sha256_matches_expected": actual_sha == spec["expected_sha256"],
        "gzip_member_count": len(members),
        "gzip_members": member_reports,
        "aggregate_valid_record_count": sum(m["row_count"] for m in member_reports),
        "expected_record_count": spec["expected_rows"],
        "manifest_status_preserved": manifest.get("status"),
        "execution_source_commit": manifest.get("source_commit_before_test"),
        "protocol_sha256": manifest.get("protocol_sha256"),
        "execution_source_checks": source_checks,
        "postgresql_version": manifest.get("postgresql_build", {}).get("version"),
        "postgresql_binary_sha256": manifest.get("postgresql_build", {}).get("binary_sha256"),
        "postgresql_source_commit": manifest.get("postgresql_build", {}).get("source_commit"),
        "numpy_version_recorded": manifest.get("numpy_version")
        or environment.get("numpy_version"),
        "input_identity": identities[0] if identities else {},
        "run_manifest_vs_input_preflight_identity_checks": input_identity_consistency,
        "run_manifest_vs_catalog_audit_checks": manifest_catalog_consistency,
        "catalog_checks": catalog_checks,
        "candidate_catalogs_by_stable_candidate_id": candidate_catalogs,
        "arm_metadata": arm_metadata,
        "cross_arm_control_comparisons": control_comparisons,
        "raw_diagnostics_status_counts": {
            config: data["diagnostics_status_counts_preserved_from_raw"]
            for config, data in recomputed.items()
        },
        "plan_rows_integrity_status_counts": {
            config: data["plan_rows_integrity_status_counts"]
            for config, data in recomputed.items()
        },
        "diagnostics_integrity_status_counts": {
            config: data["diagnostics_integrity_status_counts"]
            for config, data in recomputed.items()
        },
        "extension_diagnostics_status_counts": {
            config: data["extension_diagnostics_status_counts"]
            for config, data in recomputed.items()
        },
        "candidate_id_attribution_status_counts": {
            config: data["candidate_id_attribution_status_counts"]
            for config, data in recomputed.items()
        },
        "unknown_stat_oid_counts": {
            config: data["unknown_stat_oid_count"]
            for config, data in recomputed.items()
        },
    }
    return archive_report, recomputed


def metric_json(configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        config: {
            key: value
            for key, value in data.items()
            if key
            not in {
                "plan_rows",
                "qerrors",
                "query_ids",
                "selection_sequences",
                "estimate_sequences",
            }
        }
        for config, data in configs.items()
    }


def candidate_usage(configs: dict[str, dict[str, Any]], config_id: str) -> dict[str, Any]:
    data = configs[config_id]
    return {
        "selection_event_count_by_candidate": data["mcv_selection_event_candidate_frequency"],
        "queries_using_candidate_count": data["mcv_selection_event_query_frequency"],
        "estimate_event_count_by_candidate": data["mcv_estimate_event_candidate_frequency"],
    }


def build_outputs(
    archive_reports: dict[str, Any],
    all_configs: dict[str, dict[str, Any]],
    frozen_orders: dict[str, Any],
    frozen_resources: dict[str, Any],
    frozen_orders_path: Path,
    frozen_resources_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    forest01 = all_configs["forest10-all-random-01"]
    forest02 = all_configs["forest10-all-random-02"]
    forestb5 = all_configs["forest10-b5-nominal-matched-random01"]
    dmv01 = all_configs["dmv11-all-random-01"]
    dmv02 = all_configs["dmv11-all-random-02"]
    dmvb5 = all_configs["dmv11-b5-nominal-matched"]
    pairs = {
        "forest10_all_random01_vs_random02": compare_pair(
            forest01, forest02, "forest10-all-random-01", "forest10-all-random-02"
        ),
        "forest10_all_random01_vs_matched_b5": compare_pair(
            forest01, forestb5, "forest10-all-random-01", "forest10-b5-nominal-matched-random01"
        ),
        "dmv11_all_random02_vs_random01": compare_pair(
            dmv02, dmv01, "dmv11-all-random-02", "dmv11-all-random-01"
        ),
        "dmv11_all_random01_vs_matched_b5": compare_pair(
            dmv01, dmvb5, "dmv11-all-random-01", "dmv11-b5-nominal-matched"
        ),
    }
    b5_candidates = set(candidate_usage(all_configs, "dmv11-b5-nominal-matched")[
        "queries_using_candidate_count"
    ])
    all_candidates = set(candidate_usage(all_configs, "dmv11-all-random-01")[
        "queries_using_candidate_count"
    ])
    all_only = all_candidates - b5_candidates
    all_only_events = sum(
        count
        for candidate, count in candidate_usage(all_configs, "dmv11-all-random-01")[
            "selection_event_count_by_candidate"
        ].items()
        if candidate not in b5_candidates
    )
    dmv_all_only_queries = sum(
        1
        for sequence in dmv01["selection_sequences"]
        if any(candidate not in b5_candidates for candidate in sequence)
    )
    resource_cases = {
        item["case_id"]: item for item in frozen_resources["cases"]
    }
    frozen_b5 = {
        "forest10": resource_cases["forest10-nominal-b5"]["selected_ids"],
        "dmv11": resource_cases["dmv11-nominal-b5"]["selected_ids"],
    }
    frozen_order_sets: dict[str, dict[str, Any]] = {}
    for dataset in ("forest10", "dmv11"):
        by_order = {
            item["order_id"]: item for item in frozen_orders["datasets"][dataset]
        }
        frozen_order_sets[dataset] = {}
        for order_id in ("random-01", "random-02"):
            order = by_order[order_id]["permutation"]
            expected_size = 45 if dataset == "forest10" else 55
            if len(order) != expected_size or len(set(order)) != expected_size:
                raise ValueError(f"{dataset} {order_id}: malformed frozen permutation")
            if sha256_json(order) != by_order[order_id]["permutation_sha256"]:
                raise ValueError(f"{dataset} {order_id}: frozen order hash mismatch")
            frozen_order_sets[dataset][order_id] = {
                "permutation": order,
                "permutation_sha256": by_order[order_id]["permutation_sha256"],
            }

    def cross_arm_control(
        left_run: str, left_id: str, right_run: str, right_id: str, shared_ids: set[str]
    ) -> dict[str, Any]:
        left_report, right_report = archive_reports[left_run], archive_reports[right_run]
        left_meta = left_report["arm_metadata"][left_id]
        right_meta = right_report["arm_metadata"][right_id]
        left_catalog = left_report["candidate_catalogs_by_stable_candidate_id"][left_id]
        right_catalog = right_report["candidate_catalogs_by_stable_candidate_id"][right_id]
        common = sorted(shared_ids)
        content_equal = all(
            left_catalog.get(candidate) is not None
            and right_catalog.get(candidate) is not None
            and (
                left_catalog[candidate].get("payload_state"),
                left_catalog[candidate].get("mcv_item_count"),
                left_catalog[candidate].get("mcv_content_sha256"),
                left_catalog[candidate].get("statistics_target"),
                left_catalog[candidate].get("attnames"),
                left_catalog[candidate].get("kinds"),
            )
            == (
                right_catalog[candidate].get("payload_state"),
                right_catalog[candidate].get("mcv_item_count"),
                right_catalog[candidate].get("mcv_content_sha256"),
                right_catalog[candidate].get("statistics_target"),
                right_catalog[candidate].get("attnames"),
                right_catalog[candidate].get("kinds"),
            )
            for candidate in common
        )
        identity_fields = (
            "csv_sha256",
            "sample_sha256",
            "query_ids_sha256",
            "test_truth_canonical_sha256",
            "rendered_test_sql_sha256",
        )
        identities_equal = all(
            left_report["input_identity"].get(field)
            == right_report["input_identity"].get(field)
            for field in identity_fields
        )
        return {
            "shared_candidate_count": len(common),
            "stable_candidate_id_keyed_mcv_state_itemcount_content_target_and_attributes_match": content_equal,
            "full_table_sample_test_ids_truth_and_rendered_sql_identity_match": identities_equal,
            "sample_sha256_equal": left_meta.get("sample_sha256")
            == right_meta.get("sample_sha256"),
            "ordinary_stats_sha256_equal": left_meta.get("ordinary_stats_sha256")
            == right_meta.get("ordinary_stats_sha256"),
            "postgresql_binary_sha256_equal": left_report.get("postgresql_binary_sha256")
            == right_report.get("postgresql_binary_sha256"),
        }

    # Keep run IDs tied to RUN_SPECS rather than naming aliases.
    forest_run = RUN_SPECS["forest10_all"]["run_id"]
    forest_b5_run = RUN_SPECS["forest10_b5"]["run_id"]
    dmv_run = RUN_SPECS["dmv11"]["run_id"]
    forest_b5_id = "forest10-b5-nominal-matched-random01"
    dmv_b5_id = "dmv11-b5-nominal-matched"
    forest_b5_order = archive_reports[forest_b5_run]["arm_metadata"][forest_b5_id][
        "actual_oid_order_candidate_ids"
    ]
    dmv_b5_order = archive_reports[dmv_run]["arm_metadata"][dmv_b5_id][
        "actual_oid_order_candidate_ids"
    ]
    forest_all01_order = archive_reports[forest_run]["arm_metadata"][
        "forest10-all-random-01"
    ]["actual_oid_order_candidate_ids"]
    forest_all02_order = archive_reports[forest_run]["arm_metadata"][
        "forest10-all-random-02"
    ]["actual_oid_order_candidate_ids"]
    dmv_all01_order = archive_reports[dmv_run]["arm_metadata"][
        "dmv11-all-random-01"
    ]["actual_oid_order_candidate_ids"]
    dmv_all02_order = archive_reports[dmv_run]["arm_metadata"][
        "dmv11-all-random-02"
    ]["actual_oid_order_candidate_ids"]

    def projected(order: list[str], subset: list[str]) -> list[str]:
        selected = set(subset)
        return [candidate for candidate in order if candidate in selected]

    forest01_expected = frozen_order_sets["forest10"]["random-01"]["permutation"]
    forest02_expected = frozen_order_sets["forest10"]["random-02"]["permutation"]
    dmv01_expected = frozen_order_sets["dmv11"]["random-01"]["permutation"]
    dmv02_expected = frozen_order_sets["dmv11"]["random-02"]["permutation"]
    design_checks = {
        "frozen_order_file_sha256": sha256_file(frozen_orders_path),
        "frozen_resource_manifest_sha256": sha256_file(frozen_resources_path),
        "forest10_nominal_b5_ids": frozen_b5["forest10"],
        "dmv11_nominal_b5_ids": frozen_b5["dmv11"],
        "forest10_random01_order_matches_frozen": forest_all01_order == forest01_expected,
        "forest10_random02_order_matches_frozen": forest_all02_order == forest02_expected,
        "dmv11_random01_order_matches_frozen": dmv_all01_order == dmv01_expected,
        "dmv11_random02_order_matches_frozen": dmv_all02_order == dmv02_expected,
        "forest10_b5_ids_match_issue99_frozen_nominal": set(forest_b5_order)
        == set(frozen_b5["forest10"]),
        "dmv11_b5_ids_match_issue99_frozen_nominal": set(dmv_b5_order)
        == set(frozen_b5["dmv11"]),
        "forest10_b5_order_matches_all_random01_projection": forest_b5_order
        == projected(forest_all01_order, frozen_b5["forest10"]),
        "forest10_all_random02_projection_matches_b5": projected(
            forest_all02_order, frozen_b5["forest10"]
        )
        == forest_b5_order,
        "dmv11_b5_order_matches_all_random01_projection": dmv_b5_order
        == projected(dmv_all01_order, frozen_b5["dmv11"]),
        "dmv11_all_random02_projection_matches_b5": projected(
            dmv_all02_order, frozen_b5["dmv11"]
        )
        == dmv_b5_order,
    }
    if not all(
        design_checks[key]
        for key in (
            "forest10_random01_order_matches_frozen",
            "forest10_random02_order_matches_frozen",
            "dmv11_random01_order_matches_frozen",
            "dmv11_random02_order_matches_frozen",
            "forest10_b5_ids_match_issue99_frozen_nominal",
            "dmv11_b5_ids_match_issue99_frozen_nominal",
            "forest10_b5_order_matches_all_random01_projection",
            "dmv11_b5_order_matches_all_random01_projection",
        )
    ):
        raise ValueError("one or more frozen order/resource identity checks failed")
    cross_run_controls = {
        "forest10_all01_vs_all02": cross_arm_control(
            forest_run,
            "forest10-all-random-01",
            forest_run,
            "forest10-all-random-02",
            set(forest01_expected),
        ),
        "forest10_all01_vs_matched_b5": cross_arm_control(
            forest_run,
            "forest10-all-random-01",
            forest_b5_run,
            forest_b5_id,
            set(frozen_b5["forest10"]),
        ),
        "forest10_all02_vs_matched_b5": cross_arm_control(
            forest_run,
            "forest10-all-random-02",
            forest_b5_run,
            forest_b5_id,
            set(frozen_b5["forest10"]),
        ),
        "dmv11_all01_vs_all02": cross_arm_control(
            dmv_run,
            "dmv11-all-random-01",
            dmv_run,
            "dmv11-all-random-02",
            set(dmv01_expected),
        ),
        "dmv11_all01_vs_matched_b5": cross_arm_control(
            dmv_run,
            "dmv11-all-random-01",
            dmv_run,
            dmv_b5_id,
            set(frozen_b5["dmv11"]),
        ),
        "dmv11_all02_vs_matched_b5": cross_arm_control(
            dmv_run,
            "dmv11-all-random-02",
            dmv_run,
            dmv_b5_id,
            set(frozen_b5["dmv11"]),
        ),
    }
    recomputation = {
        "metric_definition": {
            "plan_rows_rounding": "int(numpy.round(1.0 * Plan Rows))",
            "qerror_zero_cases": {
                "estimate_zero_truth_zero": 1.0,
                "estimate_zero_truth_positive": "truth",
                "truth_zero_estimate_positive": "estimate",
            },
            "summary": "NumPy float64 median, percentile(95), percentile(99), mean, max",
            "numpy_version_used": np.__version__,
            "qerror_source_fields": ["estimate_plan_rows", "true_cardinality"],
            "stored_qerror_used_as_input": False,
        },
        "configurations": metric_json(all_configs),
        "paired_comparisons": pairs,
        "frozen_design_checks": design_checks,
        "cross_run_physical_control_checks": cross_run_controls,
        "dmv11_all_random01_vs_b5_candidate_usage": {
            "all_only_candidates_selected_in_queries": dmv_all_only_queries,
            "all_only_selection_events": all_only_events,
            "shared_five_candidate_ids": sorted(b5_candidates),
            "all_random01": candidate_usage(all_configs, "dmv11-all-random-01"),
            "b5": candidate_usage(all_configs, "dmv11-b5-nominal-matched"),
        },
        "forest10_b5_diagnostic_limitation": {
            "manifest_status": "INCOMPLETE",
            "raw_diagnostics_status_counts": forestb5["diagnostics_status_counts_preserved_from_raw"],
            "raw_events_offline_mapped_by_same_arm_catalog": True,
            "original_diagnostics_completeness_upgraded": False,
            "mapped_event_issue_count": forestb5["diagnostic_event_mapping_issue_count"],
        },
        "tolerance_checks": {
            "expected_p95": {
                "forest10-all-random-01": 15.0,
                "forest10-all-random-02": 15.0,
                "forest10-b5-nominal-matched-random01": 14.0,
                "dmv11-all-random-01": 57.6052273,
                "dmv11-all-random-02": 67.525,
                "dmv11-b5-nominal-matched": 36.0044444,
            },
            "absolute_tolerance": 1e-6,
        },
        "physical_control_evidence_is_manifest_and_catalog_audit_reported": True,
        "blocker_causality_established": False,
    }
    for config_id, expected in recomputation["tolerance_checks"]["expected_p95"].items():
        actual = all_configs[config_id]["metric_summary"]["p95"]
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError(f"{config_id}: P95 differs from expected {expected}: {actual}")
    return archive_reports, recomputation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-parent",
        type=Path,
        default=Path(os.environ["ESS_RUNTIME_PARENT"]) if os.environ.get("ESS_RUNTIME_PARENT") else None,
        required=False,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-orders", type=Path, required=True)
    parser.add_argument("--frozen-resources", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    args = parser.parse_args()
    if args.runtime_parent is None:
        parser.error("--runtime-parent or ESS_RUNTIME_PARENT is required")
    archive_reports: dict[str, Any] = {}
    all_configs: dict[str, dict[str, Any]] = {}
    frozen_orders = json.loads(args.frozen_orders.read_text(encoding="utf-8"))
    frozen_resources = json.loads(args.frozen_resources.read_text(encoding="utf-8"))
    frozen_file_checks = {}
    supplied_files = {
        "all-order-sample-v1.json": args.frozen_orders,
        "frozen-train-resources-issue96-v1.json": args.frozen_resources,
    }
    for filename, (git_path, expected_sha) in FROZEN_SOURCE_FILES.items():
        source_bytes = git_show_bytes(
            args.source_repo, FROZEN_SOURCE_COMMIT, git_path
        )
        source_sha = sha256_bytes(source_bytes)
        if source_sha != expected_sha:
            raise ValueError(f"{filename}: frozen Git object SHA mismatch")
        supplied_path = supplied_files.get(filename)
        supplied_sha = sha256_file(supplied_path) if supplied_path else None
        if supplied_path and supplied_sha != source_sha:
            raise ValueError(f"{filename}: supplied file differs from frozen Git object")
        frozen_file_checks[filename] = {
            "path_at_m0_commit": git_path,
            "source_commit": FROZEN_SOURCE_COMMIT,
            "sha256": source_sha,
            "matches_expected_sha256": True,
            "supplied_file_matches_git_object": (
                supplied_sha == source_sha if supplied_path else None
            ),
        }
    for key in RUN_SPECS:
        report, configs = inspect_run(args.runtime_parent, key, args.source_repo)
        archive_reports[RUN_SPECS[key]["run_id"]] = report
        all_configs.update(configs)
    archive_output, recomputation = build_outputs(
        archive_reports,
        all_configs,
        frozen_orders,
        frozen_resources,
        args.frozen_orders,
        args.frozen_resources,
    )
    recomputation["frozen_source_file_checks"] = frozen_file_checks
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "raw-archive-verification.json").write_text(
        json.dumps(archive_output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "independent-recomputation.json").write_text(
        json.dumps(recomputation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("archive verification: PASS")
    for run_id, run in archive_output.items():
        print(
            f"{run_id}: sha256={run['observed_archive_sha256']} "
            f"records={run['aggregate_valid_record_count']} members={run['gzip_member_count']} "
            f"manifest_status={run['manifest_status_preserved']}"
        )
    print("independent metrics: PASS")
    for config_id, row in recomputation["configurations"].items():
        metric = row["metric_summary"]
        print(
            f"{config_id}: n={row['valid_query_count']} "
            f"P50={metric['p50']:.12g} P95={metric['p95']:.12g} "
            f"P99={metric['p99']:.12g} mean={metric['mean']:.12g}"
        )
    print("pairwise:")
    for key, pair in recomputation["paired_comparisons"].items():
        print(
            f"{key}: dP95={pair['p95_left_minus_right']:.12g} "
            f"plan={pair['plan_rows_different_queries']} "
            f"qerror={pair['qerror_different_queries']} "
            f"sequence={pair['selection_sequence_different_queries']} "
            f"better/worse/equal={pair['left_qerror_better_queries']}/"
            f"{pair['left_qerror_worse_queries']}/{pair['qerror_equal_queries']}"
        )


if __name__ == "__main__":
    main()
