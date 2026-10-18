from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import pickle
from collections import OrderedDict
from pathlib import Path

import pytest

from ess_research.arecel import real

_CONVERTER_PATH = (
    Path(__file__).parents[1] / "experiments" / "arecel" / "convert_verified_pickles.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "ess_research_real_converter_test", _CONVERTER_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
_CONVERTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONVERTER)


@pytest.mark.parametrize("dataset", sorted(real.SPECS))
def test_frozen_schema_and_sql_contracts(dataset):
    spec = real.SPECS[dataset]
    contract = real.schema_contract(spec)
    assert len(contract["columns"]) == len(spec.source_columns)
    assert contract["not_null"] is spec.not_null
    first, second = spec.source_columns[:2]
    source = (
        f"SELECT COUNT(*) FROM {spec.source_relation} "
        f'WHERE "{first}" = 1 AND "{second}" = 2;'
    )
    adapted = real.adapt_query_sql(source, spec)
    assert adapted.startswith(f"SELECT * FROM {spec.relation}")
    if dataset == "census13":
        assert f'"{first}"' in adapted
    else:
        assert f'"{spec.columns[0][0]}"' in adapted
    with pytest.raises(real.InputContractError, match="audited relation"):
        real.adapt_query_sql('SELECT COUNT(*) FROM public.other WHERE "x" = 1;', spec)


def test_missing_real_input_is_explicitly_blocked(tmp_path):
    result = real.inspect_source(tmp_path / "missing", "census13")
    assert result["source_present"] is False
    assert result["status"] == "BLOCKED_MISSING_INPUT"
    with pytest.raises(real.InputContractError, match="missing audit"):
        real.validate_source(tmp_path / "missing", "census13")


@pytest.mark.parametrize("dataset", sorted(real.SPECS))
def test_canonical_records_validate_source_truth_and_order(tmp_path, dataset):
    spec = real.SPECS[dataset]
    first, second = spec.source_columns[:2]
    source_sql = (
        f"SELECT COUNT(*) FROM {spec.source_relation} "
        f'WHERE "{first}" = 1 AND "{second}" = 2;'
    )
    records = []
    for split in real.SPLITS:
        records.append(
            {
                "split": split,
                "index": 0,
                "query_id": f"arecel:{dataset}:{split}:000000",
                "sql": source_sql,
                "source_query": {
                    "format": "arecel-source-query-v1",
                    "table": dataset,
                    "ncols": 2,
                    "predicates": [
                        {"column": first, "operator": "=", "value": 1},
                        {"column": second, "operator": "=", "value": 2},
                    ],
                },
                "source_query_sha256": hashlib.sha256(source_sql.encode()).hexdigest(),
                "source_label": {"cardinality": 7, "selectivity": 0.25},
                "weight": 1.0,
            }
        )
    path = tmp_path / f"{dataset}.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    parsed = real._canonical_records(path, spec)
    assert [record["split"] for record in parsed] == list(real.SPLITS)
    assert real._split_records(parsed, spec)["train"][0]["true_cardinality"] == 7


def _tiny_query(spec):
    first, second = spec.source_columns[:2]
    first_type = spec.columns[0][1]
    first_value = 1.5 if first_type == "DOUBLE PRECISION" else "value"
    second_value = 2.5 if spec.columns[1][1] == "DOUBLE PRECISION" else "value2"
    return _CONVERTER.SafeQuery(
        OrderedDict(
            [
                (first, ("=", first_value)),
                (second, ("=", second_value)),
            ]
        ),
        2,
    )


@pytest.mark.parametrize("dataset", sorted(real.SPECS))
def test_restricted_converter_records_all_observed_splits(dataset):
    spec = real.SPECS[dataset]
    query = _tiny_query(spec)
    label = _CONVERTER.SafeLabel(7, 0.25)
    workload = {split: [query] for split in real.SPLITS}
    labels = {split: [label] for split in real.SPLITS}
    records = _CONVERTER._records(spec, workload, labels)
    assert [record["split"] for record in records] == list(real.SPLITS)
    assert all(record["source_query"]["table"] == dataset for record in records)
    assert all(record["source_label"]["cardinality"] == 7 for record in records)


def test_restricted_unpickler_rejects_unexpected_global_and_hash_mismatch(tmp_path):
    with pytest.raises(_CONVERTER.ConversionError, match="not allowlisted"):
        _CONVERTER.RestrictedUnpickler(io.BytesIO(b"cos\nsystem\n.")).load()
    path = tmp_path / "tiny.pkl"
    path.write_bytes(pickle.dumps({"not": "trusted"}, protocol=4))
    with pytest.raises(_CONVERTER.ConversionError, match="SHA256 mismatch"):
        _CONVERTER._load_pinned(path, "0" * 64, "fixture pickle")


def test_deterministic_gzip_is_stable_and_no_overwrite(tmp_path):
    first = tmp_path / "first.jsonl.gz"
    second = tmp_path / "second.jsonl.gz"
    records = [{"b": 2, "a": "stable"}]
    _CONVERTER._write_deterministic_gzip(first, records)
    _CONVERTER._write_deterministic_gzip(second, records)
    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(_CONVERTER.ConversionError, match="overwrite"):
        _CONVERTER._write_deterministic_gzip(first, records)
