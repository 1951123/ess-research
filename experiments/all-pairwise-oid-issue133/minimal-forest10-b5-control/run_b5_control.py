"""Run one frozen Forest10 Nominal B5 matched-priority comparison arm.

The runner revalidates the saved Issue #135 raw archive, builds one isolated
PostgreSQL cluster, and does not execute the new Test workload until the B5
catalog/sample/ordinary-statistics state matches the archived ALL arms.
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any
from uuid import uuid4

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ISSUE133_ROOT = HERE.parent
BASE_RUNNER_DIR = ISSUE133_ROOT / "minimal-forest10"
PROTOCOL_PATH = HERE / "protocol-v1.json"
ALL_ATTEMPT_ID = "20261028T1408Z-issue133-forest10-random01-02"
ALL_CONFIGS = ("forest10-all-random-01", "forest10-all-random-02")
B5_CONFIG = "forest10-b5-nominal-matched-random01"
DATASET = "forest10"
B5_ORDER = ("e02_08", "e03_04", "e02_07", "e01_06", "e06_08")
B5_IDS = frozenset(("e01_06", "e02_07", "e02_08", "e03_04", "e06_08"))
GIB = 1024**3

sys.path.insert(0, str(BASE_RUNNER_DIR))
import run_minimal_forest10 as base  # noqa: E402

issue101 = base.issue101
issue105 = base.issue105


class Inconclusive(RuntimeError):
    """A failed source/physical-state check prevents the matched comparison."""


class Incomplete(RuntimeError):
    """The B5 Test observation set or its diagnostics is incomplete."""


def sha256_order(order: list[str] | tuple[str, ...]) -> str:
    encoded = (json.dumps(list(order), ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def json_sha256(value: Any) -> str:
    return base.sha256_json(value)


def read_frozen_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_TEST_EXECUTION":
        raise Inconclusive("B5 protocol is not frozen")
    # Reuse Issue #135's source pins and the unchanged Issue #134 random-order
    # verifier. This validates old code/data pins without running its executor.
    all_protocol = base.read_protocol()
    inventory, random01, random02 = base.verify_orders(all_protocol)
    source_pins = protocol["frozen_b5_selection"]
    train_path = ROOT / source_pins["source_path"]
    if base.sha256_file(train_path) != source_pins["source_sha256"]:
        raise Inconclusive("Issue #99 frozen Train resource manifest SHA mismatch")
    train = json.loads(train_path.read_text(encoding="utf-8"))
    matches = [row for row in train["cases"] if row.get("case_id") == source_pins["case_id"]]
    if len(matches) != 1:
        raise Inconclusive("Issue #99 Forest10 Nominal B5 case is missing or ambiguous")
    case = matches[0]
    if (case.get("status") != "COMPLETE" or case.get("split") != "train"
            or case.get("dataset") != DATASET or case.get("objective") != "nominal"
            or case.get("budget") != 5 or sorted(case.get("selected_ids", []))
            != sorted(source_pins["selected_ids"])
            or case.get("selection_manifest_sha256") != source_pins["selection_manifest_sha256"]):
        raise Inconclusive("Issue #99 frozen B5 Nominal selection differs from the protocol")
    if set(case["selected_ids"]) != B5_IDS or len(case["selected_ids"]) != 5:
        raise Inconclusive("protocol B5 IDs are not the exact five-object frozen set")
    rows = inventory["datasets"][DATASET]["candidates"]
    candidate_ids = {row["id"] for row in rows}
    if not B5_IDS <= candidate_ids:
        raise Inconclusive("a frozen B5 candidate is absent from the Forest10 universe")
    actual01 = [candidate for candidate in random01["permutation"] if candidate in B5_IDS]
    actual02 = [candidate for candidate in random02["permutation"] if candidate in B5_IDS]
    order_pins = protocol["order_matching"]
    if (actual01 != order_pins["random01_nominal_b5_projection"]
            or actual02 != order_pins["random02_nominal_b5_projection"]
            or tuple(actual01) != B5_ORDER or tuple(order_pins["b5_create_order"]) != B5_ORDER
            or order_pins["projections_equal"] != (actual01 == actual02)
            or sha256_order(B5_ORDER) != order_pins["b5_create_order_sha256"]):
        raise Inconclusive("frozen B5 order/projection/hash differs from the Issue #134 sample")
    if order_pins["predeclared_primary_comparison"] != (
            "ALL random-01 minus B5; B5 CREATE order exactly equals the random-01 projection"):
        raise Inconclusive("primary ALL/B5 comparison policy changed")
    refs = {
        protocol["frozen_b5_selection"]["source_path"]: protocol["frozen_b5_selection"]["source_sha256"],
        order_pins["source_path"]: order_pins["source_sha256"],
        "experiments/all-pairwise-oid-issue133/candidate-universe-manifest.json":
            all_protocol["input_pins"]["candidate_universe_manifest_sha256"],
        protocol["issue135_evidence_pins"]["summary_path"]:
            protocol["issue135_evidence_pins"]["summary_sha256"],
        protocol["issue135_evidence_pins"]["catalog_audit_path"]:
            protocol["issue135_evidence_pins"]["catalog_audit_sha256"],
    }
    for relative, expected in refs.items():
        if base.sha256_file(ROOT / relative) != expected:
            raise Inconclusive(f"frozen B5 source file hash mismatch: {relative}")
    return protocol


def catalog_row_signature(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "attnames": row.get("attnames") or row.get("resolved_attnames"),
        "kinds": row.get("kinds"),
        "stxkind": row.get("stxkind"),
        "statistics_target": int(row["statistics_target"]),
        "stxkeys": row["stxkeys"],
        "payload_state": row.get("payload_state") or base.payload_state(row),
        "mcv_item_count": int(row["mcv_item_count"]),
        "mcv_content_sha256": row["mcv_content_sha256"],
    }


def qerror_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return issue105.metrics_for_rows(rows)


def verify_saved_all(protocol: dict[str, Any]) -> dict[str, Any]:
    pins = protocol["issue135_evidence_pins"]
    runtime = issue101.configured_root("ESS_RUNTIME_PARENT")
    raw_relative = Path(pins["raw_archive_path_under_ess_runtime_parent"])
    if raw_relative.is_absolute() or ".." in raw_relative.parts:
        raise Inconclusive("Issue #135 raw archive pin is not a safe relative runtime path")
    raw_path = runtime / raw_relative
    all_root = raw_path.parent
    manifest_path = all_root / "run-manifest.json"
    input_preflight_path = runtime / pins["input_preflight_path_under_ess_runtime_parent"]
    if base.sha256_file(input_preflight_path) != pins["input_preflight_sha256"]:
        raise Inconclusive("Issue #135 runtime input-preflight SHA mismatch")
    if base.sha256_file(manifest_path) != pins["run_manifest_sha256"]:
        raise Inconclusive("Issue #135 runtime run-manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = raw_path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if (raw_sha != pins["raw_archive_sha256"]
            or len(raw) != pins["raw_archive_bytes"]
            or raw_sha != manifest.get("raw_observations_sha256")):
        raise Inconclusive("Issue #135 original raw archive identity/size/SHA mismatch")
    if (manifest.get("status") != "COMPLETE"
            or manifest.get("source_commit_before_test") != pins["execution_source_commit"]
            or manifest.get("actual_explain_calls") != 20_000
            or manifest.get("attempted_explain_calls") != 20_000
            or len(manifest.get("arms", [])) != 2):
        raise Inconclusive("Issue #135 source manifest is not the complete frozen two-arm run")
    summary = json.loads((ROOT / pins["summary_path"]).read_text(encoding="utf-8"))
    audit = json.loads((ROOT / pins["catalog_audit_path"]).read_text(encoding="utf-8"))
    if summary.get("status") != "COMPLETE" or audit.get("status") != "COMPLETE":
        raise Inconclusive("Issue #135 versioned summary/catalog audit is incomplete")
    if audit.get("pretest_comparison", {}).get("status") != "PASS":
        raise Inconclusive("Issue #135 archived cross-arm physical-state check did not pass")
    if (len(manifest["arms"]) != 2 or len(summary["arms"]) != 2
            or len(audit["arms"]) != 2):
        raise Inconclusive("Issue #135 raw run, summary, and catalog-audit arm counts differ")
    member_ranges = []
    for arm in manifest["arms"]:
        member = arm["raw_member"]
        start = int(member["raw_member_offset"])
        stop = start + int(member["raw_member_bytes"])
        member_ranges.append((start, stop, arm["configuration_id"]))
    member_ranges.sort()
    cursor = 0
    for start, stop, config_id in member_ranges:
        if start != cursor or stop <= start:
            raise Inconclusive(f"Issue #135 raw gzip member boundary gap/overlap at {config_id}")
        cursor = stop
    if cursor != len(raw):
        raise Inconclusive("Issue #135 raw archive has uncovered trailing bytes")

    rows_by_config: dict[str, list[dict[str, Any]]] = {}
    metrics_by_config: dict[str, dict[str, Any]] = {}
    for arm in manifest["arms"]:
        config_id = arm["configuration_id"]
        member = arm["raw_member"]
        start = int(member["raw_member_offset"])
        stop = start + int(member["raw_member_bytes"])
        blob = raw[start:stop]
        if hashlib.sha256(blob).hexdigest() != member["raw_member_sha256"]:
            raise Inconclusive(f"Issue #135 {config_id} gzip-member SHA mismatch")
        try:
            decoded = gzip.decompress(blob)
            rows = [json.loads(line) for line in decoded.splitlines()]
        except (OSError, EOFError, json.JSONDecodeError) as exc:
            raise Inconclusive(f"Issue #135 {config_id} gzip member is unreadable: {exc}") from exc
        if (len(rows) != 10_000 or arm.get("status") != "COMPLETE"
                or arm.get("query_count") != 10_000
                or arm.get("attempted_explain_calls") != 10_000
                or any(row.get("status") != "VALID"
                       or row.get("diagnostics_status") not in {"complete", "empty"}
                       for row in rows)
                or len({row["query_id"] for row in rows}) != 10_000):
            raise Inconclusive(f"Issue #135 {config_id} lacks 10,000 unique valid rows and diagnostics")
        for row in rows:
            if (row.get("configuration_id") != f"{DATASET}-{config_id}"
                    or row.get("order") != config_id
                    or row.get("dataset") != DATASET
                    or row.get("query_id") != f"arecel:{DATASET}:test:{int(row['source_index']):06d}"):
                raise Inconclusive(f"Issue #135 {config_id} raw row identity is inconsistent")
            computed, rounded = issue101.qerror_for_plan_rows(
                row["estimate_plan_rows"], row["true_cardinality"])
            if computed != row["qerror"] or rounded != row["estimate_rounded_r1"]:
                raise Inconclusive(f"Issue #135 {config_id} Q-error/rounding does not recompute")
        recomputed = qerror_metrics(rows)
        summary_arm = next((row for row in summary["arms"]
                            if row["configuration_id"] == config_id), None)
        if summary_arm is None or summary_arm["qerror_metrics"] != recomputed:
            # JSON numeric types/ordering should compare exactly; the metrics
            # implementation is the same pinned Issue #101/#105 function.
            raise Inconclusive(f"Issue #135 {config_id} saved metrics do not recompute from raw rows")
        rows_by_config[config_id] = rows
        metrics_by_config[config_id] = recomputed

    if set(rows_by_config) != set(ALL_CONFIGS):
        raise Inconclusive("Issue #135 raw archive contains unexpected configurations")
    left, right = (rows_by_config[key] for key in ALL_CONFIGS)
    if ([(row["query_id"], row["source_index"], row["true_cardinality"]) for row in left]
            != [(row["query_id"], row["source_index"], row["true_cardinality"]) for row in right]):
        raise Inconclusive("Issue #135 two ALL members do not share identical query/truth identities")

    # The independently recorded catalog audit is keyed by candidate ID; OIDs
    # are deliberately not used to align the later B5 cluster.
    audit_arms = {row["configuration_id"]: row for row in audit["arms"]}
    manifest_arms = {row["configuration_id"]: row for row in manifest["arms"]}
    if set(audit_arms) != set(ALL_CONFIGS) or set(manifest_arms) != set(ALL_CONFIGS):
        raise Inconclusive("Issue #135 candidate audit does not match both frozen ALL configurations")
    selected_signatures: dict[str, dict[str, Any]] = {}
    for config_id in ALL_CONFIGS:
        arm = manifest_arms[config_id]
        audit_arm = audit_arms[config_id]
        if (arm["catalog_oid_order_candidate_ids"] != arm["create_statement_candidate_ids"]
                or audit_arm.get("catalog_oid_order_candidate_ids")
                != arm["catalog_oid_order_candidate_ids"]
                or audit_arm.get("create_statement_candidate_ids")
                != arm["create_statement_candidate_ids"]
                or len(arm["catalog"]) != 45):
            raise Inconclusive(f"Issue #135 {config_id} stored OID order/full object set is invalid")
        rows = {row["candidate_id"]: row for row in audit_arm["catalog"]}
        if len(rows) != 45:
            raise Inconclusive(f"Issue #135 {config_id} catalog candidate IDs are incomplete")
        selected_signatures[config_id] = {
            candidate_id: catalog_row_signature(rows[candidate_id]) for candidate_id in B5_IDS
        }
    if selected_signatures[ALL_CONFIGS[0]] != selected_signatures[ALL_CONFIGS[1]]:
        raise Inconclusive("the five shared B5 MCV states/content differ between archived ALL arms")

    for config_id in ALL_CONFIGS:
        row = next(arm for arm in manifest["arms"] if arm["configuration_id"] == config_id)
        if (row["sample_sha256"] != protocol["inputs_and_environment"]["issue99_fixed_analyze_sample_sha256"]
                or row["ordinary_stats_sha256"] != manifest_arms[ALL_CONFIGS[0]]["ordinary_stats_sha256"]):
            raise Inconclusive(f"Issue #135 {config_id} does not match the pinned sample/ordinary stats")

    input_identity = manifest["input_identity"]
    input_pins = protocol["inputs_and_environment"]
    expected_inputs = {
        "source_csv_sha256": input_pins["forest10_full_csv_sha256"],
        "workload_pickle_sha256": input_pins["workload_pickle_sha256"],
        "labels_pickle_sha256": input_pins["test_labels_container_sha256"],
        "test_truth_canonical_sha256": input_pins["test_truth_canonical_sha256"],
        "query_count": 10_000,
    }
    if any(input_identity.get(key) != value for key, value in expected_inputs.items()):
        raise Inconclusive("Issue #135 frozen Test/source identities differ from the B5 protocol")
    return {
        "status": "PASS",
        "raw_archive_path": str(raw_path),
        "raw_archive_bytes": len(raw),
        "raw_archive_sha256": raw_sha,
        "run_manifest_sha256": pins["run_manifest_sha256"],
        "source_commit_before_test": manifest["source_commit_before_test"],
        "actual_explain_calls": manifest["actual_explain_calls"],
        "query_count_per_all_arm": 10_000,
        "query_truth_order_identity_sha256": json_sha256([
            {"query_id": row["query_id"], "source_index": row["source_index"],
             "true_cardinality": row["true_cardinality"]} for row in left
        ]),
        "all_metrics_recomputed": metrics_by_config,
        "all_rows_by_config": rows_by_config,
        "catalog_signatures_for_shared_b5_ids": selected_signatures,
        "catalog_audit": audit,
        "run_manifest": manifest,
        "input_identity": input_identity,
        "b5_reference_metrics": {
            "selected_ids": sorted(B5_IDS),
            "selected_mcv_signatures": selected_signatures[ALL_CONFIGS[0]],
            "ordinary_stats_sha256": manifest_arms[ALL_CONFIGS[0]]["ordinary_stats_sha256"],
            "sample_sha256": manifest_arms[ALL_CONFIGS[0]]["sample_sha256"],
            "sample_header": audit_arms[ALL_CONFIGS[0]]["sample_header"],
            "table_logical_identity": audit_arms[ALL_CONFIGS[0]]["table_logical_identity"],
        },
    }


def signature_for_candidate_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["candidate_id"]: catalog_row_signature(row) for row in rows}


def recover_event_ids_from_catalog(rows: list[dict[str, Any]],
                                   catalog_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve saved numeric event OIDs to candidate IDs without editing raw rows on disk.

    Preserve each parsed diagnostics_status verbatim. In particular, this does
    not infer an original extension status that the first parser overwrote.
    """
    oid_to_id: dict[int, str] = {}
    for catalog_row in catalog_rows:
        oid = int(catalog_row["oid"])
        candidate_id = catalog_row["candidate_id"]
        if oid in oid_to_id or candidate_id in oid_to_id.values():
            raise Inconclusive("saved catalog has duplicate OID or candidate ID")
        oid_to_id[oid] = candidate_id
    repaired: list[dict[str, Any]] = []
    original_status_counts = Counter(row.get("diagnostics_status") for row in rows)
    mapped_events = 0
    observed_oids: Counter[int] = Counter()
    for source in rows:
        row = dict(source)
        events = []
        selections = []
        estimates = []
        for source_event in source.get("mcv_events", []):
            event = dict(source_event)
            oid_value = event.get("stat_oid")
            if isinstance(oid_value, bool) or not isinstance(oid_value, int):
                raise Inconclusive("saved MCV event lacks an integer stat_oid")
            observed_oids[oid_value] += 1
            candidate_id = oid_to_id.get(oid_value)
            if candidate_id is None:
                raise Inconclusive(f"saved MCV event OID {oid_value} is absent from B5 catalog")
            if event.get("candidate_id") not in (None, candidate_id):
                raise Inconclusive("saved MCV event candidate ID conflicts with catalog OID mapping")
            event["candidate_id"] = candidate_id
            events.append(event)
            mapped_events += 1
            if event.get("type") == "mcv_selection":
                selections.append(candidate_id)
            elif event.get("type") == "mcv_estimate":
                estimates.append(candidate_id)
        row["mcv_events"] = events
        row["mcv_selection_ids"] = selections
        row["mcv_estimate_ids"] = estimates
        repaired.append(row)
    return repaired, {
        "status": "PASS_EVENT_OID_MAPPING",
        "method": "re-map each saved integer stat_oid using the same-arm five-row catalog audit",
        "catalog_oid_to_candidate_id": {str(oid): candidate_id for oid, candidate_id in oid_to_id.items()},
        "observed_mcv_event_count": mapped_events,
        "observed_stat_oid_event_counts": {
            str(oid): count for oid, count in sorted(observed_oids.items())
        },
        "unmapped_stat_oids": [],
        "source_diagnostics_status_counts": dict(sorted(original_status_counts.items())),
        "status_handling": (
            "Original ESS Diagnostics.Status was overwritten by UNKNOWN_SELECTED_STAT_OID "
            "in the source parsed rows and is not reconstructed; repaired rows preserve that status."
        ),
    }


def build_b5_catalog_audit(protocol: dict[str, Any], all_evidence: dict[str, Any],
                           schedule: dict[str, Any], candidates: dict[str, dict[str, Any]],
                           helper_ledger: list[dict[str, Any]], helpers: Any,
                           prefix: Path, cluster: dict[str, Any], sample: Path,
                           sample_sha: str, input_identity: dict[str, Any],
                           evidence_dir: Path) -> dict[str, Any]:
    all_protocol = base.read_protocol()
    inventory, _, _ = base.verify_orders(all_protocol)
    candidate_definitions = {
        row["id"]: row for row in inventory["datasets"][DATASET]["candidates"]
    }
    name_to_id = {value["statistic_name"]: candidate_id
                  for candidate_id, value in candidates.items()}
    rows = issue105.query_catalog_audit(helpers, prefix, cluster, DATASET)
    for row in rows:
        row["candidate_id"] = name_to_id.get(row["statistic_name"])
    snapshot: dict[str, Any] = {
        "configuration_id": B5_CONFIG,
        "status": "PREVALIDATION_IN_PROGRESS",
        "catalog": rows,
        "helper_ledger": helper_ledger,
        "comparison_key": "stable candidate_id; numeric OIDs are local to each configuration",
    }
    base.atomic_json(evidence_dir / "catalog-prevalidation-snapshot.json", snapshot)
    actual_ids = [name_to_id.get(row["statistic_name"]) for row in rows]
    helper_names = [row["statistic_name"] for row in helper_ledger]
    expected_names = [candidates[candidate_id]["statistic_name"] for candidate_id in B5_ORDER]
    if (len(rows) != 5 or actual_ids != list(B5_ORDER)
            or [row["statistic_name"] for row in rows] != expected_names
            or helper_names != expected_names
            or len({row["statistic_name"] for row in rows}) != 5):
        raise Inconclusive("B5 catalog is not exactly five objects in the frozen OID order")
    ledger_by_name = {row["statistic_name"]: row for row in helper_ledger}
    oid_map: dict[int, str] = {}
    for row in rows:
        candidate_id = name_to_id.get(row["statistic_name"])
        if candidate_id not in B5_IDS:
            raise Inconclusive("B5 catalog contains an object outside the frozen selected set")
        base.validate_catalog_definition(row, candidate_definitions[candidate_id])
        ledger = ledger_by_name[row["statistic_name"]]
        if (int(ledger["oid"]) != int(row["oid"])
                or ledger["stxkeys"] != row["stxkeys"]
                or int(ledger["statistics_target"]) != int(row["statistics_target"])
                or bool(ledger["mcv_payload_present"]) != bool(row["mcv_payload_present"])
                or int(ledger["mcv_item_count"]) != int(row["mcv_item_count"])):
            raise Inconclusive(f"{candidate_id}: Issue #99 helper and direct catalog audit disagree")
        oid = int(row["oid"])
        if oid in oid_map:
            raise Inconclusive("B5 catalog contains duplicate OIDs")
        oid_map[oid] = candidate_id
        row["candidate_id"] = candidate_id

    table = issue105.table_identity(helpers, prefix, cluster, DATASET)
    snapshot["table_identity"] = table
    base.atomic_json(evidence_dir / "catalog-prevalidation-snapshot.json", snapshot)
    source_columns, pg_columns, source_rows, _csv_sha, table_name = issue101.issue99.dataset_spec(DATASET)
    expected_schema = [
        [index + 1, name, re.sub(r"^varchar", "character varying", type_name.lower())]
        for index, (name, type_name) in enumerate(pg_columns)
    ]
    if int(table["row_count"]) != source_rows or table["columns"] != expected_schema:
        raise Inconclusive("B5 full source table row count/schema differs from Issue #99")
    ordinary = issue105.ordinary_stats_audit(helpers, prefix, cluster, DATASET)
    snapshot["ordinary_column_stats"] = ordinary
    base.atomic_json(evidence_dir / "catalog-prevalidation-snapshot.json", snapshot)
    if ordinary["column_count"] != len(pg_columns):
        raise Inconclusive("B5 ordinary column statistics are incomplete")
    header = helpers.sample_header(sample)
    snapshot["sample_sha256"] = sample_sha
    snapshot["sample_header"] = header
    base.atomic_json(evidence_dir / "catalog-prevalidation-snapshot.json", snapshot)
    if (base.sha256_file(sample) != sample_sha
            or header["server_version"] != "16.14"
            or header["sample_target"] != 90_000
            or header["tuple_count"] != min(source_rows, 90_000)
            or header["natts"] != len(pg_columns)
            or int(header["relation_oid"]) != int(table["relation_oid"])
            or header["relation_identity"] != "6:public8:forest10"):
        raise Inconclusive("B5 Issue #99 sample hash/header/table identity mismatch")

    b5_signatures = signature_for_candidate_rows(rows)
    reference = all_evidence["b5_reference_metrics"]
    if b5_signatures != reference["selected_mcv_signatures"]:
        changed = [candidate_id for candidate_id in sorted(B5_IDS)
                   if b5_signatures.get(candidate_id) != reference["selected_mcv_signatures"].get(candidate_id)]
        raise Inconclusive("B5 shared MCV state/content differs from Issue #135 candidate IDs: "
                           + ",".join(changed))
    if ordinary["sha256"] != reference["ordinary_stats_sha256"]:
        raise Inconclusive("B5 ordinary-column statistics fingerprint differs from Issue #135 ALL")
    reference_header = reference["sample_header"]
    comparable_header_keys = ("relation_oid", "relation_identity", "server_version",
                              "sample_target", "tuple_count", "natts")
    if any(header[key] != reference_header[key] for key in comparable_header_keys):
        raise Inconclusive("B5 sample header differs from Issue #135 ALL")
    logical_identity = {"row_count": int(table["row_count"]), "columns": table["columns"]}
    if logical_identity != reference["table_logical_identity"]:
        raise Inconclusive("B5 logical table identity differs from Issue #135 ALL")

    audit = {
        "configuration_id": B5_CONFIG,
        "status": "PASS",
        "create_statement_candidate_ids": list(B5_ORDER),
        "catalog_oid_order_candidate_ids": actual_ids,
        "catalog_oid_order": [
            {"candidate_id": name_to_id[row["statistic_name"]],
             "statistic_name": row["statistic_name"], "oid": int(row["oid"])}
            for row in rows
        ],
        "catalog": rows,
        "candidate_payload_state_counts": dict(sorted(Counter(
            row["payload_state"] for row in rows).items())),
        "table_identity": table,
        "table_logical_identity": logical_identity,
        "ordinary_column_stats": ordinary,
        "sample_sha256": sample_sha,
        "sample_header": header,
        # Keep integer keys in memory because Issue #105 parses integer stat_oid
        # values. JSON serialization will encode object keys as strings later.
        "oid_to_candidate_id": oid_map,
        "create_count": 5,
        "target_count": 5,
        "analyze_count": 1,
        "issue135_shared_candidate_content_match": True,
        "issue135_ordinary_stats_match": True,
        "issue135_sample_match": True,
        "issue135_table_logical_identity_match": True,
        "comparison_key": "stable candidate_id; numeric OIDs are local to each configuration",
    }
    snapshot.update(audit)
    base.atomic_json(evidence_dir / "catalog-prevalidation-snapshot.json", snapshot)
    return audit


def verify_live_b5_state(arm: dict[str, Any], helpers: Any, prefix: Path,
                         cluster: dict[str, Any], candidates: dict[str, dict[str, Any]],
                         sample: Path) -> None:
    rows = issue105.query_catalog_audit(helpers, prefix, cluster, DATASET)
    name_to_id = {candidate["statistic_name"]: candidate_id
                  for candidate_id, candidate in candidates.items()}
    actual = [name_to_id.get(row["statistic_name"]) for row in rows]
    if actual != list(B5_ORDER) or len(rows) != 5:
        raise Inconclusive("B5 live catalog order/object set changed before Test EXPLAIN")
    current_by_id = {name_to_id[row["statistic_name"]]: row for row in rows}
    frozen_by_id = {row["candidate_id"]: row for row in arm["catalog"]}
    for candidate_id in B5_ORDER:
        if (int(current_by_id[candidate_id]["oid"]) != int(frozen_by_id[candidate_id]["oid"])
                or catalog_row_signature(current_by_id[candidate_id])
                != catalog_row_signature(frozen_by_id[candidate_id])):
            raise Inconclusive(f"{candidate_id}: B5 MCV state changed immediately before Test")
    table = issue105.table_identity(helpers, prefix, cluster, DATASET)
    ordinary = issue105.ordinary_stats_audit(helpers, prefix, cluster, DATASET)
    if (int(table["row_count"]) != arm["table_identity"]["row_count"]
            or table["columns"] != arm["table_identity"]["columns"]
            or ordinary["sha256"] != arm["ordinary_column_stats"]["sha256"]
            or base.sha256_file(sample) != arm["sample_sha256"]):
        raise Inconclusive("B5 table/ordinary-statistics/sample state changed before Test")


def _metric_values(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = qerror_metrics(rows)
    if metrics.get("valid_count") != 10_000:
        raise Incomplete("a configuration does not contain 10,000 valid Q-errors")
    return metrics


def _paired_comparison(all_rows: list[dict[str, Any]], b5_rows: list[dict[str, Any]],
                       secondary_rows: list[dict[str, Any]], all_metrics: dict[str, Any],
                       b5_metrics: dict[str, Any], secondary_metrics: dict[str, Any]) -> dict[str, Any]:
    def by_query(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {row["query_id"]: row for row in rows}
    all_by_id, b5_by_id, secondary_by_id = map(by_query, (all_rows, b5_rows, secondary_rows))
    if set(all_by_id) != set(b5_by_id) or set(all_by_id) != set(secondary_by_id):
        raise Inconclusive("ALL and B5 raw observations do not have identical Test query IDs")
    if len(all_by_id) != 10_000:
        raise Inconclusive("paired comparison does not contain exactly 10,000 query IDs")
    if any(all_by_id[qid]["true_cardinality"] != b5_by_id[qid]["true_cardinality"]
           or all_by_id[qid]["source_index"] != b5_by_id[qid]["source_index"]
           for qid in all_by_id):
        raise Inconclusive("paired ALL/B5 truth or source-index identity differs")

    paired = [
        (all_by_id[qid], b5_by_id[qid], secondary_by_id[qid])
        for qid in sorted(all_by_id, key=lambda qid: all_by_id[qid]["source_index"])
    ]
    deltas = np.asarray([a["qerror"] - b["qerror"] for a, b, _c in paired], dtype=np.float64)
    plan_changed = sum(a["estimate_plan_rows"] != b["estimate_plan_rows"] for a, b, _c in paired)
    improved_all = int(np.sum(deltas < 0))
    degraded_all = int(np.sum(deltas > 0))
    unchanged = int(np.sum(deltas == 0))
    selection_changed = sum(a["mcv_selection_ids"] != b["mcv_selection_ids"]
                            for a, b, _c in paired)
    estimate_changed = sum(a["mcv_estimate_ids"] != b["mcv_estimate_ids"]
                           for a, b, _c in paired)

    shared_usage: dict[str, Any] = {}
    for candidate_id in sorted(B5_IDS):
        shared_usage[candidate_id] = {}
        for config_id, rows in ((ALL_CONFIGS[0], all_rows),
                                (ALL_CONFIGS[1], secondary_rows),
                                (B5_CONFIG, b5_rows)):
            shared_usage[candidate_id][config_id] = {
                "queries_with_mcv_selection": sum(candidate_id in row["mcv_selection_ids"] for row in rows),
                "queries_with_mcv_estimate": sum(candidate_id in row["mcv_estimate_ids"] for row in rows),
                "selection_event_count": sum(
                    event["candidate_id"] == candidate_id and event["type"] == "mcv_selection"
                    for row in rows for event in row["mcv_events"]),
                "estimate_event_count": sum(
                    event["candidate_id"] == candidate_id and event["type"] == "mcv_estimate"
                    for row in rows for event in row["mcv_events"]),
            }

    new_candidate_usage = {}
    for config_id, rows in ((ALL_CONFIGS[0], all_rows), (ALL_CONFIGS[1], secondary_rows)):
        selection_counts = Counter()
        estimate_counts = Counter()
        selection_queries = estimate_queries = selection_or_estimate_queries = 0
        for row in rows:
            selected_new = set(row["mcv_selection_ids"]) - B5_IDS
            estimated_new = set(row["mcv_estimate_ids"]) - B5_IDS
            selection_queries += bool(selected_new)
            estimate_queries += bool(estimated_new)
            selection_or_estimate_queries += bool(selected_new or estimated_new)
            selection_counts.update(selected_new)
            estimate_counts.update(estimated_new)
        new_candidate_usage[config_id] = {
            "queries_with_any_new_candidate_selected": selection_queries,
            "queries_with_any_new_candidate_estimated": estimate_queries,
            "queries_with_any_new_candidate_selected_or_estimated": selection_or_estimate_queries,
            "top_new_candidates_by_selection_queries": [
                {"candidate_id": candidate_id, "queries": count}
                for candidate_id, count in selection_counts.most_common(10)
            ],
            "top_new_candidates_by_estimate_queries": [
                {"candidate_id": candidate_id, "queries": count}
                for candidate_id, count in estimate_counts.most_common(10)
            ],
        }

    def ranked_band(rows: list[dict[str, Any]]) -> set[str]:
        ordered = sorted(rows, key=lambda row: (row["qerror"], row["query_id"]))
        return {row["query_id"] for row in ordered[9400:9601]}

    all_band = ranked_band(all_rows)
    b5_band = ranked_band(b5_rows)
    band_union = all_band | b5_band
    band_pairs = [(all_by_id[qid], b5_by_id[qid]) for qid in band_union]
    band_changed_q = sum(a["qerror"] != b["qerror"] for a, b in band_pairs)
    band_changed_plan = sum(a["estimate_plan_rows"] != b["estimate_plan_rows"] for a, b in band_pairs)
    p95_examples = []
    for a, b in sorted(band_pairs, key=lambda pair: (-abs(pair[0]["qerror"] - pair[1]["qerror"]), pair[0]["query_id"]))[:12]:
        p95_examples.append({
            "query_id": a["query_id"],
            "all_random01_rank_in_ascending_qerror": None,
            "all_random01_plan_rows": a["estimate_plan_rows"],
            "all_random01_qerror": a["qerror"],
            "all_random01_mcv_selection_ids": a["mcv_selection_ids"],
            "b5_plan_rows": b["estimate_plan_rows"],
            "b5_qerror": b["qerror"],
            "b5_mcv_selection_ids": b["mcv_selection_ids"],
            "qerror_delta_all_minus_b5": a["qerror"] - b["qerror"],
        })
    all_sorted = sorted(all_rows, key=lambda row: (row["qerror"], row["query_id"]))
    b5_sorted = sorted(b5_rows, key=lambda row: (row["qerror"], row["query_id"]))
    rank_by_id_all = {row["query_id"]: rank for rank, row in enumerate(all_sorted)}
    rank_by_id_b5 = {row["query_id"]: rank for rank, row in enumerate(b5_sorted)}
    for row in p95_examples:
        qid = row["query_id"]
        row["all_random01_rank_in_ascending_qerror"] = rank_by_id_all[qid]
        row["b5_rank_in_ascending_qerror"] = rank_by_id_b5[qid]

    delta_summary = {
        "count": int(deltas.size),
        "mean": float(np.mean(deltas)),
        "min": float(np.min(deltas)),
        "p01": float(np.percentile(deltas, 1)),
        "p05": float(np.percentile(deltas, 5)),
        "p25": float(np.percentile(deltas, 25)),
        "p50": float(np.percentile(deltas, 50)),
        "p75": float(np.percentile(deltas, 75)),
        "p95": float(np.percentile(deltas, 95)),
        "p99": float(np.percentile(deltas, 99)),
        "max": float(np.max(deltas)),
    }
    return {
        "status": "COMPLETE",
        "primary_comparison": "ALL random-01 minus B5 matched priority",
        "paired_query_count": len(paired),
        "all_minus_b5_p95": float(all_metrics["qerror"]["p95"] - b5_metrics["qerror"]["p95"]),
        "plan_rows_changed_count": int(plan_changed),
        "qerror_improved_for_all_count": improved_all,
        "qerror_degraded_for_all_count": degraded_all,
        "qerror_unchanged_count": unchanged,
        "qerror_delta_all_minus_b5_distribution": delta_summary,
        "mcv_selection_sequence_changed_count": int(selection_changed),
        "mcv_estimate_sequence_changed_count": int(estimate_changed),
        "mcv_usage_by_shared_candidate_id": shared_usage,
        "all_new_candidate_usage": new_candidate_usage,
        "p95_neighborhood": {
            "sort_order": "Q-error ascending, query_id ascending for ties",
            "rank_window_zero_based_inclusive": [9400, 9600],
            "all_random01_window_size": len(all_band),
            "b5_window_size": len(b5_band),
            "overlap_query_count": len(all_band & b5_band),
            "union_query_count": len(band_union),
            "plan_rows_changed_in_union": int(band_changed_plan),
            "qerror_changed_in_union": int(band_changed_q),
            "largest_absolute_qerror_differences": p95_examples,
        },
        "secondary_unmatched_random02": {
            "role": "descriptive only; shared-object OID order differs from B5",
            "p50": secondary_metrics["qerror"]["p50"],
            "p95": secondary_metrics["qerror"]["p95"],
            "p99": secondary_metrics["qerror"]["p99"],
            "mean": secondary_metrics["qerror"]["mean"],
        },
        "limitations": [
            "Fixed Forest10 official Test workload and these configurations only; no Test-population uncertainty interval.",
            "The two compared configurations have matched relative order only for the five shared B5 candidates; additional ALL objects may precede and interact with them.",
            "This is an installed-set contrast at a fixed shared-object priority, not proof that a specific MCV object blocked another.",
            "Issue #135 random-02 is an unmatched-order secondary description.",
            "No PESS/EMPTY arm, additional dataset, repeated configuration, or significance test was run.",
        ],
    }


def write_findings(path: Path, manifest: dict[str, Any], catalog: dict[str, Any],
                   comparison: dict[str, Any]) -> None:
    metrics = manifest.get("config_metrics", {})
    all_metrics = manifest.get("all_reference_metrics", {})
    b5 = metrics.get("qerror", {})
    all01 = all_metrics.get(ALL_CONFIGS[0], {}).get("qerror", {})
    all02 = all_metrics.get(ALL_CONFIGS[1], {}).get("qerror", {})
    p95 = comparison.get("p95_neighborhood", {})
    lines = [
        "# Issue #133 Forest10 ALL versus matched Nominal B5",
        "",
        f"**Status:** `{manifest.get('status')}`.",
        "",
        "This is a one-configuration, fixed-workload installed-set comparison. B5's five shared candidate IDs were created in their predeclared ALL random-01 relative order. ALL has 40 additional candidate definitions, which may precede and interact with the shared objects; the contrast is therefore not a claim that every mechanism is isolated.",
        "",
        "## Frozen selection and order",
        "",
        f"- Frozen Issue #99 Nominal B5 IDs: `{', '.join(sorted(B5_IDS))}`.",
        f"- ALL random-01 projection / B5 CREATE order: `{', '.join(B5_ORDER)}`.",
        f"- ALL random-02 projection (not matched): `{', '.join(manifest['random02_projection'])}`.",
        f"- B5 order SHA-256: `{manifest['b5_order_sha256']}`.",
        "- The random-01 and random-02 projections differ; random-01 was frozen as primary before this B5 Test run. random-02 is descriptive only.",
        "",
        "## Physical-state verification",
        "",
        f"- PostgreSQL: 16.14 source `{manifest['postgresql_source_commit']}`; pinned binary hashes verified.",
        f"- B5 CREATE/target/ANALYZE counts: {catalog.get('create_count')}/{catalog.get('target_count')}/{catalog.get('analyze_count')}.",
        f"- Exact five-object catalog and ascending OID order: `{catalog.get('status')}`.",
        f"- Fixed Issue #99 sample SHA-256: `{catalog.get('sample_sha256')}`; ordinary column statistics match ALL: `{catalog.get('issue135_ordinary_stats_match')}`.",
        f"- Five candidate-ID keyed MCV states/content match both ALL arms: `{catalog.get('issue135_shared_candidate_content_match')}`.",
        "- B5 MCV payload states: " + json.dumps(catalog.get("candidate_payload_state_counts"), sort_keys=True) + ".",
        "",
        "## Test Q-error",
        "",
        "All three configurations use the same 10,000 official query IDs/truths and Issue #101 zero-aware Q-error/NumPy quantile implementation.",
        "",
        "| Configuration | P50 | P95 | P99 | Mean |",
        "|---|---:|---:|---:|---:|",
        f"| ALL random-01 (primary) | {all01.get('p50')} | {all01.get('p95')} | {all01.get('p99')} | {all01.get('mean')} |",
        f"| ALL random-02 (unmatched secondary) | {all02.get('p50')} | {all02.get('p95')} | {all02.get('p99')} | {all02.get('mean')} |",
        f"| Nominal B5 matched to random-01 | {b5.get('p50')} | {b5.get('p95')} | {b5.get('p99')} | {b5.get('mean')} |",
        "",
        f"Primary contrast: `P95(ALL random-01) - P95(B5) = {comparison.get('all_minus_b5_p95')}`. Positive values mean worse P95 Q-error for ALL.",
        "",
        "## Paired query comparison (ALL random-01 minus B5)",
        "",
        f"- Plan Rows changed: {comparison.get('plan_rows_changed_count')}/10,000.",
        f"- Q-error lower for ALL: {comparison.get('qerror_improved_for_all_count')}; higher for ALL: {comparison.get('qerror_degraded_for_all_count')}; unchanged: {comparison.get('qerror_unchanged_count')}.",
        f"- Q-error delta distribution: `{json.dumps(comparison.get('qerror_delta_all_minus_b5_distribution'), sort_keys=True)}`.",
        f"- MCV selection sequence changed: {comparison.get('mcv_selection_sequence_changed_count')}; estimate sequence changed: {comparison.get('mcv_estimate_sequence_changed_count')}.",
        f"- P95-rank neighborhood: {p95.get('union_query_count')} queries in the union of the two predeclared 201-rank bands; Plan Rows changed for {p95.get('plan_rows_changed_in_union')}, Q-error changed for {p95.get('qerror_changed_in_union')}.",
        "",
        "### Shared-object MCV use frequency",
        "",
        "| Candidate ID | ALL random-01 queries selected / estimated | B5 queries selected / estimated |",
        "|---|---:|---:|",
    ]
    usage = comparison.get("mcv_usage_by_shared_candidate_id", {})
    for candidate_id in sorted(B5_IDS):
        a = usage.get(candidate_id, {}).get(ALL_CONFIGS[0], {})
        b = usage.get(candidate_id, {}).get(B5_CONFIG, {})
        lines.append(
            f"| {candidate_id} | {a.get('queries_with_mcv_selection', 'n/a')} / {a.get('queries_with_mcv_estimate', 'n/a')} | "
            f"{b.get('queries_with_mcv_selection', 'n/a')} / {b.get('queries_with_mcv_estimate', 'n/a')} |"
        )
    new_use = comparison.get("all_new_candidate_usage", {}).get(ALL_CONFIGS[0], {})
    lines.extend([
        "",
        f"ALL-only candidate IDs participated in selection for {new_use.get('queries_with_any_new_candidate_selected')} queries and in MCV estimation for {new_use.get('queries_with_any_new_candidate_estimated')} queries (union: {new_use.get('queries_with_any_new_candidate_selected_or_estimated')}).",
        "",
        "### P95-neighborhood query examples",
        "",
        "| Query ID | ALL Plan Rows / Q-error / selected IDs | B5 Plan Rows / Q-error / selected IDs | Δ Q-error (ALL−B5) |",
        "|---|---|---|---:|",
    ])
    for row in p95.get("largest_absolute_qerror_differences", []):
        lines.append(
            f"| `{row['query_id']}` | {row['all_random01_plan_rows']} / {row['all_random01_qerror']} / "
            f"`{', '.join(row['all_random01_mcv_selection_ids'])}` | "
            f"{row['b5_plan_rows']} / {row['b5_qerror']} / `{', '.join(row['b5_mcv_selection_ids'])}` | "
            f"{row['qerror_delta_all_minus_b5']} |"
        )
    lines.extend([
        "",
        "## Interpretation and limits",
        "",
        "The P95 result answers the predeclared fixed-priority comparison for this Forest10 Test workload only. Query-level differences, MCV sequence changes, and ALL-only candidate use are descriptive. Shared-object priority matching does not remove interactions from the 40 additional ALL objects, and no particular blocking mechanism is established.",
        "",
        "Issue #135 raw observations and all prior ALL run files remain unchanged outside Git. This run stores only its B5 query archive under ESS_RUNTIME_PARENT; Git contains the compact summary, manifest, catalog audit, and findings.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def publish_attempt(run_manifest: dict[str, Any], catalog_audit: dict[str, Any] | None,
                    comparison: dict[str, Any] | None, environment: dict[str, Any],
                    prevalidation_audit: dict[str, Any] | None = None) -> None:
    attempt = HERE / "attempts" / str(run_manifest["run_id"])
    attempt.mkdir(parents=True, exist_ok=False)
    base.atomic_json(attempt / "run-manifest.json", compact_run_manifest(run_manifest))
    base.atomic_json(attempt / "environment.json", environment)
    if catalog_audit is not None:
        base.atomic_json(attempt / "catalog-audit.json", catalog_audit)
    elif prevalidation_audit is not None:
        prevalidation_audit["status"] = "PREVALIDATION_FAILED"
        base.atomic_json(attempt / "catalog-audit.json", prevalidation_audit)
    if comparison is not None:
        base.atomic_json(attempt / "comparison-summary.json", comparison)
    write_findings(attempt / "findings.md", run_manifest,
                   catalog_audit or {}, comparison or {})


def compact_run_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "format", "issue", "run_id", "status", "phase", "failure", "source_commit_before_test",
        "protocol_sha256", "protocol_path", "frozen_b5_case_id", "frozen_b5_ids", "b5_create_order",
        "b5_order_sha256", "random01_projection", "random02_projection", "primary_all_configuration",
        "all_archive_preflight", "input_identity", "postgresql_build", "postgresql_source_commit",
        "preexisting_postgres_processes_at_start",
        "environment", "catalog_audit_status", "catalog_fingerprint_sha256", "sample_sha256",
        "ordinary_stats_sha256", "attempted_explain_calls", "actual_explain_calls", "query_count",
        "diagnostics_status_counts", "config_metrics", "all_reference_metrics", "comparison",
        "raw_query_archive", "resource_usage", "completed_at_utc", "server_log_sha256",
    )
    return {key: manifest.get(key) for key in keys if key in manifest}


def record_preflight_failure(protocol: dict[str, Any], source_commit: str,
                             run_id: str, phase: str, exc: Exception) -> Path:
    """Keep a small durable record when pinned inputs/environment fail preflight."""
    runtime = issue101.configured_root("ESS_RUNTIME_PARENT")
    runs = issue101.runtime_runs("ess-research", 133)
    runs.mkdir(parents=True, exist_ok=True)
    run_root = runs / run_id
    run_root.mkdir(exist_ok=False)
    failure = {
        "class": type(exc).__name__,
        "message": str(exc)[:4000],
        "phase": phase,
    }
    environment = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "filesystem": shutil.disk_usage(runtime)._asdict(),
        "preexisting_postgres_processes": base.existing_postgres_processes(),
        "database_started_by_attempt": False,
    }
    manifest = {
        "format": "ess-issue133-forest10-b5-control-run-v1",
        "issue": 133,
        "run_id": run_id,
        "status": "INCONCLUSIVE",
        "phase": phase,
        "failure": failure,
        "source_commit_before_test": source_commit,
        "protocol_sha256": base.sha256_file(PROTOCOL_PATH),
        "protocol_path": str(PROTOCOL_PATH),
        "frozen_b5_case_id": "forest10-nominal-b5",
        "frozen_b5_ids": sorted(B5_IDS),
        "b5_create_order": list(B5_ORDER),
        "b5_order_sha256": protocol["order_matching"]["b5_create_order_sha256"],
        "random01_projection": protocol["order_matching"]["random01_nominal_b5_projection"],
        "random02_projection": protocol["order_matching"]["random02_nominal_b5_projection"],
        "primary_all_configuration": ALL_CONFIGS[0],
        "all_archive_preflight": "FAILED",
        "input_identity": None,
        "environment": environment,
        "attempted_explain_calls": 0,
        "actual_explain_calls": 0,
        "query_count": 0,
        "catalog_audit_status": "NOT_RUN",
        "config_metrics": {},
        "all_reference_metrics": {},
        "comparison": {},
        "resource_usage": {},
    }
    base.atomic_json(run_root / "run-manifest.json", manifest)
    base.atomic_json(run_root / "environment.json", environment)
    base.append_event(run_root / "phase-events.jsonl", "preflight_failed", failure)
    attempt = HERE / "attempts" / run_id
    attempt.mkdir(parents=True, exist_ok=False)
    base.atomic_json(attempt / "run-manifest.json", compact_run_manifest(manifest))
    base.atomic_json(attempt / "environment.json", environment)
    (attempt / "findings.md").write_text(
        "# Issue #133 Forest10 ALL versus matched Nominal B5\n\n"
        f"**Status:** `INCONCLUSIVE` (preflight stopped before PostgreSQL startup).\n\n"
        f"- Phase: `{phase}`.\n- Failure: `{type(exc).__name__}: {str(exc)}`\n"
        "- No B5 Test EXPLAIN was issued.\n",
        encoding="utf-8",
    )
    return run_root


def run(run_id: str | None = None) -> Path:
    protocol = read_frozen_protocol()
    source_commit = base.require_clean_committed_worktree()
    runtime = issue101.configured_root("ESS_RUNTIME_PARENT")
    runs = issue101.runtime_runs("ess-research", 133)
    run_id = run_id or f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-issue133-forest10-b5-{uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be a safe path component")
    try:
        all_evidence = verify_saved_all(protocol)
        all_protocol = base.read_protocol()
        prefix, pg_build = base.verify_pg_install(all_protocol)
        preexisting = base.existing_postgres_processes()
        if preexisting:
            raise Inconclusive(f"refusing to start beside existing PostgreSQL processes: {preexisting}")
        if shutil.disk_usage(runtime).free < protocol["resource_envelope"]["global_filesystem_free_space_stop_bytes"]:
            raise Inconclusive("ESS_RUNTIME_PARENT filesystem has less than the frozen 5 GiB free-space floor")
    except Exception as exc:
        return record_preflight_failure(protocol, source_commit, run_id,
                                        "saved_all_or_environment_preflight", exc)
    runs.mkdir(parents=True, exist_ok=True)
    run_root = runs / run_id
    run_root.mkdir(exist_ok=False)
    for name in ("clusters", "input", "samples", "logs", "sql"):
        (run_root / name).mkdir()
    raw_path = run_root / "raw-observations.jsonl.gz"
    protocol_sha = base.sha256_file(PROTOCOL_PATH)
    environment: dict[str, Any] = {}
    catalog: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    cluster: dict[str, Any] | None = None
    socket_owner = None
    monitor = base.ResourceMonitor(
        run_root,
        early_seconds=protocol["resource_envelope"]["early_stop_wall_seconds"],
        hard_seconds=protocol["resource_envelope"]["hard_wall_seconds"],
        early_bytes=protocol["resource_envelope"]["early_stop_allocated_bytes"],
        hard_bytes=protocol["resource_envelope"]["hard_allocated_bytes"],
    )
    start_time = time.monotonic()
    cpu_start = time.process_time()
    manifest: dict[str, Any] = {
        "format": "ess-issue133-forest10-b5-control-run-v1",
        "issue": 133,
        "run_id": run_id,
        "status": "INCOMPLETE",
        "phase": "initialization",
        "failure": None,
        "source_commit_before_test": source_commit,
        "protocol_sha256": protocol_sha,
        "protocol_path": str(PROTOCOL_PATH),
        "frozen_b5_case_id": "forest10-nominal-b5",
        "frozen_b5_ids": sorted(B5_IDS),
        "b5_create_order": list(B5_ORDER),
        "b5_order_sha256": protocol["order_matching"]["b5_create_order_sha256"],
        "random01_projection": protocol["order_matching"]["random01_nominal_b5_projection"],
        "random02_projection": protocol["order_matching"]["random02_nominal_b5_projection"],
        "primary_all_configuration": ALL_CONFIGS[0],
        "all_archive_preflight": all_evidence["status"],
        "input_identity": None,
        "postgresql_build": pg_build,
        "postgresql_source_commit": protocol["inputs_and_environment"]["postgresql_source_commit"],
        "preexisting_postgres_processes_at_start": preexisting,
        "environment": {},
        "attempted_explain_calls": 0,
        "actual_explain_calls": 0,
        "query_count": 0,
        "diagnostics_status_counts": {},
        "catalog_audit_status": "NOT_RUN",
        "catalog_fingerprint_sha256": None,
        "sample_sha256": None,
        "ordinary_stats_sha256": None,
        "config_metrics": None,
        "all_reference_metrics": all_evidence["all_metrics_recomputed"],
        "comparison": None,
        "raw_query_archive": None,
        "resource_usage": {},
    }
    base.atomic_json(run_root / "run-manifest.json", manifest)
    base.append_event(run_root / "phase-events.jsonl", "initialization", {
        "source_commit_before_test": source_commit,
        "protocol_sha256": protocol_sha,
        "all_raw_archive_sha256": all_evidence["raw_archive_sha256"],
        "run_root": str(run_root),
    })

    with monitor:
        try:
            manifest["phase"] = "official_input_preflight"
            base.atomic_json(run_root / "run-manifest.json", manifest)
            issue101_protocol = issue101.read_protocol()
            input_dir = run_root / "input" / DATASET
            csv_path, queries, truths, input_identity = issue101.extract_test_inputs(DATASET, input_dir)
            rendered = base.query_identity(queries, truths)
            expected_input = protocol["inputs_and_environment"]
            for key, value in {
                "csv_sha256": expected_input["forest10_full_csv_sha256"],
                "workload_pickle_sha256": expected_input["workload_pickle_sha256"],
                "labels_pickle_sha256": expected_input["test_labels_container_sha256"],
                "test_truth_canonical_sha256": expected_input["test_truth_canonical_sha256"],
            }.items():
                if input_identity.get(key) != value:
                    raise Inconclusive(f"official Test source identity changed at {key}")
            if (rendered["query_count"] != 10_000
                    or rendered["query_ids_sha256"] != all_evidence["input_identity"]["query_ids_sha256"]
                    or rendered["rendered_test_sql_sha256"] != all_evidence["input_identity"]["rendered_test_sql_sha256"]
                    or rendered["test_truth_canonical_sha256"] != all_evidence["input_identity"]["test_truth_canonical_sha256"]):
                raise Inconclusive("B5 official Test query/truth identity differs from Issue #135")
            if [(row["query_id"], truth) for row, truth in zip(queries, truths, strict=True)] != [
                    (row["query_id"], row["true_cardinality"])
                    for row in all_evidence["all_rows_by_config"][ALL_CONFIGS[0]]]:
                raise Inconclusive("B5 Test query IDs/truths do not pair with Issue #135 raw rows")

            helpers, run_formal, helper_hashes = issue101.load_pinned_helpers(run_root)
            sample, sample_identity = issue101.load_frozen_sample(DATASET, run_root, helpers, issue101_protocol)
            sample_sha = expected_input["issue99_fixed_analyze_sample_sha256"]
            if sample_identity["sha256"] != sample_sha or base.sha256_file(sample) != sample_sha:
                raise Inconclusive("copied Issue #99 frozen sample SHA mismatch")
            csv_sha = base.sha256_file(csv_path)
            if csv_sha != expected_input["forest10_full_csv_sha256"]:
                raise Inconclusive("extracted full Forest10 source CSV SHA mismatch")
            input_record = {**input_identity, **rendered,
                            "source_csv_sha256": csv_sha,
                            "sample_identity": sample_identity,
                            "issue135_query_truth_identity_sha256": all_evidence["query_truth_order_identity_sha256"]}
            manifest["input_identity"] = input_record
            manifest["issue99_helper_sha256"] = helper_hashes
            environment = base.environment_snapshot(prefix, pg_build, run_root)
            environment["preexisting_postgres_processes_at_start"] = preexisting
            manifest["environment"] = environment
            base.atomic_json(run_root / "environment.json", environment)
            base.atomic_json(run_root / "input-preflight.json", input_record)
            base.atomic_json(run_root / "run-manifest.json", manifest)
            base.append_event(run_root / "phase-events.jsonl", "official_input_preflight", {
                "test_query_count": len(queries),
                "source_csv_sha256": csv_sha,
                "sample_sha256": sample_sha,
                "query_ids_sha256": rendered["query_ids_sha256"],
                "rendered_test_sql_sha256": rendered["rendered_test_sql_sha256"],
            })
            monitor.checkpoint()

            candidates = issue101.candidate_map(DATASET)
            source_columns, pg_columns, source_rows, _csv_sha, table_name = issue101.issue99.dataset_spec(DATASET)
            if source_rows != 581_012 or table_name != "public.forest10":
                raise Inconclusive("Issue #99 Forest10 full-table contract changed")
            cluster_root = run_root / "clusters" / B5_CONFIG
            cluster, socket_owner = base.create_cluster(prefix, cluster_root, helpers, monitor, B5_CONFIG)
            cluster["dataset"] = DATASET
            table_load = issue101.configure_source_table(helpers, prefix, cluster, DATASET, csv_path, sample)
            if int(table_load["full_source_rows"]) != 581_012:
                raise Inconclusive("B5 full Forest10 source import row count mismatch")
            manifest["phase"] = "b5_create_analyze_catalog_audit"
            manifest["table_load"] = table_load
            base.atomic_json(run_root / "run-manifest.json", manifest)
            base.append_event(run_root / "phase-events.jsonl", "b5_setup_start", {
                "create_count": 5, "target_count": 5, "analyze_count": 1,
                "b5_create_order": list(B5_ORDER),
            })
            setup_start = time.monotonic()
            helper_ledger = issue101.run_config(
                run_formal, prefix, cluster, DATASET, candidates, B5_ORDER, sample)
            base.atomic_json(run_root / "helper-ledger.json", helper_ledger)
            catalog = build_b5_catalog_audit(
                protocol, all_evidence, {"permutation": list(B5_ORDER)}, candidates,
                helper_ledger, helpers, prefix, cluster, sample, sample_sha, input_identity,
                run_root,
            )
            catalog["setup_elapsed_seconds"] = round(time.monotonic() - setup_start, 3)
            catalog["helper_ledger"] = helper_ledger
            catalog["cluster_identity"] = cluster.get("identity")
            manifest["catalog_audit_status"] = "PASS"
            manifest["catalog_fingerprint_sha256"] = json_sha256({
                candidate_id: catalog_row_signature(row)
                for candidate_id, row in ((r["candidate_id"], r) for r in catalog["catalog"])
            })
            manifest["sample_sha256"] = sample_sha
            manifest["ordinary_stats_sha256"] = catalog["ordinary_column_stats"]["sha256"]
            base.atomic_json(run_root / "catalog-audit.json", catalog)
            base.append_event(run_root / "phase-events.jsonl", "b5_setup_and_pretest_match", {
                "status": "PASS",
                "setup_elapsed_seconds": catalog["setup_elapsed_seconds"],
                "oid_order_verified": catalog["catalog_oid_order_candidate_ids"] == list(B5_ORDER),
                "mcv_content_matches_all": catalog["issue135_shared_candidate_content_match"],
                "ordinary_stats_match_all": catalog["issue135_ordinary_stats_match"],
                "sample_matches_all": catalog["issue135_sample_match"],
            })
            monitor.checkpoint()

            # Final live read immediately before Test: no EXPLAIN is issued if
            # a catalog/data/sample state has drifted since the full audit.
            verify_live_b5_state(catalog, helpers, prefix, cluster, candidates, sample)
            manifest["phase"] = "official_test_b5"
            base.atomic_json(run_root / "run-manifest.json", manifest)
            base.append_event(run_root / "phase-events.jsonl", "official_test_b5_start", {
                "configuration_id": B5_CONFIG,
                "query_count": len(queries),
                "parallel_clients": 6,
            })
            sql_root = run_root / "sql" / B5_CONFIG
            log_root = run_root / "logs" / B5_CONFIG
            batch_start = time.monotonic()
            observations, plan_batch = base.bounded_plan_batch(
                prefix, cluster, queries, sql_root, catalog["oid_to_candidate_id"], log_root, monitor)
            order_rows = issue105.rows_for_config(
                DATASET, "b5-nominal-matched-random01", B5_ORDER, queries, truths, observations)
            member_info = issue105.append_raw_member(raw_path, order_rows)
            batch_seconds = round(time.monotonic() - batch_start, 3)
            metrics = issue105.metrics_for_rows(order_rows)
            diagnostics_valid = sum(row.get("diagnostics_status") in {"complete", "empty"}
                                    for row in order_rows)
            manifest["attempted_explain_calls"] = int(plan_batch["attempted_markers"])
            manifest["actual_explain_calls"] = int(plan_batch["attempted_markers"])
            manifest["query_count"] = len(order_rows)
            manifest["diagnostics_status_counts"] = plan_batch["diagnostics_status_counts"]
            manifest["config_metrics"] = metrics
            manifest["plan_batch"] = plan_batch
            manifest["plan_batch_seconds"] = batch_seconds
            manifest["raw_member"] = member_info
            manifest["phase"] = "official_test_b5_complete"
            if (metrics.get("valid_count") != 10_000 or diagnostics_valid != 10_000
                    or len(order_rows) != 10_000 or plan_batch["attempted_markers"] != 10_000):
                manifest["status"] = "INCOMPLETE"
                raise Incomplete("B5 Test does not have 10,000 valid Plan Rows and complete diagnostics")
            manifest["comparison"] = _paired_comparison(
                all_evidence["all_rows_by_config"][ALL_CONFIGS[0]], order_rows,
                all_evidence["all_rows_by_config"][ALL_CONFIGS[1]],
                all_evidence["all_metrics_recomputed"][ALL_CONFIGS[0]], metrics,
                all_evidence["all_metrics_recomputed"][ALL_CONFIGS[1]],
            )
            manifest["all_reference_metrics"] = all_evidence["all_metrics_recomputed"]
            manifest["status"] = "COMPLETE"
            manifest["phase"] = "complete"
            base.append_event(run_root / "phase-events.jsonl", "official_test_b5_complete", {
                "status": "COMPLETE",
                "valid_queries": metrics["valid_count"],
                "diagnostics_valid": diagnostics_valid,
                "actual_explain_calls": manifest["actual_explain_calls"],
                "plan_batch_seconds": batch_seconds,
                "raw_member_sha256": member_info["raw_member_sha256"],
            })
        except Inconclusive as exc:
            manifest["status"] = "INCONCLUSIVE"
            manifest["failure"] = {"class": type(exc).__name__,
                                   "message": str(exc)[:4000],
                                   "phase": manifest.get("phase")}
        except BaseException as exc:
            if monitor.stop_event.is_set() or str(manifest.get("phase", "")).startswith("official_test"):
                manifest["status"] = "INCOMPLETE"
            else:
                manifest["status"] = "INCONCLUSIVE"
            manifest["failure"] = {"class": type(exc).__name__,
                                   "message": str(exc)[:4000],
                                   "phase": manifest.get("phase")}
        finally:
            if cluster is not None:
                try:
                    base.stop_cluster(prefix, cluster)
                except Exception as exc:
                    manifest.setdefault("cleanup_errors", []).append(str(exc)[:1000])
            if socket_owner is not None:
                socket_owner.cleanup()

    usage = {
        "elapsed_wall_seconds": round(time.monotonic() - start_time, 3),
        "runner_process_cpu_seconds": round(time.process_time() - cpu_start, 3),
        "runner_peak_rss_kib": int(__import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss),
        "peak_run_directory_allocated_bytes": monitor.peak_bytes,
        "final_run_directory_allocated_bytes": base.allocated_bytes(run_root),
        "minimum_global_filesystem_free_bytes": monitor.minimum_global_free,
        "early_or_hard_stop_reason": monitor.stop_reason,
        "cpu_note": "runner process CPU/RSS only; PostgreSQL backend CPU is not separately attributed",
    }
    manifest["resource_usage"] = usage
    manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["raw_query_archive"] = None
    if raw_path.is_file():
        manifest["raw_query_archive"] = {
            "path_under_ess_runtime_parent": str(raw_path.relative_to(runtime)),
            "bytes": raw_path.stat().st_size,
            "sha256": base.sha256_file(raw_path),
        }
    server_log = run_root / "clusters" / B5_CONFIG / "server.log"
    manifest["server_log_path"] = str(server_log) if server_log.is_file() else None
    manifest["server_log_sha256"] = base.sha256_file(server_log) if server_log.is_file() else None
    manifest["protocol_sha256"] = protocol_sha
    base.atomic_json(run_root / "run-manifest.json", manifest)
    base.atomic_json(run_root / "environment.json", environment)
    base.append_event(run_root / "phase-events.jsonl", "finalized", {
        "status": manifest.get("status"),
        "actual_explain_calls": manifest.get("actual_explain_calls"),
        "resource_usage": usage,
    })
    preaudit_path = run_root / "catalog-prevalidation-snapshot.json"
    preaudit = json.loads(preaudit_path.read_text(encoding="utf-8")) if preaudit_path.is_file() else None
    publish_attempt(manifest, catalog, manifest.get("comparison"), environment, preaudit)
    return run_root


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    run_root = run(args.run_id)
    manifest = json.loads((run_root / "run-manifest.json").read_text())
    print(json.dumps({key: manifest.get(key) for key in (
        "run_id", "status", "phase", "actual_explain_calls", "resource_usage", "failure",
        "raw_query_archive")}, ensure_ascii=False, sort_keys=True))
    return 0 if manifest.get("status") == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
