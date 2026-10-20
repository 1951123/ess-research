"""Collect paired held-out PostgreSQL observations for Issue #38.

The protocol and all input hashes are checked before any query is measured.
The runner records raw observations outside Git under the Issue-owned runtime
root.  It never times queries and never changes the frozen resource sets.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

NUMERIC_TRACE = re.compile(r"ESS_MCV_NUMERIC_TRACE: (?P<body>.*)")
SELECTED_TRACE = re.compile(r"ESS_MCV_TRACE: (?P<body>.*)")
KEY_VALUE = re.compile(r"(\w+)=((?:\"[^\"]*\")|(?:[^ ]+))")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {shlex.join(command)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result.stdout.strip()


def psql(args: argparse.Namespace, sql: str) -> str:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.lib_dir)
    command = [
        str(args.pg_bin / "psql"),
        "-h", str(args.socket_dir), "-p", str(args.port), "-d", args.database,
        "-v", "ON_ERROR_STOP=1", "-X", "-At", "-F", "|", "-c", sql,
    ]
    return run_command(command, env=env)


def parse_key_values(body: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip('"') for match in KEY_VALUE.finditer(body)}


def parse_sample_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    position = 0

    def take(size: int) -> bytes:
        nonlocal position
        value = data[position : position + size]
        if len(value) != size:
            raise ValueError("truncated sample header")
        position += size
        return value

    def u32() -> int:
        return int.from_bytes(take(4), "little")

    def string() -> str:
        size = u32()
        return take(size).decode("utf-8")

    if take(8) != b"ESSANL01":
        raise ValueError("unexpected sample magic")
    format_version = u32()
    server_version_num = u32()
    server_version = string()
    blcksz, alignof, tuple_header_size, tuple_size, item_pointer_size = (u32() for _ in range(5))
    relation_oid = u32()
    relation_filenode = u32()
    relation_pages = u32()
    relation_identity = string()
    natts = u32()
    sample_target = u32()
    tuple_count = u32()
    return {
        "format_version": format_version,
        "server_version_num": server_version_num,
        "server_version": server_version,
        "blcksz": blcksz,
        "alignof": alignof,
        "tuple_header_size": tuple_header_size,
        "tuple_size": tuple_size,
        "item_pointer_size": item_pointer_size,
        "relation_oid": relation_oid,
        "relation_filenode": relation_filenode,
        "relation_pages": relation_pages,
        "relation_identity": relation_identity,
        "natts": natts,
        "sample_target": sample_target,
        "tuple_count": tuple_count,
        "file_bytes": len(data),
    }


def load_protocol(path: Path) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol["status"] != "FROZEN_BEFORE_POSTGRESQL_HELDOUT_OUTCOME_COLLECTION":
        raise ValueError("protocol is not the frozen pre-outcome protocol")
    if not protocol["postgresql_protocol"]["preclamp_trace_required"]:
        raise ValueError("protocol does not require pre-clamp tracing")
    return protocol


def load_selected_records(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    canonical = root / "arecel" / "audit-v1" / "forest10.canonical.jsonl.gz"
    expected_hash = protocol["source_provenance"]["artifact_sha256"]["canonical"]
    if sha256_file(canonical) != expected_hash:
        raise ValueError("canonical SHA-256 differs from frozen protocol")
    frozen = {item["query_id"]: item for item in protocol["heldout_selection"]["selected"]}
    found: dict[str, dict[str, Any]] = {}
    with gzip.open(canonical, "rb") as stream:
        for raw in stream:
            record = json.loads(raw)
            query_id = record.get("query_id")
            if query_id not in frozen:
                continue
            raw_hash = hashlib.sha256(raw.rstrip(b"\n")).hexdigest()
            expected = frozen[query_id]
            if raw_hash != expected["canonical_record_sha256"]:
                raise ValueError(f"canonical record hash changed for {query_id}")
            if record["source_query_sha256"] != expected["source_query_sha256"]:
                raise ValueError(f"source query hash changed for {query_id}")
            found[query_id] = {
                "query_id": query_id,
                "source_query_sha256": record["source_query_sha256"],
                "canonical_record_sha256": raw_hash,
                "sql": record["sql"],
                "predicates": record["source_query"]["predicates"],
                "truth": int(record["source_label"]["cardinality"]),
                "weight": record["weight"],
                "split": record["split"],
                "covered_candidates": expected["covered_candidates"],
            }
    if set(found) != set(frozen):
        raise ValueError("not all frozen held-out query IDs were found")
    ordered = [found[item["query_id"]] for item in protocol["heldout_selection"]["selected"]]
    if any(item["split"] != "test" for item in ordered):
        raise ValueError("held-out ledger includes a non-test record")
    return ordered


def wait_for_marker(log_path: Path, offset: int, marker: str) -> tuple[int, list[str]]:
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        with log_path.open("rb") as stream:
            stream.seek(offset)
            data = stream.read()
            new_offset = stream.tell()
        lines = data.decode("utf-8", errors="replace").splitlines()
        if any(marker in line for line in lines):
            return new_offset, lines
        time.sleep(0.05)
    raise RuntimeError(f"no trace marker {marker!r} appeared in {log_path}")


def trace_lines(lines: list[str], marker: str) -> dict[str, Any]:
    relevant = [line for line in lines if marker in line]
    numeric: list[dict[str, str]] = []
    selected: list[dict[str, str]] = []
    for line in relevant:
        numeric_match = NUMERIC_TRACE.search(line)
        if numeric_match:
            numeric.append(parse_key_values(numeric_match.group("body")))
        selected_match = SELECTED_TRACE.search(line)
        if selected_match:
            selected.append(parse_key_values(selected_match.group("body")))
    finals = [item for item in numeric if "base_relation_oid" in item]
    return {
        "matching_log_line_count": len(relevant),
        "numeric": numeric,
        "selected": selected,
        "finals": finals,
        "raw_lines": relevant,
    }


def catalog_snapshot(args: argparse.Namespace, candidate_ids: list[str]) -> dict[str, Any]:
    table = psql(
        args,
        "SELECT c.oid::text, c.relfilenode::text, "
        "(pg_relation_size(c.oid)/8192)::text, c.reltuples::text "
        "FROM pg_class c WHERE c.oid='public.forest10_original'::regclass;",
    ).splitlines()
    if len(table) != 1:
        raise RuntimeError(f"unexpected table identity rows: {table}")
    stats = psql(
        args,
        "SELECT s.oid::text, s.stxname, s.stxkeys::text, s.stxstattarget::text, "
        "(d.stxdmcv IS NULL)::text, COALESCE(pg_column_size(d.stxdmcv),0)::text "
        "FROM pg_statistic_ext s LEFT JOIN pg_statistic_ext_data d ON d.stxoid=s.oid "
        "WHERE s.stxname LIKE 'ess_forest10_%' ORDER BY s.stxname;",
    ).splitlines()
    mcv_counts: dict[str, int] = {}
    for line in stats:
        fields = line.split("|")
        if len(fields) != 6 or fields[4] == "t":
            continue
        name = fields[1]
        value = psql(
            args,
            "SELECT count(*)::text FROM pg_statistic_ext s "
            "JOIN pg_statistic_ext_data d ON d.stxoid=s.oid "
            "CROSS JOIN LATERAL pg_mcv_list_items(d.stxdmcv) m "
            f"WHERE s.stxname='{name}';",
        ).strip()
        mcv_counts[name] = int(value or "0")
    oid_to_candidate = {
        line.split("|", 1)[0]: line.split("|", 2)[1]
        for line in stats
        if "|" in line
    }
    return {
        "table": table,
        "statistics": stats,
        "mcv_item_counts": mcv_counts,
        "oid_to_candidate": oid_to_candidate,
        "expected_candidate_ids": candidate_ids,
    }


def selected_resource_ids_from_trace(
    selected_oids: list[str], oid_to_candidate: dict[str, str]
) -> list[str]:
    """Translate every selected statistic OID, failing closed on an unknown OID."""
    unknown = sorted(set(selected_oids) - set(oid_to_candidate))
    if unknown:
        raise RuntimeError(
            "selected statistic OID(s) absent from the catalog identity ledger: "
            + ", ".join(unknown)
        )
    return [oid_to_candidate[oid].removeprefix("ess_forest10_") for oid in selected_oids]


def prepare_fresh_output_dir(output_dir: Path) -> None:
    """Create a new evidence directory without ever overwriting a prior run."""
    if output_dir.exists() or output_dir.is_symlink():
        raise RuntimeError(
            f"refusing to write evidence into an existing output path: {output_dir}; "
            "choose a fresh scratch directory"
        )
    output_dir.mkdir(parents=True, exist_ok=False)


def decimal_log_error(estimate: Decimal, target: int) -> str:
    with localcontext() as context:
        context.prec = 60
        return str(abs((estimate / Decimal(target)).ln()))


def setup_set(
    args: argparse.Namespace,
    set_id: str,
    selected: list[str],
    candidates: dict[str, dict[str, Any]],
    sample: Path,
    sample_header: dict[str, Any],
) -> dict[str, Any]:
    all_ids = list(candidates)
    names = [f"public.ess_forest10_{item}" for item in all_ids]
    sql_parts = ["DROP STATISTICS IF EXISTS " + ", ".join(names) + ";"]
    for candidate_id in all_ids:
        if candidate_id not in selected:
            continue
        columns = ", ".join('"' + column.replace('"', '""') + '"' for column in candidates[candidate_id]["columns"])
        name = f"public.ess_forest10_{candidate_id}"
        sql_parts.append(
            f"CREATE STATISTICS {name} (mcv) ON {columns} FROM public.forest10_original;"
        )
        sql_parts.append(f"ALTER STATISTICS {name} SET STATISTICS 300;")
    escaped = str(sample).replace("'", "''")
    sql_parts.append(
        f"SET ess.analyze_sample_import='{escaped}'; "
        "ANALYZE public.forest10_original; RESET ess.analyze_sample_import;"
    )
    psql(args, " ".join(sql_parts))
    snapshot = catalog_snapshot(args, all_ids)
    table_fields = snapshot["table"][0].split("|")
    expected = [
        str(sample_header["relation_oid"]),
        str(sample_header["relation_filenode"]),
        str(sample_header["relation_pages"]),
    ]
    if table_fields[:3] != expected:
        raise RuntimeError(
            f"sample relation identity mismatch for {set_id}: table={table_fields[:3]} expected={expected}"
        )
    present_names = {line.split("|", 2)[1] for line in snapshot["statistics"] if "|" in line}
    expected_names = {f"ess_forest10_{item}" for item in selected}
    if present_names != expected_names:
        raise RuntimeError(f"statistics snapshot mismatch for {set_id}: {present_names} != {expected_names}")
    return {
        "set_id": set_id,
        "selected": selected,
        "sample_sha256": sha256_file(sample),
        "sample_header": sample_header,
        "catalog": snapshot,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--lib-dir", type=Path, required=True)
    parser.add_argument("--pg-source", type=Path, required=True)
    parser.add_argument("--socket-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", default="postgres")
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    protocol = load_protocol(args.protocol)
    pg_protocol = protocol["postgresql_protocol"]
    if args.repetitions != pg_protocol["repetitions"]:
        raise ValueError("repetition count differs from frozen protocol")
    if sha256_file(args.sample) != pg_protocol["fixed_sample_sha256"]:
        raise ValueError("sample SHA-256 differs from frozen protocol")
    sample_header = parse_sample_header(args.sample)
    if sample_header["server_version"] != pg_protocol["server_version"]:
        raise ValueError("sample server version differs from frozen protocol")
    records = load_selected_records(args.data_root.resolve(), protocol)
    candidates = {item["id"]: item for item in protocol["reference_issue23"]["candidate_rule"]["candidates"]}
    selected_sets = protocol["reference_issue23"]["frozen_selection_sets"]["all_distinct_selected_sets"]
    expected_records = args.repetitions * len(selected_sets) * len(records)
    if expected_records > pg_protocol["maximum_query_measurements"]:
        raise ValueError("run exceeds the frozen query cap")
    # This is deliberately before any PostgreSQL interaction.  A rerun must use
    # a fresh scratch directory so historical raw observations and manifests
    # remain immutable and auditable.
    prepare_fresh_output_dir(args.output_dir)
    runtime_manifest = {
        "format": "ess-issue38-forest10-runtime-manifest-v1",
        "protocol_sha256": sha256_file(args.protocol),
        "sample_sha256": sha256_file(args.sample),
        "sample_header": sample_header,
        "data_root": str(args.data_root.resolve()),
        "pg_source": str(args.pg_source.resolve()),
        "pg_source_commit": run_command(["git", "-C", str(args.pg_source), "rev-parse", "HEAD"]),
        "pg_source_worktree_clean": run_command(["git", "-C", str(args.pg_source), "status", "--porcelain"]) == "",
        "postgres_version": run_command([str(args.pg_bin / "postgres"), "--version"]),
        "psql_version": run_command([str(args.pg_bin / "psql"), "--version"]),
        "binary_sha256": {
            name: sha256_file(args.pg_bin / name)
            for name in ("postgres", "psql", "pg_config", "initdb", "pg_ctl")
        },
        "python": sys.version,
        "platform": platform.platform(),
        "cluster": {
            "socket_dir": str(args.socket_dir),
            "port": args.port,
            "database": args.database,
            "server_log": str(args.server_log),
        },
        "protocol_run_cap": expected_records,
    }
    (args.output_dir / "runtime-manifest.json").write_text(
        json.dumps(runtime_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    setup_path = args.output_dir / "setups.jsonl"
    measurement_path = args.output_dir / "measurements.jsonl"
    log_offset = args.server_log.stat().st_size
    setup_count = 0
    measurement_count = 0
    invalid_count = 0
    with setup_path.open("w", encoding="utf-8") as setup_stream, measurement_path.open("w", encoding="utf-8") as measurement_stream:
        for set_number, selected in enumerate(selected_sets):
            set_id = f"set-{set_number:02d}-{'empty' if not selected else '_'.join(selected)}"
            selected_ids = list(selected)
            for repetition in range(args.repetitions):
                setup = setup_set(args, set_id, selected_ids, candidates, args.sample, sample_header)
                setup_record = {
                    "repetition": repetition,
                    **setup,
                }
                setup_line = json.dumps(setup_record, sort_keys=True)
                setup_stream.write(setup_line + "\n")
                setup_stream.flush()
                setup_count += 1
                log_offset = args.server_log.stat().st_size
                oid_to_candidate = setup["catalog"]["oid_to_candidate"]
                for index, record in enumerate(records):
                    marker = f"ESS_MCV_NUMERIC_TRACE issue38-r{repetition}-{set_number}-{index}"
                    query = record["sql"].replace(
                        "SELECT COUNT(*)",
                        f"EXPLAIN (FORMAT JSON) /* {marker} */ SELECT *",
                        1,
                    )
                    started_offset = log_offset
                    try:
                        plan = psql(args, query)
                        log_offset, lines = wait_for_marker(args.server_log, started_offset, marker)
                        trace = trace_lines(lines, marker)
                        finals = trace["finals"]
                        if len(finals) != 1:
                            raise RuntimeError(f"expected one final trace, got {len(finals)}")
                        final = finals[0]
                        estimate = Decimal(final["nrows_preclamp"])
                        target = max(1, record["truth"])
                        if estimate <= 0:
                            raise RuntimeError(f"nonpositive pre-clamp estimate {estimate}")
                        selected_oids = sorted({item["selected_stat_oid"] for item in trace["numeric"] if item.get("selected_stat_oid")})
                        selected_candidates = selected_resource_ids_from_trace(selected_oids, oid_to_candidate)
                        result = {
                            "status": "valid",
                            "repetition": repetition,
                            "set_id": set_id,
                            "selected_resource_ids": selected_ids,
                            "query_index": index,
                            "query_id": record["query_id"],
                            "source_query_sha256": record["source_query_sha256"],
                            "canonical_record_sha256": record["canonical_record_sha256"],
                            "truth_N": record["truth"],
                            "target_T": target,
                            "estimate_preclamp": str(estimate),
                            "rows_postclamp": final.get("rows_postclamp"),
                            "signed_estimate_minus_T": str(estimate - Decimal(target)),
                            "absolute_log_error": decimal_log_error(estimate, target),
                            "selected_stat_oids": selected_oids,
                            "selected_resource_ids_from_trace": selected_candidates,
                            "trace": trace,
                            "explain_json_text": plan,
                            "sample_sha256": setup["sample_sha256"],
                        }
                    except Exception as error:  # noqa: BLE001 - preserve per-query failures for the Gate A decision
                        invalid_count += 1
                        result = {
                            "status": "INVALID",
                            "repetition": repetition,
                            "set_id": set_id,
                            "selected_resource_ids": selected_ids,
                            "query_index": index,
                            "query_id": record["query_id"],
                            "source_query_sha256": record["source_query_sha256"],
                            "canonical_record_sha256": record["canonical_record_sha256"],
                            "truth_N": record["truth"],
                            "target_T": max(1, record["truth"]),
                            "error": str(error),
                        }
                    measurement_stream.write(json.dumps(result, sort_keys=True) + "\n")
                    measurement_stream.flush()
                    measurement_count += 1
                    print(json.dumps({"set_id": set_id, "repetition": repetition, "query_id": record["query_id"], "status": result["status"]}, sort_keys=True), flush=True)
    summary = {
        "format": "ess-issue38-forest10-heldout-raw-run-summary-v1",
        "protocol_sha256": sha256_file(args.protocol),
        "runtime_manifest_sha256": sha256_file(args.output_dir / "runtime-manifest.json"),
        "setups_sha256": sha256_file(setup_path),
        "measurements_sha256": sha256_file(measurement_path),
        "expected_measurements": expected_records,
        "actual_measurements": measurement_count,
        "setup_count": setup_count,
        "invalid_measurements": invalid_count,
        "all_measurements_valid": invalid_count == 0 and measurement_count == expected_records,
        "latency_collected": False,
    }
    (args.output_dir / "raw-run-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if invalid_count == 0 and measurement_count == expected_records else 2


if __name__ == "__main__":
    raise SystemExit(main())
