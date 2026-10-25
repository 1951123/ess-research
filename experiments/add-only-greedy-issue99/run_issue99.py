"""Bounded, train-only AreCEL observation collection and greedy selection for Issue #99."""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import gzip
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
from itertools import combinations
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE / "protocol-v3.json"
PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
PROTOCOL_SHA256 = hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
PREVIOUS_PROTOCOL_PATH = HERE / "protocol-v2.json"
PREVIOUS_PROTOCOL = json.loads(PREVIOUS_PROTOCOL_PATH.read_text(encoding="utf-8"))
PREVIOUS_PROTOCOL_SHA256 = hashlib.sha256(PREVIOUS_PROTOCOL_PATH.read_bytes()).hexdigest()
SUPPORTED_PROTOCOLS = {PROTOCOL_SHA256: PROTOCOL, PREVIOUS_PROTOCOL_SHA256: PREVIOUS_PROTOCOL}
PARALLEL_COLLECTION_CONTRACT_FIELDS = ("maximum_workers", "selection", "default", "worker_model",
    "sample_contract", "configuration_assignment", "dataset_schedule")
if (any(PROTOCOL[key] != PREVIOUS_PROTOCOL[key]
        for key in ("source_pins", "scientific_scope", "postgresql_measurement", "model_fit",
                    "selection_limits", "collection_environment"))
        or any(PROTOCOL["collection_parallelism"][key] != PREVIOUS_PROTOCOL["collection_parallelism"][key]
               for key in PARALLEL_COLLECTION_CONTRACT_FIELDS)):
    raise RuntimeError("protocol-v3 may change resource limits only; scientific and selection contracts must match v2")
CENSUS_DIR = ROOT / "experiments/pess-multidataset-heldout-stage2b/census13-issue71"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(CENSUS_DIR))

from ess_research.arecel import archive, forest10, real
from ess_research.task_paths import configured_root, runtime_runs
import run_census13_smoke as legacy

STOP = threading.Event()
LOCK = threading.Lock()
BLOCK_ROWS = 2048
PART_BYTES = 8 * 1024 * 1024
LOG_QUANTUM = Decimal("0.000000000000000001")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def jsonl_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as stream:
        stream.write(json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_order_sha256(ids: list[str]) -> str:
    return sha256_bytes(json.dumps(ids, separators=(",", ":"), ensure_ascii=True).encode())


def current_source_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def expected_dataset(dataset: str) -> dict[str, Any]:
    return PROTOCOL["preflight"]["dataset_counts"][dataset]


def source_pin(dataset: str) -> dict[str, str]:
    source = PROTOCOL["source_pins"]
    return {
        "csv_sha256": source["arecel_csv_hashes"][dataset],
        "workload_pickle_sha256": source["train_workload_hashes"][dataset],
        "label_pickle_sha256": source["train_label_hashes"][dataset],
    }


def dataset_spec(dataset: str) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], int, str, str]:
    source_columns, pg_columns, _ = archive._schema(dataset)
    if dataset == "forest10":
        rows, csv_sha = forest10.EXPECTED_ROWS, forest10.CSV_SHA256
    else:
        spec = real.SPECS[dataset]
        rows, csv_sha = spec.expected_rows, spec.csv_sha256
    if csv_sha != source_pin(dataset)["csv_sha256"]:
        raise ValueError(f"{dataset} CSV pin differs from the ETL source contract")
    return tuple(source_columns), tuple(pg_columns), rows, csv_sha, f"public.{dataset}"


def _archive_members(dataset: str, root: Path, *, labels: bool, csv_file: bool) -> tuple[dict[str, Any], Path | None]:
    """Read only the selected dataset's pinned workload, optional labels, and optional CSV."""
    data_root = configured_root("ESS_DATA_ROOT")
    wanted = {
        f"data/{dataset}/workload/base.pkl": "workload",
    }
    if labels:
        wanted[f"data/{dataset}/workload/base-original-label.pkl"] = "labels"
    if csv_file:
        wanted[f"data/{dataset}/original.csv"] = "csv"
    buffers: dict[str, bytes] = {}
    csv_path = root / "input" / f"{dataset}.csv" if csv_file else None
    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    with archive._archive(data_root) as verified:
        with tarfile.open(fileobj=verified, mode="r|gz") as source:
            for member in source:
                name = member.name.removeprefix("./")
                if name not in wanted:
                    continue
                if name in seen or not member.isfile():
                    raise ValueError(f"duplicate or invalid AreCEL archive member: {name}")
                entry = source.extractfile(member)
                if entry is None:
                    raise ValueError(f"unreadable AreCEL archive member: {name}")
                seen.add(name)
                if wanted[name] == "csv":
                    digest = hashlib.sha256()
                    with entry, csv_path.open("xb") as output:
                        while block := entry.read(1024 * 1024):
                            output.write(block)
                            digest.update(block)
                    if digest.hexdigest() != source_pin(dataset)["csv_sha256"]:
                        raise ValueError(f"{dataset} CSV member hash mismatch")
                else:
                    with entry:
                        buffers[wanted[name]] = entry.read()
                if seen == set(wanted):
                    break
    if seen != set(wanted):
        raise ValueError(f"missing AreCEL archive members: {sorted(set(wanted) - seen)}")
    pin = source_pin(dataset)
    if sha256_bytes(buffers["workload"]) != pin["workload_pickle_sha256"]:
        raise ValueError(f"{dataset} workload pickle SHA-256 mismatch")
    if labels and sha256_bytes(buffers["labels"]) != pin["label_pickle_sha256"]:
        raise ValueError(f"{dataset} label pickle SHA-256 mismatch")
    workload = archive._ArchiveUnpickler(io.BytesIO(buffers["workload"])).load()
    if not isinstance(workload, dict) or not isinstance(workload.get("train"), list):
        raise ValueError(f"{dataset} pinned workload has no train list")
    result = {"workload": workload["train"], "workload_sha256": pin["workload_pickle_sha256"]}
    if labels:
        label_source = archive._ArchiveUnpickler(io.BytesIO(buffers["labels"])).load()
        if not isinstance(label_source, dict) or not isinstance(label_source.get("train"), list):
            raise ValueError(f"{dataset} pinned labels have no train list")
        result["labels"] = label_source["train"]
        result["label_sha256"] = pin["label_pickle_sha256"]
        del label_source
    return result, csv_path


def build_train_rows(dataset: str, raw_queries: list[Any]) -> tuple[list[dict[str, Any]], list[int]]:
    expected = expected_dataset(dataset)
    if len(raw_queries) != expected["train_queries"]:
        raise ValueError(f"{dataset} train query count differs from the frozen preflight")
    queries = []
    for index, source_query in enumerate(raw_queries):
        identity = {"query_id": f"arecel:{dataset}:train:{index:06d}", "source_index": index}
        queries.append({**identity, **archive._query(source_query, dataset)})
    return queries, [int(query["source_index"]) for query in queries]


def build_candidate_schedule(dataset: str, queries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, tuple[str, ...]], dict[str, int], dict[str, str]]:
    source_columns, pg_columns, _rows, _csv_sha, table = dataset_spec(dataset)
    expected = expected_dataset(dataset)
    support = {pair: 0 for pair in combinations(source_columns, 2)}
    eligible: dict[str, tuple[str, ...]] = {}
    index = {column: position for position, column in enumerate(source_columns)}
    for query in queries:
        predicate_columns = {predicate["column"] for predicate in query["predicates"]}
        selected_columns = [column for column in source_columns if column in predicate_columns]
        ids = []
        for left, right in combinations(selected_columns, 2):
            support[(left, right)] += 1
            ids.append(f"e{index[left]:02d}_{index[right]:02d}")
        eligible[query["query_id"]] = tuple(ids)
    candidates = []
    candidate_rows = []
    for left_index, left in enumerate(source_columns):
        for right_index in range(left_index + 1, len(source_columns)):
            right = source_columns[right_index]
            candidate_id = f"e{left_index:02d}_{right_index:02d}"
            catalog_left = pg_columns[left_index][0]
            catalog_right = pg_columns[right_index][0]
            candidates.append({
                "id": candidate_id,
                "statistic_name": f"ess_issue99_{dataset}_{candidate_id}",
                "catalog_columns": [catalog_left, catalog_right],
                "endpoints": [left, right],
                "table": table,
                "maintenance_cost": "1",
                "train_query_count": support[(left, right)],
            })
            candidate_rows.append({"id": candidate_id, "endpoints": [left, right]})
    ids = [candidate["id"] for candidate in candidates]
    support_rows = [{"id": row["id"], "train_query_count": candidates[pos]["train_query_count"]}
                    for pos, row in enumerate(candidate_rows)]
    hashes = {
        "candidate_order_sha256": candidate_order_sha256(ids),
        "candidate_map_sha256": sha256_bytes(json.dumps(candidate_rows, ensure_ascii=True, separators=(",", ":")).encode()),
        "train_support_map_sha256": sha256_bytes(json.dumps(support_rows, ensure_ascii=True, separators=(",", ":")).encode()),
    }
    if len(candidates) != expected["full_pairs"] or any(value <= 0 for value in support.values()):
        raise ValueError(f"{dataset} train does not support the complete frozen schema pair universe")
    for key, value in hashes.items():
        if expected[key] != value:
            raise ValueError(f"{dataset} {key} differs from the frozen Phase A result")
    if sum(map(len, eligible.values())) != expected["singleton_observations"]:
        raise ValueError(f"{dataset} train-only eligibility total differs from the frozen preflight")
    return candidates, eligible, {c["id"]: c["train_query_count"] for c in candidates}, hashes


def save_train_truth(root: Path, dataset: str, queries: list[dict[str, Any]], labels: list[Any]) -> dict[str, Any]:
    if len(labels) != len(queries):
        raise ValueError(f"{dataset} train query/label lengths differ")
    target = root / "train" / "train-truth.jsonl.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    zero_count = 0
    with target.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6, mtime=0) as out:
            for query, label in zip(queries, labels, strict=True):
                if not isinstance(label, archive.Label):
                    raise ValueError(f"{dataset} train label has unexpected source type")
                cardinality = archive._scalar(label.cardinality)
                if isinstance(cardinality, bool) or not isinstance(cardinality, int) or cardinality < 0:
                    raise ValueError(f"{dataset} train cardinality is invalid")
                zero_count += cardinality == 0
                row = {"query_id": query["query_id"], "true_cardinality": cardinality}
                line = jsonl_bytes(row)
                digest.update(line)
                out.write(line)
        raw.flush()
        os.fsync(raw.fileno())
    return {"path": str(target.relative_to(root)), "sha256": sha256_file(target),
            "canonical_values_sha256": digest.hexdigest(), "rows": len(queries), "zero_truth_count": zero_count,
            "compressed_bytes": target.stat().st_size}


class ChunkedJsonlWriter:
    """Task-specific durable gzip JSONL parts with checksummed write blocks."""

    def __init__(self, root: Path, manifest_path: Path, worker_id: int) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=False)
        self.manifest_path = manifest_path
        self.manifest: dict[str, Any] = {"format": "ess-issue99-worker-observations-v1", "worker_id": worker_id,
            "parts": [], "durable_blocks": [], "committed_observation_count": 0, "active_part": None}
        self.rows: list[bytes] = []
        self.total_rows = 0
        self.part_index = 1
        self.part_path: Path | None = None
        self.raw = None
        self.part_rows = 0
        self.part_uncompressed_bytes = 0
        self.part_compressed_bytes = 0
        self.part_first_sequence = 0
        self.block_rows = 0
        self.block_uncompressed_bytes = 0
        self._save()

    def _save(self) -> None:
        atomic_json(self.manifest_path, self.manifest)

    def _open_part(self) -> None:
        self.part_path = self.root / f"observations-{self.part_index:04d}.jsonl.gz"
        self.raw = self.part_path.open("xb")
        self.part_rows = self.part_uncompressed_bytes = self.part_compressed_bytes = 0
        self.part_first_sequence = self.total_rows - self.block_rows + 1

    def write(self, row: dict[str, Any]) -> None:
        line = jsonl_bytes(row)
        if len(line) > PART_BYTES:
            raise ValueError("one Issue #99 observation row exceeds the part byte bound")
        if self.raw is None:
            self._open_part()
        self.rows.append(line)
        self.total_rows += 1
        self.block_rows += 1
        self.block_uncompressed_bytes += len(line)
        if self.block_rows >= BLOCK_ROWS or self.block_uncompressed_bytes >= PART_BYTES:
            self.sync()

    def sync(self) -> None:
        if not self.rows:
            return
        payload = b"".join(self.rows)
        member = gzip.compress(payload, compresslevel=6, mtime=0)
        if len(member) > PART_BYTES:
            raise ValueError("one durable gzip block exceeds the part byte bound")
        if self.part_compressed_bytes and self.part_compressed_bytes + len(member) > PART_BYTES:
            self._close_part()
            self._open_part()
        offset = self.part_compressed_bytes
        first = self.total_rows - self.block_rows + 1
        if self.part_rows == 0:
            self.part_first_sequence = first
        self.raw.write(member)
        self.raw.flush()
        os.fsync(self.raw.fileno())
        self.part_compressed_bytes += len(member)
        self.part_rows += self.block_rows
        self.part_uncompressed_bytes += len(payload)
        self.manifest["durable_blocks"].append({"part": self.part_path.name, "first_sequence": first,
            "last_sequence": self.total_rows, "rows": self.block_rows, "byte_offset": offset,
            "compressed_bytes": len(member), "gzip_member_sha256": sha256_bytes(member),
            "uncompressed_sha256": sha256_bytes(payload)})
        self.rows.clear()
        self.block_rows = 0
        self.block_uncompressed_bytes = 0
        self.manifest["committed_observation_count"] = self.total_rows
        self.manifest["active_part"] = {"path": self.part_path.name, "committed_rows": self.part_rows,
            "uncompressed_bytes": self.part_uncompressed_bytes, "committed_compressed_bytes": self.part_compressed_bytes}
        self._save()

    def _finish_part(self) -> None:
        if self.rows:
            self.sync()
        self._close_part()

    def _close_part(self) -> None:
        if self.raw is None:
            return
        self.raw.flush()
        os.fsync(self.raw.fileno())
        self.raw.close()
        self.manifest["parts"].append({"path": str(self.part_path.relative_to(self.root.parent)),
            "rows": self.part_rows, "uncompressed_bytes": self.part_uncompressed_bytes,
            "compressed_bytes": self.part_path.stat().st_size, "sha256": sha256_file(self.part_path),
            "first_sequence": self.part_first_sequence,
            "last_sequence": self.part_first_sequence + self.part_rows - 1})
        self.part_index += 1
        self.raw = self.part_path = None
        self.manifest["active_part"] = None
        self._save()

    def close(self) -> None:
        self._finish_part()


def _schema_sql(dataset: str, columns: tuple[tuple[str, str], ...]) -> str:
    return f"CREATE TABLE public.{dataset} (\n" + ",\n".join(
        f'  "{name}" {type_}' for name, type_ in columns
    ) + "\n);\n"


def _populate_replay_cluster(helpers: Any, prefix: Path, cluster: dict[str, Any], dataset: str,
                             schema_path: Path, csv_path: Path, sample: Path,
                             source_rows: int, columns: tuple[tuple[str, str], ...]) -> int:
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
    table = f"public.{dataset}"
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"], schema_path.read_text(encoding="utf-8"), env)
    escaped_csv = str(csv_path).replace("'", "''")
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
        f"\\copy {table} FROM '{escaped_csv}' WITH (FORMAT csv, HEADER true);", env, timeout=600)
    count = int(helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
        f"SELECT count(*) FROM {table};", env, tuples=True).strip())
    if count != source_rows:
        raise RuntimeError(f"{dataset} replay cluster imported {count}, expected {source_rows} rows")
    for name, _type in columns:
        helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
            f'ALTER TABLE {table} ALTER COLUMN "{name}" SET STATISTICS 300;', env)
    relation_oid = int(helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
        f"SELECT '{table}'::regclass::oid;", env, tuples=True).strip())
    header = helpers.sample_header(sample)
    if header.get("server_version") != "16.14" or header.get("natts") != len(columns):
        raise RuntimeError("fixed sample version or attribute count does not match the replay table")
    if header.get("relation_oid") != relation_oid or header.get("relation_identity") != f"6:public{len(dataset)}:{dataset}":
        raise RuntimeError("fixed sample relation identity differs from the replay table")
    escaped_sample = str(sample).replace("'", "''")
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
        f"SET ess.analyze_sample_import='{escaped_sample}'; ANALYZE {table}; RESET ess.analyze_sample_import;", env, timeout=600)
    return relation_oid


def _worker_collect(worker_id: int, cluster: dict[str, Any], relation_oid: int,
                    configs: list[tuple[str, tuple[str, ...]]], queries: list[dict[str, Any]],
                    query_by_id: dict[str, dict[str, Any]], eligible: dict[str, tuple[str, ...]],
                    candidates: list[dict[str, Any]], sample: Path, prefix: Path, helpers: Any,
                    run_formal: Any, forest_adapter: Any, output_dir: Path, manifest_path: Path,
                    failure_rows: list[dict[str, Any]]) -> dict[str, Any]:
    writer = ChunkedJsonlWriter(output_dir, manifest_path, worker_id)
    by_id = {candidate["id"]: candidate for candidate in candidates}
    name_to_id = {candidate["statistic_name"]: candidate["id"] for candidate in candidates}
    expected_calls = sum(len(queries) if config_id == "Empty" else by_id[config_id]["train_query_count"]
                         for config_id, _selected in configs)
    calls = successes = attempted = mcv_events = 0
    mcv_states: dict[str, int] = {}
    started = time.monotonic()
    try:
        for config_id, selected in configs:
            if STOP.is_set():
                break
            ledger = run_formal.configure_statistics(prefix, cluster, cluster["dataset"], by_id, selected, sample)
            adapter_instance = forest_adapter.PR7StructuredExplainAdapter(
                helpers, prefix, cluster, relation_oid, ledger, name_to_id
            )
            query_ids = (list(query_by_id) if config_id == "Empty" else
                         [query["query_id"] for query in queries if config_id in eligible[query["query_id"]]])
            for query_id in query_ids:
                if STOP.is_set():
                    break
                attempted += 1
                try:
                    parsed = adapter_instance.explain(query_by_id[query_id])
                    if parsed["diagnostics_status"] != "complete":
                        raise RuntimeError("structured diagnostics are not complete")
                    row = {"query_id": query_id, "source_index": query_by_id[query_id]["source_index"],
                        "configuration_id": config_id, "worker_id": worker_id, "status": "SUCCESS",
                        "diagnostics_status": parsed["diagnostics_status"],
                        "mcv_diagnostics_status": parsed["mcv_diagnostics_status"],
                        "nrows_preclamp": parsed["estimate_preclamp"], "relation_oid": parsed["relation_oid"],
                        "mcv_events": parsed["mcv_records"]}
                    writer.write(row)
                    calls += 1
                    successes += 1
                    mcv_events += len(parsed["mcv_records"])
                    state = parsed["mcv_diagnostics_status"]
                    mcv_states[state] = mcv_states.get(state, 0) + 1
                    if calls % 10000 == 0:
                        elapsed = time.monotonic() - started
                        print(json.dumps({"event": "train_collection_progress", "worker": worker_id,
                            "calls": calls, "worker_expected_calls": expected_calls,
                            "dataset_elapsed_seconds": round(elapsed, 1),
                            "worker_calls_per_second": round(calls / elapsed, 3)}, separators=(",", ":")), flush=True)
                except BaseException as exc:
                    record = {"query_id": query_id, "source_index": query_by_id[query_id]["source_index"],
                        "configuration_id": config_id, "worker_id": worker_id, "status": "ERROR",
                        "error_class": type(exc).__name__, "error": str(exc)[:400]}
                    writer.write(record)
                    with LOCK:
                        failure_rows.append(record)
                    STOP.set()
                    raise
    finally:
        writer.manifest.update({"expected_calls": expected_calls, "attempted_calls": attempted,
            "successful_calls": successes, "mcv_event_count": mcv_events,
            "mcv_diagnostics_counts": mcv_states})
        writer.close()
    state = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"worker_id": worker_id, "expected_calls": expected_calls, "attempted_calls": attempted,
        "successful_calls": successes, "mcv_event_count": mcv_events, "mcv_diagnostics_counts": mcv_states,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "observation_manifest": str(manifest_path.relative_to(output_dir.parent.parent)),
        "observation_manifest_sha256": sha256_file(manifest_path), "parts": len(state["parts"])}


def _balance_configurations(candidates: list[dict[str, Any]], baseline_calls: int,
                            worker_count: int) -> tuple[list[list[tuple[str, tuple[str, ...]]]], list[int]]:
    if worker_count < 1:
        raise ValueError("worker count must be positive")
    assignments: list[list[tuple[str, tuple[str, ...]]]] = [[("Empty", ())]] + [
        [] for _ in range(worker_count - 1)]
    loads = [baseline_calls] + [0] * (worker_count - 1)
    for candidate in sorted(candidates, key=lambda item: (-item["train_query_count"], item["id"])):
        worker = min(range(worker_count), key=lambda idx: (loads[idx], idx))
        assignments[worker].append((candidate["id"], (candidate["id"],)))
        loads[worker] += candidate["train_query_count"]
    for worker_configs in assignments:
        worker_configs[1:] = sorted(worker_configs[1:], key=lambda item: item[0])
    all_config_ids = [config_id for worker_configs in assignments
        for config_id, _selected in worker_configs]
    candidate_ids = [candidate["id"] for candidate in candidates]
    if (all_config_ids.count("Empty") != 1
            or len(all_config_ids) != len(set(all_config_ids))
            or set(all_config_ids) != {"Empty", *candidate_ids}
            or sum(loads) != baseline_calls + sum(c["train_query_count"] for c in candidates)):
        raise RuntimeError("worker schedule must contain one baseline and each singleton exactly once")
    return assignments, loads


def _signal_stop(_signum: int, _frame: Any) -> None:
    STOP.set()
    raise KeyboardInterrupt("received SIGINT; stopping Issue #99 collection")


def _worker_accounting(output_root: Path, worker_count: int) -> list[dict[str, Any]]:
    summaries = []
    for worker_id in range(worker_count):
        worker_manifest_path = output_root / f"worker{worker_id}-manifest.json"
        if not worker_manifest_path.is_file():
            summaries.append({"worker_id": worker_id, "manifest_missing": True})
            continue
        worker = json.loads(worker_manifest_path.read_text(encoding="utf-8"))
        summaries.append({"worker_id": worker_id,
            "expected_calls": worker.get("expected_calls"),
            "attempted_calls": worker.get("attempted_calls"),
            "successful_calls": worker.get("successful_calls", 0),
            "committed_observation_count": worker.get("committed_observation_count", 0),
            "mcv_event_count": worker.get("mcv_event_count", 0),
            "parts": len(worker.get("parts", []))})
    return summaries


def collect_dataset(dataset: str, run_id: str | None = None,
                    parallelism: int | None = None) -> Path:
    if dataset not in PROTOCOL["scientific_scope"]["datasets"]:
        raise ValueError(f"unknown Issue #99 dataset: {dataset}")
    if platform.python_version() != PROTOCOL["collection_environment"]["python_version"]:
        raise RuntimeError("collector Python version differs from protocol-v3")
    numpy_version = importlib.metadata.version("numpy")
    if numpy_version != PROTOCOL["collection_environment"]["numpy_version"]:
        raise RuntimeError("collector NumPy version differs from protocol-v3")
    available_cpus = len(os.sched_getaffinity(0))
    maximum_workers = min(PROTOCOL["collection_parallelism"]["maximum_workers"], available_cpus)
    worker_count = maximum_workers if parallelism is None else parallelism
    if isinstance(worker_count, bool) or not isinstance(worker_count, int) or not 1 <= worker_count <= maximum_workers:
        raise ValueError(f"parallelism must be between 1 and {maximum_workers} CPUs available to this process")
    available_memory_bytes = None
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            available_memory_bytes = int(line.split()[1]) * 1024
            break
    STOP.clear()
    runs = runtime_runs("ess-research", 99)
    runs.mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-issue99-{dataset}-{uuid4().hex[:6]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be a single safe path component")
    root = runs / run_id
    root.mkdir(parents=True, exist_ok=False)
    previous_handler = signal.signal(signal.SIGINT, _signal_stop)
    resource_envelope = PROTOCOL["resource_envelope"]
    early_limits = resource_envelope["per_dataset_early_stop_limits"]
    hard_limits = resource_envelope["per_dataset_hard_limits"]
    guard = legacy.AggregateGuard(root,
        early_seconds=early_limits["wall_seconds"], hard_seconds=hard_limits["wall_seconds"],
        early_bytes=early_limits["allocated_disk_bytes"], hard_bytes=hard_limits["allocated_disk_bytes"])
    resource_limits = {"early_stop_wall_seconds": early_limits["wall_seconds"],
        "early_stop_allocated_disk_bytes": early_limits["allocated_disk_bytes"],
        "hard_wall_seconds": hard_limits["wall_seconds"],
        "hard_allocated_disk_bytes": hard_limits["allocated_disk_bytes"]}
    manifest: dict[str, Any] = {"format": "ess-issue99-dataset-collection-v3", "issue": 99,
        "run_id": run_id, "dataset": dataset, "split": "train", "status": "INCOMPLETE",
        "phase": "initialization", "started_at_utc": now_utc(), "source_commit": current_source_commit(),
        "protocol_sha256": PROTOCOL_SHA256, "python": platform.python_version(),
        "numpy": numpy_version,
        "resource_limits": resource_limits,
        "parallelism": worker_count, "available_cpu_affinity_count": available_cpus,
        "available_memory_bytes_at_start": available_memory_bytes,
        "arecel_archive_sha256": PROTOCOL["source_pins"]["arecel_archive_sha256"],
        "label_pickle_standard_deserialization_materializes_container": True,
        "label_split_keys_explicitly_dereferenced": ["train"],
        "nontrain_label_values_indexed_serialized_or_used": False,
        "test_workload_selected_or_iterated": False,
        "test_explain_run": False, "failure": None}
    atomic_json(root / "collection-manifest.json", manifest)
    primary_error: BaseException | None = None
    try:
        with guard:
            manifest["phase"] = "train_archive_and_schedule"
            atomic_json(root / "collection-manifest.json", manifest)
            source_columns, pg_columns, source_rows, csv_sha, table = dataset_spec(dataset)
            loaded, csv_path = _archive_members(dataset, root, labels=True, csv_file=True)
            queries, _source_indices = build_train_rows(dataset, loaded["workload"])
            candidates, eligible, support, hashes = build_candidate_schedule(dataset, queries)
            expected = expected_dataset(dataset)
            truth_identity = save_train_truth(root, dataset, queries, loaded["labels"])
            workload_pickle_sha256 = loaded["workload_sha256"]
            del loaded
            if csv_path is None or sha256_file(csv_path) != csv_sha:
                raise ValueError("extracted AreCEL CSV is missing or hash-mismatched")
            with csv_path.open("r", encoding="utf-8", newline="") as stream:
                csv_rows = sum(1 for _row in csv.reader(stream)) - 1
            if csv_rows != source_rows:
                raise ValueError(f"{dataset} CSV row count {csv_rows} differs from pinned {source_rows}")
            query_by_id = {query["query_id"]: query for query in queries}
            candidate_map_rows = [{"id": c["id"], "endpoints": c["endpoints"]} for c in candidates]
            candidate_map_path = root / "train" / "candidate-map.json"
            candidate_map_path.write_bytes(json.dumps(candidate_map_rows, ensure_ascii=True, separators=(",", ":")).encode() + b"\n")
            support_rows = [{"id": candidate["id"], "train_query_count": support[candidate["id"]]} for candidate in candidates]
            support_path = root / "train" / "candidate-support.json"
            support_path.write_bytes(json.dumps(support_rows, ensure_ascii=True, separators=(",", ":")).encode() + b"\n")
            manifest.update({"train_query_count": len(queries), "schema_columns": list(source_columns),
                "candidate_count": len(candidates), "eligible_train_query_count": sum(bool(v) for v in eligible.values()),
                "expected_observations": expected["total_observations"], "completed_observations": 0,
                "candidate_order_sha256": hashes["candidate_order_sha256"],
                "candidate_map_sha256": hashes["candidate_map_sha256"],
                "train_support_map_sha256": hashes["train_support_map_sha256"],
                "workload_pickle_sha256": workload_pickle_sha256,
                "label_pickle_sha256": source_pin(dataset)["label_pickle_sha256"],
                "train_truth": truth_identity, "source_csv_sha256": csv_sha, "source_csv_rows": csv_rows,
                "candidate_map_path": str(candidate_map_path.relative_to(root)),
                "candidate_support_path": str(support_path.relative_to(root)),
                "static_preflight_hashes": hashes})
            atomic_json(root / "collection-manifest.json", manifest)

            schema_path = root / "input" / "prepared" / "schema.sql"
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_text(_schema_sql(dataset, pg_columns), encoding="utf-8")
            manifest["phase"] = "pinned_postgresql_build"
            atomic_json(root / "collection-manifest.json", manifest)
            prefix, build = legacy.build_pg(root)
            manifest["postgresql_build"] = build
            helpers, run_formal, forest_adapter, helper_hashes = legacy.load_helpers(root)
            manifest["helper_commits"] = {"pr58": legacy.PR58_COMMIT, "pr65": legacy.PR65_COMMIT}
            manifest["helper_sha256"] = helper_hashes
            atomic_json(root / "collection-manifest.json", manifest)

            manifest["phase"] = "parallel_cluster_setup_and_fixed_sample"
            atomic_json(root / "collection-manifest.json", manifest)
            configs, worker_call_loads = _balance_configurations(candidates, len(queries), worker_count)
            scheduled_baselines = sum(config_id == "Empty" for worker_configs in configs
                for config_id, _selected in worker_configs)
            scheduled_singletons = sum(config_id != "Empty" for worker_configs in configs
                for config_id, _selected in worker_configs)
            scheduled_calls = sum(worker_call_loads)
            if (scheduled_baselines != 1 or scheduled_singletons != len(candidates)
                    or scheduled_calls != expected["total_observations"]):
                raise RuntimeError("worker schedule does not match the frozen baseline/singleton call contract")
            manifest["schedule_contract"] = {"empty_baseline_configurations": scheduled_baselines,
                "singleton_configurations": scheduled_singletons,
                "scheduled_observation_calls": scheduled_calls,
                "expected_observation_calls": expected["total_observations"],
                "verified": True}
            clusters_root = root / "clusters"
            with ExitStack() as stack:
                cluster0 = stack.enter_context(legacy.owned_cluster(helpers, prefix, clusters_root / "worker0", os.environ.copy(), guard))
                cluster0["dataset"] = dataset
                sample, sample_identity = run_formal.bootstrap_cluster(prefix, cluster0, schema_path.parent, dataset,
                    {"catalog_columns": [name for name, _type in pg_columns], "source_rows": source_rows}, csv_path)
                if sha256_file(sample) != sample_identity["sha256"]:
                    raise RuntimeError("exported common ANALYZE sample does not match its identity digest")
                header = helpers.sample_header(sample)
                clusters = [cluster0]
                relation_oids = [header["relation_oid"]]
                for worker_id in range(1, worker_count):
                    cluster = stack.enter_context(legacy.owned_cluster(helpers, prefix,
                        clusters_root / f"worker{worker_id}", os.environ.copy(), guard))
                    cluster["dataset"] = dataset
                    relation_oid = _populate_replay_cluster(helpers, prefix, cluster, dataset, schema_path,
                        csv_path, sample, source_rows, pg_columns)
                    if relation_oid != header["relation_oid"]:
                        raise RuntimeError(f"worker{worker_id} relation OID differs from the fixed sample")
                    clusters.append(cluster)
                    relation_oids.append(relation_oid)
                sample_copy = root / "sample" / f"{dataset}.fixed-sample"
                sample_copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(sample, sample_copy)
                manifest["sample"] = {"path": str(sample_copy.relative_to(root)), "sha256": sha256_file(sample_copy),
                    "bytes": sample_copy.stat().st_size, "header": header,
                    "relation_oids_by_worker": relation_oids, "same_sample_replayed": True}
                atomic_json(root / "collection-manifest.json", manifest)

                manifest["phase"] = "train_structured_explain_collection"
                manifest["worker_call_loads_including_baseline"] = worker_call_loads
                atomic_json(root / "collection-manifest.json", manifest)
                output_root = root / "observations"
                output_root.mkdir()
                failure_rows: list[dict[str, Any]] = []
                workers = []
                worker_errors = []
                with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="issue99-pg") as pool:
                    futures = [pool.submit(_worker_collect, worker_id, cluster, relation_oids[worker_id], configs[worker_id],
                        queries, query_by_id, eligible, candidates, sample, prefix, helpers, run_formal, forest_adapter,
                        output_root / f"worker{worker_id}", output_root / f"worker{worker_id}-manifest.json", failure_rows)
                        for worker_id, cluster in enumerate(clusters)]
                for worker_id, future in enumerate(futures):
                    try:
                        workers.append(future.result())
                    except BaseException as exc:
                        worker_errors.append({"worker_id": worker_id, "error_class": type(exc).__name__, "error": str(exc)[:500]})
                worker_accounting = _worker_accounting(output_root, worker_count)
                completed = sum(worker.get("successful_calls", 0) for worker in worker_accounting)
                manifest["workers"] = workers
                manifest["worker_accounting"] = worker_accounting
                manifest["worker_errors"] = worker_errors
                manifest["completed_observations"] = completed
                manifest["failure_rows"] = failure_rows
                atomic_json(root / "collection-manifest.json", manifest)
                for name, digest in build["binary_sha256"].items():
                    if sha256_file(prefix / "bin" / name) != digest:
                        raise RuntimeError(f"shared PostgreSQL installation changed during collection: {name}")
                manifest.update({"postgresql_binary_hashes_unchanged": True,
                    "collection_elapsed_seconds": round(time.monotonic() - guard.started, 3)})
                if STOP.is_set() or failure_rows or worker_errors or completed != expected["total_observations"]:
                    raise RuntimeError(f"train collection incomplete: {completed}/{expected['total_observations']} observations")
                manifest["status"] = "COMPLETE"
                manifest["phase"] = "complete"
                manifest["completed_at_utc"] = now_utc()
                manifest["peak_allocated_disk_bytes"] = guard.peak
                atomic_json(root / "collection-manifest.json", manifest)
            shutil.rmtree(root / "postgresql", ignore_errors=True)
            shutil.rmtree(root / "clusters", ignore_errors=True)
            shutil.rmtree(root / "input", ignore_errors=True)
            manifest["input_csv_and_pg_build_removed_after_shutdown"] = True
            manifest["status"] = "COMPLETE"
            manifest["phase"] = "complete"
            manifest["peak_allocated_disk_bytes"] = guard.peak
            manifest["completed_at_utc"] = now_utc()
            atomic_json(root / "collection-manifest.json", manifest)
        manifest["peak_allocated_disk_bytes"] = guard.peak
        manifest["total_wall_seconds"] = round(time.monotonic() - guard.started, 3)
        atomic_json(root / "collection-manifest.json", manifest)
    except BaseException as exc:
        primary_error = exc
        manifest["status"] = "INCOMPLETE"
        manifest["phase"] = manifest.get("phase", "unknown")
        manifest["failure"] = {"error_class": type(exc).__name__, "error": str(exc)[:1000],
            "resource_guard_stop_reason": guard.stop_reason}
        manifest["completed_at_utc"] = now_utc()
        manifest["peak_allocated_disk_bytes"] = guard.peak
        manifest["total_wall_seconds"] = round(time.monotonic() - guard.started, 3)
        output_root_local = locals().get("output_root")
        if isinstance(output_root_local, Path) and output_root_local.is_dir():
            accounting = _worker_accounting(output_root_local, worker_count)
            manifest["worker_accounting"] = accounting
            manifest["completed_observations"] = sum(
                row.get("successful_calls", 0) for row in accounting)
            manifest["attempted_observations"] = sum(
                row.get("attempted_calls", 0) for row in accounting)
            manifest["failure_rows"] = locals().get("failure_rows", [])
            if guard.stop_reason is None and isinstance(exc, KeyboardInterrupt):
                manifest["stop_origin"] = "received_sigint"
            elif guard.stop_reason is not None:
                manifest["stop_origin"] = "resource_guard"
        cleanup_complete = True
        for disposable in (root / "postgresql", root / "clusters", root / "input"):
            if disposable.exists():
                shutil.rmtree(disposable, ignore_errors=True)
                cleanup_complete = cleanup_complete and not disposable.exists()
        manifest["rebuildable_inputs_and_stopped_clusters_removed_after_failure"] = cleanup_complete
        atomic_json(root / "collection-manifest.json", manifest)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            print(f"Issue #99 collection stopped; incomplete evidence: {root}", file=sys.stderr, flush=True)
        else:
            print(json.dumps(manifest["failure"], sort_keys=True), file=sys.stderr, flush=True)
    finally:
        signal.signal(signal.SIGINT, previous_handler)
    if primary_error is not None and not isinstance(primary_error, KeyboardInterrupt):
        raise primary_error
    return root


ISSUE87_DIR = ROOT / "experiments/add-only-greedy-issue87"
sys.path.insert(0, str(ISSUE87_DIR))
import run_issue87 as issue87_runner


def _load_train_truth(run_root: Path, queries: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, int]:
    path = run_root / manifest["train_truth"]["path"]
    values: dict[str, int] = {}
    digest = hashlib.sha256()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            digest.update(line.encode())
            row = json.loads(line)
            query_id, value = row.get("query_id"), row.get("true_cardinality")
            if query_id != queries[index]["query_id"] or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"invalid or out-of-order train truth row {index}")
            values[query_id] = value
    identity = manifest["train_truth"]
    if len(values) != len(queries) or digest.hexdigest() != identity["canonical_values_sha256"]:
        raise ValueError("train-only truth rows do not match the collection manifest")
    if sha256_file(path) != identity["sha256"]:
        raise ValueError("train-only truth gzip hash does not match the collection manifest")
    return values


def _load_observations(run_root: Path, manifest: dict[str, Any], queries: list[dict[str, Any]],
                       candidates: list[dict[str, Any]], eligible: dict[str, tuple[str, ...]]) -> tuple[dict[str, Decimal], dict[str, dict[str, Decimal]], str]:
    expected_qids = {query["query_id"] for query in queries}
    candidate_ids = {candidate["id"] for candidate in candidates}
    empty: dict[str, Decimal] = {}
    singleton: dict[str, dict[str, Decimal]] = {candidate_id: {} for candidate_id in candidate_ids}
    mcv_status_counts: dict[str, int] = {}
    observation_files = []
    observed_count = 0
    worker_ids = [worker.get("worker_id") for worker in manifest.get("workers", [])]
    parallelism = manifest.get("parallelism")
    if (not isinstance(parallelism, int) or parallelism < 1
            or len(worker_ids) != parallelism or set(worker_ids) != set(range(parallelism))):
        raise ValueError("collection manifest worker IDs do not match its recorded parallelism")
    for worker_id in sorted(worker_ids):
        worker_manifest_path = run_root / "observations" / f"worker{worker_id}-manifest.json"
        worker_manifest = json.loads(worker_manifest_path.read_text(encoding="utf-8"))
        if worker_manifest.get("worker_id") != worker_id:
            raise ValueError(f"worker{worker_id} durable manifest has a mismatched worker ID")
        if worker_manifest.get("committed_observation_count") != sum(part["rows"] for part in worker_manifest["parts"]):
            raise ValueError(f"worker{worker_id} durable count differs from its completed parts")
        for part in worker_manifest["parts"]:
            path = run_root / "observations" / part["path"]
            if not path.is_file() or sha256_file(path) != part["sha256"]:
                raise ValueError(f"observation part hash mismatch: {path.name}")
            observation_files.append({"path": str(path.relative_to(run_root)), "sha256": part["sha256"], "rows": part["rows"]})
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                part_rows = 0
                for line in stream:
                    row = json.loads(line)
                    part_rows += 1
                    observed_count += 1
                    if row.get("status") != "SUCCESS" or row.get("diagnostics_status") != "complete":
                        raise ValueError(f"non-success structured observation in {path.name}")
                    query_id = row.get("query_id")
                    config_id = row.get("configuration_id")
                    if query_id not in expected_qids:
                        raise ValueError(f"observation has a query outside official train: {query_id}")
                    raw = Decimal(str(row.get("nrows_preclamp")))
                    if not raw.is_finite() or raw < 0:
                        raise ValueError(f"invalid nonnegative pre-clamp estimate in {query_id}/{config_id}")
                    if row.get("relation_oid") != manifest["sample"]["header"]["relation_oid"]:
                        raise ValueError("observation relation OID differs from the frozen sample")
                    if config_id == "Empty":
                        if query_id in empty:
                            raise ValueError(f"duplicate train baseline: {query_id}")
                        empty[query_id] = raw
                    else:
                        if config_id not in candidate_ids or config_id not in eligible[query_id]:
                            raise ValueError(f"singleton observation is outside train static eligibility: {query_id}/{config_id}")
                        if query_id in singleton[config_id]:
                            raise ValueError(f"duplicate singleton train observation: {query_id}/{config_id}")
                        singleton[config_id][query_id] = raw
                    state = row.get("mcv_diagnostics_status")
                    mcv_status_counts[state] = mcv_status_counts.get(state, 0) + 1
                if part_rows != part["rows"]:
                    raise ValueError(f"observation part row count mismatch: {path.name}")
    if set(empty) != expected_qids:
        raise ValueError("train baseline observations do not cover exactly the official train tasks")
    support = {candidate["id"]: candidate["train_query_count"] for candidate in candidates}
    if any(len(singleton[candidate_id]) != expected for candidate_id, expected in support.items()):
        raise ValueError("singleton observations do not match complete train-only static eligibility")
    if observed_count != manifest["expected_observations"] or observed_count != manifest["completed_observations"]:
        raise ValueError("raw observation count differs from the completed collection manifest")
    aggregate = sha256_bytes(json.dumps(observation_files, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode())
    manifest["verified_observation_files"] = observation_files
    manifest["observation_mcv_status_counts"] = mcv_status_counts
    manifest["observations_aggregate_sha256"] = aggregate
    return empty, singleton, aggregate


def _load_train_workload_only(dataset: str, scratch: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, tuple[str, ...]]]:
    loaded, _ = _archive_members(dataset, scratch, labels=False, csv_file=False)
    queries, _ = build_train_rows(dataset, loaded["workload"])
    candidates, eligible, _support, _hashes = build_candidate_schedule(dataset, queries)
    return queries, candidates, eligible


def _model_version(dataset: str) -> str:
    return {"forest10": "forest10-positive-preclamp-v1",
        "census13": "census13-clamped-log-v2",
        "dmv11": "dmv11-positive-preclamp-v1",
        "power7": "power7-positive-preclamp-v1"}[dataset]


def _log_ratio(numerator: Decimal | int, denominator: Decimal | int) -> str:
    left, right = Decimal(numerator), Decimal(denominator)
    if not left.is_finite() or not right.is_finite() or left <= 0 or right <= 0:
        raise ValueError("natural-log ratio requires finite positive inputs")
    with localcontext() as context:
        context.prec = 80
        value = (left / right).ln().quantize(LOG_QUANTUM, rounding=ROUND_HALF_EVEN)
    return str(Fraction(str(value)))


def _fit_base_request(dataset: str, run_root: Path, collection: dict[str, Any], queries: list[dict[str, Any]],
                      candidates: list[dict[str, Any]], eligible: dict[str, tuple[str, ...]],
                      truth: dict[str, int], empty: dict[str, Decimal],
                      singleton: dict[str, dict[str, Decimal]], observations_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    model_version = _model_version(dataset)
    clamp = dataset == "census13"
    model_hash = hashlib.sha256()
    tasks = []
    zero_estimates = {"Empty": 0}
    for candidate in candidates:
        zero_estimates[candidate["id"]] = 0
    for index, query in enumerate(queries):
        query_id = query["query_id"]
        n0 = empty[query_id]
        if n0 == 0:
            zero_estimates["Empty"] += 1
        if clamp:
            model_n0 = max(Decimal(1), n0)
            model_truth = max(1, truth[query_id])
        else:
            if n0 <= 0:
                raise ValueError(f"positive-preclamp model has a nonpositive Empty estimate: {query_id}")
            model_n0 = n0
            model_truth = max(1, truth[query_id])
        alpha = _log_ratio(model_n0, model_truth)
        available = eligible[query_id]
        corrections: dict[str, str] = {}
        for candidate_id in available:
            n1 = singleton[candidate_id][query_id]
            if n1 == 0:
                zero_estimates[candidate_id] += 1
            if clamp:
                model_n1 = max(Decimal(1), n1)
            else:
                if n1 <= 0:
                    raise ValueError(f"positive-preclamp model has a nonpositive singleton estimate: {query_id}/{candidate_id}")
                model_n1 = n1
            corrections[candidate_id] = _log_ratio(model_n1, model_n0)
        model_row = {"query_id": query_id, "alpha": alpha, "b": corrections, "available_edges": list(available)}
        model_hash.update((json.dumps(model_row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())
        tasks.append({"id": query_id, "table": f"public.{dataset}", "weight": "1", "alpha": alpha,
            "eligible_candidates": list(available), "corrections": corrections})
        if (index + 1) % 20000 == 0:
            print(json.dumps({"event": "train_model_fit_progress", "dataset": dataset,
                "tasks_fitted": index + 1, "task_count": len(queries)}, separators=(",", ":")), flush=True)
    candidate_payload = [{"id": candidate["id"], "table": candidate["table"],
        "endpoints": candidate["endpoints"], "maintenance_cost": "1"} for candidate in candidates]
    ids = [candidate["id"] for candidate in candidates]
    source_commit = current_source_commit()
    provenance = {
        "model_version": model_version,
        "advisor_source_commit": PROTOCOL["source_pins"]["advisor_source_commit"],
        "research_source_commit": source_commit,
        "postgresql_source_commit": PROTOCOL["source_pins"]["postgresql_source_commit"],
        "issue99_protocol_sha256": PROTOCOL_SHA256,
        "issue99_builder_sha256": sha256_file(Path(__file__).resolve()),
        "issue99_dataset": dataset,
        "arecel_archive_sha256": PROTOCOL["source_pins"]["arecel_archive_sha256"],
        "train_workload_pickle_sha256": collection["workload_pickle_sha256"],
        "train_label_pickle_sha256": collection["label_pickle_sha256"],
        "train_truth_gzip_sha256": collection["train_truth"]["sha256"],
        "train_truth_values_sha256": collection["train_truth"]["canonical_values_sha256"],
        "candidate_order_sha256": collection["candidate_order_sha256"],
        "candidate_map_sha256": collection["candidate_map_sha256"],
        "train_support_map_sha256": collection["train_support_map_sha256"],
        "observation_aggregate_sha256": observations_sha256,
        "sample_sha256": collection["sample"]["sha256"],
        "calibration_id": f"issue99-{dataset}-official-train-v1",
    }
    base = {"schema_version": "1", "objective": "pess", "backend": "master_oracle",
        "input_provenance": provenance,
        "instance": {"budget": "0", "candidates": candidate_payload, "tasks": tasks},
        "_nominal_priority_order": ids}
    result = {"model_version": model_version, "task_count": len(tasks), "candidate_count": len(ids),
        "coefficient_count": sum(len(task["corrections"]) for task in tasks),
        "coefficient_digest_sha256": model_hash.hexdigest(), "zero_raw_preclamp_counts": zero_estimates,
        "transform": "census max(1,x) clamped-log-v2" if clamp else "positive pre-clamp log with T=max(1,N)",
        "logs": "Decimal precision 80, 1e-18 quantization, ROUND_HALF_EVEN, then Fraction",
        "train_truth_zero_count": collection["train_truth"]["zero_truth_count"],
        "source_commit": source_commit}
    return base, result


def _scope_child(case_dir: Path, unit: str, request_path: Path) -> None:
    if os.environ.get(issue87_runner.SCOPE_ENV) != "1":
        raise RuntimeError("Advisor child is outside its configured Issue #99 systemd scope")
    p = issue87_runner.protocol()
    issue87_runner.write_active_scope_enforcement(unit, case_dir / "scope-enforcement.json", p)
    os.execv(sys.executable, [sys.executable, "-m", "pess_ess.cli", str(request_path)])


def _invoke_solver(case_dir: Path, run_id: str, case_id: str, request_path: Path,
                   p: dict[str, Any]) -> dict[str, Any]:
    limits = p["resource_limits"]
    unit = f"ess-issue99-{run_id}-{re.sub(r'[^A-Za-z0-9_.-]', '-', case_id)}-{uuid4().hex[:8]}.scope"
    time_path = case_dir / "resource-usage.txt"
    stdout_path = case_dir / "response.json"
    stderr_path = case_dir / "stderr.txt"
    command = ["systemd-run", "--user", "--scope", "--quiet", f"--unit={unit}",
        "-p", f"MemoryMax={limits['memory_limit_bytes']}", "-p", f"RuntimeMaxSec={limits['outer_hard_wall_seconds']}"]
    command.extend(f"--setenv={key}={value}" for key, value in limits["thread_environment"].items())
    command.append(f"--setenv={issue87_runner.SCOPE_ENV}=1")
    command.extend(["--", "/usr/bin/time", "-v", "-o", str(time_path), sys.executable,
        str(Path(__file__).resolve()), "_solver-scope", "--case-dir", str(case_dir), "--unit", unit,
        "--request", str(request_path)])
    started = time.monotonic()
    launch_error = None
    returncode = None
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, check=False,
                timeout=limits["outer_hard_wall_seconds"] + 30)
            returncode = result.returncode
    except subprocess.TimeoutExpired:
        launch_error = "systemd-run client exceeded the configured outer wait timeout"
        try:
            subprocess.run(["systemctl", "--user", "stop", unit], check=False,
                capture_output=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            launch_error += "; scope-stop request failed"
    except (OSError, subprocess.SubprocessError) as exc:
        launch_error = f"{type(exc).__name__}: {exc}"
    elapsed = time.monotonic() - started
    status = issue87_runner.scope_status(unit)
    proof = None
    proof_path = case_dir / "scope-enforcement.json"
    if proof_path.is_file():
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    invocation = {"unit": unit, "returncode": returncode, "launch_error": launch_error,
        "wall_seconds": elapsed, "time_report": issue87_runner.time_report(time_path),
        "systemd_status": status, "live_scope_enforcement": proof,
        "scope_errors": issue87_runner.scope_errors({"unit": unit, "returncode": returncode,
            "launch_error": launch_error, "wall_seconds": elapsed,
            "time_report": issue87_runner.time_report(time_path), "systemd_status": status,
            "live_scope_enforcement": proof}, p)}
    atomic_json(case_dir / "execution.json", invocation)
    return invocation


def _fraction_is_canonical(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(Fraction(value)) == value
    except (ValueError, ZeroDivisionError):
        return False


def _response_errors(request: dict[str, Any], response: dict[str, Any] | None) -> list[str]:
    errors = []
    if response is None:
        return ["advisor_response_missing_or_invalid"]
    if response.get("schema_version") != "1" or response.get("backend") != "add_only_greedy" or response.get("objective") != request.get("objective"):
        errors.append("advisor_schema_backend_or_objective_mismatch")
    if response.get("status") != "heuristic_completed":
        errors.append("advisor_response_not_heuristic_completed")
    if not isinstance(response.get("termination_reason"), str) or not response.get("termination_reason"):
        errors.append("advisor_termination_reason_missing")
    incumbent = response.get("incumbent")
    greedy = response.get("greedy")
    if not isinstance(incumbent, dict) or incumbent.get("validated_feasible") is not True:
        errors.append("advisor_incumbent_not_validated_feasible")
        incumbent = incumbent if isinstance(incumbent, dict) else {}
    if not isinstance(greedy, dict):
        errors.append("advisor_greedy_record_missing")
        greedy = {}
    selected = incumbent.get("selected")
    candidate_ids = {candidate["id"] for candidate in request["instance"]["candidates"]}
    if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected) or len(selected) != len(set(selected)) or set(selected) - candidate_ids:
        errors.append("selected_ids_missing_duplicated_or_outside_universe")
        selected_set = set()
    else:
        selected_set = set(selected)
    budget = Fraction(request["instance"]["budget"])
    costs = {candidate["id"]: Fraction(candidate["maintenance_cost"]) for candidate in request["instance"]["candidates"]}
    cost = sum((costs[item] for item in selected_set), Fraction(0))
    if cost > budget or incumbent.get("maintenance_cost") != str(cost):
        errors.append("selected_set_cost_or_budget_mismatch")
    if not _fraction_is_canonical(incumbent.get("objective_value")):
        errors.append("objective_value_is_not_a_canonical_fraction")
    evidence = response.get("objective_evidence", {})
    if not isinstance(evidence, dict) or evidence.get("selected_objective_fraction_certified") is not True:
        errors.append("selected_objective_fraction_not_certified")
    optimality = response.get("optimality", {})
    if not isinstance(optimality, dict) or optimality.get("outer_global_optimum_fraction_certified") is not False:
        errors.append("outer_global_optimality_claim_must_remain_false")
    calls = greedy.get("fixed_set_evaluation_calls")
    completed = greedy.get("completed_fixed_set_evaluations")
    attempts = greedy.get("candidate_attempts")
    if not isinstance(calls, int) or isinstance(calls, bool) or not isinstance(completed, int) or isinstance(completed, bool) or calls < 1 or completed != calls:
        errors.append("greedy_evaluation_round_incomplete")
    if not isinstance(attempts, int) or isinstance(attempts, bool):
        errors.append("candidate_attempt_count_missing")
    addition_order = greedy.get("addition_order")
    if not isinstance(addition_order, list) or len(addition_order) != len(set(addition_order)) or set(addition_order) != selected_set:
        errors.append("greedy_addition_order_does_not_match_selected_set")
    caps = request.get("limits", {})
    if isinstance(calls, int) and calls > caps.get("max_evaluations", 0):
        errors.append("fixed_set_evaluation_cap_exceeded")
    oracle = greedy.get("inner_oracle_work", {})
    if not isinstance(oracle, dict):
        oracle = {}
    subset_count = oracle.get("matching_subsets_examined")
    scored_count = oracle.get("maximal_matchings_scored")
    if not isinstance(subset_count, int) or isinstance(subset_count, bool) or subset_count < 0 or not isinstance(scored_count, int) or isinstance(scored_count, bool) or scored_count < 0:
        errors.append("pess_matching_work_counters_missing")
    inner_cap = caps.get("max_inner_matching_subsets")
    if request.get("objective") == "pess" and isinstance(subset_count, int) and isinstance(inner_cap, int) and subset_count > inner_cap:
        errors.append("pess_matching_subset_cap_exceeded")
    wall = response.get("wall_time_seconds")
    if isinstance(wall, bool) or not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall < 0 or wall > caps.get("total_time_seconds", 0):
        errors.append("advisor_time_cap_exceeded_or_missing")
    return errors


def _overlap_counts(candidates: list[dict[str, Any]], selected: list[str],
                    eligible: dict[str, tuple[str, ...]]) -> dict[str, int]:
    endpoints = {candidate["id"]: tuple(candidate["endpoints"]) for candidate in candidates}
    global_pairs = 0
    for left, right in combinations(selected, 2):
        shared = set(endpoints[left]) & set(endpoints[right])
        if shared:
            global_pairs += 1
    endpoint_counts: dict[str, int] = {}
    for edge in selected:
        for endpoint in endpoints[edge]:
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    task_incidence = 0
    tasks_with_overlap = 0
    for task_edges in eligible.values():
        counts: dict[str, int] = {}
        selected_edges = [edge for edge in task_edges if edge in selected]
        for edge in selected_edges:
            for endpoint in endpoints[edge]:
                counts[endpoint] = counts.get(endpoint, 0) + 1
        conflicts = sum(count >= 2 for count in counts.values())
        task_incidence += conflicts
        tasks_with_overlap += conflicts > 0
    return {"global_overlapping_endpoint_count": sum(count >= 2 for count in endpoint_counts.values()),
        "global_overlapping_resource_pair_count": global_pairs,
        "task_applicable_overlap_incidence_count": task_incidence,
        "tasks_with_task_applicable_overlap": tasks_with_overlap}


def _write_request(path: Path, request: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(request, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return sha256_file(path)


def _case_record(case_id: str, dataset: str, budget: int, objective: str,
                 request: dict[str, Any] | None, request_sha256: str | None,
                 response: dict[str, Any] | None, response_sha256: str | None,
                 invocation: dict[str, Any] | None, case_errors: list[str],
                 collection: dict[str, Any], candidates: list[dict[str, Any]],
                 eligible: dict[str, tuple[str, ...]], source_commit: str,
                 shared_b0_source: str | None = None) -> dict[str, Any]:
    incumbent = response.get("incumbent", {}) if isinstance(response, dict) else {}
    greedy = response.get("greedy", {}) if isinstance(response, dict) else {}
    incumbent = incumbent if isinstance(incumbent, dict) else {}
    greedy = greedy if isinstance(greedy, dict) else {}
    complete = not case_errors and isinstance(response, dict) and response.get("status") == "heuristic_completed"
    selected = incumbent.get("selected") if complete else None
    addition = greedy.get("addition_order") if complete else None
    steps = greedy.get("steps", []) if isinstance(greedy.get("steps"), list) else []
    trace = [{"candidate_id": step.get("candidate_id"), "objective_before_fraction": step.get("objective_before"),
        "objective_after_fraction": step.get("objective_after"), "improvement_fraction": step.get("improvement")}
        for step in steps if isinstance(step, dict) and {"candidate_id", "objective_before", "objective_after", "improvement"} <= set(step)]
    limits = request.get("limits", {}) if request else {}
    p = issue87_runner.protocol()
    resource_limits = {"advisor_total_time_seconds": limits.get("total_time_seconds"),
        "outer_hard_wall_seconds": p["resource_limits"]["outer_hard_wall_seconds"],
        "memory_limit_bytes": p["resource_limits"]["memory_limit_bytes"],
        "processes": 1, "cpu_threads": 1, "max_evaluations": limits.get("max_evaluations"),
        "max_inner_matching_subsets": limits.get("max_inner_matching_subsets"),
        "thread_environment": p["resource_limits"]["thread_environment"],
        "effective_systemd": (invocation or {}).get("systemd_status", {}).get("properties", {})}
    ids = [candidate["id"] for candidate in candidates]
    input_hashes = {"arecel_archive_sha256": PROTOCOL["source_pins"]["arecel_archive_sha256"],
        "train_workload_pickle_sha256": collection["workload_pickle_sha256"],
        "train_label_pickle_sha256": collection["label_pickle_sha256"],
        "train_truth_sha256": collection["train_truth"]["canonical_values_sha256"],
        "candidate_order_sha256": collection["candidate_order_sha256"],
        "candidate_map_sha256": collection["candidate_map_sha256"],
        "train_support_map_sha256": collection["train_support_map_sha256"],
        "sample_sha256": collection["sample"]["sha256"],
        "observations_aggregate_sha256": collection.get("observations_aggregate_sha256")}
    if selected is not None:
        overlap = _overlap_counts(candidates, selected, eligible)
    else:
        overlap = None
    work = issue87_runner.work_counters(response)
    return {"schema_version": "ess-issue99-greedy-case-v1", "case_id": case_id, "dataset": dataset,
        "split": "train", "model_version": _model_version(dataset), "objective": objective,
        "backend": "add_only_greedy", "budget": budget, "task_count": collection["train_query_count"],
        "candidate_count": len(candidates), "candidate_order_sha256": candidate_order_sha256(ids),
        "nominal_priority_order_sha256": candidate_order_sha256(ids) if objective == "nominal" else None,
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "termination_reason": response.get("termination_reason") if complete else ";".join(case_errors) or "incomplete_response",
        "selected_ids": sorted(selected) if selected is not None else None,
        "last_completed_prefix": None if complete else (greedy.get("addition_order") or incumbent.get("selected")),
        "addition_order": addition, "objective_fraction": incumbent.get("objective_value") if complete else None,
        "objective_trace": trace if complete else [], "budget_used": incumbent.get("maintenance_cost"),
        "budget_unused": incumbent.get("unused_budget"), "outer_global_optimum_claim": False,
        "resource_overlap": overlap, "wall_seconds": (invocation or {}).get("time_report", {}).get("wall_seconds", (invocation or {}).get("wall_seconds", 0.0)),
        "peak_rss_bytes": (invocation or {}).get("time_report", {}).get("peak_rss_bytes"),
        "resource_limits": resource_limits, "work_counters": work, "input_hashes": input_hashes,
        "advisor_source_commit": PROTOCOL["source_pins"]["advisor_source_commit"],
        "research_source_commit": source_commit, "request_sha256": request_sha256,
        "response_sha256": response_sha256, "shared_b0_computation_from": shared_b0_source,
        "case_failure_reasons": case_errors}


def run_selection(dataset: str, collection_path: Path) -> Path:
    collection_path = collection_path.expanduser()
    if collection_path.is_symlink():
        raise ValueError("collection path must not be a symlink")
    supplied_parent = collection_path.parent.resolve(strict=True)
    collection_path = collection_path.resolve(strict=True)
    expected_runs = runtime_runs("ess-research", 99).resolve(strict=True)
    if supplied_parent != expected_runs or not collection_path.is_dir() or collection_path.parent != expected_runs:
        raise ValueError("collection path must be a direct, non-symlink Issue #99 runtime run")
    collection = json.loads((collection_path / "collection-manifest.json").read_text(encoding="utf-8"))
    if collection.get("dataset") != dataset or collection.get("status") != "COMPLETE" or collection.get("split") != "train":
        raise ValueError("selection requires the complete official train collection for this dataset")
    if collection.get("protocol_sha256") not in SUPPORTED_PROTOCOLS:
        raise ValueError("collection protocol hash is not a supported Issue #99 protocol revision")
    queries, candidates, eligible = _load_train_workload_only(dataset, collection_path / "scratch")
    if len(queries) != collection["train_query_count"]:
        raise ValueError("reloaded train workload count differs from collection manifest")
    if sha256_file(collection_path / collection["sample"]["path"]) != collection["sample"]["sha256"]:
        raise ValueError("fixed sample bytes differ from the collection manifest")
    truth = _load_train_truth(collection_path, queries, collection)
    empty, singleton, observations_sha = _load_observations(collection_path, collection, queries, candidates, eligible)
    base_request, model = _fit_base_request(dataset, collection_path, collection, queries, candidates,
        eligible, truth, empty, singleton, observations_sha)
    collection.update({"observations_aggregate_sha256": observations_sha,
        "model_fit": model, "model_status": "COMPLETE"})

    p = issue87_runner.protocol()
    software = issue87_runner.verify_advisor_install(p)
    environment = issue87_runner.verify_run_environment(p)
    root_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-issue99-{dataset}-selection-{uuid4().hex[:6]}"
    selection_root = expected_runs / root_id
    selection_root.mkdir(parents=True, exist_ok=False)
    source_commit = current_source_commit()
    selection_manifest = {"format": "ess-issue99-train-selection-v3", "issue": 99,
        "run_id": root_id, "dataset": dataset, "split": "train", "status": "INCOMPLETE",
        "started_at_utc": now_utc(), "collection_run_id": collection_path.name,
        "collection_manifest_sha256": sha256_file(collection_path / "collection-manifest.json"),
        "protocol_sha256": PROTOCOL_SHA256, "source_commit": source_commit,
        "advisor_environment": software, "host_environment": environment,
        "case_count_expected": 10, "case_count_complete": 0, "case_count_incomplete": 0,
        "model_fit": model, "nontrain_labels_or_test_explain_used": False,
        "observation_aggregate_sha256": observations_sha,
        "cross_objective_evaluation": "not run; optional and outside the bounded predeclared case envelope"}
    atomic_json(selection_root / "selection-manifest.json", selection_manifest)
    case_records = []
    b0_nominal: dict[str, Any] | None = None
    for budget in PROTOCOL["scientific_scope"]["budgets"]:
        for objective in ("nominal", "pess"):
            case_id = f"{dataset}-{objective}-b{budget}"
            if budget == 0 and objective == "pess" and b0_nominal is not None:
                record = dict(b0_nominal)
                record.update({"case_id": case_id, "objective": "pess", "nominal_priority_order_sha256": None,
                    "request_sha256": None, "shared_b0_computation_from": f"{dataset}-nominal-b0",
                    "computation_reused": True,
                    "termination_reason": b0_nominal["termination_reason"]})
                case_records.append(record)
                with (selection_root / "case-results.jsonl").open("ab") as stream:
                    stream.write(jsonl_bytes(record)); stream.flush(); os.fsync(stream.fileno())
                continue
            case_dir = selection_root / "cases" / case_id
            case_dir.mkdir(parents=True)
            request = None
            request_sha = None
            request_path = case_dir / "request.json"
            invocation = None
            response = None
            response_raw = None
            errors: list[str] = []
            try:
                request = issue87_runner.request_for_case(base_request, budget, objective)
                request["input_provenance"].update({"issue99_protocol_sha256": PROTOCOL_SHA256,
                    "issue99_dataset": dataset, "issue99_collection_run_id": collection_path.name,
                    "issue99_observation_aggregate_sha256": observations_sha,
                    "issue99_train_truth_sha256": collection["train_truth"]["canonical_values_sha256"]})
                request_sha = _write_request(request_path, request)
                invocation = _invoke_solver(case_dir, root_id, case_id, request_path, p)
                response_path = case_dir / "response.json"
                if response_path.is_file():
                    response_raw = response_path.read_bytes()
                    try:
                        parsed = json.loads(response_raw)
                        if isinstance(parsed, dict):
                            response = parsed
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        response = None
                errors.extend(invocation["scope_errors"])
                errors.extend(_response_errors(request, response))
            except Exception as exc:
                errors.append(f"case_runner_exception:{type(exc).__name__}:{str(exc)[:300]}")
            record = _case_record(case_id, dataset, budget, objective, request, request_sha,
                response, sha256_bytes(response_raw) if response_raw else None, invocation, errors,
                collection, candidates, eligible, source_commit)
            record["computation_reused"] = False
            case_records.append(record)
            with (selection_root / "case-results.jsonl").open("ab") as stream:
                stream.write(jsonl_bytes(record)); stream.flush(); os.fsync(stream.fileno())
            request_path.unlink(missing_ok=True)
            if budget == 0 and objective == "nominal":
                b0_nominal = record
            del request
            if len(case_records) % 2 == 0:
                selection_manifest["case_count_complete"] = sum(row["status"] == "COMPLETE" for row in case_records)
                selection_manifest["case_count_incomplete"] = sum(row["status"] != "COMPLETE" for row in case_records)
                selection_manifest["cases_recorded"] = len(case_records)
                atomic_json(selection_root / "selection-manifest.json", selection_manifest)
            print(json.dumps({"event": "issue99_case_complete" if record["status"] == "COMPLETE" else "issue99_case_incomplete",
                "case_id": case_id, "termination_reason": record["termination_reason"],
                "wall_seconds": record["wall_seconds"]}, separators=(",", ":")), flush=True)
    selection_manifest["cases_recorded"] = len(case_records)
    selection_manifest["case_count_complete"] = sum(row["status"] == "COMPLETE" for row in case_records)
    selection_manifest["case_count_incomplete"] = sum(row["status"] != "COMPLETE" for row in case_records)
    selection_manifest["status"] = "COMPLETE" if selection_manifest["case_count_incomplete"] == 0 else "PARTIAL"
    selection_manifest["completed_at_utc"] = now_utc()
    atomic_json(selection_root / "selection-manifest.json", selection_manifest)
    return selection_root


def mark_selection_incomplete(dataset: str, collection_path: Path, reason: str) -> Path:
    runs = runtime_runs("ess-research", 99).resolve(strict=True)
    root = runs / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-issue99-{dataset}-selection-incomplete-{uuid4().hex[:6]}"
    root.mkdir(parents=True, exist_ok=False)
    collection_manifest = json.loads((collection_path / "collection-manifest.json").read_text(encoding="utf-8"))
    rows = []
    for budget in PROTOCOL["scientific_scope"]["budgets"]:
        for objective in ("nominal", "pess"):
            case_id = f"{dataset}-{objective}-b{budget}"
            shared = f"{dataset}-nominal-b0" if budget == 0 and objective == "pess" else None
            row = {"schema_version": "ess-issue99-greedy-case-v1", "case_id": case_id,
                "dataset": dataset, "split": "train", "model_version": _model_version(dataset),
                "objective": objective, "backend": "add_only_greedy", "budget": budget,
                "task_count": collection_manifest.get("train_query_count", 100000),
                "candidate_count": collection_manifest.get("candidate_count"), "status": "INCOMPLETE",
                "termination_reason": reason, "selected_ids": None, "last_completed_prefix": None,
                "addition_order": None, "objective_fraction": None, "objective_trace": [],
                "budget_used": None, "budget_unused": None, "outer_global_optimum_claim": False,
                "resource_overlap": None, "request_sha256": None, "response_sha256": None,
                "shared_b0_computation_from": shared, "case_failure_reasons": [reason]}
            rows.append(row)
    with (root / "case-results.jsonl").open("xb") as stream:
        for row in rows:
            stream.write(jsonl_bytes(row))
        stream.flush(); os.fsync(stream.fileno())
    summary = {"format": "ess-issue99-train-selection-v3", "issue": 99, "run_id": root.name,
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset": dataset, "status": "PARTIAL", "collection_run_id": collection_path.name,
        "case_count_expected": 10, "case_count_complete": 0, "case_count_incomplete": 10,
        "cases_recorded": 10, "failure_reason": reason,
        "label_pickle_standard_deserialization_materializes_container": collection_manifest.get(
            "label_pickle_standard_deserialization_materializes_container"),
        "nontrain_label_values_indexed_serialized_or_used": collection_manifest.get(
            "nontrain_label_values_indexed_serialized_or_used"),
        "official_test_labels_or_explain_used": False,
        "completed_at_utc": now_utc()}
    atomic_json(root / "selection-manifest.json", summary)
    return root


def _selection_run_argument(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("selection must be DATASET=RUN_ID")
    dataset, run_id = value.split("=", 1)
    if dataset not in PROTOCOL["scientific_scope"]["datasets"] or not run_id:
        raise argparse.ArgumentTypeError("selection must name one Issue #99 dataset and runtime run ID")
    return dataset, run_id


def generate_report(selection_args: list[str]) -> tuple[Path, Path]:
    run_by_dataset = dict(_selection_run_argument(value) for value in selection_args)
    datasets = PROTOCOL["scientific_scope"]["datasets"]
    if set(run_by_dataset) != set(datasets):
        raise ValueError("report requires exactly one recorded selection run per Issue #99 dataset")
    runs = runtime_runs("ess-research", 99).resolve(strict=True)
    frozen: dict[str, Any] = {"format": "ess-issue99-frozen-train-selection-v3", "issue": 99,
        "protocol_sha256": PROTOCOL_SHA256, "split": "train", "budgets": PROTOCOL["scientific_scope"]["budgets"],
        "generalization_claim": False, "datasets": {}, "case_count_expected": 40}
    case_rows = []
    report_lines = ["# Issue #99 — official AreCEL train-only greedy sweep", "",
        "**Scope:** official AreCEL train queries and train labels only; Forest10, Census13, DMV11, and Power7; budgets `B=0,2,3,4,5`; unit candidate cost is a proxy. This report makes no held-out generalization claim.", "",
        "## Evidence and interpretation", "",
        "Selections were computed with the pinned deterministic `add_only_greedy` implementation. Nominal and task-wise PESS use exact `Fraction` objective values under the stated fitted train model; the outer selection is a heuristic and is not globally optimal by claim. PESS is the task-wise sum of per-task worst losses over the prescribed inclusion-maximal matching family. PostgreSQL observations are conditional on the pinned instrumented build and replayed sample; an EXPLAIN alone is not evidence that every real PostgreSQL plan selected an MCV statistic.", "",
        "Train truth came from the pinned split-container label pickle. Standard unpickling materialized that container; the runner explicitly dereferenced only `train` and did not index, serialize, or use valid/test label values. No test EXPLAIN was run. Valid-only Issue #87 coefficients were not reused. Optional cross-objective fixed-set evaluation was not run. Training objective values describe the frozen training models and are not generalization accuracy.", "",
        "The two-worker protocol-v1 Forest10 attempt was stopped at the researcher’s request for configurable parallelism after 98,616 successful observations; those observations were not reused. A first 12-worker v2 implementation attempt was stopped after detecting duplicate baseline scheduling; its 167,593 baseline rows were retained as INCOMPLETE. Forest10 and Census13 completed under v2’s 3/4-GiB disk limits. Protocol v3 changes only the disk envelope to a 9-GiB early stop and 10-GiB hard cap; the scientific scope, PostgreSQL measurement, model fit, and selection limits are unchanged. The v2 DMV11 12/11-worker attempts stopped during cluster setup at the old disk cap with zero observations; the 10-worker attempt was stopped by the researcher before observation collection when the cap was revised.", "",
        "## Cases", "",
        "| Dataset | B | Nominal case | PESS case | Same selected set? |",
        "|---|---:|---|---|---|"]
    complete = incomplete = 0
    for dataset in datasets:
        run_id = run_by_dataset[dataset]
        selection_root = runs / run_id
        if selection_root.is_symlink() or not selection_root.is_dir():
            raise ValueError(f"selection run is not a direct Issue #99 runtime child: {run_id}")
        selection_root = selection_root.resolve(strict=True)
        if selection_root.parent != runs:
            raise ValueError(f"selection run is not a direct Issue #99 runtime child: {run_id}")
        selection_manifest = json.loads((selection_root / "selection-manifest.json").read_text(encoding="utf-8"))
        selection_protocol_sha = selection_manifest.get("protocol_sha256")
        if selection_protocol_sha not in SUPPORTED_PROTOCOLS:
            raise ValueError(f"{dataset} selection run has an unsupported protocol hash")
        case_path = selection_root / "case-results.jsonl"
        rows = [json.loads(line) for line in case_path.read_text(encoding="utf-8").splitlines() if line]
        if len(rows) != 10 or len({row["case_id"] for row in rows}) != 10:
            raise ValueError(f"{dataset} selection run does not account for ten distinct labeled cases")
        collection_root = runs / selection_manifest["collection_run_id"]
        collection = json.loads((collection_root / "collection-manifest.json").read_text(encoding="utf-8"))
        collection_protocol_sha = collection.get("protocol_sha256")
        if (collection.get("dataset") != dataset or collection.get("split") != "train"
                or collection_protocol_sha not in SUPPORTED_PROTOCOLS):
            raise ValueError(f"{dataset} collection run provenance mismatch")
        collection_protocol = SUPPORTED_PROTOCOLS[collection_protocol_sha]
        resource = collection_protocol["resource_envelope"]
        resource_limits = collection.get("resource_limits") or {
            "early_stop_wall_seconds": resource["per_dataset_early_stop_limits"]["wall_seconds"],
            "early_stop_allocated_disk_bytes": resource["per_dataset_early_stop_limits"]["allocated_disk_bytes"],
            "hard_wall_seconds": resource["per_dataset_hard_limits"]["wall_seconds"],
            "hard_allocated_disk_bytes": resource["per_dataset_hard_limits"]["allocated_disk_bytes"]}
        frozen["datasets"][dataset] = {"selection_run_id": run_id,
            "selection_manifest_sha256": sha256_file(selection_root / "selection-manifest.json"),
            "selection_protocol_sha256": selection_protocol_sha,
            "collection_run_id": collection_root.name,
            "collection_manifest_sha256": sha256_file(collection_root / "collection-manifest.json"),
            "collection_protocol_sha256": collection_protocol_sha,
            "resource_limits": resource_limits,
            "collection_status": collection.get("status"), "parallelism": collection.get("parallelism"),
            "train_queries": collection.get("train_query_count"),
            "candidate_count": collection.get("candidate_count"),
            "expected_observations": collection.get("expected_observations"),
            "completed_observations": collection.get("completed_observations"),
            "sample_sha256": collection.get("sample", {}).get("sha256"),
            "observation_aggregate_sha256": selection_manifest.get("observation_aggregate_sha256"),
            "model_fit": selection_manifest.get("model_fit")}
        case_rows.extend(rows)
        for row in rows:
            if row["status"] == "COMPLETE":
                complete += 1
            else:
                incomplete += 1
        row_by_case = {row["case_id"]: row for row in rows}
        for budget in PROTOCOL["scientific_scope"]["budgets"]:
            nominal = row_by_case[f"{dataset}-nominal-b{budget}"]
            pess = row_by_case[f"{dataset}-pess-b{budget}"]
            if nominal["status"] == "COMPLETE" and pess["status"] == "COMPLETE":
                nominal_ids, pess_ids = nominal["selected_ids"], pess["selected_ids"]
                same = "yes" if nominal_ids == pess_ids else "no"
                nominal_text = "`" + ", ".join(nominal_ids) + "`" if nominal_ids else "∅"
                pess_text = "`" + ", ".join(pess_ids) + "`" if pess_ids else "∅"
            else:
                same = "incomplete"
                nominal_text = "COMPLETE: `" + ", ".join(nominal["selected_ids"] or []) + "`" if nominal["status"] == "COMPLETE" else "INCOMPLETE: " + nominal["termination_reason"]
                pess_text = "COMPLETE: `" + ", ".join(pess["selected_ids"] or []) + "`" if pess["status"] == "COMPLETE" else "INCOMPLETE: " + pess["termination_reason"]
            report_lines.append(f"| {dataset} | {budget} | {nominal_text} | {pess_text} | {same} |")
    frozen["case_count_complete"] = complete
    frozen["case_count_incomplete"] = incomplete
    frozen["status"] = "COMPLETE" if complete == 40 else "PARTIAL"
    frozen["cases"] = case_rows
    manifest_path = HERE / "selection-manifest-v3.json"
    atomic_json(manifest_path, frozen)
    report_lines.extend(["", f"**Case accounting:** {complete}/40 COMPLETE; {incomplete}/40 INCOMPLETE. The sweep is labeled COMPLETE only when all 40 cases complete.", "",
        "## Collection evidence", "",
        "| Dataset | Workers | Early disk stop (bytes) | Hard disk cap (bytes) | Collection status | Train queries | Candidate pairs | Structured calls completed / required | Collection wall seconds | Peak allocated disk bytes |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|"])
    for dataset in datasets:
        details = frozen["datasets"][dataset]
        collection = json.loads((runs / details["collection_run_id"] / "collection-manifest.json").read_text(encoding="utf-8"))
        limits = details["resource_limits"]
        report_lines.append(f"| {dataset} | {collection.get('parallelism', '—')} | {limits['early_stop_allocated_disk_bytes']} | {limits['hard_allocated_disk_bytes']} | {collection.get('status')} | {collection.get('train_query_count', '—')} | {collection.get('candidate_count', '—')} | {collection.get('completed_observations', 0)} / {collection.get('expected_observations', '—')} | {collection.get('total_wall_seconds', collection.get('collection_elapsed_seconds', '—'))} | {collection.get('peak_allocated_disk_bytes', '—')} |")
    report_lines.extend(["", "The sizing projection was based on a previous valid-only collection and was not treated as a runtime guarantee. Protocol v2 runs retain the 7.5-hour/3-GiB early stop and 8-hour/4-GiB hard limit; protocol v3 runs use 7.5 hours/9 GiB and 8 hours/10 GiB. Each collection manifest pins its protocol hash and effective limits. Incomplete PG attempts remain separate in the runtime store.", "",
        "Exact per-case fractions, greedy traces, addition orders, selected IDs, budgets, resource limits, work counters, and input hashes are in [`selection-manifest-v3.json`](selection-manifest-v3.json). Query-level structured observations and run-local sample files remain outside Git under the Issue #99 runtime path.", ""])
    report_path = HERE / "findings-v3.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    collect_parser = sub.add_parser("collect", help="collect complete official train baseline/singleton observations for one dataset")
    collect_parser.add_argument("dataset", choices=PROTOCOL["scientific_scope"]["datasets"])
    collect_parser.add_argument("--run-id")
    collect_parser.add_argument("--parallelism", type=int,
        help=f"worker/cluster count (1..{PROTOCOL['collection_parallelism']['maximum_workers']}); defaults to maximum CPU affinity")
    select_parser = sub.add_parser("select", help="run the frozen train-only Nominal/PESS greedy case matrix")
    select_parser.add_argument("dataset", choices=PROTOCOL["scientific_scope"]["datasets"])
    select_parser.add_argument("--collection-run-id", required=True)
    report_parser = sub.add_parser("report", help="derive the concise report and frozen 40-case selection manifest")
    report_parser.add_argument("--selection", action="append", type=_selection_run_argument, required=True, metavar="DATASET=RUN_ID")
    child_parser = sub.add_parser("_solver-scope", help=argparse.SUPPRESS)
    child_parser.add_argument("--case-dir", type=Path, required=True)
    child_parser.add_argument("--unit", required=True)
    child_parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "_solver-scope":
        _scope_child(args.case_dir, args.unit, args.request)
        return 127
    if args.command == "collect":
        root = collect_dataset(args.dataset, args.run_id, args.parallelism)
        manifest = json.loads((root / "collection-manifest.json").read_text(encoding="utf-8"))
        print(json.dumps({"runtime_run": root.name, "status": manifest["status"],
            "completed_observations": manifest.get("completed_observations", 0),
            "expected_observations": manifest.get("expected_observations"),
            "parallelism": manifest.get("parallelism")}, sort_keys=True))
        return 0 if manifest["status"] == "COMPLETE" else 2
    if args.command == "select":
        runs = runtime_runs("ess-research", 99).resolve(strict=True)
        collection_path = runs / args.collection_run_id
        manifest = json.loads((collection_path / "collection-manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "COMPLETE":
            selection_root = mark_selection_incomplete(args.dataset, collection_path,
                f"collection_incomplete:{manifest.get('failure') or manifest.get('status')}")
        else:
            try:
                selection_root = run_selection(args.dataset, collection_path)
            except Exception as exc:
                selection_root = mark_selection_incomplete(args.dataset, collection_path,
                    f"model_or_selection_setup_incomplete:{type(exc).__name__}:{str(exc)[:300]}")
        selection_manifest = json.loads((selection_root / "selection-manifest.json").read_text(encoding="utf-8"))
        print(json.dumps({"runtime_run": selection_root.name, "status": selection_manifest["status"],
            "complete": selection_manifest["case_count_complete"], "incomplete": selection_manifest["case_count_incomplete"]}, sort_keys=True))
        return 0 if selection_manifest["case_count_incomplete"] == 0 else 2
    report, manifest = generate_report([f"{dataset}={run_id}" for dataset, run_id in args.selection])
    frozen = json.loads(manifest.read_text(encoding="utf-8"))
    print(json.dumps({"findings_report": str(report.relative_to(ROOT)),
        "selection_manifest": str(manifest.relative_to(ROOT)), "status": frozen["status"],
        "complete": frozen["case_count_complete"], "incomplete": frozen["case_count_incomplete"]}, sort_keys=True))
    return 0 if frozen["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
