"""Run the frozen, read-only Issue #59 workload-structure audit.

The audit consumes only archive-first prepared workload/schema/table files. It
does not open truth.json and performs no PostgreSQL operation. Results are
bounded aggregate evidence with exclusive-create output files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ess_research.arecel import prepare
from ess_research.arecel.forest10 import (
    COLUMNS as FOREST_COLUMNS,
)
from ess_research.arecel.forest10 import (
    EXPECTED_ROWS as FOREST_ROWS,
)
from ess_research.arecel.forest10 import (
    SOURCE_COLUMNS as FOREST_SOURCE_COLUMNS,
)
from ess_research.arecel.real import SPECS, SUPPORTED_OPERATORS, sha256_file

HERE = Path(__file__).resolve().parent
DATASETS = ("forest10", "census13", "dmv11", "power7")
SPLITS = ("train", "valid", "test")
FORBIDDEN_TRUTH_KEYS = frozenset({"truth_N", "true_cardinality", "source_label", "label"})
MAX_DISTINCT_VALUES = 1_000_000
ALL_SOURCE_COLUMNS = set(FOREST_SOURCE_COLUMNS) | {
    column for dataset_spec in SPECS.values() for column in dataset_spec.source_columns
}
# The archive-backed AreCEL preparation contract contains one 100,000-record
# train split and two 10,000-record evaluation splits for every audited
# dataset.  Keep this contract here rather than inferring it from a replay.
EXPECTED_PREPARED_SPLIT_COUNTS = {"train": 100_000, "valid": 10_000, "test": 10_000}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exclusive_text(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def exclusive_json(path: Path, value: Any) -> None:
    exclusive_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def git_value(*args: str) -> str:
    repository = subprocess.check_output(
        ["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], text=True
    ).strip()
    return subprocess.check_output(["git", *args], cwd=repository, text=True).strip()


def protocol() -> dict[str, Any]:
    value = load_json(HERE / "protocol-v1.json")
    if value.get("status") != "FROZEN_BEFORE_STRUCTURAL_AUDIT_V1":
        raise RuntimeError("protocol-v1 is not the committed outcome-free freeze")
    return value


def candidate_map(spec: dict[str, Any], dataset: str) -> dict[str, dict[str, Any]]:
    candidates = spec["candidate_universe"][dataset]["candidates"]
    result = {item["id"]: item for item in candidates}
    if len(result) != len(candidates):
        raise ValueError(f"duplicate candidate IDs: {dataset}")
    return result


def source_columns(dataset: str) -> tuple[str, ...]:
    if dataset == "forest10":
        return FOREST_SOURCE_COLUMNS
    return SPECS[dataset].source_columns


def schema_columns(dataset: str) -> tuple[tuple[str, str], ...]:
    if dataset == "forest10":
        return FOREST_COLUMNS
    return SPECS[dataset].columns


def source_rows(dataset: str) -> int:
    if dataset == "forest10":
        return FOREST_ROWS
    return SPECS[dataset].expected_rows


def source_csv_expected_sha256(dataset: str) -> str:
    if dataset == "forest10":
        from ess_research.arecel.forest10 import CSV_SHA256

        return CSV_SHA256
    return SPECS[dataset].csv_sha256


def source_relation(dataset: str) -> str:
    if dataset == "forest10":
        return 'public."forest10_original"'
    return SPECS[dataset].source_relation


def normalised_template(query: dict[str, Any]) -> str:
    fields = []
    for predicate in query["predicates"]:
        value = "range" if predicate["operator"] == "[]" else "scalar"
        fields.append((predicate["column"], predicate["operator"], value))
    return json.dumps(sorted(fields), ensure_ascii=False, separators=(",", ":"))


def source_sql_text_fingerprint(query: dict[str, Any]) -> str:
    return sha256_bytes(query["source_sql"].strip().encode("utf-8"))


def canonical_predicate_fingerprint(query: dict[str, Any]) -> str:
    ordered_tuples = [
        [predicate["column"], predicate["operator"], predicate["value"]]
        for predicate in query["predicates"]
    ]
    canonical = json.dumps(
        ordered_tuples, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    return sha256_bytes(canonical.encode("utf-8"))


def template_fingerprint(query: dict[str, Any]) -> str:
    return sha256_bytes(normalised_template(query).encode("utf-8"))


def operator_family(operators: list[str]) -> str:
    unique = set(operators)
    if not unique:
        return "none"
    if unique == {"="}:
        return "equality_only"
    if "[]" in unique and len(unique) == 1:
        return "range_only"
    if "[]" in unique:
        return "range_mixed"
    if unique <= {"<", "<=", ">", ">="}:
        return "inequality_only"
    return "mixed"


def empty_metric() -> dict[str, Any]:
    return {
        "queries": 0,
        "queries_with_at_least_one_edge": 0,
        "available_edge_count": {"0": 0, "1": 0, "2": 0, "3+": 0},
        "queries_with_at_least_two_edges": 0,
        "queries_with_conflicting_edges": 0,
        "queries_with_two_or_more_maximal_matchings": 0,
        "maximal_matching_count": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5+": 0},
    }


def percentage(count: int, denominator: int) -> float:
    return round(100.0 * count / denominator, 6) if denominator else 0.0


def distribution_with_percentages(counts: Counter[str] | dict[str, int], denominator: int) -> dict[str, dict[str, Any]]:
    return {
        key: {"count": int(value), "percent": percentage(int(value), denominator)}
        for key, value in sorted(counts.items())
    }


def add_metric(metric: dict[str, Any], values: dict[str, Any]) -> None:
    metric["queries"] += 1
    edge_count = len(values["raw_edges"])
    if edge_count >= 1:
        metric["queries_with_at_least_one_edge"] += 1
    bucket = str(edge_count) if edge_count < 3 else "3+"
    metric["available_edge_count"][bucket] += 1
    if edge_count >= 2:
        metric["queries_with_at_least_two_edges"] += 1
    if values["conflicting_edge_count"] >= 2:
        metric["queries_with_conflicting_edges"] += 1
    matching_count = values["maximal_matching_count"]
    matching_bucket = str(matching_count) if matching_count <= 4 else "5+"
    metric["maximal_matching_count"][matching_bucket] += 1
    if matching_count >= 2:
        metric["queries_with_two_or_more_maximal_matchings"] += 1


def edge_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return bool(set(left["source_columns"]) & set(right["source_columns"]))


def maximal_matchings(mask: int, candidates: list[dict[str, Any]]) -> list[tuple[str, ...]]:
    available = [index for index in range(len(candidates)) if mask & (1 << index)]
    result: set[tuple[str, ...]] = set()

    def disjoint(left: int, right: int) -> bool:
        return not (set(candidates[left]["source_columns"]) & set(candidates[right]["source_columns"]))

    def visit(position: int, chosen: list[int]) -> None:
        if position == len(available):
            chosen_set = set(chosen)
            is_maximal = all(
                index in chosen_set or any(not disjoint(index, selected) for selected in chosen)
                for index in available
            )
            if is_maximal:
                result.add(tuple(candidates[index]["id"] for index in chosen))
            return
        index = available[position]
        visit(position + 1, chosen)
        if all(disjoint(index, selected) for selected in chosen):
            chosen.append(index)
            visit(position + 1, chosen)
            chosen.pop()

    visit(0, [])
    return sorted(result)


def query_values(
    query: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    known_columns: set[str] | None = None,
) -> dict[str, Any]:
    predicates = query.get("predicates")
    if not isinstance(predicates, list):
        raise ValueError(f"predicates is not a list: {query.get('query_id')}")
    columns = [item.get("column") for item in predicates if isinstance(item, dict)]
    operators = [item.get("operator") for item in predicates if isinstance(item, dict)]
    known = (known_columns or ALL_SOURCE_COLUMNS) | {
        column for candidate in candidates.values() for column in candidate["source_columns"]
    }
    unknown_columns = [column for column in columns if column not in known]
    unsupported_operators = [operator for operator in operators if operator not in SUPPORTED_OPERATORS]
    distinct = set(columns)
    raw_edges = [
        candidate_id
        for candidate_id, candidate in candidates.items()
        if set(candidate["source_columns"]) <= distinct
    ]
    supported = not unknown_columns and not unsupported_operators and len(columns) == len(predicates)
    calibration_edges = raw_edges if supported and predicates else []
    strict_edges = (
        raw_edges
        if supported and len(predicates) == 2 and len(distinct) == 2
        else []
    )
    conflicting_edges = [
        candidate_id
        for candidate_id in raw_edges
        if any(
            other != candidate_id and edge_overlap(candidates[candidate_id], candidates[other])
            for other in raw_edges
        )
    ]
    overlapping_pairs = sum(
        edge_overlap(candidates[left], candidates[right])
        for index, left in enumerate(raw_edges)
        for right in raw_edges[index + 1 :]
    )
    mask = sum(1 << index for index, candidate_id in enumerate(candidates) if candidate_id in raw_edges)
    matchings = maximal_matchings(mask, list(candidates.values()))
    return {
        "predicate_count": len(predicates),
        "distinct_column_count": len(distinct),
        "operators": operators,
        "operator_family": operator_family(operators),
        "raw_edges": raw_edges,
        "calibration_edges": calibration_edges,
        "strict_edges": strict_edges,
        "unknown_columns": unknown_columns,
        "unsupported_operators": unsupported_operators,
        "repeated_predicate_columns": sorted(
            column for column, count in Counter(columns).items() if count > 1
        ),
        "conflicting_edge_count": len(conflicting_edges),
        "overlapping_edge_pair_count": overlapping_pairs,
        "maximal_matching_count": len(matchings),
    }


def metric_for(values: list[dict[str, Any]], edge_key: str, candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metric = empty_metric()
    for value in values:
        add_metric(metric, structural_projection(value, edge_key, candidates))
    return metric


def structural_projection(
    value: dict[str, Any], edge_key: str, candidates: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    selected = value[edge_key]
    conflicting = [
        candidate_id
        for candidate_id in selected
        if any(
            other != candidate_id and edge_overlap(candidates[candidate_id], candidates[other])
            for other in selected
        )
    ]
    mask = sum(1 << index for index, candidate_id in enumerate(candidates) if candidate_id in selected)
    return {
        **value,
        "raw_edges": selected,
        "conflicting_edge_count": len(conflicting),
        "maximal_matching_count": len(maximal_matchings(mask, list(candidates.values()))),
    }


def cross_tab(values: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for value in values:
        groups[str(value[key])].append(value)
    result = {}
    for group, records in sorted(groups.items(), key=lambda item: item[0]):
        result[group] = {
            "queries": len(records),
            "raw_edge_count": Counter(
                str(len(item["raw_edges"])) if len(item["raw_edges"]) < 3 else "3+"
                for item in records
            ),
            "strict_edge_available": sum(bool(item["strict_edges"]) for item in records),
            "calibration_edge_available": sum(bool(item["calibration_edges"]) for item in records),
            "conflicting_queries": sum(item["conflicting_edge_count"] >= 2 for item in records),
            "multi_maximal_queries": sum(item["maximal_matching_count"] >= 2 for item in records),
        }
        result[group]["raw_edge_count"] = dict(sorted(result[group]["raw_edge_count"].items()))
        result[group]["raw_edge_count_distribution"] = distribution_with_percentages(
            result[group]["raw_edge_count"], len(records)
        )
        for field in ("strict_edge_available", "calibration_edge_available", "conflicting_queries", "multi_maximal_queries"):
            result[group][f"{field}_percent"] = percentage(result[group][field], len(records))
    return result


def fingerprint_audit(split_records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result = {}
    for label, function in (
        ("canonical_predicate", canonical_predicate_fingerprint),
        ("source_sql_text", source_sql_text_fingerprint),
        ("template", template_fingerprint),
    ):
        groups: dict[str, list[str]] = defaultdict(list)
        for split, records in split_records.items():
            for query in records:
                groups[function(query)].append(split)
        shared = {key: splits for key, splits in groups.items() if len(set(splits)) > 1}
        pairs = Counter("+".join(sorted(set(splits))) for splits in shared.values())
        result[label] = {
            "group_count": len(groups),
            "shared_group_count": len(shared),
            "shared_record_count": sum(len(splits) for splits in shared.values()),
            "duplicate_record_excess": sum(max(0, len(splits) - 1) for splits in groups.values()),
            "shared_groups_by_split_pair": dict(sorted(pairs.items())),
            "shared_group_percent": percentage(len(shared), len(groups)),
            "shared_record_percent": percentage(
                sum(len(splits) for splits in shared.values()),
                sum(len(splits) for splits in groups.values()),
            ),
        }
    return result


def scan_table(path: Path, dataset: str) -> dict[str, Any]:
    columns = [name for name, _ in schema_columns(dataset)]
    distinct: list[set[str] | None] = [set() for _ in columns]
    empty_cells = [0 for _ in columns]
    row_count = 0
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if header != list(source_columns(dataset)):
            raise ValueError(f"unexpected source CSV header for {dataset}")
        for row in reader:
            if len(row) != len(columns):
                raise ValueError(f"CSV row width mismatch for {dataset}: {len(row)}")
            row_count += 1
            for index, value in enumerate(row):
                if value == "":
                    empty_cells[index] += 1
                if distinct[index] is not None:
                    distinct[index].add(value)
                    if len(distinct[index]) > MAX_DISTINCT_VALUES:
                        distinct[index] = None
    return {
        "status": "MEASURED",
        "csv_sha256": sha256_file(path),
        "row_count": row_count,
        "columns": {
            name: {
                "postgres_type": type_,
                "observed_empty_cells": empty_cells[index],
                "observed_empty_rate": empty_cells[index] / row_count if row_count else None,
                "distinct_non_null_csv_values": (
                    len(distinct[index]) if distinct[index] is not None else None
                ),
                "distinct_status": "MEASURED" if distinct[index] is not None else "INCONCLUSIVE_CAP_EXCEEDED",
            }
            for index, (name, type_) in enumerate(schema_columns(dataset))
        },
        "sql_null_semantics": "NOT_MEASURED; empty CSV cells are reported separately and are not asserted to be SQL NULL",
    }


def validate_prepared_provenance(
    protocol_value: dict[str, Any],
    dataset: str,
    manifest: dict[str, Any],
    table_csv: Path,
    splits: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Validate archive, adapter, table, and workload identity before success."""
    source_contract = protocol_value["source_contract"]
    if manifest.get("format") != "arecel-preparation-v1":
        raise ValueError("prepared manifest format is not arecel-preparation-v1")
    if manifest.get("issue") != 59:
        raise ValueError("prepared manifest issue is not 59")
    if manifest.get("dataset") != dataset:
        raise ValueError(f"prepared manifest dataset mismatch: {dataset}")
    if manifest.get("archive_sha256") != source_contract["archive_sha256"]:
        raise ValueError(f"{dataset} prepared archive SHA256 mismatch")
    if manifest.get("upstream_commit") != source_contract["upstream_commit"]:
        raise ValueError(f"{dataset} prepared upstream commit mismatch")
    if manifest.get("splits") != EXPECTED_PREPARED_SPLIT_COUNTS:
        raise ValueError(f"{dataset} prepared split-count contract mismatch")
    if set(splits) != set(SPLITS):
        raise ValueError(f"{dataset} workload split set mismatch")

    for split in SPLITS:
        records = splits[split]
        if len(records) != EXPECTED_PREPARED_SPLIT_COUNTS[split]:
            raise ValueError(f"{dataset} {split} workload count mismatch")
        for index, query in enumerate(records):
            expected_id = f"arecel:{dataset}:{split}:{index:06d}"
            if (
                query.get("query_id") != expected_id
                or query.get("source_index") != index
            ):
                raise ValueError(f"{dataset} {split} query identity mismatch at index {index}")

    inventory = scan_table(table_csv, dataset)
    expected_rows = source_rows(dataset)
    expected_sha256 = source_csv_expected_sha256(dataset)
    if inventory["csv_sha256"] != expected_sha256:
        raise ValueError(
            f"{dataset} CSV SHA256 mismatch: expected {expected_sha256}, "
            f"got {inventory['csv_sha256']}"
        )
    if inventory["row_count"] != expected_rows:
        raise ValueError(
            f"{dataset} CSV row count mismatch: expected {expected_rows}, "
            f"got {inventory['row_count']}"
        )
    return {
        "status": "VERIFIED",
        "archive_sha256": manifest["archive_sha256"],
        "upstream_commit": manifest["upstream_commit"],
        "dataset": dataset,
        "split_counts": dict(EXPECTED_PREPARED_SPLIT_COUNTS),
        "query_identity": "arecel:{dataset}:{split}:{source_index:06d}",
        "csv_sha256": inventory["csv_sha256"],
        "row_count": inventory["row_count"],
        "database_inventory": inventory,
    }


def split_summary(
    records: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    known_columns: set[str] | None = None,
) -> dict[str, Any]:
    values = [query_values(query, candidates, known_columns) for query in records]
    if len({query["query_id"] for query in records}) != len(records):
        raise ValueError("duplicate query IDs within split")
    if any(key in query for query in records for key in FORBIDDEN_TRUTH_KEYS):
        raise ValueError("truth-like field found in workload record")
    predicate_histogram = Counter(str(value["predicate_count"]) for value in values)
    distinct_histogram = Counter(str(value["distinct_column_count"]) for value in values)
    operator_histogram = Counter(
        operator for value in values for operator in value["operators"]
    )
    family_histogram = Counter(value["operator_family"] for value in values)
    repeated = Counter(len(value["repeated_predicate_columns"]) for value in values)
    all_metric = empty_metric()
    calibration_metric = empty_metric()
    strict_metric = empty_metric()
    for value in values:
        add_metric(all_metric, structural_projection(value, "raw_edges", candidates))
        add_metric(calibration_metric, structural_projection(value, "calibration_edges", candidates))
        add_metric(strict_metric, structural_projection(value, "strict_edges", candidates))
    shape_examples = []
    for query, value in zip(records, values, strict=True):
        if value["predicate_count"] and len(shape_examples) < 3:
            shape_examples.append({
                "columns": [item["column"] for item in query["predicates"]],
                "operators": value["operators"],
                "predicate_count": value["predicate_count"],
                "raw_edges": value["raw_edges"],
                "strict_edges": value["strict_edges"],
            })
    return {
        "query_count": len(records),
        "query_id_sha256": sha256_bytes("\n".join(query["query_id"] for query in records).encode()),
        "source_index_min": min(query["source_index"] for query in records),
        "source_index_max": max(query["source_index"] for query in records),
        "predicate_count_histogram": dict(sorted(predicate_histogram.items(), key=lambda item: int(item[0]))),
        "predicate_count_distribution": distribution_with_percentages(predicate_histogram, len(records)),
        "distinct_predicate_column_histogram": dict(sorted(distinct_histogram.items(), key=lambda item: int(item[0]))),
        "distinct_predicate_column_distribution": distribution_with_percentages(distinct_histogram, len(records)),
        "operator_histogram": dict(sorted(operator_histogram.items())),
        "operator_family_histogram": dict(sorted(family_histogram.items())),
        "operator_family_distribution": distribution_with_percentages(family_histogram, len(records)),
        "repeated_predicate_column_histogram": dict(sorted(repeated.items())),
        "repeated_predicate_column_distribution": distribution_with_percentages(repeated, len(records)),
        "unknown_column_queries": sum(bool(value["unknown_columns"]) for value in values),
        "unsupported_operator_queries": sum(bool(value["unsupported_operators"]) for value in values),
        "relation_shape": {"single_table_conjunctive_records": len(records), "other_or_unknown_records": 0},
        "raw_column_cooccurrence": all_metric,
        "calibration_eligibility": calibration_metric,
        "strict_pairwise_eligibility": strict_metric,
        "opportunity_percentages": {
            "raw_at_least_one_edge": percentage(
                all_metric["queries_with_at_least_one_edge"], len(records)
            ),
            "raw_at_least_two_edges": percentage(
                all_metric["queries_with_at_least_two_edges"], len(records)
            ),
            "raw_conflicting_edges": percentage(
                all_metric["queries_with_conflicting_edges"], len(records)
            ),
            "raw_two_or_more_maximal_matchings": percentage(
                all_metric["queries_with_two_or_more_maximal_matchings"], len(records)
            ),
            "calibration_at_least_one_edge": percentage(
                calibration_metric["queries_with_at_least_one_edge"], len(records)
            ),
            "strict_at_least_one_edge": percentage(
                strict_metric["queries_with_at_least_one_edge"], len(records)
            ),
        },
        "cross_tabs": {
            "predicate_count": cross_tab(values, "predicate_count"),
            "distinct_column_count": cross_tab(values, "distinct_column_count"),
            "operator_family": cross_tab(values, "operator_family"),
        },
        "representative_shape_examples": shape_examples,
    }


def cohort_metrics(
    records: list[dict[str, Any]],
    candidate_spec: dict[str, dict[str, Any]],
    cohort_ids: list[str],
    known_columns: set[str],
) -> dict[str, Any]:
    selected = [query for query in records if query["query_id"] in set(cohort_ids)]
    summary = split_summary(selected, candidate_spec, known_columns) if selected else {"query_count": 0}
    return {
        "reference_id_count": len(cohort_ids),
        "found_id_count": len(selected),
        "missing_reference_ids": sorted(set(cohort_ids) - {query["query_id"] for query in selected}),
        "summary": summary,
    }


def stage1a_ids() -> set[str]:
    protocol = load_json(HERE.parent / "forest10-heldout-decision-stage1a" / "protocol.json")
    return {item["query_id"] for item in protocol["heldout_selection"]["selected"]}


def historical_pg_reference(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "NOT_MEASURED", "reason": "no explicit PR #58 evidence root supplied"}
    result: dict[str, Any] = {"status": "MEASURED_FROM_EXISTING_EVIDENCE_ONLY", "root": str(path), "datasets": {}}
    for dataset in ("forest10", "census13"):
        ledger_path = path / dataset / "validation-calibration-ledger.jsonl"
        if not ledger_path.is_file():
            result["status"] = "INCONCLUSIVE"
            result["datasets"][dataset] = {"status": "MISSING"}
            continue
        rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line]
        by_resource: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "payload_present_rows": 0, "trace_selected_rows": 0})
        for row in rows:
            if row.get("phase") != "validation_calibration" or row.get("repetition") != 0:
                continue
            resource_set = row.get("resource_set_id", "")
            if resource_set == "calibration-empty":
                continue
            candidate = resource_set.removeprefix("calibration-")
            record = by_resource[candidate]
            record["rows"] += 1
            if candidate in row.get("payload_present_resource_ids", []):
                record["payload_present_rows"] += 1
            if row.get("selected_resource_ids_from_trace"):
                record["trace_selected_rows"] += 1
        result["datasets"][dataset] = {
            "status": "MEASURED_FROM_EXISTING_EVIDENCE_ONLY",
            "ledger_sha256": sha256_file(ledger_path),
            "validation_singleton_resources": dict(sorted(by_resource.items())),
            "interpretation": "historical PR #58 validation evidence; not used to choose this audit's candidates or filters",
        }
    return result


@contextmanager
def prepared_workload(dataset: str) -> Iterator[tuple[dict[str, Any], Path, dict[str, list[dict[str, Any]]]]]:
    with prepare(issue=59, dataset=dataset) as prepared:
        splits: dict[str, list[dict[str, Any]]] = {}
        for split in SPLITS:
            payload = (prepared.dataset_root / split / "workload.json").read_bytes()
            value = json.loads(payload)
            if value.get("format") != "arecel-prepared-v1" or value.get("dataset") != dataset:
                raise ValueError(f"invalid workload identity: {dataset}/{split}")
            splits[split] = value["queries"]
        yield prepared.manifest, prepared.csv, splits


def audit_dataset(spec: dict[str, Any], dataset: str, legacy_ids: set[str], cohort_ids: list[str]) -> dict[str, Any]:
    candidates = candidate_map(spec, dataset)
    known_columns = set(source_columns(dataset))
    with prepared_workload(dataset) as (manifest, table_csv, splits):
        provenance_check = validate_prepared_provenance(
            spec, dataset, manifest, table_csv, splits
        )
        database_inventory = provenance_check.pop("database_inventory")
        split_results = {
            split: split_summary(splits[split], candidates, known_columns) for split in SPLITS
        }
        strict_records = {
            split: [
                query
                for query in splits[split]
                if query_values(query, candidates, known_columns)["strict_edges"]
            ]
            for split in SPLITS
        }
        cross_split = fingerprint_audit(splits)
        stage1a_overlap = sorted(set(query["query_id"] for query in splits["test"]) & legacy_ids)
        stage2b = (
            cohort_metrics(splits["test"], candidates, cohort_ids, known_columns)
            if cohort_ids
            else {"status": "NOT_APPLICABLE"}
        )
        if dataset == "forest10":
            stage2b["stage1a_legacy_ids_in_test"] = len(stage1a_overlap)
            stage2b["stage1a_legacy_ids_in_strict_test"] = sum(
                query["query_id"] in set(stage1a_overlap) for query in strict_records["test"]
            )
        return {
            "dataset": dataset,
            "provenance": {
                "prepare_manifest": manifest,
                "source_relation": source_relation(dataset),
                "source_rows_stated": source_rows(dataset),
                "source_csv_expected_sha256": source_csv_expected_sha256(dataset),
                "schema_columns": [
                    {"name": name, "postgres_type": type_}
                    for name, type_ in schema_columns(dataset)
                ],
                "validation": provenance_check,
            },
            "database_inventory": {
                **database_inventory,
                "provenance_validation": provenance_check["status"],
            },
            "split_summaries": split_results,
            "cross_split_fingerprint_audit": cross_split,
            "stage2b_cohort_reference": stage2b,
            "candidate_universe": {
                "candidate_ids": list(candidates),
                "candidates": list(candidates.values()),
                "physical_pg_payload_status": "NOT_MEASURED_BY_ISSUE_59; historical cross-reference is separate",
            },
        }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Issue #59 workload structure and PESS/MCV matching opportunity audit",
        "",
        "Evidence label: **Experimentally observed descriptive workload/data characterization; no PostgreSQL runtime assertion.**",
        "",
        "## Boundary and protocol",
        "",
        f"Protocol SHA-256: `{summary['protocol_sha256']}`. The audit used only the archive-first `prepare(issue=59, dataset=...)` path, read workload/schema/table artifacts, and did not open `truth.json`, run PostgreSQL, create statistics, or run ANALYZE. Candidate universes and all eligibility rules were frozen before the audit.",
        "",
        "Raw column co-occurrence, calibration eligibility, and strict Stage 2B pairwise eligibility are separate measures. None proves MCV payload existence, actual PostgreSQL selection, maximal-matching containment, or PESS/Nominal decision divergence.",
        "",
        "## Dataset comparison",
        "",
        "| Dataset | split | queries | strict eligible | calibration edge | raw >=2 edges | conflicting | >=2 maximal matchings | table rows measured/stated |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset in DATASETS:
        item = summary["datasets"][dataset]
        for split in SPLITS:
            split_item = item["split_summaries"][split]
            strict = split_item["strict_pairwise_eligibility"]
            calibration = split_item["calibration_eligibility"]
            raw = split_item["raw_column_cooccurrence"]
            table = item["database_inventory"]
            total = split_item["query_count"]
            def fmt(count: int) -> str:
                return f"{count} ({percentage(count, total):.6f}%)"

            lines.append(
                f"| {dataset} | {split} | {total} | {fmt(strict['queries_with_at_least_one_edge'])} | {fmt(calibration['queries_with_at_least_one_edge'])} | {fmt(raw['queries_with_at_least_two_edges'])} | {fmt(raw['queries_with_conflicting_edges'])} | {fmt(raw['queries_with_two_or_more_maximal_matchings'])} | {table['row_count']}/{item['provenance']['source_rows_stated']} |"
            )
    lines += [
        "",
        "The table's row count is an independent CSV scan; the stated count comes from the pinned schema/source contract. Empty CSV cells are not asserted to be SQL NULL. Distinctness is reported per column in the dataset JSON files and is not a PostgreSQL catalog statistic.",
        "",
        "## Stage 2B cohort impact",
        "",
    ]
    for dataset in ("forest10", "census13"):
        cohort = summary["datasets"][dataset]["stage2b_cohort_reference"]
        lines.append(
            f"- **{dataset}**: reference cohort IDs {cohort['reference_id_count']}, found {cohort['found_id_count']}; the cohort summary is shape-only and does not change membership. Missing IDs: {len(cohort.get('missing_reference_ids', []))}."
        )
    lines += [
        "- DMV11 and Power7 have no Stage 2B frozen cohort; their prospective adjacent-pair candidate policy is outcome-blind and the cohort comparison is `NOT_APPLICABLE`.",
        "",
        "Forest10 additionally records the Stage 1A legacy IDs seen in its test workload and their strict-eligibility overlap. Exclusion is reported as a historical filter; no Stage 1A test truth or estimate is read.",
        "",
        "## Fingerprint overlap and physical cross-reference",
        "",
        "Canonical ordered-predicate, source-SQL-text, and normalized-template fingerprint overlap is reported per dataset with group and record percentages in the dataset JSON files. The source-SQL-text metric hashes stripped source SQL bytes; it is not the canonical predicate fingerprint. Shared groups across splits mean query IDs cannot be treated as group-independent evidence.",
        "",
        "For Forest10/Census13, the optional historical cross-reference contains only already observed PR #58 validation ledger fields (requested resources, catalog MCV payload presence, and trace-selected resources). It is not used to construct candidates or eligibility. DMV11/Power7 physical payload and trace status is **NOT MEASURED**.",
        "",
        "## Interpretation",
        "",
        "This audit establishes descriptive structural opportunity under the frozen candidate graphs. Multiple maximal matchings are a graph property of the prescribed candidate universe; they do not establish that a fixed PostgreSQL catalog realizes all of them, that PESS and Nominal differ on held-out estimates, or that either policy is physically beneficial. The DMV11/Power7 adjacent-pair universe is a bounded prospective structural policy, not an exhaustive pairwise universe.",
        "",
        "Representative operator/column shapes are stored without literal values in the per-dataset summaries. No raw SQL, table rows, truth values, estimates, or large derived artifacts are committed.",
        "",
        "Decision type: **descriptive feasibility assessment only**. Any future prospective nontrivial PESS-versus-Nominal study requires its own outcome-free protocol and independent held-out design; this report does not amend Stage 2B protocol-v4.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> None:
    spec = protocol()
    initial_dirty = bool(git_value("status", "--porcelain"))
    output = args.output_root.resolve()
    if output.exists():
        raise SystemExit(f"refusing existing output root: {output}")
    output.mkdir(parents=True)
    legacy = stage1a_ids()
    datasets: dict[str, Any] = {}
    total_table_rows = 0
    for dataset in DATASETS:
        cohort_ids = spec["stage2b_cohort_reference"].get(f"{dataset}_test_cohort_ids", [])
        datasets[dataset] = audit_dataset(spec, dataset, legacy, cohort_ids)
        total_table_rows += datasets[dataset]["database_inventory"]["row_count"]
        if total_table_rows > 15_000_000:
            raise RuntimeError("aggregate CSV scan exceeded the frozen 15000000-row cap")
        exclusive_json(output / f"{dataset}.json", datasets[dataset])
    summary = {
        "format": "ess-issue59-workload-structure-audit-summary-v1",
        "protocol_sha256": sha256_file(HERE / "protocol-v1.json"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "worktree_dirty_at_start": initial_dirty,
        "python": platform.python_version(),
        "datasets": datasets,
        "historical_pg_cross_reference": historical_pg_reference(args.stage2b_v4_root),
        "scientific_boundary": [
            "descriptive structural audit only",
            "no PostgreSQL runtime or catalog assertion",
            "no truth, estimate, or model-objective use",
            "no group-independent population inference",
        ],
    }
    exclusive_json(output / "summary.json", summary)
    exclusive_text(output / "report.md", render_report(summary))
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    exclusive_text(
        output / "SHA256SUMS",
        "".join(f"{sha256_file(path)}  {path.relative_to(output)}\n" for path in files),
    )
    print(json.dumps({"output": str(output), "datasets": list(datasets)}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--stage2b-v4-root", type=Path)
    run(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
