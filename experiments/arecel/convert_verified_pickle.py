#!/usr/bin/env python3
"""One-time, gated conversion of the two pinned Forest10 pickle inputs.

This file is not imported by the normal ETL module, CI, or ordinary parsing
commands.  It is intended to run only in a disposable network-disabled
sandbox after the two input hashes have been independently verified.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import pickle
import stat
import tempfile
from collections import OrderedDict, namedtuple
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from numpy._core import multiarray as _numpy_multiarray

ARCHIVE_UPSTREAM_COMMIT = "aa52da7768023270bad884232972e0b77ec6534a"
WORKLOAD_SHA256 = "501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea"
LABEL_SHA256 = "34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974"
HISTORICAL_CANONICAL_SHA256 = (
    "a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74"
)
CANONICAL_FORMAT = "arecel-forest10-derived-canonical-v1"
SOURCE_COLUMNS = (
    "Elevation",
    "Aspect",
    "Slope",
    "Horizontal_Distance_To_Hydrology",
    "Vertical_Distance_To_Hydrology",
    "Horizontal_Distance_To_Roadways",
    "Hillshade_9am",
    "Hillshade_Noon",
    "Hillshade_3pm",
    "Horizontal_Distance_To_Fire_Points",
)
EXPECTED_SPLITS = {"valid": 10_000, "test": 10_000}

SafeQuery = namedtuple("SafeQuery", ("predicates", "ncols"))
SafeLabel = namedtuple("SafeLabel", ("cardinality", "selectivity"))


class ConversionError(ValueError):
    pass


class RestrictedUnpickler(pickle.Unpickler):
    """Allow only the known value constructors used by the pinned files."""

    _allowed: ClassVar[dict[tuple[str, str], Any]] = {
        ("builtins", "set"): set,
        ("builtins", "frozenset"): frozenset,
        ("collections", "OrderedDict"): OrderedDict,
        ("lecarb.workload.workload", "Query"): SafeQuery,
        ("lecarb.workload.workload", "Label"): SafeLabel,
        ("numpy.core.multiarray", "scalar"): _numpy_multiarray.scalar,
        ("numpy", "dtype"): np.dtype,
    }

    def find_class(self, module: str, name: str) -> Any:
        try:
            return self._allowed[(module, name)]
        except KeyError as exc:
            raise ConversionError(
                f"pickle global is not allowlisted: {module}.{name}"
            ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular_nonlink(path: Path, label: str) -> None:
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise ConversionError(f"{label} must be a regular non-symlink file")


def _load_pinned(path: Path, expected_sha256: str, label: str) -> Any:
    _regular_nonlink(path, label)
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ConversionError(f"{label} SHA256 mismatch: {actual}")
    with path.open("rb") as stream:
        return RestrictedUnpickler(stream).load()


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ConversionError("nonfinite numeric value in pinned pickle")
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    raise ConversionError(f"unsupported value type in pinned pickle: {type(value)!r}")


def _sql_value(value: Any) -> str:
    value = _json_value(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if value is None or isinstance(value, bool):
        raise ConversionError("invalid SQL predicate literal")
    return str(value)


def _source_sql(query: SafeQuery) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(query.predicates, (dict, OrderedDict)):
        raise ConversionError("query predicates are not mapping-like")
    predicates: list[str] = []
    provenance: list[dict[str, Any]] = []
    for column, expression in query.predicates.items():
        if column not in SOURCE_COLUMNS:
            raise ConversionError(f"unexpected Forest10 query column: {column!r}")
        if expression is None:
            continue
        if not isinstance(expression, tuple) or len(expression) != 2:
            raise ConversionError("query predicate is not a two-item expression")
        operator, value = expression
        if operator == "[]":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ConversionError("range predicate does not have two bounds")
            left, right = value
            predicate_sql = (
                f'"{column}" between {_sql_value(left)} and {_sql_value(right)}'
            )
            predicate_record = {
                "column": column,
                "operator": "[]",
                "value": [_json_value(left), _json_value(right)],
            }
        elif isinstance(operator, str) and operator in {"=", "<", "<=", ">", ">="}:
            predicate_sql = f'"{column}" {operator} {_sql_value(value)}'
            predicate_record = {
                "column": column,
                "operator": operator,
                "value": _json_value(value),
            }
        else:
            raise ConversionError(
                f"unsupported Forest10 predicate operator: {operator!r}"
            )
        predicates.append(predicate_sql)
        provenance.append(predicate_record)
    if not predicates:
        raise ConversionError(
            "empty Forest10 predicate set is not a valid source query"
        )
    sql = (
        'SELECT COUNT(*) FROM public."forest10_original" WHERE '
        + " AND ".join(predicates)
        + ";"
    )
    return sql, provenance


def _records(workload: Any, labels: Any) -> list[dict[str, Any]]:
    if not isinstance(workload, dict) or not isinstance(labels, dict):
        raise ConversionError("pinned pickle roots must be dictionaries")
    if set(workload) != set(labels):
        raise ConversionError("workload and label split keys differ")
    records: list[dict[str, Any]] = []
    for split in ("valid", "test"):
        queries = workload.get(split)
        split_labels = labels.get(split)
        if not isinstance(queries, list) or not isinstance(split_labels, list):
            raise ConversionError(f"missing list split: {split}")
        if (
            len(queries) != EXPECTED_SPLITS[split]
            or len(split_labels) != EXPECTED_SPLITS[split]
        ):
            raise ConversionError(f"unexpected {split} count or alignment")
        for index, (query, label) in enumerate(zip(queries, split_labels, strict=True)):
            if not isinstance(query, SafeQuery) or not isinstance(label, SafeLabel):
                raise ConversionError("pinned object type did not match the allowlist")
            truth = _json_value(label.cardinality)
            if not isinstance(truth, int) or truth < 0:
                raise ConversionError(
                    "source cardinality is not an exact nonnegative integer"
                )
            selectivity = _json_value(label.selectivity)
            if not isinstance(selectivity, (int, float)) or not math.isfinite(
                float(selectivity)
            ):
                raise ConversionError("source selectivity is not finite")
            source_sql, predicates = _source_sql(query)
            query_id = f"arecel:forest10:{split}:{index:06d}"
            records.append(
                {
                    "split": split,
                    "index": index,
                    "query_id": query_id,
                    "sql": source_sql,
                    "source_query": {
                        "format": "arecel-source-query-v1",
                        "table": "forest10_original",
                        "ncols": int(query.ncols),
                        "predicates": predicates,
                    },
                    "source_query_sha256": hashlib.sha256(
                        source_sql.encode("utf-8")
                    ).hexdigest(),
                    "source_label": {
                        "cardinality": truth,
                        "selectivity": float(selectivity),
                        "method": "AreCELearnedYet-base-original-label-pkl-v1",
                    },
                    "weight": 1.0,
                    "weight_provenance": "unit-weight-v1; source pickles contain no task weights",
                }
            )
    return records


def _write_deterministic_gzip(path: Path, records: list[dict[str, Any]]) -> None:
    if path.exists():
        raise ConversionError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)[1])
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(
                fileobj=raw, mode="wb", filename="", mtime=0
            ) as compressed:
                for record in records:
                    line = json.dumps(
                        record,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                    compressed.write((line + "\n").encode("utf-8"))
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload-pickle", type=Path, required=True)
    parser.add_argument("--label-pickle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-pinned-pickle-conversion", action="store_true")
    args = parser.parse_args()
    if not args.allow_pinned_pickle_conversion:
        parser.error(
            "refusing pickle conversion without --allow-pinned-pickle-conversion"
        )
    workload = _load_pinned(args.workload_pickle, WORKLOAD_SHA256, "workload pickle")
    labels = _load_pinned(args.label_pickle, LABEL_SHA256, "label pickle")
    records = _records(workload, labels)
    _write_deterministic_gzip(args.output, records)
    print(
        json.dumps(
            {
                "format": CANONICAL_FORMAT,
                "upstream_commit": ARCHIVE_UPSTREAM_COMMIT,
                "workload_pickle_sha256": WORKLOAD_SHA256,
                "label_pickle_sha256": LABEL_SHA256,
                "historical_canonical_sha256": HISTORICAL_CANONICAL_SHA256,
                "output_sha256": _sha256(args.output),
                "records": len(records),
                "split_counts": {
                    split: EXPECTED_SPLITS[split] for split in EXPECTED_SPLITS
                },
                "weight_policy": "unit-weight-v1",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
