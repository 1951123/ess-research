from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import audit_structure
import pytest
from audit_structure import (
    canonical_predicate_fingerprint,
    fingerprint_audit,
    maximal_matchings,
    normalised_template,
    protocol,
    query_values,
    source_sql_text_fingerprint,
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


def test_fingerprint_names_distinguish_sql_text_and_canonical_predicates() -> None:
    left = query(
        {"column": "a", "operator": "=", "value": 1},
        {"column": "b", "operator": "=", "value": 2},
    )
    right = query(
        {"column": "b", "operator": "=", "value": 2},
        {"column": "a", "operator": "=", "value": 1},
    )
    assert canonical_predicate_fingerprint(left) != canonical_predicate_fingerprint(
        right
    )
    assert source_sql_text_fingerprint(left) == source_sql_text_fingerprint(right)
    assert set(fingerprint_audit({"train": [left], "test": [right]})) == {
        "canonical_predicate",
        "source_sql_text",
        "template",
    }


def _provenance_fixture(
    tmp_path: Path,
) -> tuple[dict[str, object], Path, dict[str, list[dict[str, object]]]]:
    dataset = "census13"
    columns = list(audit_structure.source_columns(dataset))
    csv_path = tmp_path / "table.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerow(["1"] * len(columns))

    splits: dict[str, list[dict[str, object]]] = {}
    for split in audit_structure.SPLITS:
        splits[split] = [
            {
                "query_id": f"arecel:{dataset}:{split}:000000",
                "source_index": 0,
                "source_sql": "SELECT COUNT(*) FROM public.census13 WHERE \"age\" = '1';",
                "predicates": [{"column": "age", "operator": "=", "value": 1}],
                "weight": 1.0,
            }
        ]
    manifest = {
        "format": "arecel-preparation-v1",
        "issue": 59,
        "dataset": dataset,
        "archive_sha256": protocol()["source_contract"]["archive_sha256"],
        "upstream_commit": protocol()["source_contract"]["upstream_commit"],
        "splits": dict(audit_structure.EXPECTED_PREPARED_SPLIT_COUNTS),
    }
    return manifest, csv_path, splits


def test_changed_csv_same_shape_fails_before_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        audit_structure,
        "EXPECTED_PREPARED_SPLIT_COUNTS",
        {split: 1 for split in audit_structure.SPLITS},
    )
    monkeypatch.setattr(audit_structure, "source_rows", lambda dataset: 1)
    manifest, csv_path, splits = _provenance_fixture(tmp_path)
    good_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    csv_path.write_bytes(csv_path.read_bytes().replace(b"1,1", b"2,1", 1))
    monkeypatch.setattr(
        audit_structure, "source_csv_expected_sha256", lambda dataset: good_sha256
    )
    with pytest.raises(ValueError, match="CSV SHA256 mismatch"):
        audit_structure.validate_prepared_provenance(
            protocol(), "census13", manifest, csv_path, splits
        )


def test_corrupted_manifest_fails_before_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        audit_structure,
        "EXPECTED_PREPARED_SPLIT_COUNTS",
        {split: 1 for split in audit_structure.SPLITS},
    )
    monkeypatch.setattr(audit_structure, "source_rows", lambda dataset: 1)
    manifest, csv_path, splits = _provenance_fixture(tmp_path)
    manifest["archive_sha256"] = "0" * 64
    good_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        audit_structure, "source_csv_expected_sha256", lambda dataset: good_sha256
    )
    with pytest.raises(ValueError, match="prepared archive SHA256 mismatch"):
        audit_structure.validate_prepared_provenance(
            protocol(), "census13", manifest, csv_path, splits
        )
