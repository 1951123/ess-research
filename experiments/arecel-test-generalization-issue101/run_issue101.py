"""Run the frozen, official AreCEL test Q-error evaluation for Issue #101."""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
from typing import Any
from uuid import uuid4

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/add-only-greedy-issue99"))

from ess_research.arecel import archive as arecel
from ess_research.arecel.real import ARCHIVE_SHA256, UPSTREAM_COMMIT
from ess_research.task_paths import configured_root, runtime_runs
import run_issue99 as issue99

PROTOCOL_PATH = HERE / "protocol-v1.json"
TRAIN_RESOURCES = ROOT / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
DATASETS = ("forest10", "census13", "dmv11", "power7")
POSTGRESQL_COMMIT = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
ISSUE99_HELPER_COMMIT = "76106024611ae91505f1f05bdc35aed44d9c38c4"
PLAN_MARKER = re.compile(r"^__ISSUE101_(BEGIN|END)_(\d{5})__$")
PLAN_OPTIONS = "-c client_min_messages=warning -c plan_cache_mode=force_custom_plan -c max_parallel_workers_per_gather=0"
@contextmanager
def fixed_pgoptions():
    previous = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = PLAN_OPTIONS
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = previous


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def read_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_TEST_OUTCOME_ACCESS":
        raise RuntimeError("Issue #101 protocol is not frozen")
    if protocol["source_pins"]["arecel_archive_sha256"] != ARCHIVE_SHA256:
        raise RuntimeError("protocol AreCEL archive pin differs from the pinned ETL")
    if protocol["source_pins"]["arecel_upstream_commit"] != UPSTREAM_COMMIT:
        raise RuntimeError("protocol AreCEL source pin differs from the pinned ETL")
    if protocol["source_pins"]["postgresql_source_commit"] != POSTGRESQL_COMMIT:
        raise RuntimeError("protocol PostgreSQL pin differs from the Issue #99 build")
    if (platform.python_version() != protocol["execution_environment"]["python_version"]
            or np.__version__ != protocol["execution_environment"]["numpy_version"]):
        raise RuntimeError("Issue #101 Python/NumPy version differs from the frozen execution environment")
    if sha256_file(TRAIN_RESOURCES) != protocol["source_pins"]["train_resources_sha256"]:
        raise RuntimeError("frozen Issue #99 train resource file hash mismatch")
    validate_schedule(protocol)
    return protocol


def validate_schedule(protocol: dict[str, Any]) -> None:
    frozen = json.loads(TRAIN_RESOURCES.read_text(encoding="utf-8"))
    frozen_rows = [row for row in frozen["cases"] if row.get("dataset") in DATASETS]
    expected = {
        (row["dataset"], row["case_id"]):
        (row["objective"], int(row["budget"]), tuple(row["selected_ids"]))
        for row in frozen_rows
    }
    actual: dict[tuple[str, str], tuple[str, int, tuple[str, ...]]] = {}
    distinct_count = 0
    planned_calls = 0
    for dataset in DATASETS:
        spec = protocol["datasets"][dataset]
        cases = spec["cases"]
        if len(cases) != 10 or spec["test_queries"] != 10_000:
            raise RuntimeError(f"{dataset} does not have the frozen 10-case/10,000-query scope")
        for case in cases:
            key = (dataset, case["case_id"])
            if key in actual:
                raise RuntimeError(f"duplicate frozen case: {key}")
            actual[key] = (case["objective"], int(case["budget"]), tuple(case["selected_ids"]))
        configs = spec["configurations"]
        if len(configs) != spec["distinct_config_count"]:
            raise RuntimeError(f"{dataset} unique configuration count mismatch")
        aliases: dict[tuple[str, ...], list[str]] = {}
        for case in cases:
            aliases.setdefault(tuple(case["selected_ids"]), []).append(case["case_id"])
        if len(aliases) != len(configs):
            raise RuntimeError(f"{dataset} configurations are not deduplicated exactly once")
        config_keys = set()
        for config in configs:
            selected = tuple(config["selected_ids"])
            if selected in config_keys or config["case_ids"] != aliases[selected]:
                raise RuntimeError(f"{dataset} configuration mapping differs from frozen cases")
            config_keys.add(selected)
        if sum(len(c["case_ids"]) for c in configs) != len(cases):
            raise RuntimeError(f"{dataset} case mapping is incomplete")
        distinct_count += len(configs)
        planned_calls += len(configs) * spec["test_queries"]
    if actual != expected:
        raise RuntimeError("Issue #101 case map differs from the merged Issue #99 frozen selections")
    if len(actual) != 40 or distinct_count != 25 or planned_calls != 250_000:
        raise RuntimeError("Issue #101 call schedule differs from its frozen 40-case/250,000-call contract")
    if protocol["execution"]["configuration_count"] != distinct_count:
        raise RuntimeError("protocol configuration count mismatch")
    if protocol["execution"]["planned_explain_calls"] != planned_calls:
        raise RuntimeError("protocol planned Plan Rows call count mismatch")


def parse_top_level_plan_rows(output: str) -> int:
    """Read only the top-level EXPLAIN Plan Rows field from one JSON result."""
    try:
        document = json.loads(output.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_EXPLAIN_JSON") from exc
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise ValueError("INVALID_EXPLAIN_DOCUMENT")
    plan = document[0].get("Plan")
    if not isinstance(plan, dict):
        raise ValueError("MISSING_TOP_LEVEL_PLAN")
    if "Plan Rows" not in plan:
        raise ValueError("MISSING_TOP_LEVEL_PLAN_ROWS")
    rows = plan.get("Plan Rows")
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 0:
        raise ValueError("INVALID_TOP_LEVEL_PLAN_ROWS")
    return rows


def qerror(estimate: float, truth: float) -> float:
    """Pinned AreCEL qerror semantics, including its three zero cases."""
    if estimate == 0 and truth == 0:
        return 1.0
    if estimate == 0:
        return float(truth)
    if truth == 0:
        return float(estimate)
    if estimate > truth:
        return float(estimate / truth)
    return float(truth / estimate)


def qerror_for_plan_rows(plan_rows: int, truth: int) -> tuple[float, int]:
    if (isinstance(plan_rows, bool) or not isinstance(plan_rows, int) or plan_rows < 0
            or isinstance(truth, bool) or not isinstance(truth, int) or truth < 0):
        raise ValueError("Plan Rows and truth must be nonnegative integers")
    rounded = int(np.round(1.0 * plan_rows))
    return qerror(float(rounded), float(truth)), rounded


def summarize_errors(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty error vector")
    errors = np.asarray(values, dtype=np.float64)
    return {
        "p50": float(np.median(errors)),
        "p95": float(np.percentile(errors, 95)),
        "p99": float(np.percentile(errors, 99)),
        "max": float(np.max(errors)),
    }


def parse_batch_output(stdout: str, expected_count: int) -> list[dict[str, Any]]:
    """Parse marker-delimited ordinary EXPLAIN responses, preserving each failure."""
    output: list[dict[str, Any]] = [
        {"status": "NOT_EXECUTED_PROCESS_STOP", "plan_rows": None} for _ in range(expected_count)
    ]
    active: int | None = None
    chunks: list[str] = []
    seen_begins: set[int] = set()
    seen_ends: set[int] = set()

    def finish(index: int) -> None:
        payload = "\n".join(chunks).strip()
        if not payload:
            output[index] = {"status": "MISSING_EXPLAIN_OUTPUT", "plan_rows": None}
            return
        try:
            rows = parse_top_level_plan_rows(payload)
        except ValueError as exc:
            output[index] = {"status": str(exc), "plan_rows": None}
        else:
            output[index] = {"status": "VALID", "plan_rows": rows}

    for line in stdout.splitlines():
        match = PLAN_MARKER.fullmatch(line.strip())
        if not match:
            if active is not None:
                chunks.append(line)
            continue
        kind, raw_index = match.groups()
        index = int(raw_index)
        if index >= expected_count:
            raise ValueError("batch output contains an out-of-schedule query marker")
        if kind == "BEGIN":
            if active is not None or index in seen_begins:
                raise ValueError("batch output contains a nested or duplicate BEGIN marker")
            active = index
            seen_begins.add(index)
            chunks = []
        else:
            if active != index or index in seen_ends:
                raise ValueError("batch output END marker does not match its active query")
            finish(index)
            active = None
            seen_ends.add(index)
    if active is not None:
        output[active] = {"status": "TRUNCATED_EXPLAIN_OUTPUT", "plan_rows": None}
    return output


def build_batch_sql(queries: list[dict[str, Any]], path: Path) -> None:
    lines: list[str] = []
    for index, query in enumerate(queries):
        sql = str(query["sql"]).strip()
        if not sql.upper().startswith("SELECT ") or not sql.endswith(";"):
            raise ValueError("AreCEL adapter did not produce one terminated SELECT per query")
        lines.append(f"\\echo __ISSUE101_BEGIN_{index:05d}__")
        lines.append("EXPLAIN (FORMAT JSON, SUMMARY OFF) " + sql)
        lines.append(f"\\echo __ISSUE101_END_{index:05d}__")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_test_inputs(dataset: str, input_root: Path) -> tuple[Path, list[dict[str, Any]], list[int], dict[str, Any]]:
    """Extract the full table CSV but only dereference official test split values."""
    input_root.mkdir(parents=True, exist_ok=False)
    csv_path = input_root / "table.csv"
    members = {
        f"data/{dataset}/original.csv": "csv",
        f"data/{dataset}/workload/base.pkl": "workload",
        f"data/{dataset}/workload/base-original-label.pkl": "labels",
    }
    buffers: dict[str, bytes] = {}
    seen: set[str] = set()
    with arecel._archive(configured_root("ESS_DATA_ROOT")) as verified:
        with tarfile.open(fileobj=verified, mode="r|gz") as archive_file:
            for member in archive_file:
                name = member.name.removeprefix("./")
                if name not in members:
                    continue
                if name in seen or not member.isfile():
                    raise RuntimeError(f"duplicate or nonregular pinned AreCEL member: {name}")
                source = archive_file.extractfile(member)
                if source is None:
                    raise RuntimeError(f"unreadable pinned AreCEL member: {name}")
                seen.add(name)
                key = members[name]
                if key == "csv":
                    digest = hashlib.sha256()
                    with source, csv_path.open("xb") as target:
                        while block := source.read(1024 * 1024):
                            target.write(block)
                            digest.update(block)
                    expected_csv = issue99.dataset_spec(dataset)[3]
                    if digest.hexdigest() != expected_csv:
                        raise RuntimeError(f"{dataset} original CSV SHA-256 mismatch")
                else:
                    with source:
                        buffers[key] = source.read()
                if seen == set(members):
                    break
    if seen != set(members):
        raise RuntimeError(f"missing pinned AreCEL members: {sorted(set(members) - seen)}")

    workload_hash = sha256_bytes(buffers["workload"])
    labels_hash = sha256_bytes(buffers["labels"])
    workload_doc = arecel._ArchiveUnpickler(io.BytesIO(buffers["workload"])).load()
    label_doc = arecel._ArchiveUnpickler(io.BytesIO(buffers["labels"])).load()
    if (not isinstance(workload_doc, dict) or not isinstance(label_doc, dict)
            or set(workload_doc) != set(label_doc) or set(workload_doc) != {"train", "valid", "test"}):
        raise RuntimeError("pinned AreCEL split containers have unexpected keys")
    raw_queries = workload_doc["test"]
    raw_labels = label_doc["test"]
    if not isinstance(raw_queries, list) or not isinstance(raw_labels, list) or len(raw_queries) != 10_000 or len(raw_labels) != 10_000:
        raise RuntimeError(f"{dataset} official test workload/label count is not exactly 10,000")
    queries = []
    truths = []
    truth_digest = hashlib.sha256()
    for index, (source_query, source_label) in enumerate(zip(raw_queries, raw_labels, strict=True)):
        converted = arecel._query(source_query, dataset)
        query_id = f"arecel:{dataset}:test:{index:06d}"
        if not isinstance(source_label, arecel.Label):
            raise RuntimeError(f"{dataset} test label {index} has an unexpected type")
        truth = arecel._scalar(source_label.cardinality)
        if isinstance(truth, bool) or not isinstance(truth, int) or truth < 0:
            raise RuntimeError(f"{dataset} test truth {index} is not a nonnegative integer")
        queries.append({"query_id": query_id, "source_index": index, **converted})
        truths.append(truth)
        truth_digest.update(json_bytes({"query_id": query_id, "true_cardinality": truth}))
    # The trusted pickle containers materialize their other split objects, but
    # this runner never indexes, serializes, or uses train/valid labels.
    del workload_doc, label_doc, raw_queries, raw_labels, buffers

    source_columns, pg_columns, source_rows, csv_sha, _table = issue99.dataset_spec(dataset)
    if sha256_file(csv_path) != csv_sha:
        raise RuntimeError(f"{dataset} original CSV hash mismatch after extraction")
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        csv_rows = sum(1 for _ in csv.reader(stream)) - 1
    if csv_rows != source_rows:
        raise RuntimeError(f"{dataset} CSV row count {csv_rows} differs from pinned {source_rows}")
    identity = {
        "dataset": dataset,
        "split": "test",
        "query_count": len(queries),
        "truth_count": len(truths),
        "workload_pickle_sha256": workload_hash,
        "labels_pickle_sha256": labels_hash,
        "test_truth_canonical_sha256": truth_digest.hexdigest(),
        "csv_sha256": csv_sha,
        "csv_rows": csv_rows,
        "schema_columns": list(source_columns),
        "catalog_columns": [name for name, _ in pg_columns],
        "container_deserialization_materializes_all_split_objects": True,
        "explicitly_dereferenced_label_split": "test",
        "non_test_label_values_indexed_serialized_or_used": False,
    }
    return csv_path, queries, truths, identity


def load_pinned_helpers(root: Path) -> tuple[Any, Any, dict[str, str]]:
    helper_root = root / "pinned-helpers"
    helper_root.mkdir()
    files = {
        "gate_audit_v2.py": "experiments/pess-multidataset-heldout-stage2b/gate_audit_v2.py",
        "run_formal.py": "experiments/pess-multidataset-heldout-stage2b/run_formal.py",
    }
    digests: dict[str, str] = {}
    for name, path in files.items():
        content = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{ISSUE99_HELPER_COMMIT}:{path}"],
            check=True, capture_output=True,
        ).stdout
        digest = sha256_bytes(content)
        expected = issue99.legacy.PR58_HASHES[name]
        if digest != expected:
            raise RuntimeError(f"pinned Issue #99 helper hash mismatch: {name}")
        (helper_root / name).write_bytes(content)
        digests[name] = digest
    sys.path.insert(0, str(helper_root))
    spec = importlib.util.spec_from_file_location("gate_audit_v2", helper_root / "gate_audit_v2.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pinned PostgreSQL helper")
    helpers = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helpers
    spec.loader.exec_module(helpers)
    formal_spec = importlib.util.spec_from_file_location("run_formal", helper_root / "run_formal.py")
    if formal_spec is None or formal_spec.loader is None:
        raise RuntimeError("could not load pinned Issue #99 PostgreSQL setup helper")
    run_formal = importlib.util.module_from_spec(formal_spec)
    sys.modules[formal_spec.name] = run_formal
    formal_spec.loader.exec_module(run_formal)
    return helpers, run_formal, digests


def load_frozen_sample(dataset: str, root: Path, helpers: Any, protocol: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    sample_spec = protocol["datasets"][dataset]["sample"]
    runs = runtime_runs("ess-research", 99)
    source_root = runs / sample_spec["source_issue99_run_id"]
    source_manifest = source_root / "collection-manifest.json"
    sample_source = source_root / "sample" / f"{dataset}.fixed-sample"
    if sha256_file(source_manifest) != sample_spec["source_manifest_sha256"]:
        raise RuntimeError(f"{dataset} Issue #99 sample collection manifest changed")
    prior = json.loads(source_manifest.read_text(encoding="utf-8"))
    if prior.get("status") != "COMPLETE" or prior.get("dataset") != dataset:
        raise RuntimeError(f"{dataset} source sample is not from a complete Issue #99 collection")
    destination = root / "samples" / f"{dataset}.fixed-sample"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sample_source.open("rb") as source, destination.open("xb") as target:
        shutil.copyfileobj(source, target, 1024 * 1024)
    if sha256_file(destination) != sample_spec["sha256"]:
        raise RuntimeError(f"{dataset} copied frozen sample hash mismatch")
    header = helpers.sample_header(destination)
    source_rows = issue99.dataset_spec(dataset)[2]
    columns = len(issue99.dataset_spec(dataset)[1])
    if (header["server_version"] != "16.14" or header["sample_target"] != 90_000
            or header["tuple_count"] != min(source_rows, 90_000) or header["natts"] != columns
            or sample_spec["bytes"] != destination.stat().st_size):
        raise RuntimeError(f"{dataset} frozen sample header differs from the Issue #99 protocol")
    return destination, {"sha256": sample_spec["sha256"], "bytes": destination.stat().st_size,
                         "source_issue99_run_id": sample_spec["source_issue99_run_id"],
                         "source_manifest_sha256": sample_spec["source_manifest_sha256"],
                         "header": header}


def candidate_map(dataset: str) -> dict[str, dict[str, Any]]:
    source_columns, pg_columns, _rows, _csv_sha, table = issue99.dataset_spec(dataset)
    candidates: dict[str, dict[str, Any]] = {}
    for left in range(len(source_columns)):
        for right in range(left + 1, len(source_columns)):
            edge = f"e{left:02d}_{right:02d}"
            candidates[edge] = {
                "id": edge,
                "statistic_name": f"ess_issue99_{dataset}_{edge}",
                "catalog_columns": [pg_columns[left][0], pg_columns[right][0]],
                "endpoints": [source_columns[left], source_columns[right]],
                "table": table,
            }
    return candidates


def configure_source_table(helpers: Any, prefix: Path, cluster: dict[str, Any], dataset: str,
                           csv_path: Path, sample: Path) -> dict[str, Any]:
    _source_columns, pg_columns, source_rows, _csv_sha, table = issue99.dataset_spec(dataset)
    schema = issue99._schema_sql(dataset, pg_columns)
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=PLAN_OPTIONS)
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"], schema, env)
    escaped_csv = str(csv_path).replace("'", "''")
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                 f"\\copy {table} FROM '{escaped_csv}' WITH (FORMAT csv, HEADER true);", env, timeout=1800)
    count = int(helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                             f"SELECT count(*) FROM {table};", env, tuples=True).strip())
    if count != source_rows:
        raise RuntimeError(f"{dataset} imported {count} rows; expected the full {source_rows}-row table")
    for name, _type in pg_columns:
        helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                     f'ALTER TABLE {table} ALTER COLUMN "{name}" SET STATISTICS 300;', env)
    relation_oid = int(helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                                    f"SELECT '{table}'::regclass::oid;", env, tuples=True).strip())
    sample_header = helpers.sample_header(sample)
    if (sample_header["relation_oid"] != relation_oid
            or sample_header["relation_identity"] != f"6:public{len(dataset)}:{dataset}"):
        raise RuntimeError(f"{dataset} fixed sample relation identity does not match its fresh full table")
    return {"table": table, "full_source_rows": count, "relation_oid": relation_oid,
            "ordinary_column_target": 300, "sample_relation_identity_matches": True}


def run_config(run_formal: Any, prefix: Path, cluster: dict[str, Any], dataset: str,
               candidates: dict[str, dict[str, Any]], selected: tuple[str, ...], sample: Path) -> list[dict[str, Any]]:
    return run_formal.configure_statistics(prefix, cluster, dataset, candidates, selected, sample)


def run_plan_batch(prefix: Path, cluster: dict[str, Any], queries: list[dict[str, Any]],
                   sql_root: Path, parallelism: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if parallelism != 6:
        raise ValueError("Issue #101 freezes six concurrent clients per stable configuration")
    partitions: list[list[tuple[int, dict[str, Any]]]] = [[] for _ in range(parallelism)]
    for index, query in enumerate(queries):
        partitions[index % parallelism].append((index, query))
    parsed_all: list[dict[str, Any]] = [
        {"status": "NOT_EXECUTED_PROCESS_STOP", "plan_rows": None} for _ in queries
    ]
    worker_diagnostics: list[dict[str, Any]] = []

    def run_worker(worker_id: int, partition: list[tuple[int, dict[str, Any]]]):
        worker_queries = [query for _index, query in partition]
        sql_path = sql_root / f"worker{worker_id}.sql"
        build_batch_sql(worker_queries, sql_path)
        env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=PLAN_OPTIONS)
        command = [str(prefix / "bin/psql"), "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=0",
                   "-h", str(cluster["socket_dir"]), "-p", str(cluster["port"]), "-d", "postgres",
                   "-f", str(sql_path)]
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        parsed = parse_batch_output(result.stdout, len(worker_queries))
        diagnostic = {"worker_id": worker_id, "query_count": len(worker_queries),
                      "psql_returncode": result.returncode,
                      "stderr_bytes": len(result.stderr.encode("utf-8")),
                      "stderr_sha256": sha256_bytes(result.stderr.encode("utf-8")),
                      "valid_plan_rows": sum(row["status"] == "VALID" for row in parsed),
                      "unresolved_or_unstarted": sum(row["status"] != "VALID" for row in parsed),
                      "attempted_markers": sum(row["status"] != "NOT_EXECUTED_PROCESS_STOP" for row in parsed)}
        sql_path.unlink(missing_ok=True)
        return partition, parsed, diagnostic

    with ThreadPoolExecutor(max_workers=parallelism, thread_name_prefix="issue101-plan") as pool:
        futures = [pool.submit(run_worker, worker_id, partition)
                   for worker_id, partition in enumerate(partitions)]
        for future in futures:
            partition, parsed, diagnostic = future.result()
            worker_diagnostics.append(diagnostic)
            for (source_index, _query), row in zip(partition, parsed, strict=True):
                parsed_all[source_index] = row
    diagnostic = {
        "parallel_clients": parallelism,
        "worker_count": len(worker_diagnostics),
        "valid_plan_rows": sum(row["status"] == "VALID" for row in parsed_all),
        "unresolved_or_unstarted": sum(row["status"] != "VALID" for row in parsed_all),
        "attempted_markers": sum(row["status"] != "NOT_EXECUTED_PROCESS_STOP" for row in parsed_all),
        "workers": worker_diagnostics,
    }
    return parsed_all, diagnostic


def metrics_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["status"] == "VALID"]
    errors = [float(row["qerror"]) for row in valid]
    zeros = {
        "both_zero": sum(row["estimate_rounded_r1"] == 0 and row["true_cardinality"] == 0 for row in valid),
        "estimate_zero_truth_positive": sum(row["estimate_rounded_r1"] == 0 and row["true_cardinality"] > 0 for row in valid),
        "truth_zero_estimate_positive": sum(row["estimate_rounded_r1"] > 0 and row["true_cardinality"] == 0 for row in valid),
        "both_positive": sum(row["estimate_rounded_r1"] > 0 and row["true_cardinality"] > 0 for row in valid),
    }
    return {
        "status": "COMPLETE" if len(valid) == len(rows) else "INCOMPLETE",
        "query_count": len(rows),
        "valid_count": len(valid),
        "unresolved_count": len(rows) - len(valid),
        "qerror": summarize_errors(errors) if errors else None,
        "zero_cases": zeros,
        "unresolved_status_counts": {
            status: sum(row["status"] == status for row in rows)
            for status in sorted({row["status"] for row in rows if row["status"] != "VALID"})
        },
    }


def evaluate_dataset(dataset: str, protocol: dict[str, Any], run_root: Path,
                     helpers: Any, run_formal: Any, prefix: Path, guard: Any,
                     manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dataset_spec = protocol["datasets"][dataset]
    input_root = run_root / "input" / dataset
    csv_path, queries, truths, input_identity = extract_test_inputs(dataset, input_root)
    sample, sample_identity = load_frozen_sample(dataset, run_root, helpers, protocol)
    if len(queries) != dataset_spec["test_queries"]:
        raise RuntimeError(f"{dataset} test query count differs from frozen protocol")
    candidate_specs = candidate_map(dataset)
    raw_path = run_root / "raw-observations.jsonl.gz"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    config_results: dict[str, dict[str, Any]] = {}
    config_query_rows: dict[str, list[dict[str, Any]]] = {}
    dataset_result: dict[str, Any] = {"dataset": dataset, "status": "INCOMPLETE",
        "input": input_identity, "sample": sample_identity, "configurations": []}
    cluster_root = run_root / "clusters" / dataset
    with issue99.legacy.owned_cluster(helpers, prefix, cluster_root, os.environ.copy(), guard) as cluster:
        cluster["dataset"] = dataset
        dataset_result["postgresql_table"] = configure_source_table(
            helpers, prefix, cluster, dataset, csv_path, sample
        )
        for config in dataset_spec["configurations"]:
            config_id = config["configuration_id"]
            selected = tuple(config["selected_ids"])
            catalog = run_config(run_formal, prefix, cluster, dataset, candidate_specs, selected, sample)
            if any(row["statistics_target"] != 300 for row in catalog):
                raise RuntimeError(f"{dataset}/{config_id} extended-statistics target is not 300")
            sql_root = run_root / "input" / config_id
            sql_root.mkdir()
            plan_rows, diagnostic = run_plan_batch(
                prefix, cluster, queries, sql_root,
                protocol["execution"]["parallel_clients_per_configuration"],
            )
            shutil.rmtree(sql_root)
            rows: list[dict[str, Any]] = []
            for query, truth, observation in zip(queries, truths, plan_rows, strict=True):
                row: dict[str, Any] = {
                    "dataset": dataset,
                    "configuration_id": config_id,
                    "selected_ids": list(selected),
                    "query_id": query["query_id"],
                    "source_index": query["source_index"],
                    "true_cardinality": truth,
                    "estimate_plan_rows": observation["plan_rows"],
                    "estimate_rounded_r1": None,
                    "qerror": None,
                    "status": observation["status"],
                }
                if observation["status"] == "VALID":
                    value, rounded = qerror_for_plan_rows(observation["plan_rows"], truth)
                    row["estimate_rounded_r1"] = rounded
                    row["qerror"] = value
                rows.append(row)
            raw_fields = ("dataset", "configuration_id", "query_id", "source_index",
                          "true_cardinality", "estimate_plan_rows", "status")
            raw_member_rows = [{key: row[key] for key in raw_fields} for row in rows]
            member = gzip.compress(b"".join(json_bytes(row) for row in raw_member_rows), compresslevel=6, mtime=0)
            raw_offset = raw_path.stat().st_size if raw_path.exists() else 0
            with raw_path.open("ab") as stream:
                stream.write(member)
                stream.flush()
                os.fsync(stream.fileno())
            metrics = metrics_for_rows(rows)
            config_record = {"configuration_id": config_id, "selected_ids": list(selected),
                             "case_ids": config["case_ids"], "sample_replay_status": "PASS",
                             "catalog": catalog,
                             "plan_batch": diagnostic, "metrics": metrics,
                             "raw_member_offset": raw_offset,
                             "raw_member_sha256": sha256_bytes(member),
                             "raw_member_bytes": len(member)}
            config_results[config_id] = metrics
            config_query_rows[config_id] = rows
            dataset_result["configurations"].append(config_record)
            manifest["current_dataset_progress"] = {
                "dataset": dataset, "completed_configurations": len(dataset_result["configurations"]),
                "expected_configurations": dataset_spec["distinct_config_count"],
                "attempted_explain_calls": sum(
                    item["plan_batch"]["attempted_markers"] for item in dataset_result["configurations"]
                ),
            }
            write_manifest(run_root, manifest)
        cluster_identity = cluster["identity"]
        dataset_result["cluster_identity"] = [str(x) for x in cluster_identity]

    # Retain the server log, sample, compact observations and provenance; drop
    # only this run's stopped PGDATA so four datasets fit the same disk cap.
    pgdata = cluster_root / "pgdata"
    if pgdata.exists():
        shutil.rmtree(pgdata)
    shutil.rmtree(input_root, ignore_errors=True)
    dataset_result["status"] = "COMPLETE" if all(
        item["metrics"]["status"] == "COMPLETE" for item in dataset_result["configurations"]
    ) else "INCOMPLETE"
    dataset_result["cases"] = map_case_metrics(dataset_spec, config_results, config_query_rows)
    return dataset_result, dataset_result["cases"]


def map_case_metrics(dataset_spec: dict[str, Any], config_metrics: dict[str, dict[str, Any]],
                     config_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    case_to_config: dict[str, str] = {}
    for config in dataset_spec["configurations"]:
        for case_id in config["case_ids"]:
            case_to_config[case_id] = config["configuration_id"]
    cases = []
    pairwise = []
    for budget in (0, 2, 3, 4, 5):
        nominal = next(row for row in dataset_spec["cases"] if row["objective"] == "nominal" and int(row["budget"]) == budget)
        pess = next(row for row in dataset_spec["cases"] if row["objective"] == "pess" and int(row["budget"]) == budget)
        nominal_config = case_to_config[nominal["case_id"]]
        pess_config = case_to_config[pess["case_id"]]
        pair = {"budget": budget, "nominal_case_id": nominal["case_id"], "pess_case_id": pess["case_id"],
                "nominal_configuration_id": nominal_config, "pess_configuration_id": pess_config}
        left = config_rows[nominal_config]
        right = config_rows[pess_config]
        if nominal_config == pess_config:
            pair.update({"status": "IDENTICAL_FROZEN_SELECTIONS", "paired_query_count": len(left),
                         "pess_lower_qerror_count": 0, "pess_higher_qerror_count": 0,
                         "tie_count": len(left), "unresolved_count": sum(row["status"] != "VALID" for row in left)})
        else:
            differences = []
            for lrow, rrow in zip(left, right, strict=True):
                if lrow["query_id"] != rrow["query_id"]:
                    raise RuntimeError("paired query IDs differ across frozen configurations")
                if lrow["status"] == rrow["status"] == "VALID":
                    differences.append((float(lrow["qerror"]), float(rrow["qerror"])))
            pair.update({"status": "COMPLETE" if len(differences) == len(left) else "INCOMPLETE",
                         "paired_query_count": len(differences),
                         "pess_lower_qerror_count": sum(p < n for n, p in differences),
                         "pess_higher_qerror_count": sum(p > n for n, p in differences),
                         "tie_count": sum(p == n for n, p in differences),
                         "unresolved_count": len(left) - len(differences)})
        pairwise.append(pair)
        for case in (nominal, pess):
            config_id = case_to_config[case["case_id"]]
            cases.append({"case_id": case["case_id"], "objective": case["objective"],
                          "budget": budget, "selected_ids": case["selected_ids"],
                          "configuration_id": config_id, "metrics": config_metrics[config_id]})
    return cases + [{"paired_comparisons": pairwise}]


def write_manifest(root: Path, value: dict[str, Any]) -> None:
    target = root / "run-manifest.json"
    temporary = target.with_name(".run-manifest.tmp")
    temporary.write_bytes(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
    os.replace(temporary, target)


def markdown_report(summary: dict[str, Any]) -> str:
    lines = ["# Issue #101 — official AreCEL test generalization", "",
             f"- Evidence label: **{summary['evidence_label']}**.",
             f"- Frozen source commit: `{summary['source_commit']}`.",
             f"- Run ID: `{summary['run_id']}`; raw observations SHA-256: `{summary.get('raw_observations_sha256', 'INCOMPLETE')}`.",
             "- PostgreSQL 16.14, Issue #99 fixed samples, full source tables, and per-column/per-extstats target 300 were used.",
             "- AreCEL zero-aware Q-error with static `r=1`; P50/P95/P99 use NumPy median/percentile semantics; Max uses NumPy max.",
             "- The results compare Plan Rows and do not establish parity with AreCEL's published learned-estimator environment.", ""]
    for dataset in DATASETS:
        result = summary.get("datasets", {}).get(dataset)
        if not result:
            lines += [f"## {dataset}", "", "Status: **NOT RUN**", ""]
            continue
        lines += [f"## {dataset}", "", f"Status: **{result['status']}**", "",
                  "| Objective | Budget | Selected set | Valid / total | P50 | P95 | P99 | Max |",
                  "|---|---:|---|---:|---:|---:|---:|---:|"]
        for case in result.get("cases", []):
            if "case_id" not in case:
                continue
            metrics = case["metrics"]
            q = metrics["qerror"] or {}
            values = [q.get(key) for key in ("p50", "p95", "p99", "max")]
            formatted = ["—" if value is None else f"{value:.6g}" for value in values]
            lines.append(f"| {case['objective']} | {case['budget']} | `{','.join(case['selected_ids']) or 'Empty'}` | "
                         f"{metrics['valid_count']} / {metrics['query_count']} | " + " | ".join(formatted) + " |")
        paired = next((row["paired_comparisons"] for row in result.get("cases", []) if "paired_comparisons" in row), [])
        if paired:
            lines += ["", "Paired per-query PESS-versus-Nominal Q-error counts:", "",
                      "| Budget | Pair status | PESS lower | PESS higher | Tie | Unresolved |",
                      "|---:|---|---:|---:|---:|---:|"]
            for pair in paired:
                lines.append(f"| {pair['budget']} | {pair['status']} | {pair['pess_lower_qerror_count']} | "
                             f"{pair['pess_higher_qerror_count']} | {pair['tie_count']} | {pair['unresolved_count']} |")
        lines.append("")
    lines += ["## Scope limits", "",
              "The comparison is conditional on the pinned AreCEL archive, PostgreSQL source/build, fixed samples and selected target. Statistics target 300 follows Issue #99 and the explicit researcher decision; AreCEL's public Justfile uses 10000, so exact published-environment parity is not claimed. The frozen selections remain train-only heuristic outputs; this evaluation does not retune resources or prove which statistics object a PostgreSQL plan used.", ""]
    return "\n".join(lines)


def execute(run_id: str | None = None) -> Path:
    protocol = read_protocol()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise RuntimeError("Issue #101 test access requires the committed clean freeze worktree")
    source_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  check=True, capture_output=True, text=True).stdout.strip()
    run_id = run_id or f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-issue101-{uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be one safe path component")
    runs = runtime_runs("ess-research", 101)
    runs.mkdir(parents=True, exist_ok=True)
    root = runs / run_id
    root.mkdir(exist_ok=False)
    (root / "input").mkdir()
    (root / "logs").mkdir()
    manifest: dict[str, Any] = {
        "format": "ess-issue101-run-manifest-v1", "issue": 101, "run_id": run_id,
        "status": "INCOMPLETE", "source_commit": source_commit,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "train_resources_sha256": protocol["source_pins"]["train_resources_sha256"],
        "planned_explain_calls": protocol["execution"]["planned_explain_calls"],
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "available_cpu_affinity_count": len(os.sched_getaffinity(0)),
        "available_disk_bytes_at_start": shutil.disk_usage(root).free,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "datasets": {}, "failure": None,
    }
    write_manifest(root, manifest)
    guard = issue99.legacy.AggregateGuard(
        root, early_seconds=10**12, hard_seconds=10**12,
        early_bytes=protocol["resource_envelope"]["allocated_disk_early_stop_bytes"],
        hard_bytes=protocol["resource_envelope"]["allocated_disk_hard_max_bytes"],
    )
    try:
        with fixed_pgoptions(), guard:
            manifest["phase"] = "pinned_postgresql_build"
            write_manifest(root, manifest)
            prefix, pg_build = issue99.legacy.build_pg(root)
            if pg_build["source_commit"] != POSTGRESQL_COMMIT or pg_build["version"] != "PostgreSQL 16.14":
                raise RuntimeError("built PostgreSQL does not match the frozen source/version")
            manifest["postgresql_build"] = pg_build
            helpers, run_formal, helper_hashes = load_pinned_helpers(root)
            manifest["helper_commit"] = ISSUE99_HELPER_COMMIT
            manifest["helper_sha256"] = helper_hashes
            write_manifest(root, manifest)
            for dataset in DATASETS:
                manifest["phase"] = f"official_test_{dataset}"
                manifest["current_dataset_progress"] = {"dataset": dataset, "completed_configurations": 0,
                                                         "expected_configurations": protocol["datasets"][dataset]["distinct_config_count"]}
                write_manifest(root, manifest)
                result, _ = evaluate_dataset(dataset, protocol, root, helpers, run_formal, prefix, guard, manifest)
                result["attempted_explain_calls"] = sum(
                    item["plan_batch"]["attempted_markers"] for item in result["configurations"]
                )
                manifest["datasets"][dataset] = result
                manifest["attempted_explain_calls"] = sum(
                    item["attempted_explain_calls"] for item in manifest["datasets"].values()
                )
                write_manifest(root, manifest)
            manifest["status"] = "COMPLETE" if all(
                row["status"] == "COMPLETE" for row in manifest["datasets"].values()
            ) else "INCOMPLETE"
            manifest["phase"] = "complete" if manifest["status"] == "COMPLETE" else "completed_with_unresolved_plans"
            manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            manifest["peak_allocated_disk_bytes"] = guard.peak
            manifest["raw_observations_sha256"] = sha256_file(root / "raw-observations.jsonl.gz")
            manifest["raw_observations_bytes"] = (root / "raw-observations.jsonl.gz").stat().st_size
            if manifest["attempted_explain_calls"] > manifest["planned_explain_calls"]:
                raise RuntimeError("Issue #101 attempted more Plan Rows calls than the frozen hard maximum")
            manifest["source_archive_bytes_retained"] = False
            manifest["full_csv_files_retained"] = False
            summary_path = root / "summary.json"
            summary_path.write_text(json.dumps({
                "format": "ess-issue101-analysis-v1", "evidence_label": "experimentally_observed_postgresql_measurements",
                "run_id": run_id, "source_commit": source_commit, "protocol_sha256": manifest["protocol_sha256"],
                "status": manifest["status"], "datasets": manifest["datasets"],
                "raw_observations_sha256": manifest["raw_observations_sha256"],
            }, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            report_path = root / "findings.md"
            report_path.write_text(markdown_report(json.loads(summary_path.read_text())), encoding="utf-8")
    except BaseException as exc:
        manifest["status"] = "INCOMPLETE"
        manifest["failure"] = {"error_class": type(exc).__name__, "message": str(exc)[:1000],
                               "phase": manifest.get("phase"), "guard_stop_reason": guard.stop_reason}
        manifest["peak_allocated_disk_bytes"] = guard.peak
        manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if (root / "raw-observations.jsonl.gz").is_file():
            manifest["raw_observations_sha256"] = sha256_file(root / "raw-observations.jsonl.gz")
            manifest["raw_observations_bytes"] = (root / "raw-observations.jsonl.gz").stat().st_size
        write_manifest(root, manifest)
        raise
    write_manifest(root, manifest)
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    root = execute(args.run_id)
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({"run_root": str(root), "status": manifest["status"],
                      "source_commit": manifest["source_commit"],
                      "peak_allocated_disk_bytes": manifest.get("peak_allocated_disk_bytes"),
                      "raw_observations_sha256": manifest.get("raw_observations_sha256")}, sort_keys=True))
    return 0 if manifest["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
