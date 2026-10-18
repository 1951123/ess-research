#!/usr/bin/env python3
"""Run the Issue #9 fixed-target CPU maintenance campaign.

The campaign reuses the merged Issue #7 weak-association and correlated
fixtures, but changes every ordinary-column and MCV target to one common
target (100 or 300) for each condition.  It records psql round-trip time only
as a secondary diagnostic.  The primary measurement is the opt-in backend
CPU trace emitted around the complete BuildRelationExtStatistics() phase.

The script deliberately writes raw stdout, stderr, the generated SQL, and the
parsed JSON separately.  It refuses to overwrite an output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import random
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


TABLES = {
    "weakassoc": "ess_mcv_weakassoc",
    "correlated": "ess_mcv_correlated",
}
EDGES = ("ab", "bc", "cd")
ATTRIBUTES = ("id", "a", "b", "c", "d")
EDGE_COLUMNS = {"ab": "a,b", "bc": "b,c", "cd": "c,d"}
TARGETS = (100, 300)
TRACE_RE = re.compile(
    r"ESS_EXT_CPU_TRACE: phase=BuildRelationExtStatistics "
    r"relid=(\d+) stats_count=(\d+) built_count=(\d+) "
    r"user_us=(-?\d+) system_us=(-?\d+) cpu_us=(-?\d+)"
)
RUN_RE = re.compile(r"^RUN\|([^|]+)\|(\d+)\|(\d+)$")
TIME_RE = re.compile(r"^Time: ([0-9]+(?:\.[0-9]+)?) ms$")
META_EXT_RE = re.compile(
    r"^METAEXT\|([^|]+)\|(\d+)\|([^|]+)\|(\d+)\|(\d+)\|(true|false)$"
)
META_NONE_RE = re.compile(r"^METAEXT\|([^|]+)\|(\d+)\|NONE$")
META_ORD_RE = re.compile(r"^METAORD\|([^|]+)\|(\d+)\|(\d+)\|(.+)$")


@dataclass(frozen=True)
class Condition:
    condition_id: str
    regime: str
    table: str
    subset: tuple[str, ...]
    target: int
    ordinary_column_target: int
    requested_sample_rows: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def all_subsets() -> list[tuple[str, ...]]:
    return [subset for count in range(len(EDGES) + 1) for subset in itertools.combinations(EDGES, count)]


def condition_list() -> list[Condition]:
    result: list[Condition] = []
    for regime, table in TABLES.items():
        for target in TARGETS:
            for subset in all_subsets():
                subset_name = "none" if not subset else "_".join(subset)
                result.append(
                    Condition(
                        condition_id=f"{regime}__{subset_name}__target{target}",
                        regime=regime,
                        table=table,
                        subset=subset,
                        target=target,
                        ordinary_column_target=target,
                        requested_sample_rows=300 * target,
                    )
                )
    return result


def sql_ident(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise ValueError(f"unsafe SQL identifier: {value!r}")
    return value


def object_name(table: str, edge: str) -> str:
    return f"{table}_{edge}"


def setup_sql(condition: Condition) -> str:
    table = sql_ident(condition.table)
    lines = ["\\timing off"]
    for edge in EDGES:
        lines.append(f"DROP STATISTICS IF EXISTS {sql_ident(object_name(table, edge))};")
    for edge in condition.subset:
        name = sql_ident(object_name(table, edge))
        lines.append(
            f"CREATE STATISTICS {name} (mcv) ON {EDGE_COLUMNS[edge]} FROM {table};"
        )
        lines.append(f"ALTER STATISTICS {name} SET STATISTICS {condition.target};")
    for attr in ATTRIBUTES:
        lines.append(
            f"ALTER TABLE {table} ALTER COLUMN {attr} SET STATISTICS {condition.ordinary_column_target};"
        )
    return "\n".join(lines) + "\n"


def metadata_sql(condition: Condition, repetition: int) -> str:
    table = sql_ident(condition.table)
    cid = condition.condition_id.replace("'", "''")
    names = ", ".join(
        "'" + object_name(table, edge).replace("'", "''") + "'" for edge in EDGES
    )
    return (
        "SELECT 'METAEXT|' || '"
        + cid
        + "' || '|' || "
        + str(repetition)
        + "::text || '|' || e.stxname || '|' || e.oid::text || '|' || "
        "e.stxstattarget::text || '|' || (d.stxdmcv IS NOT NULL)::text "
        "FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid=e.oid "
        f"WHERE e.stxrelid='{table}'::regclass AND e.stxname IN ({names}) "
        "ORDER BY e.stxname;\n"
        "SELECT 'METAEXT|' || '"
        + cid
        + "' || '|' || "
        + str(repetition)
        + "::text || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e "
        f"WHERE e.stxrelid='{table}'::regclass AND e.stxname IN ({names}));\n"
        "SELECT 'METAORD|' || '"
        + cid
        + "' || '|' || "
        + str(repetition)
        + "::text || '|' || c.oid::text || '|' || "
        "string_agg(a.attname || '=' || a.attstattarget::text, ',' ORDER BY a.attnum) "
        "FROM pg_class c JOIN pg_attribute a ON a.attrelid=c.oid "
        f"WHERE c.oid='{table}'::regclass AND a.attnum>0 AND NOT a.attisdropped "
        "GROUP BY c.oid;\n"
    )


def schedule_sql(schedule: list[tuple[Condition, int, int]]) -> str:
    lines = [
        "\\set ON_ERROR_STOP on",
        "\\pset pager off",
        "\\pset format unaligned",
        "\\pset tuples_only on",
        "\\set VERBOSITY terse",
        "SET client_min_messages = debug1;",
        "SET synchronous_commit = on;",
        "SET ess.mcv_cpu_trace = on;",
        "\\timing off",
    ]
    for condition, repetition, order_index in schedule:
        lines.append(f"\\echo SETUP|{condition.condition_id}|{repetition}|{order_index}")
        lines.append(setup_sql(condition).rstrip())
        lines.append(f"\\echo WARMUP|{condition.condition_id}|{repetition}|{order_index}")
        lines.append(f"ANALYZE {sql_ident(condition.table)};")
        lines.append(metadata_sql(condition, repetition).rstrip())
        lines.append("\\timing on")
        lines.append(f"\\echo RUN|{condition.condition_id}|{repetition}|{order_index}")
        lines.append(f"ANALYZE {sql_ident(condition.table)};")
        lines.append("\\timing off")
    return "\n".join(lines) + "\n"


def build_schedule(seed: int, repetitions: int) -> list[tuple[Condition, int, int]]:
    conditions = condition_list()
    rng = random.Random(seed)
    schedule: list[tuple[Condition, int, int]] = []
    order_index = 0
    for repetition in range(1, repetitions + 1):
        block = list(conditions)
        rng.shuffle(block)
        for condition in block:
            order_index += 1
            schedule.append((condition, repetition, order_index))
    return schedule


def run_psql(
    psql: Path,
    host: str,
    port: int,
    database: str,
    user: str,
    sql: str,
    raw_dir: Path,
) -> tuple[int, str, str]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", host, "-p", str(port),
        "-U", user, "-d", database,
    ]
    (raw_dir / "psql-command.json").write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")
    (raw_dir / "schedule.sql").write_text(sql, encoding="utf-8")
    completed = subprocess.run(
        command, input=sql, text=True, capture_output=True, check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    (raw_dir / "psql.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (raw_dir / "psql.stderr.log").write_text(completed.stderr, encoding="utf-8")
    return completed.returncode, completed.stdout, completed.stderr


def parse_psql_output(
    stdout: str,
    stderr: str,
    schedule: list[tuple[Condition, int, int]],
) -> tuple[list[dict], list[dict], list[dict]]:
    expected = len(schedule)
    runs: list[dict] = []
    for line in stdout.splitlines():
        match = RUN_RE.match(line.strip())
        if match:
            runs.append({
                "condition_id": match.group(1),
                "repetition": int(match.group(2)),
                "order_index": int(match.group(3)),
            })
    times = [float(match.group(1)) for line in stdout.splitlines() if (match := TIME_RE.match(line.strip()))]
    if len(runs) != expected or len(times) != expected:
        raise RuntimeError(f"expected {expected} RUN/Time lines, found {len(runs)}/{len(times)}")

    stream_traces = {}
    for stream_name, stream in (("stdout", stdout), ("stderr", stderr)):
        matches = [match for line in stream.splitlines() if (match := TRACE_RE.search(line))]
        if matches:
            stream_traces[stream_name] = matches
    if len(stream_traces) != 1:
        raise RuntimeError(
            "CPU telemetry must be present in exactly one ordered stream; "
            f"found streams: {sorted(stream_traces)}"
        )
    trace_stream, trace_matches = next(iter(stream_traces.items()))
    if len(trace_matches) != 2 * expected:
        raise RuntimeError(
            f"expected {2 * expected} CPU traces (warmup + timed), found {len(trace_matches)}; "
            f"stream={trace_stream}; raw logs are retained for diagnosis"
        )

    observations: list[dict] = []
    for index, ((condition, repetition, order_index), run, elapsed_ms) in enumerate(
        zip(schedule, runs, times)
    ):
        if (condition.condition_id, repetition, order_index) != (
            run["condition_id"], run["repetition"], run["order_index"]
        ):
            raise RuntimeError(f"RUN routing mismatch at schedule index {index}: {run}")
        warmup = _trace_record(trace_stream, trace_matches[2 * index])
        timed = _trace_record(trace_stream, trace_matches[2 * index + 1])
        if warmup["relid"] != timed["relid"]:
            raise RuntimeError(f"warmup/timed relation mismatch at {condition.condition_id}")
        row = asdict(condition)
        row.update(run)
        row.update({
            "psql_elapsed_ms": elapsed_ms,
            "trace_stream": trace_stream,
            "warmup_cpu_trace": warmup,
            "cpu_trace": timed,
        })
        observations.append(row)

    metadata: list[dict] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if match := META_EXT_RE.match(stripped):
            metadata.append({
                "kind": "extended",
                "condition_id": match.group(1),
                "repetition": int(match.group(2)),
                "name": match.group(3),
                "oid": int(match.group(4)),
                "statistics_target": int(match.group(5)),
                "mcv_payload_built": match.group(6) == "true",
            })
        elif match := META_NONE_RE.match(stripped):
            metadata.append({
                "kind": "extended",
                "condition_id": match.group(1),
                "repetition": int(match.group(2)),
                "name": None,
                "oid": None,
                "statistics_target": None,
                "mcv_payload_built": None,
            })
        elif match := META_ORD_RE.match(stripped):
            target_map = {}
            for item in match.group(4).split(","):
                name, target = item.split("=", 1)
                target_map[name] = int(target)
            metadata.append({
                "kind": "ordinary",
                "condition_id": match.group(1),
                "repetition": int(match.group(2)),
                "table_oid": int(match.group(3)),
                "targets": target_map,
            })
    return observations, metadata, [
        {"stream": trace_stream, "text": match.group(0)} for match in trace_matches
    ]


def _trace_record(stream: str, match: re.Match[str]) -> dict:
    values = match.groups()
    return {
        "stream": stream,
        "relid": int(values[0]),
        "stats_count": int(values[1]),
        "built_count": int(values[2]),
        "user_us": int(values[3]),
        "system_us": int(values[4]),
        "cpu_us": int(values[5]),
    }


def validate_cpu_trace_pair(row: dict, condition: Condition) -> None:
    expected_count = len(condition.subset)
    warmup = row["warmup_cpu_trace"]
    timed = row["cpu_trace"]
    if warmup["stream"] != timed["stream"]:
        raise RuntimeError(f"warmup/timed trace stream mismatch for {condition.condition_id}")
    if row.get("trace_stream") != timed["stream"]:
        raise RuntimeError(f"observation/trace stream mismatch for {condition.condition_id}")
    for phase, trace in (("warmup", warmup), ("timed", timed)):
        if trace["stats_count"] != expected_count or trace["built_count"] != expected_count:
            raise RuntimeError(f"{phase} trace count mismatch for {condition.condition_id}")
        if trace["relid"] <= 0:
            raise RuntimeError(f"invalid {phase} trace relation for {condition.condition_id}")
        if trace["cpu_us"] < 0 or trace["user_us"] < 0 or trace["system_us"] < 0:
            raise RuntimeError(f"negative {phase} CPU measurement for {condition.condition_id}")
        if trace["cpu_us"] != trace["user_us"] + trace["system_us"]:
            raise RuntimeError(f"{phase} CPU decomposition mismatch for {condition.condition_id}")


def validate(observations: list[dict], metadata: list[dict], repetitions: int) -> None:
    conditions = {condition.condition_id: condition for condition in condition_list()}
    expected = len(conditions) * repetitions
    if len(observations) != expected:
        raise RuntimeError(f"expected {expected} observations, found {len(observations)}")
    keys = {(row["condition_id"], row["repetition"]) for row in observations}
    expected_keys = {
        (condition_id, repetition)
        for condition_id in conditions
        for repetition in range(1, repetitions + 1)
    }
    if keys != expected_keys:
        raise RuntimeError("duplicate, missing, or unexpected condition/repetition observation")
    for row in observations:
        if row["condition_id"] not in conditions:
            raise RuntimeError(f"unknown condition in observation: {row['condition_id']}")
        condition = conditions[row["condition_id"]]
        validate_cpu_trace_pair(row, condition)
    ordinary = [row for row in metadata if row["kind"] == "ordinary"]
    extended = [row for row in metadata if row["kind"] == "extended"]
    if len(ordinary) != expected:
        raise RuntimeError(f"expected {expected} ordinary target metadata rows, found {len(ordinary)}")
    ordinary_by_cell = {
        (row["condition_id"], row["repetition"]): row for row in ordinary
    }
    extended_by_cell: dict[tuple[str, int], list[dict]] = {}
    for row in extended:
        extended_by_cell.setdefault(
            (row["condition_id"], row["repetition"]), []
        ).append(row)
    if set(ordinary_by_cell) != set(keys) or set(extended_by_cell) != set(keys):
        raise RuntimeError("metadata cell coverage does not match timed observations")
    for row in ordinary:
        condition = conditions[row["condition_id"]]
        if row["targets"] != {attr: condition.target for attr in ATTRIBUTES}:
            raise RuntimeError(f"ordinary target mismatch for {row['condition_id']}")
    for cell, rows in extended_by_cell.items():
        condition = conditions[cell[0]]
        expected_names = [object_name(condition.table, edge) for edge in condition.subset]
        expected_name_set = set(expected_names)
        if not expected_names:
            if len(rows) != 1 or rows[0]["name"] is not None:
                raise RuntimeError(f"expected exactly one empty MCV metadata record for {cell}")
        else:
            observed_names = [row["name"] for row in rows]
            if (
                len(rows) != len(expected_names)
                or any(name not in expected_name_set for name in observed_names)
                or len(observed_names) != len(set(observed_names))
                or set(observed_names) != expected_name_set
            ):
                raise RuntimeError(f"MCV object coverage mismatch for {cell}")
        for row in rows:
            if row["name"] is not None:
                if row["statistics_target"] != condition.target or not row["mcv_payload_built"]:
                    raise RuntimeError(f"MCV target/payload mismatch for {cell}")
                if (
                    not isinstance(row["oid"], int)
                    or isinstance(row["oid"], bool)
                    or row["oid"] <= 0
                ):
                    raise RuntimeError(f"invalid MCV object OID for {cell}")
    nonempty_oids = [row["oid"] for row in extended if row["name"] is not None]
    if len(nonempty_oids) != len(set(nonempty_oids)):
        raise RuntimeError("duplicate MCV object OID across metadata records")
    for row in observations:
        cell = (row["condition_id"], row["repetition"])
        if row["cpu_trace"]["relid"] != ordinary_by_cell[cell]["table_oid"]:
            raise RuntimeError(f"trace relation does not match target table for {cell}")
        if row["warmup_cpu_trace"]["relid"] != row["cpu_trace"]["relid"]:
            raise RuntimeError(f"warmup/timed relation mismatch for {cell}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psql", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--postgres-binary-sha256", required=True)
    parser.add_argument("--fixture-metrics", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repetitions < 20:
        raise SystemExit("Issue #9 requires at least 20 randomized repetitions")
    if args.output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {args.output_dir}")
    if not args.psql.is_file():
        raise SystemExit(f"missing psql: {args.psql}")
    schedule = build_schedule(args.seed, args.repetitions)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    raw_dir = args.output_dir / "raw"
    sql = schedule_sql(schedule)
    returncode, stdout, stderr = run_psql(
        args.psql, args.host, args.port, args.database, args.user, sql, raw_dir
    )
    if returncode != 0:
        (args.output_dir / "failure.json").write_text(
            json.dumps({"returncode": returncode}, indent=2) + "\n", encoding="utf-8"
        )
        print("psql schedule failed; raw logs retained", file=sys.stderr)
        return returncode
    try:
        observations, metadata, trace_inventory = parse_psql_output(stdout, stderr, schedule)
        validate(observations, metadata, args.repetitions)
    except Exception as exc:
        (args.output_dir / "parse-failure.json").write_text(
            json.dumps({"error": str(exc)}, indent=2) + "\n", encoding="utf-8"
        )
        print(f"raw parse/validation failed: {exc}", file=sys.stderr)
        return 1
    conditions = condition_list()
    payload = {
        "schema_version": 1,
        "experiment": "issue-9-pg16-fixed-target-extstats-cpu",
        "seed": args.seed,
        "repetitions": args.repetitions,
        "condition_count": len(conditions),
        "timed_observation_count": len(observations),
        "primary_timing": {
            "source": "opt-in DEBUG1 ESS_EXT_CPU_TRACE",
            "clock": "getrusage(RUSAGE_SELF) in the PostgreSQL backend",
            "scope": "complete BuildRelationExtStatistics phase, including object build, serialization, catalog persistence, and phase overhead",
            "unit": "microseconds of backend user plus system CPU",
            "wall_time_secondary": "psql persistent-session round trip in milliseconds; not used as primary CPU evidence",
        },
        "provenance": {
            "source_commit": args.source_commit,
            "postgres_binary_sha256": args.postgres_binary_sha256,
            "psql_binary_sha256": sha256_file(args.psql),
            "psql_path": str(args.psql),
            "host": args.host,
            "port": args.port,
            "database": args.database,
            "user": args.user,
            "fixed_fixture": "experiments/pg-maintenance/fixture.sql",
            "ordinary_columns": list(ATTRIBUTES),
            "sample_rows_formula": "max(100, 300 * max(ordinary target, analyzable extended-stat target))",
            "requested_sample_rows_by_target": {str(target): 300 * target for target in TARGETS},
            "realized_sample_rows_observed": False,
        },
        "conditions": [asdict(condition) for condition in conditions],
        "metadata_observations": metadata,
        "trace_inventory": trace_inventory,
        "observations": observations,
    }
    if args.fixture_metrics:
        payload["fixture_metrics"] = json.loads(args.fixture_metrics.read_text(encoding="utf-8"))
    output = args.output_dir / "raw-observations.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output} ({len(observations)} timed observations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
