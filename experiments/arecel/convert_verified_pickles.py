#!/usr/bin/env python3
"""One-time gated conversion of the three pinned AreCEL pickle pairs.

This converter is intentionally outside the normal ETL import path.  It loads
only the exact workload/label hashes frozen in ``arecel.real`` and uses a
restricted pickle global allowlist.  CI and ordinary ``inspect``/``build``
commands consume the resulting canonical JSONL.gz and never deserialize
pickle inputs.
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

from ess_research.arecel.real import (
    DERIVED_CANONICAL_FORMAT,
    SPECS,
    SPLITS,
    UPSTREAM_COMMIT,
    DatasetSpec,
)

SafeQuery = namedtuple("SafeQuery", ("predicates", "ncols"))
SafeLabel = namedtuple("SafeLabel", ("cardinality", "selectivity"))


class ConversionError(ValueError):
    """The pinned conversion input or output contract is invalid."""


class RestrictedUnpickler(pickle.Unpickler):
    """Allow only value constructors observed in the pinned AreCEL files."""

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


def _source_sql(
    query: SafeQuery, spec: DatasetSpec
) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(query.predicates, (dict, OrderedDict)):
        raise ConversionError("query predicates are not mapping-like")
    source_to_type = dict(
        zip(spec.source_columns, (type_ for _, type_ in spec.columns), strict=True)
    )
    predicates: list[str] = []
    provenance: list[dict[str, Any]] = []
    for column, expression in query.predicates.items():
        if column not in spec.source_columns:
            raise ConversionError(f"unexpected {spec.slug} query column: {column!r}")
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
                f"unsupported {spec.slug} predicate operator: {operator!r}"
            )
        if source_to_type[column] == "DOUBLE PRECISION" and isinstance(value, str):
            raise ConversionError(
                f"numeric {spec.slug} predicate contains a string literal"
            )
        if (
            source_to_type[column].startswith("VARCHAR")
            and not isinstance(value, str)
            and operator != "[]"
        ):
            raise ConversionError(
                f"categorical {spec.slug} predicate contains a non-string literal"
            )
        predicates.append(predicate_sql)
        provenance.append(predicate_record)
    if not predicates:
        raise ConversionError(
            f"empty {spec.slug} predicate set is not a valid source query"
        )
    sql = (
        f"SELECT COUNT(*) FROM {spec.source_relation} WHERE "
        + " AND ".join(predicates)
        + ";"
    )
    return sql, provenance


def _records(spec: DatasetSpec, workload: Any, labels: Any) -> list[dict[str, Any]]:
    if not isinstance(workload, dict) or not isinstance(labels, dict):
        raise ConversionError("pinned pickle roots must be dictionaries")
    if set(workload) != set(labels) or set(workload) != set(SPLITS):
        raise ConversionError(
            f"{spec.slug} workload and label split keys must be train/valid/test"
        )
    records: list[dict[str, Any]] = []
    for split in SPLITS:
        queries = workload[split]
        split_labels = labels[split]
        if not isinstance(queries, list) or not isinstance(split_labels, list):
            raise ConversionError(f"{spec.slug} split is not a list")
        if len(queries) != len(split_labels) or not queries:
            raise ConversionError(f"{spec.slug} {split} count or alignment is invalid")
        for index, (query, label) in enumerate(zip(queries, split_labels, strict=True)):
            if not isinstance(query, SafeQuery) or not isinstance(label, SafeLabel):
                raise ConversionError(
                    f"{spec.slug} object type did not match the allowlist"
                )
            truth = _json_value(label.cardinality)
            if not isinstance(truth, int) or truth < 0:
                raise ConversionError(
                    f"{spec.slug} source cardinality is not exact nonnegative integer"
                )
            selectivity = _json_value(label.selectivity)
            if not isinstance(selectivity, (int, float)) or not math.isfinite(
                float(selectivity)
            ):
                raise ConversionError(f"{spec.slug} source selectivity is not finite")
            source_sql, predicates = _source_sql(query, spec)
            records.append(
                {
                    "split": split,
                    "index": index,
                    "query_id": f"arecel:{spec.slug}:{split}:{index:06d}",
                    "sql": source_sql,
                    "source_query": {
                        "format": "arecel-source-query-v1",
                        "table": spec.slug,
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
    parser.add_argument("--dataset", choices=sorted(SPECS), required=True)
    parser.add_argument("--workload-pickle", type=Path, required=True)
    parser.add_argument("--label-pickle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-pinned-pickle-conversion", action="store_true")
    args = parser.parse_args()
    if not args.allow_pinned_pickle_conversion:
        parser.error(
            "refusing pickle conversion without --allow-pinned-pickle-conversion"
        )
    spec = SPECS[args.dataset]
    workload = _load_pinned(
        args.workload_pickle,
        spec.workload_pickle_sha256,
        f"{spec.slug} workload pickle",
    )
    labels = _load_pinned(
        args.label_pickle, spec.label_pickle_sha256, f"{spec.slug} label pickle"
    )
    records = _records(spec, workload, labels)
    _write_deterministic_gzip(args.output, records)
    print(
        json.dumps(
            {
                "format": DERIVED_CANONICAL_FORMAT,
                "dataset": spec.slug,
                "upstream_commit": UPSTREAM_COMMIT,
                "workload_pickle_sha256": spec.workload_pickle_sha256,
                "label_pickle_sha256": spec.label_pickle_sha256,
                "historical_canonical_sha256": spec.historical_canonical_sha256,
                "output_sha256": _sha256(args.output),
                "records": len(records),
                "split_counts": {
                    split: sum(record["split"] == split for record in records)
                    for split in SPLITS
                },
                "weight_policy": "unit-weight-v1",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
