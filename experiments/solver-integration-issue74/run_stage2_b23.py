"""Reviewed, serial runner for the authorized Issue #74 Stage 2 case matrix.

CI exercises only command construction and first-failure behavior. Solver
execution requires a merged runner commit, explicit CLI acknowledgements, and
one systemd resource scope per case.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import adapter

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "stage2-b23-runner-config-v1.json"
PROTOCOL_PATH = HERE / "stage2-b23-protocol-v1.json"
PROTOCOL_MERGE = "9b858e47284a290c1b078333929238cf55efdbff"
STAGE1_COMMIT = "6c0d82d258faaa817f2bc977ff99b04971550aa0"
ADVISOR_COMMIT = "d40a57d4704345fef85298dd97192b2d998dc6eb"
CASE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_safe(value: Any) -> Any:
    """Keep failure metadata serializable while the full response is retained separately."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_float": repr(value)}
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", *args], cwd=repo, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def verify_static_pins(repo: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    config = load_json(CONFIG_PATH)
    protocol = load_json(PROTOCOL_PATH)
    protocol_sha = sha256_file(PROTOCOL_PATH)
    if config["protocol_merge_commit"] != PROTOCOL_MERGE:
        raise RuntimeError("runner config protocol merge SHA mismatch")
    if config["stage1_adapter_base_commit"] != STAGE1_COMMIT:
        raise RuntimeError("runner config Stage-1 adapter SHA mismatch")
    if config["advisor_source_commit"] != ADVISOR_COMMIT:
        raise RuntimeError("runner config Advisor SHA mismatch")
    if protocol_sha != config["protocol_sha256"]:
        raise RuntimeError("merged Stage-2 protocol content SHA-256 mismatch")
    if protocol["immutable_software"]["stage1_adapter_baseline_commit"] != STAGE1_COMMIT:
        raise RuntimeError("protocol Stage-1 adapter pin mismatch")
    if protocol["immutable_software"]["advisor_source_commit"] != ADVISOR_COMMIT:
        raise RuntimeError("protocol Advisor pin mismatch")
    if protocol["solver_jobs_authorized"] is not False:
        raise RuntimeError("historical protocol must retain its no-run-authorization state")
    if protocol["execution_gate"]["this_protocol_pr_may_execute_solver"] is not False:
        raise RuntimeError("protocol execution gate was changed")
    cases = protocol["case_order"]
    case_ids = [case["case_id"] for case in cases]
    if case_ids != config["case_order"] or len(set(case_ids)) != 8:
        raise RuntimeError("runner case order does not exactly match the approved protocol")
    return config, protocol, protocol_sha


def verify_repo_gate(repo: Path) -> str:
    """Require a clean runner checkout already merged into the fetched main."""
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    if git(repo, "status", "--porcelain", "--untracked-files=normal").stdout.strip():
        raise RuntimeError("runner checkout must be clean before execution")
    if git(repo, "merge-base", "--is-ancestor", head, "origin/main", check=False).returncode:
        raise RuntimeError("runner HEAD is not contained in fetched origin/main; merge/review gate is unmet")
    if git(repo, "merge-base", "--is-ancestor", PROTOCOL_MERGE, head, check=False).returncode:
        raise RuntimeError("protocol merge commit is not an ancestor of runner HEAD")
    if git(repo, "merge-base", "--is-ancestor", STAGE1_COMMIT, head, check=False).returncode:
        raise RuntimeError("Stage-1 adapter baseline is not an ancestor of runner HEAD")
    expected_adapter_blob = git(repo, "rev-parse", f"{STAGE1_COMMIT}:experiments/solver-integration-issue74/adapter.py").stdout.strip()
    actual_adapter_blob = git(repo, "hash-object", "experiments/solver-integration-issue74/adapter.py").stdout.strip()
    if actual_adapter_blob != expected_adapter_blob:
        raise RuntimeError("Stage-1 adapter differs from its immutable baseline")
    merge_object = git(repo, "cat-file", "-t", PROTOCOL_MERGE, check=False)
    if merge_object.returncode or merge_object.stdout.strip() != "commit":
        raise RuntimeError("protocol merge commit is unavailable locally")
    return head


def verify_environment() -> dict[str, str]:
    config = load_json(CONFIG_PATH)
    expected = config["environment"]
    versions = {
        "python": ".".join(map(str, sys.version_info[:3])),
        "pess_ess": importlib.metadata.version("pess-ess"),
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
    }
    if versions != expected:
        raise RuntimeError(f"runtime versions differ from frozen protocol: {versions!r}")
    direct_url_text = importlib.metadata.distribution("pess-ess").read_text("direct_url.json")
    if direct_url_text is None:
        raise RuntimeError("pess-ess direct_url.json is missing")
    direct_url = json.loads(direct_url_text)
    installed_sha = direct_url.get("vcs_info", {}).get("commit_id")
    if installed_sha != ADVISOR_COMMIT:
        raise RuntimeError(f"installed Advisor pin mismatch: {installed_sha!r}")
    return {**versions, "advisor_source_commit": installed_sha}


def candidate_order_sha256(candidate_ids: list[str]) -> str:
    data = json.dumps(candidate_ids, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(data)


def verify_model_inputs(repo: Path, source: dict[str, Any], protocol: dict[str, Any],
                        dataset: str) -> dict[str, str]:
    """Recheck protocol-pinned artifacts and adapter provenance before solving."""
    model = protocol["frozen_inputs"][dataset]
    provenance = source["input_provenance"]
    if provenance.get("model_version") != model["model_version"]:
        raise RuntimeError("model version differs from protocol")
    if provenance.get("model_source_commit") != model["model_source_commit"]:
        raise RuntimeError("frozen model source commit differs from protocol")
    file_pins = [(model["frozen_selection_path"], model["frozen_selection_sha256"])]
    if dataset == "forest10":
        file_pins.append((model["coefficient_artifact_path"],
                          model["coefficient_artifact_sha256"]))
        provenance_pins = {
            "coefficient_artifact_sha256": model["coefficient_artifact_sha256"],
            "valid_truth_values_sha256": model["valid_truth_sha256"],
            "arecel_archive_sha256": model["arecel_archive_sha256"],
        }
    else:
        file_pins.append((model["plan_path"], model["plan_sha256"]))
        provenance_pins = {
            "plan_sha256": model["plan_sha256"],
            "coefficient_sha256": model["coefficient_sha256"],
            "observation_sha256": model["observation_sha256"],
            "valid_truth_sha256": model["valid_truth_sha256"],
            "arecel_archive_sha256": model["arecel_archive_sha256"],
        }
    provenance_pins["frozen_reference_sha256"] = model["frozen_selection_sha256"]
    checked: dict[str, str] = {}
    for relative_path, expected_sha in file_pins:
        actual_sha = sha256_file(repo / relative_path)
        if actual_sha != expected_sha:
            raise RuntimeError(f"frozen input hash mismatch: {relative_path}")
        checked[relative_path] = actual_sha
    for key, expected in provenance_pins.items():
        if provenance.get(key) != expected:
            raise RuntimeError(f"adapter provenance mismatch for {key}")
    return checked


def build_case_command(repo: Path, case: dict[str, Any], run_dir: Path,
                      python: str = sys.executable) -> list[str]:
    """Build exactly one bounded case invocation; this function starts nothing."""
    limits = load_json(CONFIG_PATH)["limits"]
    index = int(case["index"])
    if not 1 <= index <= 8:
        raise ValueError("case index outside the frozen eight-case matrix")
    case_dir = run_dir / f"{index:02d}-{case['case_id']}"
    resource_log = case_dir / "time.txt"
    return [
        "systemd-run", "--user", "--scope", "--quiet",
        "-p", f"MemoryMax={limits['memory_max_bytes']}",
        "-p", f"RuntimeMaxSec={limits['runtime_max_seconds_per_case']}",
        "--setenv=ESS_ISSUE74_B23_SCOPE_GUARD=1",
        "/usr/bin/time", "-v", "-o", str(resource_log),
        python, str(HERE / "run_stage2_b23.py"), "_case",
        "--repo", str(repo), "--run-dir", str(case_dir),
        "--case-index", str(index), "--scope-guard", "--systemd-scope",
    ]


def exact_reference(instance: Any, selected: frozenset[str], objective: str,
                    priority_order: list[str]) -> Fraction:
    from pess_ess.reference import reference_nominal_objective, reference_objective

    if objective == "nominal":
        value, _ = reference_nominal_objective(instance, selected, tuple(priority_order))
    else:
        value, _ = reference_objective(instance, selected)
    return value


def check_solver_status(response: dict[str, Any], *, response_json_finite: bool = True) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not response_json_finite:
        failures.append("nonfinite_or_nonstandard_response_value")
    statuses = response.get("solver_statuses")
    required = {
        "status_code", "message", "solver_reported_optimal", "incumbent_returned",
        "primal_objective", "dual_bound", "mip_gap", "duration_seconds",
        "highs_invocations", "selected_attempt",
    }
    if not isinstance(statuses, list) or not statuses:
        failures.append("missing_solver_statuses")
        statuses = []
    for index, status in enumerate(statuses):
        if not isinstance(status, dict) or not required <= set(status):
            failures.append(f"incomplete_solver_status_{index}")
            continue
        if status["highs_invocations"] != 1:
            failures.append(f"fallback_attempt_evidence_incomplete_{index}")
        if status["status_code"] != 0 or status["solver_reported_optimal"] is not True:
            failures.append(f"nonoptimal_solver_status_{index}")
        if status["incumbent_returned"] is not True:
            failures.append(f"solver_status_without_incumbent_{index}")
    if response.get("status") != "optimal":
        failures.append("advisor_status_not_optimal")
    if response.get("optimality", {}).get("solver_reported_optimal") is not True:
        failures.append("solver_optimality_not_reported")
    warnings = response.get("diagnostics", {}).get("numerical_warnings", [])
    if warnings:
        failures.append("numerical_warnings_present")
    return not failures, failures


def check_response_contract(response: dict[str, Any], payload: dict[str, Any],
                            protocol: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != protocol["immutable_software"]["advisor_schema_version"]:
        errors.append("request_schema_version_mismatch")
    if response.get("schema_version") != payload.get("schema_version"):
        errors.append("response_schema_version_mismatch")
    if response.get("objective") != payload.get("objective"):
        errors.append("response_objective_mismatch")
    expected_backend = protocol["objectives"][payload["objective"]]["backend"]
    if response.get("backend") != expected_backend:
        errors.append("response_backend_mismatch")
    if response.get("input_provenance") != payload.get("input_provenance"):
        errors.append("response_input_provenance_mismatch")
    provenance = response.get("provenance", {})
    if provenance.get("package_version") != protocol["immutable_software"]["pess_ess_version"]:
        errors.append("response_advisor_version_mismatch")
    if provenance.get("scipy_version") != protocol["immutable_software"]["scipy_version"]:
        errors.append("response_scipy_version_mismatch")
    return errors


def execute_case(repo: Path, run_dir: Path, case: dict[str, Any],
                 runner_commit: str, environment: dict[str, str],
                 config: dict[str, Any], protocol: dict[str, Any],
                 protocol_sha: str) -> dict[str, Any]:
    if os.environ.get("ESS_ISSUE74_B23_SCOPE_GUARD") != "1":
        raise RuntimeError("case process was not launched by the bounded runner")
    from pess_ess import solve_payload
    from pess_ess.model import instance_from_dict

    started = time.monotonic()
    dataset, objective, budget = case["dataset"], case["objective"], case["budget"]
    loader = {"forest10": adapter.forest10_request,
              "census13": adapter.census13_request}[dataset]
    source = loader(repo, budget=budget)
    verified_input_files = verify_model_inputs(repo, source, protocol, dataset)
    if len(source["instance"]["tasks"]) != 10_000:
        raise RuntimeError("full task universe was not loaded")
    model = protocol["frozen_inputs"][dataset]
    candidate_ids = source["_candidate_ids"]
    if len(candidate_ids) != model["candidate_count"]:
        raise RuntimeError("full candidate universe was not loaded")
    if candidate_order_sha256(candidate_ids) != model["candidate_order_sha256"]:
        raise RuntimeError("candidate order hash differs from protocol")
    frozen = source["_frozen_selection"]
    frozen_key = "Nominal" if objective == "nominal" else "PESS"
    frozen_case = frozen[frozen_key][str(budget)]
    expected_value = Fraction(frozen_case["objective_fraction"])
    expected_ties = [sorted(items) for items in frozen_case["all_optimal_sets"]]

    order = source["_nominal_priority_order"]
    payload = adapter.advisor_request_payload(
        source, objective, priority_order=order if objective == "nominal" else None)
    payload["input_provenance"]["advisor_source_commit"] = ADVISOR_COMMIT
    payload["options"] = protocol["solver_settings"]["options"]
    limits = protocol["solver_settings"]
    payload["limits"] = {
        "time_seconds": limits["case_time_seconds"],
        "total_time_seconds": limits["total_time_seconds"],
    }
    if objective == "pess":
        payload["limits"]["inner_time_seconds"] = limits["pess_inner_time_seconds"]

    payload_bytes = canonical(payload)
    instance = instance_from_dict(source["instance"])
    response = solve_payload(payload)
    try:
        response_bytes = canonical(response)
        response_json_finite = True
    except (TypeError, ValueError):
        response_bytes = (json.dumps(response, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=True) + "\n").encode("utf-8")
        response_json_finite = False
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "advisor-response.json").write_bytes(response_bytes)

    incumbent = response.get("incumbent", {})
    selected_raw = incumbent.get("selected")
    selected = frozenset(selected_raw) if isinstance(selected_raw, list) else None
    exact_value = None
    tie_member = False
    feasible = incumbent.get("validated_feasible") is True
    reference_errors: list[str] = []
    if selected is None:
        reference_errors.append("missing_selected_set")
    else:
        if len(selected) > budget or selected - set(candidate_ids):
            reference_errors.append("selected_set_violates_candidate_or_budget_scope")
        if instance.maintenance_cost(selected) > instance.budget:
            reference_errors.append("selected_set_is_infeasible_under_instance_cost")
        exact_value = exact_reference(instance, selected, objective, order)
        tie_member = sorted(selected) in expected_ties
        if exact_value != expected_value:
            reference_errors.append("selected_set_exact_objective_differs_from_frozen_optimum")
        if not tie_member:
            reference_errors.append("selected_set_not_in_frozen_exact_ties")
    statuses_ok, status_errors = check_solver_status(
        response, response_json_finite=response_json_finite)
    status_errors.extend(check_response_contract(response, payload, protocol))
    statuses_ok = statuses_ok and not status_errors
    if not feasible:
        reference_errors.append("incumbent_not_validated_feasible")
    passed = feasible and not reference_errors and statuses_ok
    request_sha = sha256_bytes(payload_bytes)
    response_sha = sha256_bytes(response_bytes)
    return {
        "format": "ess-issue74-stage2-b23-case-result-v1",
        "case_id": case["case_id"], "index": case["index"],
        "dataset": dataset, "objective": objective, "budget": budget,
        "outcome": "PASS" if passed else "STOP_FOR_REVIEW",
        "runner_source_commit": runner_commit,
        "stage1_adapter_base_commit": STAGE1_COMMIT,
        "protocol_merge_commit": PROTOCOL_MERGE,
        "protocol_sha256": protocol_sha,
        "runner_config_sha256": sha256_file(CONFIG_PATH),
        "advisor_source_commit": ADVISOR_COMMIT,
        "environment": environment,
        "request_sha256": request_sha,
        "response_sha256": response_sha,
        "response_sha256_method": ("canonical-json-v1" if response_json_finite
                                   else "python-json-nonfinite-fallback-v1"),
        "response_standard_json": response_json_finite,
        "model_version": source["input_provenance"]["model_version"],
        "input_provenance": payload["input_provenance"],
        "verified_input_file_sha256": verified_input_files,
        "task_count": len(instance.tasks),
        "candidate_count": len(instance.candidates),
        "candidate_ids": candidate_ids,
        "candidate_order_sha256": model["candidate_order_sha256"],
        "priority_order": order if objective == "nominal" else None,
        "selected": sorted(selected) if selected is not None else None,
        "validated_feasible": feasible,
        "solver_reported_objective": incumbent.get(
            "objective_value" if objective == "nominal" else "witness_aggregate"),
        "selected_set_exact_objective_fraction": str(exact_value) if exact_value is not None else None,
        "selected_set_exact_fraction_certified": exact_value is not None,
        "advisor_selected_pess_value_fraction_certified": response.get(
            "objective_evidence", {}).get("selected_pess_value_fraction_certified")
            if objective == "pess" else None,
        "frozen_exact_objective_fraction": str(expected_value),
        "frozen_exact_tie_sets": expected_ties,
        "selected_set_in_frozen_exact_ties": tie_member,
        "solver_status_complete_and_optimal": statuses_ok,
        "solver_status_errors": status_errors,
        "reference_or_acceptance_errors": reference_errors,
        "advisor_status": response.get("status"),
        "termination_reason": response.get("termination_reason"),
        "optimality": json_safe(response.get("optimality")),
        "objective_evidence": json_safe(response.get("objective_evidence")),
        "solver_statuses": json_safe(response.get("solver_statuses")),
        "wall_time_seconds": response.get("wall_time_seconds"),
        "numerical_warnings": json_safe(response.get("diagnostics", {}).get("numerical_warnings", [])),
        "runner_elapsed_seconds_inside_scope": time.monotonic() - started,
        "resource_log": "time.txt",
        "limits": config["limits"],
    }


def run_sequence(cases: list[dict[str, Any]], invoke: Any) -> list[dict[str, Any]]:
    """Invoke serially and stop immediately after the first non-PASS case."""
    outcomes: list[dict[str, Any]] = []
    for case in cases:
        result = invoke(case)
        outcomes.append(result)
        if result.get("outcome") != "PASS":
            break
    return outcomes


def case_child(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    config, protocol, protocol_sha = verify_static_pins(repo)
    runner_commit = verify_repo_gate(repo)
    environment = verify_environment()
    case = protocol["case_order"][args.case_index - 1]
    try:
        result = execute_case(repo, args.run_dir.resolve(), case, runner_commit,
                              environment, config, protocol, protocol_sha)
    except Exception as exc:
        result = {
            "format": "ess-issue74-stage2-b23-case-result-v1",
            "case_id": protocol["case_order"][args.case_index - 1]["case_id"],
            "index": args.case_index, "outcome": "STOP_FOR_REVIEW",
            "runner_source_commit": runner_commit,
            "protocol_merge_commit": PROTOCOL_MERGE,
            "protocol_sha256": protocol_sha,
            "error": repr(exc),
        }
        args.run_dir.mkdir(parents=True, exist_ok=True)
    (args.run_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8")
    print(json.dumps({"case_id": result["case_id"], "outcome": result["outcome"]}, sort_keys=True))
    return 0 if result["outcome"] == "PASS" else 2


def main_run(args: argparse.Namespace) -> int:
    if not args.research_owner_authorized:
        raise RuntimeError("pass --research-owner-authorized only after the reviewed-runner gate is met")
    repo = args.repo.resolve()
    config, protocol, protocol_sha = verify_static_pins(repo)
    runner_commit = verify_repo_gate(repo)
    environment = verify_environment()
    runtime_parent = Path(os.environ["ESS_RUNTIME_PARENT"]).resolve()
    if not CASE_RE.fullmatch(args.run_id):
        raise ValueError("run-id contains unsupported characters")
    run_root = runtime_parent / "ess-research" / "issue74" / f"stage2-b23-{args.run_id}"
    run_root.resolve().relative_to(runtime_parent)
    run_root.mkdir(parents=True, exist_ok=False)
    metadata = {
        "format": "ess-issue74-stage2-b23-run-metadata-v1",
        "status": "EXECUTION_STARTED_AFTER_REVIEW_GATE",
        "authorization_source": config["execution_authorization_source"],
        "runner_source_commit": runner_commit,
        "protocol_merge_commit": PROTOCOL_MERGE,
        "protocol_sha256": protocol_sha,
        "runner_config_sha256": sha256_file(CONFIG_PATH),
        "advisor_source_commit": ADVISOR_COMMIT,
        "environment": environment,
        "case_order": config["case_order"],
        "limits": config["limits"],
    }
    (run_root / "run-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def invoke(case: dict[str, Any]) -> dict[str, Any]:
        case_dir = run_root / f"{case['index']:02d}-{case['case_id']}"
        case_dir.mkdir()
        command = build_case_command(repo, case, run_root)
        with (case_dir / "runner.log").open("wb") as log:
            completed = subprocess.run(command, cwd=repo,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       check=False)
        result_path = case_dir / "result.json"
        if not result_path.is_file():
            result = {
                "format": "ess-issue74-stage2-b23-case-result-v1",
                "case_id": case["case_id"], "index": case["index"],
                "outcome": "STOP_FOR_REVIEW",
                "error": "systemd scope exited without a result; timeout/OOM/launch failure is possible",
                "systemd_exit_code": completed.returncode,
            }
        else:
            result = load_json(result_path)
            result["systemd_exit_code"] = completed.returncode
            if completed.returncode != 0 and result.get("outcome") == "PASS":
                result["outcome"] = "STOP_FOR_REVIEW"
                result["error"] = "systemd scope returned nonzero after case result"
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        with (run_root / "case-outcomes.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
        print(json.dumps({"case_id": case["case_id"], "outcome": result["outcome"]}, sort_keys=True), flush=True)
        return result

    outcomes = run_sequence(protocol["case_order"], invoke)
    final = "ALL_EIGHT_PASS" if len(outcomes) == 8 and all(
        item.get("outcome") == "PASS" for item in outcomes) else "STOPPED_FOR_REVIEW"
    (run_root / "run-summary.json").write_text(
        json.dumps({"status": final, "cases_attempted": len(outcomes),
                    "case_outcomes": [item.get("outcome") for item in outcomes]},
                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if final == "ALL_EIGHT_PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run the reviewed eight-case matrix")
    run_parser.add_argument("--repo", type=Path, required=True)
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--research-owner-authorized", action="store_true")
    child_parser = subparsers.add_parser("_case", help=argparse.SUPPRESS)
    child_parser.add_argument("--repo", type=Path, required=True)
    child_parser.add_argument("--run-dir", type=Path, required=True)
    child_parser.add_argument("--case-index", type=int, required=True, choices=range(1, 9))
    child_parser.add_argument("--scope-guard", action="store_true")
    child_parser.add_argument("--systemd-scope", action="store_true")
    args = parser.parse_args()
    if args.command == "_case":
        if not args.scope_guard or not args.systemd_scope:
            raise RuntimeError("internal case command requires systemd scope guards")
        return case_child(args)
    return main_run(args)


if __name__ == "__main__":
    raise SystemExit(main())

