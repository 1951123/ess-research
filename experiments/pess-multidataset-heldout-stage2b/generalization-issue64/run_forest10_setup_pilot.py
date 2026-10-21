"""One-shot, capped JSON-only Forest10 integration pilot for Issue #64.

This program reads only the official valid workload (never labels), does not
calibrate/select resources, discards EXPLAIN output, and retains only a small
technical summary. Run only after explicit researcher authorization.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import io
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
from decimal import Decimal
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
PILOT_QUERY_ID = "arecel:forest10:valid:000005"
PILOT_QUERY_INDEX = 5
MCV_NUMERIC_FIELDS = ("simple_sel", "mcv_sel", "mcv_basesel", "mcv_totalsel", "stat_sel")
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
ESS_POSTGRESQL_OBJECT_STORE = Path("/home/wqts/projects/ess-postgresql")
ESS_POSTGRESQL_COMMIT = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
PR58_REPOSITORY_URL = "https://github.com/1951123/ess-research.git"
PR58_SOURCE_COMMIT = "76106024611ae91505f1f05bdc35aed44d9c38c4"
PR58_RUN_FORMAL_SHA256 = "61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322"
PR58_GATE_AUDIT_SHA256 = "03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4"
PR58_HELPER_FILES = (
    "experiments/pess-multidataset-heldout-stage2b/run_formal.py",
    "experiments/pess-multidataset-heldout-stage2b/gate_audit_v2.py",
)
SAMPLE_IMPORT_SOURCE_SHA256 = "661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68"


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


def _pinned_pr58_root(run_root: Path) -> Path:
    """Return the helper directory inside this run's private source checkout."""
    return run_root / "pr58-source" / "experiments" / "pess-multidataset-heldout-stage2b"


def _run_pr58_git(source_root: Path, args: list[str]) -> str:
    """Run one pinned-source Git operation and fail with its precise stage."""
    phase = "git " + " ".join(args[:2])
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), *args],
            capture_output=True, text=True, check=False, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        reason = "timeout" if isinstance(exc, subprocess.TimeoutExpired) else type(exc).__name__
        raise RuntimeError(f"PR #58 source acquisition failed during {phase}: {reason}") from None
    if result.returncode:
        detail = (result.stderr or "").strip().splitlines()
        safe_detail = detail[-1][:240] if detail else "no Git diagnostic"
        raise RuntimeError(
            f"PR #58 source acquisition failed during {phase} "
            f"(exit {result.returncode}): {safe_detail}"
        )
    return result.stdout.strip()


def _fetch_pinned_pr58_source(run_root: Path) -> Path:
    """Fetch only the two pinned PR #58 helpers into this isolated run."""
    runs_root = runtime_runs("ess-research", 64).resolve()
    if run_root.is_symlink():
        raise RuntimeError("PR #58 source requires a direct, non-symlink Issue #64 run directory")
    run_root = run_root.resolve(strict=True)
    if run_root.parent != runs_root or not run_root.is_dir():
        raise RuntimeError("PR #58 source requires a direct, non-symlink Issue #64 run directory")
    source_root = run_root / "pr58-source"
    try:
        source_root.mkdir()
    except FileExistsError:
        raise RuntimeError("PR #58 source directory already exists; refusing reuse or overwrite") from None

    _run_pr58_git(source_root, ["init", "--quiet"])
    _run_pr58_git(source_root, ["remote", "add", "origin", PR58_REPOSITORY_URL])
    _run_pr58_git(
        source_root,
        ["fetch", "--depth=1", "--filter=blob:none", "origin", PR58_SOURCE_COMMIT],
    )
    fetched = _run_pr58_git(source_root, ["rev-parse", "FETCH_HEAD"])
    if fetched != PR58_SOURCE_COMMIT:
        raise RuntimeError(
            f"PR #58 fetched commit mismatch: expected {PR58_SOURCE_COMMIT}, got {fetched}"
        )
    _run_pr58_git(source_root, ["sparse-checkout", "init", "--no-cone"])
    _run_pr58_git(
        source_root,
        ["sparse-checkout", "set", "--no-cone", "--", *[f"/{path}" for path in PR58_HELPER_FILES]],
    )
    _run_pr58_git(source_root, ["checkout", "--detach", "FETCH_HEAD"])
    head = _run_pr58_git(source_root, ["rev-parse", "HEAD"])
    if head != PR58_SOURCE_COMMIT:
        raise RuntimeError(f"PR #58 checkout commit mismatch: expected {PR58_SOURCE_COMMIT}, got {head}")

    source_dir = source_root / "experiments" / "pess-multidataset-heldout-stage2b"
    expected_hashes = {
        "run_formal.py": PR58_RUN_FORMAL_SHA256,
        "gate_audit_v2.py": PR58_GATE_AUDIT_SHA256,
    }
    for name, expected in expected_hashes.items():
        path = source_dir / name
        try:
            actual = _sha256(path)
        except OSError as exc:
            raise RuntimeError(f"PR #58 required source file unavailable: {name} ({type(exc).__name__})") from None
        if actual != expected:
            raise RuntimeError(
                f"PR #58 {name} SHA-256 mismatch: expected {expected}, got {actual}"
            )
    status = _run_pr58_git(source_root, ["status", "--porcelain"])
    if status:
        raise RuntimeError("PR #58 sparse source checkout is unexpectedly modified")
    return source_dir


def _load_pinned_pr58_modules(run_root: Path) -> tuple[Any, Any, dict[str, str]]:
    """Import helpers only after per-run fetch, commit, and content verification."""
    source_root = _fetch_pinned_pr58_source(run_root)
    run_formal_path = source_root / "run_formal.py"
    gate_audit_path = source_root / "gate_audit_v2.py"
    pinned_paths = {"run_formal": run_formal_path.resolve(), "gate_audit_v2": gate_audit_path.resolve()}
    for module_name, expected_path in pinned_paths.items():
        loaded = sys.modules.get(module_name)
        loaded_path = getattr(loaded, "__file__", None) if loaded is not None else None
        if loaded_path is not None and Path(loaded_path).resolve() != expected_path:
            raise RuntimeError(f"refusing non-pinned cached PR #58 module: {module_name}")
    source_str = str(source_root)
    if source_str in sys.path:
        sys.path.remove(source_str)
    sys.path.insert(0, source_str)
    import gate_audit_v2
    import run_formal

    return gate_audit_v2, run_formal, {
        "pr58_source_commit": PR58_SOURCE_COMMIT,
        "run_formal_sha256": PR58_RUN_FORMAL_SHA256,
        "gate_audit_v2_sha256": PR58_GATE_AUDIT_SHA256,
        "pr58_source_path": str(source_root.parent.parent),
    }


def _run_build_command(
    command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path,
    phase: str, phase_sink: Callable[[str], None], phase_times: dict[str, float], timeout: int,
) -> subprocess.CompletedProcess[str]:
    phase_sink(phase)
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=cwd, env=env, text=True, capture_output=True,
            check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise PilotPostgreSQLFailure(phase, Path(command[0]).name, "timeout", None) from None
    finally:
        phase_times[phase] = round(time.monotonic() - started, 3)
    with log_path.open("ab") as log:
        log.write((result.stdout or "").encode("utf-8", errors="replace"))
        log.write((result.stderr or "").encode("utf-8", errors="replace"))
    if result.returncode:
        raise PilotPostgreSQLFailure(
            phase, Path(command[0]).name, _safe_pg_cause(result.stderr or ""), result.returncode
        )
    return result


def _materialize_pinned_postgresql_source(run_root: Path) -> tuple[Path, str]:
    """Export only the pinned commit from the local Git object store into this run."""
    runs_root = runtime_runs("ess-research", 64).resolve()
    if run_root.is_symlink():
        raise RuntimeError("PostgreSQL source requires a direct, non-symlink Issue #64 run directory")
    run_root = run_root.resolve(strict=True)
    if run_root.parent != runs_root or not run_root.is_dir():
        raise RuntimeError("PostgreSQL source requires a direct, non-symlink Issue #64 run directory")

    object_store = ESS_POSTGRESQL_OBJECT_STORE
    pin = ESS_POSTGRESQL_COMMIT
    if len(pin) != 40 or any(ch not in "0123456789abcdef" for ch in pin):
        raise RuntimeError("pinned PostgreSQL source commit is not a full lowercase SHA-1")

    def git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
        try:
            result = subprocess.run(
                ["git", "-C", str(object_store), *args],
                check=False, capture_output=True, text=not binary, timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            reason = "timeout" if isinstance(exc, subprocess.TimeoutExpired) else type(exc).__name__
            raise RuntimeError(f"pinned PostgreSQL source acquisition failed during {args[0]}: {reason}") from None
        if result.returncode:
            stderr = result.stderr.decode("utf-8", "replace") if binary else (result.stderr or "")
            detail = stderr.strip().splitlines()
            safe_detail = detail[-1][:200] if detail else "no Git diagnostic"
            raise RuntimeError(
                f"pinned PostgreSQL source acquisition failed during {args[0]} "
                f"(exit {result.returncode}): {safe_detail}"
            )
        return result

    resolved = git(["rev-parse", "--verify", f"{pin}^{{commit}}"]).stdout.strip()
    if resolved != pin:
        raise RuntimeError("local PostgreSQL object store resolved a different commit than the immutable pin")

    pg_root = run_root / "postgresql"
    pg_root.mkdir(exist_ok=True)
    source = pg_root / "source"
    try:
        source.mkdir()
    except FileExistsError:
        raise RuntimeError("PostgreSQL source directory already exists; refusing reuse or overwrite") from None

    archive = git(["archive", "--format=tar", pin], binary=True).stdout
    if not archive:
        raise RuntimeError("pinned PostgreSQL source archive is empty")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            members = tar.getmembers()
            for member in members:
                member_path = Path(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise RuntimeError("pinned PostgreSQL source archive contains an unsafe path")
                if not (member.isdir() or member.isfile()):
                    raise RuntimeError("pinned PostgreSQL source archive contains a non-regular entry")
            tar.extractall(path=source, members=members, filter="data")
    except (tarfile.TarError, OSError) as exc:
        raise RuntimeError(f"pinned PostgreSQL source archive extraction failed: {type(exc).__name__}") from None

    if not (source / "configure").is_file():
        raise RuntimeError("pinned PostgreSQL source extraction is incomplete (configure missing)")
    source_hash = _sha256(source / "src/backend/commands/analyze_sample_cache.c")
    if source_hash != SAMPLE_IMPORT_SOURCE_SHA256:
        raise RuntimeError("pinned PostgreSQL sample-import source SHA-256 mismatch")
    return source, resolved


def _prepare_owned_postgresql(
    run_root: Path, *, phase_sink: Callable[[str], None], phase_times: dict[str, float]
) -> tuple[Path, Path, dict[str, Any]]:
    """Fetch, build out-of-tree, and install PR #7 PostgreSQL inside this run."""
    pg_root = run_root / "postgresql"
    pg_root.mkdir()
    source = pg_root / "source"
    build = pg_root / "build"
    prefix = pg_root / "install"
    log_path = pg_root / "build.log"
    env = dict(os.environ, LC_ALL="C")
    source, head = _materialize_pinned_postgresql_source(run_root)

    build.mkdir()
    _run_build_command(
        [str(source / "configure"), f"--prefix={prefix}", "--without-readline", "--without-zlib"],
        cwd=build, env=env, log_path=log_path, phase="postgresql_configure",
        phase_sink=phase_sink, phase_times=phase_times, timeout=300,
    )
    _run_build_command(
        ["make", "-j2"], cwd=build, env=env, log_path=log_path,
        phase="postgresql_compile", phase_sink=phase_sink, phase_times=phase_times, timeout=1200,
    )
    _run_build_command(
        ["make", "install"], cwd=build, env=env, log_path=log_path,
        phase="postgresql_install", phase_sink=phase_sink, phase_times=phase_times, timeout=300,
    )
    binaries = {name: prefix / "bin" / name for name in ("postgres", "initdb", "pg_ctl", "psql", "pg_config")}
    if any(not path.is_file() for path in binaries.values()):
        raise RuntimeError("fresh PostgreSQL install is missing a required executable")
    hashes = {name: _sha256(path) for name, path in binaries.items()}
    versions = {}
    for name in ("postgres", "pg_config"):
        result = subprocess.run(
            [str(binaries[name]), "--version"], env=dict(env, LD_LIBRARY_PATH=str(prefix / "lib")),
            check=True, capture_output=True, text=True, timeout=15,
        )
        versions[name] = result.stdout.strip()
    if any("16.14" not in version for version in versions.values()):
        raise RuntimeError("fresh PostgreSQL binaries are not version 16.14")
    return prefix, source, {
        "source_acquisition": "local_git_archive_into_private_run",
        "object_store": str(ESS_POSTGRESQL_OBJECT_STORE),
        "commit": head,
        "sample_import_source_sha256": SAMPLE_IMPORT_SOURCE_SHA256,
        "calibration_interface": "PR7StructuredExplainAdapter; ESS_DIAGNOSTICS JSON",
        "binary_sha256": hashes,
        "versions": versions,
        "build_mode": "out_of_tree_private_per_run",
    }


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
    if "explain (ess_diagnostics, format json, summary off)" in normalized:
        return "structured_valid_explain", program
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
    phase_times: dict[str, float] | None = None,
) -> Callable[[], None]:
    """Instrument the pinned PR #58 call path and return a restoration callback."""
    original_run_command = helpers.run_command
    original_validate_identity = helpers.validate_cluster_identity

    def diagnostic_run_command(command, *, env, input_text=None, timeout=180):
        phase, _program = _classify_pg_command(command)
        started = time.monotonic()
        try:
            return _run_diagnostic_pg_command(
                command,
                env=env,
                input_text=input_text,
                timeout=timeout,
                phase_sink=phase_sink,
                failure_sink=failure_sink,
            )
        finally:
            if phase_times is not None:
                phase_times[phase] = round(
                    phase_times.get(phase, 0.0) + time.monotonic() - started, 3
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


def _watchdog_stop_reason(
    allocated_bytes: int,
    elapsed_seconds: float,
    *,
    disk_threshold_bytes: int = SOFT_STOP_DISK_BYTES,
    wall_threshold_seconds: int = SOFT_STOP_SECONDS,
) -> str | None:
    if allocated_bytes >= disk_threshold_bytes:
        return (
            "disk_safety_abort_1.5_GiB"
            if disk_threshold_bytes == SOFT_STOP_DISK_BYTES
            else "disk_safety_abort_custom"
        )
    if elapsed_seconds >= wall_threshold_seconds:
        return (
            "wall_safety_abort_28_minutes"
            if wall_threshold_seconds == SOFT_STOP_SECONDS
            else "wall_safety_abort_custom"
        )
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


def _fixed_valid_query(queries: list[Any]) -> dict[str, Any]:
    """Resolve only official valid query 000005; never substitute another query."""
    if len(queries) != 10_000 or PILOT_QUERY_INDEX >= len(queries):
        raise RuntimeError("official Forest10 valid workload does not contain the fixed query")
    source_query = queries[PILOT_QUERY_INDEX]
    query = {
        "query_id": f"arecel:forest10:valid:{PILOT_QUERY_INDEX:06d}",
        "source_index": PILOT_QUERY_INDEX,
        **_query(source_query, "forest10"),
    }
    if query["query_id"] != PILOT_QUERY_ID or not _valid_candidate(query, PILOT_EDGE):
        raise RuntimeError("fixed official valid query is not statically eligible for e00_01")
    if not query["sql"].startswith("SELECT * FROM public.forest10 WHERE "):
        raise RuntimeError("fixed valid query does not target public.forest10")
    return query


def _load_fixed_valid_query(data_root: Path) -> dict[str, Any]:
    """Read only the workload pickle and resolve exactly valid:000005."""
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
    return _fixed_valid_query(queries)


def _legacy_trace_summary(
    helpers: Any,
    raw_result: dict[str, Any],
    ledger: list[dict[str, Any]],
    query: dict[str, Any],
    marker: str,
) -> dict[str, Any]:
    """Retain only base/MCV fields needed for the adapter comparison."""
    trace = helpers.evaluate_trace(
        raw_result["raw_associated_trace_lines"],
        ledger,
        label=marker,
        query_id=query["query_id"],
    )
    if trace.get("status") != "VERIFIED":
        raise RuntimeError("legacy PR #58 trace diagnostics are incomplete or incompatible")
    base_records = [row for row in trace["numeric"] if "nrows_preclamp" in row]
    if len(base_records) != 1:
        raise RuntimeError("legacy PR #58 trace did not provide exactly one base estimate")
    base = base_records[0]
    base_relation_oid = int(base["base_relation_oid"])
    mcv_records = []
    for row in trace["numeric"]:
        if "selected_stat_oid" not in row:
            continue
        terms = {name: str(Decimal(row[name])) for name in MCV_NUMERIC_FIELDS}
        mcv_records.append({
            "relation_oid": int(row["relid"]),
            "stat_oid": int(row["selected_stat_oid"]),
            "numeric_terms": terms,
        })
    selected_oids = {int(oid) for oid in trace["selected_stat_oids"]}
    if selected_oids != {row["stat_oid"] for row in mcv_records}:
        raise RuntimeError("legacy PR #58 selected MCV OIDs lack corresponding numeric trace records")
    if len({row["stat_oid"] for row in mcv_records}) != len(mcv_records):
        raise RuntimeError("legacy PR #58 trace contains duplicate MCV numeric records")
    clauses = trace["claimed_clause_coverage"]["claimed_clauses_by_stat_oid"]
    for row in mcv_records:
        row["clause_indexes"] = sorted(int(index) for index in clauses.get(str(row["stat_oid"]), []))
    return {
        "diagnostics_status": "VERIFIED",
        "relation_oid": base_relation_oid,
        "estimate_preclamp": str(Decimal(raw_result["estimate_preclamp"])),
        "mcv_diagnostics_status": "VERIFIED" if mcv_records else "NO_MCV_EVENTS",
        "mcv_records": mcv_records,
    }


def _compare_diagnostic_summaries(legacy: dict[str, Any], structured: dict[str, Any]) -> dict[str, Any]:
    """Compare exact Decimal values and event identities without retaining raw output."""
    if legacy.get("diagnostics_status") != "VERIFIED":
        raise RuntimeError("legacy server-log diagnostics are not verified")
    if structured.get("diagnostics_status") != "complete":
        raise RuntimeError("structured diagnostics are not complete")
    legacy_base = Decimal(legacy["estimate_preclamp"])
    structured_base = Decimal(structured["estimate_preclamp"])
    base_delta = legacy_base - structured_base
    old_mcv = legacy["mcv_records"]
    new_mcv = structured["mcv_records"]
    comparison: dict[str, Any] = {
        "legacy_diagnostics_status": legacy["diagnostics_status"],
        "structured_diagnostics_status": structured["diagnostics_status"],
        "base_relation_oid_equal": legacy["relation_oid"] == structured["relation_oid"],
        "legacy_preclamp": str(legacy_base),
        "structured_preclamp": str(structured_base),
        "preclamp_delta_legacy_minus_structured": str(base_delta),
        "preclamp_exact_decimal_match": base_delta == 0,
        "mcv_event_presence": "BOTH_PRESENT" if old_mcv and new_mcv else (
            "BOTH_ABSENT" if not old_mcv and not new_mcv else "MISMATCH"
        ),
        "mcv_records": [],
    }
    if not old_mcv and not new_mcv:
        comparison["mcv_hit_parity"] = "NOT_VERIFIED_NO_MCV_EVENTS"
    elif bool(old_mcv) != bool(new_mcv):
        comparison["mcv_hit_parity"] = "MISMATCH"
    else:
        old_by_oid = {row["stat_oid"]: row for row in old_mcv}
        new_by_oid = {row["stat_oid"]: row for row in new_mcv}
        if set(old_by_oid) != set(new_by_oid):
            comparison["mcv_hit_parity"] = "MISMATCH"
        else:
            records_match = True
            for oid in sorted(old_by_oid):
                before, after = old_by_oid[oid], new_by_oid[oid]
                terms = {}
                for name in MCV_NUMERIC_FIELDS:
                    left = Decimal(before["numeric_terms"][name])
                    right = Decimal(after[name])
                    delta = left - right
                    terms[name] = {
                        "legacy": str(left),
                        "structured": str(right),
                        "delta_legacy_minus_structured": str(delta),
                        "exact_decimal_match": delta == 0,
                    }
                    records_match &= delta == 0
                identity_match = (
                    before["relation_oid"] == after["relation_oid"]
                    and before["clause_indexes"] == after["clause_indexes"]
                )
                records_match &= identity_match
                comparison["mcv_records"].append({
                    "relation_oid": before["relation_oid"],
                    "stat_oid": oid,
                    "clause_indexes": before["clause_indexes"],
                    "identity_match": identity_match,
                    "numeric_terms": terms,
                })
            comparison["mcv_hit_parity"] = "MATCH" if records_match else "MISMATCH"
    if comparison["mcv_event_presence"] == "MISMATCH":
        comparison["status"] = "MISMATCH_MCV_EVENT_PRESENCE"
    elif not comparison["base_relation_oid_equal"]:
        comparison["status"] = "MISMATCH_RELATION_OID"
    elif not comparison["preclamp_exact_decimal_match"]:
        comparison["status"] = "MISMATCH_PRECLAMP"
    elif comparison["mcv_hit_parity"] == "MISMATCH":
        comparison["status"] = "MISMATCH_MCV_DIAGNOSTICS"
    elif comparison["mcv_hit_parity"] == "NOT_VERIFIED_NO_MCV_EVENTS":
        comparison["status"] = "BASE_MATCH_MCV_NOT_VERIFIED"
    else:
        comparison["status"] = "MATCH"
    return comparison


def _worker(root: Path) -> int:
    started = time.monotonic()
    summary: dict[str, Any] = {
        "format": "ess-issue64-forest10-json-only-pilot-v1",
        "status": "FAILED",
        "researcher_approved_scope": "Forest10 JSON-only integration; Empty/e00_01; one valid query; no test access",
        "phases_seconds": {},
        "checks": {},
        "query": {},
        "sample": {},
        "statistics_object": {},
        "explain": {"interface": "PR #7 structured JSON only", "attempts": 0, "completed": 0,
                    "plan_rows_retained": False},
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
        helpers, run_formal, pr58_pin = timed(
            "pr58_helper_fetch_hash_verification_and_import",
            lambda: _load_pinned_pr58_modules(root),
        )
        import forest10_runner as issue64_runner
        summary["checks"]["pr58_source_pin"] = pr58_pin

        query = timed(
            "valid_workload_and_query_resolution",
            lambda: _load_fixed_valid_query(configured_root("ESS_DATA_ROOT")),
        )
        summary["query"] = {
            "query_id": query["query_id"],
            "source_index": query["source_index"],
            "split": "valid",
            "static_e00_01_eligibility": "PASS",
            "diagnostic_interface": "PR7StructuredExplainAdapter only",
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

        def record_build_phase(phase: str) -> None:
            nonlocal current_phase
            current_phase = phase

        prefix, _pg_source, pg_build = timed(
            "private_postgresql_fetch_build_install",
            lambda: _prepare_owned_postgresql(
                root, phase_sink=record_build_phase, phase_times=summary["phases_seconds"]
            ),
        )
        summary["postgresql_build"] = pg_build
        summary["checks"]["postgresql_source_and_binaries"] = "PASS"

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
            phase_times=summary["phases_seconds"],
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

            structured_adapter = issue64_runner.PR7StructuredExplainAdapter(
                helpers,
                prefix,
                cluster,
                int(identity["header"]["relation_oid"]),
                singleton_ledger,
                backend.name_to_id,
            )
            summary["explain"]["attempts"] += 1
            structured_diagnostic = timed(
                "pr7_structured_diagnostics_explain",
                lambda: structured_adapter.explain(query),
            )
            summary["explain"]["completed"] += 1
            summary["explain"]["structured"] = structured_diagnostic
            summary["checks"]["structured_status_complete"] = (
                "PASS" if structured_diagnostic["diagnostics_status"] == "complete" else "FAIL"
            )
            summary["checks"]["positive_finite_preclamp"] = "PASS"
            summary["checks"]["base_relation_oid_and_query_association"] = "PASS"
            summary["checks"]["mcv_events"] = structured_diagnostic["mcv_diagnostics_status"]
            if structured_diagnostic["diagnostics_status"] != "complete":
                raise RuntimeError("PR #7 structured diagnostics are not complete")
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


def _supervise(
    root: Path,
    *,
    worker_command: list[str] | None = None,
    soft_wall_seconds: int = SOFT_STOP_SECONDS,
    hard_wall_seconds: int = HARD_WALL_SECONDS,
    soft_disk_bytes: int = SOFT_STOP_DISK_BYTES,
    hard_disk_bytes: int = HARD_DISK_BYTES,
    worker_summary_name: str = "pilot-worker-summary.json",
    summary_format: str = "ess-issue64-forest10-setup-pilot-supervisor-v1",
) -> int:
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
            worker_command or [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)],
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
            stop_reason = _watchdog_stop_reason(
                current,
                elapsed,
                disk_threshold_bytes=soft_disk_bytes,
                wall_threshold_seconds=soft_wall_seconds,
            )
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
    if stop_reason is None and elapsed >= soft_wall_seconds:
        stop_reason = _watchdog_stop_reason(0, elapsed, wall_threshold_seconds=soft_wall_seconds)
    cluster_data = root / "cluster" / "pgdata"
    if (stop_reason is not None or return_code != 0) and cluster_data.exists():
        pg_ctl = root / "postgresql" / "install" / "bin" / "pg_ctl"
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
    if elapsed > hard_wall_seconds or (peak is not None and peak >= hard_disk_bytes):
        stop_reason = stop_reason or "hard_cap_exceeded_or_monitor_late"
    worker_summary_path = root / worker_summary_name
    worker_summary = None
    if worker_summary_path.is_file():
        worker_summary = json.loads(worker_summary_path.read_text(encoding="utf-8"))
    final = {
        "format": summary_format,
        "status": "ABORTED" if stop_reason else (worker_summary or {}).get("status", "FAILED"),
        "stop_reason": stop_reason,
        "worker_exit_code": return_code,
        "elapsed_seconds": round(elapsed, 3),
        "elapsed_cap_seconds": hard_wall_seconds,
        "peak_allocated_disk_bytes": peak,
        "peak_disk_measurement": "MEASURED" if peak is not None else "UNKNOWN",
        "disk_monitor_error": disk_monitor_error,
        "hard_disk_cap_bytes": hard_disk_bytes,
        "watchdog_abort_threshold_bytes": soft_disk_bytes,
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
