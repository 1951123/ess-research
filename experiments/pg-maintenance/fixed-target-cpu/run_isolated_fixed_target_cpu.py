#!/usr/bin/env python3
"""Own the isolated PostgreSQL lifecycle for Issue #9.

The wrapper always attempts database removal and server shutdown after a
failure.  It retains all logs and marks the campaign incomplete unless the
640-cell raw artifact and offline analysis both succeed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    command: list[str],
    log_dir: Path,
    name: str,
    *,
    input_text: str | None = None,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    (log_dir / f"{name}.stdout.log").write_text(result.stdout, encoding="utf-8")
    (log_dir / f"{name}.stderr.log").write_text(result.stderr, encoding="utf-8")
    (log_dir / f"{name}.command.json").write_text(
        json.dumps(command, indent=2) + "\n", encoding="utf-8"
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--database", default="ess_issue9_cpu")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--repetitions", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.database):
        raise SystemExit(f"unsafe database identifier: {args.database!r}")
    if args.root.exists():
        raise SystemExit(f"refusing to reuse existing temporary root: {args.root}")
    if args.output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {args.output_dir}")
    if not args.fixture.is_file():
        raise SystemExit(f"missing fixture: {args.fixture}")

    prefix = args.prefix.resolve()
    bin_dir = prefix / "bin"
    data_dir = args.root / "data"
    socket_dir = args.root / "socket"
    lifecycle_dir = args.output_dir / "lifecycle"
    lifecycle_dir.mkdir(parents=True, exist_ok=False)
    args.root.mkdir(parents=True, exist_ok=False)
    data_dir.mkdir()
    socket_dir.mkdir()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "LD_LIBRARY_PATH": str(prefix / "lib"),
        "LC_ALL": "C",
    }
    psql = bin_dir / "psql"
    base = [
        str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", str(socket_dir),
        "-p", str(args.port), "-U", "postgres",
    ]
    started = False
    database_created = False
    failure_stage: str | None = None
    benchmark_returncode: int | None = None
    analysis_returncode: int | None = None

    initdb = run(
        [
            str(bin_dir / "initdb"), "-D", str(data_dir), "-U", "postgres",
            "-A", "trust", "--no-locale", "--encoding=UTF8",
        ],
        lifecycle_dir,
        "initdb",
        environment=env,
    )
    if initdb.returncode != 0:
        failure_stage = "initdb"
    if failure_stage is None:
        start = run(
            [
                str(bin_dir / "pg_ctl"), "-D", str(data_dir), "-o",
                f"-k {socket_dir} -p {args.port} -c autovacuum=off",
                "-l", str(lifecycle_dir / "server.log"), "start", "-w",
            ],
            lifecycle_dir,
            "pg-ctl-start",
            environment=env,
        )
        started = start.returncode == 0
        if start.returncode != 0:
            failure_stage = "pg_ctl_start"
    if failure_stage is None:
        create_db = run(
            base + ["-d", "postgres", "-c", f"CREATE DATABASE {args.database};"],
            lifecycle_dir,
            "create-database",
            environment=env,
        )
        database_created = create_db.returncode == 0
        if create_db.returncode != 0:
            failure_stage = "create_database"
    if failure_stage is None:
        fixture = run(
            base + ["-d", args.database, "-f", str(args.fixture)],
            lifecycle_dir,
            "fixture",
            environment=env,
        )
        if fixture.returncode != 0:
            failure_stage = "fixture"
    if failure_stage is None:
        fixture_metrics = run(
            [
                sys.executable,
                str(args.fixture.parent / "fixture_metrics.py"),
                "--psql", str(psql), "--host", str(socket_dir),
                "--port", str(args.port), "--database", args.database,
                "--output-dir", str(args.output_dir / "fixture-metrics"),
            ],
            lifecycle_dir,
            "fixture-metrics",
            environment=env,
        )
        if fixture_metrics.returncode != 0:
            failure_stage = "fixture_metrics"
    if failure_stage is None:
        raw_dir = args.output_dir / "measurement"
        benchmark = run(
            [
                sys.executable,
                str(Path(__file__).with_name("run_fixed_target_cpu.py")),
                "--psql", str(psql), "--host", str(socket_dir),
                "--port", str(args.port), "--database", args.database,
                "--output-dir", str(raw_dir), "--seed", str(args.seed),
                "--repetitions", str(args.repetitions),
                "--source-commit", args.source_commit,
                "--postgres-binary-sha256", sha256(bin_dir / "postgres"),
                "--fixture-metrics",
                str(args.output_dir / "fixture-metrics" / "fixture-metrics.json"),
            ],
            lifecycle_dir,
            "fixed-target-cpu",
            environment=env,
        )
        benchmark_returncode = benchmark.returncode
        if benchmark.returncode != 0:
            failure_stage = "measurement"
    if failure_stage is None:
        analysis = run(
            [
                sys.executable,
                str(Path(__file__).with_name("analyze_fixed_target_cpu.py")),
                str(args.output_dir / "measurement" / "raw-observations.json"),
                "--output-dir", str(args.output_dir / "analysis"),
            ],
            lifecycle_dir,
            "offline-analysis",
            environment=env,
        )
        analysis_returncode = analysis.returncode
        if analysis.returncode != 0:
            failure_stage = "analysis"

    drop = None
    absence = None
    if started and database_created:
        drop = run(
            base + ["-d", "postgres", "-c", f"DROP DATABASE {args.database};"],
            lifecycle_dir,
            "drop-database",
            environment=env,
        )
        absence = run(
            base + [
                "-d", "postgres", "-At", "-c",
                f"SELECT datname FROM pg_database WHERE datname = '{args.database}';",
            ],
            lifecycle_dir,
            "database-absence",
            environment=env,
        )
    cleanup_ok = bool(
        drop is not None
        and absence is not None
        and drop.returncode == 0
        and absence.returncode == 0
        and absence.stdout.strip() == ""
    )
    cleanup_before_stop = {
        "drop_database_returncode": None if drop is None else drop.returncode,
        "database_absence_query_returncode": None if absence is None else absence.returncode,
        "database_absence_stdout": None if absence is None else absence.stdout,
        "database_absent_while_server_running": cleanup_ok,
    }
    (args.output_dir / "cleanup-before-stop.json").write_text(
        json.dumps(cleanup_before_stop, indent=2) + "\n", encoding="utf-8"
    )
    stop = None
    status = None
    if started:
        stop = run(
            [str(bin_dir / "pg_ctl"), "-D", str(data_dir), "-m", "fast", "stop", "-w"],
            lifecycle_dir,
            "pg-ctl-stop",
            environment=env,
        )
        status = run(
            [str(bin_dir / "pg_ctl"), "-D", str(data_dir), "status"],
            lifecycle_dir,
            "pg-ctl-status-after-stop",
            environment=env,
        )
    server_stopped = bool(
        stop is not None and status is not None and stop.returncode == 0 and status.returncode != 0
    )
    complete = failure_stage is None and cleanup_ok and server_stopped
    evidence = {
        "experiment": "issue-9-pg16-fixed-target-extstats-cpu",
        "source_commit": args.source_commit,
        "postgres_binary": str(bin_dir / "postgres"),
        "postgres_binary_sha256": sha256(bin_dir / "postgres"),
        "psql_binary": str(psql),
        "psql_binary_sha256": sha256(psql),
        "fixture_sha256": sha256(args.fixture),
        "database": args.database,
        "socket_dir": str(socket_dir),
        "port": args.port,
        "repetitions": args.repetitions,
        "seed": args.seed,
        "failure_stage": failure_stage,
        "benchmark_returncode": benchmark_returncode,
        "analysis_returncode": analysis_returncode,
        "database_absent_while_server_running": cleanup_ok,
        "server_stopped": server_stopped,
        "complete": complete,
        "temporary_root": str(args.root),
    }
    (args.output_dir / "cleanup-status.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    if server_stopped:
        shutil.rmtree(args.root)
        (args.output_dir / "temporary-root-removed.txt").write_text("removed\n", encoding="utf-8")
    else:
        (args.output_dir / "temporary-root-removed.txt").write_text(
            "not removed; inspect lifecycle logs\n", encoding="utf-8"
        )
    if not complete:
        print(json.dumps(evidence, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
