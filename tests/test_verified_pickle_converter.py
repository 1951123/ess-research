from __future__ import annotations

import importlib.util
import io
import pickle
from collections import OrderedDict
from pathlib import Path

import pytest

_CONVERTER_PATH = (
    Path(__file__).parents[1] / "experiments" / "arecel" / "convert_verified_pickle.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "ess_research_verified_pickle_converter_test", _CONVERTER_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
_CONVERTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONVERTER)


def _tiny_query(converter):
    return converter.SafeQuery(
        OrderedDict(
            [
                ("Elevation", ("=", 1.5)),
                ("Aspect", None),
                ("Slope", ("[]", (2.0, 3.0))),
            ]
        ),
        3,
    )


def _tiny_label(converter, cardinality=7):
    return converter.SafeLabel(cardinality, 0.25)


def test_restricted_unpickler_accepts_only_an_allowlisted_global():
    payload = pickle.dumps(OrderedDict([("x", 1)]), protocol=4)
    value = _CONVERTER.RestrictedUnpickler(io.BytesIO(payload)).load()
    assert value == OrderedDict([("x", 1)])


def test_restricted_unpickler_rejects_an_unexpected_global_without_executing_it():
    # This is a tiny in-memory protocol fixture.  The restricted loader must
    # reject the global before any callable can be resolved or invoked.
    payload = b"cos\nsystem\n."
    with pytest.raises(_CONVERTER.ConversionError, match="not allowlisted"):
        _CONVERTER.RestrictedUnpickler(io.BytesIO(payload)).load()


def test_pinned_loader_refuses_a_hash_mismatch_before_deserialization(tmp_path):
    path = tmp_path / "tiny.pkl"
    path.write_bytes(pickle.dumps({"not": "trusted"}, protocol=4))
    with pytest.raises(_CONVERTER.ConversionError, match="SHA256 mismatch"):
        _CONVERTER._load_pinned(path, "0" * 64, "fixture pickle")


def test_records_validate_split_alignment_and_preserve_source_order(monkeypatch):
    monkeypatch.setattr(_CONVERTER, "EXPECTED_SPLITS", {"valid": 1, "test": 1})
    query = _tiny_query(_CONVERTER)
    labels = {
        "valid": [_tiny_label(_CONVERTER)],
        "test": [_tiny_label(_CONVERTER, cardinality=9)],
    }
    records = _CONVERTER._records(
        {"valid": [query], "test": [query]},
        labels,
    )
    assert [record["split"] for record in records] == ["valid", "test"]
    assert records[0]["source_label"]["cardinality"] == 7
    assert records[1]["source_label"]["cardinality"] == 9
    assert records[0]["source_query"]["predicates"] == [
        {"column": "Elevation", "operator": "=", "value": 1.5},
        {"column": "Slope", "operator": "[]", "value": [2.0, 3.0]},
    ]
    assert records[0]["sql"] == (
        'SELECT COUNT(*) FROM public."forest10_original" '
        'WHERE "Elevation" = 1.5 AND "Slope" between 2.0 and 3.0;'
    )


def test_records_reject_misaligned_splits_and_invalid_truth(monkeypatch):
    monkeypatch.setattr(_CONVERTER, "EXPECTED_SPLITS", {"valid": 1, "test": 1})
    query = _tiny_query(_CONVERTER)
    with pytest.raises(_CONVERTER.ConversionError, match="unexpected test count"):
        _CONVERTER._records(
            {"valid": [query], "test": [query]},
            {"valid": [_tiny_label(_CONVERTER)], "test": []},
        )
    with pytest.raises(_CONVERTER.ConversionError, match="nonnegative integer"):
        _CONVERTER._records(
            {"valid": [query], "test": [query]},
            {
                "valid": [_tiny_label(_CONVERTER, cardinality=-1)],
                "test": [_tiny_label(_CONVERTER)],
            },
        )


def test_deterministic_gzip_is_byte_stable_and_never_overwrites(tmp_path):
    first = tmp_path / "first.jsonl.gz"
    second = tmp_path / "second.jsonl.gz"
    records = [{"b": 2, "a": "stable"}]
    _CONVERTER._write_deterministic_gzip(first, records)
    _CONVERTER._write_deterministic_gzip(second, records)
    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(_CONVERTER.ConversionError, match="refusing to overwrite"):
        _CONVERTER._write_deterministic_gzip(first, records)
