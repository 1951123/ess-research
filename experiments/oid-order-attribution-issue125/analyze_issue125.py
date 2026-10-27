#!/usr/bin/env python3
"""Read-only query attribution over frozen Issue #105/#107 observations."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
from itertools import combinations
import json
import math
import os
from pathlib import Path
import zlib
from typing import Any, Iterator

import numpy as np

import run_issue101 as issue101
import run_issue105 as issue105
import run_issue107 as issue107


HERE = Path(__file__).resolve().parent
RUN_IDS = {
    "issue105": (105, "20261025T130222Z-issue105-official-v2"),
    "issue107_parent": (107, "20261026T055503Z-issue107-sampled-v1"),
    "issue107_continuation": (107, "20261026T062137Z-issue107-pess3-cont-v1"),
}
ARCHIVE_SHA256 = {
    "issue105": "ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2",
    "issue107_parent": "d90b4600754fe2dedeb1e7dfc1ccfe75c2de325d630bca565150d1c8218cd767",
    "issue107_continuation": "27e0a437f5eda7a87be712fe9850bfa939b07df03eed84169b27868a34707ea5",
}
MANIFEST_SHA256 = {
    "issue107_parent": "360af848afa93d54a958348981c5764dc643a9fccf0ff4e1b30eaf925eec44e3",
    "issue107_continuation": "639b6c30e2a168d13077a2d3866d598da8612f780285c34b3c6f142748e3d549",
}
COMBINED_ANALYSIS_SHA256 = "7861f15ff62978a23f3a76307afa67fa8bceaf62a75ceacc43ff3c534a67ea3e"
MCV_VALUE_FIELDS = ("simple_sel", "mcv_sel", "mcv_basesel", "mcv_totalsel", "stat_sel")


@dataclass
class OrderData:
    record: dict[str, Any]
    qerrors: np.ndarray
    selection_sequences: list[tuple[str, ...]]
    estimate_sequences: list[tuple[str, ...]]
    estimate_values: list[tuple[tuple[str, tuple[Any, ...]], ...]]
    estimate_value_signatures: list[tuple[tuple[str, str], ...]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def same_json_value(left: Any, right: Any) -> bool:
    """Compare serialized numeric values exactly, without tolerance masking."""
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(same_json_value(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_json_value(a, b) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and not isinstance(left, bool):
        return isinstance(right, (int, float)) and not isinstance(right, bool) and float(left) == float(right)
    return left == right


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if not same_json_value(actual, expected):
        raise ValueError(f"{label} differs from the frozen identity or recomputation")


def iter_member_rows(path: Path, offset: int, byte_count: int) -> Iterator[dict[str, Any]]:
    """Decode one exact gzip member incrementally and reject trailing bytes."""
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buffered = bytearray()
    with path.open("rb") as stream:
        stream.seek(offset)
        remaining = byte_count
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block:
                raise ValueError(f"compressed member is truncated at offset {offset}")
            remaining -= len(block)
            buffered.extend(decoder.decompress(block))
            while True:
                newline = buffered.find(b"\n")
                if newline < 0:
                    break
                line = bytes(buffered[:newline])
                del buffered[: newline + 1]
                if not line:
                    raise ValueError("JSONL member contains a blank record")
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("JSONL row is not an object")
                yield value
        buffered.extend(decoder.flush())
    if buffered:
        if not buffered.endswith(b"\n"):
            raise ValueError("JSONL member has an unterminated final row")
        line = bytes(buffered[:-1])
        if line:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("JSONL row is not an object")
            yield value
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError(f"gzip member boundary is invalid at offset {offset}")


def catalog_oid_map(arm: dict[str, Any]) -> dict[int, str]:
    catalog = arm.get("catalog_oid_order", [])
    oids = [row.get("oid") for row in catalog]
    if any(isinstance(oid, bool) or not isinstance(oid, int) for oid in oids) or len(set(oids)) != len(oids):
        raise ValueError("catalog OID map is missing or contains duplicate/noninteger OIDs")
    return {row["oid"]: row["candidate_id"] for row in catalog}


def validate_physical_identity(
    arm: dict[str, Any], dataset: str, permutation: tuple[str, ...],
    sample_sha256: str, label: str,
) -> dict[int, str]:
    if arm.get("catalog_definition_status") != "PASS" or arm.get("sample_replay_status") != "PASS":
        raise ValueError(f"{label}: catalog or fixed ANALYZE-sample replay did not pass")
    if arm.get("sample_sha256", arm.get("fixed_analyze_sample_sha256")) != sample_sha256:
        raise ValueError(f"{label}: fixed ANALYZE sample hash mismatch")
    oid_map = catalog_oid_map(arm)
    catalog = arm.get("catalog", [])
    candidates = issue101.candidate_map(dataset)
    by_name = {row["statistic_name"]: candidate_id for candidate_id, row in candidates.items()}
    if len(catalog) != len(permutation):
        raise ValueError(f"{label}: catalog object count differs from frozen set size")
    seen_ids = []
    for row in catalog:
        candidate_id = by_name.get(row.get("statistic_name"))
        if candidate_id is None or oid_map.get(row.get("oid")) != candidate_id:
            raise ValueError(f"{label}: catalog name/OID does not resolve to the frozen candidate")
        if (row.get("statistics_target") != 300 or row.get("kinds") != ["m"]
                or row.get("stxkind") != "{m}" or not row.get("mcv_payload_present")
                or not isinstance(row.get("mcv_item_count"), int) or row["mcv_item_count"] <= 0
                or row.get("mcv_content_sha256") != arm.get("mcv_content_sha256_by_candidate", {}).get(candidate_id)):
            raise ValueError(f"{label}: catalog statistics target/MCV payload identity mismatch")
        seen_ids.append(candidate_id)
    if seen_ids != list(permutation) or arm.get("catalog_oid_order_candidate_ids") != list(permutation):
        raise ValueError(f"{label}: physical catalog OID sequence differs from frozen permutation")
    return oid_map


def validate_mcv_row(row: dict[str, Any], oid_map: dict[int, str], selected: set[str], label: str) -> tuple[
    tuple[str, ...], tuple[str, ...], tuple[tuple[str, tuple[Any, ...]], ...]
]:
    if row.get("diagnostics_status") not in issue107.VALID_DIAGNOSTIC_STATUSES:
        raise ValueError(f"{label}: ESS diagnostics status is incomplete")
    event_count = row.get("diagnostics_event_count")
    events = row.get("mcv_events")
    if isinstance(event_count, bool) or not isinstance(event_count, int) or event_count < 0 or not isinstance(events, list):
        raise ValueError(f"{label}: ESS diagnostics event count/list is invalid")
    sequence_numbers: list[int] = []
    selections: list[str] = []
    estimates: list[str] = []
    values: list[tuple[str, tuple[Any, ...]]] = []
    for event in events:
        if event.get("type") not in issue105.MCV_EVENT_TYPES:
            raise ValueError(f"{label}: unknown retained MCV event type")
        oid = event.get("stat_oid")
        candidate_id = event.get("candidate_id")
        if isinstance(oid, bool) or not isinstance(oid, int) or oid_map.get(oid) != candidate_id:
            raise ValueError(f"{label}: MCV event OID does not map to its candidate ID")
        if candidate_id not in selected:
            raise ValueError(f"{label}: MCV event references a statistic outside the frozen set")
        sequence = event.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise ValueError(f"{label}: MCV event lacks an integer sequence number")
        sequence_numbers.append(sequence)
        if event["type"] == "mcv_selection":
            selections.append(candidate_id)
        elif event["type"] == "mcv_estimate":
            estimates.append(candidate_id)
            numbers = tuple(event.get(field) for field in MCV_VALUE_FIELDS)
            for value in numbers:
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                ):
                    raise ValueError(f"{label}: MCV estimate contains a nonfinite value")
            values.append((candidate_id, numbers))
    if sequence_numbers != sorted(sequence_numbers) or len(sequence_numbers) != len(set(sequence_numbers)):
        raise ValueError(f"{label}: MCV event sequence is not strictly ordered")
    if row.get("mcv_selection_ids") != selections or row.get("mcv_estimate_ids") != estimates:
        raise ValueError(f"{label}: MCV sequence projection disagrees with retained events")
    return tuple(selections), tuple(estimates), tuple(values)


def numeric_estimate_signature(values: tuple[tuple[str, tuple[Any, ...]], ...]) -> tuple[tuple[str, str], ...]:
    """Canonicalize numeric estimates by candidate ID, independent of event order."""
    return tuple(sorted(
        (candidate_id, json.dumps(list(fields), separators=(",", ":"), allow_nan=False))
        for candidate_id, fields in values
    ))


def audit_member(
    *,
    source: str,
    root: Path,
    arm: dict[str, Any],
    dataset: str,
    permutation: tuple[str, ...],
    selected_ids: list[str],
    oid_map: dict[int, str],
    truths_by_dataset: dict[str, list[int | None]],
    retain_queries: bool,
) -> tuple[dict[str, Any], OrderData | None, tuple[int, int, str]]:
    raw_path = root / "raw-observations.jsonl.gz"
    member = arm if source == "issue105" else arm.get("raw_member", {})
    offset, byte_count = member.get("raw_member_offset"), member.get("raw_member_bytes")
    member_sha = member.get("raw_member_sha256")
    if (isinstance(offset, bool) or not isinstance(offset, int) or offset < 0
            or isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count <= 0):
        raise ValueError(f"{source}/{dataset}/{permutation}: missing compressed extent")
    with raw_path.open("rb") as stream:
        stream.seek(offset)
        compressed = stream.read(byte_count)
    if len(compressed) != byte_count or hashlib.sha256(compressed).hexdigest() != member_sha:
        raise ValueError(f"{source}/{dataset}/{permutation}: compressed member hash mismatch")

    expected_set = set(selected_ids)
    truth_vector = truths_by_dataset.setdefault(dataset, [None] * 10_000)
    metric_rows: list[dict[str, Any]] = []
    qerrors: list[float] = []
    selection_sequences: list[tuple[str, ...]] = []
    estimate_sequences: list[tuple[str, ...]] = []
    estimate_values: list[tuple[tuple[str, tuple[Any, ...]], ...]] = []
    estimate_value_signatures: list[tuple[tuple[str, str], ...]] = []
    count = 0
    for row in iter_member_rows(raw_path, offset, byte_count):
        index = count
        label = f"{source}/{dataset}/{permutation}/{index}"
        expected_query_id = f"arecel:{dataset}:test:{index:06d}"
        if (index >= 10_000 or row.get("dataset") != dataset or row.get("source_index") != index
        or isinstance(row.get("source_index"), bool) or not isinstance(row.get("source_index"), int)
                or row.get("query_id") != expected_query_id or row.get("status") != "VALID"):
            raise ValueError(f"{label}: Test query identity/status differs")
        if (len(row.get("selected_ids", [])) != len(expected_set)
                or set(row.get("selected_ids", [])) != expected_set):
            raise ValueError(f"{label}: row resource set differs from manifest")
        if source == "issue105":
            expected_order = arm["order"]
            expected_configuration = arm["configuration_id"]
        else:
            expected_order = arm["configuration_id"]
            expected_configuration = f"{dataset}-{arm['configuration_id']}"
        if row.get("order") != expected_order or row.get("configuration_id") != expected_configuration:
            raise ValueError(f"{label}: configuration label differs from manifest")
        truth = row.get("true_cardinality")
        plan_rows = row.get("estimate_plan_rows")
        qerror, rounded = issue101.qerror_for_plan_rows(plan_rows, truth)
        if row.get("estimate_rounded_r1") != rounded or row.get("qerror") != qerror:
            raise ValueError(f"{label}: stored Q-error does not reproduce Issue #101")
        if truth_vector[index] is None:
            truth_vector[index] = truth
        elif truth_vector[index] != truth:
            raise ValueError(f"{label}: truth cardinality differs across configurations")
        selections, estimates, values = validate_mcv_row(row, oid_map, expected_set, label)
        metric_rows.append({
            "status": row["status"],
            "qerror": qerror,
            "estimate_rounded_r1": rounded,
            "true_cardinality": truth,
            "diagnostics_status": row["diagnostics_status"],
            "mcv_events": row["mcv_events"],
            "mcv_selection_ids": list(selections),
            "mcv_estimate_ids": list(estimates),
        })
        if retain_queries:
            qerrors.append(qerror)
            selection_sequences.append(selections)
            estimate_sequences.append(estimates)
            estimate_values.append(values)
            estimate_value_signatures.append(numeric_estimate_signature(values))
        count += 1
    if count != 10_000:
        raise ValueError(f"{source}/{dataset}/{permutation}: only {count} rows; expected 10,000")
    metrics = issue105.metrics_for_rows(metric_rows) if source == "issue105" else issue107._record_metrics(metric_rows)
    if not same_json_value(arm.get("metrics", {}), metrics):
        raise ValueError(f"{source}/{dataset}/{permutation}: recomputed metrics differ from manifest")
    data = None
    if retain_queries:
        record = dict(arm)
        record["metrics"] = metrics
        data = OrderData(
            record=record,
            qerrors=np.asarray(qerrors, dtype=np.float64),
            selection_sequences=selection_sequences,
            estimate_sequences=estimate_sequences,
            estimate_values=estimate_values,
            estimate_value_signatures=estimate_value_signatures,
        )
    return metrics, data, (offset, offset + byte_count, f"{source}/{dataset}/{permutation}")


def validate_member_extents(root: Path, members: list[tuple[int, int, str]]) -> None:
    members.sort()
    path = root / "raw-observations.jsonl.gz"
    size = path.stat().st_size
    if (not members or members[0][0] != 0 or members[-1][1] != size
            or any(left[1] != right[0] for left, right in zip(members, members[1:]))):
        raise ValueError(f"{path}: member extents overlap, leave gaps, or do not cover the archive")


def load_and_check_inputs() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Path], dict[str, str]
]:
    runtime_raw = os.environ.get("ESS_RUNTIME_PARENT")
    if not runtime_raw or not Path(runtime_raw).is_absolute():
        raise RuntimeError("ESS_RUNTIME_PARENT must be set to the configured absolute runtime root")
    runtime = Path(runtime_raw).resolve(strict=True)
    roots = {
        key: runtime / "ess-research" / f"issue{number}" / "runs" / run_id
        for key, (number, run_id) in RUN_IDS.items()
    }
    for path in roots.values():
        if not path.is_dir():
            raise FileNotFoundError(f"required frozen run directory is unavailable: {path}")
    manifests = {key: json_file(path / "run-manifest.json") for key, path in roots.items()}
    manifest_hashes: dict[str, str] = {}
    for key, root in roots.items():
        manifest_path = root / "run-manifest.json"
        raw_path = root / "raw-observations.jsonl.gz"
        manifest_hashes[key] = sha256_file(manifest_path)
        if sha256_file(raw_path) != ARCHIVE_SHA256[key]:
            raise ValueError(f"{key}: frozen raw archive SHA-256 mismatch")
        if manifests[key].get("raw_observations_sha256") != ARCHIVE_SHA256[key]:
            raise ValueError(f"{key}: manifest raw archive SHA-256 mismatch")
        if key in MANIFEST_SHA256 and manifest_hashes[key] != MANIFEST_SHA256[key]:
            raise ValueError(f"{key}: frozen manifest SHA-256 mismatch")
    schedule, schedule_index = issue107.checked_frozen_schedule()
    if len(schedule_index) != 156:
        raise ValueError("checked Issue #107 sample does not contain exactly 156 configurations")
    for key in ("issue107_parent", "issue107_continuation"):
        if (manifests[key].get("frozen_schedule") != schedule
                or manifests[key].get("sample_sha256") != issue107.ISSUE107_SAMPLE_SHA256):
            raise ValueError(f"{key}: embedded schedule/sample differs from checked-in frozen sample")
    if manifests["issue105"].get("run_id") != issue107.ISSUE105_RUN_ID:
        raise ValueError("#105 manifest run ID differs from the pinned #107 reuse source")
    if manifests["issue105"].get("postgresql_source_commit") != issue107.POSTGRESQL_COMMIT:
        raise ValueError("#105 PostgreSQL source commit differs from Issue #107")
    continuation = manifests["issue107_continuation"]
    if continuation.get("parent_run_id") != manifests["issue107_parent"].get("run_id"):
        raise ValueError("#107 continuation names a different parent run")
    parent_manifest_sha = manifest_hashes["issue107_parent"]
    if continuation.get("parent_run_manifest_sha256") != parent_manifest_sha:
        raise ValueError("#107 continuation parent-manifest hash mismatch")
    combined_path = roots["issue107_continuation"] / "combined-analysis.json"
    if sha256_file(combined_path) != COMBINED_ANALYSIS_SHA256:
        raise ValueError("#107 combined official analysis SHA-256 mismatch")
    combined = json_file(combined_path)
    return schedule, schedule_index, combined, roots, manifest_hashes


def manifest_arm_maps(
    schedule: dict[str, Any], schedule_index: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]],
    manifests: dict[str, dict[str, Any]], protocol: dict[str, Any],
) -> tuple[dict[tuple[str, str, tuple[str, ...]], tuple[str, dict[str, Any]]], list[tuple[dict[str, Any], str]]]:
    parent = manifests["issue107_parent"]
    continuation = manifests["issue107_continuation"]
    if (parent.get("status") != "INCOMPLETE" or parent.get("attempted_explain_calls") != 1_440_000
            or parent.get("arms_completed") != 156
            or parent.get("postgresql_build", {}).get("version") != "PostgreSQL 16.14"
            or parent.get("postgresql_build", {}).get("source_commit") != issue107.POSTGRESQL_COMMIT):
        raise ValueError("#107 parent totals differ from its frozen first attempt")
    if (continuation.get("status") != "COMPLETE" or continuation.get("attempted_explain_calls") != 120_000
            or continuation.get("arms_completed") != 12
            or continuation.get("postgresql_build", {}).get("version") != "PostgreSQL 16.14"
            or continuation.get("postgresql_build", {}).get("source_commit") != issue107.POSTGRESQL_COMMIT):
        raise ValueError("#107 continuation totals differ from the authorized 12 arms")
    parent_arms: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for dataset in issue101.DATASETS:
        for arm in parent.get("datasets", {}).get(dataset, {}).get("arms", []):
            key = (dataset, arm.get("policy"), tuple(arm.get("permutation", ())))
            if key in parent_arms:
                raise ValueError(f"#107 parent repeats a configuration identity: {key}")
            frozen = issue107.validate_scheduled_arm(
                schedule_index, dataset=dataset, policy=arm.get("policy"), case_id=arm.get("case_id"),
                resource_ids=arm.get("resource_ids", []), permutation=arm.get("permutation", []),
                selection=arm.get("selection"),
            )
            for field in ("draw_index", "inclusion_probability"):
                if arm.get(field) != frozen.get(field):
                    raise ValueError(f"#107 parent {key}: {field} differs from frozen schedule")
            stratum = next(row for row in schedule["schedules"]
                           if row["dataset"] == dataset and row["policy"] == arm["policy"])
            if arm.get("candidate_map_sha256") != stratum["candidate_map_sha256"]:
                raise ValueError(f"#107 parent {key}: candidate-map identity mismatch")
            if arm.get("status") == "COMPLETE":
                if (arm.get("create_statement_candidate_ids") != arm["permutation"]
                        or arm.get("catalog_oid_order_candidate_ids") != arm["permutation"]):
                    raise ValueError(f"#107 parent {key}: physical OID order differs from frozen order")
                validate_physical_identity(
                    arm, dataset, key[2], protocol["datasets"][dataset]["sample"]["sha256"],
                    f"#107 parent {key}",
                )
            parent_arms[key] = arm
    if set(parent_arms) != set(schedule_index):
        raise ValueError("#107 parent identities do not equal the 156 frozen schedule arms")

    continuation_arms: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for dataset in ("forest10", "power7"):
        for arm in continuation.get("datasets", {}).get(dataset, {}).get("arms", []):
            key = (dataset, arm.get("policy"), tuple(arm.get("permutation", ())))
            if key in continuation_arms:
                raise ValueError(f"#107 continuation repeats a configuration: {key}")
            frozen = issue107.validate_scheduled_arm(
                schedule_index, dataset=dataset, policy=arm.get("policy"), case_id=arm.get("case_id"),
                resource_ids=arm.get("resource_ids", []), permutation=arm.get("permutation", []),
                selection=arm.get("selection"),
            )
            for field in ("draw_index", "inclusion_probability"):
                if arm.get(field) != frozen.get(field):
                    raise ValueError(f"#107 continuation {key}: {field} differs from frozen schedule")
            stratum = next(row for row in schedule["schedules"]
                           if row["dataset"] == dataset and row["policy"] == arm["policy"])
            if (arm.get("candidate_map_sha256") != stratum["candidate_map_sha256"]
                    or arm.get("create_statement_candidate_ids") != arm["permutation"]
                    or arm.get("catalog_oid_order_candidate_ids") != arm["permutation"]
                    or arm.get("status") != "COMPLETE"):
                raise ValueError(f"#107 continuation {key}: physical identity/status mismatch")
            validate_physical_identity(
                arm, dataset, key[2], protocol["datasets"][dataset]["sample"]["sha256"],
                f"#107 continuation {key}",
            )
            continuation_arms[key] = arm
    target_keys = {
        (row["dataset"], row["policy"], tuple(row["permutation"]))
        for row in continuation.get("target_arm_keys", [])
    }
    failed_keys = {key for key, arm in parent_arms.items() if arm.get("status") != "COMPLETE"}
    if len(failed_keys) != 12 or target_keys != failed_keys or set(continuation_arms) != failed_keys:
        raise ValueError("continuation is not the same exact 12 failed pre-EXPLAIN configurations")
    for key in failed_keys:
        arm = parent_arms[key]
        message = arm.get("error", {}).get("message", "")
        if (key[0] not in {"forest10", "power7"} or key[1] != "pess"
                or len(arm.get("resource_ids", [])) != 3
                or arm.get("status") != "CONFIGURATION_INVALID"
                or arm.get("attempted_explain_calls") != 0
                or arm.get("raw_member") is not None
                or "relation does not have exactly the five selected statistics" not in message):
            raise ValueError(f"#107 initial pre-EXPLAIN failure history is inconsistent: {key}")
    return ({key: ("issue107_parent", arm) for key, arm in parent_arms.items() if key not in failed_keys}
            | {key: ("issue107_continuation", arm) for key, arm in continuation_arms.items()},
            [(arm, "issue107_parent") for key, arm in parent_arms.items() if key in failed_keys])


def validate_issue105_fixed(
    schedule: dict[str, Any], protocol: dict[str, Any], manifest: dict[str, Any]
) -> list[tuple[dict[str, Any], str, tuple[str, ...]]]:
    if (manifest.get("status") != "COMPLETE" or manifest.get("attempted_explain_calls") != 80_000
            or manifest.get("source_commit") != issue107.ISSUE105_SOURCE_COMMIT):
        raise ValueError("#105 source run status, call count, or source commit mismatch")
    fixed = {
        (stratum["dataset"], tuple(arm["permutation"])): (stratum, arm)
        for stratum in schedule["schedules"] for arm in stratum["permutations"]
        if arm["selection"] == "fixed"
    }
    rows: list[tuple[dict[str, Any], str, tuple[str, ...]]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for dataset in issue101.DATASETS:
        result = manifest.get("datasets", {}).get(dataset, {})
        configurations = result.get("configurations", [])
        if result.get("status") != "COMPLETE" or len(configurations) != 2:
            raise ValueError(f"#105 {dataset}: expected complete canonical/reverse pair")
        for arm in configurations:
            order = arm.get("catalog_oid_order_candidate_ids", [])
            key = (dataset, tuple(order))
            if key not in fixed or key in seen:
                raise ValueError(f"#105 configuration is outside/repeats the frozen certainty orders: {key}")
            stratum, frozen = fixed[key]
            if (set(arm.get("selected_ids", [])) != set(stratum["resource_ids"])
                    or order != frozen["permutation"]
                    or arm.get("create_statement_candidate_ids") != order
                    or arm.get("sample_sha256") != protocol["datasets"][dataset]["sample"]["sha256"]):
                raise ValueError(f"#105 {dataset}/{arm.get('order')}: set/order/sample identity mismatch")
            oid_map = validate_physical_identity(
                arm, dataset, tuple(order), protocol["datasets"][dataset]["sample"]["sha256"],
                f"#105 {dataset}/{arm.get('order')}",
            )
            selected = list(stratum["resource_ids"])
            rows.append((arm, dataset, tuple(order)))
            arm["_issue125_oid_map"] = oid_map
            arm["_issue125_selected"] = selected
            seen.add(key)
    if len(rows) != 8 or seen != set(fixed):
        raise ValueError("#105 does not contain exactly the eight frozen certainty configurations")
    return rows


def compare_pair(anchor: OrderData, other: OrderData, dataset: str) -> dict[str, Any]:
    n = len(anchor.qerrors)
    if n == 0 or len(other.qerrors) != n:
        raise ValueError("paired order comparison requires a nonempty shared query set")
    counts: Counter[str] = Counter()
    tail_counts: Counter[str] = Counter()
    entrant_queries: Counter[int] = Counter()
    exit_queries: Counter[int] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    anchor_p95 = float(np.percentile(anchor.qerrors, 95))
    other_p95 = float(np.percentile(other.qerrors, 95))
    anchor_tail = anchor.qerrors >= anchor_p95
    other_tail = other.qerrors >= other_p95
    estimate_diag_changed = 0
    for index in range(n):
        left = float(anchor.qerrors[index])
        right = float(other.qerrors[index])
        qclass = "tie" if right == left else "higher" if right > left else "lower"
        sel_changed = anchor.selection_sequences[index] != other.selection_sequences[index]
        est_changed = anchor.estimate_sequences[index] != other.estimate_sequences[index]
        value_changed = anchor.estimate_value_signatures[index] != other.estimate_value_signatures[index]
        any_sequence_changed = sel_changed or est_changed
        counts[f"qerror_{qclass}"] += 1
        counts["selection_sequence_changed"] += sel_changed
        counts["estimate_sequence_changed"] += est_changed
        counts["any_id_sequence_changed"] += any_sequence_changed
        counts["estimate_values_changed"] += value_changed
        counts["id_sequence_changed_qerror_tie"] += any_sequence_changed and qclass == "tie"
        counts["id_sequence_changed_qerror_changed"] += any_sequence_changed and qclass != "tie"
        counts["id_sequence_same_qerror_changed"] += not any_sequence_changed and qclass != "tie"
        estimate_diag_changed += value_changed
        if other_tail[index] and not anchor_tail[index]:
            tail_counts["entered"] += 1
            entrant_queries[index] += 1
        elif anchor_tail[index] and not other_tail[index]:
            tail_counts["exited"] += 1
            exit_queries[index] += 1
        for category, matched in (
            ("sequence_changed_qerror_tie", any_sequence_changed and qclass == "tie"),
            ("sequence_same_qerror_changed", not any_sequence_changed and qclass != "tie"),
            ("sequence_changed_qerror_changed", any_sequence_changed and qclass != "tie"),
        ):
            if matched and category not in examples:
                examples[category] = {
                    "dataset": dataset,
                    "query_id": f"arecel:{dataset}:test:{index:06d}",
                    "anchor_configuration": anchor.record["configuration_id"],
                    "other_configuration": other.record["configuration_id"],
                    "anchor_qerror": left,
                    "other_qerror": right,
                    "qerror_direction": qclass,
                    "selection_sequence_changed": sel_changed,
                    "anchor_selection_sequence": list(anchor.selection_sequences[index]),
                    "other_selection_sequence": list(other.selection_sequences[index]),
                    "estimate_sequence_changed": est_changed,
                    "anchor_estimate_sequence": list(anchor.estimate_sequences[index]),
                    "other_estimate_sequence": list(other.estimate_sequences[index]),
                    "estimate_values_changed": value_changed,
                    "anchor_mcv_estimates": [
                        {"candidate_id": cid, **dict(zip(MCV_VALUE_FIELDS, values))}
                        for cid, values in anchor.estimate_values[index]
                    ],
                    "other_mcv_estimates": [
                        {"candidate_id": cid, **dict(zip(MCV_VALUE_FIELDS, values))}
                        for cid, values in other.estimate_values[index]
                    ],
                }
    return {
        "qerror_direction_counts": {name.removeprefix("qerror_"): counts[name]
                                    for name in ("qerror_lower", "qerror_higher", "qerror_tie")},
        "selection_sequence_changed_count": counts["selection_sequence_changed"],
        "estimate_sequence_changed_count": counts["estimate_sequence_changed"],
        "any_id_sequence_changed_count": counts["any_id_sequence_changed"],
        "estimate_values_changed_count": counts["estimate_values_changed"],
        "id_sequence_changed_qerror_tie_count": counts["id_sequence_changed_qerror_tie"],
        "id_sequence_changed_qerror_changed_count": counts["id_sequence_changed_qerror_changed"],
        "id_sequence_same_qerror_changed_count": counts["id_sequence_same_qerror_changed"],
        "tail_entered_count": tail_counts["entered"],
        "tail_exited_count": tail_counts["exited"],
        "tail_entered_query_indices": list(entrant_queries),
        "tail_exited_query_indices": list(exit_queries),
        "examples": examples,
        "anchor_p95": anchor_p95,
        "other_p95": other_p95,
        "query_pairs": n,
    }


def top_query_ids(indices: Counter[int], dataset: str, limit: int = 4) -> list[dict[str, Any]]:
    return [
        {"query_id": f"arecel:{dataset}:test:{index:06d}", "order_pair_count": count}
        for index, count in sorted(indices.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def select_anchor_orders(stratum: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    rows = stratum["permutations"]
    fixed = [row for row in rows if row["selection"] == "fixed"]
    sampled = [row for row in rows if row["selection"] == "srswor"]
    enumerated = [row for row in rows if row["selection"] == "enumerated"]
    if stratum["policy"] == "nominal":
        canonical = next((row for row in fixed if tuple(row["permutation"]) == tuple(stratum["resource_ids"])), None)
        if canonical is None or len(fixed) != 2:
            raise ValueError("Nominal stratum must retain canonical and reverse certainty orders")
        anchor_row = canonical
        compared = sampled
        anchor_kind = "fixed canonical certainty order"
    elif sampled:
        anchor_row = min(sampled, key=lambda row: row["draw_index"])
        compared = [row for row in sampled if row is not anchor_row]
        anchor_kind = "first frozen SRSWOR draw (descriptive anchor only)"
    else:
        anchor_row = min(enumerated, key=lambda row: tuple(row["permutation"]))
        compared = [row for row in enumerated if row is not anchor_row]
        anchor_kind = "lexicographically first fully enumerated order"
    return anchor_row, compared, anchor_kind


def require_complete_order_record(arm: dict[str, Any], key: Any) -> dict[str, Any]:
    if arm.get("status") != "COMPLETE":
        raise ValueError(f"final #107 configuration is incomplete: {key}")
    return arm


def pairwise_id_sequence_audit(
    stratum: dict[str, Any], data: dict[tuple[str, ...], OrderData]
) -> dict[str, Any]:
    """Describe all non-certainty-certainty order pairs without inferential weighting."""
    rows = stratum["permutations"]
    groups: dict[str, dict[str, Any]] = {}
    for left_row, right_row in combinations(rows, 2):
        left_kind, right_kind = left_row["selection"], right_row["selection"]
        if left_kind == right_kind == "fixed":
            # The canonical/reverse pair is already fully analyzed in Issue #105.
            continue
        if left_kind == right_kind == "srswor":
            pair_class = "sampled_vs_sampled"
        elif {left_kind, right_kind} == {"fixed", "srswor"}:
            pair_class = "certainty_vs_sampled"
        elif left_kind == right_kind == "enumerated":
            pair_class = "fully_enumerated_pairs"
        else:
            raise ValueError(f"unexpected order-design pair in {stratum['dataset']}/{stratum['policy']}")
        result = groups.setdefault(pair_class, {
            "order_pair_count": 0,
            "query_pair_count": 0,
            "qerror_direction_counts": Counter(),
            "selection_sequence_changed_count": 0,
            "estimate_sequence_changed_count": 0,
            "id_sequence_changed_qerror_tie_count": 0,
            "id_sequence_changed_qerror_changed_count": 0,
            "id_sequence_same_qerror_changed_count": 0,
            "estimate_values_changed_count": 0,
            "examples": {},
        })
        left = data[tuple(left_row["permutation"])]
        right = data[tuple(right_row["permutation"])]
        result["order_pair_count"] += 1
        result["query_pair_count"] += len(left.qerrors)
        for index, (left_error, right_error) in enumerate(zip(left.qerrors, right.qerrors, strict=True)):
            if right_error == left_error:
                qclass = "tie"
            else:
                qclass = "higher" if right_error > left_error else "lower"
            result["qerror_direction_counts"][qclass] += 1
            selection_changed = left.selection_sequences[index] != right.selection_sequences[index]
            estimate_changed = left.estimate_sequences[index] != right.estimate_sequences[index]
            any_sequence_changed = selection_changed or estimate_changed
            values_changed = left.estimate_value_signatures[index] != right.estimate_value_signatures[index]
            result["selection_sequence_changed_count"] += selection_changed
            result["estimate_sequence_changed_count"] += estimate_changed
            result["estimate_values_changed_count"] += values_changed
            result["id_sequence_changed_qerror_tie_count"] += any_sequence_changed and qclass == "tie"
            result["id_sequence_changed_qerror_changed_count"] += any_sequence_changed and qclass != "tie"
            result["id_sequence_same_qerror_changed_count"] += not any_sequence_changed and qclass != "tie"
            categories = (
                ("sequence_changed_qerror_tie", any_sequence_changed and qclass == "tie"),
                ("sequence_same_qerror_changed", not any_sequence_changed and qclass != "tie"),
                ("sequence_changed_qerror_changed", any_sequence_changed and qclass != "tie"),
            )
            for category, matched in categories:
                if not matched or category in result["examples"]:
                    continue
                result["examples"][category] = {
                    "query_id": f"arecel:{stratum['dataset']}:test:{index:06d}",
                    "left_configuration": left.record["configuration_id"],
                    "right_configuration": right.record["configuration_id"],
                    "left_qerror": float(left_error),
                    "right_qerror": float(right_error),
                    "qerror_direction": qclass,
                    "selection_sequence_changed": selection_changed,
                    "left_selection_sequence": list(left.selection_sequences[index]),
                    "right_selection_sequence": list(right.selection_sequences[index]),
                    "estimate_sequence_changed": estimate_changed,
                    "left_estimate_sequence": list(left.estimate_sequences[index]),
                    "right_estimate_sequence": list(right.estimate_sequences[index]),
                    "estimate_values_changed": values_changed,
                    "left_mcv_estimates": [
                        {"candidate_id": cid, **dict(zip(MCV_VALUE_FIELDS, fields))}
                        for cid, fields in left.estimate_values[index]
                    ],
                    "right_mcv_estimates": [
                        {"candidate_id": cid, **dict(zip(MCV_VALUE_FIELDS, fields))}
                        for cid, fields in right.estimate_values[index]
                    ],
                }
    for result in groups.values():
        result["qerror_direction_counts"] = dict(result["qerror_direction_counts"])
    return groups


def analyze_stratum(stratum: dict[str, Any], data: dict[tuple[str, ...], OrderData]) -> dict[str, Any]:
    rows = stratum["permutations"]
    if len(data) != len(rows):
        raise ValueError(f"{stratum['dataset']}/{stratum['policy']}: missing analyzed orders")
    anchor_row, compared, anchor_kind = select_anchor_orders(stratum)
    anchor = data[tuple(anchor_row["permutation"])]
    pair_rows = []
    entrant_frequency: Counter[int] = Counter()
    exit_frequency: Counter[int] = Counter()
    totals: Counter[str] = Counter()
    for row in compared:
        candidate = data[tuple(row["permutation"])]
        pair = compare_pair(anchor, candidate, stratum["dataset"])
        pair_rows.append({
            "selection": row["selection"],
            "draw_index": row.get("draw_index"),
            "configuration_id": candidate.record["configuration_id"],
            "permutation": list(row["permutation"]),
            **{key: value for key, value in pair.items() if key not in (
                "tail_entered_query_indices", "tail_exited_query_indices", "examples"
            )},
        })
        for index in pair["tail_entered_query_indices"]:
            entrant_frequency[index] += 1
        for index in pair["tail_exited_query_indices"]:
            exit_frequency[index] += 1
        for key in (
            "selection_sequence_changed_count", "estimate_sequence_changed_count",
            "any_id_sequence_changed_count", "estimate_values_changed_count",
            "id_sequence_changed_qerror_tie_count", "id_sequence_changed_qerror_changed_count",
            "id_sequence_same_qerror_changed_count",
            "tail_entered_count", "tail_exited_count",
        ):
            totals[key] += pair[key]
        for direction, count in pair["qerror_direction_counts"].items():
            totals[f"qerror_{direction}"] += count
        for category, example in pair["examples"].items():
            totals.setdefault(f"first_example:{category}", example)
    order_ranges = {}
    for selection, label in (("fixed", "fixed_certainty"), ("srswor", "srswor_sample"), ("enumerated", "enumerated_census")):
        selected_rows = [row for row in rows if row["selection"] == selection]
        if not selected_rows:
            continue
        observed = [(float(np.percentile(data[tuple(row["permutation"])].qerrors, 95)), row)
                    for row in selected_rows]
        low = min(observed, key=lambda pair: (pair[0], tuple(pair[1]["permutation"])))
        high = max(observed, key=lambda pair: (pair[0], tuple(pair[1]["permutation"])))
        order_ranges[label] = {
            "order_count": len(observed),
            "observed_p95_min": low[0],
            "min_configuration": data[tuple(low[1]["permutation"])].record["configuration_id"],
            "observed_p95_max": high[0],
            "max_configuration": data[tuple(high[1]["permutation"])].record["configuration_id"],
        }
    return {
        "dataset": stratum["dataset"],
        "policy": stratum["policy"],
        "case_id": stratum["case_id"],
        "resource_ids": list(stratum["resource_ids"]),
        "permutation_population_size": stratum["permutation_population_size"],
        "anchor_configuration": anchor.record["configuration_id"],
        "anchor_kind": anchor_kind,
        "comparisons": pair_rows,
        "comparison_pair_count": len(pair_rows) * 10_000,
        "comparison_order_count": len(pair_rows),
        "paired_totals": dict(totals),
        "tail_entered_query_ids": top_query_ids(entrant_frequency, stratum["dataset"]),
        "tail_exited_query_ids": top_query_ids(exit_frequency, stratum["dataset"]),
        "distinct_tail_entered_query_count": len(entrant_frequency),
        "distinct_tail_exited_query_count": len(exit_frequency),
        "order_p95_ranges": order_ranges,
        "pairwise_id_sequence_audit": pairwise_id_sequence_audit(stratum, data),
    }


def run_analysis() -> dict[str, Any]:
    schedule, schedule_index, official, roots, manifest_hashes = load_and_check_inputs()
    protocol = issue101.read_protocol()
    manifests = {key: json_file(root / "run-manifest.json") for key, root in roots.items()}
    checked_arms, failed_parent_rows = manifest_arm_maps(
        schedule, schedule_index, manifests, protocol
    )
    # Explicitly confirm Issue #107 recorded the #105 preflight as globally intact,
    # while its separate row-level reuse validation rejected all eight fixed arms.
    reuse = manifests["issue107_parent"].get("issue105_reuse_audit", {})
    if reuse.get("global_integrity_status") != "PASS" or reuse.get("eligible_reuse_count") != 0:
        raise ValueError("#107 recorded #105 archive preflight/reuse disposition differs")
    if not all(reuse.get("global_checks", {}).values()) or not all(reuse.get("member_checks", {}).values()):
        raise ValueError("#107 recorded a failed #105 archive/member integrity check")
    reuse_reason_counts = Counter(
        reason
        for arm in reuse.get("arms", {}).values()
        for reason in arm.get("reasons", [])
    )
    if reuse_reason_counts != Counter({"raw observation identity/recomputation failed": 8}):
        raise ValueError("#107 #105 fixed-arm rejection history differs from the retained generic reason")

    # Audit #105 independently and do not re-run its already reported canonical/reverse attribution.
    fixed_rows = validate_issue105_fixed(schedule, protocol, manifests["issue105"])
    truths: dict[str, list[int | None]] = {}
    extents: dict[str, list[tuple[int, int, str]]] = {key: [] for key in roots}
    source_counts = {key: 0 for key in roots}
    for arm, dataset, permutation in fixed_rows:
        oid_map = arm.pop("_issue125_oid_map")
        selected = arm.pop("_issue125_selected")
        _, _, extent = audit_member(
            source="issue105", root=roots["issue105"], arm=arm, dataset=dataset,
            permutation=permutation, selected_ids=selected, oid_map=oid_map,
            truths_by_dataset=truths, retain_queries=False,
        )
        extents["issue105"].append(extent)
        source_counts["issue105"] += 10_000
    validate_member_extents(roots["issue105"], extents["issue105"])

    continuation = manifests["issue107_continuation"]
    combined_arms = checked_arms

    final_records: list[dict[str, Any]] = []
    strata_results = []
    for stratum in schedule["schedules"]:
        group: dict[tuple[str, ...], OrderData] = {}
        for sampled_arm in stratum["permutations"]:
            key = (stratum["dataset"], stratum["policy"], tuple(sampled_arm["permutation"]))
            source, arm = combined_arms[key]
            require_complete_order_record(arm, key)
            frozen = issue107.validate_scheduled_arm(
                schedule_index, dataset=key[0], policy=key[1], case_id=arm.get("case_id"),
                resource_ids=arm.get("resource_ids", []), permutation=arm.get("permutation", []),
                selection=arm.get("selection"),
            )
            if (arm.get("configuration_id") is None or arm.get("resource_ids") != stratum["resource_ids"]
                    or arm.get("selection") != sampled_arm["selection"]
                    or arm.get("draw_index") != frozen.get("draw_index")
                    or arm.get("inclusion_probability") != frozen.get("inclusion_probability")):
                raise ValueError(f"final #107 configuration identity differs from frozen schedule: {key}")
            data_oid_map = catalog_oid_map(arm)
            if list(data_oid_map.values()) != list(sampled_arm["permutation"]):
                raise ValueError(f"final #107 OID map differs from frozen permutation: {key}")
            _, observed, extent = audit_member(
                source=source, root=roots[source], arm=arm, dataset=key[0],
                permutation=key[2], selected_ids=list(stratum["resource_ids"]), oid_map=data_oid_map,
                truths_by_dataset=truths, retain_queries=True,
            )
            assert observed is not None
            # The parent v1 manifest used sample_sha256 for ANALYZE, so the post-run
            # analyzer derives this separate schedule identity exactly as #107 did.
            observed.record["permutation_sample_sha256"] = stratum["sample_sha256"]
            group[key[2]] = observed
            final_records.append(observed.record)
            extents[source].append(extent)
            source_counts[source] += 10_000
        strata_results.append(analyze_stratum(stratum, group))
    for source in ("issue107_parent", "issue107_continuation"):
        validate_member_extents(roots[source], extents[source])
    if (len(final_records) != 156 or set(combined_arms) != set(schedule_index)
            or len(failed_parent_rows) != 12):
        raise ValueError("final #107 raw observations do not cover the exact 156 frozen arms")
    if sum(arm.get("plan_batch", {}).get("attempted_markers", 0) for arm in final_records) != 1_560_000:
        raise ValueError("final #107 observed arm records do not account for 1,560,000 EXPLAIN calls")

    # Recompute the existing official aggregate from validated raw query rows.
    recomputed = issue107.analyze_results(schedule, final_records)
    for dataset in issue101.DATASETS:
        for policy in ("nominal", "pess"):
            if not same_json_value(
                official["analysis"][dataset]["policies"][policy]["expectation"],
                recomputed[dataset]["policies"][policy]["expectation"],
            ):
                raise ValueError(f"official #107 aggregate differs after raw-row recomputation: {dataset}/{policy}")
        if not same_json_value(
            official["analysis"][dataset]["contrast_pess_minus_nominal"],
            recomputed[dataset]["contrast_pess_minus_nominal"],
        ):
            raise ValueError(f"official #107 PESS-Nominal contrast differs after recomputation: {dataset}")
    for dataset, values in truths.items():
        if len(values) != 10_000 or any(value is None for value in values):
            raise ValueError(f"{dataset}: cross-order Test truth identity is incomplete")

    # Hash again after streaming to detect concurrent mutation; all inputs remain read-only.
    for source, root in roots.items():
        if sha256_file(root / "raw-observations.jsonl.gz") != ARCHIVE_SHA256[source]:
            raise ValueError(f"{source}: raw archive changed during analysis")

    return {
        "format": "ess-issue125-read-only-order-attribution-v1",
        "status": "COMPLETE",
        "runtime_roots": {key: str(value) for key, value in roots.items()},
        "archive_sha256": ARCHIVE_SHA256,
        "manifest_sha256": manifest_hashes,
        "combined_analysis_sha256": COMBINED_ANALYSIS_SHA256,
        "permutation_sample_sha256": issue107.ISSUE107_SAMPLE_SHA256,
        "root_seed": schedule["root_seed"],
        "rng_version": schedule["rng_version"],
        "source_query_rows_validated": source_counts,
        "compressed_member_count": {key: len(value) for key, value in extents.items()},
        "final_configuration_count": len(final_records),
        "cumulative_explain_calls": 1_560_000,
        "official_aggregate_recomputed_from_raw_and_matched": True,
        "issue105_reuse_preflight": {
            "global_integrity_status": reuse["global_integrity_status"],
            "global_checks_all_passed": all(reuse["global_checks"].values()),
            "member_checks_all_passed": all(reuse["member_checks"].values()),
            "row_level_reuse_eligible_count": reuse["eligible_reuse_count"],
            "generic_rejection_reason_counts": dict(reuse_reason_counts),
            "specific_row_level_exception_persisted": any(
                row.get("row_validation_failure") for row in reuse.get("arms", {}).values()
            ),
            "fixed_orders_remeasured_at_same_frozen_permutations": 8,
        },
        "issue107_initial_pre_explain_failures": [
            {
                "dataset": arm["dataset"],
                "configuration_id": arm["configuration_id"],
                "selected_object_count": len(arm["resource_ids"]),
                "status": arm["status"],
                "attempted_explain_calls": arm.get("attempted_explain_calls"),
                "error": arm.get("error", {}).get("message"),
                "continuation_status": "COMPLETE",
            }
            for arm, _source in failed_parent_rows
        ],
        "strata": strata_results,
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Issue #125 — Read-only physical order attribution", "",
        "**Evidence class:** experimentally observed, frozen PostgreSQL 16.14 Test observations; all new analysis is descriptive and post hoc over the frozen sample. No database process, ANALYZE, EXPLAIN, resource reselection, training, or resampling is invoked by this analyzer.", "",
        "## Data integrity gate", "",
        "The analyzer resolves only the three run IDs specified in Issue #125 under `ESS_RUNTIME_PARENT`. It verifies archive SHA-256, the frozen #107 sample and schedule, arm identity, compressed member SHA-256 and exhaustive contiguous extents, one gzip member per arm, 10,000 valid Test rows per complete arm, canonical Test IDs, recomputed Issue #101 Q-error, MCV event/OID mappings, event sequence projections, and manifest metrics. Candidate IDs, not numeric OIDs, are the cross-order join key; each row’s candidate mapping is verified against that physical configuration’s catalog.", "",
        f"- Sample SHA-256: `{result['permutation_sample_sha256']}`; seed `{result['root_seed']}`; RNG `{result['rng_version']}`.",
        f"- Final #107 identities: **{result['final_configuration_count']}**; cumulative EXPLAIN calls: **{result['cumulative_explain_calls']:,}**.",
        f"- Revalidated rows: #105 `{result['source_query_rows_validated']['issue105']:,}`, #107 parent `{result['source_query_rows_validated']['issue107_parent']:,}`, #107 continuation `{result['source_query_rows_validated']['issue107_continuation']:,}`.",
        "- Member counts: " + ", ".join(f"`{key}` {value}" for key, value in result["compressed_member_count"].items()) + ".",
        f"- Official #107 finite-population aggregates and PESS − Nominal contrasts were recomputed from the raw qerrors and matched exactly: **{result['official_aggregate_recomputed_from_raw_and_matched']}**.",
        f"- #105 reuse audit: global archive/provenance **{result['issue105_reuse_preflight']['global_integrity_status']}**; all retained archive/member checks pass; row-level reuse eligible **{result['issue105_reuse_preflight']['row_level_reuse_eligible_count']}/8**; all eight fixed permutations were physically remeasured at those same positions.",
        "- The #107 parent’s 12 invalid Forest10/Power7 three-object arms are pre-EXPLAIN configuration failures. The continuation replaces exactly those 12 frozen identities. This is separate from the #105 fixed-row reuse rejection.",
        "", "### Frozen evidence locations and hashes", "",
        "| Source | Runtime path | Raw archive SHA-256 | Manifest SHA-256 |", "|---|---|---|---|",
    ]
    for key in ("issue105", "issue107_parent", "issue107_continuation"):
        lines.append(
            f"| `{key}` | `{result['runtime_roots'][key]}` | `{result['archive_sha256'][key]}` | `{result['manifest_sha256'][key]}` |"
        )
    lines += [
        "", "## Existing attribution and scope", "",
        "Issue #105 already compares the four Nominal canonical/reverse pairs query by query, including Q-error direction and MCV selection/estimate candidate-ID sequence changes. Those eight certainty arms are not re-counted as a new result here. Issue #107’s verified aggregate analysis explicitly did not decompress raw rows or read query-level Q-error, so it did not perform the sampled-order attribution below. Issue #116 is a separate Census13 Train-only model analysis and does not explain these physical Test observations.", "",
        "### Reuse rejection history (Event A)", "",
        "The retained #107 parent manifest shows all global #105 archive/provenance checks and all eight compressed-member hash checks passed, but row-level reuse eligibility was 0/8. Each arm has only the generic reason `raw observation identity/recomputation failed`; `row_validation_failure` is empty, and the eight final arm records do not retain an exception. The current read-only audit verifies the original #105 members, 10,000 row identities, stored/recomputed Q-errors, MCV diagnostics, and exact canonical/reverse order labels, while the frozen #107 arms show those same eight permutations were physically remeasured. The historical rejecting assertion cannot be confirmed from retained evidence. This is not evidence that the #105 raw observations were corrupt; it does not establish the specific failure cause either.", "",
        "### Three-object pre-EXPLAIN rejection history (Event B)", "",
        "The other 12 failures are distinct: six Forest10 and six Power7 PESS configurations had three selected objects, zero EXPLAIN calls, and no raw member. Their parent manifest records `relation does not have exactly the five selected statistics`. The source pinned to the initial #107 run (`af6d01e`) confirms `validate_catalog_rows` used a literal `len(rows) != 5` guard; the corrected runner compares against the selected-set length. The continuation completed those same 12 identities and 120,000 EXPLAIN calls. This validator defect did not cause the eight five-object Nominal reuse rejections in Event A.", "",
        "The order-level inferential target remains `E_pi[P95_q Q(q,M,pi)]`. This report does not calculate or substitute `P95_q[E_pi Q]`. Query comparisons below are paired descriptive contrasts to one anchor order within each frozen set; they are not independent order samples, do not estimate a new population mean, and do not alter #107’s finite-population weighted estimator.", "",
        "For Nominal, the anchor is the fixed canonical order and the 22 SRSWOR orders are compared separately; the fixed reverse order remains a certainty arm and is not pooled into those comparisons. For five-object PESS sets, the anchor is the first frozen SRSWOR draw and the remaining 23 sampled orders are descriptive contrasts. For three-object PESS sets, the lexicographically first order anchors the other five fully enumerated orders. No anchor is selected by its Q-error.", "",
        "High-tail membership is defined within each order as `Q-error >= that order's NumPy P95`; values tied at the threshold are retained. Entrants/exits compare those per-order sets against the stated anchor. This is a descriptive query-membership diagnostic, not a second estimand.", "",
        "## Observed per-order P95 ranges", "",
        "Ranges are split by the frozen design class; extrema are observed sample extrema unless the stratum is fully enumerated.", "",
        "| Dataset | Policy | Set size | Fixed certainty P95 range | SRSWOR P95 range | Full enumeration P95 range |", "|---|---|---:|---|---|---|",
    ]
    for s in result["strata"]:
        r = s["order_p95_ranges"]
        def span(name: str) -> str:
            v = r.get(name)
            if not v:
                return "—"
            return f"{v['observed_p95_min']:.6g} ({v['min_configuration']}) – {v['observed_p95_max']:.6g} ({v['max_configuration']})"
        lines.append(f"| {s['dataset']} | {s['policy']} | {len(s['resource_ids'])} | {span('fixed_certainty')} | {span('srswor_sample')} | {span('enumerated_census')} |")
    lines += [
        "", "## Paired query diagnostics by frozen set", "",
        "Counts are query-order pairs against the anchor described above. The repeated observations share Test queries and, in sampled strata, the anchor is also part of the finite sample; counts are descriptive and are not IID standard errors.", "",
        "| Dataset | Policy | Anchor | Compared orders | Q-error lower / higher / tie | Selection IDs changed | Estimate IDs changed | ID-sequence changed, Q-error tied | ID-sequence changed, Q-error changed | ID-sequence same, Q-error changed | MCV estimate values changed | Tail entered / exited events | Distinct entering / exiting queries |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in result["strata"]:
        t = s["paired_totals"]
        q = f"{t.get('qerror_lower',0)} / {t.get('qerror_higher',0)} / {t.get('qerror_tie',0)}"
        seq_tie = t.get("id_sequence_changed_qerror_tie_count", 0)
        seq_changed = t.get("id_sequence_changed_qerror_changed_count", 0)
        seq_same = t.get("id_sequence_same_qerror_changed_count", 0)
        tail_events = f"{t.get('tail_entered_count',0)} / {t.get('tail_exited_count',0)}"
        distinct = f"{s['distinct_tail_entered_query_count']} / {s['distinct_tail_exited_query_count']}"
        lines.append(f"| {s['dataset']} | {s['policy']} | {s['anchor_kind']} | {s['comparison_order_count']} | {q} | {t.get('selection_sequence_changed_count',0)} | {t.get('estimate_sequence_changed_count',0)} | {seq_tie} | {seq_changed} | {seq_same} | {t.get('estimate_values_changed_count',0)} | {tail_events} | {distinct} |")
    lines += [
        "", "## Counterexample audit over every eligible order pair", "",
        "This second diagnostic checks every unordered pair of frozen orders except the canonical/reverse pair already analyzed in #105. It keeps certainty-versus-SRSWOR, SRSWOR-versus-SRSWOR, and complete-enumeration pairs separate. These repeated pair counts are not independent observations and are not used for a mean, confidence interval, or population extrapolation.", "",
        "| Dataset | Policy | Pair design | Order pairs | Query pairs | ID sequence changed, Q-error tied | ID sequence changed, Q-error changed | ID sequence same, Q-error changed | Numeric MCV values changed after candidate-ID alignment |", "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in result["strata"]:
        for pair_class, audit in s["pairwise_id_sequence_audit"].items():
            lines.append(
                f"| {s['dataset']} | {s['policy']} | {pair_class} | {audit['order_pair_count']} | {audit['query_pair_count']} | {audit['id_sequence_changed_qerror_tie_count']} | {audit['id_sequence_changed_qerror_changed_count']} | {audit['id_sequence_same_qerror_changed_count']} | {audit['estimate_values_changed_count']} |"
            )
    lines += [
        "", "No `ID sequence same, Q-error changed` pair was observed in the checked pair classes." if all(
            audit["id_sequence_same_qerror_changed_count"] == 0
            for s in result["strata"] for audit in s["pairwise_id_sequence_audit"].values()
        ) else "At least one `ID sequence same, Q-error changed` pair was observed; examples follow below.",
        "This is a finite sample/enumeration statement about the listed pair classes, not a causal result or a claim about every one of the 120 possible five-object orders.",
        "",
    ]
    lines += [
        "", "## Recurrent Test IDs entering or leaving the high-error tail", "",
        "For each set, the IDs below recur most often among paired entrant/exit events; ties are ordered by Test index. They identify sample-level cases for inspection, not population-wide tail probabilities.", "",
        "| Dataset | Policy | Most recurrent entrants (ID × order pairs) | Most recurrent exits (ID × order pairs) |", "|---|---|---|---|",
    ]
    for s in result["strata"]:
        entrants = ", ".join(f"`{r['query_id']}` × {r['order_pair_count']}" for r in s["tail_entered_query_ids"]) or "—"
        exits = ", ".join(f"`{r['query_id']}` × {r['order_pair_count']}" for r in s["tail_exited_query_ids"]) or "—"
        lines.append(f"| {s['dataset']} | {s['policy']} | {entrants} | {exits} |")
    lines += ["", "## Query-level examples for Census13 and DMV11", ""]
    for dataset in ("census13", "dmv11"):
        lines.append(f"### {dataset}")
        lines.append("")
        for s in (row for row in result["strata"] if row["dataset"] == dataset):
            lines.append(f"**{s['policy']}** — all eligible order pairs are grouped by design in the table above; anchor-based tail diagnostics use `{s['anchor_configuration']}`.")
            lines.append("")
            emitted = False
            categories = (
                ("sequence_changed_qerror_tie", "MCV ID sequence changed while Q-error tied"),
                ("sequence_same_qerror_changed", "MCV ID sequence stayed the same while Q-error changed"),
                ("sequence_changed_qerror_changed", "MCV ID sequence and Q-error both changed"),
            )
            for pair_class, audit in s["pairwise_id_sequence_audit"].items():
                for category, title in categories:
                    example = audit["examples"].get(category)
                    if not example:
                        continue
                    emitted = True
                    lines.append(f"- **{title} ({pair_class}):** `{example['query_id']}`; `{example['left_configuration']}` Q-error {example['left_qerror']:.9g} → `{example['right_configuration']}` {example['right_qerror']:.9g} ({example['qerror_direction']}). Selection sequence `{example['left_selection_sequence']}` → `{example['right_selection_sequence']}`; estimate sequence `{example['left_estimate_sequence']}` → `{example['right_estimate_sequence']}`; per-candidate numeric MCV estimate values changed: `{example['estimate_values_changed']}`.")
            if not emitted:
                lines.append("- No paired example of an MCV ID-sequence/Q-error relation occurred in these order-pair classes.")
            lines.append("")
    lines += [
        "## Interpretation and paper-use boundary", "",
        "**Safe as a scoped descriptive statement:** on the frozen PostgreSQL 16.14 build, Issue #99 train-only selected sets, fixed ANALYZE samples/statistics target, and official 10,000-query Test workloads, sampled global OID-order configurations show query-level Q-error and MCV diagnostic variation. The tables give paired associations and concrete diagnostic traces for these exact physical configurations.", "",
        "**Not established:** that OID order or a particular MCV event caused a Q-error change; that MCV diagnostics fully mediate planner estimates; that PostgreSQL randomly assigns OIDs; that the observed sample extrema are global worst cases; that the paired query-order counts are independent or population estimates; or that results generalize beyond these frozen builds, sets, data, and sampled orders. No causal intervention isolated one statistic or planner mechanism.", "",
        "No query-level average was converted to a P95. No resource set, Test query, or order was selected or replaced based on these observations. No new physical experiment was run.", "",
        "## Reproduction", "",
        "From the repository Worktree with the frozen environment initialized:", "",
        "```bash",
        "PYTHONPATH=src:experiments/arecel-test-generalization-issue101:experiments/oid-order-stress-test-issue105:experiments/oid-uniform-priority-issue107 \\",
        "  ../../.venv/bin/python -B experiments/oid-order-attribution-issue125/analyze_issue125.py \\",
        "  --output experiments/oid-order-attribution-issue125/findings.md",
        "```",
        "",
        "The command reads the pinned runtime archives and writes only the derived findings report at the requested output path. It does not start PostgreSQL or modify run artifacts.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "findings.md")
    args = parser.parse_args()
    result = run_analysis()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown_report(result), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "output": str(args.output.resolve()),
        "configuration_count": result["final_configuration_count"],
        "rows_validated": result["source_query_rows_validated"],
        "official_aggregate_recomputed_and_matched": result["official_aggregate_recomputed_from_raw_and_matched"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
