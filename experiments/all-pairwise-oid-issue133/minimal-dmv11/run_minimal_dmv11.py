"""Run the frozen three-arm DMV11 ALL-order and matched-Nominal-B5 experiment.

The implementation reuses the Issue #101 input/sample/DDL helpers and the
Issue #105 catalog and Q-error definitions. OID attribution and the raw ESS
diagnostic status are recorded as separate fields.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL_PATH = HERE / "protocol-v1.json"
BASE_DIR = HERE.parent / "minimal-forest10"
ISSUE101_DIR = ROOT / "experiments/arecel-test-generalization-issue101"
ISSUE105_DIR = ROOT / "experiments/oid-order-stress-test-issue105"
DATASET = "dmv11"
ALL01 = "dmv11-all-random-01"
ALL02 = "dmv11-all-random-02"
B5 = "dmv11-b5-nominal-matched"
CONFIGS = (ALL01, ALL02, B5)
PARALLEL_CLIENTS = 6
GIB = 1024**3

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(ISSUE101_DIR))
sys.path.insert(0, str(ISSUE105_DIR))
import run_minimal_forest10 as shared  # noqa: E402

issue101 = shared.issue101
issue105 = shared.issue105


class Inconclusive(RuntimeError):
    """An identity or physical-state mismatch invalidates a planned contrast."""


class Incomplete(RuntimeError):
    """A physical arm, Plan Rows set, or required diagnostics are incomplete."""


def sha256_file(path: Path) -> str:
    return shared.sha256_file(path)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(issue101.json_bytes(value)).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    shared.atomic_json(path, value)


def append_event(path: Path, phase: str, detail: dict[str, Any]) -> None:
    shared.append_event(path, phase, detail)


def normalize_oid_map(raw: dict[Any, Any]) -> dict[int, str]:
    """Canonicalize JSON string keys and live numeric catalog OIDs to int keys."""
    result: dict[int, str] = {}
    for key, candidate_id in raw.items():
        if isinstance(key, bool):
            raise Inconclusive("boolean is not a valid statistics OID")
        if isinstance(key, int):
            oid = key
        elif isinstance(key, str) and key.isascii() and key.isdecimal():
            oid = int(key)
        else:
            raise Inconclusive(f"invalid statistics OID key: {key!r}")
        if oid <= 0 or not isinstance(candidate_id, str) or not candidate_id:
            raise Inconclusive(f"invalid OID/candidate mapping: {key!r} -> {candidate_id!r}")
        if oid in result:
            raise Inconclusive(f"duplicate OID after normalization: {oid}")
        result[oid] = candidate_id
    return result


def _event_oid(raw_oid: Any) -> int | None:
    if isinstance(raw_oid, bool):
        return None
    if isinstance(raw_oid, int) and raw_oid > 0:
        return raw_oid
    if isinstance(raw_oid, str) and raw_oid.isascii() and raw_oid.isdecimal():
        oid = int(raw_oid)
        return oid if oid > 0 else None
    return None


def parse_explain_payload(payload: str, raw_oid_map: dict[Any, Any]) -> dict[str, Any]:
    """Parse Plan Rows while retaining raw extension diagnostics unchanged."""
    oid_to_id = normalize_oid_map(raw_oid_map)
    try:
        document = json.loads(payload.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_EXPLAIN_JSON") from exc
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise ValueError("INVALID_EXPLAIN_DOCUMENT")

    try:
        plan_rows = issue101.parse_top_level_plan_rows(payload)
    except (TypeError, ValueError, KeyError) as exc:
        plan_rows = None
        plan_status = f"INVALID_PLAN_ROWS:{type(exc).__name__}"
    else:
        plan_status = "VALID"

    raw_diagnostics = document[0].get("ESS Diagnostics")
    diagnostics = raw_diagnostics if isinstance(raw_diagnostics, dict) else None
    raw_status = diagnostics.get("Status") if diagnostics is not None else None
    raw_events = diagnostics.get("Events") if diagnostics is not None else None
    raw_count = diagnostics.get("Event Count") if diagnostics is not None else None
    structure_status = "PASS"
    if diagnostics is None:
        structure_status = "MISSING_ESS_DIAGNOSTICS"
        events: list[Any] = []
    elif not isinstance(raw_events, list):
        structure_status = "INVALID_EVENTS_FIELD"
        events = []
    else:
        events = raw_events
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count != len(events):
            structure_status = "EVENT_COUNT_MISMATCH"
        elif raw_status not in {"complete", "empty", "incomplete"}:
            structure_status = "INVALID_EXTENSION_STATUS"
        elif raw_status == "empty" and events:
            structure_status = "EMPTY_STATUS_WITH_EVENTS"
        elif raw_status == "complete" and not events:
            structure_status = "COMPLETE_STATUS_WITHOUT_EVENTS"

    annotated: list[dict[str, Any]] = []
    selection_ids: list[str | None] = []
    estimate_ids: list[str | None] = []
    unknown_oids: list[Any] = []
    recognized = set(issue105.MCV_EVENT_TYPES)
    for event in events:
        if not isinstance(event, dict) or event.get("type") not in recognized:
            continue
        event_oid = _event_oid(event.get("stat_oid"))
        candidate_id = oid_to_id.get(event_oid) if event_oid is not None else None
        if candidate_id is None:
            unknown_oids.append(event.get("stat_oid"))
        copied = dict(event)  # Preserve every extension-provided field verbatim.
        copied["candidate_id"] = candidate_id
        annotated.append(copied)
        if event.get("type") == "mcv_selection":
            selection_ids.append(candidate_id)
        elif event.get("type") == "mcv_estimate":
            estimate_ids.append(candidate_id)

    attribution_status = "PASS"
    if unknown_oids:
        attribution_status = "UNKNOWN_STAT_OID"
    elif not annotated:
        attribution_status = "PASS_EMPTY"

    # This field is deliberately the unmodified PostgreSQL status. Mapping or
    # structural failures live in separate columns and never replace it.
    compatibility_status = raw_status if isinstance(raw_status, str) else (
        "MISSING_ESS_DIAGNOSTICS" if diagnostics is None else "MISSING_EXTENSION_STATUS"
    )
    return {
        "status": "VALID" if plan_status == "VALID" else "INVALID_PLAN_ROWS",
        "plan_rows": plan_rows,
        "plan_rows_integrity_status": plan_status,
        "diagnostics_status": compatibility_status,
        "extension_diagnostics_status": raw_status,
        "diagnostics_integrity_status": structure_status,
        "candidate_id_attribution_status": attribution_status,
        "diagnostics_event_count": raw_count,
        "mcv_events": annotated,
        "mcv_selection_ids": selection_ids,
        "mcv_estimate_ids": estimate_ids,
        "unknown_stat_oids": unknown_oids,
        "raw_ess_diagnostics": raw_diagnostics,
    }


MARKER = re.compile(r"^__ISSUE105_(BEGIN|END)_(\d{5})__$")


def parse_batch_output(stdout: str, expected_count: int,
                       raw_oid_map: dict[Any, Any]) -> list[dict[str, Any]]:
    oid_to_id = normalize_oid_map(raw_oid_map)
    empty = {
        "status": "NOT_EXECUTED_PROCESS_STOP",
        "plan_rows": None,
        "plan_rows_integrity_status": "NOT_EXECUTED",
        "diagnostics_status": "NOT_AVAILABLE",
        "extension_diagnostics_status": None,
        "diagnostics_integrity_status": "NOT_AVAILABLE",
        "candidate_id_attribution_status": "NOT_AVAILABLE",
        "diagnostics_event_count": None,
        "mcv_events": [],
        "mcv_selection_ids": [],
        "mcv_estimate_ids": [],
        "unknown_stat_oids": [],
        "raw_ess_diagnostics": None,
        "explain_begin_seen": False,
        "explain_end_seen": False,
    }
    output = [dict(empty) for _ in range(expected_count)]
    active: int | None = None
    chunks: list[str] = []
    seen_begins: set[int] = set()
    seen_ends: set[int] = set()

    def finish(index: int) -> None:
        payload = "\n".join(chunks).strip()
        output[index]["explain_end_seen"] = True
        if not payload:
            output[index]["status"] = "MISSING_EXPLAIN_OUTPUT"
            output[index]["plan_rows_integrity_status"] = "MISSING_EXPLAIN_OUTPUT"
            return
        try:
            parsed = parse_explain_payload(payload, oid_to_id)
        except ValueError as exc:
            output[index]["status"] = str(exc)
            output[index]["plan_rows_integrity_status"] = str(exc)
            return
        output[index].update(parsed)

    for line in stdout.splitlines():
        match = MARKER.fullmatch(line.strip())
        if not match:
            if active is not None:
                chunks.append(line)
            continue
        kind, index_text = match.groups()
        index = int(index_text)
        if index >= expected_count:
            raise ValueError("batch output contains an out-of-schedule marker")
        if kind == "BEGIN":
            if active is not None or index in seen_begins:
                raise ValueError("batch output contains nested or duplicate BEGIN marker")
            active = index
            seen_begins.add(index)
            output[index]["explain_begin_seen"] = True
            chunks = []
        else:
            if active != index or index in seen_ends:
                raise ValueError("batch output END marker does not match its active query")
            finish(index)
            active = None
    if active is not None:
        output[active]["status"] = "TRUNCATED_EXPLAIN_OUTPUT"
        output[active]["plan_rows_integrity_status"] = "TRUNCATED_EXPLAIN_OUTPUT"
    return output


def input_identity(queries: list[dict[str, Any]], truths: list[int]) -> dict[str, Any]:
    if len(queries) != 10_000 or len(truths) != 10_000:
        raise Inconclusive("official DMV11 Test is not exactly 10,000 query/truth pairs")
    ids = [query["query_id"] for query in queries]
    if len(set(ids)) != len(ids):
        raise Inconclusive("DMV11 official Test query IDs are not unique")
    sql_rows = [
        {"query_id": q["query_id"], "source_index": q["source_index"], "sql": q["sql"]}
        for q in queries
    ]
    truth_digest = hashlib.sha256()
    for query, truth in zip(queries, truths, strict=True):
        truth_digest.update(issue101.json_bytes({
            "query_id": query["query_id"], "true_cardinality": truth
        }))
    return {
        "query_count": len(queries),
        "query_ids_sha256": sha256_json(ids),
        "rendered_test_sql_sha256": sha256_json(sql_rows),
        "truth_sequence_sha256": truth_digest.hexdigest(),
    }


def read_frozen_inputs(protocol: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]],
                                                          dict[str, list[str]], dict[str, Any]]:
    pins = protocol["input_pins"]
    code_pins = protocol["pinned_code"]
    for relative, digest in pins["repository_files"].items():
        if sha256_file(ROOT / relative) != digest:
            raise Inconclusive(f"frozen repository file hash mismatch: {relative}")

    issue101_protocol = issue101.read_protocol()
    if sha256_file(issue101.PROTOCOL_PATH) != code_pins["issue101_protocol_sha256"]:
        raise Inconclusive("Issue #101 protocol hash changed")
    if sha256_file(ISSUE101_DIR / "run_issue101.py") != code_pins["issue101_runner_sha256"]:
        raise Inconclusive("Issue #101 runner hash changed")
    if sha256_file(ISSUE105_DIR / "run_issue105.py") != code_pins["issue105_runner_sha256"]:
        raise Inconclusive("Issue #105 parser hash changed")
    if sha256_file(ISSUE105_DIR / "protocol-v1.md") != code_pins["issue105_protocol_sha256"]:
        raise Inconclusive("Issue #105 protocol hash changed")
    if sha256_file(ISSUE105_DIR / "protocol-amendment-v1.md") != code_pins["issue105_amendment_sha256"]:
        raise Inconclusive("Issue #105 amendment hash changed")
    issue101_source_run = issue101.runtime_runs("ess-research", 101) / protocol["issue101_source_run"]["run_id"]
    if sha256_file(issue101_source_run / "run-manifest.json") != protocol["issue101_source_run"]["run_manifest_sha256"]:
        raise Inconclusive("Issue #101 source run manifest hash changed")
    if issue101.POSTGRESQL_COMMIT != protocol["postgresql"]["source_commit"]:
        raise Inconclusive("Issue #101 PostgreSQL source pin changed")
    if sha256_file(HERE / "run_minimal_dmv11.py") != protocol["implementation"]["runner_sha256"]:
        raise Inconclusive("DMV11 runner differs from frozen protocol implementation hash")
    if sha256_file(HERE / "test_minimal_dmv11.py") != protocol["implementation"]["tests_sha256"]:
        raise Inconclusive("DMV11 tests differ from frozen protocol implementation hash")
    if sha256_file(HERE / "analyze_minimal_dmv11.py") != protocol["implementation"]["analyzer_sha256"]:
        raise Inconclusive("DMV11 analyzer differs from frozen protocol implementation hash")

    inventory = json.loads((ROOT / protocol["candidate_universe"]["source_path"]).read_text(encoding="utf-8"))
    dataset = inventory["datasets"][DATASET]
    candidates = issue101.candidate_map(DATASET)
    frozen_candidates = dataset["candidates"]
    frozen_ids = [row["id"] for row in frozen_candidates]
    if len(frozen_ids) != 55 or len(set(frozen_ids)) != 55 or len(candidates) != 55:
        raise Inconclusive("DMV11 frozen universe is not 55 unique candidates")
    if set(candidates) != set(frozen_ids) or dataset["candidate_count"] != 55:
        raise Inconclusive("DMV11 Issue #101 candidate map differs from Issue #134 universe")
    for row in frozen_candidates:
        generated = candidates[row["id"]]
        if (
            row.get("kind") != ["mcv"]
            or row.get("expressions") is not False
            or len(row.get("catalog_columns", [])) != 2
            or row.get("target") != 300
            or generated["statistic_name"] != row["statistic_name"]
            or generated["catalog_columns"] != row["catalog_columns"]
            or generated["endpoints"] != row["source_columns"]
        ):
            raise Inconclusive(f"{row['id']}: frozen object definition differs")

    order_pins = protocol["order_pins"]
    schedule_doc = json.loads((ROOT / order_pins["source_path"]).read_text(encoding="utf-8"))
    if schedule_doc.get("rng_version") != order_pins["rng_version"] or schedule_doc.get("root_seed") != order_pins["root_seed"]:
        raise Inconclusive("Issue #134 RNG identity changed")
    schedule_rows = schedule_doc["datasets"][DATASET]
    schedule_by_id = {row["order_id"]: row for row in schedule_rows}
    orders: dict[str, list[str]] = {}
    for config_id, schedule_id in ((ALL01, "random-01"), (ALL02, "random-02")):
        row = schedule_by_id.get(schedule_id)
        if row is None or row.get("kind") != "random_without_replacement":
            raise Inconclusive(f"missing frozen DMV11 {schedule_id}")
        order = row["permutation"]
        digest = sha256_json(order)
        if (
            len(order) != 55
            or len(set(order)) != 55
            or set(order) != set(frozen_ids)
            or digest != row.get("permutation_sha256")
            or digest != order_pins["all_orders"][config_id]["permutation_sha256"]
        ):
            raise Inconclusive(f"DMV11 {schedule_id} length/set/hash verification failed")
        orders[config_id] = order
    if orders[ALL01] == orders[ALL02]:
        raise Inconclusive("the two frozen DMV11 random orders are identical")

    b5_spec = protocol["frozen_nominal_b5"]
    train_path = ROOT / b5_spec["source_path"]
    train_doc = json.loads(train_path.read_text(encoding="utf-8"))
    frozen_case = [row for row in train_doc["cases"] if row.get("case_id") == "dmv11-nominal-b5"]
    if len(frozen_case) != 1:
        raise Inconclusive("frozen DMV11 Nominal B5 case missing or ambiguous")
    case = frozen_case[0]
    b5_ids = case.get("selected_ids", [])
    if (
        case.get("status") != "COMPLETE"
        or case.get("split") != "train"
        or case.get("dataset") != DATASET
        or case.get("objective") != "nominal"
        or int(case.get("budget", -1)) != 5
        or b5_ids != b5_spec["selected_candidate_ids"]
        or len(b5_ids) != 5
        or not set(b5_ids) <= set(frozen_ids)
    ):
        raise Inconclusive("frozen DMV11 Nominal B5 selection differs from protocol")
    projection01 = [candidate_id for candidate_id in orders[ALL01] if candidate_id in set(b5_ids)]
    projection02 = [candidate_id for candidate_id in orders[ALL02] if candidate_id in set(b5_ids)]
    if projection01 != order_pins["b5_order"] or projection02 != order_pins["random02_b5_projection"]:
        raise Inconclusive("B5 projections differ from frozen protocol")
    if sha256_json(projection01) != order_pins["b5_order_sha256"]:
        raise Inconclusive("matched DMV11 B5 order hash differs")
    orders[B5] = projection01

    runtime = issue101.configured_root("ESS_RUNTIME_PARENT")
    candidate_map_path = runtime / dataset["candidate_map_runtime_relative_path"]
    collection_path = runtime / dataset["collection_manifest_runtime_relative_path"]
    if sha256_file(candidate_map_path) != dataset["candidate_map_file_bytes_sha256"]:
        raise Inconclusive("Issue #99 DMV11 runtime candidate map hash differs")
    if sha256_file(collection_path) != dataset["collection_manifest_sha256"]:
        raise Inconclusive("Issue #99 DMV11 collection manifest hash differs")
    sample_spec = issue101_protocol["datasets"][DATASET]["sample"]
    if (
        sample_spec["sha256"] != pins["sample_sha256"]
        or sample_spec["bytes"] != pins["sample_bytes"]
        or sample_spec["source_manifest_sha256"] != pins["sample_collection_manifest_sha256"]
    ):
        raise Inconclusive("Issue #99 DMV11 fixed sample does not match the protocol")
    return inventory, candidates, orders, {
        "dataset_manifest": dataset,
        "issue101_protocol": issue101_protocol,
        "sample_spec": sample_spec,
        "candidate_map_path": candidate_map_path,
        "collection_manifest_path": collection_path,
        "projection_random02": projection02,
    }


def payload_state(row: dict[str, Any]) -> str:
    if not row["mcv_payload_present"]:
        return "NULL"
    return "POPULATED" if int(row["mcv_item_count"]) > 0 else "PRESENT_EMPTY"


def catalog_audit_for_arm(
    config_id: str,
    order: list[str],
    candidates: dict[str, dict[str, Any]],
    expected_ids: list[str],
    helper_ledger: list[dict[str, Any]],
    helpers: Any,
    prefix: Path,
    cluster: dict[str, Any],
    sample: Path,
    sample_spec: dict[str, Any],
    expected_table: dict[str, Any],
) -> dict[str, Any]:
    rows = issue105.query_catalog_audit(helpers, prefix, cluster, DATASET)
    expected_names = [candidates[candidate_id]["statistic_name"] for candidate_id in order]
    actual_names = [row["statistic_name"] for row in rows]
    if len(rows) != len(order) or actual_names != expected_names:
        raise Inconclusive(f"{config_id}: catalog object count/names/OID order differ from request")
    if len({row["statistic_name"] for row in rows}) != len(order):
        raise Inconclusive(f"{config_id}: duplicate statistics catalog names")
    ledger_names = [row["statistic_name"] for row in helper_ledger]
    if ledger_names != expected_names:
        raise Inconclusive(f"{config_id}: Issue #99 helper ledger order differs from CREATE order")
    ledger_by_name = {row["statistic_name"]: row for row in helper_ledger}
    id_by_name = {candidate["statistic_name"]: candidate_id for candidate_id, candidate in candidates.items()}
    source_columns, pg_columns, source_rows, _csv_sha, table_name = issue101.issue99.dataset_spec(DATASET)
    attnums = {name: index + 1 for index, (name, _type) in enumerate(pg_columns)}
    catalog_ids: list[str] = []
    oid_to_id: dict[int, str] = {}
    for row in rows:
        candidate_id = id_by_name.get(row["statistic_name"])
        if candidate_id is None or candidate_id not in expected_ids:
            raise Inconclusive(f"{config_id}: unexpected object {row['statistic_name']}")
        candidate = candidates[candidate_id]
        expected_keys = " ".join(str(attnums[column]) for column in candidate["catalog_columns"])
        if (
            row.get("stxkind") != "{m}"
            or int(row.get("statistics_target", -1)) != 300
            or row.get("stxkeys") != expected_keys
            or row.get("kinds") not in (None, ["m"])
            or row.get("attnames") not in (None, candidate["catalog_columns"])
            or int(row.get("mcv_item_count", -1)) < 0
            or not row.get("mcv_content_sha256")
            or (row.get("mcv_payload_present") and (
                row.get("kinds") != ["m"] or row.get("attnames") != candidate["catalog_columns"]
            ))
            or (not row.get("mcv_payload_present") and int(row.get("mcv_item_count", -1)) != 0)
        ):
            raise Inconclusive(f"{config_id}/{candidate_id}: MCV kind/keys/target/payload metadata invalid")
        ledger = ledger_by_name[row["statistic_name"]]
        if (
            int(ledger["oid"]) != int(row["oid"])
            or ledger["stxkeys"] != row["stxkeys"]
            or int(ledger["statistics_target"]) != int(row["statistics_target"])
            or bool(ledger["mcv_payload_present"]) != bool(row["mcv_payload_present"])
            or int(ledger["mcv_item_count"]) != int(row["mcv_item_count"])
        ):
            raise Inconclusive(f"{config_id}/{candidate_id}: independent and helper catalog audits differ")
        oid = int(row["oid"])
        if oid in oid_to_id:
            raise Inconclusive(f"{config_id}: duplicate numeric OID")
        oid_to_id[oid] = candidate_id
        row["candidate_id"] = candidate_id
        row["payload_state"] = payload_state(row)
        catalog_ids.append(candidate_id)
    if catalog_ids != order:
        raise Inconclusive(f"{config_id}: actual ascending OID order differs from frozen request")

    table = issue105.table_identity(helpers, prefix, cluster, DATASET)
    normalized_schema = [
        [index + 1, name, re.sub(r"^varchar", "character varying", type_name.lower())]
        for index, (name, type_name) in enumerate(pg_columns)
    ]
    if (
        table_name != "public.dmv11"
        or int(source_rows) != int(expected_table["row_count"])
        or int(table["row_count"]) != int(expected_table["row_count"])
        or table["columns"] != normalized_schema
        or int(table["relation_oid"]) != int(expected_table["relation_oid"])
        or table.get("relfilenode") != expected_table.get("relfilenode")
    ):
        raise Inconclusive(f"{config_id}: full-table identity/schema/row count changed")
    ordinary = issue105.ordinary_stats_audit(helpers, prefix, cluster, DATASET)
    if ordinary["column_count"] != len(pg_columns):
        raise Inconclusive(f"{config_id}: ordinary-column statistics are incomplete")
    if sha256_file(sample) != sample_spec["sha256"]:
        raise Inconclusive(f"{config_id}: frozen ANALYZE sample hash changed")
    header = helpers.sample_header(sample)
    if (
        header["server_version"] != "16.14"
        or int(header["sample_target"]) != 90_000
        or int(header["tuple_count"]) != min(source_rows, 90_000)
        or int(header["natts"]) != len(pg_columns)
        or int(header["relation_oid"]) != int(table["relation_oid"])
        or header["relation_identity"] != "6:public5:dmv11"
    ):
        raise Inconclusive(f"{config_id}: frozen sample identity/header is incompatible")
    return {
        "configuration_id": config_id,
        "create_statement_candidate_ids": list(order),
        "catalog_oid_order_candidate_ids": catalog_ids,
        "catalog_oid_order": [
            {"candidate_id": row["candidate_id"], "statistic_name": row["statistic_name"],
             "oid": int(row["oid"])}
            for row in rows
        ],
        "catalog": rows,
        "table_identity": table,
        "ordinary_column_stats": ordinary,
        "sample_sha256": sample_spec["sha256"],
        "sample_header": header,
        "oid_to_candidate_id": oid_to_id,
        "payload_state_counts": dict(sorted(Counter(row["payload_state"] for row in rows).items())),
        "create_count": len(order),
        "statistics_target_count": len(order),
        "analyze_count": 1,
        "catalog_status": "PASS",
    }


def physical_signature(audit: dict[str, Any], candidate_ids: list[str]) -> dict[str, Any]:
    rows = {row["candidate_id"]: row for row in audit["catalog"]}
    return {
        "table": {
            "relation_oid": int(audit["table_identity"]["relation_oid"]),
            "relfilenode": audit["table_identity"]["relfilenode"],
            "row_count": int(audit["table_identity"]["row_count"]),
            "columns": audit["table_identity"]["columns"],
        },
        "ordinary_stats_sha256": audit["ordinary_column_stats"]["sha256"],
        "sample_sha256": audit["sample_sha256"],
        "sample_header": {
            key: audit["sample_header"][key]
            for key in ("relation_oid", "relation_identity", "server_version",
                        "sample_target", "tuple_count", "natts")
        },
        "candidate_mcv_by_id": {
            candidate_id: {
                "statistic_name": rows[candidate_id]["statistic_name"],
                "attnames": rows[candidate_id]["attnames"],
                "kinds": rows[candidate_id]["kinds"],
                "stxkind": rows[candidate_id]["stxkind"],
                "stxkeys": rows[candidate_id]["stxkeys"],
                "statistics_target": int(rows[candidate_id]["statistics_target"]),
                "payload_state": rows[candidate_id]["payload_state"],
                "mcv_item_count": int(rows[candidate_id]["mcv_item_count"]),
                "mcv_content_sha256": rows[candidate_id]["mcv_content_sha256"],
            }
            for candidate_id in candidate_ids
        },
    }


def compare_physical_state(reference: dict[str, Any], current: dict[str, Any],
                           candidate_ids: list[str], contrast: str) -> dict[str, Any]:
    left = physical_signature(reference, candidate_ids)
    right = physical_signature(current, candidate_ids)
    if left != right:
        changed = [
            candidate_id for candidate_id in candidate_ids
            if left["candidate_mcv_by_id"].get(candidate_id)
            != right["candidate_mcv_by_id"].get(candidate_id)
        ]
        raise Inconclusive(
            f"{contrast}: table/sample/ordinary stats or MCV state differs; "
            f"changed candidate IDs={','.join(changed[:30])}"
        )
    return {
        "status": "PASS",
        "candidate_count_compared": len(candidate_ids),
        "candidate_id_keyed_mcv_state_content_and_target_equal": True,
        "table_sample_ordinary_stats_equal": True,
    }


def verify_live_state(audit: dict[str, Any], expected_ids: list[str],
                      candidates: dict[str, dict[str, Any]], helpers: Any,
                      prefix: Path, cluster: dict[str, Any], sample: Path,
                      sample_spec: dict[str, Any]) -> None:
    rows = issue105.query_catalog_audit(helpers, prefix, cluster, DATASET)
    id_by_name = {candidate["statistic_name"]: candidate_id
                  for candidate_id, candidate in candidates.items()}
    current_order = [id_by_name.get(row["statistic_name"]) for row in rows]
    if current_order != expected_ids:
        raise Inconclusive(f"{audit['configuration_id']}: live OID order changed before EXPLAIN")
    previous = {row["candidate_id"]: row for row in audit["catalog"]}
    for row in rows:
        candidate_id = id_by_name.get(row["statistic_name"])
        if candidate_id not in previous:
            raise Inconclusive(f"{audit['configuration_id']}: live catalog contains unexpected object")
        old = previous[candidate_id]
        if (
            int(old["oid"]) != int(row["oid"])
            or old["stxkeys"] != row["stxkeys"]
            or old["stxkind"] != row["stxkind"]
            or int(old["statistics_target"]) != int(row["statistics_target"])
            or old["kinds"] != row["kinds"]
            or old["attnames"] != row["attnames"]
            or old["mcv_content_sha256"] != row["mcv_content_sha256"]
            or bool(old["mcv_payload_present"]) != bool(row["mcv_payload_present"])
            or int(old["mcv_item_count"]) != int(row["mcv_item_count"])
        ):
            raise Inconclusive(f"{audit['configuration_id']}/{candidate_id}: live MCV state drifted")
    table = issue105.table_identity(helpers, prefix, cluster, DATASET)
    ordinary = issue105.ordinary_stats_audit(helpers, prefix, cluster, DATASET)
    if (
        table != audit["table_identity"]
        or ordinary["sha256"] != audit["ordinary_column_stats"]["sha256"]
        or sha256_file(sample) != sample_spec["sha256"]
    ):
        raise Inconclusive(f"{audit['configuration_id']}: live table/sample/ordinary stats drifted")


def parse_worker_output(stdout: str, partition: list[tuple[int, dict[str, Any]]],
                        oid_map: dict[int, str]) -> list[dict[str, Any]]:
    return parse_batch_output(stdout, len(partition), oid_map)


def bounded_plan_batch(prefix: Path, cluster: dict[str, Any], queries: list[dict[str, Any]],
                       sql_root: Path, log_root: Path, oid_map: dict[int, str],
                       monitor: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    oid_map = normalize_oid_map(oid_map)
    partitions: list[list[tuple[int, dict[str, Any]]]] = [[] for _ in range(PARALLEL_CLIENTS)]
    for index, query in enumerate(queries):
        partitions[index % PARALLEL_CLIENTS].append((index, query))
    empty = parse_batch_output("", 1, oid_map)[0]
    rows = [dict(empty) for _ in queries]
    sql_root.mkdir(parents=True, exist_ok=False)
    log_root.mkdir(parents=True, exist_ok=False)

    def stop_worker(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()

    def worker(worker_id: int, part: list[tuple[int, dict[str, Any]]]):
        sql_path = sql_root / f"worker{worker_id}.sql"
        issue105.build_batch_sql([query for _, query in part], sql_path)
        env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=issue101.PLAN_OPTIONS)
        command = [str(prefix / "bin/psql"), "-X", "-q", "-A", "-t",
                   "-v", "ON_ERROR_STOP=0", "-h", str(cluster["socket_dir"]),
                   "-p", str(cluster["port"]), "-d", "postgres", "-f", str(sql_path)]
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
        deadline = time.monotonic() + monitor.worker_timeout()
        timed_out = False
        resource_stopped = False
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    if monitor.stop_event.is_set():
                        resource_stopped = True
                        stop_worker(process)
                        stdout, stderr = process.communicate()
                        break
                    if time.monotonic() >= deadline:
                        timed_out = True
                        stop_worker(process)
                        stdout, stderr = process.communicate()
                        break
        finally:
            stop_worker(process)
        try:
            parsed = parse_worker_output(stdout, part, oid_map)
            parse_error = None
        except Exception as exc:
            parsed = [dict(empty) for _ in part]
            parse_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        stderr_bytes = stderr.encode("utf-8")
        stderr_path = None
        if stderr_bytes:
            stderr_path = log_root / f"worker{worker_id}.stderr"
            stderr_path.write_bytes(stderr_bytes)
        summary = {
            "worker_id": worker_id,
            "query_count": len(part),
            "return_code": process.returncode,
            "plan_rows_valid": sum(row["status"] == "VALID" for row in parsed),
            "begins_seen": sum(row["explain_begin_seen"] for row in parsed),
            "ends_seen": sum(row["explain_end_seen"] for row in parsed),
            "extension_status_counts": dict(sorted(Counter(
                str(row["extension_diagnostics_status"]) for row in parsed
            ).items())),
            "diagnostics_integrity_counts": dict(sorted(Counter(
                row["diagnostics_integrity_status"] for row in parsed
            ).items())),
            "candidate_attribution_counts": dict(sorted(Counter(
                row["candidate_id_attribution_status"] for row in parsed
            ).items())),
            "unknown_stat_oid_event_count": sum(len(row["unknown_stat_oids"]) for row in parsed),
            "stderr_bytes": len(stderr_bytes),
            "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
            "stderr_path": str(stderr_path) if stderr_path else None,
            "timed_out": timed_out,
            "resource_stopped": resource_stopped,
            "parse_error": parse_error,
        }
        sql_path.unlink(missing_ok=True)
        return part, parsed, summary

    worker_summaries = []
    with ThreadPoolExecutor(max_workers=PARALLEL_CLIENTS, thread_name_prefix="dmv11-explain") as pool:
        futures = [pool.submit(worker, worker_id, part)
                   for worker_id, part in enumerate(partitions)]
        for future in futures:
            part, parsed, summary = future.result()
            worker_summaries.append(summary)
            for (source_index, _query), row in zip(part, parsed, strict=True):
                rows[source_index] = row
    shutil.rmtree(sql_root, ignore_errors=True)
    summary = {
        "parallel_clients": PARALLEL_CLIENTS,
        "worker_count": len(worker_summaries),
        "plan_rows_valid": sum(row["status"] == "VALID" for row in rows),
        "begin_markers_seen": sum(row["explain_begin_seen"] for row in rows),
        "end_markers_seen": sum(row["explain_end_seen"] for row in rows),
        "extension_status_counts": dict(sorted(Counter(
            str(row["extension_diagnostics_status"]) for row in rows
        ).items())),
        "diagnostics_integrity_counts": dict(sorted(Counter(
            row["diagnostics_integrity_status"] for row in rows
        ).items())),
        "candidate_attribution_counts": dict(sorted(Counter(
            row["candidate_id_attribution_status"] for row in rows
        ).items())),
        "unknown_stat_oid_event_count": sum(len(row["unknown_stat_oids"]) for row in rows),
        "workers": worker_summaries,
    }
    return rows, summary


def make_query_rows(config_id: str, selected: list[str], queries: list[dict[str, Any]],
                    truths: list[int], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for query, truth, obs in zip(queries, truths, observations, strict=True):
        plan_rows = obs["plan_rows"] if obs["status"] == "VALID" else None
        rounded = qerror = None
        if plan_rows is not None:
            qerror, rounded = issue101.qerror_for_plan_rows(plan_rows, truth)
        rows.append({
            "dataset": DATASET,
            "configuration_id": config_id,
            "selected_ids": selected,
            "query_id": query["query_id"],
            "source_index": query["source_index"],
            "true_cardinality": truth,
            "estimate_plan_rows": plan_rows,
            "estimate_rounded_r1": rounded,
            "qerror": qerror,
            "status": obs["status"],
            "plan_rows_integrity_status": obs["plan_rows_integrity_status"],
            "diagnostics_status": obs["diagnostics_status"],
            "extension_diagnostics_status": obs["extension_diagnostics_status"],
            "diagnostics_integrity_status": obs["diagnostics_integrity_status"],
            "candidate_id_attribution_status": obs["candidate_id_attribution_status"],
            "diagnostics_event_count": obs["diagnostics_event_count"],
            "mcv_events": obs["mcv_events"],
            "mcv_selection_ids": obs["mcv_selection_ids"],
            "mcv_estimate_ids": obs["mcv_estimate_ids"],
            "unknown_stat_oids": obs["unknown_stat_oids"],
            "raw_ess_diagnostics": obs["raw_ess_diagnostics"],
        })
    return rows


def append_raw_member(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    body = b"".join(issue101.json_bytes(row) for row in rows)
    member = gzip.compress(body, compresslevel=6, mtime=0)
    offset = path.stat().st_size if path.exists() else 0
    with path.open("ab") as stream:
        stream.write(member)
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "offset": offset,
        "bytes": len(member),
        "rows": len(rows),
        "sha256": hashlib.sha256(member).hexdigest(),
    }


def metrics_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = issue105.metrics_for_rows(rows)
    result["plan_rows_integrity_counts"] = dict(sorted(Counter(
        row["plan_rows_integrity_status"] for row in rows
    ).items()))
    result["extension_diagnostics_status_counts"] = dict(sorted(Counter(
        str(row["extension_diagnostics_status"]) for row in rows
    ).items()))
    result["diagnostics_integrity_counts"] = dict(sorted(Counter(
        row["diagnostics_integrity_status"] for row in rows
    ).items()))
    result["candidate_id_attribution_counts"] = dict(sorted(Counter(
        row["candidate_id_attribution_status"] for row in rows
    ).items()))
    result["diagnostics_complete_count"] = sum(
        row["diagnostics_integrity_status"] == "PASS"
        and row["extension_diagnostics_status"] in {"complete", "empty"}
        for row in rows
    )
    result["candidate_attribution_complete_count"] = sum(
        row["candidate_id_attribution_status"] in {"PASS", "PASS_EMPTY"}
        for row in rows
    )
    result["unknown_stat_oid_event_count"] = sum(len(row["unknown_stat_oids"]) for row in rows)
    return result


def execute(run_id: str | None = None) -> Path:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_TEST_EXECUTION":
        raise Inconclusive("DMV11 protocol has not been frozen")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise Inconclusive("DMV11 Test execution requires a clean committed worktree")
    source_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   check=True, capture_output=True, text=True).stdout.strip()
    runtime = issue101.configured_root("ESS_RUNTIME_PARENT")
    run_parent = issue101.runtime_runs("ess-research", 133)
    run_parent.mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-issue133-dmv11-{uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be a safe path component")
    run_root = run_parent / run_id
    run_root.mkdir(exist_ok=False)
    for name in ("clusters", "input", "samples", "sql", "logs"):
        (run_root / name).mkdir()

    manifest: dict[str, Any] = {
        "format": "ess-issue133-minimal-dmv11-three-arm-v1",
        "issue": 133,
        "run_id": run_id,
        "status": "INCOMPLETE",
        "phase": "initialization",
        "source_branch": "experiment/minimal-dmv11-oid-133",
        "source_commit_before_test": source_commit,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "protocol_path": str(PROTOCOL_PATH),
        "expected_configuration_ids": list(CONFIGS),
        "expected_explain_calls": 30_000,
        "actual_explain_calls": 0,
        "explain_begin_markers_seen": 0,
        "create_statistics_statements_expected": 115,
        "statistics_target_statements_expected": 115,
        "analyze_runs_expected": 3,
        "parallel_clients_per_arm": PARALLEL_CLIENTS,
        "preexisting_postgres_processes_at_start": [],
        "input_identity": None,
        "postgresql_build": None,
        "pretest_state_comparisons": [],
        "arms": [],
        "failure": None,
        "resource_usage": {},
    }
    atomic_json(run_root / "run-manifest.json", manifest)
    append_event(run_root / "phase-events.jsonl", "initialization", {
        "source_commit_before_test": source_commit,
        "protocol_sha256": manifest["protocol_sha256"],
    })

    monitor = shared.ResourceMonitor(
        run_root,
        early_seconds=protocol["resource_envelope"]["early_stop_seconds"],
        hard_seconds=protocol["resource_envelope"]["hard_stop_seconds"],
        early_bytes=protocol["resource_envelope"]["early_stop_bytes"],
        hard_bytes=protocol["resource_envelope"]["hard_stop_bytes"],
    )
    started = time.monotonic()
    cpu_started = time.process_time()
    preexisting = shared.existing_postgres_processes()
    manifest["preexisting_postgres_processes_at_start"] = preexisting
    cluster: dict[str, Any] | None = None
    socket_owner = None
    audit_list: list[dict[str, Any]] = []
    with monitor:
        try:
            if preexisting:
                raise Inconclusive(f"refusing to start beside existing PostgreSQL processes: {preexisting}")
            if shutil.disk_usage(run_root).free < protocol["resource_envelope"]["minimum_free_bytes"]:
                raise Inconclusive("runtime filesystem has less than the frozen minimum free-space threshold")
            inventory, candidates, orders, frozen = read_frozen_inputs(protocol)
            issue101_protocol = frozen["issue101_protocol"]
            all_protocol = shared.read_protocol()
            prefix, pg_build = shared.verify_pg_install(all_protocol)
            helpers, run_formal, helper_hashes = issue101.load_pinned_helpers(run_root)

            manifest["postgresql_build"] = pg_build
            manifest["issue99_helper_sha256"] = helper_hashes
            manifest["python_version"] = platform.python_version()
            manifest["numpy_version"] = np.__version__
            manifest["cpu_affinity_count"] = len(os.sched_getaffinity(0))
            manifest["available_disk_bytes_at_start"] = shutil.disk_usage(run_root).free
            environment = shared.environment_snapshot(prefix, pg_build, run_root)
            environment["preexisting_postgres_processes_at_start"] = preexisting
            atomic_json(run_root / "environment.json", environment)

            manifest["phase"] = "official_test_input_preflight"
            atomic_json(run_root / "run-manifest.json", manifest)
            csv_path, queries, truths, source_identity = issue101.extract_test_inputs(
                DATASET, run_root / "input" / DATASET
            )
            expected = protocol["input_pins"]
            for key, actual_key in (
                ("csv_sha256", "csv_sha256"),
                ("workload_pickle_sha256", "workload_pickle_sha256"),
                ("labels_pickle_sha256", "labels_pickle_sha256"),
                ("test_truth_canonical_sha256", "test_truth_canonical_sha256"),
                ("csv_rows", "csv_rows"),
                ("query_count", "test_query_count"),
                ("truth_count", "test_query_count"),
            ):
                if source_identity.get(key) != expected[actual_key]:
                    raise Inconclusive(f"official DMV11 Test/source identity differs at {key}")
            rendered = input_identity(queries, truths)
            if rendered["truth_sequence_sha256"] != expected["test_truth_canonical_sha256"]:
                raise Inconclusive("rendered DMV11 query/truth pairing differs from frozen truth identity")
            sample, sample_identity = issue101.load_frozen_sample(
                DATASET, run_root, helpers, issue101_protocol
            )
            if sample_identity["sha256"] != expected["sample_sha256"]:
                raise Inconclusive("copied DMV11 Issue #99 fixed sample SHA differs")
            manifest["input_identity"] = {
                **source_identity, **rendered, "sample_identity": sample_identity,
                "candidate_universe_sha256": expected["candidate_universe_sha256"],
                "order_sample_sha256": expected["order_sample_sha256"],
            }
            atomic_json(run_root / "input-preflight.json", manifest["input_identity"])
            manifest["phase"] = "input_preflight_complete"
            atomic_json(run_root / "run-manifest.json", manifest)
            append_event(run_root / "phase-events.jsonl", "input_preflight_complete", {
                "query_count": len(queries),
                "source_csv_sha256": source_identity["csv_sha256"],
                "test_sql_sha256": rendered["rendered_test_sql_sha256"],
                "sample_sha256": sample_identity["sha256"],
            })
            monitor.checkpoint()

            cluster_root = run_root / "clusters" / DATASET
            cluster, socket_owner = shared.create_cluster(
                prefix, cluster_root, helpers, monitor, "dmv11-three-arm"
            )
            cluster["dataset"] = DATASET
            table_load = issue101.configure_source_table(
                helpers, prefix, cluster, DATASET, csv_path, sample
            )
            if int(table_load["full_source_rows"]) != expected["csv_rows"]:
                raise Inconclusive("DMV11 full table load row count differs from frozen source")
            table_before = issue105.table_identity(helpers, prefix, cluster, DATASET)
            manifest["table_load"] = table_load
            manifest["full_table_identity_before_arms"] = table_before
            csv_path.unlink(missing_ok=True)
            shutil.rmtree(run_root / "input" / DATASET, ignore_errors=True)
            atomic_json(run_root / "run-manifest.json", manifest)

            reference_audit: dict[str, Any] | None = None
            arm_rows: dict[str, list[dict[str, Any]]] = {}
            arm_metrics: dict[str, dict[str, Any]] = {}
            raw_path = run_root / "raw-observations.jsonl.gz"
            for config_id in CONFIGS:
                monitor.checkpoint()
                order = orders[config_id]
                manifest["phase"] = f"setup_{config_id}"
                atomic_json(run_root / "run-manifest.json", manifest)
                helper_ledger = issue101.run_config(
                    run_formal, prefix, cluster, DATASET, candidates, tuple(order), sample
                )
                audit = catalog_audit_for_arm(
                    config_id, order, candidates, list(order), helper_ledger,
                    helpers, prefix, cluster, sample, frozen["sample_spec"], table_before
                )
                audit["permutation_sha256"] = protocol["order_pins"].get(
                    config_id, protocol["order_pins"]["b5_order_sha256"] if config_id == B5 else None
                )
                audit["helper_ledger"] = helper_ledger
                audit["analysis_and_ddl_status"] = "PASS"
                for previous_audit in audit_list:
                    compared_ids = list(orders[ALL01]) if config_id == ALL02 else list(order)
                    compare = compare_physical_state(
                        previous_audit, audit, compared_ids,
                        f"{config_id} vs {previous_audit['configuration_id']}",
                    )
                    manifest["pretest_state_comparisons"].append({
                        "contrast": f"{config_id} vs {previous_audit['configuration_id']}",
                        **compare,
                    })
                # Re-read the live catalog and table state immediately before
                # formal Test EXPLAINs, retaining a same-arm audit snapshot.
                verify_live_state(
                    audit, list(order), candidates, helpers, prefix, cluster,
                    sample, frozen["sample_spec"]
                )
                audit["immediate_pre_explain_status"] = "PASS"
                audit_list.append(audit)
                atomic_json(run_root / "catalog-audit.json", {
                    "status": "IN_PROGRESS", "completed_arm_audits": audit_list,
                    "pretest_state_comparisons": manifest["pretest_state_comparisons"],
                })
                if config_id == ALL01:
                    reference_audit = audit
                manifest["arms"] = [
                    {key: value for key, value in arm.items() if key not in {"catalog", "helper_ledger"}}
                    for arm in audit_list
                ]
                manifest["phase"] = f"official_test_{config_id}"
                atomic_json(run_root / "run-manifest.json", manifest)
                append_event(run_root / "phase-events.jsonl", f"official_test_{config_id}_start", {
                    "candidate_count": len(order),
                    "query_count": len(queries),
                    "parallel_clients": PARALLEL_CLIENTS,
                })

                observations, batch = bounded_plan_batch(
                    prefix, cluster, queries,
                    run_root / "sql" / config_id,
                    run_root / "logs" / config_id,
                    audit["oid_to_candidate_id"],
                    monitor,
                )
                rows = make_query_rows(config_id, order, queries, truths, observations)
                member = append_raw_member(raw_path, rows)
                metrics = metrics_for_rows(rows)
                audit["plan_rows_integrity"] = {
                    "valid": metrics["valid_count"],
                    "expected": 10_000,
                    "status": "PASS" if metrics["valid_count"] == 10_000 else "INCOMPLETE",
                }
                audit["diagnostics_integrity"] = {
                    "complete": metrics["diagnostics_complete_count"],
                    "expected": 10_000,
                    "extension_status_counts": metrics["extension_diagnostics_status_counts"],
                    "structural_status_counts": metrics["diagnostics_integrity_counts"],
                    "status": "PASS" if metrics["diagnostics_complete_count"] == 10_000 else "INCOMPLETE",
                }
                audit["candidate_id_attribution"] = {
                    "complete": metrics["candidate_attribution_complete_count"],
                    "expected": 10_000,
                    "status_counts": metrics["candidate_id_attribution_counts"],
                    "unknown_stat_oid_event_count": metrics["unknown_stat_oid_event_count"],
                    "status": "PASS" if metrics["candidate_attribution_complete_count"] == 10_000 else "INCOMPLETE",
                }
                audit["test_status"] = "COMPLETE" if (
                    audit["plan_rows_integrity"]["status"] == "PASS"
                    and audit["diagnostics_integrity"]["status"] == "PASS"
                    and audit["candidate_id_attribution"]["status"] == "PASS"
                    and batch["begin_markers_seen"] == 10_000
                    and batch["end_markers_seen"] == 10_000
                ) else "INCOMPLETE"
                audit["query_count"] = len(rows)
                audit["actual_explain_call_count"] = batch["begin_markers_seen"]
                audit["plan_batch"] = batch
                audit["qerror_metrics"] = metrics
                audit["raw_member"] = member
                audit["catalog_fingerprint_sha256"] = sha256_json(
                    physical_signature(audit, list(order))["candidate_mcv_by_id"]
                )
                audit["ordinary_stats_sha256"] = audit["ordinary_column_stats"]["sha256"]
                arm_rows[config_id] = rows
                arm_metrics[config_id] = metrics
                manifest["actual_explain_calls"] += batch["end_markers_seen"]
                manifest["explain_begin_markers_seen"] += batch["begin_markers_seen"]
                manifest["arms"] = [
                    {key: value for key, value in arm.items() if key not in {"catalog", "helper_ledger", "oid_to_candidate_id"}}
                    for arm in audit_list
                ]
                manifest["phase"] = f"official_test_{config_id}_complete"
                atomic_json(run_root / "run-manifest.json", manifest)
                atomic_json(run_root / "catalog-audit.json", {
                    "status": "IN_PROGRESS" if audit["test_status"] == "COMPLETE" else "INCOMPLETE",
                    "arms": audit_list,
                    "pretest_state_comparisons": manifest["pretest_state_comparisons"],
                })
                append_event(run_root / "phase-events.jsonl", f"official_test_{config_id}_complete", {
                    "test_status": audit["test_status"],
                    "valid_plan_rows": metrics["valid_count"],
                    "diagnostics_complete": metrics["diagnostics_complete_count"],
                    "candidate_attribution_complete": metrics["candidate_attribution_complete_count"],
                    "explain_calls": batch["end_markers_seen"],
                    "raw_member_sha256": member["sha256"],
                })
                if audit["test_status"] != "COMPLETE":
                    raise Incomplete(
                        f"{config_id}: Plan Rows, diagnostic integrity, or candidate-ID attribution incomplete; stopping before next arm"
                    )
                monitor.checkpoint()

            manifest["status"] = "COMPLETE"
            manifest["phase"] = "all_three_arms_complete"
            manifest["config_metrics"] = arm_metrics
            manifest["raw_archive"] = {
                "path_under_ess_runtime_parent": str(raw_path.relative_to(runtime)),
                "bytes": raw_path.stat().st_size,
                "sha256": sha256_file(raw_path),
                "members": [arm["raw_member"] for arm in audit_list],
            }
            atomic_json(run_root / "catalog-audit.json", {
                "status": "PASS",
                "arms": audit_list,
                "pretest_state_comparisons": manifest["pretest_state_comparisons"],
            })
        except Inconclusive as exc:
            manifest["status"] = "INCONCLUSIVE"
            manifest["failure"] = {"class": type(exc).__name__, "phase": manifest.get("phase"),
                                   "message": str(exc)[:4000]}
        except BaseException as exc:
            manifest["status"] = "INCOMPLETE"
            manifest["failure"] = {"class": type(exc).__name__, "phase": manifest.get("phase"),
                                   "message": str(exc)[:4000]}
        finally:
            if cluster is not None:
                try:
                    shared.stop_cluster(prefix, cluster)
                except Exception as exc:
                    manifest.setdefault("cleanup_errors", []).append(str(exc)[:1000])
            if socket_owner is not None:
                socket_owner.cleanup()

    manifest["resource_usage"] = {
        "elapsed_wall_seconds": round(time.monotonic() - started, 3),
        "runner_process_cpu_seconds": round(time.process_time() - cpu_started, 3),
        "runner_peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "peak_run_directory_allocated_bytes": monitor.peak_bytes,
        "final_run_directory_allocated_bytes": shared.allocated_bytes(run_root),
        "minimum_global_filesystem_free_bytes": monitor.minimum_global_free,
        "early_or_hard_stop_reason": monitor.stop_reason,
        "cpu_note": "runner process CPU/RSS only; PostgreSQL server/backend CPU is not separately attributed",
    }
    manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    raw_path = run_root / "raw-observations.jsonl.gz"
    if raw_path.is_file():
        previous_archive = manifest.get("raw_archive", {})
        members = previous_archive.get("members")
        if not members:
            members = [
                arm["raw_member"] for arm in manifest.get("arms", [])
                if isinstance(arm, dict) and isinstance(arm.get("raw_member"), dict)
            ]
        manifest["raw_archive"] = {
            "path_under_ess_runtime_parent": str(raw_path.relative_to(runtime)),
            "bytes": raw_path.stat().st_size,
            "sha256": sha256_file(raw_path),
            "members": members or [],
        }
    atomic_json(run_root / "run-manifest.json", manifest)
    append_event(run_root / "phase-events.jsonl", "finalized", {
        "status": manifest["status"],
        "actual_explain_calls": manifest["actual_explain_calls"],
        "resource_usage": manifest["resource_usage"],
    })
    return run_root


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    run_root = execute(args.run_id)
    manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "run_root": str(run_root),
        "status": manifest["status"],
        "actual_explain_calls": manifest["actual_explain_calls"],
        "failure": manifest["failure"],
    }, sort_keys=True))
    return 0 if manifest["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
