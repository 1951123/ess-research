"""Deterministic Census13 configuration assignment and smoke comparison."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence


def assign_configurations(
    candidates: Sequence[Mapping[str, Any]], worker_count: int
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]:
    """Assign each singleton config to one worker; Empty is measured once."""
    if worker_count not in (1, 2):
        raise ValueError("the frozen acquisition protocol supports one or two workers")
    configs: list[tuple[str, tuple[str, ...]]] = [("Empty", ())]
    for row in candidates:
        candidate_id = str(row["id"])
        support = row["eligible_valid_query_count"]
        if isinstance(support, bool) or not isinstance(support, int) or support <= 0:
            raise ValueError(f"candidate {candidate_id} has invalid frozen support")
        configs.append((candidate_id, (candidate_id,)))
    assigned: list[list[tuple[str, tuple[str, ...]]]] = [[] for _ in range(worker_count)]
    assigned[0].append(configs[0])
    for candidate_index, config in enumerate(configs[1:]):
        assigned[candidate_index % worker_count].append(config)
    flattened = [config_id for worker in assigned for config_id, _ in worker]
    expected = [config_id for config_id, _ in configs]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(expected):
        raise AssertionError("configuration assignment is not a partition")
    return tuple(tuple(rows) for rows in assigned)


def calls_for_worker(
    assigned_configs: Sequence[tuple[str, tuple[str, ...]]],
    ordered_query_ids: Sequence[str],
    eligible_by_query: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, str], ...]:
    """Return the serial call list for one worker in config/query order."""
    if len(ordered_query_ids) != len(set(ordered_query_ids)):
        raise ValueError("query IDs must be unique")
    if set(eligible_by_query) != set(ordered_query_ids):
        raise ValueError("eligibility must cover exactly the ordered query IDs")
    calls: list[tuple[str, str]] = []
    for config_id, selected in assigned_configs:
        if config_id == "Empty":
            if selected:
                raise ValueError("Empty configuration cannot contain resources")
            calls.extend((query_id, config_id) for query_id in ordered_query_ids)
            continue
        if selected != (config_id,):
            raise ValueError("only singleton configurations are supported")
        calls.extend(
            (query_id, config_id)
            for query_id in ordered_query_ids
            if config_id in eligible_by_query[query_id]
        )
    if len(calls) != len(set(calls)):
        raise AssertionError("worker schedule contains duplicate query/config pairs")
    return tuple(calls)


def compare_smoke_observations(
    serial_rows: Sequence[Mapping[str, Any]],
    parallel_rows: Sequence[Mapping[str, Any]],
    expected_pairs: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Compare semantic diagnostics; OIDs are validated per-cluster, not equated."""
    def index(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
        found: dict[tuple[str, str], Mapping[str, Any]] = {}
        for row in rows:
            key = (str(row.get("query_id", "")), str(row.get("config_id", "")))
            if not all(key) or key in found:
                raise ValueError("observation identity is missing or duplicated")
            found[key] = row
        return found

    expected = set(expected_pairs)
    if len(expected) != len(expected_pairs):
        raise ValueError("expected query/config schedule contains duplicates")
    left, right = index(serial_rows), index(parallel_rows)
    if set(left) != expected or set(right) != expected:
        raise ValueError("serial and parallel observations must exactly cover the frozen schedule")

    compared_fields = (
        "diagnostics_status", "mcv_diagnostics_status", "mcv_candidate_ids", "clause_indexes"
    )
    for key in sorted(expected):
        a, b = left[key], right[key]
        if a.get("status") != "SUCCESS" or b.get("status") != "SUCCESS":
            raise ValueError(f"smoke observation failed: {key}")
        try:
            estimate_a = Decimal(str(a["nrows_preclamp"]))
            estimate_b = Decimal(str(b["nrows_preclamp"]))
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ValueError(f"smoke observation lacks a decimal pre-clamp estimate: {key}") from exc
        if not estimate_a.is_finite() or estimate_a <= 0 or estimate_a != estimate_b:
            raise ValueError(f"serial/parallel pre-clamp values differ or are invalid: {key}")
        if any(a.get(field) != b.get(field) for field in compared_fields):
            raise ValueError(f"serial/parallel diagnostic semantics differ: {key}")
        for row in (a, b):
            if isinstance(row.get("relation_oid"), bool) or not isinstance(row.get("relation_oid"), int) or row["relation_oid"] <= 0:
                raise ValueError(f"observation lacks a valid per-cluster relation OID: {key}")
            if row.get("mcv_diagnostics_status") == "NO_MCV_EVENTS" and row.get("mcv_candidate_ids"):
                raise ValueError(f"NO_MCV_EVENTS row contains an MCV selection: {key}")
    return {"status": "PASS", "compared_pairs": len(expected), "preclamp_equal": True,
            "diagnostic_semantics_equal": True, "oid_policy": "each cluster OID retained and validated independently"}
