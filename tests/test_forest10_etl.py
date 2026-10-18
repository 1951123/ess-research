from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from ess_research.arecel import forest10


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_synthetic_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "input"
    forest_root = root / "arecel" / "raw" / "data" / "forest10"
    audit_root = root / "arecel" / "audit-v1"
    forest_root.joinpath("workload").mkdir(parents=True)
    audit_root.mkdir(parents=True)

    csv_bytes = (
        (",".join(forest10.SOURCE_COLUMNS) + "\n")
        + "1,2,3,4,5,6,7,8,9,10\n"
        + "11,,13,14,15,16,17,18,19,20\n"
    ).encode()
    csv_path = forest_root / "original.csv"
    csv_path.write_bytes(csv_bytes)
    workload_pickle = b"not a pickle; this boundary hashes bytes only"
    label_pickle = b"also deliberately not deserialized"
    (forest_root / "workload" / "base.pkl").write_bytes(workload_pickle)
    (forest_root / "workload" / "base-original-label.pkl").write_bytes(label_pickle)

    records = []
    for split, cardinality in (("valid", 7), ("test", 11)):
        source_sql = (
            'SELECT COUNT(*) FROM public."forest10_original" '
            'WHERE "Elevation" <= 10.5 AND "Aspect" = \'literal forest10_original\';'
        )
        records.append(
            {
                "split": split,
                "index": 0,
                "query_id": f"arecel:forest10:{split}:000000",
                "sql": source_sql,
                "source_query": {"predicates": [{"column": "Elevation"}]},
                "source_query_sha256": _sha(source_sql.encode()),
                "source_label": {
                    "cardinality": cardinality,
                    "method": "synthetic-exact-count-v1",
                },
                "weight": 2.0,
            }
        )
    canonical_buffer = io.StringIO()
    for record in records:
        canonical_buffer.write(json.dumps(record, sort_keys=True) + "\n")
    canonical_path = audit_root / "forest10.canonical.jsonl.gz"
    with gzip.open(canonical_path, "wt", encoding="utf-8") as stream:
        stream.write(canonical_buffer.getvalue())
    canonical_bytes = canonical_path.read_bytes()

    archive_path = root / "arecel" / "incoming" / "arecel-data.tar.gz"
    archive_path.parent.mkdir(parents=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, content in {
            "data/forest10/original.csv": csv_bytes,
            "data/forest10/workload/base.pkl": workload_pickle,
            "data/forest10/workload/base-original-label.pkl": label_pickle,
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))

    hashes = {
        "archive": _sha(archive_path.read_bytes()),
        "csv": _sha(csv_bytes),
        "workload": _sha(workload_pickle),
        "label": _sha(label_pickle),
        "canonical": _sha(canonical_bytes),
    }
    monkeypatch.setattr(forest10, "ARCHIVE_SHA256", hashes["archive"])
    monkeypatch.setattr(forest10, "CSV_SHA256", hashes["csv"])
    monkeypatch.setattr(forest10, "WORKLOAD_PICKLE_SHA256", hashes["workload"])
    monkeypatch.setattr(forest10, "LABEL_PICKLE_SHA256", hashes["label"])
    monkeypatch.setattr(forest10, "CANONICAL_WORKLOAD_SHA256", hashes["canonical"])
    monkeypatch.setattr(forest10, "EXPECTED_ROWS", 2)
    monkeypatch.setattr(forest10, "EXPECTED_SPLIT_COUNTS", {"valid": 1, "test": 1})
    audit = {
        "format": "arecel-source-audit-v1",
        "upstream": {
            "repository": forest10.UPSTREAM_URL,
            "commit": forest10.UPSTREAM_COMMIT,
        },
        "archive": {"url": forest10.ARCHIVE_URL, "sha256": hashes["archive"]},
        "datasets": {
            forest10.BENCHMARK_ID: {
                "csv": {"sha256": hashes["csv"], "rows": 2},
                "workload": {
                    "pickle_sha256": hashes["workload"],
                    "label_pickle_sha256": hashes["label"],
                    "canonical_sha256": hashes["canonical"],
                },
                "schema_contract_id": forest10.SCHEMA_CONTRACT_ID,
            }
        },
    }
    (audit_root / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
    return root


def test_explicit_data_root_is_required_and_missing_inputs_fail_closed(tmp_path):
    with pytest.raises(forest10.InputContractError, match="explicit"):
        forest10.validate_source(None)
    report = forest10.inspect_source(tmp_path / "does-not-exist")
    assert report["source_present"] is False
    assert report["status"] == "BLOCKED_MISSING_INPUT"
    with pytest.raises(forest10.InputContractError, match="audit metadata"):
        forest10.validate_source(tmp_path / "does-not-exist")


def test_synthetic_source_round_trip_and_truth_separation(tmp_path, monkeypatch):
    root = _write_synthetic_input(tmp_path, monkeypatch)
    validation = forest10.validate_source(root)
    assert validation["split_counts"] == {"valid": 1, "test": 1}

    output = tmp_path / "output"
    manifest = forest10.build_artifacts(root, output, split="test")
    workload = json.loads((output / "workload.json").read_text(encoding="utf-8"))
    truth = json.loads((output / "truth.json").read_text(encoding="utf-8"))
    assert manifest["record_count"] == 1
    assert workload["queries"][0]["query_id"] == "arecel_forest10_test_000000"
    assert workload["queries"][0]["source_sql"].startswith("SELECT COUNT(*)")
    assert workload["queries"][0]["estimator_sql"].startswith(
        "SELECT * FROM public.forest10"
    )
    assert "true_cardinality" not in workload["queries"][0]
    assert truth["truth"][0]["true_cardinality"] == 11
    assert truth["truth"][0]["truth_sql"] == workload["queries"][0]["source_sql"]
    with pytest.raises(forest10.InputContractError, match="overwrite"):
        forest10.build_artifacts(root, output, split="test")


def test_sql_adaptation_changes_only_contractual_identifiers_and_projection():
    source = (
        'SELECT COUNT(*) FROM public."forest10_original" '
        'WHERE "Elevation" <= 1.25 AND "Aspect" = \'forest10_original\' '
        'AND "Slope" >= -3.0;'
    )
    adapted = forest10.adapt_query_sql(source)
    assert adapted == (
        "SELECT * FROM public.forest10 "
        'WHERE "elevation" <= 1.25 AND "aspect" = \'forest10_original\' '
        'AND "slope" >= -3.0;'
    )
    with pytest.raises(forest10.InputContractError, match="audited relation"):
        forest10.adapt_query_sql("SELECT COUNT(*) FROM public.other WHERE 1 = 1")
    with pytest.raises(forest10.InputContractError, match="outside"):
        forest10.adapt_query_sql(
            'SELECT COUNT(*) FROM public."forest10_original" WHERE "unknown" = 1'
        )


def test_csv_hash_mismatch_is_rejected(tmp_path, monkeypatch):
    root = _write_synthetic_input(tmp_path, monkeypatch)
    csv_path = root / "arecel" / "raw" / "data" / "forest10" / "original.csv"
    csv_path.write_bytes(csv_path.read_bytes() + b"\n")
    with pytest.raises(forest10.InputContractError, match="CSV SHA256 mismatch"):
        forest10.validate_source(root)


def test_duplicate_canonical_indices_are_rejected(tmp_path, monkeypatch):
    root = _write_synthetic_input(tmp_path, monkeypatch)
    canonical = root / "arecel" / "audit-v1" / "forest10.canonical.jsonl.gz"
    with gzip.open(canonical, "rt", encoding="utf-8") as stream:
        original_lines = stream.readlines()
    with gzip.open(canonical, "wt", encoding="utf-8") as stream:
        stream.writelines(original_lines)
        stream.write(original_lines[0])
    updated_hash = _sha(canonical.read_bytes())
    updated_records = forest10._canonical_records(canonical, updated_hash)
    with pytest.raises(forest10.InputContractError, match="expected 1 Forest10 valid"):
        forest10._validate_split(updated_records, "valid")


def test_unsafe_archive_member_is_rejected(tmp_path):
    path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("../escape")
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(forest10.InputContractError, match="unsafe archive"):
        forest10._archive_members(path)


def test_pickle_bytes_are_only_hashed_never_deserialized(tmp_path, monkeypatch):
    root = _write_synthetic_input(tmp_path, monkeypatch)
    report = forest10.validate_source(root)
    assert (
        report["source_file_sha256"]["workload_pickle"]
        == forest10.WORKLOAD_PICKLE_SHA256
    )
    assert report["source_file_sha256"]["label_pickle"] == forest10.LABEL_PICKLE_SHA256
