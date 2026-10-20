"""Run the frozen Stage 2B validation-calibration and held-out study.

The protocol must already be committed as ``protocol-v4.json``.  Validation
truths are read only after that boundary to calibrate the model.  Test truth
is opened only after all model selections are frozen.  PostgreSQL observations
and full traces remain under the Issue-owned runtime root; the evidence
directory receives only bounded, exclusive-create summaries and ledgers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from gate_audit_v2 import (
    EXPECTED_PG_COMMIT,
    audit_pg_binary,
    audit_pg_source,
    capture_query_trace,
    evaluate_trace,
    owned_cluster,
    psql,
    sample_header,
    sha256_file,
    write_exclusive_json,
)

from ess_research.arecel import prepare
from ess_research.task_paths import configured_root, worktree_path

DATASETS = ("forest10", "census13")
METHODS = ("Empty", "Nominal", "PESS")
PESS_METHOD = "PESS"
NOMINAL_METHOD = "Nominal"
HERE = Path(__file__).resolve().parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def write_jsonl_exclusive(path: Path, rows: list[dict[str, Any]]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)


def load_workload(root: Path, split: str) -> list[dict[str, Any]]:
    value = load_json(root / split / "workload.json")
    if value.get("format") != "arecel-prepared-v1" or not isinstance(value.get("queries"), list):
        raise ValueError(f"invalid workload: {split}")
    return value["queries"]


def load_truth(root: Path, split: str) -> dict[str, int]:
    value = load_json(root / split / "truth.json")
    if value.get("format") != "arecel-prepared-v1" or not isinstance(value.get("queries"), list):
        raise ValueError(f"invalid truth: {split}")
    result = {}
    for row in value["queries"]:
        if not isinstance(row.get("true_cardinality"), int) or row["true_cardinality"] < 0:
            raise ValueError(f"invalid truth cardinality for {row.get('query_id')}")
        result[row["query_id"]] = row["true_cardinality"]
    return result


def verify_protocol_records(
    queries: list[dict[str, Any]], records: list[dict[str, Any]], *, label: str
) -> dict[str, dict[str, Any]]:
    by_id = {query["query_id"]: query for query in queries}
    if len(by_id) != len(queries):
        raise ValueError(f"duplicate query IDs in {label} workload")
    found = {}
    for record in records:
        query = by_id.get(record["query_id"])
        if query is None:
            raise ValueError(f"protocol query missing from {label}: {record['query_id']}")
        source_hash = sha256_bytes(query["source_sql"].encode())
        if source_hash != record["source_sql_sha256"]:
            raise ValueError(f"source SQL hash changed for {record['query_id']}")
        found[record["query_id"]] = query
    if len(found) != len(records):
        raise ValueError(f"duplicate protocol IDs in {label}")
    return found


def decimal_log(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        return value.ln()


def rational_log(value: Decimal) -> Fraction:
    # The quantization is explicit model-input rationalization, not an exact
    # claim about the originating binary PostgreSQL value.
    with localcontext() as context:
        context.prec = 80
        quantized = value.quantize(Decimal("0.000000000000000001"))
    return Fraction(str(quantized))


def edges_for_query(query: dict[str, Any], candidates: list[dict[str, Any]]) -> list[str]:
    columns = {predicate["column"] for predicate in query["predicates"]}
    return [candidate["id"] for candidate in candidates if set(candidate["source_columns"]) <= columns]


def maximal_matchings(available: list[str], candidates: dict[str, dict[str, Any]]) -> list[tuple[str, ...]]:
    result: list[tuple[str, ...]] = []
    ordered = list(available)

    def is_disjoint(left: str, right: str) -> bool:
        return set(candidates[left]["source_columns"]).isdisjoint(candidates[right]["source_columns"])

    def recurse(index: int, chosen: list[str]) -> None:
        if index == len(ordered):
            chosen_set = set(chosen)
            maximal = all(
                edge in chosen_set
                or any(not is_disjoint(edge, selected) for selected in chosen)
                for edge in ordered
            )
            if maximal:
                result.append(tuple(chosen))
            return
        edge = ordered[index]
        recurse(index + 1, chosen)
        if all(is_disjoint(edge, selected) for selected in chosen):
            chosen.append(edge)
            recurse(index + 1, chosen)
            chosen.pop()

    recurse(0, [])
    return sorted(set(result))


def nominal_matching(available: list[str], candidates: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    chosen: list[str] = []
    for edge in available:
        endpoints = set(candidates[edge]["source_columns"])
        if all(endpoints.isdisjoint(candidates[selected]["source_columns"]) for selected in chosen):
            chosen.append(edge)
    return tuple(chosen)


def model_loss(
    query_model: dict[str, Any], selected: tuple[str, ...], method: str, candidates: dict[str, dict[str, Any]]
) -> Fraction:
    alpha = Fraction(query_model["alpha"])
    b = {edge: Fraction(value) for edge, value in query_model["b"].items()}
    available = [edge for edge in query_model["available_edges"] if edge in selected]
    matchings = maximal_matchings(available, candidates)
    if method == "Empty":
        matching = ()
        return abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))
    if method == NOMINAL_METHOD:
        matching = nominal_matching(available, candidates)
        return abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))
    if method == PESS_METHOD:
        return max(
            abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))
            for matching in matchings
        )
    raise ValueError(f"unknown model method: {method}")


def choose_model_sets(
    task_models: list[dict[str, Any]], candidates: list[dict[str, Any]], budgets: list[int]
) -> dict[str, Any]:
    candidate_map = {candidate["id"]: candidate for candidate in candidates}
    candidate_ids = [candidate["id"] for candidate in candidates]
    output: dict[str, Any] = {method: {} for method in METHODS}
    for budget in budgets:
        feasible = [
            tuple(edge for position, edge in enumerate(candidate_ids) if mask & (1 << position))
            for mask in range(1 << len(candidate_ids))
            if sum(bool(mask & (1 << position)) for position in range(len(candidate_ids))) <= budget
        ]
        for method in METHODS:
            method_feasible = [()] if method == "Empty" else feasible
            scored = []
            for selected in method_feasible:
                objective = sum(
                    (model_loss(task, selected, method, candidate_map) for task in task_models),
                    Fraction(0),
                )
                scored.append((objective, selected))
            optimum = min(item[0] for item in scored)
            ties = sorted(selected for objective, selected in scored if objective == optimum)
            output[method][str(budget)] = {
                "selected": list(ties[0]),
                "tie_count": len(ties),
                "all_optimal_sets": [list(item) for item in ties],
                "objective": str(optimum),
                "task_count": len(task_models),
                "exact_fraction_reference": True,
            }
    return output


def parse_positive_estimate(trace_result: dict[str, Any]) -> Decimal:
    value = trace_result.get("positive_preclamp")
    if value is None:
        raise RuntimeError("missing positive pre-clamp estimate")
    estimate = Decimal(value)
    if estimate <= 0:
        raise RuntimeError(f"nonpositive pre-clamp estimate: {estimate}")
    return estimate


def run_query(
    prefix: Path,
    cluster: dict[str, Any],
    query: dict[str, Any],
    ledger: list[dict[str, Any]],
    marker: str,
    log_offset: int,
    statistic_name_to_id: dict[str, str],
) -> tuple[dict[str, Any], int]:
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
    sql = (
        "SET client_min_messages=debug1; SET plan_cache_mode=force_custom_plan; "
        "SET max_parallel_workers_per_gather=0; EXPLAIN (FORMAT JSON, SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE "
        + marker
        + " */ "
        + query["sql"]
    )
    plan = psql(prefix, cluster["socket_dir"], cluster["port"], sql, env)
    capture = capture_query_trace(cluster["server_log"], log_offset, marker)
    evaluated = evaluate_trace(
        capture["associated_trace_lines"],
        ledger,
        label=marker,
        query_id=query["query_id"],
    )
    if evaluated["status"] != "VERIFIED":
        raise RuntimeError("; ".join(evaluated["errors"]))
    estimate = parse_positive_estimate(evaluated)
    selected_names = evaluated["selected_stat_names"]
    selected_ids = []
    for name in selected_names:
        if name not in statistic_name_to_id:
            raise RuntimeError(f"selected statistic name is absent from candidate mapping: {name}")
        selected_ids.append(statistic_name_to_id[name])
    return {
        "query_id": query["query_id"],
        "source_index": query["source_index"],
        "estimate_preclamp": str(estimate),
        "plan_output_sha256": sha256_bytes(plan.encode()),
        "selected_resource_ids_from_trace": selected_ids,
        "selected_stat_oids": evaluated["selected_stat_oids"],
        "claimed_clause_coverage": evaluated["claimed_clause_coverage"],
        "trace_numeric_count": len(evaluated["numeric"]),
        "trace_mcv_count": len(evaluated["selected_trace_records"]),
        "raw_associated_trace_lines": capture["associated_trace_lines"],
        "raw_foreign_trace_counts": {
            "numeric": len(capture["foreign_numeric_trace_lines"]),
            "mcv": len(capture["foreign_mcv_trace_lines"]),
        },
    }, capture["end_offset"]


def configure_statistics(
    prefix: Path,
    cluster: dict[str, Any],
    dataset: str,
    candidates: dict[str, dict[str, Any]],
    selected: tuple[str, ...],
    sample: Path,
) -> list[dict[str, Any]]:
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
    table = f"public.{dataset}"
    names = [candidate["statistic_name"] for candidate in candidates.values()]
    statements = [
        "DROP STATISTICS IF EXISTS "
        + ", ".join(f'public."{name}"' for name in names)
        + ";"
    ]
    for edge in selected:
        candidate = candidates[edge]
        columns = ", ".join(f'"{column}"' for column in candidate["catalog_columns"])
        statements.append(
            f'CREATE STATISTICS public."{candidate["statistic_name"]}" (mcv) ON {columns} FROM {table};'
        )
        statements.append(f'ALTER STATISTICS public."{candidate["statistic_name"]}" SET STATISTICS 300;')
    escaped = str(sample).replace("'", "''")
    statements.append(
        f"SET ess.analyze_sample_import='{escaped}'; ANALYZE {table}; RESET ess.analyze_sample_import;"
    )
    psql(prefix, cluster["socket_dir"], cluster["port"], " ".join(statements), env, timeout=600)
    if not selected:
        return []
    wanted = ", ".join("'" + candidates[edge]["statistic_name"].replace("'", "''") + "'" for edge in selected)
    rows = psql(
        prefix,
        cluster["socket_dir"],
        cluster["port"],
        "SELECT s.stxname, s.oid, s.stxkeys::text, s.stxstattarget, "
        "(d.stxdmcv IS NOT NULL)::int, CASE WHEN d.stxdmcv IS NULL THEN 0 "
        "ELSE (SELECT count(*) FROM pg_mcv_list_items(d.stxdmcv)) END "
        "FROM pg_statistic_ext s LEFT JOIN pg_statistic_ext_data d "
        "ON d.stxoid=s.oid AND NOT d.stxdinherit WHERE s.stxname IN ("
        + wanted
        + ") ORDER BY s.oid;",
        env,
        tuples=True,
    ).splitlines()
    ledger = []
    for line in rows:
        fields = line.split("|")
        if len(fields) != 6:
            raise RuntimeError(f"malformed catalog ledger row: {line!r}")
        ledger.append(
            {
                "statistic_name": fields[0],
                "oid": int(fields[1]),
                "stxkeys": fields[2],
                "statistics_target": int(fields[3]),
                "mcv_payload_present": bool(int(fields[4])),
                "mcv_item_count": int(fields[5]),
            }
        )
    if {row["statistic_name"] for row in ledger} != {candidates[edge]["statistic_name"] for edge in selected}:
        raise RuntimeError("catalog ledger does not contain every requested statistic")
    return ledger


def bootstrap_cluster(
    prefix: Path, cluster: dict[str, Any], prepared_root: Path, dataset: str, spec: dict[str, Any], prepared_csv: Path
) -> tuple[Path, dict[str, Any]]:
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
    table = f"public.{dataset}"
    psql(prefix, cluster["socket_dir"], cluster["port"], (prepared_root / "schema.sql").read_text(encoding="utf-8"), env)
    escaped_csv = str(prepared_csv).replace("'", "''")
    psql(prefix, cluster["socket_dir"], cluster["port"], f"\\copy {table} FROM '{escaped_csv}' WITH (FORMAT csv, HEADER true);", env, timeout=600)
    count = psql(prefix, cluster["socket_dir"], cluster["port"], f"SELECT count(*) FROM {table};", env, tuples=True).strip()
    if count != str(spec["source_rows"]):
        raise RuntimeError(f"imported row count mismatch: {count}")
    for column in spec["catalog_columns"]:
        psql(prefix, cluster["socket_dir"], cluster["port"], f'ALTER TABLE {table} ALTER COLUMN "{column}" SET STATISTICS 300;', env)
    sample = cluster["pgdata"].parent.parent / "results" / f"{dataset}.fixed-sample"
    sample.parent.mkdir(exist_ok=True)
    escaped_sample = str(sample).replace("'", "''")
    psql(
        prefix,
        cluster["socket_dir"],
        cluster["port"],
        f"SET ess.analyze_sample_export='{escaped_sample}'; ANALYZE {table}; RESET ess.analyze_sample_export;",
        env,
        timeout=600,
    )
    header = sample_header(sample)
    if header["server_version"] != "16.14" or header["natts"] != len(spec["catalog_columns"]):
        raise RuntimeError("sample header server version or attribute count mismatch")
    return sample, {"sha256": sha256_file(sample), "bytes": sample.stat().st_size, "header": header, "table": table, "rows": int(count)}


def calibration_models(
    records: list[dict[str, Any]],
    calibration_queries: dict[str, dict[str, Any]],
    calibration_truth: dict[str, int],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_task: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in records:
        if row["repetition"] == 0:
            by_task[row["query_id"]][row["resource_set_id"]] = row
    models = []
    for query_id, query in calibration_queries.items():
        baseline = by_task[query_id].get("calibration-empty")
        if baseline is None:
            raise RuntimeError(f"missing Empty calibration for {query_id}")
        n0 = Decimal(baseline["estimate_preclamp"])
        target = max(1, calibration_truth[query_id])
        if n0 <= 0:
            raise RuntimeError(f"nonpositive Empty calibration estimate for {query_id}")
        b_values = {}
        for candidate in candidates:
            row = by_task[query_id].get(f"calibration-{candidate['id']}")
            if row is None:
                raise RuntimeError(f"missing calibration {candidate['id']} for {query_id}")
            estimate = Decimal(row["estimate_preclamp"])
            if estimate <= 0:
                raise RuntimeError(f"nonpositive calibration estimate for {query_id}/{candidate['id']}")
            b_values[candidate["id"]] = str(rational_log(estimate / n0))
        models.append(
            {
                "query_id": query_id,
                "source_index": query["source_index"],
                "true_cardinality": calibration_truth[query_id],
                "target_T": target,
                "n0_preclamp": str(n0),
                "alpha": str(rational_log(n0 / Decimal(target))),
                "b": b_values,
                "available_edges": edges_for_query(query, candidates),
                "weight": str(query.get("weight", 1.0)),
                "rationalization": "Decimal natural log quantized to 18 places, then Fraction strings",
            }
        )
    return models


def metric(values: list[Decimal]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    with localcontext() as context:
        context.prec = 80
        count = len(ordered)
        mean = sum(ordered, Decimal(0)) / Decimal(count)
        median = (ordered[(count - 1) // 2] + ordered[count // 2]) / Decimal(2)
        p90 = ordered[max(1, math.ceil(Decimal("0.90") * count)) - 1]
    return {"count": len(ordered), "mean": str(mean), "median": str(median), "p90": str(p90), "max": str(ordered[-1])}


def paired_summary(rows: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> dict[str, Any]:
    left = {(row["query_id"], row["repetition"]): Decimal(row["absolute_log_error"]) for row in rows}
    right = {(row["query_id"], row["repetition"]): Decimal(row["absolute_log_error"]) for row in baseline}
    if set(left) != set(right):
        raise RuntimeError("paired summary key mismatch")
    by_query = defaultdict(list)
    for key, value in left.items():
        by_query[key[0]].append(value - right[key])
    deltas = [sum(values, Decimal(0)) / Decimal(len(values)) for values in by_query.values()]
    return {
        "independent_query_id_count": len(deltas),
        "delta_abs_log_error": metric(deltas),
        "benefits_negative_delta": sum(value < 0 for value in deltas),
        "ties_zero_delta": sum(value == 0 for value in deltas),
        "harms_positive_delta": sum(value > 0 for value in deltas),
    }


def summarize_heldout(
    rows: list[dict[str, Any]],
    protocol: dict[str, Any],
    selected_sets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_set = defaultdict(list)
    for row in rows:
        by_set[row["resource_set_id"]].append(row)
    summaries = []
    for set_id, set_rows in sorted(by_set.items()):
        errors = [Decimal(row["absolute_log_error"]) for row in set_rows]
        truth = {row["query_id"]: row["truth_N"] for row in set_rows}
        top_ids = [query_id for query_id, _ in sorted(truth.items(), key=lambda item: (-item[1], item[0]))[: max(1, math.ceil(0.10 * len(truth)))]]
        selected_names = Counter(name for row in set_rows for name in row["selected_resource_ids_from_trace"])
        payload_names = sorted({name for row in set_rows for name in row["payload_present_resource_ids"]})
        summaries.append(
            {
                "resource_set_id": set_id,
                "selected": selected_sets[set_id]["selected"],
                "budgets_methods": selected_sets[set_id]["aliases"],
                "rows": len(set_rows),
                "absolute_log_error": metric(errors),
                "zero_truth": metric([Decimal(row["absolute_log_error"]) for row in set_rows if row["truth_N"] == 0]),
                "tail_top_decile": metric([Decimal(row["absolute_log_error"]) for row in set_rows if row["query_id"] in top_ids]),
                "tail_query_ids": top_ids,
                "trace_selected_resource_counts": dict(sorted(selected_names.items())),
                "payload_present_resource_ids": payload_names,
                "requested_resource_ids": sorted(set(set_rows[0]["requested_resource_ids"])),
                "repetition_error_spread": metric([
                    abs(Decimal(pair[0]["absolute_log_error"]) - Decimal(pair[1]["absolute_log_error"]))
                    for query_id in sorted(truth)
                    for pair in [[
                        next(row for row in set_rows if row["query_id"] == query_id and row["repetition"] == 0),
                        next(row for row in set_rows if row["query_id"] == query_id and row["repetition"] == 1),
                    ]]
                ]),
            }
        )
    empty_id = next(set_id for set_id, value in selected_sets.items() if value["selected"] == [])
    empty_rows = by_set[empty_id]
    paired = []
    for set_id, value in sorted(selected_sets.items()):
        if set_id == empty_id:
            continue
        paired.append({
            "resource_set_id": set_id,
            "selected": value["selected"],
            "budgets_methods": value["aliases"],
            "vs_empty": paired_summary(by_set[set_id], empty_rows),
        })
    nominal_candidates = [
        (
            max(alias["budget"] for alias in value["aliases"] if alias["method"] == NOMINAL_METHOD),
            set_id,
        )
        for set_id, value in selected_sets.items()
        if any(alias["method"] == NOMINAL_METHOD for alias in value["aliases"])
    ]
    nominal_id = max(nominal_candidates)[1] if nominal_candidates else None
    if nominal_id is not None:
        for item in paired:
            if item["resource_set_id"] != nominal_id:
                item["vs_nominal"] = paired_summary(by_set[item["resource_set_id"]], by_set[nominal_id])
    return {
        "resource_sets": summaries,
        "paired": paired,
        "rows": len(rows),
        "query_ids": len({row["query_id"] for row in rows}),
        "repetitions": 2,
        "model_and_pg_domains_separate": True,
    }


def run_dataset(
    dataset: str,
    protocol: dict[str, Any],
    prefix: Path,
    build_manifest: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    spec = protocol["datasets"][dataset]
    candidates = spec["candidates"]
    candidate_map = {candidate["id"]: candidate for candidate in candidates}
    name_to_id = {candidate["statistic_name"]: candidate["id"] for candidate in candidates}
    with prepare(issue=48, dataset=dataset) as prepared:
        valid_queries = load_workload(prepared.dataset_root, "valid")
        test_queries = load_workload(prepared.dataset_root, "test")
        calibration_records = spec["validation_calibration"]["records"]
        test_records = spec["test_cohort"]["records"]
        calibration_queries = verify_protocol_records(valid_queries, calibration_records, label=f"{dataset}/valid")
        test_query_map = verify_protocol_records(test_queries, test_records, label=f"{dataset}/test")
        with owned_cluster(prefix, prepared.run_root / "formal-pg", os.environ.copy()) as cluster:
            sample, sample_identity = bootstrap_cluster(prefix, cluster, prepared.dataset_root, dataset, spec, prepared.csv)
            raw_root = prepared.run_root / "results"
            raw_calibration: list[dict[str, Any]] = []
            raw_heldout: list[dict[str, Any]] = []
            setup_ledger: list[dict[str, Any]] = []
            for repetition in range(2):
                for resource_set_id, selected in [("calibration-empty", ())] + [
                    (f"calibration-{candidate['id']}", (candidate["id"],)) for candidate in candidates
                ]:
                    ledger = configure_statistics(prefix, cluster, dataset, candidate_map, selected, sample)
                    setup_ledger.append({
                        "phase": "validation_calibration",
                        "repetition": repetition,
                        "resource_set_id": resource_set_id,
                        "requested_resource_ids": list(selected),
                        "catalog": ledger,
                    })
                    offset = cluster["server_log"].stat().st_size
                    for query_id in [item["query_id"] for item in calibration_records]:
                        marker = f"issue48-formal-{dataset}-calibration-{repetition}-{resource_set_id}-{query_id.rsplit(':', 1)[-1]}"
                        measured, offset = run_query(prefix, cluster, calibration_queries[query_id], ledger, marker, offset, name_to_id)
                        raw_calibration.append({
                            **measured,
                            "dataset": dataset,
                            "phase": "validation_calibration",
                            "repetition": repetition,
                            "resource_set_id": resource_set_id,
                            "requested_resource_ids": list(selected),
                            "payload_present_resource_ids": [
                                name for name in candidate_map if any(
                                    item["statistic_name"] == candidate_map[name]["statistic_name"] and item["mcv_payload_present"]
                                    for item in ledger
                                )
                            ],
                        })
            validation_truth = load_truth(prepared.dataset_root, "valid")
            models = calibration_models(raw_calibration, calibration_queries, validation_truth, candidates)
            selected_by_method = choose_model_sets(models, candidates, protocol["measurement_contract"]["budgets_proxy_units"])
            selected_sets: dict[str, dict[str, Any]] = {}
            for method in METHODS:
                for budget, value in selected_by_method[method].items():
                    selected = tuple(value["selected"])
                    set_id = "set-" + ("empty" if not selected else "_".join(selected))
                    selected_sets.setdefault(set_id, {"selected": list(selected), "aliases": []})
                    selected_sets[set_id]["aliases"].append({"budget": int(budget), "method": method, "tie_count": value["tie_count"]})

            test_truth = load_truth(prepared.dataset_root, "test")
            if not set(test_query_map) <= set(test_truth):
                raise RuntimeError("frozen test cohort IDs are absent from test truth")
            for repetition in range(2):
                for set_id, value in sorted(selected_sets.items()):
                    selected = tuple(value["selected"])
                    ledger = configure_statistics(prefix, cluster, dataset, candidate_map, selected, sample)
                    setup_ledger.append({
                        "phase": "heldout",
                        "repetition": repetition,
                        "resource_set_id": set_id,
                        "requested_resource_ids": list(selected),
                        "catalog": ledger,
                    })
                    offset = cluster["server_log"].stat().st_size
                    for record in test_records:
                        query_id = record["query_id"]
                        marker = f"issue48-formal-{dataset}-heldout-{repetition}-{set_id}-{query_id.rsplit(':', 1)[-1]}"
                        measured, offset = run_query(prefix, cluster, test_query_map[query_id], ledger, marker, offset, name_to_id)
                        estimate = Decimal(measured["estimate_preclamp"])
                        truth = test_truth[query_id]
                        target = max(1, truth)
                        error = abs(decimal_log(estimate / Decimal(target)))
                        raw_heldout.append({
                            **measured,
                            "dataset": dataset,
                            "phase": "heldout",
                            "repetition": repetition,
                            "resource_set_id": set_id,
                            "requested_resource_ids": list(selected),
                            "payload_present_resource_ids": [
                                name for name in candidate_map if any(
                                    item["statistic_name"] == candidate_map[name]["statistic_name"] and item["mcv_payload_present"]
                                    for item in ledger
                                )
                            ],
                            "truth_N": truth,
                            "target_T": target,
                            "absolute_log_error": str(error),
                            "signed_estimate_minus_T": str(estimate - Decimal(target)),
                        })
            if len(raw_heldout) > protocol["resource_budget"]["maximum_query_measurements_per_dataset"]:
                raise RuntimeError("held-out measurement cap exceeded")
            raw_calibration_path = raw_root / "formal-calibration.jsonl"
            raw_heldout_path = raw_root / "formal-heldout.jsonl"
            write_jsonl_exclusive(raw_calibration_path, raw_calibration)
            write_jsonl_exclusive(raw_heldout_path, raw_heldout)
            write_jsonl_exclusive(raw_root / "formal-setups.jsonl", setup_ledger)

        evidence_root.mkdir(parents=True, exist_ok=False)
        bounded_heldout = [
            {
                key: value
                for key, value in row.items()
                if key not in {"raw_associated_trace_lines", "raw_foreign_trace_counts", "plan_output_sha256"}
            }
            for row in raw_heldout
        ]
        bounded_calibration = [
            {
                key: value
                for key, value in row.items()
                if key not in {"raw_associated_trace_lines", "raw_foreign_trace_counts", "plan_output_sha256"}
            }
            for row in raw_calibration
        ]
        write_jsonl_exclusive(evidence_root / "heldout-ledger.jsonl", bounded_heldout)
        write_jsonl_exclusive(evidence_root / "validation-calibration-ledger.jsonl", bounded_calibration)
        write_exclusive_json(evidence_root / "validation-model.json", {
            "format": "ess-issue48-stage2b-validation-model-v1",
            "evidence_label": "experimentally_observed_validation_calibration_plus_exact_fraction_reference",
            "dataset": dataset,
            "protocol_sha256": sha256_file(HERE / "protocol-v4.json"),
            "sample": sample_identity,
            "calibration_task_ids": [item["query_id"] for item in calibration_records],
            "models": models,
            "selected_by_method_and_budget": selected_by_method,
            "selected_sets": selected_sets,
            "limitations": ["validation-derived model inputs are separate from held-out PostgreSQL measurements", "Fraction exactness applies only after recorded rationalization", "no solver or universal optimality claim"],
        })
        summary = summarize_heldout(raw_heldout, protocol, selected_sets)
        write_exclusive_json(evidence_root / "heldout-summary.json", {
            "format": "ess-issue48-stage2b-heldout-summary-v1",
            "evidence_label": "experimentally_observed_postgresql_measurement",
            "dataset": dataset,
            "protocol_sha256": sha256_file(HERE / "protocol-v4.json"),
            "sample": sample_identity,
            "raw_external": {
                "calibration": str(raw_calibration_path),
                "calibration_sha256": sha256_file(raw_calibration_path),
                "heldout": str(raw_heldout_path),
                "heldout_sha256": sha256_file(raw_heldout_path),
            },
            "summary": summary,
            "scientific_boundary": ["positive pre-clamp numeric trace is the primary estimate", "Plan Rows and latency are not used", "requested/payload/trace-selected resources are separate", "no universal PESS dominance or PostgreSQL containment claim"],
        })
        return {
            "dataset": dataset,
            "status": "VALID",
            "evidence_dir": str(evidence_root),
            "heldout_rows": len(raw_heldout),
            "selected_sets": selected_sets,
            "summary": summary,
            "raw_external": {"run_root": str(prepared.run_root), "heldout_sha256": sha256_file(raw_heldout_path)},
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol-v4.json")
    parser.add_argument("--pg-source", type=Path, required=True)
    parser.add_argument("--pg-prefix", type=Path, required=True)
    parser.add_argument("--pg-build-manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()

    configured_root("ESS_DATA_ROOT")
    configured_root("ESS_RUNTIME_PARENT")
    configured_worktree = worktree_path("ess-research", 48).resolve()
    if Path.cwd().resolve() != configured_worktree:
        raise SystemExit(f"run from the configured Issue Worktree: {configured_worktree}")
    protocol = load_json(args.protocol)
    if protocol.get("status") != "FROZEN_BEFORE_HELDOUT_OUTCOME_COLLECTION_V4":
        raise SystemExit("protocol-v4 is not the committed pre-outcome freeze")
    if args.evidence_root.exists():
        raise SystemExit(f"refusing existing evidence root: {args.evidence_root}")
    prefix = args.pg_prefix.resolve()
    source = args.pg_source.resolve()
    if not (prefix / "bin/postgres").is_file() or not args.pg_build_manifest.is_file():
        raise SystemExit("pinned PostgreSQL prefix/build manifest is missing")
    source_audit = audit_pg_source(source)
    if source_audit.get("status") != "VERIFIED" or source_audit.get("head") != EXPECTED_PG_COMMIT:
        raise SystemExit(f"pinned PostgreSQL source audit failed: {source_audit}")
    binary_audit = audit_pg_binary(prefix, args.pg_build_manifest.resolve())
    if binary_audit.get("status") != "VERIFIED":
        raise SystemExit(f"pinned PostgreSQL binary audit failed: {binary_audit}")
    results = []
    for dataset in DATASETS:
        dataset_evidence = args.evidence_root / dataset
        results.append(run_dataset(dataset, protocol, prefix, args.pg_build_manifest, dataset_evidence))
    overall = "MEASURED_PENDING_ANALYSIS" if all(item["status"] == "VALID" for item in results) else "INCONCLUSIVE"
    write_exclusive_json(args.evidence_root / "run-summary.json", {
        "format": "ess-issue48-stage2b-formal-run-v1",
        "evidence_label": "experimentally_observed_postgresql_measurement",
        "overall_status": overall,
        "protocol_sha256": sha256_file(args.protocol),
        "pg_source": str(source),
        "pg_prefix": str(prefix),
        "pg_build_manifest": str(args.pg_build_manifest.resolve()),
        "postgresql_source_audit": source_audit,
        "postgresql_binary_audit": binary_audit,
        "python": platform.python_version(),
        "results": results,
        "scientific_boundary": ["GO is a bounded decision-quality study result, not universal objective dominance", "group overlap is retained and limits independence", "physical maintenance and latency were not measured"],
    })
    print(json.dumps({"output": str(args.evidence_root / "run-summary.json"), "overall_status": overall, "datasets": [item["dataset"] for item in results]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
