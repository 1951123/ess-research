"""Outcome-format adapter for top-level PostgreSQL EXPLAIN Plan Rows."""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Any


def parse_top_level_plan_rows(payload: str | bytes | dict[str, Any] | list[Any]) -> int:
    """Parse exactly one JSON EXPLAIN root and return its top-level Plan Rows."""
    value: Any = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    if isinstance(value, list):
        if len(value) != 1 or not isinstance(value[0], dict):
            raise ValueError("EXPLAIN JSON must contain exactly one root object")
        value = value[0]
    if not isinstance(value, dict) or not isinstance(value.get("Plan"), dict):
        raise ValueError("EXPLAIN JSON is missing its top-level Plan object")
    estimate = value["Plan"].get("Plan Rows")
    if isinstance(estimate, bool) or not isinstance(estimate, int) or estimate < 0:
        raise ValueError("top-level Plan Rows must be a nonnegative integer")
    return estimate


def q1(plan_rows: int, truth: int) -> Fraction:
    """One-row-floor Q-error: max(E,A,1) / max(min(E,A),1)."""
    for name, value in (("Plan Rows", plan_rows), ("truth", truth)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    return Fraction(max(plan_rows, truth, 1), max(min(plan_rows, truth), 1))
