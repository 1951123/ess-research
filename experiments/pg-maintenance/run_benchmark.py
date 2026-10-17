#!/usr/bin/env python3
"""Run the Issue #7 PostgreSQL ANALYZE maintenance benchmark.

The only timed operation is the server command ``ANALYZE <table>``.  A single
persistent psql process is used so connection establishment is outside every
timed command.  DDL and condition setup are emitted with timing disabled.
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
from typing import Iterable


TABLES = {
    "weakassoc": "ess_mcv_weakassoc",
    "correlated": "ess_mcv_correlated",
}
EDGES = ("ab", "bc", "cd")
TARGET_MODES = {
    "uniform10": {edge: 10 for edge in EDGES},
    "uniform100": {edge: 100 for edge in EDGES},
    "mixed_10_100_10": {"ab": 10, "bc": 100, "cd": 10},
    "uniform300": {edge: 300 for edge in EDGES},
    "mixed_10_300_10": {"ab": 10, "bc": 300, "cd": 10},
}
TIME_RE = re.compile(r"^Time: ([0-9]+(?:\.[0-9]+)?) ms$")
META_RE_WITH_REPETITION = re.compile(
    r"^META\|([^|]+)\|([0-9]+)\|([^|]+)(?:\|([0-9]+)\|([^|]+)\|([^|]+))?$"
)
META_RE_LEGACY = re.compile(
    r"^META\|([^|]+)\|([^|]+)(?:\|([0-9]+)\|([^|]+)\|([^|]+))?$"
)
RUN_RE = re.compile(r"^RUN\|([^|]+)\|([0-9]+)\|([0-9]+)$")


@dataclass(frozen=True)
class Condition:
    condition_id: str
    regime: str
    table: str
    subset: tuple[str, ...]
    target_mode: str
    targets: dict[str, int]
    requested_target: int
    requested_sample_rows: int
    ordinary_column_target: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def conditions() -> list[Condition]:
    result: list[Condition] = []
    for regime, table in TABLES.items():
        for target_mode, target_values in TARGET_MODES.items():
            for count in range(4):
                for subset in itertools.combinations(EDGES, count):
                    active_target = max(
                        (target_values[edge] for edge in subset), default=1
                    )
                    condition_id = f"{regime}__{'none' if not subset else '_'.join(subset)}__{target_mode}"
                    result.append(
                        Condition(
                            condition_id=condition_id,
                            regime=regime,
                            table=table,
                            subset=tuple(subset),
                            target_mode=target_mode,
                            targets={edge: target_values[edge] for edge in subset},
                            requested_target=active_target,
                            requested_sample_rows=300 * active_target,
                            ordinary_column_target=1,
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
    names = [object_name(table, edge) for edge in EDGES]
    lines = ["\\timing off"]
    for name in names:
        lines.append(f"DROP STATISTICS IF EXISTS {sql_ident(name)};")
    for edge in condition.subset:
        name = sql_ident(object_name(table, edge))
        columns = {"ab": "a,b", "bc": "b,c", "cd": "c,d"}[edge]
        lines.append(f"CREATE STATISTICS {name} (mcv) ON {columns} FROM {table};")
        lines.append(f"ALTER STATISTICS {name} SET STATISTICS {condition.targets[edge]};")
    return "\n".join(lines) + "\n"


def metadata_sql(condition: Condition, repetition: int) -> str:
    table = sql_ident(condition.table)
    names = ", ".join(
        "'" + object_name(table, edge).replace("'", "''") + "'" for edge in EDGES
    )
    cid = condition.condition_id.replace("'", "''")
    return (
        "SELECT 'META|' || '"
        + cid
        + "' || '|' || "
        + str(repetition)
        + "::text || '|' || e.stxname || '|' || e.oid::text || '|' || "
        "COALESCE(e.stxstattarget::text, 'NULL') || '|' || "
        "(d.stxdmcv IS NOT NULL)::text "
        "FROM pg_statistic_ext e "
        "LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid "
        f"WHERE e.stxrelid = '{table}'::regclass AND e.stxname IN ({names}) "
        "ORDER BY e.stxname;\n"
        "SELECT 'META|' || '"
        + cid
        + "' || '|' || "
        + str(repetition)
        + "::text || '|NONE' WHERE NOT EXISTS ("
        "SELECT 1 FROM pg_statistic_ext e "
        f"WHERE e.stxrelid = '{table}'::regclass AND e.stxname IN ({names})"
        ");\n"
    )


def schedule_sql(schedule: list[tuple[Condition, int, int]]) -> str:
    lines = [
        "\\set ON_ERROR_STOP on",
        "\\pset pager off",
        "\\pset format unaligned",
        "\\pset tuples_only on",
        "\\set VERBOSITY terse",
        "SET client_min_messages = warning;",
        "SET synchronous_commit = on;",
        "\\timing off",
    ]
    for condition, repetition, order_index in schedule:
        lines.append(f"\\echo SETUP|{condition.condition_id}|{repetition}|{order_index}")
        lines.append(setup_sql(condition).rstrip())
        lines.append(f"\\echo WARMUP|{condition.condition_id}|{repetition}|{order_index}")
        lines.append(f"ANALYZE {sql_ident(condition.table)};")
        # Read payload metadata only after the untimed ANALYZE has built the
        # newly created objects.  Reading it before warm-up would only prove
        # that the objects exist, not that their MCV payloads were built.
        lines.append(metadata_sql(condition, repetition).rstrip())
        lines.append("\\timing on")
        lines.append(f"\\echo RUN|{condition.condition_id}|{repetition}|{order_index}")
        lines.append(f"ANALYZE {sql_ident(condition.table)};")
        lines.append("\\timing off")
    return "\n".join(lines) + "\n"


def build_schedule(seed: int, reps: int) -> list[tuple[Condition, int, int]]:
    all_conditions = conditions()
    rng = random.Random(seed)
    schedule: list[tuple[Condition, int, int]] = []
    order_index = 0
    for repetition in range(1, reps + 1):
        block = list(all_conditions)
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
        str(psql),
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-d",
        database,
    ]
    (raw_dir / "psql-command.json").write_text(
        json.dumps(command, indent=2) + "\n", encoding="utf-8"
    )
    completed = subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    (raw_dir / "schedule.sql").write_text(sql, encoding="utf-8")
    (raw_dir / "psql.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (raw_dir / "psql.stderr.log").write_text(completed.stderr, encoding="utf-8")
    return completed.returncode, completed.stdout, completed.stderr


def parse_output(stdout: str, expected_runs: int) -> tuple[list[dict], list[dict]]:
    observations: list[dict] = []
    metadata: list[dict] = []
    pending_run: dict | None = None
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        match = RUN_RE.match(line)
        if match:
            pending_run = {
                "condition_id": match.group(1),
                "repetition": int(match.group(2)),
                "order_index": int(match.group(3)),
            }
            continue
        match = TIME_RE.match(line)
        if match:
            if pending_run is None:
                raise RuntimeError(f"unattributed timing line: {line!r}")
            row = dict(pending_run)
            row["psql_elapsed_ms"] = float(match.group(1))
            observations.append(row)
            pending_run = None
            continue
        match = META_RE_WITH_REPETITION.match(line)
        legacy = False
        if match is None:
            match = META_RE_LEGACY.match(line)
            legacy = match is not None
        if match:
            if legacy:
                condition_id, name, oid, target, built = match.groups()
                repetition = None
            else:
                condition_id, repetition, name, oid, target, built = match.groups()
            metadata.append(
                {
                    "condition_id": condition_id,
                    "repetition": None if repetition is None else int(repetition),
                    "name": None if name == "NONE" else name,
                    "oid": None if name == "NONE" else int(oid),
                    "statistics_target": None if name == "NONE" else int(target),
                    "mcv_payload_built": None if name == "NONE" else built == "true",
                }
            )
    if pending_run is not None:
        raise RuntimeError(f"missing timing for {pending_run}")
    if len(observations) != expected_runs:
        raise RuntimeError(
            f"expected {expected_runs} timed ANALYZE observations, found {len(observations)}"
        )
    return observations, metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psql", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--postgres-binary-sha256", required=True)
    parser.add_argument("--fixture-metrics", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repetitions < 7:
        raise SystemExit("Issue #7 requires at least seven timed repetitions")
    if not args.psql.is_file():
        raise SystemExit(f"psql does not exist: {args.psql}")
    schedule = build_schedule(args.seed, args.repetitions)
    condition_map = {condition.condition_id: condition for condition in conditions()}
    expected = len(schedule)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    raw_dir = args.output_dir / "raw"
    sql = schedule_sql(schedule)
    returncode, stdout, stderr = run_psql(
        args.psql,
        args.host,
        args.port,
        args.database,
        args.user,
        sql,
        raw_dir,
    )
    if returncode != 0:
        (args.output_dir / "failure.json").write_text(
            json.dumps({"returncode": returncode}, indent=2) + "\n",
            encoding="utf-8",
        )
        print("psql schedule failed; raw logs were retained", file=sys.stderr)
        return returncode
    observations, metadata = parse_output(stdout, expected)
    for row in observations:
        row.update(asdict(condition_map[row["condition_id"]]))
    payload = {
        "schema_version": 1,
        "experiment": "issue-7-pg16-analyze-maintenance",
        "seed": args.seed,
        "repetitions": args.repetitions,
        "condition_count": len(condition_map),
        "timed_observation_count": len(observations),
        "timing_method": {
            "client": "pinned PostgreSQL 16.14 psql \\timing",
            "clock": "CLOCK_MONOTONIC via instr_time on the measured platform",
            "scope": "server command round-trip; persistent connection; excludes DDL/setup and connection establishment",
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
            "ordinary_column_target": 1,
            "sample_rows_formula": "max(300*ordinary_column_target, 300*max(enabled extended target))",
            "realized_sample_rows_observed": False,
        },
        "conditions": [asdict(condition) for condition in condition_map.values()],
        "metadata_observations": metadata,
        "observations": observations,
    }
    if args.fixture_metrics:
        payload["fixture_metrics"] = json.loads(
            args.fixture_metrics.read_text(encoding="utf-8")
        )
    output = args.output_dir / "raw-observations.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output} ({len(observations)} timed observations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
