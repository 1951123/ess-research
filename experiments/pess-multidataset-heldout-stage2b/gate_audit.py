#!/usr/bin/env python3
"""Read-only Gate A audit for Issue #48.

The audit verifies only explicit, hash-pinned inputs and local provenance.  It
does not deserialize pickles, create a database, run PostgreSQL, select a test
cohort, or inspect held-out outcomes.  Missing runtime/build prerequisites are
reported as BLOCKED rather than replaced.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


EXPECTED_COMMIT = "23c7c2fdd4bfb561f3257d947fee956a2999fdb6"
EXPECTED_ARCHIVE_SHA256 = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
DATASETS = ("forest10", "census13", "dmv11", "power7")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_paths(root: Path, dataset: str) -> dict[str, Path]:
    data = root / "arecel" / "raw" / "data" / dataset
    return {
        "archive": root / "arecel" / "incoming" / "arecel-data.tar.gz",
        "csv": data / "original.csv",
        "workload_pickle": data / "workload" / "base.pkl",
        "label_pickle": data / "workload" / "base-original-label.pkl",
        "canonical": root / "arecel" / "audit-v1" / f"{dataset}.canonical.jsonl.gz",
    }


def audit_csv(path: Path, expected_header: list[str], expected_rows: int) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = 0
    header: list[str] | None = None
    with path.open("rb") as raw:
        for block in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(block)
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        for rows, row in enumerate(reader, start=1):
            if len(row) != len(expected_header):
                raise ValueError(f"row {rows} has {len(row)} fields, expected {len(expected_header)}")
    return {
        "sha256": digest.hexdigest(),
        "rows": rows,
        "header": header,
        "expected_header": expected_header,
        "header_match": header == expected_header,
        "row_count_match": rows == expected_rows,
    }


def audit_canonical(path: Path, dataset: str, expected_table: str, expected_counts: dict[str, int]) -> dict[str, Any]:
    digest = hashlib.sha256()
    records = 0
    split_counts: dict[str, int] = {}
    query_ids: set[str] = set()
    source_hashes = 0
    valid_truths = 0
    with path.open("rb") as raw:
        for block in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(block)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"canonical line {line_number} is not an object")
            split = record.get("split")
            query_id = record.get("query_id")
            source_sql = record.get("sql")
            source_query = record.get("source_query")
            label = record.get("source_label")
            if split not in expected_counts or not isinstance(query_id, str) or query_id in query_ids:
                raise ValueError(f"invalid or duplicate identity at canonical line {line_number}")
            if not isinstance(source_sql, str) or not isinstance(source_query, dict) or not isinstance(label, dict):
                raise ValueError(f"invalid query/truth record at canonical line {line_number}")
            if source_query.get("format") != "arecel-source-query-v1" or source_query.get("table") != expected_table:
                raise ValueError(f"source-query contract mismatch at canonical line {line_number}")
            if not query_id.startswith(f"arecel:{dataset}:{split}:"):
                raise ValueError(f"query ID contract mismatch at canonical line {line_number}")
            truth = label.get("cardinality")
            if not isinstance(truth, int) or isinstance(truth, bool) or truth < 0:
                raise ValueError(f"invalid nonnegative truth at canonical line {line_number}")
            if record.get("source_query_sha256") != hashlib.sha256(source_sql.encode()).hexdigest():
                raise ValueError(f"source SQL hash mismatch at canonical line {line_number}")
            query_ids.add(query_id)
            records += 1
            split_counts[split] = split_counts.get(split, 0) + 1
            source_hashes += 1
            valid_truths += 1
    return {
        "sha256": digest.hexdigest(),
        "records": records,
        "split_counts": split_counts,
        "expected_split_counts": expected_counts,
        "split_counts_match": split_counts == expected_counts,
        "unique_query_ids": len(query_ids) == records,
        "source_query_hashes_checked": source_hashes,
        "nonnegative_truths_checked": valid_truths,
        "dataset": dataset,
    }


def audit_dataset(protocol: dict[str, Any], root: Path, dataset: str) -> dict[str, Any]:
    provenance = protocol["source_provenance"][dataset]
    spec = protocol["datasets"][dataset]
    paths = expected_paths(root, dataset)
    result: dict[str, Any] = {
        "dataset": dataset,
        "status": "INPUT_AVAILABLE",
        "paths": {name: str(path) for name, path in paths.items()},
        "checks": {},
        "errors": [],
    }
    try:
        expected_header = spec["source_columns"]
        expected_rows = provenance["csv_rows"]
        expected_splits = {"valid": 10000, "test": 10000} if dataset == "forest10" else {"train": 100000, "valid": 10000, "test": 10000}
        expected_hashes = {
            "csv": provenance["csv_sha256"],
            "workload_pickle": provenance["workload_pickle_sha256"],
            "label_pickle": provenance["label_pickle_sha256"],
            "canonical": provenance["derived_canonical_sha256"],
        }
        for name, path in paths.items():
            if not path.is_file():
                raise FileNotFoundError(f"missing {name}: {path}")
        result["checks"]["archive_sha256"] = sha256_file(paths["archive"])
        result["checks"]["csv"] = audit_csv(paths["csv"], expected_header, expected_rows)
        result["checks"]["canonical"] = audit_canonical(paths["canonical"], dataset, spec["source_query_table"], expected_splits)
        result["checks"]["artifact_sha256"] = {
            name: sha256_file(paths[name]) for name in ("csv", "workload_pickle", "label_pickle", "canonical")
        }
        result["checks"]["archive_expected_sha256"] = EXPECTED_ARCHIVE_SHA256
        result["checks"]["archive_hash_match"] = result["checks"]["archive_sha256"] == EXPECTED_ARCHIVE_SHA256
        result["checks"]["expected_sha256"] = expected_hashes
        result["checks"]["hashes_match"] = all(
            result["checks"]["artifact_sha256"][name] == expected for name, expected in expected_hashes.items()
        )
        if not result["checks"]["csv"]["header_match"] or not result["checks"]["csv"]["row_count_match"]:
            raise ValueError("CSV schema or row count mismatch")
        if not result["checks"]["canonical"]["split_counts_match"] or not result["checks"]["canonical"]["unique_query_ids"]:
            raise ValueError("canonical split or identity mismatch")
        if not result["checks"]["hashes_match"] or not result["checks"]["archive_hash_match"]:
            raise ValueError("one or more pinned artifact hashes mismatch")
    except FileNotFoundError as exc:
        result["status"] = "MISSING"
        result["errors"].append(str(exc))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["status"] = "INCOMPATIBLE"
        result["errors"].append(str(exc))
    return result


def audit_pg_source(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "BLOCKED", "reason": "--pg-source was not supplied"}
    try:
        head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        trace_files = {
            "src/backend/statistics/extended_stats.c": ("ESS_MCV_TRACE", "ESS_MCV_NUMERIC_TRACE"),
            "src/backend/optimizer/path/costsize.c": ("ESS_MCV_NUMERIC_TRACE",),
        }
        markers = {
            relative: {
                marker: marker in (path / relative).read_text(encoding="utf-8", errors="replace")
                for marker in required
            }
            for relative, required in trace_files.items()
        }
        status = "SOURCE_MARKERS_PRESENT" if head == EXPECTED_COMMIT and all(all(item.values()) for item in markers.values()) else "INCOMPATIBLE"
        return {"status": status, "head": head, "expected_head": EXPECTED_COMMIT, "trace_markers": markers}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"status": "INCOMPATIBLE", "reason": str(exc)}


def runtime_validation(
    pg_bin: Path | None, sample_manifest: Path | None, runtime_manifest: Path | None, runtime_root: Path | None
) -> dict[str, Any]:
    """Return conservative readiness states until a complete runtime validator exists."""

    root_status = "PRESENT" if runtime_root is not None and runtime_root.is_dir() else "MISSING"
    not_implemented = "complete PG binary/sample/cluster/trace validator is not implemented in this audit"
    return {
        "validator_status": "NOT_IMPLEMENTED_BLOCKED",
        "runtime_root_presence": {"status": root_status, "path": str(runtime_root) if runtime_root else None},
        "pg_binary_pinned": {
            "status": "BLOCKED",
            "path": str(pg_bin) if pg_bin else None,
            "reason": not_implemented,
        },
        "fixed_sample_manifest_verified": {
            "status": "BLOCKED",
            "path": str(sample_manifest) if sample_manifest else None,
            "reason": not_implemented,
        },
        "issue_cluster_ready": {
            "status": "BLOCKED",
            "path": str(runtime_manifest) if runtime_manifest else None,
            "reason": not_implemented,
        },
        "trace_contract_verified": {"status": "BLOCKED", "reason": not_implemented},
    }


def compute_overall_status(datasets: list[dict[str, Any]], pg_source: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Never report PASS without an independently implemented runtime validator."""

    runtime_checks = ("pg_binary_pinned", "fixed_sample_manifest_verified", "issue_cluster_ready", "trace_contract_verified")
    if runtime.get("validator_status") != "IMPLEMENTED":
        return "BLOCKED"
    if sum(item.get("status") == "INPUT_AVAILABLE" for item in datasets) < 2:
        return "BLOCKED"
    if pg_source.get("status") != "SOURCE_MARKERS_PRESENT":
        return "BLOCKED"
    if any(runtime.get(key, {}).get("status") != "VERIFIED" for key in runtime_checks):
        return "BLOCKED"
    return "PASS"


def write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    """Create a JSON evidence file once, refusing files and symlinks atomically."""

    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(path, flags, 0o644)
        created = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--pg-source", type=Path, default=None)
    parser.add_argument("--pg-bin", type=Path, default=None)
    parser.add_argument("--sample-manifest", type=Path, default=None)
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.add_argument("--runtime-manifest", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root_value = args.data_root or (Path(os.environ["ESS_DATA_ROOT"]) if os.environ.get("ESS_DATA_ROOT") else None)
    if root_value is None:
        raise SystemExit("provide --data-root or ESS_DATA_ROOT")
    root = root_value.expanduser().resolve()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    datasets = [audit_dataset(protocol, root, dataset) for dataset in DATASETS]
    pg_source = audit_pg_source(args.pg_source.expanduser().resolve() if args.pg_source else None)
    runtime = runtime_validation(
        args.pg_bin.expanduser().resolve() if args.pg_bin else None,
        args.sample_manifest.expanduser().resolve() if args.sample_manifest else None,
        args.runtime_manifest.expanduser().resolve() if args.runtime_manifest else None,
        args.runtime_root.expanduser().resolve() if args.runtime_root else None,
    )
    result = {
        "format": "ess-issue48-stage2b-gate-a-audit-v2",
        "evidence_label": "experimentally_observed_input_availability_only",
        "protocol_sha256": sha256_file(args.protocol),
        "data_root": str(root),
        "datasets": datasets,
        "postgresql_source": pg_source,
        "runtime_validation": runtime,
        "overall_status": compute_overall_status(datasets, pg_source, runtime),
        "limitations": ["This audit does not create a PG cluster, verify a fixed sample, select a cohort, or collect outcomes.", "It does not establish PostgreSQL statistic selection, MCV payload availability, model adequacy, or any physical guarantee."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_exclusive_json(args.output, result)
    print(json.dumps({"output": str(args.output), "overall_status": result["overall_status"], "dataset_status": {item["dataset"]: item["status"] for item in datasets}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
