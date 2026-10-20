"""Pure-Python source-indexed ledger and fail-closed gate checks.

The ledger mirrors only the pinned PostgreSQL 16.14 path under the frozen
simple equality premises.  It is not a general SQL parser or a replacement
for PostgreSQL's planner.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


class LedgerError(ValueError):
    """The frozen source premises cannot be established."""


_WHERE_RE = re.compile(r"\bWHERE\b(?P<body>.*?)(?:;\s*)?$", re.IGNORECASE | re.DOTALL)
_TERM_RE = re.compile(r"^(?P<column>[a-z][a-z0-9_]*)\s*=\s*(?P<value>-?[0-9]+)$", re.IGNORECASE)


def parse_equality_clauses(sql: str, expected_columns: Iterable[str]) -> list[dict[str, object]]:
    """Parse the deliberately narrow one-equality-per-column fixture form."""

    match = _WHERE_RE.search(sql.strip())
    if not match:
        raise LedgerError("query has no WHERE clause")
    body = match.group("body").strip()
    if re.search(r"\b(?:OR|BETWEEN|LIKE|IS|IN|NOT)\b", body, re.IGNORECASE):
        raise LedgerError("query is outside the simple equality-only gate")
    terms = [term.strip() for term in re.split(r"\s+AND\s+", body, flags=re.IGNORECASE)]
    expected = list(expected_columns)
    if len(set(expected)) != len(expected):
        raise LedgerError("expected columns are not distinct")
    clauses: list[dict[str, object]] = []
    for index, term in enumerate(terms):
        parsed = _TERM_RE.fullmatch(term.rstrip(";"))
        if not parsed:
            raise LedgerError(f"unsupported equality term: {term!r}")
        clauses.append({
            "clause_index": index,
            "column": parsed.group("column"),
            "operator": "=",
            "source_text": term,
        })
    columns = [str(item["column"]) for item in clauses]
    if columns != expected:
        raise LedgerError(f"clause crosswalk mismatch: parsed={columns}, expected={expected}")
    return clauses


def _is_mcv(row: Mapping[str, object]) -> bool:
    kind = str(row.get("kind", ""))
    return "m" in kind.lower()


def _clause_indices_for_row(
    row: Mapping[str, object],
    clauses: list[Mapping[str, object]],
    remaining: set[int],
) -> list[int]:
    columns = {str(item) for item in row.get("columns", [])}
    return [
        int(clause["clause_index"])
        for clause in clauses
        if int(clause["clause_index"]) in remaining and str(clause["column"]) in columns
    ]


def build_source_ledger(
    catalog_rows: Iterable[Mapping[str, object]],
    clauses: list[Mapping[str, object]],
) -> dict[str, object]:
    """Reconstruct every selector iteration from catalog rows and clauses.

    For the frozen fixture every object has exactly two user keys and every
    clause is a simple Var = Const over a distinct attribute. Under these
    premises, ``choose_best_statistics`` selects the first OID-ordered row
    covering both remaining endpoint clauses. The ledger records all rows at
    every iteration, including rows skipped by kind, inheritance, coverage,
    or key-shape checks.
    """

    rows = sorted((dict(row) for row in catalog_rows), key=lambda row: int(row["oid"]))
    if [int(row["oid"]) for row in rows] != sorted(int(row["oid"]) for row in rows):
        raise LedgerError("catalog rows are not OID ordered")
    remaining = {int(clause["clause_index"]) for clause in clauses}
    iterations: list[dict[str, object]] = []

    while True:
        considered: list[dict[str, object]] = []
        best: Mapping[str, object] | None = None
        best_matched = 2
        best_keys = 9  # STATS_MAX_DIMENSIONS + 1 in the pinned source.
        for row in rows:
            keys = [int(key) for key in row.get("keys", [])]
            matched = _clause_indices_for_row(row, clauses, remaining)
            num_matched = len({str(clauses[index]["column"]) for index in matched})
            reasons: list[str] = []
            if not _is_mcv(row):
                reasons.append("wrong_kind")
            if not bool(row.get("source_loaded", True)):
                reasons.append("mcv_kind_not_built")
            if bool(row.get("inherit", False)):
                reasons.append("inheritance_mismatch")
            if len(keys) != 2:
                reasons.append("not_two_keys")
            if num_matched < 2:
                reasons.append("fewer_than_two_remaining_attributes")
            selector_eligible = not reasons
            if selector_eligible and (
                num_matched > best_matched
                or (num_matched == best_matched and len(keys) < best_keys)
            ):
                best = row
                best_matched = num_matched
                best_keys = len(keys)
            considered.append({
                "candidate_id": str(row["id"]),
                "statistic_oid": int(row["oid"]),
                "remaining_clause_indices": sorted(remaining),
                "matched_clause_indices": matched,
                "num_matched_attributes": num_matched,
                "num_keys": len(keys),
                "selector_eligible": selector_eligible,
                "usable_edge": bool(row.get("source_loaded", True)) and bool(row.get("mcv_item_count", 0) > 0) and selector_eligible,
                "skip_reasons": reasons,
            })

        if best is None:
            iterations.append({
                "remaining_clause_indices": sorted(remaining),
                "considered": considered,
                "selected_candidate_id": None,
                "selected_statistic_oid": None,
            })
            break

        selected_indices = _clause_indices_for_row(best, clauses, remaining)
        iterations.append({
            "remaining_clause_indices": sorted(remaining),
            "considered": considered,
            "selected_candidate_id": str(best["id"]),
            "selected_statistic_oid": int(best["oid"]),
            "selected_claimed_clause_indices": selected_indices,
        })
        remaining.difference_update(selected_indices)

    usable_ids = [
        str(row["id"])
        for row in rows
        if bool(row.get("source_loaded", True))
        and bool(row.get("mcv_item_count", 0) > 0)
        and len(row.get("keys", [])) == 2
        and all(
            any(str(clause["column"]) == str(column) for clause in clauses)
            for column in row.get("columns", [])
        )
    ]
    return {
        "source_basis": "PostgreSQL 16.14 choose_best_statistics and statext_mcv_clauselist_selectivity under frozen simple-equality premises",
        "catalog_order": [int(row["oid"]) for row in rows],
        "remaining_clause_indices_at_termination": sorted(remaining),
        "iterations": iterations,
        "expected_selected_ids": [
            str(item["selected_candidate_id"])
            for item in iterations
            if item["selected_candidate_id"] is not None
        ],
        "expected_selected_oids": [
            int(item["selected_statistic_oid"])
            for item in iterations
            if item["selected_statistic_oid"] is not None
        ],
        "expected_claimed_clause_indices": [
            int(index)
            for item in iterations
            if item["selected_candidate_id"] is not None
            for index in item["selected_claimed_clause_indices"]
        ],
        "usable_ids": usable_ids,
        "source_loaded_ids": [
            str(row["id"]) for row in rows if bool(row.get("source_loaded", True))
        ],
        "complete_considered_candidate_ledger": True,
    }


def verify_trace_against_ledger(
    ledger: Mapping[str, object],
    catalog_rows: Iterable[Mapping[str, object]],
    trace: Mapping[str, object],
) -> dict[str, object]:
    """Classify one trace without silently promoting an incomplete trace."""

    selected_oids = [int(item) for item in trace.get("selected_stat_oids", [])]
    claimed = [int(item) for item in trace.get("claimed_clause_indices", [])]
    expected_oids = [int(item) for item in ledger["expected_selected_oids"]]
    expected_claimed = [int(item) for item in ledger["expected_claimed_clause_indices"]]
    catalog_by_oid = {int(row["oid"]): row for row in catalog_rows}
    selected_ids = [str(catalog_by_oid[oid]["id"]) for oid in selected_oids if oid in catalog_by_oid]
    reasons: list[str] = []

    if any(oid not in catalog_by_oid for oid in selected_oids):
        reasons.append("unmapped_selected_stat_oid")
    if selected_oids != expected_oids:
        reasons.append("selected_sequence_not_reconciled_with_source_ledger")
    if claimed != expected_claimed:
        reasons.append("claimed_clause_indices_not_reconciled_with_source_ledger")
    if not bool(trace.get("candidate_none", False)) and not trace.get("query_error"):
        reasons.append("missing_candidate_none_termination")
    if trace.get("query_error"):
        reasons.append("query_error")

    usable_ids = set(str(item) for item in ledger["usable_ids"])
    selected_outside = [item for item in selected_ids if item not in usable_ids]
    if selected_outside:
        reasons.append("selected_outside_usable_edge_graph")

    no_built_mcv_early_return = bool(catalog_by_oid) and not ledger.get("source_loaded_ids") and not trace.get("query_error")
    if no_built_mcv_early_return:
        reasons.append("no_built_mcv_kind_early_return")

    result: dict[str, object] = {
        "selected_stat_oids": selected_oids,
        "selected_candidate_ids": selected_ids,
        "selected_outside_usable_edge_graph": selected_outside,
        "expected_selected_oids": expected_oids,
        "expected_claimed_clause_indices": expected_claimed,
        "source_ledger_complete": bool(ledger.get("complete_considered_candidate_ledger")),
        "reconciliation_reasons": reasons,
    }
    if no_built_mcv_early_return:
        result["status"] = "OUTSIDE_GATE"
    elif trace.get("query_error") and selected_outside:
        result["status"] = "OUTSIDE_GATE"
    elif trace.get("query_error"):
        result["status"] = "INCONCLUSIVE"
    elif selected_outside:
        result["status"] = "OUTSIDE_GATE"
    elif reasons:
        result["status"] = "INCONCLUSIVE"
    else:
        result["status"] = "WITHIN_GATE_PASS"
    return result

