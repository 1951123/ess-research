#!/usr/bin/env python3
"""Own the complete disposable PostgreSQL lifecycle for Issue #7.

This wrapper records every setup/fixture/lifecycle subprocess output and only
invokes the benchmark after the private server and database are ready.  It
does not touch any pre-existing PostgreSQL process or data directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--database", default="ess_issue7")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--repetitions", type=int, default=7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.root.exists():
        raise SystemExit(f"refusing to reuse existing experiment root: {args.root}")
    if args.output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing result directory: {args.output_dir}")
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
    initdb = run(
        [str(bin_dir / "initdb"), "-D", str(data_dir), "-U", "postgres", "-A", "trust", "--no-locale", "--encoding=UTF8"],
        lifecycle_dir,
        "initdb",
        environment=env,
    )
    if initdb.returncode != 0:
        return initdb.returncode
    start = run(
        [
            str(bin_dir / "pg_ctl"),
            "-D",
            str(data_dir),
            "-o",
            f"-k {socket_dir} -p {args.port} -c autovacuum=off",
            "-l",
            str(lifecycle_dir / "server.log"),
            "start",
            "-w",
        ],
        lifecycle_dir,
        "pg_ctl-start",
        environment=env,
    )
    if start.returncode != 0:
        return start.returncode
    psql = bin_dir / "psql"
    base = [str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", str(socket_dir), "-p", str(args.port), "-U", "postgres"]
    create_db = run(base + ["-d", "postgres", "-c", f"CREATE DATABASE {args.database};"], lifecycle_dir, "create-database", environment=env)
    if create_db.returncode != 0:
        return create_db.returncode
    fixture = run(base + ["-d", args.database, "-f", str(args.fixture)], lifecycle_dir, "fixture", environment=env)
    if fixture.returncode != 0:
        return fixture.returncode
    benchmark = run(
        [
            sys.executable,
            str(args.fixture.parent / "run_benchmark.py"),
            "--psql",
            str(psql),
            "--host",
            str(socket_dir),
            "--port",
            str(args.port),
            "--database",
            args.database,
            "--output-dir",
            str(args.output_dir / "measurement"),
            "--seed",
            str(args.seed),
            "--repetitions",
            str(args.repetitions),
            "--source-commit",
            args.source_commit,
            "--postgres-binary-sha256",
            sha256(bin_dir / "postgres"),
        ],
        lifecycle_dir,
        "benchmark-wrapper",
        environment=env,
    )
    if benchmark.returncode != 0:
        return benchmark.returncode
    raw_json = args.output_dir / "measurement" / "raw-observations.json"
    analysis = run(
        [
            sys.executable,
            str(args.fixture.parent / "analyze_benchmark.py"),
            str(raw_json),
            "--output-dir",
            str(args.output_dir / "analysis"),
        ],
        lifecycle_dir,
        "offline-analysis",
        environment=env,
    )
    if analysis.returncode != 0:
        return analysis.returncode
    drop_db = run(
        base + ["-d", "postgres", "-c", f"DROP DATABASE {args.database};"],
        lifecycle_dir,
        "drop-database",
        environment=env,
    )
    absence = run(
        base + ["-d", "postgres", "-At", "-c", f"SELECT datname FROM pg_database WHERE datname = '{args.database}';"],
        lifecycle_dir,
        "database-absence",
        environment=env,
    )
    cleanup_before_stop = {
        "drop_database_returncode": drop_db.returncode,
        "database_absence_query_returncode": absence.returncode,
        "database_absence_stdout": absence.stdout,
        "database_absent_while_server_running": absence.returncode == 0 and absence.stdout.strip() == "",
    }
    (args.output_dir / "cleanup-before-stop.json").write_text(json.dumps(cleanup_before_stop, indent=2) + "\n", encoding="utf-8")
    stop = run(
        [str(bin_dir / "pg_ctl"), "-D", str(data_dir), "-m", "fast", "stop", "-w"],
        lifecycle_dir,
        "pg_ctl-stop",
        environment=env,
    )
    server_status = run(
        [str(bin_dir / "pg_ctl"), "-D", str(data_dir), "status"],
        lifecycle_dir,
        "pg_ctl-status-after-stop",
        environment=env,
    )
    evidence = {
        "source_commit": args.source_commit,
        "postgres_binary": str(bin_dir / "postgres"),
        "postgres_binary_sha256": sha256(bin_dir / "postgres"),
        "psql_binary": str(psql),
        "psql_binary_sha256": sha256(psql),
        "database": args.database,
        "socket_dir": str(socket_dir),
        "port": args.port,
        "database_absent_while_server_running": cleanup_before_stop["database_absent_while_server_running"],
        "server_stopped": stop.returncode == 0 and server_status.returncode != 0,
        "temporary_root": str(args.root),
    }
    (args.output_dir / "cleanup-status.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if stop.returncode == 0 and server_status.returncode != 0:
        shutil.rmtree(args.root)
        (args.output_dir / "temporary-root-removed.txt").write_text("removed\n", encoding="utf-8")
    else:
        (args.output_dir / "temporary-root-removed.txt").write_text("not removed; inspect lifecycle logs\n", encoding="utf-8")
    if drop_db.returncode != 0 or not cleanup_before_stop["database_absent_while_server_running"]:
        return 1
    if stop.returncode != 0 or server_status.returncode == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
