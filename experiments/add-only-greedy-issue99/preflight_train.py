"""Outcome-free static sizing for Issue #99's official AreCEL train splits.

Only the pinned workload pickle member is opened. No label pickle or
PostgreSQL process is used. The script reads and iterates only the train list.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import tarfile
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from ess_research.arecel import archive
from ess_research.arecel.forest10 import WORKLOAD_PICKLE_SHA256
from ess_research.arecel.real import SPECS, SUPPORTED_OPERATORS


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def candidate_order_sha256(candidate_ids: list[str]) -> str:
    payload = json.dumps(candidate_ids, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))


def _load_train_workload(dataset: str, data_root: Path) -> tuple[dict[str, Any], str, int]:
    workload_member = f"data/{dataset}/workload/base.pkl"
    csv_member = f"data/{dataset}/original.csv"
    workload_bytes: bytes | None = None
    csv_bytes: int | None = None

    with archive._archive(data_root) as verified:
        with tarfile.open(fileobj=verified, mode="r|gz") as tar:
            for member in tar:
                name = member.name.removeprefix("./")
                if name == csv_member:
                    if csv_bytes is not None or not member.isfile():
                        raise ValueError(f"invalid source CSV member: {csv_member}")
                    csv_bytes = member.size
                elif name == workload_member:
                    if workload_bytes is not None or not member.isfile():
                        raise ValueError(f"invalid workload member: {workload_member}")
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise ValueError(f"unreadable workload member: {workload_member}")
                    with stream:
                        workload_bytes = stream.read()
                    break

    if workload_bytes is None or csv_bytes is None:
        raise ValueError(f"missing source member for {dataset}")
    expected = (
        WORKLOAD_PICKLE_SHA256
        if dataset == "forest10"
        else SPECS[dataset].workload_pickle_sha256
    )
    actual = sha256_bytes(workload_bytes)
    if actual != expected:
        raise ValueError(f"{dataset} workload pickle SHA-256 mismatch")

    source = archive._ArchiveUnpickler(io.BytesIO(workload_bytes)).load()
    if not isinstance(source, dict) or not isinstance(source.get("train"), list):
        raise ValueError(f"pinned archive has no train workload list for {dataset}")
    return source, actual, csv_bytes


def _dataset_summary(dataset: str, data_root: Path) -> dict[str, Any]:
    source, workload_sha256, csv_bytes = _load_train_workload(dataset, data_root)
    queries = source["train"]
    columns, _types, _relation = archive._schema(dataset)
    column_order = {column: index for index, column in enumerate(columns)}
    support: Counter[tuple[str, str]] = Counter()
    rejected_predicates: Counter[str] = Counter()
    eligible_query_count = 0
    max_query_singletons = 0

    for query in queries:
        predicates = getattr(query, "predicates", None)
        if not isinstance(predicates, dict):
            raise ValueError(f"malformed {dataset} train query predicate map")
        eligible_columns: set[str] = set()
        rejected_columns: set[str] = set()
        for column, expression in predicates.items():
            if expression is None:
                continue
            if column not in column_order:
                rejected_predicates["unknown_column"] += 1
                rejected_columns.add(column)
                continue
            if (
                not isinstance(expression, tuple)
                or len(expression) != 2
                or expression[0] not in SUPPORTED_OPERATORS
            ):
                rejected_predicates["unsupported_predicate"] += 1
                rejected_columns.add(column)
                continue
            if expression[0] == "[]" and (
                not isinstance(expression[1], (tuple, list))
                or len(expression[1]) != 2
            ):
                rejected_predicates["malformed_range"] += 1
                rejected_columns.add(column)
                continue
            eligible_columns.add(column)

        eligible_columns.difference_update(rejected_columns)
        ordered = sorted(eligible_columns, key=column_order.__getitem__)
        query_pairs = list(combinations(ordered, 2))
        eligible_query_count += bool(query_pairs)
        max_query_singletons = max(max_query_singletons, len(query_pairs))
        support.update(query_pairs)

    candidate_map = [
        {
            "id": f"e{column_order[left]:02d}_{column_order[right]:02d}",
            "endpoints": [left, right],
        }
        for left, right in combinations(columns, 2)
    ]
    candidate_ids = [candidate["id"] for candidate in candidate_map]
    support_rows = [
        {
            "id": candidate["id"],
            "train_query_count": support[
                tuple(candidate["endpoints"])
            ],
        }
        for candidate in candidate_map
    ]
    candidate_map_bytes = json.dumps(
        candidate_map, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    support_bytes = json.dumps(
        support_rows, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    singleton_count = sum(support.values())
    positive_support = [row["train_query_count"] for row in support_rows if row["train_query_count"]]

    return {
        "dataset": dataset,
        "split": "train",
        "train_query_count": len(queries),
        "schema_columns": list(columns),
        "schema_pair_count": len(candidate_map),
        "train_applicable_pair_count": len(positive_support),
        "zero_train_support_pair_count": len(candidate_map) - len(positive_support),
        "train_queries_with_applicable_pair": eligible_query_count,
        "empty_baseline_observations": len(queries),
        "singleton_observations": singleton_count,
        "total_required_observations": len(queries) + singleton_count,
        "candidate_support_min": min(positive_support) if positive_support else 0,
        "candidate_support_max": max(positive_support) if positive_support else 0,
        "max_singletons_for_one_query": max_query_singletons,
        "rejected_predicate_counts": dict(sorted(rejected_predicates.items())),
        "candidate_order_sha256": candidate_order_sha256(candidate_ids),
        "candidate_map_sha256": sha256_bytes(candidate_map_bytes),
        "train_support_map_sha256": sha256_bytes(support_bytes),
        "workload_pickle_sha256": workload_sha256,
        "source_csv_member_bytes": csv_bytes,
    }


def _source_commit() -> str | None:
    repository = Path(__file__).resolve().parents[2]
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    data_root = Path(os.environ["ESS_DATA_ROOT"]).expanduser().resolve()
    datasets = [_dataset_summary(dataset, data_root) for dataset in archive.DATASETS]
    result = {
        "format": "ess-issue99-train-static-preflight-v1",
        "research_source_commit": _source_commit(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": __import__("numpy").__version__,
        "arecel_upstream_commit": archive.UPSTREAM_COMMIT,
        "arecel_archive_sha256": archive.ARCHIVE_SHA256,
        "label_pickle_member_opened": False,
        "test_label_values_read_or_used": False,
        "test_workload_split_selected_or_iterated": False,
        "postgresql_started": False,
        "datasets": datasets,
        "total_train_queries": sum(row["train_query_count"] for row in datasets),
        "total_required_observations": sum(
            row["total_required_observations"] for row in datasets
        ),
        "total_source_csv_member_bytes": sum(
            row["source_csv_member_bytes"] for row in datasets
        ),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
