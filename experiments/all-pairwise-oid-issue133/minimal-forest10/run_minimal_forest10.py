"""Run the frozen two-order Forest10 all-pairwise MCV experiment.

Test EXPLAINs are executed only after protocol/code/input checks and both
independent catalog+ANALYZE preflights have passed. Query-level observations
stay under ESS_RUNTIME_PARENT; only compact summaries are written to Git.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
from uuid import uuid4

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL_PATH = HERE / "protocol-v1.json"
ISSUE101_RUN_ID = "20261025T-issue101-full-test-v1"
DATASET = "forest10"
ORDERS = ("forest10-all-random-01", "forest10-all-random-02")
PARALLEL_CLIENTS = 6
GIB = 1024**3

sys.path.insert(0, str(ROOT / "experiments/arecel-test-generalization-issue101"))
sys.path.insert(0, str(ROOT / "experiments/oid-order-stress-test-issue105"))
import run_issue101 as issue101  # noqa: E402
import run_issue105 as issue105  # noqa: E402


class Inconclusive(RuntimeError):
    """A physical-state or identity failure prevents the order-only contrast."""


class Incomplete(RuntimeError):
    """A measured arm or its query/diagnostic records are incomplete."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(issue101.json_bytes(value)).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def append_event(path: Path, phase: str, detail: dict[str, Any]) -> None:
    row = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "phase": phase, **detail}
    with path.open("ab") as stream:
        stream.write((json.dumps(row, sort_keys=True, ensure_ascii=False,
                                 allow_nan=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def allocated_bytes(root: Path) -> int:
    total = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(base) / name).is_symlink()]
        for name in files:
            path = Path(base) / name
            try:
                st = path.lstat()
            except FileNotFoundError:
                continue
            if path.is_symlink() or not path.is_file():
                continue
            total += st.st_blocks * 512
    return total


class ResourceMonitor:
    def __init__(self, root: Path, *, early_seconds: int, hard_seconds: int,
                 early_bytes: int, hard_bytes: int):
        self.root = root
        self.early_seconds = early_seconds
        self.hard_seconds = hard_seconds
        self.early_bytes = early_bytes
        self.hard_bytes = hard_bytes
        self.started = time.monotonic()
        self.stop_event = threading.Event()
        self.done = threading.Event()
        self.stop_reason: str | None = None
        self.peak_bytes = 0
        self.minimum_global_free = shutil.disk_usage(root).free
        self.thread = threading.Thread(target=self._watch, name="issue133-resource-watch", daemon=True)

    def _watch(self) -> None:
        while not self.done.wait(1):
            try:
                used = allocated_bytes(self.root)
                free = shutil.disk_usage(self.root).free
            except FileNotFoundError:
                continue
            self.peak_bytes = max(self.peak_bytes, used)
            self.minimum_global_free = min(self.minimum_global_free, free)
            elapsed = time.monotonic() - self.started
            reason = None
            if used >= self.hard_bytes:
                reason = "hard allocated-disk cap reached"
            elif elapsed >= self.hard_seconds:
                reason = "hard wall-time cap reached"
            elif used >= self.early_bytes:
                reason = "early allocated-disk stop line reached"
            elif elapsed >= self.early_seconds:
                reason = "early wall-time stop line reached"
            elif free < 5 * GIB:
                reason = "global filesystem free space fell below 5 GiB"
            if reason:
                self.stop_reason = reason
                self.stop_event.set()

    def __enter__(self) -> "ResourceMonitor":
        self.thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.done.set()
        self.thread.join(timeout=5)
        self.peak_bytes = max(self.peak_bytes, allocated_bytes(self.root))
        self.minimum_global_free = min(self.minimum_global_free, shutil.disk_usage(self.root).free)

    def checkpoint(self) -> None:
        if self.stop_event.is_set():
            raise Incomplete(f"resource monitor requested stop: {self.stop_reason}")

    def worker_timeout(self) -> int:
        remaining = max(1, int(self.hard_seconds - (time.monotonic() - self.started)))
        return min(1800, remaining)


def read_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_TEST_EXECUTION":
        raise RuntimeError("experiment protocol is not frozen")
    if platform.python_version() != "3.12.3" or np.__version__ != "2.3.4":
        raise RuntimeError("runtime must match the Issue #101 Python 3.12.3 / NumPy 2.3.4 pin")
    refs = {
        "experiments/all-pairwise-oid-issue133/candidate-universe-manifest.json": protocol["input_pins"]["candidate_universe_manifest_sha256"],
        "experiments/all-pairwise-oid-issue133/all-order-sample-v1.json": protocol["order_source"]["file_sha256"],
        "experiments/all-pairwise-oid-issue133/sample_all_orders.py": protocol["order_source"]["generator_sha256"],
        "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json": protocol["input_pins"]["frozen_train_resource_manifest_sha256"],
        "experiments/arecel-test-generalization-issue101/protocol-v1.json": protocol["pinned_code"]["issue101_protocol_sha256"],
        "experiments/arecel-test-generalization-issue101/run_issue101.py": protocol["pinned_code"]["issue101_runner_sha256"],
        "experiments/oid-order-stress-test-issue105/protocol-v1.md": protocol["pinned_code"]["issue105_protocol_sha256"],
        "experiments/oid-order-stress-test-issue105/protocol-amendment-v1.md": protocol["pinned_code"]["issue105_amendment_sha256"],
        "experiments/oid-order-stress-test-issue105/run_issue105.py": protocol["pinned_code"]["issue105_runner_sha256"],
    }
    for relative, expected in refs.items():
        if sha256_file(ROOT / relative) != expected:
            raise RuntimeError(f"frozen source hash mismatch: {relative}")
    return protocol


def require_clean_committed_worktree() -> str:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise RuntimeError("Test access requires a clean worktree containing the frozen protocol and runner")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          check=True, capture_output=True, text=True).stdout.strip()


def existing_postgres_processes() -> list[dict[str, str]]:
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            comm = (proc / "comm").read_text().strip()
            if comm not in {"postgres", "postmaster"}:
                continue
            cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            found.append({"pid": proc.name, "comm": comm, "cmdline": cmdline[:1000]})
        except OSError:
            continue
    return found


def verify_orders(protocol: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    inventory_path = ROOT / protocol["input_pins"]["candidate_universe_manifest_path"]
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    forest = inventory["datasets"][DATASET]
    expected_rows = forest["candidates"]
    expected_ids = [row["id"] for row in expected_rows]
    if len(expected_ids) != 45 or len(set(expected_ids)) != 45:
        raise Inconclusive("frozen candidate inventory is not 45 unique objects")
    for row in expected_rows:
        if (row.get("kind") != ["mcv"] or row.get("expressions") is not False
                or len(row.get("catalog_columns", [])) != 2 or row.get("target") != 300):
            raise Inconclusive(f"candidate is outside the frozen ordinary two-key MCV set: {row.get('id')}")

    schedule = json.loads((ROOT / protocol["order_source"]["repository_path"]).read_text())
    if hashlib.sha256((ROOT / protocol["order_source"]["repository_path"]).read_bytes()).hexdigest() != protocol["order_source"]["file_sha256"]:
        raise Inconclusive("order-schedule SHA-256 differs from the protocol")
    schedule_rows = schedule["datasets"][DATASET]
    by_name = {row["order_id"]: row for row in schedule_rows}
    resolved = []
    for arm_id in ORDERS:
        order_id = protocol["order_source"]["orders"][arm_id]["order_id"]
        row = by_name.get(order_id)
        if row is None or row.get("kind") != "random_without_replacement":
            raise Inconclusive(f"missing frozen random order {order_id}")
        permutation = row["permutation"]
        digest = sha256_json(permutation)
        if (len(permutation) != 45 or len(set(permutation)) != 45
                or set(permutation) != set(expected_ids)
                or digest != row.get("permutation_sha256")
                or digest != protocol["order_source"]["orders"][arm_id]["permutation_sha256"]):
            raise Inconclusive(f"frozen order {order_id} failed ID-set or SHA verification")
        resolved.append(row)
    if resolved[0]["permutation"] == resolved[1]["permutation"]:
        raise Inconclusive("random-01 and random-02 are not distinct")

    derived = issue101.candidate_map(DATASET)
    derived_ids = list(derived)
    if set(derived_ids) != set(expected_ids):
        raise Inconclusive("Issue #101 DDL candidate generator differs from the M0 frozen IDs")
    for frozen in expected_rows:
        got = derived[frozen["id"]]
        if (got["statistic_name"] != frozen["statistic_name"]
                or got["catalog_columns"] != frozen["catalog_columns"]
                or got["endpoints"] != frozen["source_columns"]):
            raise Inconclusive(f"generated CREATE definition differs for {frozen['id']}")

    runtime_map = Path(os.environ["ESS_RUNTIME_PARENT"]) / forest["candidate_map_runtime_relative_path"]
    if sha256_file(runtime_map) != protocol["input_pins"]["forest10_runtime_candidate_map_sha256"]:
        raise Inconclusive("Issue #99 runtime Forest10 candidate-map file hash mismatch")
    collection_manifest = runtime_map.parents[1] / "collection-manifest.json"
    if sha256_file(collection_manifest) != protocol["input_pins"]["forest10_collection_manifest_sha256"]:
        raise Inconclusive("Issue #99 Forest10 collection manifest hash mismatch")
    return inventory, resolved[0], resolved[1]


def verify_pg_install(protocol: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    runtime = Path(os.environ["ESS_RUNTIME_PARENT"])
    run_root = runtime / "ess-research" / "issue101" / "runs" / ISSUE101_RUN_ID
    previous = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
    expected_commit = protocol["postgresql"]["source_commit"]
    if (previous.get("postgresql_build", {}).get("source_commit") != expected_commit
            or previous.get("postgresql_build", {}).get("version") != "PostgreSQL 16.14"):
        raise Inconclusive("Issue #101 installed binary provenance differs from the frozen PG pin")
    prefix = run_root / "postgresql" / "install"
    expected = protocol["postgresql"]["binary_sha256"]
    actual = {}
    versions = {}
    for name, digest in expected.items():
        executable = prefix / "bin" / name
        actual[name] = sha256_file(executable)
        if actual[name] != digest:
            raise Inconclusive(f"pinned PostgreSQL binary hash mismatch: {name}")
        result = subprocess.run([str(executable), "--version"], check=True,
                                capture_output=True, text=True)
        versions[name] = result.stdout.strip()
    if (not versions["postgres"].endswith("16.14")
            or not versions["pg_config"].endswith("16.14")):
        raise Inconclusive("pinned PostgreSQL executable version is not 16.14")
    build = {
        "status": "VERIFIED",
        "source_run_id": ISSUE101_RUN_ID,
        "source_commit": expected_commit,
        "version": "16.14",
        "build_flags": protocol["postgresql"]["build_flags"],
        "prefix_runtime_relative": f"ess-research/issue101/runs/{ISSUE101_RUN_ID}/postgresql/install",
        "binary_sha256": actual,
        "binary_version_output": versions,
        "issue101_build_manifest_sha256": sha256_file(run_root / "run-manifest.json"),
    }
    return prefix, build


def expected_source_identity(protocol: dict[str, Any]) -> dict[str, Any]:
    pins = protocol["input_pins"]
    return {
        "dataset": DATASET,
        "split": "test",
        "query_count": pins["test_query_count"],
        "truth_count": pins["test_query_count"],
        "workload_pickle_sha256": pins["forest10_workload_pickle_sha256"],
        "labels_pickle_sha256": pins["forest10_test_labels_container_sha256"],
        "test_truth_canonical_sha256": pins["forest10_test_truth_canonical_sha256"],
        "csv_sha256": pins["forest10_full_csv_sha256"],
        "csv_rows": pins["forest10_full_table_rows"],
        "schema_columns": ["Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology",
                           "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways",
                           "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm",
                           "Horizontal_Distance_To_Fire_Points"],
        "catalog_columns": ["elevation", "aspect", "slope", "horizontal_distance_to_hydrology",
                            "vertical_distance_to_hydrology", "horizontal_distance_to_roadways",
                            "hillshade_9am", "hillshade_noon", "hillshade_3pm",
                            "horizontal_distance_to_fire_points"],
        "container_deserialization_materializes_all_split_objects": True,
        "explicitly_dereferenced_label_split": "test",
        "non_test_label_values_indexed_serialized_or_used": False,
    }


def query_identity(queries: list[dict[str, Any]], truths: list[int]) -> dict[str, Any]:
    if len(queries) != 10_000 or len(truths) != 10_000:
        raise Inconclusive("official Forest10 Test workload is not exactly 10,000 rows")
    sql_rows = [{"query_id": q["query_id"], "source_index": q["source_index"], "sql": q["sql"]}
                for q in queries]
    ids = [q["query_id"] for q in queries]
    if len(set(ids)) != 10_000:
        raise Inconclusive("official Test query IDs are not unique")
    return {
        "query_count": len(queries),
        "query_ids_sha256": sha256_json(ids),
        "rendered_test_sql_sha256": sha256_json(sql_rows),
        "test_truth_canonical_sha256": issue101.sha256_bytes(b"".join(
            issue101.json_bytes({"query_id": q["query_id"], "true_cardinality": truth})
            for q, truth in zip(queries, truths, strict=True)
        )),
    }


def cluster_options(port: int, socket_dir: Path) -> str:
    return (f"-p {port} -k {socket_dir} -c log_min_messages=debug1 "
            "-c log_line_prefix='%m [%p] %u@%d app=%a '")


def create_cluster(prefix: Path, root: Path, helpers: Any, monitor: ResourceMonitor,
                   order_id: str) -> tuple[dict[str, Any], tempfile.TemporaryDirectory[str]]:
    root.mkdir(parents=True, exist_ok=False)
    socket_owner = tempfile.TemporaryDirectory(prefix=f"e133-{order_id[-2:]}-")
    socket_dir = Path(socket_owner.name)
    pgdata = root / "pgdata"
    log_path = root / "server.log"
    port = helpers.reserve_port()
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
    cluster = {"pgdata": pgdata, "socket_dir": socket_dir, "port": port,
               "server_log": log_path, "env": env, "socket_owner": socket_owner,
               "order_id": order_id, "started": False}
    try:
        helpers.run_command(
            [str(prefix / "bin/initdb"), "-D", str(pgdata), "--no-locale", "--encoding=UTF8", "-U", "wqts"],
            env=env, timeout=180,
        )
        monitor.checkpoint()
        helpers.run_command(
            [str(prefix / "bin/pg_ctl"), "-D", str(pgdata), "-l", str(log_path),
             "-o", cluster_options(port, socket_dir), "-w", "start"], env=env, timeout=120,
        )
        cluster["started"] = True
        identity = helpers.psql(
            prefix, socket_dir, port,
            "SELECT current_setting('data_directory'), current_setting('port'), current_database(), version();",
            env, tuples=True,
        )
        fields = identity.strip().split("|")
        helpers.validate_cluster_identity(fields, pgdata, port)
        cluster["identity"] = fields
        return cluster, socket_owner
    except BaseException:
        try:
            stop_cluster(prefix, cluster)
        finally:
            socket_owner.cleanup()
        raise


def stop_cluster(prefix: Path, cluster: dict[str, Any]) -> None:
    if not cluster.get("started"):
        return
    subprocess.run([str(prefix / "bin/pg_ctl"), "-D", str(cluster["pgdata"]),
                    "-m", "fast", "-w", "stop"], env=cluster["env"],
                   check=True, capture_output=True, text=True, timeout=120)
    cluster["started"] = False


@contextmanager
def start_existing_cluster(prefix: Path, cluster: dict[str, Any], helpers: Any):
    if cluster.get("started"):
        raise RuntimeError("refusing to start an already active Issue #133 cluster")
    subprocess.run([str(prefix / "bin/pg_ctl"), "-D", str(cluster["pgdata"]),
                    "-l", str(cluster["server_log"]), "-o",
                    cluster_options(cluster["port"], cluster["socket_dir"]), "-w", "start"],
                   env=cluster["env"], check=True, capture_output=True, text=True, timeout=120)
    cluster["started"] = True
    try:
        identity = helpers.psql(
            prefix, cluster["socket_dir"], cluster["port"],
            "SELECT current_setting('data_directory'), current_setting('port'), current_database(), version();",
            cluster["env"], tuples=True,
        )
        fields = identity.strip().split("|")
        helpers.validate_cluster_identity(fields, cluster["pgdata"], cluster["port"])
        cluster["identity"] = fields
        yield cluster
    finally:
        stop_cluster(prefix, cluster)


def payload_state(row: dict[str, Any]) -> str:
    if not row["mcv_payload_present"]:
        return "NULL"
    if int(row["mcv_item_count"]) == 0:
        return "PRESENT_EMPTY"
    return "POPULATED"


def validate_catalog_definition(row: dict[str, Any], candidate: dict[str, Any]) -> None:
    """Validate the catalog definition while retaining NULL/empty MCV states."""
    columns = candidate["catalog_columns"]
    pg_columns = issue101.issue99.dataset_spec(DATASET)[1]
    attnum = {name: index + 1 for index, (name, _type) in enumerate(pg_columns)}
    try:
        expected_keys = " ".join(str(attnum[name]) for name in columns)
    except KeyError as exc:
        raise Inconclusive(f"candidate uses a column outside the Forest10 table: {exc}") from exc
    payload_present = bool(row["mcv_payload_present"])
    kinds = row.get("kinds")
    attnames = row.get("attnames")
    if (row["stxkind"] != "{m}" or int(row["statistics_target"]) != 300
            or row["stxkeys"] != expected_keys
            or kinds not in (None, ["m"])
            or (attnames is not None and attnames != columns)
            or (payload_present and (kinds != ["m"] or attnames != columns))
            or int(row["mcv_item_count"]) < 0
            or not row.get("mcv_content_sha256")):
        raise Inconclusive(f"{candidate['id']}: catalog definition or MCV diagnostic is inconsistent")
    row["resolved_attnames"] = columns
    row["payload_state"] = payload_state(row)


def audit_signature(audit: dict[str, Any]) -> dict[str, Any]:
    header = audit["sample_header"]
    return {
        "table_logical_identity": audit["table_logical_identity"],
        "ordinary_stats_sha256": audit["ordinary_column_stats"]["sha256"],
        "sample_sha256": audit["sample_sha256"],
        "sample_header": {key: header[key] for key in (
            "relation_oid", "relation_identity", "server_version", "sample_target", "tuple_count", "natts")},
        "candidate_payloads": {
            row["candidate_id"]: {
                "attnames": row["attnames"],
                "kinds": row["kinds"],
                "stxkind": row["stxkind"],
                "statistics_target": row["statistics_target"],
                "stxkeys": row["stxkeys"],
                "payload_state": payload_state(row),
                "mcv_item_count": int(row["mcv_item_count"]),
                "mcv_content_sha256": row["mcv_content_sha256"],
            }
            for row in audit["catalog"]
        },
    }


def catalog_audit_for_arm(dataset: str, order_id: str, schedule_row: dict[str, Any],
                          candidates: dict[str, dict[str, Any]], helper_ledger: list[dict[str, Any]],
                          helpers: Any, prefix: Path, cluster: dict[str, Any],
                          sample: Path, sample_sha: str,
                          input_identity: dict[str, Any]) -> dict[str, Any]:
    order = schedule_row["permutation"]
    rows = issue105.query_catalog_audit(helpers, prefix, cluster, dataset)
    expected_names = [candidates[candidate_id]["statistic_name"] for candidate_id in order]
    actual_names = [row["statistic_name"] for row in rows]
    helper_names = [row["statistic_name"] for row in helper_ledger]
    if (len(rows) != 45 or actual_names != expected_names or helper_names != expected_names
            or len({row["statistic_name"] for row in rows}) != 45):
        raise Inconclusive(f"{order_id}: catalog OID order or exact 45-object set differs from CREATE order")
    name_to_id = {row["statistic_name"]: row["id"] for row in candidates.values()}
    expected_by_id = {row["id"]: row for row in json.loads(
        (ROOT / "experiments/all-pairwise-oid-issue133/candidate-universe-manifest.json").read_text()
    )["datasets"][DATASET]["candidates"]}
    ledger_by_name = {row["statistic_name"]: row for row in helper_ledger}
    oid_map: dict[int, str] = {}
    for row in rows:
        candidate_id = name_to_id.get(row["statistic_name"])
        if candidate_id not in order:
            raise Inconclusive(f"{order_id}: unexpected catalog statistics object")
        expected = expected_by_id[candidate_id]
        validate_catalog_definition(row, expected)
        ledger = ledger_by_name[row["statistic_name"]]
        if (int(ledger["oid"]) != int(row["oid"])
                or ledger["stxkeys"] != row["stxkeys"]
                or int(ledger["statistics_target"]) != int(row["statistics_target"])
                or bool(ledger["mcv_payload_present"]) != bool(row["mcv_payload_present"])
                or int(ledger["mcv_item_count"]) != int(row["mcv_item_count"])):
            raise Inconclusive(f"{order_id}/{candidate_id}: helper and SQL catalog audits differ")
        oid = int(row["oid"])
        if oid in oid_map:
            raise Inconclusive(f"{order_id}: duplicate statistics OID")
        oid_map[oid] = candidate_id
        row["candidate_id"] = candidate_id

    table = issue105.table_identity(helpers, prefix, cluster, dataset)
    expected_schema = [
        [index + 1, name, re.sub(r"^varchar", "character varying", type_name.lower())]
        for index, (name, type_name) in enumerate(issue101.issue99.dataset_spec(dataset)[1])
    ]
    if (int(table["row_count"]) != input_identity["csv_rows"]
            or table["columns"] != expected_schema):
        raise Inconclusive(f"{order_id}: full source table row count or schema differs")
    ordinary = issue105.ordinary_stats_audit(helpers, prefix, cluster, dataset)
    if ordinary["column_count"] != len(expected_schema):
        raise Inconclusive(f"{order_id}: ordinary column statistics are incomplete")
    header = helpers.sample_header(sample)
    source_rows = issue101.issue99.dataset_spec(dataset)[2]
    if (sha256_file(sample) != sample_sha or header["server_version"] != "16.14"
            or header["sample_target"] != 90_000
            or header["tuple_count"] != min(source_rows, 90_000)
            or header["natts"] != len(expected_schema)
            or int(header["relation_oid"]) != int(table["relation_oid"])
            or header["relation_identity"] != "6:public8:forest10"):
        raise Inconclusive(f"{order_id}: fixed ANALYZE sample identity/header mismatch")
    catalog_ids = [name_to_id[name] for name in actual_names]
    if catalog_ids != order:
        raise Inconclusive(f"{order_id}: actual OID order differs from the frozen request")
    return {
        "configuration_id": order_id,
        "order_id": schedule_row["order_id"],
        "permutation_sha256": schedule_row["permutation_sha256"],
        "create_statement_candidate_ids": order,
        "catalog_oid_order_candidate_ids": catalog_ids,
        "catalog_oid_order": [
            {"candidate_id": name_to_id[row["statistic_name"]],
             "statistic_name": row["statistic_name"], "oid": int(row["oid"])}
            for row in rows
        ],
        "catalog": rows,
        "table_identity": table,
        "table_logical_identity": {"row_count": int(table["row_count"]), "columns": table["columns"]},
        "ordinary_column_stats": ordinary,
        "sample_sha256": sample_sha,
        "sample_header": header,
        "oid_to_candidate_id": {str(oid): candidate_id for oid, candidate_id in oid_map.items()},
        "candidate_payload_state_counts": dict(sorted(Counter(row["payload_state"] for row in rows).items())),
        "catalog_definition_status": "PASS",
        "sample_replay_status": "PASS",
    }


def compare_pretest_audits(arms: list[dict[str, Any]]) -> dict[str, Any]:
    if len(arms) != 2:
        raise Inconclusive("both frozen ALL arms must be preflighted before Test execution")
    left = audit_signature(arms[0])
    right = audit_signature(arms[1])
    if left != right:
        left_candidates = left["candidate_payloads"]
        right_candidates = right["candidate_payloads"]
        changed = [candidate_id for candidate_id in sorted(left_candidates)
                   if left_candidates[candidate_id] != right_candidates.get(candidate_id)]
        if (left["table_logical_identity"] != right["table_logical_identity"]
                or left["ordinary_stats_sha256"] != right["ordinary_stats_sha256"]
                or left["sample_sha256"] != right["sample_sha256"]
                or left["sample_header"] != right["sample_header"]
                or changed):
            raise Inconclusive(
                "pre-Test physical-state comparison failed; changed candidate IDs=" + ",".join(changed[:20])
            )
    return {
        "status": "PASS",
        "table_logical_identity_equal": True,
        "ordinary_stats_fingerprint_equal": True,
        "fixed_sample_and_header_equal": True,
        "all_45_candidate_payload_states_and_fingerprints_equal": True,
        "comparison_key": "stable candidate_id; numeric OIDs are arm-local only",
    }


def bounded_plan_batch(prefix: Path, cluster: dict[str, Any], queries: list[dict[str, Any]],
                       sql_root: Path, oid_to_id: dict[int, str], log_root: Path,
                       monitor: ResourceMonitor) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    partitions: list[list[tuple[int, dict[str, Any]]]] = [[] for _ in range(PARALLEL_CLIENTS)]
    for index, query in enumerate(queries):
        partitions[index % PARALLEL_CLIENTS].append((index, query))
    all_rows = [{"status": "NOT_EXECUTED_PROCESS_STOP", "plan_rows": None,
                 "diagnostics_status": "NOT_EXECUTED", "mcv_events": [],
                 "mcv_selection_ids": [], "mcv_estimate_ids": []} for _ in queries]

    def stop_worker(process: subprocess.Popen[str]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()

    def worker(worker_id: int, part: list[tuple[int, dict[str, Any]]]):
        sql_path = sql_root / f"worker{worker_id}.sql"
        issue105.build_batch_sql([query for _idx, query in part], sql_path)
        env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"), PGOPTIONS=issue101.PLAN_OPTIONS)
        command = [str(prefix / "bin/psql"), "-X", "-q", "-A", "-t",
                   "-v", "ON_ERROR_STOP=0", "-h", str(cluster["socket_dir"]),
                   "-p", str(cluster["port"]), "-d", "postgres", "-f", str(sql_path)]
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=True)
        timeout = monitor.worker_timeout()
        deadline = time.monotonic() + timeout
        resource_stopped = False
        timed_out = False
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    if monitor.stop_event.is_set():
                        resource_stopped = True
                        stop_worker(process)
                        stdout, stderr = process.communicate()
                        break
                    if time.monotonic() >= deadline:
                        timed_out = True
                        stop_worker(process)
                        stdout, stderr = process.communicate()
                        break
        finally:
            if process.poll() is None:
                stop_worker(process)
        try:
            parsed = issue105.parse_batch_output(stdout, len(part), oid_to_id)
        except Exception as exc:
            parsed = [{"status": "WORKER_EXCEPTION", "plan_rows": None,
                       "diagnostics_status": "INVALID", "mcv_events": [],
                       "mcv_selection_ids": [], "mcv_estimate_ids": []} for _ in part]
            parse_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        else:
            parse_error = None
        if resource_stopped or timed_out:
            for row in parsed:
                if row["status"] == "NOT_EXECUTED_PROCESS_STOP":
                    row["status"] = "RESOURCE_STOP" if resource_stopped else "WORKER_TIMEOUT"
                    row["diagnostics_status"] = "NOT_AVAILABLE"
        stderr_bytes = stderr.encode("utf-8")
        stderr_path = None
        if stderr_bytes:
            stderr_path = log_root / f"worker{worker_id}.stderr"
            stderr_path.write_bytes(stderr_bytes)
        diagnostic = {
            "worker_id": worker_id,
            "query_count": len(part),
            "return_code": process.returncode,
            "valid_plan_rows": sum(row["status"] == "VALID" for row in parsed),
            "attempted_markers": sum(row["status"] != "NOT_EXECUTED_PROCESS_STOP" for row in parsed),
            "diagnostics_status_counts": dict(sorted(Counter(row.get("diagnostics_status", "NOT_AVAILABLE")
                                                                 for row in parsed).items())),
            "stderr_bytes": len(stderr_bytes),
            "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
            "stderr_path": str(stderr_path) if stderr_path else None,
            "resource_stopped": resource_stopped,
            "worker_timed_out": timed_out,
            "parse_error": parse_error,
        }
        sql_path.unlink(missing_ok=True)
        return part, parsed, diagnostic

    sql_root.mkdir(parents=True, exist_ok=False)
    log_root.mkdir(parents=True, exist_ok=False)
    worker_rows = []
    with ThreadPoolExecutor(max_workers=PARALLEL_CLIENTS, thread_name_prefix="issue133-explain") as pool:
        futures = [pool.submit(worker, worker_id, part)
                   for worker_id, part in enumerate(partitions)]
        for future in futures:
            part, parsed, diagnostic = future.result()
            worker_rows.append(diagnostic)
            for (source_index, _query), row in zip(part, parsed, strict=True):
                all_rows[source_index] = row
    shutil.rmtree(sql_root, ignore_errors=True)
    summary = {
        "parallel_clients": PARALLEL_CLIENTS,
        "worker_count": len(worker_rows),
        "valid_plan_rows": sum(row["status"] == "VALID" for row in all_rows),
        "unresolved_or_unstarted": sum(row["status"] != "VALID" for row in all_rows),
        "attempted_markers": sum(row["status"] != "NOT_EXECUTED_PROCESS_STOP" for row in all_rows),
        "diagnostics_status_counts": dict(sorted(Counter(
            row.get("diagnostics_status", "NOT_AVAILABLE") for row in all_rows).items())),
        "workers": worker_rows,
    }
    return all_rows, summary


def current_arm_state(arm: dict[str, Any], helpers: Any, prefix: Path,
                      cluster: dict[str, Any], candidates: dict[str, dict[str, Any]],
                      sample: Path) -> None:
    order = arm["create_statement_candidate_ids"]
    rows = issue105.query_catalog_audit(helpers, prefix, cluster, DATASET)
    name_to_id = {candidate["statistic_name"]: candidate_id
                  for candidate_id, candidate in candidates.items()}
    actual = [name_to_id.get(row["statistic_name"]) for row in rows]
    if actual != order:
        raise Inconclusive(f"{arm['configuration_id']}: catalog order changed before EXPLAIN")
    current_state = {"catalog": rows,
                     "table_logical_identity": issue105.table_identity(helpers, prefix, cluster, DATASET)}
    stored_by_id = {row["candidate_id"]: row for row in arm["catalog"]}
    live_by_id = {name_to_id[row["statistic_name"]]: row for row in rows}
    for candidate_id in order:
        frozen = stored_by_id[candidate_id]
        current_row = live_by_id[candidate_id]
        if (int(frozen["oid"]) != int(current_row["oid"])
                or frozen["attnames"] != current_row["attnames"]
                or frozen["kinds"] != current_row["kinds"]
                or frozen["stxkind"] != current_row["stxkind"]
                or int(frozen["statistics_target"]) != int(current_row["statistics_target"])
                or frozen["stxkeys"] != current_row["stxkeys"]
                or frozen["mcv_content_sha256"] != current_row["mcv_content_sha256"]
                or payload_state(frozen) != payload_state(current_row)
                or int(frozen["mcv_item_count"]) != int(current_row["mcv_item_count"])):
            raise Inconclusive(f"{arm['configuration_id']}/{candidate_id}: MCV state changed before EXPLAIN")
    if (current_state["table_logical_identity"]["row_count"] != arm["table_logical_identity"]["row_count"]
            or current_state["table_logical_identity"]["columns"] != arm["table_logical_identity"]["columns"]
            or issue105.ordinary_stats_audit(helpers, prefix, cluster, DATASET)["sha256"]
            != arm["ordinary_column_stats"]["sha256"]
            or sha256_file(sample) != arm["sample_sha256"]):
        raise Inconclusive(f"{arm['configuration_id']}: data/sample/ordinary stats changed before EXPLAIN")


def analyze_pair(rows_by_order: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    left = rows_by_order[ORDERS[0]]
    right = rows_by_order[ORDERS[1]]
    if len(left) != 10_000 or len(right) != 10_000:
        return {"status": "INCOMPLETE", "paired_valid_query_count": 0}
    if [row["query_id"] for row in left] != [row["query_id"] for row in right]:
        raise Inconclusive("paired arms do not contain the same ordered query IDs")
    plan_diff = qerror_diff = select_diff = estimate_diff = 0
    valid_pairs = 0
    examples: list[dict[str, Any]] = []
    for a, b in zip(left, right, strict=True):
        valid = a["status"] == b["status"] == "VALID"
        if not valid:
            continue
        valid_pairs += 1
        plan_changed = a["estimate_plan_rows"] != b["estimate_plan_rows"]
        q_changed = a["qerror"] != b["qerror"]
        s_changed = a["mcv_selection_ids"] != b["mcv_selection_ids"]
        e_changed = a["mcv_estimate_ids"] != b["mcv_estimate_ids"]
        plan_diff += plan_changed
        qerror_diff += q_changed
        select_diff += s_changed
        estimate_diff += e_changed
        category = None
        if s_changed and q_changed:
            category = "selection_and_qerror_changed"
        elif s_changed and not q_changed:
            category = "selection_changed_qerror_same"
        elif not s_changed and q_changed:
            category = "selection_same_qerror_changed"
        elif plan_changed:
            category = "plan_rows_changed_qerror_same"
        if category and len(examples) < 12:
            examples.append({
                "category": category,
                "query_id": a["query_id"],
                "source_index": a["source_index"],
                "random_01": {
                    "plan_rows": a["estimate_plan_rows"], "qerror": a["qerror"],
                    "mcv_selection_ids": a["mcv_selection_ids"],
                    "mcv_estimate_ids": a["mcv_estimate_ids"],
                    "mcv_events": a["mcv_events"],
                },
                "random_02": {
                    "plan_rows": b["estimate_plan_rows"], "qerror": b["qerror"],
                    "mcv_selection_ids": b["mcv_selection_ids"],
                    "mcv_estimate_ids": b["mcv_estimate_ids"],
                    "mcv_events": b["mcv_events"],
                },
            })
    return {
        "status": "COMPLETE" if valid_pairs == 10_000 else "INCOMPLETE",
        "paired_valid_query_count": valid_pairs,
        "plan_rows_changed_count": plan_diff,
        "qerror_changed_count": qerror_diff,
        "mcv_selection_sequence_changed_count": select_diff,
        "mcv_estimate_sequence_changed_count": estimate_diff,
        "paired_query_count": 10_000,
        "examples": examples,
    }


def environment_snapshot(prefix: Path, pg_build: dict[str, Any], root: Path) -> dict[str, Any]:
    free = shutil.disk_usage(root).free
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "python_executable": sys.executable,
        "python_prefix": sys.prefix,
        "numpy_module_path": np.__file__,
        "platform": platform.platform(),
        "cpu_affinity_count": len(os.sched_getaffinity(0)),
        "logical_cpu_count": os.cpu_count(),
        "memory_bytes_at_preflight": int(Path("/proc/meminfo").read_text().split("MemAvailable:")[1].split()[0]) * 1024,
        "runtime_filesystem_free_bytes_at_preflight": free,
        "filesystem": shutil.disk_usage(root)._asdict(),
        "postgresql_build": pg_build,
        "plan_options": issue101.PLAN_OPTIONS,
        "concurrent_explain_clients": PARALLEL_CLIENTS,
        "only_this_experiment_cluster_started": True,
        "preexisting_postgres_processes_at_start": 0,
    }


def report_metrics(summary: dict[str, Any], raw_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    arms = summary.get("arms", [])
    audit = {"status": summary.get("status"), "pretest_comparison": summary.get("pretest_comparison"), "arms": [
        {key: arm[key] for key in (
            "configuration_id", "order_id", "permutation_sha256", "create_statement_candidate_ids",
            "catalog_oid_order_candidate_ids", "catalog_oid_order", "catalog",
            "table_identity", "table_logical_identity", "ordinary_column_stats",
            "sample_sha256", "sample_header", "candidate_payload_state_counts",
            "catalog_definition_status", "sample_replay_status") if key in arm}
        for arm in arms
    ]}
    raw_identity = None
    if raw_path.is_file():
        raw_identity = {"path_under_runtime_root": str(raw_path),
                        "bytes": raw_path.stat().st_size,
                        "sha256": sha256_file(raw_path)}
    result = {
        "format": "ess-issue133-minimal-forest10-analysis-v1",
        "evidence_label": "experimentally_observed_postgresql_measurements" if summary.get("status") == "COMPLETE" else "incomplete_or_inconclusive_attempt",
        "run_id": summary.get("run_id"),
        "source_commit_before_test": summary.get("source_commit_before_test"),
        "protocol_sha256": summary.get("protocol_sha256"),
        "status": summary.get("status"),
        "outcome_classification": summary.get("outcome_classification"),
        "input_identity": summary.get("input_identity"),
        "resource_usage": summary.get("resource_usage"),
        "attempted_explain_calls": summary.get("attempted_explain_calls"),
        "expected_explain_calls": 20000,
        "arms": [{key: arm.get(key) for key in (
            "configuration_id", "order_id", "permutation_sha256", "status",
            "attempted_explain_calls", "query_count", "diagnostics_status_counts",
            "qerror_metrics", "plan_batch_seconds", "catalog_fingerprint_sha256",
            "ordinary_stats_sha256", "sample_sha256", "raw_member")}
                  for arm in arms],
        "paired": summary.get("paired"),
        "raw_query_archive": raw_identity,
        "limits": [
            "Only the two preselected global OID orders were compared.",
            "No inference about all 45! orders, a random-order expectation, or best/worst order is made.",
            "Changed MCV selection is descriptive and does not by itself identify blocking as the Q-error mechanism.",
            "The official fixed Test workload bounds the observation; no workload-population uncertainty is estimated.",
        ],
    }
    return result, audit


def publish_git_artifacts(summary: dict[str, Any], environment: dict[str, Any],
                          raw_path: Path) -> None:
    analysis, audit = report_metrics(summary, raw_path)
    attempt_root = HERE / "attempts" / str(summary.get("run_id"))
    attempt_root.mkdir(parents=True, exist_ok=False)
    atomic_json(attempt_root / "run-summary.json", analysis)
    atomic_json(attempt_root / "catalog-audit.json", audit)
    atomic_json(attempt_root / "environment.json", environment)
    paired = summary.get("paired") or {}
    lines = [
        "# Issue #133 minimal Forest10 all-MCV OID-order experiment",
        "",
        f"**Status:** `{summary.get('status', 'INCOMPLETE')}`.",
        f"**Outcome:** `{summary.get('outcome_classification', 'NOT_CLASSIFIED')}`.",
        "",
        "This is one fixed-set comparison of the 45 frozen Forest10 ordinary two-column MCV objects. "
        "The only planned intervention was the already-frozen global CREATE/OID order. It does not estimate "
        "the result over all 45! orders and does not establish a blocker mechanism by itself.",
        "",
        "## Frozen order identities",
        "",
        "| Arm | Order | SHA-256 | Catalog OID order verified |",
        "|---|---|---|---|",
    ]
    for arm in summary.get("arms", []):
        lines.append(
            f"| {arm.get('configuration_id')} | {arm.get('order_id')} | "
            f"`{arm.get('permutation_sha256')}` | "
            f"{arm.get('catalog_order_status', 'NOT VERIFIED')} |"
        )
    lines.extend(["", "## Physical-state checks", ""])
    for check in summary.get("pretest_comparison", {}).items():
        lines.append(f"- {check[0]}: `{check[1]}`")
    lines.extend(["", "## Query completeness and metrics", ""])
    lines.append("| Arm | Valid queries | Diagnostics complete/empty | P50 | P95 | P99 | Mean |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for arm in summary.get("arms", []):
        q = arm.get("qerror_metrics") or {}
        lines.append(
            f"| {arm.get('configuration_id')} | {q.get('valid_count', 0)} | "
            f"{arm.get('diagnostics_valid_count', 0)} | {q.get('qerror', {}).get('p50')} | "
            f"{q.get('qerror', {}).get('p95')} | {q.get('qerror', {}).get('p99')} | "
            f"{q.get('qerror', {}).get('mean')} |"
        )
    lines.extend(["", "Paired differences over the same Test query IDs:", ""])
    for key in ("paired_valid_query_count", "plan_rows_changed_count", "qerror_changed_count",
                "mcv_selection_sequence_changed_count", "mcv_estimate_sequence_changed_count"):
        lines.append(f"- {key}: `{paired.get(key, 'unavailable')}`")
    lines.extend(["", "## Reproducibility and resource record", ""])
    lines.append(f"- Run ID: `{summary.get('run_id')}`")
    lines.append(f"- Frozen source commit before Test: `{summary.get('source_commit_before_test')}`")
    lines.append(f"- Protocol SHA-256: `{summary.get('protocol_sha256')}`")
    lines.append(f"- Input identity: `{json.dumps(summary.get('input_identity'), sort_keys=True)}`")
    lines.append(f"- Resource usage: `{json.dumps(summary.get('resource_usage'), sort_keys=True)}`")
    lines.append(f"- External raw query archive: `{json.dumps(analysis.get('raw_query_archive'), sort_keys=True)}`")
    lines.extend(["", "## Interpretation and limits", ""])
    if summary.get("status") != "COMPLETE":
        lines.append("The physical comparison is not complete. Do not interpret one arm as an order effect.")
    elif paired.get("plan_rows_changed_count", 0) and paired.get("qerror_changed_count", 0):
        lines.append("The two fixed OID orders produced different Plan Rows and Test Q-errors with the recorded physical-state checks passing. This supports order sensitivity for this PostgreSQL build, dataset, workload, and these two interventions only.")
    elif paired.get("plan_rows_changed_count", 0):
        lines.append("The two fixed OID orders changed some Plan Rows, while Test Q-error did not change for all paired observations. Report the per-query evidence; this still establishes estimate sensitivity but not Q-error change in this comparison.")
    else:
        lines.append("No Plan Rows difference was observed between these two fixed orders. This does not establish equivalence across other permutations.")
    lines.extend([
        "",
        "MCV sequence changes are association evidence. No claim that a less useful object blocked a more useful object is made without candidate eligibility/ranking/blocker traces.",
        "The complete query-level observations are retained outside Git under the configured ESS_RUNTIME_PARENT; the report stores only compact summaries and a small number of diagnostic cases.",
        "",
    ])
    (attempt_root / "findings.md").write_text("\n".join(lines), encoding="utf-8")
    paired_path = attempt_root / "mechanism-cases.json"
    atomic_json(paired_path, {"note": "descriptive MCV sequence cases only; not proof of blocking or mediation",
                              "cases": paired.get("examples", [])})


def execute(run_id: str | None = None) -> Path:
    protocol = read_protocol()
    source_commit = require_clean_committed_worktree()
    inventory, order_a, order_b = verify_orders(protocol)
    prefix, pg_build = verify_pg_install(protocol)
    preexisting_pg = existing_postgres_processes()
    if preexisting_pg:
        raise Inconclusive(f"refusing to start alongside existing PostgreSQL processes: {preexisting_pg}")
    runtime = issue101.configured_root("ESS_RUNTIME_PARENT")
    run_parent = issue101.runtime_runs("ess-research", 133)
    run_parent.mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-issue133-forest10-{uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run ID must be a safe path component")
    run_root = run_parent / run_id
    if run_root.exists():
        unexpected = {path.name for path in run_root.iterdir()} - {".venv"}
        if unexpected:
            raise FileExistsError(f"refusing to reuse nonempty run root: {sorted(unexpected)}")
    else:
        run_root.mkdir(exist_ok=False)
    for name in ("clusters", "input", "samples", "sql", "logs"):
        (run_root / name).mkdir(exist_ok=True)
    protocol_sha = sha256_file(PROTOCOL_PATH)
    raw_path = run_root / "raw-observations.jsonl.gz"
    manifest: dict[str, Any] = {
        "format": "ess-issue133-minimal-forest10-run-v1",
        "issue": 133,
        "run_id": run_id,
        "status": "INCOMPLETE",
        "phase": "initialization",
        "source_commit_before_test": source_commit,
        "protocol_sha256": protocol_sha,
        "protocol_path": str(PROTOCOL_PATH),
        "input_candidate_universe_sha256": protocol["input_pins"]["candidate_universe_manifest_sha256"],
        "frozen_orders": protocol["order_source"]["orders"],
        "expected_configurations": 2,
        "expected_explain_calls": 20_000,
        "attempted_explain_calls": 0,
        "actual_explain_calls": 0,
        "create_statistics_statements_expected": 90,
        "statistics_target_statements_expected": 90,
        "analyze_runs_expected": 2,
        "parallel_clients_per_arm": PARALLEL_CLIENTS,
        "postgresql_build": pg_build,
        "preexisting_postgres_processes_at_start": preexisting_pg,
        "environment": {},
        "input_identity": None,
        "pretest_comparison": None,
        "arms": [],
        "paired": None,
        "resource_usage": {},
        "failure": None,
    }
    atomic_json(run_root / "run-manifest.json", manifest)
    append_event(run_root / "phase-events.jsonl", "initialization", {
        "source_commit_before_test": source_commit,
        "protocol_sha256": protocol_sha,
        "run_root": str(run_root),
    })

    monitor = ResourceMonitor(run_root, early_seconds=protocol["resource_envelope"]["early_stop_wall_seconds"],
                              hard_seconds=protocol["resource_envelope"]["hard_wall_seconds"],
                              early_bytes=protocol["resource_envelope"]["early_stop_allocated_bytes"],
                              hard_bytes=protocol["resource_envelope"]["hard_allocated_bytes"])
    clusters: dict[str, dict[str, Any]] = {}
    socket_owners: list[tempfile.TemporaryDirectory[str]] = []
    started_at = time.monotonic()
    cpu_started = time.process_time()
    peak_rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    overall_status = "INCOMPLETE"
    environment: dict[str, Any] = {}
    with monitor:
        try:
            manifest["phase"] = "frozen_input_and_environment_preflight"
            atomic_json(run_root / "run-manifest.json", manifest)
            protocol101 = issue101.read_protocol()
            if issue101.sha256_file(issue101.PROTOCOL_PATH) != protocol["pinned_code"]["issue101_protocol_sha256"]:
                raise Inconclusive("Issue #101 protocol hash differs from the frozen pin")
            input_dir = run_root / "input" / DATASET
            csv_path, queries, truths, input_identity = issue101.extract_test_inputs(DATASET, input_dir)
            expected_identity = expected_source_identity(protocol)
            for key, expected in expected_identity.items():
                if input_identity.get(key) != expected:
                    raise Inconclusive(f"Forest10 source identity differs at {key}")
            rendered_identity = query_identity(queries, truths)
            helpers, run_formal, helper_hashes = issue101.load_pinned_helpers(run_root)
            sample, sample_identity = issue101.load_frozen_sample(DATASET, run_root, helpers,
                                                                  protocol101)
            sample_sha = protocol["input_pins"]["forest10_fixed_analyze_sample_sha256"]
            if sample_identity["sha256"] != sample_sha or sha256_file(sample) != sample_sha:
                raise Inconclusive("fixed Forest10 ANALYZE sample hash mismatch")
            source_csv_hash = sha256_file(csv_path)
            if source_csv_hash != protocol["input_pins"]["forest10_full_csv_sha256"]:
                raise Inconclusive("extracted Forest10 full CSV hash mismatch")
            input_identity_record = {
                **input_identity,
                **rendered_identity,
                "source_csv_sha256": source_csv_hash,
                "sample_identity": sample_identity,
                "query_ids_are_ordered_and_unique": True,
            }
            atomic_json(run_root / "input-preflight.json", input_identity_record)
            manifest["input_identity"] = input_identity_record
            manifest["issue99_helper_commit"] = protocol["pinned_code"]["issue99_helper_commit"]
            manifest["issue99_helper_sha256"] = helper_hashes
            manifest["python_version"] = platform.python_version()
            manifest["numpy_version"] = np.__version__
            manifest["cpu_affinity_count"] = len(os.sched_getaffinity(0))
            manifest["available_disk_bytes_at_start"] = shutil.disk_usage(run_root).free
            environment = environment_snapshot(prefix, pg_build, run_root)
            environment["preexisting_postgres_processes_at_start"] = preexisting_pg
            manifest["environment"] = environment
            atomic_json(run_root / "environment.json", environment)
            atomic_json(run_root / "run-manifest.json", manifest)
            append_event(run_root / "phase-events.jsonl", "frozen_input_and_environment_preflight", {
                "test_query_count": len(queries), "csv_sha256": source_csv_hash,
                "sample_sha256": sample_sha, "sql_sha256": rendered_identity["rendered_test_sql_sha256"],
                "memory_available_bytes": environment["memory_bytes_at_preflight"],
                "filesystem_free_bytes": environment["runtime_filesystem_free_bytes_at_preflight"],
            })
            monitor.checkpoint()

            candidates = issue101.candidate_map(DATASET)
            schedules = {ORDERS[0]: order_a, ORDERS[1]: order_b}
            candidate_manifest = json.loads((ROOT / "experiments/all-pairwise-oid-issue133/candidate-universe-manifest.json").read_text())
            source_columns, pg_columns, source_rows, _, table = issue101.issue99.dataset_spec(DATASET)
            if source_rows != 581_012 or table != "public.forest10":
                raise Inconclusive("Issue #99 full Forest10 table contract changed")
            preflight_arms = []
            for order_id in ORDERS:
                monitor.checkpoint()
                arm_setup_started = time.monotonic()
                manifest["phase"] = f"pretest_setup_{order_id}"
                atomic_json(run_root / "run-manifest.json", manifest)
                cluster_root = run_root / "clusters" / order_id
                cluster, socket_owner = create_cluster(prefix, cluster_root, helpers, monitor, order_id)
                clusters[order_id] = cluster
                socket_owners.append(socket_owner)
                cluster["dataset"] = DATASET
                table_load = issue101.configure_source_table(helpers, prefix, cluster, DATASET,
                                                             csv_path, sample)
                if int(table_load["full_source_rows"]) != 581_012:
                    raise Inconclusive(f"{order_id}: full source table import row count mismatch")
                helper_ledger = issue101.run_config(run_formal, prefix, cluster, DATASET,
                                                    candidates, tuple(schedules[order_id]["permutation"]), sample)
                monitor.checkpoint()
                audit = catalog_audit_for_arm(DATASET, order_id, schedules[order_id], candidates,
                                              helper_ledger, helpers, prefix, cluster,
                                              sample, sample_sha, input_identity)
                audit["table_load"] = table_load
                audit["table_load_ddl_sample_replay_analyze_seconds"] = round(time.monotonic() - arm_setup_started, 3)
                audit["analysis_and_ddl_status"] = "PASS"
                audit["analyze_count"] = 1
                audit["create_count"] = 45
                audit["target_count"] = 45
                audit["cluster"] = {key: str(value) if isinstance(value, Path) else value
                                     for key, value in cluster.items() if key not in {"env", "socket_owner", "started"}}
                preflight_arms.append(audit)
                stop_cluster(prefix, cluster)
                append_event(run_root / "phase-events.jsonl", f"pretest_setup_{order_id}", {
                    "status": "PASS", "create_count": 45, "target_count": 45,
                    "analyze_count": 1, "catalog_oid_order_count": len(audit["catalog_oid_order"]),
                })
                manifest["arms"] = preflight_arms
                manifest["phase"] = f"pretest_setup_{order_id}_complete"
                atomic_json(run_root / "run-manifest.json", manifest)
                monitor.checkpoint()

            comparison = compare_pretest_audits(preflight_arms)
            manifest["pretest_comparison"] = comparison
            manifest["phase"] = "both_arms_preflighted_before_test"
            atomic_json(run_root / "catalog-audit.json", {"status": "PASS", "arms": preflight_arms,
                                                               "comparison": comparison})
            atomic_json(run_root / "run-manifest.json", manifest)
            append_event(run_root / "phase-events.jsonl", "both_arms_preflighted_before_test", comparison)
            monitor.checkpoint()

            # Source CSV is reconstructable from the pinned AreCEL archive; keep no second copy after both full-table loads.
            csv_path.unlink(missing_ok=True)
            shutil.rmtree(input_dir, ignore_errors=True)
            rows_by_order: dict[str, list[dict[str, Any]]] = {}
            for arm_index, order_id in enumerate(ORDERS):
                monitor.checkpoint()
                arm = manifest["arms"][arm_index]
                cluster = clusters[order_id]
                manifest["phase"] = f"official_test_{order_id}"
                atomic_json(run_root / "run-manifest.json", manifest)
                order_rows = []
                oid_to_id = {int(oid): candidate_id for oid, candidate_id
                             in arm["oid_to_candidate_id"].items()}
                with start_existing_cluster(prefix, cluster, helpers) as active:
                    current_arm_state(arm, helpers, prefix, active, candidates, sample)
                    sql_root = run_root / "sql" / order_id
                    log_root = run_root / "logs" / order_id
                    plan_started = time.monotonic()
                    observations, plan_batch = bounded_plan_batch(
                        prefix, active, queries, sql_root, oid_to_id, log_root, monitor,
                    )
                    plan_seconds = round(time.monotonic() - plan_started, 3)
                    order_rows = issue105.rows_for_config(
                        DATASET, order_id, schedules[order_id]["permutation"], queries, truths, observations,
                    )
                    raw_member = issue105.append_raw_member(raw_path, order_rows)
                metrics = issue105.metrics_for_rows(order_rows)
                diagnostics_valid = sum(row.get("diagnostics_status") in {"complete", "empty"}
                                        for row in order_rows)
                arm.update({
                    "status": "COMPLETE" if metrics.get("valid_count") == 10_000 and diagnostics_valid == 10_000 else "INCOMPLETE",
                    "catalog_order_status": "PASS",
                    "attempted_explain_calls": plan_batch["attempted_markers"],
                    "query_count": len(order_rows),
                    "diagnostics_valid_count": diagnostics_valid,
                    "diagnostics_status_counts": plan_batch["diagnostics_status_counts"],
                    "plan_batch": plan_batch,
                    "plan_batch_seconds": plan_seconds,
                    "qerror_metrics": metrics,
                    "raw_member": raw_member,
                    "catalog_fingerprint_sha256": sha256_json(audit_signature(arm)["candidate_payloads"]),
                    "ordinary_stats_sha256": arm["ordinary_column_stats"]["sha256"],
                })
                manifest["attempted_explain_calls"] += plan_batch["attempted_markers"]
                manifest["actual_explain_calls"] += plan_batch["attempted_markers"]
                rows_by_order[order_id] = order_rows
                manifest["phase"] = f"official_test_{order_id}_complete"
                atomic_json(run_root / "run-manifest.json", manifest)
                append_event(run_root / "phase-events.jsonl", f"official_test_{order_id}_complete", {
                    "arm_status": arm["status"], "valid_queries": metrics.get("valid_count"),
                    "diagnostics_valid_count": diagnostics_valid,
                    "attempted_markers": plan_batch["attempted_markers"],
                    "plan_batch_seconds": plan_seconds,
                    "raw_member": raw_member,
                })
                if arm["status"] != "COMPLETE":
                    raise Incomplete(f"{order_id}: not all 10,000 Plan Rows and diagnostics are valid")
                monitor.checkpoint()

            paired = analyze_pair(rows_by_order)
            monitor.checkpoint()
            manifest["paired"] = paired
            if manifest["attempted_explain_calls"] != 20_000 or manifest["actual_explain_calls"] != 20_000:
                raise Incomplete("the exact 20,000-call schedule was not completed")
            if paired["status"] != "COMPLETE":
                raise Incomplete("paired query analysis is incomplete")
            if paired["plan_rows_changed_count"] and paired["qerror_changed_count"]:
                outcome = "ORDER_SENSITIVE_ESTIMATES_AND_QERROR_OBSERVED"
            elif paired["plan_rows_changed_count"]:
                outcome = "ORDER_SENSITIVE_ESTIMATES_QERROR_UNCHANGED"
            else:
                outcome = "NO_PLAN_ROWS_DIFFERENCE_OBSERVED"
            manifest["outcome_classification"] = outcome
            manifest["status"] = "COMPLETE"
            manifest["phase"] = "complete"
            overall_status = "COMPLETE"
        except Inconclusive as exc:
            manifest["status"] = "INCONCLUSIVE"
            manifest["failure"] = {"class": type(exc).__name__, "message": str(exc)[:4000],
                                   "phase": manifest.get("phase")}
            overall_status = "INCONCLUSIVE"
        except BaseException as exc:
            before_test = str(manifest.get("phase", "")).startswith("pretest_setup_") or manifest.get("phase") == "both_arms_preflighted_before_test"
            manifest["status"] = "INCOMPLETE" if monitor.stop_event.is_set() or not before_test else "INCONCLUSIVE"
            manifest["failure"] = {"class": type(exc).__name__, "message": str(exc)[:4000],
                                   "phase": manifest.get("phase")}
            overall_status = manifest["status"]
        finally:
            for cluster in reversed(list(clusters.values())):
                try:
                    stop_cluster(prefix, cluster)
                except Exception as stop_exc:
                    manifest.setdefault("cleanup_errors", []).append(str(stop_exc)[:1000])
            for socket_owner in socket_owners:
                socket_owner.cleanup()
            elapsed = time.monotonic() - started_at
            usage = resource.getrusage(resource.RUSAGE_SELF)
            manifest["resource_usage"] = {
                "elapsed_wall_seconds": round(elapsed, 3),
                "runner_process_cpu_seconds": round(time.process_time() - cpu_started, 3),
                "runner_peak_rss_kib": int(max(peak_rss_before, usage.ru_maxrss)),
                "peak_run_directory_allocated_bytes": monitor.peak_bytes,
                "final_run_directory_allocated_bytes": allocated_bytes(run_root),
                "minimum_global_filesystem_free_bytes": monitor.minimum_global_free,
                "early_or_hard_stop_reason": monitor.stop_reason,
                "cpu_note": "runner process CPU/RSS only; PostgreSQL server/backend CPU is not separately attributed",
            }
            manifest["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            manifest["raw_observations_path"] = str(raw_path) if raw_path.exists() else None
            if raw_path.exists():
                manifest["raw_observations_bytes"] = raw_path.stat().st_size
                manifest["raw_observations_sha256"] = sha256_file(raw_path)
            manifest["protocol_sha256"] = protocol_sha
            manifest["source_commit_before_test"] = source_commit
            if not manifest.get("arms"):
                manifest["arms"] = []
            atomic_json(run_root / "run-manifest.json", manifest)
            if environment:
                try:
                    publish_git_artifacts(manifest, environment, raw_path)
                except Exception as publish_exc:
                    manifest["artifact_publish_error"] = str(publish_exc)[:1000]
                    atomic_json(run_root / "run-manifest.json", manifest)
            append_event(run_root / "phase-events.jsonl", "finalized", {
                "status": manifest.get("status"),
                "attempted_explain_calls": manifest.get("attempted_explain_calls"),
                "resource_usage": manifest.get("resource_usage"),
            })
    return run_root


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    run_root = execute(args.run_id)
    manifest = json.loads((run_root / "run-manifest.json").read_text())
    print(json.dumps({key: manifest.get(key) for key in (
        "run_id", "status", "outcome_classification", "source_commit_before_test",
        "attempted_explain_calls", "actual_explain_calls", "resource_usage", "failure",
        "raw_observations_sha256")}, ensure_ascii=False, sort_keys=True))
    return 0 if manifest.get("status") == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
