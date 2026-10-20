from __future__ import annotations

import pytest

from audit_structure import (
    maximal_matchings,
    normalised_template,
    protocol,
    query_values,
    split_summary,
)


def graph() -> list[dict[str, object]]:
    return [
        {"id": "e01", "source_columns": ["a", "b"]},
        {"id": "e12", "source_columns": ["b", "c"]},
        {"id": "e23", "source_columns": ["c", "d"]},
    ]


def query(*predicates: dict[str, object], query_id: str = "q") -> dict[str, object]:
    return {
        "query_id": query_id,
        "source_index": 0,
        "source_sql": "SELECT COUNT(*) FROM public.t WHERE ...",
        "predicates": list(predicates),
        "weight": 1.0,
    }


def test_protocol_is_frozen_and_outcome_free() -> None:
    value = protocol()
    assert value["status"] == "FROZEN_BEFORE_STRUCTURAL_AUDIT_V1"
    assert value["scope"]["no_test_truth_values"] is True
    assert value["scope"]["no_postgresql"] is True
    assert len(value["candidate_universe"]["dmv11"]["candidates"]) == 10
    assert len(value["candidate_universe"]["power7"]["candidates"]) == 6


def test_maximal_matching_differs_from_maximum_cardinality() -> None:
    candidates = graph()
    matchings = maximal_matchings(0b111, candidates)
    assert () not in matchings
    assert ("e12",) in matchings
    assert ("e01", "e23") in matchings
    assert len(matchings) == 2


def test_raw_strict_and_calibration_edges_are_separate() -> None:
    candidates = {item["id"]: item for item in graph()}
    value = query_values(
        query(
            {"column": "a", "operator": "=", "value": 1},
            {"column": "b", "operator": "<", "value": 2},
            {"column": "b", "operator": ">", "value": 0},
        ),
        candidates,
    )
    assert value["raw_edges"] == ["e01"]
    assert value["calibration_edges"] == ["e01"]
    assert value["strict_edges"] == []
    assert value["repeated_predicate_columns"] == ["b"]


def test_malformed_column_and_operator_are_recorded_without_coercion() -> None:
    candidates = {item["id"]: item for item in graph()}
    value = query_values(
        query(
            {"column": "a", "operator": "LIKE", "value": "x"},
            {"column": "unknown", "operator": "=", "value": 1},
        ),
        candidates,
    )
    assert value["unknown_columns"] == ["unknown"]
    assert value["unsupported_operators"] == ["LIKE"]
    assert value["calibration_edges"] == []
    assert value["strict_edges"] == []


def test_duplicate_query_ids_fail_closed() -> None:
    candidates = {item["id"]: item for item in graph()}
    record = query(
        {"column": "a", "operator": "=", "value": 1},
        {"column": "b", "operator": "=", "value": 2},
    )
    with pytest.raises(ValueError, match="duplicate query IDs"):
        split_summary([record, {**record}], candidates)


def test_template_fingerprint_removes_literal_values() -> None:
    left = query(
        {"column": "a", "operator": "=", "value": 1},
        {"column": "b", "operator": "[]", "value": [2, 3]},
    )
    right = query(
        {"column": "b", "operator": "[]", "value": [20, 30]},
        {"column": "a", "operator": "=", "value": 10},
    )
    assert normalised_template(left) == normalised_template(right)
