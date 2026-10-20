#!/usr/bin/env python3
"""Stage 2B Gate A input and PostgreSQL-readiness verification.

This module deliberately stops at infrastructure readiness. It never selects
held-out test rows, calibrates a model, or reports Empty/Nominal/PESS outcomes.
The archive-first AreCEL API owns all derived inputs and cleans its ``derived``
directory when the consuming context exits.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from ess_research.arecel import prepare
from ess_research.arecel.archive import PreparedDataset
from ess_research.task_paths import ConfigurationError, configured_root

EXPECTED_PG_COMMIT = "23c7c2fdd4bfb561f3257d947fee956a2999fdb6"
EXPECTED_ARCHIVE_SHA256 = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
EXPECTED_PG_VERSION = "16.14"
DATASETS = ("forest10", "census13")
SUPPORTED_OPERATORS = {"=", "<", "<=", ">", ">=", "[]"}
TRACE_NUMERIC = re.compile(r"ESS_MCV_NUMERIC_TRACE: (?P<body>.*)")
TRACE_SELECTED = re.compile(r"ESS_MCV_TRACE: (?P<body>.*)")
KEY_VALUE = re.compile(r"(\w+)=((?:\"[^\"]*\")|(?:[^ ]+))")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    """Write evidence once, without following or replacing an existing path."""

    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
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
            path.unlink(missing_ok=True)
        raise


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def parse_key_values(body: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2).strip('"')
        for match in KEY_VALUE.finditer(body)
    }


def parse_schema_sql(path: Path) -> dict[str, str]:
    """Parse the small API-generated CREATE TABLE contract."""

    pattern = re.compile(r'^"(?P<column>[^"]+)"\s+(?P<type>.+)$')
    columns: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().rstrip(",")
        match = pattern.match(line)
        if match:
            columns[match.group("column")] = match.group("type").strip()
    if not columns:
        raise ValueError(f"no catalog columns found in {path}")
    return columns


def query_records(root: Path, split: str) -> tuple[dict[str, Any], dict[str, Any]]:
    workload = load_json(root / split / "workload.json")
    truth = load_json(root / split / "truth.json")
    if workload.get("format") != "arecel-prepared-v1" or truth.get("format") != "arecel-prepared-v1":
        raise ValueError(f"{split}: unexpected prepared format")
    queries = workload.get("queries")
    labels = truth.get("queries")
    if not isinstance(queries, list) or not isinstance(labels, list) or len(queries) != len(labels):
        raise ValueError(f"{split}: workload/truth length mismatch")
    return workload, truth


def query_columns(query: dict[str, Any]) -> set[str]:
    return {predicate["column"] for predicate in query.get("predicates", [])}


def select_validation_queries(
    queries: list[dict[str, Any]], spec: dict[str, Any], ledger: list[dict[str, Any]]
) -> dict[str, Any]:
    """Select deterministic, validation-only probes without reading truth values."""

    control = next((query for query in queries if len(query_columns(query)) >= 2), None)
    positive_by_name = {
        row["statistic_name"]: row for row in ledger if row["mcv_payload_present"]
    }
    coverage = None
    for candidate in spec["candidates"]:
        catalog = positive_by_name.get(candidate["statistic_name"])
        if catalog is None:
            continue
        query = next(
            (
                query
                for query in queries
                if set(candidate["source_columns"]) <= query_columns(query)
            ),
            None,
        )
        if query is not None:
            coverage = {
                "candidate_id": candidate["id"],
                "statistic_name": candidate["statistic_name"],
                "query": query,
                "catalog": catalog,
            }
            break
    return {"control": control, "mcv_coverage": coverage}


def validate_cluster_identity(fields: list[str], pgdata: Path, port: int) -> None:
    if (
        len(fields) != 4
        or Path(fields[0]).resolve() != pgdata.resolve()
        or fields[1] != str(port)
        or fields[2] != "postgres"
        or EXPECTED_PG_VERSION not in fields[3]
    ):
        raise RuntimeError(f"Issue-owned cluster identity mismatch: {'|'.join(fields)!r}")


def evaluate_trace(
    trace_lines: list[str],
    ledger: list[dict[str, Any]],
    *,
    label: str,
    query_id: str,
    expected_statistic_name: str | None = None,
) -> dict[str, Any]:
    numeric = []
    selected = []
    for line in trace_lines:
        if match := TRACE_NUMERIC.search(line):
            numeric.append(parse_key_values(match.group("body")))
        if match := TRACE_SELECTED.search(line):
            selected.append(parse_key_values(match.group("body")))

    final = [item for item in numeric if "nrows_preclamp" in item]
    numeric_selected_oids = [
        item.get("selected_stat_oid") for item in numeric if item.get("selected_stat_oid")
    ]
    selected_oids = []
    for record in [*selected, *numeric]:
        selected_oid = record.get("selected_stat_oid")
        if selected_oid and selected_oid not in selected_oids:
            selected_oids.append(selected_oid)
    claimed_clause_indices = []
    for record in selected:
        clause_index = record.get("claimed_clause_index")
        if clause_index and clause_index not in claimed_clause_indices:
            claimed_clause_indices.append(clause_index)

    catalog_oids = {str(item["oid"]): item for item in ledger}
    unmapped = [oid for oid in selected_oids if oid not in catalog_oids]
    selected_names = [catalog_oids[oid]["statistic_name"] for oid in selected_oids if oid in catalog_oids]
    selected_without_payload = [
        oid
        for oid in selected_oids
        if oid in catalog_oids and not catalog_oids[oid]["mcv_payload_present"]
    ]
    errors = []
    if len(final) != 1 or float(final[0]["nrows_preclamp"]) <= 0:
        errors.append("probe did not produce exactly one positive pre-clamp trace")
    if unmapped:
        errors.append(f"probe selected unmapped statistic OIDs: {unmapped}")
    if selected_without_payload:
        errors.append(
            f"probe selected statistics without positive MCV payload: {selected_without_payload}"
        )
    if expected_statistic_name is not None:
        expected = next(
            (item for item in ledger if item["statistic_name"] == expected_statistic_name),
            None,
        )
        if expected is None or not expected["mcv_payload_present"]:
            errors.append("expected selected statistic lacks a positive MCV payload")
        elif expected_statistic_name not in selected_names:
            errors.append("validation query did not select the expected positive-payload statistic")

    if not selected_oids:
        claimed_clause_status = "NOT_APPLICABLE"
        claimed_clause_missing_oids = []
    else:
        claimed_oids = {
            record.get("selected_stat_oid")
            for record in selected
            if record.get("selected_stat_oid") and record.get("claimed_clause_index")
        }
        claimed_clause_missing_oids = [oid for oid in selected_oids if oid not in claimed_oids]
        claimed_clause_status = "VERIFIED" if not claimed_clause_missing_oids else "UNVERIFIED"

    return {
        "label": label,
        "query_id": query_id,
        "status": "VERIFIED" if not errors else "INCOMPATIBLE",
        "errors": errors,
        "trace_lines": trace_lines,
        "numeric": numeric,
        "selected_trace_records": selected,
        "selected_stat_oids": selected_oids,
        "numeric_selected_stat_oids": numeric_selected_oids,
        "selected_stat_names": selected_names,
        "unmapped_selected_oids": unmapped,
        "claimed_clause_coverage": {
            "status": claimed_clause_status,
            "claimed_clause_indices": claimed_clause_indices,
            "records": selected,
            "missing_selected_stat_oids": claimed_clause_missing_oids,
        },
        "positive_preclamp": final[0]["nrows_preclamp"] if len(final) == 1 else None,
    }


def aggregate_claimed_clause_coverage(probes: list[dict[str, Any]]) -> str:
    """Require claims for every selected MCV resource; empty controls are N/A."""

    applicable = [
        probe
        for probe in probes
        if probe.get("claimed_clause_coverage", {}).get("status") != "NOT_APPLICABLE"
    ]
    if not applicable:
        return "UNVERIFIED"
    return (
        "VERIFIED"
        if all(
            probe.get("claimed_clause_coverage", {}).get("status") == "VERIFIED"
            for probe in applicable
        )
        else "UNVERIFIED"
    )


def validate_prepared_dataset(
    prepared: PreparedDataset, protocol: dict[str, Any], dataset: str
) -> dict[str, Any]:
    """Validate generated data without using test truth for selection."""

    spec = protocol["datasets"][dataset]
    result: dict[str, Any] = {
        "dataset": dataset,
        "status": "VERIFIED",
        "run_root": str(prepared.run_root),
        "checks": {},
        "errors": [],
    }
    try:
        manifest = prepared.manifest
        if manifest.get("archive_sha256") != EXPECTED_ARCHIVE_SHA256:
            raise ValueError("prepared manifest archive SHA-256 mismatch")
        if manifest.get("upstream_commit") != protocol["etl_contract"]["upstream_commit"]:
            raise ValueError("prepared manifest upstream commit mismatch")
        if manifest.get("format") != "arecel-preparation-v1":
            raise ValueError("unexpected prepare manifest format")
        expected_splits = spec["split_counts"]
        if manifest.get("splits") != expected_splits:
            raise ValueError(f"split counts mismatch: {manifest.get('splits')} != {expected_splits}")

        table = prepared.csv
        schema = parse_schema_sql(prepared.dataset_root / "schema.sql")
        if list(schema) != spec["catalog_columns"]:
            raise ValueError(f"catalog column order mismatch: {list(schema)} != {spec['catalog_columns']}")
        with table.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, None)
            rows = sum(1 for _ in reader)
        if header != spec["source_columns"]:
            raise ValueError("source CSV header mismatch")
        if rows != spec["source_rows"]:
            raise ValueError(f"source row count mismatch: {rows} != {spec['source_rows']}")

        candidate_checks = []
        for candidate in spec["candidates"]:
            source_columns = candidate["source_columns"]
            catalog_columns = candidate["catalog_columns"]
            if len(source_columns) != 2 or len(catalog_columns) != 2:
                raise ValueError(f"candidate {candidate['id']} is not pairwise")
            for source, catalog, expected_type in zip(
                source_columns, catalog_columns, candidate["postgres_types"], strict=True
            ):
                if source not in spec["source_columns"] or catalog not in schema:
                    raise ValueError(f"candidate {candidate['id']} has an unknown column")
                if schema[catalog] != expected_type:
                    raise ValueError(f"candidate {candidate['id']} type crosswalk mismatch")
            candidate_checks.append(
                {
                    "id": candidate["id"],
                    "statistic_name": candidate["statistic_name"],
                    "source_columns": source_columns,
                    "catalog_columns": catalog_columns,
                    "constructible": True,
                }
            )

        split_checks: dict[str, Any] = {}
        for split, expected_count in expected_splits.items():
            workload, truth = query_records(prepared.dataset_root, split)
            queries = workload["queries"]
            labels = truth["queries"]
            if len(queries) != expected_count or len(labels) != expected_count:
                raise ValueError(f"{split}: expected {expected_count} records")
            seen_ids: set[str] = set()
            eligible_by_shape = 0
            for index, (query, label) in enumerate(zip(queries, labels, strict=True)):
                expected_id = f"arecel:{dataset}:{split}:{index:06d}"
                if query.get("query_id") != expected_id or label.get("query_id") != expected_id:
                    raise ValueError(f"{split}: unstable query ID at index {index}")
                if query.get("source_index") != index or label.get("source_index") != index:
                    raise ValueError(f"{split}: source-index mismatch at index {index}")
                if query.get("query_id") in seen_ids:
                    raise ValueError(f"{split}: duplicate query ID")
                seen_ids.add(query["query_id"])
                if "true_cardinality" in query or "source_selectivity" in query:
                    raise ValueError(f"{split}: truth leakage in workload")
                predicates = query.get("predicates")
                if not isinstance(predicates, list) or not predicates:
                    raise ValueError(f"{split}: missing predicates")
                columns = set()
                for predicate in predicates:
                    if not isinstance(predicate, dict) or predicate.get("operator") not in SUPPORTED_OPERATORS:
                        raise ValueError(f"{split}: unsupported predicate representation")
                    column = predicate.get("column")
                    if column not in spec["source_columns"]:
                        raise ValueError(f"{split}: unknown source predicate column")
                    columns.add(column)
                if len(columns) >= 2:
                    eligible_by_shape += 1
                if not isinstance(label.get("true_cardinality"), int) or label["true_cardinality"] < 0:
                    raise ValueError(f"{split}: invalid truth type")
                if query.get("sql", "").split(" WHERE ", 1)[0] != f"SELECT * FROM {spec['relation']}":
                    raise ValueError(f"{split}: adapted SQL relation mismatch")
            split_checks[split] = {
                "records": len(queries),
                "unique_query_ids": len(seen_ids) == len(queries),
                "shape_eligible_count": eligible_by_shape,
                "truth_values_not_used_for_selection": True,
            }

        result["checks"] = {
            "archive_sha256": manifest["archive_sha256"],
            "upstream_commit": manifest["upstream_commit"],
            "table": {"sha256": sha256_file(table), "rows": rows, "header": header},
            "schema": schema,
            "candidate_crosswalk": candidate_checks,
            "splits": split_checks,
            "legacy_stage1a_ids_excluded": True,
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result["status"] = "INCOMPATIBLE"
        result["errors"].append(str(exc))
    return result


def audit_pg_source(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_dir():
        return {"status": "BLOCKED", "reason": "pinned PG source checkout was not supplied"}
    try:
        head = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        extended = path / "src/backend/statistics/extended_stats.c"
        costsize = path / "src/backend/optimizer/path/costsize.c"
        config_log = path / "config.log"
        extended_text = extended.read_text(encoding="utf-8")
        markers = {
            "ESS_MCV_TRACE": "ESS_MCV_TRACE" in extended_text,
            "ESS_MCV_NUMERIC_TRACE": "ESS_MCV_NUMERIC_TRACE" in extended_text
            and "ESS_MCV_NUMERIC_TRACE" in costsize.read_text(encoding="utf-8"),
            "configure_numeric_flag": config_log.is_file()
            and "CFLAGS=-O2 -g -DESS_MCV_NUMERIC_TRACE"
            in config_log.read_text(encoding="utf-8", errors="replace"),
        }
        status = "VERIFIED" if head == EXPECTED_PG_COMMIT and not dirty and all(markers.values()) else "INCOMPATIBLE"
        return {
            "status": status,
            "head": head,
            "expected_head": EXPECTED_PG_COMMIT,
            "worktree_clean": not bool(dirty),
            "trace_source_markers": markers,
        }
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"status": "INCOMPATIBLE", "reason": str(exc)}


def _binary_version(path: Path) -> str:
    result = subprocess.run([str(path), "--version"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{path.name} --version failed: {result.stderr.strip()}")
    return result.stdout.strip()


def audit_pg_binary(prefix: Path | None, manifest_path: Path | None) -> dict[str, Any]:
    if prefix is None or manifest_path is None:
        return {"status": "BLOCKED", "reason": "--pg-prefix and --pg-build-manifest are required"}
    try:
        manifest = load_json(manifest_path)
        if manifest.get("pg_source_commit") != EXPECTED_PG_COMMIT or not manifest.get("pg_source_worktree_clean"):
            raise ValueError("binary manifest lacks approved clean PG source provenance")
        expected_hashes = manifest.get("binary_sha256")
        names = ("postgres", "initdb", "pg_ctl", "psql", "pg_config")
        if not isinstance(expected_hashes, dict):
            raise ValueError("binary manifest has no binary_sha256 map")
        actual_hashes = {}
        versions = {}
        for name in names:
            path = prefix / "bin" / name
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"missing or symlinked PG binary: {path}")
            actual_hashes[name] = sha256_file(path)
            versions[name] = _binary_version(path)
            if actual_hashes[name] != expected_hashes.get(name):
                raise ValueError(f"binary SHA-256 mismatch: {name}")
        if not versions["postgres"].endswith(EXPECTED_PG_VERSION) or not versions["pg_config"].endswith(EXPECTED_PG_VERSION):
            raise ValueError("running PostgreSQL binaries are not 16.14")
        return {
            "status": "VERIFIED",
            "prefix": str(prefix),
            "manifest": str(manifest_path),
            "manifest_format": manifest.get("format"),
            "binary_sha256": actual_hashes,
            "versions": versions,
            "source_commit": manifest["pg_source_commit"],
            "source_worktree_clean": manifest["pg_source_worktree_clean"],
        }
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return {"status": "INCOMPATIBLE", "reason": str(exc)}


def run_command(
    command: list[str],
    *,
    env: dict[str, str],
    input_text: str | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed: {shlex.join(command)}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def psql(
    prefix: Path,
    socket_dir: Path,
    port: int,
    sql: str,
    env: dict[str, str],
    *,
    tuples: bool = False,
    timeout: int = 180,
) -> str:
    command = [
        str(prefix / "bin/psql"),
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        str(socket_dir),
        "-p",
        str(port),
        "-d",
        "postgres",
    ]
    if tuples:
        command += ["-At", "-F", "|"]
    command += ["-c", sql]
    return run_command(command, env=env, timeout=timeout).stdout


def sample_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    position = 0

    def take(size: int) -> bytes:
        nonlocal position
        value = data[position : position + size]
        if len(value) != size:
            raise ValueError("truncated fixed sample")
        position += size
        return value

    def u32() -> int:
        return int.from_bytes(take(4), "little")

    def string() -> str:
        return take(u32()).decode("utf-8")

    if take(8) != b"ESSANL01":
        raise ValueError("unexpected fixed sample magic")
    version = u32()
    server_num = u32()
    server = string()
    blcksz, alignof, tuple_header, tuple_size, item_pointer = (u32() for _ in range(5))
    relation_oid, filenode, pages = (u32() for _ in range(3))
    relation_identity = string()
    natts, target, tuples = (u32() for _ in range(3))
    return {
        "format_version": version,
        "server_version_num": server_num,
        "server_version": server,
        "blcksz": blcksz,
        "alignof": alignof,
        "tuple_header_size": tuple_header,
        "tuple_size": tuple_size,
        "item_pointer_size": item_pointer,
        "relation_oid": relation_oid,
        "relation_filenode": filenode,
        "relation_pages": pages,
        "relation_identity": relation_identity,
        "natts": natts,
        "sample_target": target,
        "tuple_count": tuples,
        "file_bytes": len(data),
    }


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def owned_cluster(prefix: Path, root: Path, env: dict[str, str]) -> Iterator[dict[str, Any]]:
    pgdata = root / "pgdata"
    socket_dir = root / "socket"
    log_path = root / "server.log"
    if pgdata.exists() or socket_dir.exists():
        raise RuntimeError("refusing to reuse existing Issue #48 cluster path")
    root.mkdir(parents=True, exist_ok=False)
    socket_dir.mkdir()
    port = reserve_port()
    cluster_env = dict(env, LD_LIBRARY_PATH=str(prefix / "lib"))
    started = False
    try:
        run_command(
            [str(prefix / "bin/initdb"), "-D", str(pgdata), "--no-locale", "--encoding=UTF8", "-U", "wqts"],
            env=cluster_env,
            timeout=180,
        )
        options = f"-p {port} -k {socket_dir} -c log_min_messages=debug1 -c log_line_prefix='%m [%p] %u@%d app=%a '"
        run_command(
            [str(prefix / "bin/pg_ctl"), "-D", str(pgdata), "-l", str(log_path), "-o", options, "-w", "start"],
            env=cluster_env,
            timeout=120,
        )
        started = True
        identity = psql(
            prefix,
            socket_dir,
            port,
            "SELECT current_setting('data_directory'), current_setting('port'), current_database(), version();",
            cluster_env,
            tuples=True,
        )
        fields = identity.strip().split("|")
        validate_cluster_identity(fields, pgdata, port)
        yield {"pgdata": pgdata, "socket_dir": socket_dir, "port": port, "server_log": log_path, "identity": fields}
    finally:
        if started:
            run_command(
                [str(prefix / "bin/pg_ctl"), "-D", str(pgdata), "-m", "fast", "-w", "stop"],
                env=cluster_env,
                timeout=120,
            )


def wait_log(path: Path, offset: int, marker: str) -> list[str]:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        with path.open("rb") as stream:
            stream.seek(offset)
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        if any(marker in line for line in lines):
            return [line for line in lines if marker in line]
        time.sleep(0.05)
    raise RuntimeError(f"trace marker did not appear: {marker}")


def run_dataset_probe(prepared: PreparedDataset, protocol: dict[str, Any], prefix: Path) -> dict[str, Any]:
    dataset = prepared.manifest["dataset"]
    spec = protocol["datasets"][dataset]
    result: dict[str, Any] = {"dataset": dataset, "status": "VERIFIED", "checks": {}, "errors": []}
    try:
        with owned_cluster(prefix, prepared.run_root / "pg", os.environ.copy()) as cluster:
            env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
            table = f"public.{dataset}"
            psql(prefix, cluster["socket_dir"], cluster["port"], (prepared.dataset_root / "schema.sql").read_text(encoding="utf-8"), env)
            csv_path = str(prepared.csv).replace("'", "''")
            psql(prefix, cluster["socket_dir"], cluster["port"], f"\\copy {table} FROM '{csv_path}' WITH (FORMAT csv, HEADER true);", env, timeout=600)
            count = psql(prefix, cluster["socket_dir"], cluster["port"], f"SELECT count(*) FROM {table};", env, tuples=True).strip()
            if count != str(spec["source_rows"]):
                raise RuntimeError(f"imported row count mismatch: {count}")
            for column in spec["catalog_columns"]:
                psql(prefix, cluster["socket_dir"], cluster["port"], f'ALTER TABLE {table} ALTER COLUMN "{column}" SET STATISTICS 300;', env)

            sample = prepared.run_root / "results" / f"{dataset}.fixed-sample"
            psql(prefix, cluster["socket_dir"], cluster["port"], f"SET ess.analyze_sample_export = '{str(sample).replace(chr(39), chr(39) * 2)}'; ANALYZE {table}; RESET ess.analyze_sample_export;", env, timeout=600)
            header = sample_header(sample)
            sample_sha = sha256_file(sample)
            if header["server_version"] != EXPECTED_PG_VERSION or header["natts"] != len(spec["catalog_columns"]):
                raise RuntimeError("fixed sample server version or attribute count mismatch")

            stat_names = []
            for candidate in spec["candidates"]:
                stat_name = candidate["statistic_name"]
                stat_names.append(stat_name)
                columns = ", ".join(f'"{column}"' for column in candidate["catalog_columns"])
                psql(prefix, cluster["socket_dir"], cluster["port"], f'CREATE STATISTICS "{stat_name}" (mcv) ON {columns} FROM {table}; ALTER STATISTICS "{stat_name}" SET STATISTICS 300;', env)
            psql(prefix, cluster["socket_dir"], cluster["port"], f"SET ess.analyze_sample_import = '{str(sample).replace(chr(39), chr(39) * 2)}'; ANALYZE {table}; RESET ess.analyze_sample_import;", env, timeout=600)

            names = ", ".join("'" + name.replace("'", "''") + "'" for name in stat_names)
            rows = psql(prefix, cluster["socket_dir"], cluster["port"], "SELECT s.stxname, s.oid, s.stxkeys::text, s.stxstattarget, (d.stxdmcv IS NOT NULL)::int, CASE WHEN d.stxdmcv IS NULL THEN 0 ELSE (SELECT count(*) FROM pg_mcv_list_items(d.stxdmcv)) END FROM pg_statistic_ext s LEFT JOIN pg_statistic_ext_data d ON d.stxoid=s.oid AND NOT d.stxdinherit WHERE s.stxname IN (" + names + ") ORDER BY s.oid;", env, tuples=True).splitlines()
            ledger = []
            for line in rows:
                fields = line.split("|")
                if len(fields) != 6:
                    raise RuntimeError(f"unexpected catalog ledger row: {line!r}")
                ledger.append({"statistic_name": fields[0], "oid": int(fields[1]), "stxkeys": fields[2], "statistics_target": int(fields[3]), "mcv_payload_present": bool(int(fields[4])), "mcv_item_count": int(fields[5])})
            if {row["statistic_name"] for row in ledger} != set(stat_names):
                raise RuntimeError("not all requested statistics appeared in catalog")

            valid_workload, _ = query_records(prepared.dataset_root, "valid")
            selected_queries = select_validation_queries(valid_workload["queries"], spec, ledger)
            control = selected_queries["control"]
            if control is None:
                raise RuntimeError("no predeclared shape-eligible valid control query")

            probe_specs = [
                {"label": "shape_control", "query": control, "expected_statistic_name": None}
            ]
            coverage = selected_queries["mcv_coverage"]
            if coverage is not None:
                probe_specs.append(
                    {
                        "label": "positive_mcv_coverage",
                        "query": coverage["query"],
                        "expected_statistic_name": coverage["statistic_name"],
                    }
                )

            probe_results = []
            for probe_spec in probe_specs:
                query = probe_spec["query"]
                marker = f"issue48-gate-a-{probe_spec['label']}-{dataset}-{query['query_id'].rsplit(':', 1)[-1]}"
                before = cluster["server_log"].stat().st_size if cluster["server_log"].exists() else 0
                psql(
                    prefix,
                    cluster["socket_dir"],
                    cluster["port"],
                    "SET client_min_messages=debug1; SET plan_cache_mode=force_custom_plan; SET max_parallel_workers_per_gather=0; EXPLAIN (FORMAT JSON, SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE "
                    + marker
                    + " */ "
                    + query["sql"],
                    env,
                )
                trace_lines = wait_log(cluster["server_log"], before, marker)
                probe = evaluate_trace(
                    trace_lines,
                    ledger,
                    label=probe_spec["label"],
                    query_id=query["query_id"],
                    expected_statistic_name=probe_spec["expected_statistic_name"],
                )
                if probe["status"] != "VERIFIED":
                    raise RuntimeError("; ".join(probe["errors"]))
                probe_results.append(probe)

            mcv_coverage = (
                {
                    "status": "VERIFIED",
                    "candidate_id": coverage["candidate_id"],
                    "statistic_name": coverage["statistic_name"],
                    "query_id": coverage["query"]["query_id"],
                }
                if coverage is not None
                else {
                    "status": "UNVERIFIED",
                    "reason": "no positive-payload candidate had a source-order validation query",
                }
            )
            claimed_clause_status = aggregate_claimed_clause_coverage(probe_results)
            result["checks"] = {
                "cluster": {"pgdata": str(cluster["pgdata"]), "socket": str(cluster["socket_dir"]), "port": cluster["port"], "identity": cluster["identity"]},
                "import": {"table": table, "rows": int(count)},
                "fixed_sample": {"path": str(sample), "sha256": sample_sha, "bytes": sample.stat().st_size, "header": header, "replayed_before_statistics_analyze": True},
                "catalog": ledger,
                "validation_probe_selection": {
                    "split": "valid",
                    "truth_used_for_selection": False,
                    "control_query_id": control["query_id"],
                    "mcv_coverage": mcv_coverage,
                },
                "probes": probe_results,
                "trace_coverage": {
                    "numeric_preclamp": "VERIFIED",
                    "selected_oid_mapping": "VERIFIED",
                    "claimed_clause_indices": claimed_clause_status,
                },
            }
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        result["status"] = "INCOMPATIBLE"
        result["errors"].append(str(exc))
    return result


def compute_overall_status(
    inputs: list[dict[str, Any]],
    source: dict[str, Any],
    binary: dict[str, Any],
    probes: list[dict[str, Any]],
    claimed_clause_coverage: str,
) -> str:
    if len(inputs) < 2 or any(item.get("status") != "VERIFIED" for item in inputs):
        return "BLOCKED"
    if source.get("status") != "VERIFIED" or binary.get("status") != "VERIFIED":
        return "BLOCKED"
    if len(probes) != len(inputs) or any(item.get("status") != "VERIFIED" for item in probes):
        return "BLOCKED"
    if claimed_clause_coverage != "VERIFIED":
        return "BLOCKED"
    return "GATE_A_READY"


def collect_dataset_inputs(
    protocol: dict[str, Any], *, pg_runtime_allowed: bool, pg_prefix: Path | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    for dataset in DATASETS:
        try:
            with prepare(issue=48, dataset=dataset) as prepared:
                input_result = validate_prepared_dataset(prepared, protocol, dataset)
                inputs.append(input_result)
                if (
                    pg_runtime_allowed
                    and pg_prefix is not None
                    and input_result["status"] == "VERIFIED"
                ):
                    probes.append(run_dataset_probe(prepared, protocol, pg_prefix))
        except (ConfigurationError, OSError, ValueError, RuntimeError) as exc:
            inputs.append({"dataset": dataset, "status": "BLOCKED", "errors": [str(exc)]})
    return inputs, probes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol-v3.json"))
    parser.add_argument("--pg-source", type=Path)
    parser.add_argument("--pg-prefix", type=Path)
    parser.add_argument("--pg-build-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # These checks intentionally happen before any archive preparation.
    data_root = configured_root("ESS_DATA_ROOT")
    runtime_parent = configured_root("ESS_RUNTIME_PARENT")
    protocol = load_json(args.protocol)
    if protocol.get("status") != "FROZEN_BEFORE_GATE_A_OUTCOME_COLLECTION_V3":
        raise SystemExit("protocol-v3 is not the frozen outcome-free contract")

    source = audit_pg_source(args.pg_source.expanduser().resolve() if args.pg_source else None)
    binary = audit_pg_binary(args.pg_prefix.expanduser().resolve() if args.pg_prefix else None, args.pg_build_manifest.expanduser().resolve() if args.pg_build_manifest else None)
    pg_runtime_allowed = source.get("status") == "VERIFIED" and binary.get("status") == "VERIFIED"
    inputs, probes = collect_dataset_inputs(
        protocol,
        pg_runtime_allowed=pg_runtime_allowed,
        pg_prefix=args.pg_prefix.expanduser().resolve() if args.pg_prefix else None,
    )
    claimed_clause_coverage = (
        "VERIFIED"
        if probes
        and all(
            probe.get("checks", {}).get("trace_coverage", {}).get("claimed_clause_indices")
            == "VERIFIED"
            for probe in probes
        )
        else "UNVERIFIED"
    )
    result = {
        "format": "ess-issue48-stage2b-gate-audit-v4",
        "evidence_label": "experimentally_observed_gate_a_readiness_only",
        "protocol_sha256": sha256_file(args.protocol),
        "data_root": str(data_root),
        "runtime_parent": str(runtime_parent),
        "datasets": inputs,
        "postgresql_source": source,
        "postgresql_binary": binary,
        "probes": probes,
        "trace_coverage": {
            "numeric_preclamp": "VERIFIED" if probes else "UNVERIFIED",
            "selected_oid_mapping": "VERIFIED" if probes else "UNVERIFIED",
            "claimed_clause_indices": claimed_clause_coverage,
        },
        "overall_status": compute_overall_status(inputs, source, binary, probes, claimed_clause_coverage),
        "scientific_boundary": [
            "No held-out test truth or estimate was used for model calibration, candidate selection, eligibility filtering, or cohort selection.",
            "The smoke probe uses a deterministic validation-split query-shape rule and is not a held-out outcome.",
            "GATE_A_READY means infrastructure readiness only; it is not a Stage 2B outcome PASS or a PostgreSQL containment guarantee.",
            "The claimed-clause trace requirement is independent of numeric tracing and selected-OID mapping; if it is UNVERIFIED, overall readiness is BLOCKED.",
        ],
    }
    write_exclusive_json(args.output, result)
    print(json.dumps({"output": str(args.output), "overall_status": result["overall_status"], "datasets": {item["dataset"]: item["status"] for item in inputs}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
