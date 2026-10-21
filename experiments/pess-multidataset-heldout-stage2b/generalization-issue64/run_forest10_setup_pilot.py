"""One-shot, capped Forest10 sample-replay setup pilot for Issue #64.

This program reads only the official valid workload (never labels), does not
calibrate/select resources, discards EXPLAIN output, and retains only a small
technical summary. Run only after explicit researcher authorization.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

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
DISK_SCAN_RACE_RETRIES = 2
TRANSIENT_DISK_SCAN_ERRNOS = {errno.ENOENT, getattr(errno, "ESTALE", -1)}
SAMPLE_RELATION_IDENTITY = "6:public8:forest10"
PILOT_RUNTIME_PREFIX = "f10-"
# The pinned Linux PostgreSQL build uses sockaddr_un.sun_path[108].
UNIX_SOCKET_PATH_MAX_BYTES = 107


def _validate_socket_path(root: Path) -> int:
    """Allow room for the largest port before creating any PostgreSQL process."""
    length = len(os.fsencode(str(root / "cluster" / "socket" / ".s.PGSQL.65535")))
    if length > UNIX_SOCKET_PATH_MAX_BYTES:
        raise RuntimeError(
            f"Unix socket path needs {length} bytes; pinned Linux limit is {UNIX_SOCKET_PATH_MAX_BYTES}"
        )
    return length


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _allocated_bytes(root: Path) -> int:
    for attempt in range(DISK_SCAN_RACE_RETRIES + 1):
        total = 0
        pending = [root]
        race_error: OSError | None = None
        while pending:
            path = pending.pop()
            try:
                info = path.lstat()
                total += info.st_blocks * 512
                if stat.S_ISDIR(info.st_mode):
                    with os.scandir(path) as entries:
                        pending.extend(Path(entry.path) for entry in entries)
            except OSError as exc:
                if path != root and exc.errno in TRANSIENT_DISK_SCAN_ERRNOS:
                    race_error = exc
                    break
                raise
        if race_error is None:
            return total
        if attempt == DISK_SCAN_RACE_RETRIES:
            raise race_error
    raise AssertionError("unreachable disk scan retry state")


def _safe_pg_cause(stderr: str) -> str:
    text = stderr.lower()
    if "unix-domain socket path" in text and "is too long" in text:
        return "unix_socket_path_too_long"
    if "permission denied" in text:
        return "permission_denied"
    if "address already in use" in text or "could not bind" in text:
        return "port_bind_failure"
    if "no space left on device" in text:
        return "no_space_left"
    if "could not connect" in text or "connection refused" in text:
        return "connection_failure"
    if "could not start server" in text:
        return "server_start_failure"
    if "no server running" in text:
        return "server_not_running"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if "fatal:" in text or "error:" in text:
        return "postgresql_reported_error"
    return "nonzero_exit"


class PilotPostgreSQLFailure(RuntimeError):
    """Bounded diagnostic for one PG startup/setup command; never stores SQL/output."""

    def __init__(
        self,
        phase: str,
        program: str,
        cause: str,
        exit_code: int | None,
        *,
        error_class: str = "PostgreSQLCommandError",
        error_number: int | None = None,
    ) -> None:
        super().__init__("PostgreSQL command failed; SQL and command output omitted")
        self.phase = phase
        self.program = program
        self.cause = cause
        self.exit_code = exit_code
        self.error_class = error_class
        self.error_number = error_number

    def record(self) -> dict[str, Any]:
        command = {"program": self.program, "cause": self.cause, "exit_code": self.exit_code}
        if self.error_number is not None:
            command["errno"] = self.error_number
        return {
            "phase": self.phase,
            "type": self.error_class,
            "message": "PostgreSQL command failed; SQL and command output omitted",
            "postgresql_command": command,
        }


def _classify_pg_command(command: list[str]) -> tuple[str, str]:
    """Return a fixed stage/program label without retaining command arguments."""
    program = Path(command[0]).name if command else "unknown"
    if program not in {"initdb", "pg_ctl", "psql"}:
        program = "postgresql_command"
    if program == "initdb":
        return "initdb", program
    if program == "pg_ctl":
        action = command[-1].lower() if len(command) > 1 else ""
        if action == "start":
            return "pg_ctl_start", program
        if action == "stop":
            return "pg_ctl_stop", program
        return "pg_ctl_command", program
    if program != "psql":
        return "postgresql_command", program

    sql = command[command.index("-c") + 1] if "-c" in command and command.index("-c") + 1 < len(command) else ""
    normalized = re.sub(r"\s+", " ", sql.strip().lower())
    if "current_setting('data_directory')" in normalized and "current_database()" in normalized:
        return "psql_identity_check", program
    if normalized.startswith("create table public.forest10"):
        return "schema_create", program
    if normalized.startswith("\\copy public.forest10 from "):
        return "csv_import", program
    if "ess.analyze_sample_export" in normalized and "analyze public.forest10" in normalized:
        return "sample_export_analyze", program
    if "ess.analyze_sample_import" in normalized and "analyze public.forest10" in normalized:
        return "sample_replay_analyze", program
    if normalized.startswith("select count(*) from public.forest10"):
        return "csv_import_verify", program
    if normalized.startswith("alter table public.forest10"):
        return "column_statistics_target", program
    if normalized.startswith(("create statistics ", "drop statistics ")):
        return "statistics_object_setup", program
    if normalized.startswith("analyze public.forest10"):
        return "sample_replay_analyze", program
    if normalized.startswith("explain "):
        return "valid_explain", program
    return "psql_command", program


def _run_diagnostic_pg_command(
    command: list[str],
    *,
    env: dict[str, str],
    input_text: str | None = None,
    timeout: int = 180,
    phase_sink: Callable[[str], None] | None = None,
    failure_sink: list[dict[str, Any]] | None = None,
) -> subprocess.CompletedProcess[str]:
    phase, program = _classify_pg_command(command)
    if phase_sink is not None:
        phase_sink(phase)
    try:
        result = subprocess.run(
            command,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        failure = PilotPostgreSQLFailure(phase, program, "timeout", None, error_class="TimeoutExpired")
        if failure_sink is not None:
            failure_sink.append(failure.record())
        raise failure from None
    except OSError as exc:
        cause = "command_unavailable" if exc.errno == errno.ENOENT else (
            "permission_denied" if exc.errno in {errno.EACCES, errno.EPERM} else "command_os_error"
        )
        failure = PilotPostgreSQLFailure(
            phase,
            program,
            cause,
            None,
            error_class=type(exc).__name__,
            error_number=exc.errno,
        )
        if failure_sink is not None:
            failure_sink.append(failure.record())
        raise failure from None
    if result.returncode:
        cause = _safe_pg_cause(f"{result.stderr}\n{result.stdout}")
        # pg_ctl normally emits only "could not start server". Consult its
        # startup-only log before cleanup, retaining a fixed category, no text.
        if phase == "pg_ctl_start" and "-l" in command:
            log_index = command.index("-l") + 1
            if log_index < len(command):
                try:
                    with Path(command[log_index]).open("rb") as startup_log:
                        log_cause = _safe_pg_cause(startup_log.read(64 * 1024).decode("utf-8", errors="replace"))
                    if log_cause != "nonzero_exit":
                        cause = log_cause
                except OSError:
                    pass  # Preserve the pg_ctl cause if its log is unavailable.
        failure = PilotPostgreSQLFailure(
            phase,
            program,
            cause,
            result.returncode,
        )
        if failure_sink is not None:
            failure_sink.append(failure.record())
        raise failure from None
    return result


def _install_pinned_pg_diagnostics(
    helpers: Any,
    *,
    phase_sink: Callable[[str], None],
    failure_sink: list[dict[str, Any]],
) -> Callable[[], None]:
    """Instrument the pinned PR #58 call path and return a restoration callback."""
    original_run_command = helpers.run_command
    original_validate_identity = helpers.validate_cluster_identity

    def diagnostic_run_command(command, *, env, input_text=None, timeout=180):
        return _run_diagnostic_pg_command(
            command,
            env=env,
            input_text=input_text,
            timeout=timeout,
            phase_sink=phase_sink,
            failure_sink=failure_sink,
        )

    def diagnostic_validate_identity(fields, pgdata, port):
        phase_sink("psql_identity_check")
        try:
            return original_validate_identity(fields, pgdata, port)
        except RuntimeError:
            failure = PilotPostgreSQLFailure(
                "psql_identity_check",
                "psql",
                "identity_mismatch",
                None,
                error_class="ClusterIdentityError",
            )
            failure_sink.append(failure.record())
            raise failure from None

    helpers.run_command = diagnostic_run_command
    helpers.validate_cluster_identity = diagnostic_validate_identity

    def restore() -> None:
        helpers.run_command = original_run_command
        helpers.validate_cluster_identity = original_validate_identity

    return restore


def _merge_pg_failures(summary: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    """Keep the earliest operation failure primary and later shutdown failures separate."""
    if not failures:
        return
    cleanup_phases = {"pg_ctl_stop", "postgresql_shutdown"}
    primary = next((item for item in failures if item["phase"] not in cleanup_phases), None)
    existing = summary.get("error")
    if primary is not None and (existing is None or "postgresql_command" in existing):
        summary["error"] = primary
        summary["status"] = "FAILED"
    cleanup_errors = summary.setdefault("cleanup_errors", [])
    skipped_primary = False
    for item in failures:
        if primary is item and not skipped_primary:
            skipped_primary = True
            continue
        if item not in cleanup_errors:
            cleanup_errors.append(item)


def _worker_error_record(exc: BaseException, phase: str) -> dict[str, Any]:
    if isinstance(exc, PilotPostgreSQLFailure):
        return exc.record()
    message = str(exc).splitlines()[0][:300]
    if "command failed:" in message:
        raw_stderr = str(exc).partition("\nstderr=")[2]
        cause = _safe_pg_cause(raw_stderr.splitlines()[0] if raw_stderr else "")
        return {
            "phase": phase,
            "type": type(exc).__name__,
            "message": "PostgreSQL command failed; SQL and command output omitted",
            "postgresql_command": {"cause": cause, "exit_code": None},
        }
    return {"phase": phase, "type": type(exc).__name__, "message": message}


def _record_cleanup_error(summary: dict[str, Any], exc: BaseException, phase: str) -> None:
    summary.setdefault("cleanup_errors", []).append(_worker_error_record(exc, phase))


def _watchdog_stop_reason(allocated_bytes: int, elapsed_seconds: float) -> str | None:
    if allocated_bytes >= SOFT_STOP_DISK_BYTES:
        return "disk_safety_abort_1.5_GiB"
    if elapsed_seconds >= SOFT_STOP_SECONDS:
        return "wall_safety_abort_28_minutes"
    return None


def _monitor_error_record(exc: OSError) -> dict[str, Any]:
    return {"error_class": type(exc).__name__, "errno": exc.errno}


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
        summary["checks"]["unix_socket_path_bytes_upper_bound"] = _validate_socket_path(root)
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
        pg_command_failures: list[dict[str, Any]] = []

        def set_pg_phase(phase: str) -> None:
            nonlocal current_phase
            current_phase = phase

        restore_pg_helpers = _install_pinned_pg_diagnostics(
            helpers,
            phase_sink=set_pg_phase,
            failure_sink=pg_command_failures,
        )
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
        except BaseException as exc:
            summary["status"] = "FAILED"
            summary["error"] = _worker_error_record(exc, current_phase)
        finally:
            current_phase = "postgresql_shutdown"
            if backend_context is not None and cluster_entered:
                try:
                    backend_context.__exit__(None, None, None)
                    summary["checks"]["postgresql_shutdown"] = "PASS"
                except BaseException as exc:
                    summary["status"] = "FAILED"
                    if not isinstance(exc, PilotPostgreSQLFailure):
                        _record_cleanup_error(summary, exc, current_phase)
                    summary["checks"]["postgresql_shutdown"] = "FAIL"
            summary["phases_seconds"]["cluster_lifecycle_including_shutdown"] = round(
                time.monotonic() - cluster_lifecycle_start, 3
            )
            current_phase = "local_file_cleanup"
            try:
                (input_root / "forest10-original.csv").unlink(missing_ok=True)
                (prepared_root / "schema.sql").unlink(missing_ok=True)
            except OSError as exc:
                summary["status"] = "FAILED"
                _record_cleanup_error(summary, exc, current_phase)
            try:
                (root / "cluster" / "server.log").unlink(missing_ok=True)
            except OSError:
                pass
            restore_pg_helpers()
        _merge_pg_failures(summary, pg_command_failures)
    except BaseException as exc:
        summary["status"] = "FAILED"
        summary["error"] = _worker_error_record(exc, current_phase)
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
    peak: int | None = 0
    disk_monitor_error: dict[str, Any] | None = None
    postgresql_cleanup: dict[str, Any] | None = None
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
            except OSError as exc:
                peak = None
                disk_monitor_error = _monitor_error_record(exc)
                stop_reason = "disk_monitor_unavailable"
                break
            peak = max(peak or 0, current)
            stop_reason = _watchdog_stop_reason(current, elapsed)
            if stop_reason is not None:
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
    if peak is not None:
        try:
            peak = max(peak, _allocated_bytes(root))
        except OSError as exc:
            peak = None
            disk_monitor_error = _monitor_error_record(exc)
            stop_reason = stop_reason or "disk_monitor_unavailable"
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
                stopped = subprocess.run(
                    [str(pg_ctl), "-D", str(cluster_data), "-m", "fast", "-w", "stop"],
                    env=dict(env, LD_LIBRARY_PATH=str(pg_ctl.parent.parent / "lib")),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if stopped.returncode:
                    postgresql_cleanup = {
                        "program": "pg_ctl",
                        "operation": "stop",
                        "exit_code": stopped.returncode,
                        "cause": _safe_pg_cause(stopped.stderr),
                    }
            elif status.returncode != 3:
                postgresql_cleanup = {
                    "program": "pg_ctl",
                    "operation": "status",
                    "exit_code": status.returncode,
                    "cause": _safe_pg_cause(status.stderr),
                }
        except subprocess.TimeoutExpired:
            postgresql_cleanup = {
                "program": "pg_ctl",
                "operation": "cleanup",
                "exit_code": None,
                "cause": "timeout",
            }
        except OSError as exc:
            postgresql_cleanup = {
                "program": "pg_ctl",
                "operation": "cleanup",
                "exit_code": None,
                "cause": "command_unavailable" if exc.errno == errno.ENOENT else "command_os_error",
                "errno": exc.errno,
            }
        elapsed = time.monotonic() - started
        try:
            (root / "cluster" / "server.log").unlink(missing_ok=True)
        except OSError:
            pass
    if elapsed > HARD_WALL_SECONDS or (peak is not None and peak >= HARD_DISK_BYTES):
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
        "peak_disk_measurement": "MEASURED" if peak is not None else "UNKNOWN",
        "disk_monitor_error": disk_monitor_error,
        "hard_disk_cap_bytes": HARD_DISK_BYTES,
        "watchdog_abort_threshold_bytes": SOFT_STOP_DISK_BYTES,
        "postgresql_cleanup": postgresql_cleanup,
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
    root = Path(tempfile.mkdtemp(prefix=PILOT_RUNTIME_PREFIX, dir=runs))
    print(f"PILOT_RUNTIME_ROOT={root}", flush=True)
    return _supervise(root)


if __name__ == "__main__":
    raise SystemExit(main())
