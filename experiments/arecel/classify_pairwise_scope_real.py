#!/usr/bin/env python3
"""Read-only source-shape screen for the restricted pairwise-MCV scope."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from ess_research.arecel.real import SPECS, SUPPORTED_OPERATORS, sha256_file


def classify(path: Path, dataset: str) -> dict[str, Any]:
    spec = SPECS[dataset]
    records: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            record = json.loads(line)
            if not isinstance(record, dict):
                raise TypeError(f"line {line_number} is not an object")
            records.append(record)
    ids = [record.get("query_id") for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate query IDs")
    counts = {
        "total": len(records),
        "train": sum(record.get("split") == "train" for record in records),
        "valid": sum(record.get("split") == "valid" for record in records),
        "test": sum(record.get("split") == "test" for record in records),
        "single_table_conjunctive": 0,
        "supported_predicate_syntax": 0,
        "at_least_two_predicate_attributes": 0,
        "eligible_for_restricted_pairwise_mcv": 0,
    }
    predicate_histogram: dict[str, int] = {}
    eligible_ids: list[str] = []
    for record in records:
        source_query = record.get("source_query")
        predicates = (
            source_query.get("predicates") if isinstance(source_query, dict) else None
        )
        single_table = (
            isinstance(source_query, dict)
            and source_query.get("format") == "arecel-source-query-v1"
            and source_query.get("table") == spec.slug
            and isinstance(predicates, list)
        )
        if single_table:
            counts["single_table_conjunctive"] += 1
        valid_syntax = single_table and bool(predicates)
        columns: set[str] = set()
        if valid_syntax:
            for predicate in predicates:
                if not isinstance(predicate, dict):
                    valid_syntax = False
                    break
                column = predicate.get("column")
                operator = predicate.get("operator")
                if (
                    column not in spec.source_columns
                    or operator not in SUPPORTED_OPERATORS
                ):
                    valid_syntax = False
                    break
                columns.add(column)
        if valid_syntax:
            counts["supported_predicate_syntax"] += 1
        predicate_count = len(predicates) if isinstance(predicates, list) else 0
        predicate_histogram[str(predicate_count)] = (
            predicate_histogram.get(str(predicate_count), 0) + 1
        )
        if valid_syntax and len(columns) >= 2:
            counts["at_least_two_predicate_attributes"] += 1
            counts["eligible_for_restricted_pairwise_mcv"] += 1
            eligible_ids.append(record["query_id"])
        label = record.get("source_label")
        truth = label.get("cardinality") if isinstance(label, dict) else None
        weight = record.get("weight")
        if not isinstance(truth, int) or isinstance(truth, bool) or truth < 0:
            raise ValueError(f"invalid truth for {record.get('query_id')}")
        if (
            not isinstance(weight, (int, float))
            or isinstance(weight, bool)
            or not math.isfinite(float(weight))
            or float(weight) <= 0
        ):
            raise ValueError(f"invalid weight for {record.get('query_id')}")
    return {
        "format": "arecel-real-pairwise-scope-diagnostic-v1",
        "benchmark_id": spec.benchmark_id,
        "classification_is": "read-only syntactic screen, not PostgreSQL statistic-selection evidence",
        "input": {"path": "<explicit-canonical-path>", "sha256": sha256_file(path)},
        "counts": counts,
        "predicate_count_histogram": predicate_histogram,
        "eligible_query_ids_sha256": hashlib.sha256(
            "\n".join(eligible_ids).encode("utf-8")
        ).hexdigest(),
        "criteria": {
            "single_table": f"source_query.table == {spec.slug}",
            "conjunctive": "source_query.predicates is a list; no OR/join representation is accepted",
            "operators": sorted(SUPPORTED_OPERATORS),
            "pairwise_requirement": "at least two distinct constrained source attributes",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(SPECS), required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    result = classify(args.canonical, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{args.output.name}.", dir=args.output.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
