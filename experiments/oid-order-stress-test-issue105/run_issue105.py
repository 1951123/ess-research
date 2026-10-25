"""Run the frozen Issue #105 PostgreSQL OID-order comparison."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
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
ISSUE101_DIR = ROOT / "experiments/arecel-test-generalization-issue101"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ISSUE101_DIR))
from ess_research.task_paths import runtime_runs
import run_issue101 as issue101

DATASETS = issue101.DATASETS
TRAIN_RESOURCES = ROOT / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
ISSUE101_PROTOCOL_SHA256 = "7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787"
ISSUE101_RUNNER_SHA256 = "894b8276f58d36d7d513138e574a9832aa03b8e8a21f3dd84494dbc0367b9244"
ISSUE105_PROTOCOL_SHA256 = "3afe7853a891f177ed836993bef2cd77a232f35e5398843d0019b12b384653d6"
ISSUE105_AMENDMENT_SHA256 = "58b2a15b6fee0f86212c27482aa646c25a9d0b1024ddd79a17520db6ab870e8b"
POSTGRESQL_COMMIT = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
ISSUE99_HELPER_COMMIT = "76106024611ae91505f1f05bdc35aed44d9c38c4"
PARALLEL_CLIENTS = 6
MARKER = re.compile(r"^__ISSUE105_(BEGIN|END)_(\d{5})__$")
MCV_EVENT_TYPES = {"mcv_selection", "mcv_clause", "mcv_estimate"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_schedule(protocol101: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if sha256_file(TRAIN_RESOURCES) != protocol101["source_pins"]["train_resources_sha256"]:
        raise RuntimeError("Issue #99 frozen resource manifest hash mismatch")
    frozen = json.loads(TRAIN_RESOURCES.read_text(encoding="utf-8"))
    schedule: dict[str, dict[str, Any]] = {}
    for dataset in DATASETS:
        matches = [row for row in frozen["cases"]
                   if row.get("dataset") == dataset
                   and row.get("objective") == "nominal"
                   and int(row.get("budget", -1)) == 5]
        if len(matches) != 1:
            raise RuntimeError(f"{dataset} must have exactly one frozen Nominal B=5 case")
        case = matches[0]
        selected = list(case["selected_ids"])
        if len(selected) != 5 or selected != sorted(selected) or len(set(selected)) != 5:
            raise RuntimeError(f"{dataset} frozen Nominal B=5 set is not five canonical unique IDs")

        candidates = issue101.candidate_map(dataset)
        candidate_rows = [
            {"id": candidate_id, "endpoints": candidates[candidate_id]["endpoints"]}
            for candidate_id in sorted(candidates)
        ]
        candidate_digest = hashlib.sha256(json.dumps(
            candidate_rows, ensure_ascii=True, separators=(",", ":")
        ).encode()).hexdigest()
        frozen_digest = case["input_hashes"]["candidate_map_sha256"]
        if candidate_digest != frozen_digest:
            raise RuntimeError(f"{dataset} candidate map differs from the frozen Issue #99 map")
        if any(candidate_id not in candidates for candidate_id in selected):
            raise RuntimeError(f"{dataset} frozen set contains an unknown candidate")

        conflicts: set[tuple[str, str]] = set()
        conflict_endpoints: set[str] = set()
        for index, left_id in enumerate(selected):
            left = set(candidates[left_id]["endpoints"])
            for right_id in selected[index + 1:]:
                shared = left.intersection(candidates[right_id]["endpoints"])
                if shared:
                    conflicts.add((left_id, right_id))
                    conflict_endpoints.update(shared)
        expected_conflicts = {"forest10": (3, 3), "census13": (3, 3),
                              "dmv11": (3, 3), "power7": (4, 4)}[dataset]
        observed_conflicts = (len(conflicts), len(conflict_endpoints))
        if observed_conflicts != expected_conflicts:
            raise RuntimeError(f"{dataset} endpoint-conflict counts differ from Issue #105 preflight")
        schedule[dataset] = {
            "case_id": case["case_id"],
            "selected_ids": selected,
            "orders": {
                "canonical": selected,
                "reverse": list(reversed(selected)),
            },
            "candidate_map_sha256": candidate_digest,
            "endpoint_conflict_pair_count": len(conflicts),
            "distinct_conflict_endpoints": sorted(conflict_endpoints),
        }
    return schedule


def validate_catalog_rows(dataset: str, order: str, selected: list[str],
                          candidates: dict[str, dict[str, Any]], rows: list[dict[str, Any]],
                          helper_ledger: list[dict[str, Any]]) -> dict[int, str]:
    expected_names = [candidates[candidate_id]["statistic_name"] for candidate_id in selected]
    actual_names = [row["statistic_name"] for row in rows]
    helper_names = [row["statistic_name"] for row in helper_ledger]
    if actual_names != expected_names:
        raise RuntimeError(f"{dataset}/{order} catalog OID order differs from requested CREATE order")
    if helper_names != expected_names:
        raise RuntimeError(f"{dataset}/{order} helper ledger order differs from catalog order")
    if len(rows) != 5 or len(set(actual_names)) != 5:
        raise RuntimeError(f"{dataset}/{order} relation does not have exactly the five selected statistics")

    name_to_id = {candidate["statistic_name"]: candidate_id
                  for candidate_id, candidate in candidates.items()}
    oid_to_id: dict[int, str] = {}
    helper_by_name = {row["statistic_name"]: row for row in helper_ledger}
    for row in rows:
        candidate_id = name_to_id.get(row["statistic_name"])
        if candidate_id not in selected:
            raise RuntimeError(f"{dataset}/{order} unexpected statistics object {row['statistic_name']}")
        candidate = candidates[candidate_id]
        if row["attnames"] != candidate["catalog_columns"]:
            raise RuntimeError(f"{dataset}/{order}/{candidate_id} catalog columns differ from frozen candidate")
        if row["kinds"] != ["m"] or row["statistics_target"] != 300:
            raise RuntimeError(f"{dataset}/{order}/{candidate_id} is not target-300 MCV statistics")
        if not row["mcv_payload_present"] or int(row["mcv_item_count"]) <= 0:
            raise RuntimeError(f"{dataset}/{order}/{candidate_id} has no populated MCV list")
        if row["stxkind"] != "{m}" or not row["mcv_content_sha256"]:
            raise RuntimeError(f"{dataset}/{order}/{candidate_id} catalog audit is incomplete")
        helper_row = helper_by_name[row["statistic_name"]]
        if (int(helper_row["oid"]) != int(row["oid"])
                or helper_row["stxkeys"] != row["stxkeys"]
                or int(helper_row["statistics_target"]) != int(row["statistics_target"])
                or bool(helper_row["mcv_payload_present"]) != bool(row["mcv_payload_present"])
                or int(helper_row["mcv_item_count"]) != int(row["mcv_item_count"])):
            raise RuntimeError(f"{dataset}/{order}/{candidate_id} helper and independent catalog audits differ")
        oid = int(row["oid"])
        if oid in oid_to_id:
            raise RuntimeError(f"{dataset}/{order} duplicate statistics OID")
        oid_to_id[oid] = candidate_id
    return oid_to_id


def explain_payload(payload: str, oid_to_id: dict[int, str]) -> dict[str, Any]:
    try:
        document = json.loads(payload.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_EXPLAIN_JSON") from exc
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise ValueError("INVALID_EXPLAIN_DOCUMENT")
    plan_rows = issue101.parse_top_level_plan_rows(payload)
    diagnostics = document[0].get("ESS Diagnostics")
    if not isinstance(diagnostics, dict):
        return {"plan_rows": plan_rows, "diagnostics_status": "MISSING_ESS_DIAGNOSTICS",
                "diagnostics_event_count": None, "mcv_events": [],
                "mcv_selection_ids": [], "mcv_estimate_ids": []}
    events = diagnostics.get("Events")
    if not isinstance(events, list):
        return {"plan_rows": plan_rows, "diagnostics_status": "INVALID_ESS_DIAGNOSTICS_EVENTS",
                "diagnostics_event_count": diagnostics.get("Event Count"), "mcv_events": [],
                "mcv_selection_ids": [], "mcv_estimate_ids": []}
    mcv_events = []
    unknown_oid = False
    for event in events:
        if not isinstance(event, dict) or event.get("type") not in MCV_EVENT_TYPES:
            continue
        stat_oid = event.get("stat_oid")
        candidate_id = oid_to_id.get(int(stat_oid)) if isinstance(stat_oid, int) else None
        if stat_oid is not None and candidate_id is None:
            unknown_oid = True
        compact = {key: event[key] for key in (
            "sequence", "type", "stat_oid", "key_count", "clause_index", "clause_count",
            "simple_sel", "mcv_sel", "mcv_basesel", "mcv_totalsel", "stat_sel",
        ) if key in event}
        compact["candidate_id"] = candidate_id
        mcv_events.append(compact)
    status = diagnostics.get("Status")
    event_count = diagnostics.get("Event Count")
    if (isinstance(event_count, bool) or not isinstance(event_count, int)
            or event_count != len(events)):
        status = "INVALID_ESS_DIAGNOSTICS_EVENT_COUNT"
    elif status not in {"complete", "empty", "incomplete"}:
        status = "INVALID_ESS_DIAGNOSTICS_STATUS"
    elif status == "empty" and events:
        status = "INVALID_ESS_DIAGNOSTICS_EMPTY_STATUS"
    elif status == "complete" and not events:
        status = "INVALID_ESS_DIAGNOSTICS_COMPLETE_STATUS"
    if unknown_oid:
        status = "UNKNOWN_SELECTED_STAT_OID"
    return {
        "plan_rows": plan_rows,
        "diagnostics_status": status if isinstance(status, str) else "INVALID_ESS_DIAGNOSTICS_STATUS",
        "diagnostics_event_count": event_count,
        "mcv_events": mcv_events,
        "mcv_selection_ids": [event["candidate_id"] for event in mcv_events
                               if event["type"] == "mcv_selection"],
        "mcv_estimate_ids": [event["candidate_id"] for event in mcv_events
                              if event["type"] == "mcv_estimate"],
    }


def parse_batch_output(stdout: str, expected_count: int,
                       oid_to_id: dict[int, str]) -> list[dict[str, Any]]:
    output = [{"status": "NOT_EXECUTED_PROCESS_STOP", "plan_rows": None,
               "diagnostics_status": "NOT_EXECUTED", "mcv_events": [],
               "mcv_selection_ids": [], "mcv_estimate_ids": []}
              for _ in range(expected_count)]
    active: int | None = None
    chunks: list[str] = []
    seen_begins: set[int] = set()
    seen_ends: set[int] = set()

    def finish(index: int) -> None:
        payload = "\n".join(chunks).strip()
        if not payload:
            output[index] = {"status": "MISSING_EXPLAIN_OUTPUT", "plan_rows": None,
                             "diagnostics_status": "NOT_AVAILABLE", "mcv_events": [],
                             "mcv_selection_ids": [], "mcv_estimate_ids": []}
            return
        try:
            parsed = explain_payload(payload, oid_to_id)
        except ValueError as exc:
            output[index] = {"status": str(exc), "plan_rows": None,
                             "diagnostics_status": "NOT_AVAILABLE", "mcv_events": [],
                             "mcv_selection_ids": [], "mcv_estimate_ids": []}
        else:
            output[index] = {"status": "VALID", **parsed}

    for line in stdout.splitlines():
        match = MARKER.fullmatch(line.strip())
        if not match:
            if active is not None:
                chunks.append(line)
            continue
        kind, raw_index = match.groups()
        index = int(raw_index)
        if index >= expected_count:
            raise ValueError("batch output contains an out-of-schedule query marker")
        if kind == "BEGIN":
            if active is not None or index in seen_begins:
                raise ValueError("batch output contains a nested or duplicate BEGIN marker")
            active = index
            seen_begins.add(index)
            chunks = []
        else:
            if active != index or index in seen_ends:
                raise ValueError("batch output END marker does not match its active query")
            finish(index)
            active = None
            seen_ends.add(index)
    if active is not None:
        output[active] = {"status": "TRUNCATED_EXPLAIN_OUTPUT", "plan_rows": None,
                          "diagnostics_status": "TRUNCATED", "mcv_events": [],
                          "mcv_selection_ids": [], "mcv_estimate_ids": []}
    return output


def catalog_audit(helpers: Any, prefix: Path, cluster: dict[str, Any], dataset: str) -> list[dict[str, Any]]:
    sql = f"""
SELECT COALESCE(jsonb_agg(to_jsonb(q) ORDER BY q.oid), '[]'::jsonb)::text
FROM (
  SELECT s.oid::bigint AS oid, s.stxname::text AS statistic_name,
         s.stxkeys::text AS stxkeys, s.stxkind::text AS stxkind,
         s.stxstattarget AS statistics_target, p.attnames AS attnames,
         p.kinds AS kinds, (d.stxdmcv IS NOT NULL) AS mcv_payload_present,
         CASE WHEN d.stxdmcv IS NULL THEN 0
              ELSE (SELECT count(*)::int FROM pg_catalog.pg_mcv_list_items(d.stxdmcv))
         END AS mcv_item_count,
         p.most_common_vals::text AS most_common_vals_text,
         p.most_common_freqs::text AS most_common_freqs_text,
         p.most_common_base_freqs::text AS most_common_base_freqs_text
  FROM pg_catalog.pg_statistic_ext AS s
  LEFT JOIN pg_catalog.pg_statistic_ext_data AS d
    ON d.stxoid = s.oid AND NOT d.stxdinherit
  LEFT JOIN pg_catalog.pg_stats_ext AS p
    ON p.schemaname = 'public' AND p.tablename = '{dataset}'
   AND p.statistics_name = s.stxname AND NOT p.inherited
  WHERE s.stxrelid = 'public.{dataset}'::regclass
) AS q;
"""
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=issue101.PLAN_OPTIONS)
    raw = helpers.psql(prefix, cluster["socket_dir"], cluster["port"], sql, env, tuples=True).strip()
    value = json.loads(raw)
    if not isinstance(value, list):
        raise RuntimeError(f"{dataset} catalog audit did not return a JSON array")
    for row in value:
        mcv_payload = {
            key: row.pop(key, None)
            for key in ("most_common_vals_text", "most_common_freqs_text",
                        "most_common_base_freqs_text")
        }
        row["mcv_content_sha256"] = hashlib.sha256(json.dumps(
            mcv_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
    return value


def ordinary_stats_audit(helpers: Any, prefix: Path, cluster: dict[str, Any], dataset: str) -> dict[str, Any]:
    sql = f"""
SELECT jsonb_build_object(
  'rows', COALESCE(jsonb_agg(to_jsonb(q) ORDER BY q.attname), '[]'::jsonb)
)::text
FROM (
  SELECT attname::text AS attname, null_frac, avg_width, n_distinct,
         most_common_vals::text AS most_common_vals,
         most_common_freqs::text AS most_common_freqs,
         histogram_bounds::text AS histogram_bounds, correlation,
         most_common_elems::text AS most_common_elems,
         most_common_elem_freqs::text AS most_common_elem_freqs,
         elem_count_histogram::text AS elem_count_histogram
  FROM pg_catalog.pg_stats
  WHERE schemaname = 'public' AND tablename = '{dataset}' AND NOT inherited
) AS q;
"""
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=issue101.PLAN_OPTIONS)
    raw = helpers.psql(prefix, cluster["socket_dir"], cluster["port"], sql, env, tuples=True).strip()
    value = json.loads(raw)
    if not isinstance(value, dict) or not isinstance(value.get("rows"), list):
        raise RuntimeError(f"{dataset} ordinary-column statistics audit is malformed")
    canonical = json.dumps(value["rows"], ensure_ascii=True, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode()
    return {"column_count": len(value["rows"]), "sha256": hashlib.sha256(canonical).hexdigest()}


def table_identity(helpers: Any, prefix: Path, cluster: dict[str, Any], dataset: str) -> dict[str, Any]:
    sql = f"""
SELECT jsonb_build_object(
  'relation_oid', c.oid,
  'relfilenode', pg_catalog.pg_relation_filenode(c.oid),
  'row_count', (SELECT count(*) FROM public.{dataset}),
  'columns', (
    SELECT jsonb_agg(jsonb_build_array(a.attnum, a.attname,
      pg_catalog.format_type(a.atttypid, a.atttypmod)) ORDER BY a.attnum)
    FROM pg_catalog.pg_attribute AS a
    WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
  )
)::text
FROM pg_catalog.pg_class AS c
WHERE c.oid = 'public.{dataset}'::regclass;
"""
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=issue101.PLAN_OPTIONS)
    raw = helpers.psql(prefix, cluster["socket_dir"], cluster["port"], sql, env, tuples=True).strip()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{dataset} table identity audit is malformed")
    return value


def build_batch_sql(queries: list[dict[str, Any]], path: Path) -> None:
    lines = []
    for index, query in enumerate(queries):
        sql = str(query["sql"]).strip()
        if not sql.upper().startswith("SELECT ") or not sql.endswith(";"):
            raise ValueError("AreCEL adapter did not produce one terminated SELECT per query")
        lines.append(f"\\echo __ISSUE105_BEGIN_{index:05d}__")
        lines.append("EXPLAIN (FORMAT JSON, SUMMARY OFF, ESS_DIAGNOSTICS true) " + sql)
        lines.append(f"\\echo __ISSUE105_END_{index:05d}__")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_plan_batch(prefix: Path, cluster: dict[str, Any], queries: list[dict[str, Any]],
                   sql_root: Path, oid_to_id: dict[int, str],
                   log_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    partitions: list[list[tuple[int, dict[str, Any]]]] = [[] for _ in range(PARALLEL_CLIENTS)]
    for index, query in enumerate(queries):
        partitions[index % PARALLEL_CLIENTS].append((index, query))
    parsed_all: list[dict[str, Any]] = [
        {"status": "NOT_EXECUTED_PROCESS_STOP", "plan_rows": None,
         "diagnostics_status": "NOT_EXECUTED", "mcv_events": [],
         "mcv_selection_ids": [], "mcv_estimate_ids": []}
        for _ in queries
    ]
    workers = []

    def run_worker(worker_id: int, partition: list[tuple[int, dict[str, Any]]]):
        worker_queries = [query for _index, query in partition]
        sql_path = sql_root / f"worker{worker_id}.sql"
        build_batch_sql(worker_queries, sql_path)
        env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=issue101.PLAN_OPTIONS)
        command = [str(prefix / "bin/psql"), "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=0",
                   "-h", str(cluster["socket_dir"]), "-p", str(cluster["port"]), "-d", "postgres",
                   "-f", str(sql_path)]
        result: subprocess.CompletedProcess[str] | None = None
        try:
            result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
            parsed = parse_batch_output(result.stdout, len(worker_queries), oid_to_id)
            diagnostic = {
                "worker_id": worker_id, "query_count": len(worker_queries),
                "psql_returncode": result.returncode,
                "stderr_bytes": len(result.stderr.encode("utf-8")),
                "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
                "valid_plan_rows": sum(row["status"] == "VALID" for row in parsed),
                "diagnostics_status_counts": dict(sorted(Counter(
                    row.get("diagnostics_status", "NOT_AVAILABLE") for row in parsed
                ).items())),
                "attempted_markers": sum(row["status"] != "NOT_EXECUTED_PROCESS_STOP" for row in parsed),
            }
        except Exception as exc:
            parsed = [{"status": "WORKER_EXCEPTION", "plan_rows": None,
                       "diagnostics_status": "NOT_AVAILABLE", "mcv_events": [],
                       "mcv_selection_ids": [], "mcv_estimate_ids": []}
                      for _ in worker_queries]
            diagnostic = {"worker_id": worker_id, "query_count": len(worker_queries),
                          "worker_exception": f"{type(exc).__name__}: {str(exc)[:500]}",
                          "valid_plan_rows": 0, "attempted_markers": len(worker_queries)}
        if result is not None:
            stderr_bytes = result.stderr.encode("utf-8")
            diagnostic["psql_returncode"] = result.returncode
            diagnostic["stderr_bytes"] = len(stderr_bytes)
            diagnostic["stderr_sha256"] = hashlib.sha256(stderr_bytes).hexdigest()
            if stderr_bytes:
                stderr_path = log_root / f"worker{worker_id}.stderr"
                stderr_path.write_bytes(stderr_bytes)
                diagnostic["stderr_path"] = str(stderr_path)
        sql_path.unlink(missing_ok=True)
        return partition, parsed, diagnostic

    with ThreadPoolExecutor(max_workers=PARALLEL_CLIENTS, thread_name_prefix="issue105-plan") as pool:
        futures = [pool.submit(run_worker, worker_id, partition)
                   for worker_id, partition in enumerate(partitions)]
        for future in futures:
            partition, parsed, diagnostic = future.result()
            workers.append(diagnostic)
            for (source_index, _query), row in zip(partition, parsed, strict=True):
                parsed_all[source_index] = row
    diagnostics = {
        "parallel_clients": PARALLEL_CLIENTS,
        "worker_count": len(workers),
        "valid_plan_rows": sum(row["status"] == "VALID" for row in parsed_all),
        "unresolved_or_unstarted": sum(row["status"] != "VALID" for row in parsed_all),
        "attempted_markers": sum(row["status"] != "NOT_EXECUTED_PROCESS_STOP" for row in parsed_all),
        "diagnostics_status_counts": dict(sorted(Counter(
            row.get("diagnostics_status", "NOT_AVAILABLE") for row in parsed_all
        ).items())),
        "workers": workers,
    }
    return parsed_all, diagnostics


def rows_for_config(dataset: str, order: str, selected: list[str], queries: list[dict[str, Any]],
                    truths: list[int], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for query, truth, observation in zip(queries, truths, observations, strict=True):
        row: dict[str, Any] = {
            "dataset": dataset, "order": order, "configuration_id": f"{dataset}-{order}",
            "selected_ids": selected, "query_id": query["query_id"],
            "source_index": query["source_index"], "true_cardinality": truth,
            "estimate_plan_rows": observation.get("plan_rows"),
            "estimate_rounded_r1": None, "qerror": None,
            "status": observation["status"],
            "diagnostics_status": observation.get("diagnostics_status", "NOT_AVAILABLE"),
            "diagnostics_event_count": observation.get("diagnostics_event_count"),
            "mcv_events": observation.get("mcv_events", []),
            "mcv_selection_ids": observation.get("mcv_selection_ids", []),
            "mcv_estimate_ids": observation.get("mcv_estimate_ids", []),
        }
        if observation["status"] == "VALID":
            error, rounded = issue101.qerror_for_plan_rows(observation["plan_rows"], truth)
            row["estimate_rounded_r1"] = rounded
            row["qerror"] = error
        rows.append(row)
    return rows


def metrics_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = issue101.metrics_for_rows(rows)
    valid_errors = [float(row["qerror"]) for row in rows if row["status"] == "VALID"]
    if valid_errors:
        result["qerror"]["mean"] = float(np.mean(np.asarray(valid_errors, dtype=np.float64)))
    result["diagnostics_status_counts"] = dict(sorted(Counter(
        row["diagnostics_status"] for row in rows
    ).items()))
    result["queries_with_mcv_selection"] = sum(bool(row["mcv_selection_ids"]) for row in rows)
    result["queries_with_mcv_estimate"] = sum(bool(row["mcv_estimate_ids"]) for row in rows)
    result["mcv_selection_event_count"] = sum(
        sum(event["type"] == "mcv_selection" for event in row["mcv_events"]) for row in rows
    )
    result["mcv_estimate_event_count"] = sum(
        sum(event["type"] == "mcv_estimate" for event in row["mcv_events"]) for row in rows
    )
    return result


def append_raw_member(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_fields = (
        "dataset", "order", "configuration_id", "selected_ids", "query_id", "source_index",
        "true_cardinality", "estimate_plan_rows", "estimate_rounded_r1", "qerror", "status",
        "diagnostics_status", "diagnostics_event_count", "mcv_events",
        "mcv_selection_ids", "mcv_estimate_ids",
    )
    body = b"".join(issue101.json_bytes({key: row[key] for key in raw_fields}) for row in rows)
    member = gzip.compress(body, compresslevel=6, mtime=0)
    offset = path.stat().st_size if path.exists() else 0
    with path.open("ab") as stream:
        stream.write(member)
        stream.flush()
        os.fsync(stream.fileno())
    return {"raw_member_offset": offset,
            "raw_member_bytes": len(member),
            "raw_member_sha256": hashlib.sha256(member).hexdigest()}


def compare_arm_summaries(canonical: list[dict[str, Any]], reverse: list[dict[str, Any]],
                          canonical_metrics: dict[str, Any], reverse_metrics: dict[str, Any]) -> dict[str, Any]:
    canonical_by_id = {row["query_id"]: row for row in canonical}
    reverse_by_id = {row["query_id"]: row for row in reverse}
    if set(canonical_by_id) != set(reverse_by_id):
        raise RuntimeError("canonical/reverse query IDs differ")
    valid_pairs = []
    unresolved = 0
    lower = higher = tied = 0
    diag_comparable = 0
    selection_changed = estimate_changed = 0
    cross = Counter()
    for query_id in canonical_by_id:
        left = canonical_by_id[query_id]
        right = reverse_by_id[query_id]
        if left["status"] != "VALID" or right["status"] != "VALID":
            unresolved += 1
            continue
        left_error = float(left["qerror"])
        right_error = float(right["qerror"])
        if right_error < left_error:
            lower += 1
            qclass = "reverse_lower"
        elif right_error > left_error:
            higher += 1
            qclass = "reverse_higher"
        else:
            tied += 1
            qclass = "tie"
        valid_pairs.append((left_error, right_error))
        diag_ok = left["diagnostics_status"] in {"complete", "empty"} and right["diagnostics_status"] in {"complete", "empty"}
        if diag_ok:
            diag_comparable += 1
            selected_diff = left["mcv_selection_ids"] != right["mcv_selection_ids"]
            estimate_diff = left["mcv_estimate_ids"] != right["mcv_estimate_ids"]
            selection_changed += selected_diff
            estimate_changed += estimate_diff
            cross[(qclass, "mcv_estimate_changed" if estimate_diff else "mcv_estimate_same")] += 1
    qleft = canonical_metrics.get("qerror")
    qright = reverse_metrics.get("qerror")
    differences = {}
    ratio = None
    if qleft and qright:
        for metric in ("p50", "p95", "p99", "max", "mean"):
            differences[metric] = qright[metric] - qleft[metric]
        if qleft["p95"] != 0:
            ratio = qright["p95"] / qleft["p95"]
    return {
        "status": "COMPLETE" if unresolved == 0 else "INCOMPLETE",
        "paired_valid_query_count": len(valid_pairs), "unresolved_query_count": unresolved,
        "reverse_lower_qerror_count": lower, "reverse_higher_qerror_count": higher,
        "qerror_tie_count": tied, "reverse_minus_canonical": differences,
        "p95_ratio_reverse_over_canonical": ratio,
        "diagnostics_comparable_query_count": diag_comparable,
        "mcv_selection_sequence_changed_count": selection_changed,
        "mcv_estimate_sequence_changed_count": estimate_changed,
        "qerror_by_mcv_estimate_change": {
            f"{qclass}/{mcv_status}": count
            for (qclass, mcv_status), count in sorted(cross.items())
        },
    }


def query_catalog_audit(helpers: Any, prefix: Path, cluster: dict[str, Any],
                        dataset: str) -> list[dict[str, Any]]:
    return catalog_audit(helpers, prefix, cluster, dataset)


def configure_and_audit_arm(dataset: str, order: str, selected: list[str],
                            candidates: dict[str, dict[str, Any]], sample: Path,
                            sample_spec: dict[str, Any], csv_path: Path,
                            input_identity: dict[str, Any], helpers: Any, run_formal: Any,
                            prefix: Path, cluster: dict[str, Any], expected_table: dict[str, Any],
                            expected_ordinary_digest: str | None = None,
                            expected_mcv_digests: dict[str, str] | None = None) -> dict[str, Any]:
    if sha256_file(csv_path) != input_identity["csv_sha256"]:
        raise RuntimeError(f"{dataset}/{order} source CSV hash differs before arm setup")
    if sha256_file(sample) != sample_spec["sha256"]:
        raise RuntimeError(f"{dataset}/{order} sample SHA-256 differs before replay")
    helper_ledger = issue101.run_config(run_formal, prefix, cluster, dataset,
                                        candidates, tuple(selected), sample)
    rows = query_catalog_audit(helpers, prefix, cluster, dataset)
    oid_to_id = validate_catalog_rows(dataset, order, selected, candidates, rows, helper_ledger)
    table_state = table_identity(helpers, prefix, cluster, dataset)
    if table_state != expected_table or int(table_state["row_count"]) != int(input_identity["csv_rows"]):
        raise RuntimeError(f"{dataset}/{order} table OID/file/schema identity changed")
    if sha256_file(csv_path) != input_identity["csv_sha256"]:
        raise RuntimeError(f"{dataset}/{order} source CSV hash changed during arm setup")
    ordinary = ordinary_stats_audit(helpers, prefix, cluster, dataset)
    expected_columns = len(issue101.issue99.dataset_spec(dataset)[1])
    if int(ordinary["column_count"]) != expected_columns:
        raise RuntimeError(f"{dataset}/{order} ordinary column statistics are incomplete")
    if expected_ordinary_digest is not None and ordinary["sha256"] != expected_ordinary_digest:
        raise RuntimeError(f"{dataset}/{order} ordinary column statistics differ across orders")
    by_candidate = {oid_to_id[int(row["oid"])]: row for row in rows}
    mcv_digests = {candidate_id: row["mcv_content_sha256"] for candidate_id, row in by_candidate.items()}
    if expected_mcv_digests is not None and mcv_digests != expected_mcv_digests:
        raise RuntimeError(f"{dataset}/{order} MCV contents differ across orders")
    if sha256_file(sample) != sample_spec["sha256"]:
        raise RuntimeError(f"{dataset}/{order} sample SHA-256 changed during replay")
    header = helpers.sample_header(sample)
    source_rows = issue101.issue99.dataset_spec(dataset)[2]
    column_count = len(issue101.issue99.dataset_spec(dataset)[1])
    if (header["server_version"] != "16.14" or header["sample_target"] != 90_000
            or header["tuple_count"] != min(source_rows, 90_000)
            or header["natts"] != column_count
            or header["relation_oid"] != expected_table["relation_oid"]
            or header["relation_identity"] != f"6:public{len(dataset)}:{dataset}"):
        raise RuntimeError(f"{dataset}/{order} sample relation identity differs from full table")
    return {
        "create_statement_candidate_ids": selected,
        "catalog_oid_order_candidate_ids": [oid_to_id[int(row["oid"])] for row in rows],
        "catalog_oid_order": [{"candidate_id": oid_to_id[int(row["oid"])],
                                "statistic_name": row["statistic_name"], "oid": int(row["oid"])}
                               for row in rows],
        "catalog": rows,
        "ordinary_column_stats": ordinary,
        "mcv_content_sha256_by_candidate": mcv_digests,
        "sample_sha256": sample_spec["sha256"],
        "sample_header": header,
        "table_identity": table_state,
        "oid_to_candidate_id": oid_to_id,
        "sample_replay_status": "PASS",
        "catalog_definition_status": "PASS",
    }


def execute(run_id: str | None = None) -> Path:
    protocol101 = issue101.read_protocol()
    if issue101.sha256_file(issue101.PROTOCOL_PATH) != ISSUE101_PROTOCOL_SHA256:
        raise RuntimeError("Issue #101 protocol hash differs from the frozen Issue #105 reference")
    if issue101.sha256_file(issue101.PROTOCOL_PATH.parent / "run_issue101.py") != ISSUE101_RUNNER_SHA256:
        raise RuntimeError("Issue #101 runner hash differs from the frozen Issue #105 reference")
    if issue101.sha256_file(HERE / "protocol-v1.md") != ISSUE105_PROTOCOL_SHA256:
        raise RuntimeError("Issue #105 approved protocol changed")
    if sha256_file(HERE / "protocol-amendment-v1.md") != ISSUE105_AMENDMENT_SHA256:
        raise RuntimeError("Issue #105 execution amendment changed after its source pin")
    schedule = frozen_schedule(protocol101)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise RuntimeError("Issue #105 Test access requires a clean committed worktree")
    source_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   check=True, capture_output=True, text=True).stdout.strip()
    run_id = run_id or f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-issue105-{uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be one safe path component")
    runs = runtime_runs("ess-research", 105)
    runs.mkdir(parents=True, exist_ok=True)
    root = runs / run_id
    root.mkdir(exist_ok=False)
    (root / "logs").mkdir()
    manifest: dict[str, Any] = {
        "format": "ess-issue105-run-manifest-v1", "issue": 105, "run_id": run_id,
        "source_commit": source_commit, "status": "INCOMPLETE", "phase": "initializing",
        "protocol_sha256": ISSUE105_PROTOCOL_SHA256,
        "protocol_amendment_sha256": sha256_file(HERE / "protocol-amendment-v1.md"),
        "issue101_protocol_sha256": ISSUE101_PROTOCOL_SHA256,
        "issue101_runner_sha256": ISSUE101_RUNNER_SHA256,
        "train_resources_sha256": protocol101["source_pins"]["train_resources_sha256"],
        "postgresql_source_commit": POSTGRESQL_COMMIT,
        "issue99_helper_commit": ISSUE99_HELPER_COMMIT,
        "planned_explain_calls": 8 * 10_000,
        "attempted_explain_calls": 0,
        "parallel_clients_per_configuration": PARALLEL_CLIENTS,
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "available_cpu_affinity_count": len(os.sched_getaffinity(0)),
        "allocated_disk_early_stop_bytes": protocol101["resource_envelope"]["allocated_disk_early_stop_bytes"],
        "allocated_disk_hard_max_bytes": protocol101["resource_envelope"]["allocated_disk_hard_max_bytes"],
        "available_disk_bytes_at_start": shutil.disk_usage(root).free,
        "schedule": schedule, "datasets": {}, "failure": None,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    issue101.write_manifest(root, manifest)
    envelope = protocol101["resource_envelope"]
    guard = issue101.issue99.legacy.AggregateGuard(
        root, early_seconds=10**12, hard_seconds=10**12,
        early_bytes=envelope["allocated_disk_early_stop_bytes"],
        hard_bytes=envelope["allocated_disk_hard_max_bytes"],
    )
    raw_path = root / "raw-observations.jsonl.gz"
    try:
        with issue101.fixed_pgoptions(), guard:
            manifest["phase"] = "pinned_postgresql_build"
            issue101.write_manifest(root, manifest)
            prefix, pg_build = issue101.issue99.legacy.build_pg(root)
            if (pg_build["source_commit"] != POSTGRESQL_COMMIT
                    or pg_build["version"] != "PostgreSQL 16.14"):
                raise RuntimeError("fresh PostgreSQL build does not match the frozen 16.14 source")
            manifest["postgresql_build"] = pg_build
            helpers, run_formal, helper_hashes = issue101.load_pinned_helpers(root)
            manifest["helper_sha256"] = helper_hashes
            manifest["datasets"] = {}
            issue101.write_manifest(root, manifest)

            for dataset in DATASETS:
                manifest["phase"] = f"official_test_{dataset}"
                manifest["current_dataset_progress"] = {
                    "dataset": dataset, "completed_orders": 0, "expected_orders": 2,
                    "attempted_explain_calls": 0,
                }
                issue101.write_manifest(root, manifest)
                input_root = root / "input" / dataset
                csv_path, queries, truths, input_identity = issue101.extract_test_inputs(dataset, input_root)
                if len(queries) != 10_000 or len(truths) != 10_000:
                    raise RuntimeError(f"{dataset} official Test split is not exactly 10,000 queries")
                sample, sample_identity = issue101.load_frozen_sample(dataset, root, helpers, protocol101)
                dataset_schedule = schedule[dataset]
                candidates = issue101.candidate_map(dataset)
                dataset_result: dict[str, Any] = {
                    "dataset": dataset, "status": "INCOMPLETE",
                    "source_input_identity": input_identity,
                    "sample_identity": sample_identity,
                    "endpoint_conflict_pair_count": dataset_schedule["endpoint_conflict_pair_count"],
                    "distinct_conflict_endpoints": dataset_schedule["distinct_conflict_endpoints"],
                    "configurations": [], "paired": None,
                }
                manifest["datasets"][dataset] = dataset_result
                issue101.write_manifest(root, manifest)
                cluster_root = root / "clusters" / dataset
                config_rows: dict[str, list[dict[str, Any]]] = {}
                config_metrics: dict[str, dict[str, Any]] = {}
                setup_reference: dict[str, Any] | None = None
                with issue101.issue99.legacy.owned_cluster(
                        helpers, prefix, cluster_root, os.environ.copy(), guard) as cluster:
                    cluster["dataset"] = dataset
                    table_load = issue101.configure_source_table(
                        helpers, prefix, cluster, dataset, csv_path, sample
                    )
                    initial_table = table_identity(helpers, prefix, cluster, dataset)
                    expected_columns = [
                        [index + 1, name, re.sub(r"^varchar", "character varying", type_name.lower())]
                        for index, (name, type_name) in enumerate(
                            issue101.issue99.dataset_spec(dataset)[1]
                        )
                    ]
                    if (int(initial_table["relation_oid"]) != int(table_load["relation_oid"])
                            or int(initial_table["row_count"]) != int(input_identity["csv_rows"])
                            or initial_table["columns"] != expected_columns):
                        raise RuntimeError(f"{dataset} imported full-table identity/count differs from source")
                    dataset_result["postgresql_table"] = {
                        **table_load, "identity": initial_table,
                        "source_csv_sha256": input_identity["csv_sha256"],
                    }

                    for order in ("canonical", "reverse"):
                        selected = dataset_schedule["orders"][order]
                        arm = configure_and_audit_arm(
                            dataset, order, selected, candidates, sample,
                            protocol101["datasets"][dataset]["sample"], csv_path,
                            input_identity, helpers, run_formal,
                            prefix, cluster, initial_table,
                            expected_ordinary_digest=(setup_reference["ordinary_column_stats"]["sha256"]
                                                      if setup_reference else None),
                            expected_mcv_digests=(setup_reference["mcv_content_sha256_by_candidate"]
                                                  if setup_reference else None),
                        )
                        if setup_reference is None:
                            setup_reference = arm
                        arm["candidate_map_sha256"] = dataset_schedule["candidate_map_sha256"]
                        arm["configuration_id"] = f"{dataset}-{order}"
                        arm["order"] = order
                        arm["selected_ids"] = selected
                        sql_root = root / "sql" / f"{dataset}-{order}"
                        sql_root.mkdir(parents=True, exist_ok=False)
                        log_root = root / "logs" / f"{dataset}-{order}"
                        log_root.mkdir(parents=True, exist_ok=False)
                        plan_rows, plan_diagnostics = run_plan_batch(
                            prefix, cluster, queries, sql_root, arm["oid_to_candidate_id"], log_root
                        )
                        shutil.rmtree(sql_root, ignore_errors=True)
                        query_rows = rows_for_config(dataset, order, selected, queries, truths, plan_rows)
                        raw_member = append_raw_member(raw_path, query_rows)
                        metrics = metrics_for_rows(query_rows)
                        config_record = {
                            **{key: value for key, value in arm.items() if key != "oid_to_candidate_id"},
                            "plan_batch": plan_diagnostics,
                            "metrics": metrics,
                            **raw_member,
                        }
                        dataset_result["configurations"].append(config_record)
                        config_rows[order] = query_rows
                        config_metrics[order] = metrics
                        manifest["attempted_explain_calls"] += plan_diagnostics["attempted_markers"]
                        manifest["current_dataset_progress"] = {
                            "dataset": dataset, "completed_orders": len(dataset_result["configurations"]),
                            "expected_orders": 2,
                            "attempted_explain_calls": sum(
                                item["plan_batch"]["attempted_markers"]
                                for item in dataset_result["configurations"]
                            ),
                        }
                        manifest["datasets"][dataset] = dataset_result
                        issue101.write_manifest(root, manifest)
                    dataset_result["cluster_identity"] = [str(value) for value in cluster["identity"]]
                pgdata = cluster_root / "pgdata"
                if pgdata.exists():
                    shutil.rmtree(pgdata)
                shutil.rmtree(input_root, ignore_errors=True)
                dataset_result["paired"] = compare_arm_summaries(
                    config_rows["canonical"], config_rows["reverse"],
                    config_metrics["canonical"], config_metrics["reverse"],
                )
                dataset_result["status"] = "COMPLETE" if all(
                    item["metrics"]["status"] == "COMPLETE"
                    for item in dataset_result["configurations"]
                ) else "INCOMPLETE"
                manifest["datasets"][dataset] = dataset_result
                issue101.write_manifest(root, manifest)

            complete = all(item["status"] == "COMPLETE" for item in manifest["datasets"].values())
            manifest["status"] = "COMPLETE" if complete else "INCOMPLETE"
            manifest["phase"] = "complete" if complete else "completed_with_unresolved_plans"
            manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            manifest["peak_allocated_disk_bytes"] = guard.peak
            manifest["raw_observations_sha256"] = sha256_file(raw_path)
            manifest["raw_observations_bytes"] = raw_path.stat().st_size
            if manifest["attempted_explain_calls"] > manifest["planned_explain_calls"]:
                raise RuntimeError("attempted EXPLAIN calls exceeded the frozen 80,000 maximum")
            manifest["source_archive_bytes_retained"] = False
            manifest["full_csv_files_retained"] = False
            manifest["summary_path"] = str(root / "summary.json")
            summary = {
                "format": "ess-issue105-analysis-v1",
                "evidence_label": "experimentally_observed_postgresql_measurements",
                "run_id": run_id, "source_commit": source_commit,
                "protocol_sha256": manifest["protocol_sha256"],
                "status": manifest["status"], "datasets": manifest["datasets"],
                "raw_observations_sha256": manifest["raw_observations_sha256"],
            }
            (root / "summary.json").write_text(
                json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            (root / "findings.md").write_text(markdown_report(summary), encoding="utf-8")
    except BaseException as exc:
        manifest["status"] = "INCOMPLETE"
        manifest["failure"] = {
            "error_class": type(exc).__name__, "message": str(exc)[:1000],
            "phase": manifest.get("phase"), "guard_stop_reason": guard.stop_reason,
        }
        manifest["peak_allocated_disk_bytes"] = guard.peak
        manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if raw_path.is_file():
            manifest["raw_observations_sha256"] = sha256_file(raw_path)
            manifest["raw_observations_bytes"] = raw_path.stat().st_size
        issue101.write_manifest(root, manifest)
        incomplete_summary = {
            "format": "ess-issue105-analysis-v1",
            "evidence_label": "experimentally_observed_postgresql_measurements",
            "run_id": run_id, "source_commit": source_commit,
            "protocol_sha256": manifest["protocol_sha256"],
            "status": "INCOMPLETE", "datasets": manifest["datasets"],
            "raw_observations_sha256": manifest.get("raw_observations_sha256"),
            "failure": manifest["failure"],
        }
        (root / "summary.json").write_text(
            json.dumps(incomplete_summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (root / "findings.md").write_text(markdown_report(incomplete_summary), encoding="utf-8")
        raise
    issue101.write_manifest(root, manifest)
    return root


def markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Issue #105 — OID-order AreCEL Test comparison", "",
        f"- Evidence label: **{summary['evidence_label']}**.",
        f"- Run status: **{summary.get('status', 'UNKNOWN')}**.",
        f"- Run ID: {summary['run_id']}; source commit: {summary['source_commit']}.",
        f"- Raw observations SHA-256: {summary.get('raw_observations_sha256', 'INCOMPLETE')}.",
        "- PostgreSQL 16.14; full source tables; Issue #99 fixed samples; target 300; six planner clients.", "",
        "| Dataset | Order | Valid / total | P50 | P95 | P99 | Max | Mean | Diagnostics complete/empty |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if summary.get("failure"):
        failure = summary["failure"]
        lines.insert(7, f"- Failure: `{failure['error_class']}` — {failure['message']} "
                     f"(phase `{failure.get('phase')}`).")
    for dataset in DATASETS:
        result = summary.get("datasets", {}).get(dataset)
        if not result:
            lines.append(f"| {dataset} | — | NOT RUN | — | — | — | — | — | — |")
            continue
        if not result.get("configurations"):
            lines.append(f"| {dataset} | — | NOT RUN | — | — | — | — | — | — |")
            continue
        for arm in result.get("configurations", []):
            metrics = arm["metrics"]
            q = metrics.get("qerror") or {}
            formatted = ["—" if q.get(key) is None else f"{q[key]:.6g}"
                         for key in ("p50", "p95", "p99", "max", "mean")]
            diag = metrics["diagnostics_status_counts"]
            complete_diag = diag.get("complete", 0) + diag.get("empty", 0)
            lines.append(
                f"| {dataset} | {arm['order']} | {metrics['valid_count']} / {metrics['query_count']} | "
                + " | ".join(formatted) + f" | {complete_diag} / {metrics['query_count']} |"
            )
        pair = result.get("paired")
        if pair:
            delta = pair["reverse_minus_canonical"]
            lines += [
                "", f"### {dataset} paired order effect", "",
                f"- P95 reverse − canonical: {delta.get('p95', 'NA')}; "
                f"P95 ratio: {pair.get('p95_ratio_reverse_over_canonical', 'NA')}.",
                f"- P50/P99/Max/mean deltas: {delta}.",
                f"- Reverse lower/higher/tied Q-error: {pair['reverse_lower_qerror_count']}/"
                f"{pair['reverse_higher_qerror_count']}/{pair['qerror_tie_count']}; "
                f"unresolved paired queries: {pair['unresolved_query_count']}.",
                f"- MCV selection/estimate sequence changed on "
                f"{pair['mcv_selection_sequence_changed_count']}/"
                f"{pair['mcv_estimate_sequence_changed_count']} diagnostically comparable queries.",
                f"- Q-error by MCV estimate change: {pair['qerror_by_mcv_estimate_change']}.",
            ]
    lines += [
        "", "## Scope limits", "",
        "These measurements concern only the four frozen Nominal B=5 sets, the two prespecified orders, "
        "this AreCEL Test split, and the pinned PostgreSQL build/sample/settings. The reverse order is not "
        "a worst-permutation claim. Instrumented MCV event changes are reported as query-level evidence; "
        "they do not establish a universal causal effect or a result for other PostgreSQL versions.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    root = execute(args.run_id)
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "run_root": str(root), "status": manifest["status"],
        "source_commit": manifest["source_commit"],
        "attempted_explain_calls": manifest["attempted_explain_calls"],
        "peak_allocated_disk_bytes": manifest.get("peak_allocated_disk_bytes"),
        "raw_observations_sha256": manifest.get("raw_observations_sha256"),
    }, sort_keys=True))
    return 0 if manifest["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
