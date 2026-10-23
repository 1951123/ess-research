"""Single-case, interruption-durable Issue #74 recovery runner.

The checked-in protocol is deliberately unauthorized. CI never starts a solver.
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
    root: Path, exit_code: int | None, failure: dict[str, Any] | None = None
) -> dict[str, Any]:
    last_child = checkpoint(root)
    event(
        root,
        "child_missing_result",
        systemd_exit_code=exit_code,
        last_child_checkpoint=last_child,
        **(failure or {}),
    )
    return {
        "outcome": "STOP_FOR_REVIEW",
        "systemd_exit_code": exit_code,
        "last_child_checkpoint": last_child,
    }


def reconcile_scope_exit(
    result: dict[str, Any], exit_code: int | None
) -> dict[str, Any]:
    result = {**result, "systemd_exit_code": exit_code}
    if exit_code != 0 and result.get("outcome") == "PASS":
        result.update(outcome="STOP_FOR_REVIEW", error="systemd scope exited nonzero")
    return result


def protocol() -> dict[str, Any]:
    p = json.loads(PROTOCOL.read_text())
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
    return p


def scope_command(repo: Path, root: Path, python: str = sys.executable) -> list[str]:
    limits = protocol()["solver"]
    return [
        "systemd-run",
        "--user",
        "--scope",
        "--quiet",
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


def run(repo: Path, run_id: str, authorized_flag: bool) -> int:
    p = protocol()
    if not authorized_flag or p["execution_authorized"] is not True:
        raise RuntimeError(
            "reviewed protocol and separate researcher execution authorization required"
        )
    runtime = Path(os.environ["ESS_RUNTIME_PARENT"]).resolve()
    if not run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for c in run_id
    ):
        raise ValueError("invalid run id")
    root = runtime / "ess-research" / "issue74" / "runs" / run_id
    root.resolve().relative_to(runtime)
    root.mkdir(parents=True, exist_ok=False)
    protocol_sha = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    write_atomic(
        root / "run-metadata.json",
        {
            "status": "RUNNING",
            "case_id": "forest10-nominal-b2",
            "protocol_sha256": protocol_sha,
            "advisor_source_commit": p["immutable_software"]["advisor_source_commit"],
            "limits": p["solver"],
        },
    )
    event(root, "run_started", protocol_sha256=protocol_sha)
    try:
        with (root / "runner.log").open("wb") as log:
            completed = subprocess.run(
                scope_command(repo, root),
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
    result_path = root / "case-result.json"
    if not result_path.exists():
        result = record_missing_child_result(root, exit_code, failure)
    else:
        result = reconcile_scope_exit(json.loads(result_path.read_text()), exit_code)
    child_checkpoint = result.get("last_child_checkpoint")
    write_atomic(result_path, result)
    if checkpoint(root).get("phase") != "run_finished":
        event(
            root, "run_finished", outcome=result["outcome"], systemd_exit_code=exit_code
        )
    metadata = json.loads((root / "run-metadata.json").read_text())
    metadata.update(
        status=result["outcome"],
        systemd_exit_code=exit_code,
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
    started = time.monotonic()
    try:
        runner_commit = verify(repo, p)
        verify_environment(p)
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
            except BaseException as exc:
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
            "advisor_source_commit": p["immutable_software"]["advisor_source_commit"],
            "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
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
    except BaseException as exc:
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
