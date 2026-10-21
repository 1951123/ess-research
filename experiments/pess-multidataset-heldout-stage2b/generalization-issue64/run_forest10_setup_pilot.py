"""One-shot, capped Forest10 sample-replay setup pilot for Issue #64.

This program reads only the official valid workload (never labels), does not
calibrate/select resources, discards EXPLAIN output, and retains only a small
technical summary. Run only after explicit researcher authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ISSUE64_ROOT = HERE.parents[2]
sys.path.insert(0, str(ISSUE64_ROOT / "src"))

from ess_research.arecel.archive import _ArchiveUnpickler, _open_verified, _query, _schema
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import CSV_SHA256, EXPECTED_ROWS, SOURCE_COLUMNS
from ess_research.task_paths import configured_root, runtime_runs

PILOT_EDGE = ("Elevation", "Aspect")
HARD_WALL_SECONDS = 30 * 60
SOFT_STOP_SECONDS = 28 * 60
HARD_DISK_BYTES = 2 * 1024**3
SOFT_STOP_DISK_BYTES = 1536 * 1024**2
SAMPLE_RELATION_IDENTITY = "6:public8:forest10"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _allocated_bytes(root: Path) -> int:
    total = 0
    pending = [root]
    while pending:
        path = pending.pop()
        info = path.lstat()
        total += info.st_blocks * 512
        if path.is_dir() and not path.is_symlink():
            with os.scandir(path) as entries:
                pending.extend(Path(entry.path) for entry in entries)
    return total


def _extract_csv(data_root: Path, destination: Path) -> None:
    archive_path = data_root / "arecel-data.tar.gz"
    if not archive_path.is_file():
        raise RuntimeError("pinned AreCEL archive is missing locally; network download is disabled")
    destination.parent.mkdir(parents=True, exist_ok=True)
    wanted = "data/forest10/original.csv"
    found = False
    with _open_verified(archive_path) as verified:
        with tarfile.open(fileobj=verified, mode="r|gz") as archive:
            for member in archive:
                if member.name.removeprefix("./") != wanted:
                    continue
                if found or not member.isfile():
                    raise RuntimeError("Forest10 CSV archive member is duplicate or nonregular")
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError("Forest10 CSV archive member cannot be read")
                with source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                found = True
    if not found or _sha256(destination) != CSV_SHA256:
        raise RuntimeError("pinned Forest10 CSV member is missing or its SHA-256 differs")


def _valid_candidate(query: dict[str, Any], edge: tuple[str, str]) -> bool:
    result = discover_candidates([query], SOURCE_COLUMNS)
    return any(
        (row["column_a"], row["column_b"]) == edge
        and row["eligible_valid_query_count"] == 1
        for row in result["candidates"]
    )


def _load_first_valid_query(data_root: Path) -> tuple[str, int, str]:
    """Read the pinned workload pickle only; never open its label pickle."""
    archive_path = data_root / "arecel-data.tar.gz"
    if not archive_path.is_file():
        raise RuntimeError("pinned AreCEL archive is missing locally; network access is disabled")
    workload_member = "data/forest10/workload/base.pkl"
    loaded = None
    with _open_verified(archive_path) as verified:
        with tarfile.open(fileobj=verified, mode="r|gz") as archive:
            for member in archive:
                if member.name.removeprefix("./") != workload_member:
                    continue
                if loaded is not None or not member.isfile():
                    raise RuntimeError("Forest10 workload member is duplicate or nonregular")
                stream = archive.extractfile(member)
                if stream is None:
                    raise RuntimeError("Forest10 workload member cannot be read")
                with stream:
                    loaded = _ArchiveUnpickler(stream).load()
    if not isinstance(loaded, dict) or not isinstance(loaded.get("valid"), list):
        raise RuntimeError("pinned Forest10 workload has no official valid split")
    queries = loaded["valid"]
    if len(queries) != 10_000:
        raise RuntimeError("official Forest10 valid workload does not contain 10,000 queries")
    for source_index, source_query in enumerate(queries):
        query = {
            "query_id": f"arecel:forest10:valid:{source_index:06d}",
            "source_index": source_index,
            **_query(source_query, "forest10"),
        }
        if _valid_candidate(query, PILOT_EDGE):
            if not query["sql"].startswith("SELECT * FROM public.forest10 WHERE "):
                raise RuntimeError("prepared valid query does not target public.forest10")
            return query["query_id"], source_index, query["sql"]
    raise RuntimeError("no official valid query statically supports e00_01")


def _worker(root: Path) -> int:
    started = time.monotonic()
    summary: dict[str, Any] = {
        "format": "ess-issue64-forest10-setup-pilot-v1",
        "status": "FAILED",
        "researcher_approved_scope": "Forest10 setup-only; Empty/e00_01; one valid query; no test access",
        "phases_seconds": {},
        "checks": {},
        "query": {},
        "sample": {},
        "statistics_object": {},
        "explain": {"attempts": 0, "completed": 0, "plan_rows_retained": False},
        "error": None,
    }
    current_phase = "preflight"

    def timed(label: str, function):
        nonlocal current_phase
        current_phase = label
        before = time.monotonic()
        try:
            return function()
        finally:
            summary["phases_seconds"][label] = round(time.monotonic() - before, 3)

    try:
        runtime_root = runtime_runs("ess-research", 64).resolve()
        if root.parent.resolve() != runtime_root or not root.is_dir() or root.is_symlink():
            raise RuntimeError("worker runtime root is not the dedicated pilot directory")
        original_runtime = configured_root("ESS_RUNTIME_PARENT")
        prefix = original_runtime / "issue38" / "pg-prefix"
        pg_source = original_runtime / "issue38" / "pg-src"
        pg_manifest = original_runtime / "issue38" / "results" / "heldout-v1" / "runtime-manifest.json"

        pr58_root = ISSUE64_ROOT.parent / "ess-research-issue48" / "experiments" / "pess-multidataset-heldout-stage2b"
        expected_run_formal_sha = "61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322"
        run_formal_path = pr58_root / "run_formal.py"
        if _sha256(run_formal_path) != expected_run_formal_sha:
            raise RuntimeError("PR #58 run_formal.py does not match the pinned source SHA-256")
        if str(pr58_root) not in sys.path:
            sys.path.insert(0, str(pr58_root))
        import gate_audit_v2 as helpers
        import run_formal
        import forest10_runner as issue64_runner

        if helpers.EXPECTED_PG_COMMIT != "23c7c2fdd4bfb561f3257d947fee956a2999fdb6":
            raise RuntimeError("PR #58 PG source pin differs from the approved protocol")
        source_audit = helpers.audit_pg_source(pg_source)
        binary_audit = helpers.audit_pg_binary(prefix, pg_manifest)
        if source_audit.get("status") != "VERIFIED" or binary_audit.get("status") != "VERIFIED":
            raise RuntimeError("pinned PostgreSQL source/binary audit did not pass")
        sample_source = pg_source / "src/backend/commands/analyze_sample_cache.c"
        if _sha256(sample_source) != "661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68":
            raise RuntimeError("sample-import source file differs from its pinned SHA-256")
        summary["checks"]["postgresql_source_and_binaries"] = "PASS"
        summary["checks"]["pr58_run_formal_sha256"] = expected_run_formal_sha

        query_id, source_index, query_sql = timed(
            "valid_workload_and_query_resolution",
            lambda: _load_first_valid_query(configured_root("ESS_DATA_ROOT")),
        )
        summary["query"] = {
            "query_id": query_id,
            "source_index": source_index,
            "split": "valid",
            "static_e00_01_eligibility": "PASS",
            "same_sql_used_for_both_configurations": True,
        }

        input_root = root / "input"
        input_root.mkdir()
        prepared_root = input_root / "prepared"
        prepared_root.mkdir()
        source_columns, columns, _ = _schema("forest10")
        if tuple(source_columns) != SOURCE_COLUMNS:
            raise RuntimeError("Forest10 source column order differs from pinned ETL")
        schema_sql = "CREATE TABLE public.forest10 (\n" + ",\n".join(
            f'  "{name}" {type_}' for name, type_ in columns
        ) + "\n);\n"
        (prepared_root / "schema.sql").write_text(schema_sql, encoding="utf-8")
        csv_path = input_root / "forest10-original.csv"
        timed("pinned_csv_verification_and_extraction", lambda: _extract_csv(configured_root("ESS_DATA_ROOT"), csv_path))

        candidates = issue64_runner.pr58_candidate_specs((("e00_01", PILOT_EDGE),))
        backend_context = None
        cluster_entered = False
        cluster_lifecycle_start = time.monotonic()
        current_phase = "cluster_start_bootstrap_and_replays"
        try:
            backend_context = helpers.owned_cluster(prefix, root / "cluster", os.environ.copy())
            cluster = backend_context.__enter__()
            cluster_entered = True
            summary["checks"]["independent_cluster_identity"] = "PASS"
            spec = {"catalog_columns": [name for name, _ in columns], "source_rows": EXPECTED_ROWS}
            sample, identity = timed(
                "table_bootstrap_and_one_initial_sample_export_analyze",
                lambda: run_formal.bootstrap_cluster(
                    prefix, cluster, prepared_root, "forest10", spec, csv_path
                ),
            )
            run_formal_identity = {
                "table": identity["table"],
                "header": identity["header"],
                "sha256": identity["sha256"],
            }
            issue64_runner.validate_fresh_sample_identity(sample, run_formal_identity, helpers)
            if identity["table"] != "public.forest10" or identity["header"].get("relation_identity") != SAMPLE_RELATION_IDENTITY:
                raise RuntimeError("fresh sample relation identity/header differs from public.forest10")
            summary["sample"] = {
                "source_relation": identity["table"],
                "relation_identity": identity["header"]["relation_identity"],
                "relation_oid": identity["header"]["relation_oid"],
                "relation_filenode": identity["header"]["relation_filenode"],
                "relation_pages": identity["header"]["relation_pages"],
                "natts": identity["header"]["natts"],
                "server_version": identity["header"]["server_version"],
                "bytes": identity["bytes"],
                "sha256": identity["sha256"],
                "local_path": str(sample),
            }
            summary["checks"]["fresh_same_cluster_sample_export_header_hash"] = "PASS"

            backend = issue64_runner.PR58Forest10Backend(
                run_formal, prefix, cluster, candidates, sample, run_formal_identity
            )
            issue64_runner.validate_fresh_sample_identity(sample, run_formal_identity, helpers)
            empty_ledger = timed("empty_sample_replay_analyze", lambda: backend.configure(()))
            summary["checks"]["empty_replay_same_sample"] = "PASS" if not empty_ledger else "FAIL"
            if empty_ledger:
                raise RuntimeError("Empty configuration unexpectedly returned statistics objects")
            absent = helpers.psql(
                prefix, cluster["socket_dir"], cluster["port"],
                "SELECT count(*) FROM pg_statistic_ext WHERE stxname='ess_issue64_forest10_e00_01';",
                dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib")), tuples=True,
            ).strip()
            if absent != "0":
                raise RuntimeError("e00_01 statistics object was unexpectedly present for Empty")

            explain_sql = "EXPLAIN (FORMAT JSON) " + query_sql
            before = time.monotonic()
            summary["explain"]["attempts"] += 1
            helpers.psql(prefix, cluster["socket_dir"], cluster["port"], explain_sql,
                         dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib")), timeout=60)
            summary["phases_seconds"]["empty_one_valid_explain"] = round(time.monotonic() - before, 3)
            summary["explain"]["completed"] += 1

            issue64_runner.validate_fresh_sample_identity(sample, run_formal_identity, helpers)
            singleton_ledger = timed(
                "e00_01_sample_replay_analyze",
                lambda: backend.configure(("e00_01",)),
            )
            summary["checks"]["e00_01_replay_same_sample"] = "PASS"
            if len(singleton_ledger) != 1 or singleton_ledger[0]["statistic_name"] != candidates[0]["statistic_name"]:
                raise RuntimeError("e00_01 object absent from the PostgreSQL catalog ledger")
            row = singleton_ledger[0]
            expected_keys = "1 2"
            if row["stxkeys"] != expected_keys or row["statistics_target"] != 300:
                raise RuntimeError("e00_01 catalog key order or statistics target differs from protocol")
            catalog = helpers.psql(
                prefix, cluster["socket_dir"], cluster["port"],
                "SELECT (s.stxrelid='public.forest10'::regclass), s.stxkind::text, s.stxkeys::text, s.stxstattarget "
                "FROM pg_statistic_ext s WHERE s.stxname='ess_issue64_forest10_e00_01';",
                dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib")), tuples=True,
            ).strip()
            if catalog != "t|{m}|1 2|300":
                raise RuntimeError("e00_01 relation/kind/keys/target catalog verification failed")
            summary["statistics_object"] = {
                "name": row["statistic_name"],
                "oid": row["oid"],
                "relation": "public.forest10",
                "kind": "mcv",
                "stxkeys": row["stxkeys"],
                "statistics_target": row["statistics_target"],
                "catalog_verification": "PASS",
            }

            before = time.monotonic()
            summary["explain"]["attempts"] += 1
            helpers.psql(prefix, cluster["socket_dir"], cluster["port"], explain_sql,
                         dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib")), timeout=60)
            summary["phases_seconds"]["e00_01_one_valid_explain"] = round(time.monotonic() - before, 3)
            summary["explain"]["completed"] += 1
            summary["checks"]["same_query_two_explains_no_values_retained"] = "PASS"
            summary["status"] = "SUCCESS"
        finally:
            if backend_context is not None and cluster_entered:
                backend_context.__exit__(None, None, None)
            summary["phases_seconds"]["cluster_lifecycle_including_shutdown"] = round(
                time.monotonic() - cluster_lifecycle_start, 3
            )
            current_phase = "local_cleanup"
            (input_root / "forest10-original.csv").unlink(missing_ok=True)
            (prepared_root / "schema.sql").unlink(missing_ok=True)
            try:
                (root / "cluster" / "server.log").unlink(missing_ok=True)
            except OSError:
                pass
        summary["checks"]["postgresql_shutdown"] = "PASS"
    except BaseException as exc:
        summary["status"] = "FAILED"
        message = str(exc).splitlines()[0][:300]
        if "command failed:" in message:
            message = "PostgreSQL command failed; SQL and raw diagnostics intentionally not retained"
        summary["error"] = {"phase": current_phase, "type": type(exc).__name__, "message": message}
    summary["worker_elapsed_seconds"] = round(time.monotonic() - started, 3)
    output = root / "pilot-worker-summary.json"
    output.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "SUCCESS" else 2


def _supervise(root: Path) -> int:
    original_runtime = configured_root("ESS_RUNTIME_PARENT")
    root = root.resolve()
    if root.is_symlink() or root.parent.resolve() != runtime_runs("ess-research", 64).resolve():
        raise RuntimeError("pilot directory is not a newly isolated Issue #64 runtime child")
    env = dict(os.environ)
    log_path = root / "worker-console.log"
    started = time.monotonic()
    peak = 0
    stop_reason: str | None = None
    with log_path.open("xb") as console:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)],
            env=env,
            stdout=console,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        while process.poll() is None:
            elapsed = time.monotonic() - started
            try:
                current = _allocated_bytes(root)
            except OSError:
                current = HARD_DISK_BYTES + 1
            peak = max(peak, current)
            if current >= SOFT_STOP_DISK_BYTES:
                stop_reason = "disk_safety_abort_1.5_GiB"
                break
            if elapsed >= SOFT_STOP_SECONDS:
                stop_reason = "wall_safety_abort_28_minutes"
                break
            time.sleep(0.1)
        if stop_reason is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        return_code = process.wait()

    elapsed = time.monotonic() - started
    peak = max(peak, _allocated_bytes(root))
    if stop_reason is None and peak >= SOFT_STOP_DISK_BYTES:
        stop_reason = "disk_safety_abort_1.5_GiB"
    if stop_reason is None and elapsed >= SOFT_STOP_SECONDS:
        stop_reason = "wall_safety_abort_28_minutes"
    cluster_data = root / "cluster" / "pgdata"
    if (stop_reason is not None or return_code != 0) and cluster_data.exists():
        pg_ctl = original_runtime / "issue38" / "pg-prefix" / "bin" / "pg_ctl"
        try:
            status = subprocess.run(
                [str(pg_ctl), "-D", str(cluster_data), "status"],
                env=dict(env, LD_LIBRARY_PATH=str(pg_ctl.parent.parent / "lib")),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if status.returncode == 0:
                subprocess.run(
                    [str(pg_ctl), "-D", str(cluster_data), "-m", "fast", "-w", "stop"],
                    env=dict(env, LD_LIBRARY_PATH=str(pg_ctl.parent.parent / "lib")),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
        except (OSError, subprocess.TimeoutExpired):
            pass
        elapsed = time.monotonic() - started
        try:
            (root / "cluster" / "server.log").unlink(missing_ok=True)
        except OSError:
            pass
    if elapsed > HARD_WALL_SECONDS or peak >= HARD_DISK_BYTES:
        stop_reason = stop_reason or "hard_cap_exceeded_or_monitor_late"
    worker_summary_path = root / "pilot-worker-summary.json"
    worker_summary = None
    if worker_summary_path.is_file():
        worker_summary = json.loads(worker_summary_path.read_text(encoding="utf-8"))
    final = {
        "format": "ess-issue64-forest10-setup-pilot-supervisor-v1",
        "status": "ABORTED" if stop_reason else (worker_summary or {}).get("status", "FAILED"),
        "stop_reason": stop_reason,
        "worker_exit_code": return_code,
        "elapsed_seconds": round(elapsed, 3),
        "elapsed_cap_seconds": HARD_WALL_SECONDS,
        "peak_allocated_disk_bytes": peak,
        "hard_disk_cap_bytes": HARD_DISK_BYTES,
        "watchdog_abort_threshold_bytes": SOFT_STOP_DISK_BYTES,
        "sample_and_cluster_runtime_path": str(root),
        "worker_summary": worker_summary,
        "worker_log": str(log_path),
    }
    (root / "pilot-supervisor-summary.json").write_text(
        json.dumps(final, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(final, sort_keys=True))
    return 0 if final["status"] == "SUCCESS" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--researcher-approved", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        return _worker(args.worker.resolve())
    if not args.researcher_approved:
        raise SystemExit("refusing to run without explicit --researcher-approved")
    runs = runtime_runs("ess-research", 64)
    runs.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(runs).free < HARD_DISK_BYTES:
        raise SystemExit("refusing pilot: runtime filesystem has less than the 2-GiB cap available")
    root = Path(tempfile.mkdtemp(prefix="forest10-setup-pilot-", dir=runs))
    print(f"PILOT_RUNTIME_ROOT={root}", flush=True)
    return _supervise(root)


if __name__ == "__main__":
    raise SystemExit(main())
