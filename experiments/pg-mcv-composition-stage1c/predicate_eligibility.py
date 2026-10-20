"""Conservative task-predicate eligibility checks for the pinned PG selector.

This is an offline crosswalk, not a replacement PostgreSQL planner.  It only
accepts the simple comparison forms supported by the pinned source's
``statext_is_compatible_clause_internal`` path and expands BETWEEN into the
two comparison clauses PostgreSQL parses.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


SUPPORTED_OPERATORS = frozenset({"=", "<", ">", "<=", ">="})
_BETWEEN = re.compile(
    r'"(?P<column>[^"]+)"\s+BETWEEN\s+'
    r"(?P<lower>[-+0-9.eE]+)\s+AND\s+(?P<upper>[-+0-9.eE]+)",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r'"(?P<column>[^"]+)"\s*(?P<operator><=|>=|=|<|>)\s*'
    r"(?P<value>[-+0-9.eE]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PredicateClause:
    clause_index: int
    column: str
    operator: str
    source_text: str


def _where_sql(sql: str) -> str:
    match = re.search(r"\bWHERE\b(?P<where>.*?)(?:;\s*)?$", sql, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("query has no WHERE clause")
    return match.group("where")


def extract_supported_clauses(sql: str) -> list[PredicateClause]:
    """Expand simple source predicates in planner clause order.

    The function fails closed if a quoted column predicate is not one of the
    supported comparison forms.  It intentionally does not claim to parse
    arbitrary SQL.
    """

    where = _where_sql(sql)
    matches: list[tuple[int, int, str, str, str]] = []
    for match in _BETWEEN.finditer(where):
        matches.append((match.start(), match.end(), match.group("column"), ">=", match.group(0)))
        matches.append((match.start(), match.end(), match.group("column"), "<=", match.group(0)))
    for match in _COMPARISON.finditer(where):
        if not any(start <= match.start() < end for start, end, *_ in matches):
            matches.append((match.start(), match.end(), match.group("column"), match.group("operator"), match.group(0)))
    matches.sort(key=lambda item: (item[0], item[3] == "<="))

    quoted_columns = set(re.findall(r'"([^"]+)"', where))
    parsed_columns = {item[2] for item in matches}
    if quoted_columns - parsed_columns:
        raise ValueError(f"unsupported or unparsed quoted predicates: {sorted(quoted_columns - parsed_columns)}")
    if not matches:
        raise ValueError("no supported comparison predicates")

    return [
        PredicateClause(index, column, operator, source_text)
        for index, (_, _, column, operator, source_text) in enumerate(matches)
    ]


def eligible_candidate_edges(
    sql: str,
    candidates: Iterable[Mapping[str, object]],
) -> tuple[list[PredicateClause], dict[str, dict[str, object]]]:
    """Return clauses and a conservative per-candidate eligibility ledger."""

    clauses = extract_supported_clauses(sql)
    by_column: dict[str, list[PredicateClause]] = {}
    for clause in clauses:
        by_column.setdefault(clause.column, []).append(clause)

    result: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        candidate_id = str(candidate["id"])
        columns = [str(column) for column in candidate["columns"]]
        missing = [column for column in columns if column not in by_column]
        endpoint_clauses = {
            column: [clause.clause_index for clause in by_column.get(column, [])]
            for column in columns
        }
        if missing:
            result[candidate_id] = {
                "eligible": False,
                "reason": "missing_supported_predicate",
                "missing_columns": missing,
                "endpoint_clause_indices": endpoint_clauses,
            }
        else:
            result[candidate_id] = {
                "eligible": True,
                "reason": "both_endpoints_have_supported_predicates",
                "missing_columns": [],
                "endpoint_clause_indices": endpoint_clauses,
            }
    return clauses, result
