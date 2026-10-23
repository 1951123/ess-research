"""Single-case, interruption-durable Issue #74 recovery runner.

Execution is effective only for the reviewed, merged, source-pinned gate.
CI tests mock the outer launch and never start a solver.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "stage2-b2-recovery-protocol-v1.json"
AUTHORIZATION_REQUEST = HERE / "stage2-b2-recovery-authorization-request-v1.json"
EXECUTION_GATE = HERE / "stage2-b2-recovery-execution-gate-v1.json"


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def write_atomic(path: Path, value: bytes | object) -> None:
    data = value if isinstance(value, bytes) else canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def event(root: Path, phase: str, **fields: Any) -> None:
    item = {"utc_epoch_seconds": time.time(), "phase": phase, **fields}
    with (root / "phase-events.jsonl").open("ab") as f:
        f.write(canonical(item))
        f.flush()
        os.fsync(f.fileno())
    write_atomic(root / "phase-checkpoint.json", item)


def checkpoint(root: Path) -> dict[str, Any] | None:
    path = root / "phase-checkpoint.json"
    return json.loads(path.read_text()) if path.exists() else None


def record_missing_child_result(
    root: Path,
    exit_code: int | None,
    failure: dict[str, Any] | None = None,
    systemd_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_child = checkpoint(root)
    event(
        root,
        "child_missing_result",
        systemd_exit_code=exit_code,
        systemd_status=systemd_status or {"available": False, "state": "unknown"},
        last_child_checkpoint=last_child,
        **(failure or {}),
    )
    return {
        "outcome": "STOP_FOR_REVIEW",
        "systemd_exit_code": exit_code,
        "systemd_status": systemd_status or {"available": False, "state": "unknown"},
        "last_child_checkpoint": last_child,
    }


def reconcile_scope_exit(
    result: dict[str, Any], exit_code: int | None
) -> dict[str, Any]:
    result = {**result, "systemd_exit_code": exit_code}
    if exit_code != 0 and result.get("outcome") == "PASS":
        result.update(outcome="STOP_FOR_REVIEW", error="systemd scope exited nonzero")
    return result


def reconcile_systemd_acceptance(
    result: dict[str, Any], systemd_status: dict[str, Any]
) -> dict[str, Any]:
    """A child PASS also requires a collected successful systemd outcome."""
    if result.get("outcome") != "PASS":
        return result
    properties = systemd_status.get("properties")
    systemd_result = properties.get("Result") if isinstance(properties, dict) else None
    if (
        systemd_status.get("available") is not True
        or not isinstance(systemd_result, str)
        or systemd_result != "success"
    ):
        result.update(
            outcome="STOP_FOR_REVIEW",
            error=(
                "PASS result lacks a collected successful systemd Result; "
                f"observed {systemd_result!r}"
            ),
        )
    return result


def protocol() -> dict[str, Any]:
    p = json.loads(PROTOCOL.read_text())
    request = json.loads(AUTHORIZATION_REQUEST.read_text())
    gate = json.loads(EXECUTION_GATE.read_text())
    if (
        p["format"] != "ess-issue74-stage2-b2-recovery-protocol-v1"
        or p["scope"]["cases"] != ["forest10-nominal-b2"]
        or p["scope"]["retries"] != 0
        or p["immutable_software"]["advisor_source_commit"]
        != "369d90217e931c7d1b0cd6e82c88527a25cc7129"
    ):
        raise RuntimeError("recovery protocol scope or pin mismatch")
    if (
        p["solver"]["time_limit_seconds"] != 600
        or p["solver"]["total_time_limit_seconds"] != 600
        or p["solver"]["outer_memory_max_bytes"] != 12884901888
        or p["solver"]["outer_runtime_max_seconds"] != 900
        or p["gates"]["this_pull_request_may_execute_solver"] is not False
    ):
        raise RuntimeError("recovery limits or solver-free PR gate changed")
    if (
        request["execution_authorized"] is not False
        or request["authorization_gate"]["current_execution_authorized"] is not False
        or hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
        != gate["base_protocol"]["sha256"]
        or gate["base_protocol"]["path"]
        != "experiments/solver-integration-issue74/stage2-b2-recovery-protocol-v1.json"
        or hashlib.sha256(AUTHORIZATION_REQUEST.read_bytes()).hexdigest()
        != gate["authorization_request"]["sha256"]
        or gate["authorization_request"]["path"]
        != "experiments/solver-integration-issue74/stage2-b2-recovery-authorization-request-v1.json"
    ):
        raise RuntimeError(
            "execution gate does not match reviewed authorization inputs"
        )
    if (
        gate["format"] != "ess-issue74-stage2-b2-recovery-execution-gate-v1"
        or gate["execution_authorized"] is not True
        or gate["status"]
        != "CONDITIONALLY_AUTHORIZED_EFFECTIVE_ONLY_AFTER_REVIEWED_MERGE"
        or gate["grant"]["issue_number"] != 74
        or gate["grant"]["authorized_by"] != "1951123"
        or gate["grant"]["authorized_case"] != "forest10-nominal-b2"
        or gate["grant"]["authorized_attempts"] != 1
        or gate["grant"]["conditional_on_reviewed_merge"] is not True
        or gate["grant"]["base_protocol_sha256"] != gate["base_protocol"]["sha256"]
        or gate["one_shot"]["enabled"] is not True
        or gate["one_shot"]["retry_permitted"] is not False
        or gate["one_shot"]["concurrent_attempts_permitted"] is not False
        or gate["one_shot"]["outer_requires_valid_child_start_claim_for_pass"]
        is not True
        or gate["runner_source"]["path"]
        != "experiments/solver-integration-issue74/run_stage2_b2_recovery.py"
        or len(gate["runner_source"]["blob_git_sha1"]) != 40
        or any(
            c not in "0123456789abcdef" for c in gate["runner_source"]["blob_git_sha1"]
        )
    ):
        raise RuntimeError("execution gate scope, grant, or runner pin mismatch")
    if (
        request["scope"]["cases"] != p["scope"]["cases"]
        or request["scope"]["retries"] != p["scope"]["retries"]
        or request["scope"]["tasks"] != p["scope"]["tasks"]
        or request["scope"]["candidates"] != p["scope"]["candidates"]
        or request["scope"]["budget"] != p["scope"]["budget"]
        or request["solver_limits"]["outer_memory_max_bytes"]
        != p["solver"]["outer_memory_max_bytes"]
        or request["solver_limits"]["outer_runtime_max_seconds"]
        != p["solver"]["outer_runtime_max_seconds"]
        or request["solver_limits"]["advisor_time_limit_seconds"]
        != p["solver"]["time_limit_seconds"]
        or request["solver_limits"]["advisor_total_time_limit_seconds"]
        != p["solver"]["total_time_limit_seconds"]
        or gate["grant"]["research_runner_merge_commit"]
        != "d4a3fd6636b28fc33adfb51d45e652c534175ec8"
        or gate["grant"]["research_runner_source_commit"]
        != request["immutable_software"]["research_runner_source_commit"]
        or gate["grant"]["research_runner_merge_commit"]
        != request["immutable_software"]["research_runner_merge_commit"]
        or gate["grant"]["advisor_source_commit"]
        != p["immutable_software"]["advisor_source_commit"]
        or gate["grant"]["advisor_source_commit"]
        != request["immutable_software"]["advisor_source_commit"]
    ):
        raise RuntimeError("execution gate changes the reviewed recovery scope")
    p["execution_authorized"] = True
    p["execution_gate"] = gate
    p["immutable_software"]["recovery_runner_blob_git_sha1"] = gate["runner_source"][
        "blob_git_sha1"
    ]
    p["immutable_software"]["recovery_runner_source_commit"] = gate["grant"][
        "research_runner_source_commit"
    ]
    return p


def scope_command(
    repo: Path,
    root: Path,
    python: str = sys.executable,
    unit_name: str = "ess-issue74-b2-recovery.scope",
) -> list[str]:
    limits = protocol()["solver"]
    return [
        "systemd-run",
        "--user",
        "--scope",
        "--quiet",
        f"--unit={unit_name}",
        "-p",
        f"MemoryMax={limits['outer_memory_max_bytes']}",
        "-p",
        f"RuntimeMaxSec={limits['outer_runtime_max_seconds']}",
        "--setenv=ESS_ISSUE74_B2_RECOVERY_SCOPE=1",
        "/usr/bin/time",
        "-v",
        "-o",
        str(root / "time.txt"),
        python,
        str(HERE / "run_stage2_b2_recovery.py"),
        "_case",
        "--repo",
        str(repo.resolve()),
        "--run-dir",
        str(root.resolve()),
    ]


def systemd_unit_name(run_id: str) -> str:
    return f"ess-issue74-b2-{run_id}.scope"


def consume_execution_grant_once(
    runtime: Path, run_id: str, protocol_sha: str, gate_sha: str
) -> Path:
    runs = runtime / "ess-research" / "issue74" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    record_path = runs / f"authorization-consumed-{gate_sha}.json"
    record = canonical(
        {
            "run_id": run_id,
            "protocol_sha256": protocol_sha,
            "execution_gate_sha256": gate_sha,
            "consumed_utc_epoch_seconds": time.time(),
            "retry_permitted": False,
        }
    )
    try:
        fd = os.open(record_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(
            "single execution grant was already consumed; retry is prohibited"
        ) from exc
    with os.fdopen(fd, "wb") as claim:
        claim.write(record)
        claim.flush()
        os.fsync(claim.fileno())
    dir_fd = os.open(runs, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return record_path


def claim_child_start_once(root: Path, runtime: Path, p: dict[str, Any]) -> Path:
    run_id = root.name
    if not run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for c in run_id
    ):
        raise RuntimeError("invalid child run directory")
    runs = runtime.resolve() / "ess-research" / "issue74" / "runs"
    root = root.resolve()
    if root.parent != runs.resolve():
        raise RuntimeError("child run directory is outside the pinned runtime root")
    gate_sha = hashlib.sha256(EXECUTION_GATE.read_bytes()).hexdigest()
    protocol_sha = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    parent_claim = runs / f"authorization-consumed-{gate_sha}.json"
    try:
        claim = json.loads(parent_claim.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "child requires the durable outer authorization claim"
        ) from exc
    if (
        claim.get("run_id") != run_id
        or claim.get("protocol_sha256") != protocol_sha
        or claim.get("execution_gate_sha256") != gate_sha
        or claim.get("retry_permitted") is not False
    ):
        raise RuntimeError("outer authorization claim does not match this child")
    marker = root / "child-start-consumed.json"
    record = canonical(
        {
            "run_id": run_id,
            "protocol_sha256": protocol_sha,
            "execution_gate_sha256": gate_sha,
            "child_started_utc_epoch_seconds": time.time(),
            "retry_permitted": False,
        }
    )
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(
            "child start was already consumed; retry is prohibited"
        ) from exc
    with os.fdopen(fd, "wb") as started:
        started.write(record)
        started.flush()
        os.fsync(started.fileno())
    dir_fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return marker


def collect_systemd_status(unit_name: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                unit_name,
                "-p",
                "Id",
                "-p",
                "Result",
                "-p",
                "MemoryPeak",
                "-p",
                "ExecMainStatus",
            ],
            check=False,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "state": "unknown",
            "unit": unit_name,
            "error": f"{type(exc).__name__}: {exc}",
        }
    raw = result.stdout
    if result.returncode != 0:
        return {
            "available": False,
            "state": "unknown",
            "unit": unit_name,
            "query_returncode": result.returncode,
            "raw_properties": raw,
            "query_stderr": result.stderr,
        }
    properties = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
    return {
        "available": True,
        "state": "collected",
        "unit": unit_name,
        "query_returncode": result.returncode,
        "properties": properties,
        "raw_properties": raw,
    }


def verify_frozen_file_hashes(repo: Path, p: dict[str, Any]) -> dict[str, str]:
    frozen = p["frozen_input"]
    pins = {
        "frozen_selection": (
            frozen["frozen_selection_path"],
            frozen["frozen_selection_sha256"],
        ),
        "coefficient_artifact": (
            frozen["coefficient_artifact_path"],
            frozen["coefficient_artifact_sha256"],
        ),
    }
    hashes: dict[str, str] = {}
    repo = repo.resolve()
    for name, (relative_path, expected) in pins.items():
        path = (repo / relative_path).resolve()
        try:
            path.relative_to(repo)
        except ValueError as exc:
            raise RuntimeError(f"pinned {name} path escapes repository") from exc
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"pinned {name} SHA-256 mismatch: {actual}")
        hashes[name] = actual
    return hashes


def run(repo: Path, run_id: str, authorized_flag: bool) -> int:
    p = protocol()
    if not authorized_flag or p["execution_authorized"] is not True:
        raise RuntimeError(
            "reviewed protocol and separate researcher execution authorization required"
        )
    runner_commit = verify(repo, p)
    runtime = Path(os.environ["ESS_RUNTIME_PARENT"]).resolve()
    if not run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for c in run_id
    ):
        raise ValueError("invalid run id")
    root = runtime / "ess-research" / "issue74" / "runs" / run_id
    root.resolve().relative_to(runtime)
    if root.exists():
        raise FileExistsError(f"run directory already exists: {root}")
    protocol_sha = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    execution_gate_sha = hashlib.sha256(EXECUTION_GATE.read_bytes()).hexdigest()
    authorization_claim = consume_execution_grant_once(
        runtime, run_id, protocol_sha, execution_gate_sha
    )
    root.mkdir(parents=True, exist_ok=False)
    write_atomic(
        root / "run-metadata.json",
        {
            "status": "RUNNING",
            "case_id": "forest10-nominal-b2",
            "protocol_sha256": protocol_sha,
            "execution_gate_sha256": execution_gate_sha,
            "authorization_claim_path": str(authorization_claim),
            "runner_source_commit": runner_commit,
            "runner_blob_git_sha1": p["immutable_software"][
                "recovery_runner_blob_git_sha1"
            ],
            "advisor_source_commit": p["immutable_software"]["advisor_source_commit"],
            "limits": p["solver"],
        },
    )
    event(
        root,
        "run_started",
        protocol_sha256=protocol_sha,
        execution_gate_sha256=execution_gate_sha,
        authorization_claim_path=str(authorization_claim),
        runner_source_commit=runner_commit,
    )
    unit_name = systemd_unit_name(run_id)
    try:
        with (root / "runner.log").open("wb") as log:
            completed = subprocess.run(
                scope_command(repo, root, unit_name=unit_name),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        exit_code = completed.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        exit_code = None
        failure = {"exception_type": type(exc).__name__, "message": str(exc)}
    else:
        failure = {}
    systemd_status = collect_systemd_status(unit_name)
    event(
        root,
        "systemd_status_collected",
        unit=unit_name,
        systemd_exit_code=exit_code,
        systemd_status=systemd_status,
    )
    result_path = root / "case-result.json"
    if not result_path.exists():
        result = record_missing_child_result(root, exit_code, failure, systemd_status)
    else:
        result = reconcile_scope_exit(json.loads(result_path.read_text()), exit_code)
        result["systemd_status"] = systemd_status
    result = reconcile_systemd_acceptance(result, systemd_status)
    child_claim_path = root / "child-start-consumed.json"
    try:
        child_claim = json.loads(child_claim_path.read_text())
    except (OSError, json.JSONDecodeError):
        child_claim = None
    child_claim_valid = (
        isinstance(child_claim, dict)
        and child_claim.get("run_id") == run_id
        and child_claim.get("protocol_sha256") == protocol_sha
        and child_claim.get("execution_gate_sha256") == execution_gate_sha
        and child_claim.get("retry_permitted") is False
    )
    if result.get("outcome") == "PASS" and not child_claim_valid:
        result.update(
            outcome="STOP_FOR_REVIEW",
            error="PASS result lacks a valid one-shot child-start claim",
        )
    result["child_start_claim_valid"] = child_claim_valid
    result["child_start_claim_path"] = str(child_claim_path)
    result["protocol_sha256"] = protocol_sha
    result["execution_gate_sha256"] = execution_gate_sha
    result["authorization_claim_path"] = str(authorization_claim)
    child_checkpoint = result.get("last_child_checkpoint")
    write_atomic(result_path, result)
    if checkpoint(root).get("phase") != "run_finished":
        event(
            root,
            "run_finished",
            outcome=result["outcome"],
            systemd_exit_code=exit_code,
            systemd_status=systemd_status,
            execution_gate_sha256=execution_gate_sha,
        )
    metadata = json.loads((root / "run-metadata.json").read_text())
    metadata.update(
        status=result["outcome"],
        child_start_claim_valid=child_claim_valid,
        systemd_exit_code=exit_code,
        systemd_unit=unit_name,
        systemd_status=systemd_status,
        execution_gate_sha256=execution_gate_sha,
        authorization_claim_path=str(authorization_claim),
        last_child_checkpoint=child_checkpoint,
    )
    write_atomic(root / "run-metadata.json", metadata)
    return 0 if exit_code == 0 and result["outcome"] == "PASS" else 2


def verify(repo: Path, p: dict[str, Any]) -> str:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, text=True, capture_output=True
        ).stdout.strip()

    head = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("execution checkout must be clean")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", head, "origin/main"],
        cwd=repo,
        check=False,
    ).returncode:
        raise RuntimeError(
            "reviewed runner commit must be merged into fetched origin/main"
        )
    expected = p["immutable_software"]["stage1_adapter_blob_git_sha1"]
    if (
        git("hash-object", "experiments/solver-integration-issue74/adapter.py")
        != expected
    ):
        raise RuntimeError("Stage-1 adapter content differs from pinned blob")
    expected_runner = p["immutable_software"]["recovery_runner_blob_git_sha1"]
    actual_runner = git("hash-object", p["execution_gate"]["runner_source"]["path"])
    if actual_runner != expected_runner:
        raise RuntimeError("recovery runner content differs from execution-gate pin")
    return head


def verify_environment(p: dict[str, Any]) -> None:
    pins = p["immutable_software"]
    actual = {
        "pess-ess": importlib.metadata.version("pess-ess"),
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
        "python": ".".join(map(str, sys.version_info[:3])),
    }
    expected = {
        "pess-ess": pins["pess_ess_version"],
        "numpy": pins["numpy_version"],
        "scipy": pins["scipy_version"],
        "python": pins["python_version"],
    }
    if actual != expected:
        raise RuntimeError(f"runtime versions differ from protocol: {actual!r}")
    raw = importlib.metadata.distribution("pess-ess").read_text("direct_url.json")
    commit = json.loads(raw or "{}").get("vcs_info", {}).get("commit_id")
    if commit != pins["advisor_source_commit"]:
        raise RuntimeError("installed Advisor commit differs from protocol")


def child(repo: Path, root: Path) -> int:
    p = protocol()
    if (
        p["execution_authorized"] is not True
        or os.getenv("ESS_ISSUE74_B2_RECOVERY_SCOPE") != "1"
    ):
        raise RuntimeError("child requires separately authorized systemd scope")
    runtime = Path(os.environ["ESS_RUNTIME_PARENT"]).resolve()
    child_claim = claim_child_start_once(root, runtime, p)
    started = time.monotonic()
    try:
        runner_commit = verify(repo, p)
        verify_environment(p)
        event(root, "child_start_claimed", claim_path=str(child_claim))
        frozen_file_hashes = verify_frozen_file_hashes(repo, p)
        event(root, "frozen_files_verified", sha256=frozen_file_hashes)
        sys.path.insert(0, str(HERE))
        import adapter
        from pess_ess import mip, nominal, solve_payload
        from pess_ess.model import instance_from_dict
        from pess_ess.reference import reference_nominal_objective

        pins = p["frozen_input"]
        source = adapter.forest10_request(repo, budget=2)
        provenance = source["input_provenance"]
        for key, expected in (
            ("model_version", pins["model_version"]),
            ("model_source_commit", pins["model_source_commit"]),
            ("frozen_reference_sha256", pins["frozen_selection_sha256"]),
            ("coefficient_artifact_sha256", pins["coefficient_artifact_sha256"]),
            ("valid_truth_values_sha256", pins["valid_truth_sha256"]),
            ("arecel_archive_sha256", pins["arecel_archive_sha256"]),
        ):
            if provenance.get(key) != expected:
                raise RuntimeError(f"input provenance mismatch: {key}")
        candidates = source["_candidate_ids"]
        order_sha = hashlib.sha256(
            json.dumps(candidates, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            len(source["instance"]["tasks"]) != 10000
            or len(candidates) != 45
            or order_sha != pins["candidate_order_sha256"]
        ):
            raise RuntimeError("frozen Forest10 task/candidate universe mismatch")
        event(
            root,
            "input_verified",
            tasks=10000,
            candidates=45,
            candidate_order_sha256=order_sha,
            frozen_file_sha256=frozen_file_hashes,
        )
        payload = adapter.advisor_request_payload(
            source, "nominal", priority_order=source["_nominal_priority_order"]
        )
        payload["input_provenance"]["advisor_source_commit"] = p["immutable_software"][
            "advisor_source_commit"
        ]
        payload["options"] = p["solver"]["options"]
        payload["limits"] = {
            "time_seconds": p["solver"]["time_limit_seconds"],
            "total_time_seconds": p["solver"]["total_time_limit_seconds"],
        }
        request_bytes = canonical(payload)
        instance = instance_from_dict(source["instance"])
        event(
            root,
            "request_prepared",
            request_sha256=hashlib.sha256(request_bytes).hexdigest(),
        )

        original_milp, original_sparse = mip.milp, mip._sparse_constraint_matrix
        original_nominal, original_binary = (
            nominal._nominal_milp,
            nominal.solve_binary_milp,
        )
        phases: dict[str, float] = {}
        calls = 0

        def sparse(*args: Any, **kwargs: Any) -> Any:
            matrix, coo, csr = original_sparse(*args, **kwargs)
            phases.update(coo=coo, csr=csr)
            event(
                root,
                "coo_csr_ready",
                coo_assembly_seconds=coo,
                coo_to_csr_conversion_seconds=csr,
                rows=matrix.shape[0],
                columns=matrix.shape[1],
                stored_entries=matrix.nnz,
            )
            return matrix, coo, csr

        def nominal_build(*args: Any, **kwargs: Any) -> Any:
            begin = time.monotonic()

            def binary(**solver_kwargs: Any) -> Any:
                phases["python_constraints"] = time.monotonic() - begin
                event(
                    root,
                    "python_constraints_ready",
                    python_constraint_construction_seconds=phases["python_constraints"],
                )
                phases["prep_begin"] = time.monotonic()
                return original_binary(**solver_kwargs)

            nominal.solve_binary_milp = binary
            try:
                return original_nominal(*args, **kwargs)
            finally:
                nominal.solve_binary_milp = original_binary

        def traced_milp(**kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            prep = max(
                0.0,
                time.monotonic()
                - phases.get("prep_begin", time.monotonic())
                - phases.get("coo", 0.0)
                - phases.get("csr", 0.0),
            )
            matrix = getattr(kwargs.get("constraints"), "A", None)
            event(
                root,
                "solver_invocation_started",
                invocation=calls,
                solver_input_preparation_seconds=prep,
                python_constraint_construction_seconds=phases.get("python_constraints"),
                elapsed_seconds=time.monotonic() - started,
                rows=getattr(matrix, "shape", (None, None))[0],
                columns=getattr(matrix, "shape", (None, None))[1],
                stored_entries=getattr(matrix, "nnz", None),
            )
            began = time.monotonic()
            try:
                result = original_milp(**kwargs)
            except Exception as exc:
                event(
                    root,
                    "solver_invocation_raised",
                    invocation=calls,
                    duration_seconds=time.monotonic() - began,
                    exception=type(exc).__name__,
                )
                raise
            event(
                root,
                "solver_invocation_finished",
                invocation=calls,
                duration_seconds=time.monotonic() - began,
                status=getattr(result, "status", None),
            )
            return result

        mip._sparse_constraint_matrix, nominal._nominal_milp, mip.milp = (
            sparse,
            nominal_build,
            traced_milp,
        )
        try:
            response = solve_payload(payload)
        finally:
            mip.milp, mip._sparse_constraint_matrix = original_milp, original_sparse
            nominal._nominal_milp, nominal.solve_binary_milp = (
                original_nominal,
                original_binary,
            )
        response_bytes = canonical(response)
        write_atomic(root / "advisor-response.json", response_bytes)
        event(
            root,
            "response_saved",
            response_sha256=hashlib.sha256(response_bytes).hexdigest(),
            phase_timings_seconds=response.get("phase_timings_seconds"),
        )
        incumbent = response.get("incumbent", {})
        raw = incumbent.get("selected")
        selected = frozenset(raw) if isinstance(raw, list) else None
        exact = (
            None
            if selected is None
            else reference_nominal_objective(
                instance, selected, tuple(source["_nominal_priority_order"])
            )[0]
        )
        expected, ties = (
            pins["frozen_exact_objective_fraction"],
            pins["all_frozen_exact_tie_sets"],
        )
        statuses = response.get("solver_statuses", [])
        status_ok = bool(statuses) and all(
            s.get("status_code") == 0
            and s.get("solver_reported_optimal") is True
            and s.get("incumbent_returned") is True
            and s.get("highs_invocations") == 1
            for s in statuses
        )
        tie_member = selected is not None and sorted(selected) in [
            sorted(t) for t in ties
        ]
        no_warnings = not response.get("diagnostics", {}).get("numerical_warnings", [])
        passed = (
            response.get("status") == "optimal"
            and incumbent.get("validated_feasible") is True
            and str(exact) == expected
            and tie_member
            and status_ok
            and no_warnings
        )
        result = {
            "outcome": "PASS" if passed else "STOP_FOR_REVIEW",
            "runner_source_commit": runner_commit,
            "runner_blob_git_sha1": p["immutable_software"][
                "recovery_runner_blob_git_sha1"
            ],
            "advisor_source_commit": p["immutable_software"]["advisor_source_commit"],
            "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
            "execution_gate_sha256": hashlib.sha256(
                EXECUTION_GATE.read_bytes()
            ).hexdigest(),
            "child_start_claim_path": str(child_claim),
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "frozen_file_sha256": frozen_file_hashes,
            "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
            "selected": sorted(selected) if selected is not None else None,
            "selected_set_exact_objective_fraction": str(exact)
            if exact is not None
            else None,
            "frozen_exact_objective_fraction": expected,
            "selected_set_in_frozen_exact_ties": tie_member,
            "solver_statuses": statuses,
            "phase_timings_seconds": response.get("phase_timings_seconds"),
            "wall_seconds": time.monotonic() - started,
        }
        event(
            root,
            "exact_selection_evaluated",
            outcome=result["outcome"],
            selected_set_exact_objective_fraction=result[
                "selected_set_exact_objective_fraction"
            ],
        )
        write_atomic(root / "case-result.json", result)
        event(root, "run_finished", outcome=result["outcome"])
        return 0 if passed else 2
    except Exception as exc:
        last = checkpoint(root)
        event(
            root,
            "case_exception",
            exception=type(exc).__name__,
            message=str(exc),
            last_child_checkpoint=last,
        )
        write_atomic(
            root / "case-result.json",
            {
                "outcome": "STOP_FOR_REVIEW",
                "exception": type(exc).__name__,
                "message": str(exc),
                "last_child_checkpoint": last,
            },
        )
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    parent = sub.add_parser("run")
    parent.add_argument("--repo", type=Path, default=Path.cwd())
    parent.add_argument("--run-id", required=True)
    parent.add_argument("--research-owner-authorized", action="store_true")
    child_parser = sub.add_parser("_case")
    child_parser.add_argument("--repo", type=Path, required=True)
    child_parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "_case":
        return child(args.repo, args.run_dir)
    return run(args.repo, args.run_id, args.research_owner_authorized)


if __name__ == "__main__":
    raise SystemExit(main())
