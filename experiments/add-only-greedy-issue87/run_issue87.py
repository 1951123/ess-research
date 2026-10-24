"""Run the frozen Issue #87 cases after the separate execution gate is opened."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE / "protocol-v1.json"
ADAPTER_PATH = HERE / "adapter.py"
PROTOCOL_SHA256 = "ef095a12dd1a1ac676acd822e24d93e369b61cbd56297ced87b6771111f07623"
SCOPE_ENV = "ESS_ISSUE87_SYSTEMD_SCOPE"
RECORD_VERSION = "ess-issue87-greedy-case-v1"
CONTRAST_VERSION = "ess-issue87-greedy-contrast-v1"


def _load_adapter():
    spec = importlib.util.spec_from_file_location(
        "ess_issue87_frozen_adapter", ADAPTER_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load the frozen Issue #87 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = _load_adapter()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def jsonl_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    write_bytes(path, json_bytes(value))


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(jsonl_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_order_sha256(candidate_ids: list[str]) -> str:
    data = json.dumps(candidate_ids, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return sha256_bytes(data)


def protocol() -> dict[str, Any]:
    return read_json(PROTOCOL_PATH)


def require_execution_authorized(p: dict[str, Any] | None = None) -> None:
    frozen = protocol()
    if p is not None and p != frozen:
        raise PermissionError("in-memory protocol differs from protocol-v1 on disk")
    if frozen.get("execution_authorized") is not True:
        raise PermissionError(
            "protocol execution_authorized is false; no solver cases were started"
        )
    if sha256_file(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise PermissionError("protocol-v1 hash differs from the reviewed pin")


def case_plan(p: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    p = p or protocol()
    datasets = p["scope"]["datasets"]
    budgets = p["scope"]["budget_sequence"]
    if datasets != ["forest10", "census13"] or budgets != [0, 2, 3, 4, 5]:
        raise ValueError(
            "Issue #87 dataset or budget sequence differs from protocol-v1"
        )
    return [
        {
            "case_id": f"{dataset}-{objective}-b{budget}",
            "dataset": dataset,
            "budget": budget,
            "objective": objective,
        }
        for dataset in datasets
        for budget in budgets
        for objective in ("nominal", "pess")
    ]


def request_for_case(
    base_request: dict[str, Any], budget: int, objective: str
) -> dict[str, Any]:
    request = dict(base_request)
    request["instance"] = dict(base_request["instance"])
    request["instance"]["budget"] = str(budget)
    return adapter.adapt_request(request, objective)


def systemd_unit_name(run_id: str, case_id: str) -> str:
    safe_case = re.sub(r"[^A-Za-z0-9_.-]", "-", case_id)
    return f"ess-issue87-{run_id}-{safe_case}-{uuid4().hex[:8]}.scope"


def scope_command(
    unit_name: str,
    time_path: Path,
    child_args: list[str],
    p: dict[str, Any] | None = None,
) -> list[str]:
    p = p or protocol()
    limits = p["resource_limits"]
    command = [
        "systemd-run",
        "--user",
        "--scope",
        "--quiet",
        f"--unit={unit_name}",
        "-p",
        f"MemoryMax={limits['memory_limit_bytes']}",
        "-p",
        f"RuntimeMaxSec={limits['outer_hard_wall_seconds']}",
    ]
    command.extend(
        f"--setenv={key}={value}" for key, value in limits["thread_environment"].items()
    )
    command.append(f"--setenv={SCOPE_ENV}=1")
    command.extend(
        [
            "--",
            "/usr/bin/time",
            "-v",
            "-o",
            str(time_path),
            sys.executable,
            str(Path(__file__).resolve()),
            *child_args,
        ]
    )
    return command


def verify_advisor_install(p: dict[str, Any] | None = None) -> dict[str, str]:
    p = p or protocol()
    software = p["immutable_software"]
    expected_version = software["advisor_package"].split("==", 1)[1]
    distribution = importlib.metadata.distribution("pess-ess")
    installed_version = distribution.version
    direct_url = distribution.read_text("direct_url.json")
    if installed_version != expected_version or direct_url is None:
        raise RuntimeError(
            "pess-ess version or pinned Git installation metadata is missing"
        )
    vcs = json.loads(direct_url).get("vcs_info", {})
    if vcs.get("commit_id") != software["advisor_source_commit"]:
        raise RuntimeError("installed pess-ess commit differs from the protocol pin")
    versions = {
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
        "networkx": importlib.metadata.version("networkx"),
    }
    if versions != software["dependency_versions_for_future_execution"]:
        raise RuntimeError(
            "installed numerical dependency versions differ from the protocol pin"
        )
    return {
        "advisor_package": f"pess-ess=={installed_version}",
        "advisor_source_commit": vcs["commit_id"],
        **versions,
        "python": platform.python_version(),
    }


def verify_source_checkout(repo: Path, p: dict[str, Any] | None = None) -> str:
    p = p or protocol()
    software = p["immutable_software"]
    if repo.resolve() != ROOT:
        raise RuntimeError("runner and frozen inputs must come from the same checkout")
    if sha256_file(ADAPTER_PATH) != software["new_issue87_adapter_sha256"]:
        raise RuntimeError("Issue #87 adapter source hash differs from protocol-v1")
    model_path = repo / software["existing_model_adapter_path"]
    if sha256_file(model_path) != software["existing_model_adapter_sha256"]:
        raise RuntimeError("frozen model adapter hash differs from protocol-v1")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if dirty:
        raise RuntimeError("research checkout must be clean before a run")
    return head


def verify_run_environment(p: dict[str, Any]) -> dict[str, str]:
    if platform.system() != "Linux":
        raise RuntimeError("the frozen systemd resource envelope requires Linux")
    if (
        platform.python_version()
        != p["immutable_software"]["python_version_for_future_execution"]
    ):
        raise RuntimeError("Python version differs from the frozen future-run pin")
    for executable in ("systemd-run", "systemctl"):
        if shutil.which(executable) is None:
            raise RuntimeError(
                f"required resource-control command is unavailable: {executable}"
            )
    if not Path("/usr/bin/time").is_file():
        raise RuntimeError(
            "/usr/bin/time is required to capture case wall time and peak RSS"
        )
    return verify_advisor_install(p)


def scope_status(unit_name: str) -> dict[str, Any]:
    command = [
        "systemctl",
        "--user",
        "show",
        unit_name,
        "-p",
        "Id",
        "-p",
        "Result",
        "-p",
        "ActiveState",
        "-p",
        "ControlGroup",
        "-p",
        "ExecMainStatus",
        "-p",
        "MemoryMax",
        "-p",
        "MemoryPeak",
        "-p",
        "RuntimeMaxUSec",
    ]
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    properties = dict(
        line.split("=", 1) for line in completed.stdout.splitlines() if "=" in line
    )
    return {
        "available": completed.returncode == 0,
        "query_returncode": completed.returncode,
        "properties": properties,
        "raw_properties": completed.stdout,
        "query_stderr": completed.stderr,
    }


def active_scope_enforcement(unit_name: str, p: dict[str, Any]) -> dict[str, Any]:
    """Capture the active systemd limit and cgroup values from inside the scope."""
    limits = p["resource_limits"]
    deadline = monotonic() + 5
    status: dict[str, Any] = {"available": False, "properties": {}}
    while monotonic() < deadline:
        status = scope_status(unit_name)
        properties = status.get("properties", {})
        if status.get("available") and properties.get("ActiveState") == "active":
            break
        sleep(0.05)

    properties = status.get("properties", {}) if status.get("available") else {}
    errors: list[str] = []
    control_group = properties.get("ControlGroup")
    process_group = None
    cgroup_memory_max = None
    cgroup_memory_max_bytes = None
    if not status.get("available"):
        errors.append("systemd_status_unavailable_while_active")
    if properties.get("Id") != unit_name:
        errors.append("active_scope_unit_id_missing_or_mismatched")
    if properties.get("ActiveState") != "active":
        errors.append("scope_not_observed_active")
    if properties.get("MemoryMax") != str(limits["memory_limit_bytes"]):
        errors.append("active_memory_max_missing_or_mismatched")
    if (
        systemd_seconds(properties.get("RuntimeMaxUSec", ""))
        != limits["outer_hard_wall_seconds"]
    ):
        errors.append("active_runtime_max_missing_or_mismatched")
    try:
        process_group = next(
            line.split("::", 1)[1]
            for line in Path("/proc/self/cgroup")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith("0::")
        )
        if process_group != control_group:
            errors.append("process_cgroup_does_not_match_active_scope")
        cgroup_root = Path("/sys/fs/cgroup").resolve()
        cgroup_path = (cgroup_root / str(control_group).lstrip("/")).resolve()
        if cgroup_root not in cgroup_path.parents:
            raise ValueError("scope cgroup is outside the cgroup-v2 mount")
        cgroup_memory_max = (
            (cgroup_path / "memory.max").read_text(encoding="ascii").strip()
        )
        if cgroup_memory_max.isdigit():
            cgroup_memory_max_bytes = int(cgroup_memory_max)
        if cgroup_memory_max_bytes != limits["memory_limit_bytes"]:
            errors.append("cgroup_memory_max_missing_or_mismatched")
    except (OSError, StopIteration, ValueError) as exc:
        errors.append(f"active_cgroup_memory_limit_unavailable:{type(exc).__name__}")
    return {
        "format": "ess-issue87-active-scope-enforcement-v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "unit": unit_name,
        "verified": not errors,
        "verification_errors": errors,
        "properties": properties,
        "control_group": control_group,
        "process_control_group": process_group,
        "cgroup_memory_max": cgroup_memory_max,
        "cgroup_memory_max_bytes": cgroup_memory_max_bytes,
        "status_query": status,
    }


def scope_enforcement_errors(
    evidence: dict[str, Any] | None, p: dict[str, Any]
) -> list[str]:
    limits = p["resource_limits"]
    failures: list[str] = []
    if not evidence or evidence.get("verified") is not True:
        failures.append("active_scope_limit_verification_missing_or_failed")
    properties = evidence.get("properties", {}) if evidence else {}
    if properties.get("ActiveState") != "active":
        failures.append("scope_not_verified_active")
    if properties.get("MemoryMax") != str(limits["memory_limit_bytes"]):
        failures.append("active_memory_limit_missing_or_mismatched")
    if (
        systemd_seconds(properties.get("RuntimeMaxUSec", ""))
        != limits["outer_hard_wall_seconds"]
    ):
        failures.append("active_wall_limit_missing_or_mismatched")
    if evidence and evidence.get("control_group") != evidence.get(
        "process_control_group"
    ):
        failures.append("active_scope_cgroup_identity_mismatch")
    cgroup_memory = evidence.get("cgroup_memory_max_bytes") if evidence else None
    if cgroup_memory != limits["memory_limit_bytes"]:
        failures.append("active_cgroup_memory_limit_missing_or_mismatched")
    return failures


def write_active_scope_enforcement(
    unit_name: str, evidence_path: Path, p: dict[str, Any]
) -> dict[str, Any]:
    evidence = active_scope_enforcement(unit_name, p)
    write_json(evidence_path, evidence)
    errors = scope_enforcement_errors(evidence, p)
    if errors:
        raise RuntimeError(";".join(errors))
    return evidence


def time_report(path: Path) -> dict[str, float | int] | None:
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8", errors="replace")
    rss_match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", raw)
    wall_match = re.search(
        r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([0-9:.]+)", raw
    )
    if rss_match is None or wall_match is None:
        return None
    units = [float(part) for part in wall_match.group(1).split(":")]
    wall_seconds = sum(
        value * (60**index) for index, value in enumerate(reversed(units))
    )
    return {
        "wall_seconds": wall_seconds,
        "peak_rss_bytes": int(rss_match.group(1)) * 1024,
    }


def systemd_seconds(value: str) -> float | None:
    """Parse systemctl's human-readable RuntimeMaxUSec property."""
    units = {"us": 1e-6, "ms": 1e-3, "s": 1, "min": 60, "h": 3600, "d": 86400}
    compact = value.replace(" ", "")
    parts = list(re.finditer(r"(\d+(?:\.\d+)?)(us|ms|min|s|h|d)", compact))
    if not parts or "".join(part.group(0) for part in parts) != compact:
        return None
    return sum(float(part.group(1)) * units[part.group(2)] for part in parts)


def scope_errors(
    invoked: dict[str, Any],
    p: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if invoked.get("launch_error"):
        failures.append("systemd_scope_launch_failed")
    if invoked.get("returncode") != 0:
        failures.append("systemd_scope_returncode_nonzero_or_missing")
    status = invoked.get("systemd_status", {})
    props = status.get("properties", {}) if status.get("available") else {}
    if not status.get("available"):
        failures.append("systemd_status_unavailable")
    if props.get("Result") != "success":
        failures.append(f"systemd_result_{props.get('Result', 'unknown')}")
    if props.get("ExecMainStatus") not in (None, "", "0"):
        failures.append("systemd_exec_status_nonzero_or_missing")
    limits = p["resource_limits"]
    failures.extend(scope_enforcement_errors(invoked.get("live_scope_enforcement"), p))
    measured = invoked.get("time_report")
    if measured is None:
        failures.append("time_or_peak_rss_measurement_missing")
    elif measured["peak_rss_bytes"] > limits["memory_limit_bytes"]:
        failures.append("measured_peak_rss_exceeded_memory_limit")
    if invoked.get("wall_seconds", 0) > limits["outer_hard_wall_seconds"]:
        failures.append("outer_wall_limit_exceeded")
    memory_peak = props.get("MemoryPeak")
    if (
        memory_peak
        and memory_peak.isdigit()
        and int(memory_peak) > limits["memory_limit_bytes"]
    ):
        failures.append("systemd_memory_peak_exceeded_memory_limit")
    return failures


def candidate_cost(request: dict[str, Any], selected: set[str]) -> Fraction:
    costs = {
        item["id"]: Fraction(item["maintenance_cost"])
        for item in request["instance"]["candidates"]
    }
    return sum((costs[item] for item in selected), Fraction(0))


def request_errors(
    case: dict[str, Any], request: dict[str, Any], p: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    frozen = p["frozen_inputs"][case["dataset"]]
    instance = request.get("instance")
    if not isinstance(instance, dict):
        return ["request_instance_missing"]
    candidates = instance.get("candidates", [])
    tasks = instance.get("tasks", [])
    if not isinstance(candidates, list) or not isinstance(tasks, list):
        return ["request_candidate_or_task_list_malformed"]
    if any(not isinstance(item, dict) for item in candidates) or any(
        not isinstance(item, dict) for item in tasks
    ):
        return ["request_candidate_or_task_record_malformed"]
    candidate_ids = [item.get("id") for item in candidates if isinstance(item, dict)]
    provenance = request.get("input_provenance", {})
    if not isinstance(provenance, dict):
        return ["request_input_provenance_missing"]
    if request.get("objective") != case["objective"]:
        failures.append("request_objective_mismatch")
    if request.get("backend") != "add_only_greedy":
        failures.append("request_backend_mismatch")
    if instance.get("budget") != str(case["budget"]):
        failures.append("request_budget_mismatch")
    if len(tasks) != frozen["valid_task_count"]:
        failures.append("request_task_count_mismatch")
    if len(candidates) != frozen["candidate_count"]:
        failures.append("request_candidate_count_mismatch")
    if candidate_order_sha256(candidate_ids) != frozen["candidate_order_sha256"]:
        failures.append("request_candidate_order_mismatch")
    if any(item.get("maintenance_cost") != "1" for item in candidates):
        failures.append("request_unit_cost_mismatch")
    if provenance.get("issue87_dataset") != case["dataset"]:
        failures.append("request_dataset_provenance_mismatch")
    if provenance.get("model_version") != frozen["model_version"]:
        failures.append("request_model_version_mismatch")
    if provenance.get("issue87_model_source_commit") != frozen["model_source_commit"]:
        failures.append("request_model_source_commit_mismatch")
    if (
        provenance.get("advisor_source_commit")
        != p["immutable_software"]["advisor_source_commit"]
    ):
        failures.append("request_advisor_commit_mismatch")
    if (
        provenance.get("issue87_adapter_source_sha256")
        != p["immutable_software"]["new_issue87_adapter_sha256"]
    ):
        failures.append("request_adapter_hash_mismatch")
    if request.get("objective") == "nominal":
        priority = request.get("priority_order", [])
        if candidate_order_sha256(priority) != frozen["candidate_order_sha256"]:
            failures.append("request_nominal_priority_mismatch")
    elif "priority_order" in request:
        failures.append("pess_request_must_not_contain_nominal_priority")
    expected_caps = p["resource_limits"]["per_dataset_budget_caps"][
        case["dataset"]
    ].get(str(case["budget"]))
    if expected_caps is None:
        return [*failures, "request_budget_outside_frozen_cap_table"]
    limits = request.get("limits", {})
    if not isinstance(limits, dict):
        return [*failures, "request_limits_malformed"]
    if limits.get("max_evaluations") != expected_caps["max_evaluations"]:
        failures.append("request_evaluation_cap_mismatch")
    if (
        case["objective"] == "pess"
        and limits.get("max_inner_matching_subsets")
        != expected_caps["max_inner_matching_subsets_pess"]
    ):
        failures.append("request_pess_subset_cap_mismatch")
    return failures


def response_errors(
    request: dict[str, Any], response: dict[str, Any], p: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    objective = request.get("objective")
    if (
        response.get("schema_version")
        != p["immutable_software"]["advisor_schema_version"]
        or response.get("backend") != "add_only_greedy"
        or response.get("objective") != objective
    ):
        failures.append("response_schema_backend_or_objective_mismatch")
    if response.get("status") != "heuristic_completed":
        failures.append("advisor_response_not_heuristic_completed")
    if not isinstance(response.get("termination_reason"), str) or not response.get(
        "termination_reason"
    ):
        failures.append("advisor_termination_reason_missing")
    incumbent = response.get("incumbent")
    if (
        not isinstance(incumbent, dict)
        or incumbent.get("validated_feasible") is not True
    ):
        failures.append("advisor_incumbent_not_validated_feasible")
        incumbent = incumbent if isinstance(incumbent, dict) else {}
    selected = incumbent.get("selected")
    candidates = request["instance"]["candidates"]
    candidate_ids = [item["id"] for item in candidates]
    if (
        not isinstance(selected, list)
        or any(not isinstance(item, str) for item in selected)
        or len(set(selected)) != len(selected)
        or set(selected) - set(candidate_ids)
    ):
        failures.append("selected_set_missing_duplicated_or_outside_candidate_universe")
        selected_set: set[str] = set()
    else:
        selected_set = set(selected)
    budget = Fraction(request["instance"]["budget"])
    cost = candidate_cost(request, selected_set)
    if cost > budget or incumbent.get("maintenance_cost") != str(cost):
        failures.append("selected_set_cost_or_budget_mismatch")
    objective_value = incumbent.get("objective_value")
    try:
        if (
            not isinstance(objective_value, str)
            or str(Fraction(objective_value)) != objective_value
        ):
            failures.append("selected_objective_missing_or_noncanonical_fraction")
    except (ValueError, ZeroDivisionError):
        failures.append("selected_objective_missing_or_noncanonical_fraction")
    evidence = response.get("objective_evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    if evidence.get("selected_objective_fraction_certified") is not True:
        failures.append("selected_objective_fraction_not_certified")
    optimality = response.get("optimality", {})
    if not isinstance(optimality, dict):
        optimality = {}
    if optimality.get("outer_global_optimum_fraction_certified") is not False:
        failures.append("outer_global_optimum_claim_must_remain_false")
    greedy = response.get("greedy", {})
    if not isinstance(greedy, dict):
        failures.append("greedy_work_record_missing")
        return failures
    fixed_calls = greedy.get("fixed_set_evaluation_calls")
    completed_calls = greedy.get("completed_fixed_set_evaluations")
    candidate_attempts = greedy.get("candidate_attempts")
    if (
        not isinstance(fixed_calls, int)
        or isinstance(fixed_calls, bool)
        or not isinstance(completed_calls, int)
        or isinstance(completed_calls, bool)
        or fixed_calls < 1
        or completed_calls != fixed_calls
    ):
        failures.append("greedy_candidate_round_incomplete")
    if not isinstance(candidate_attempts, int) or isinstance(candidate_attempts, bool):
        failures.append("greedy_candidate_attempt_count_missing")
    addition_order = greedy.get("addition_order")
    if (
        not isinstance(addition_order, list)
        or any(not isinstance(item, str) for item in addition_order)
        or len(set(addition_order)) != len(addition_order)
        or set(addition_order) != selected_set
    ):
        failures.append("greedy_addition_order_does_not_match_selected_set")
    limits = request.get("limits", {})
    if isinstance(fixed_calls, int) and fixed_calls > limits.get("max_evaluations", 0):
        failures.append("fixed_set_evaluation_cap_exceeded")
    provenance = request.get("input_provenance", {})
    dataset = provenance.get("issue87_dataset")
    budget_key = request.get("instance", {}).get("budget")
    candidate_cap = (
        p["resource_limits"]["per_dataset_budget_caps"]
        .get(dataset, {})
        .get(budget_key, {})
        .get("candidate_attempts_upper_bound")
    )
    if (
        isinstance(candidate_attempts, int)
        and isinstance(candidate_cap, int)
        and candidate_attempts > candidate_cap
    ):
        failures.append("candidate_attempt_cap_exceeded")
    inner = greedy.get("inner_oracle_work", {})
    if not isinstance(inner, dict):
        inner = {}
    inner_cap = limits.get("max_inner_matching_subsets")
    for field in ("matching_subsets_examined", "maximal_matchings_scored"):
        value = inner.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            failures.append(f"inner_work_counter_missing:{field}")
    subset_count = inner.get("matching_subsets_examined")
    if objective == "pess":
        if (
            isinstance(inner_cap, int)
            and isinstance(subset_count, int)
            and subset_count > inner_cap
        ):
            failures.append("pess_inner_subset_cap_exceeded")
    advisor_wall = response.get("wall_time_seconds")
    if (
        not isinstance(advisor_wall, (int, float))
        or isinstance(advisor_wall, bool)
        or not math.isfinite(advisor_wall)
        or advisor_wall < 0
        or advisor_wall > limits.get("total_time_seconds", 0)
    ):
        failures.append("advisor_total_time_limit_exceeded_or_missing")
    return failures


def _overlap(request: dict[str, Any], selected: list[str]) -> dict[str, int]:
    endpoints = {
        item["id"]: item["endpoints"] for item in request["instance"]["candidates"]
    }
    counts = Counter(endpoint for item in selected for endpoint in endpoints[item])
    shared = {endpoint for endpoint, count in counts.items() if count >= 2}
    pair_count = sum(count * (count - 1) // 2 for count in counts.values())
    incidence = 0
    tasks_with_overlap = 0
    for task in request["instance"]["tasks"]:
        eligible = set(task["eligible_candidates"]) & set(selected)
        task_counts = Counter(
            endpoint for item in eligible for endpoint in endpoints[item]
        )
        task_shared = sum(count >= 2 for count in task_counts.values())
        incidence += task_shared
        tasks_with_overlap += task_shared > 0
    return {
        "global_overlapping_endpoint_count": len(shared),
        "global_overlapping_resource_pair_count": pair_count,
        "task_applicable_overlap_incidence_count": incidence,
        "tasks_with_task_applicable_overlap": tasks_with_overlap,
    }


def frozen_input_hashes(p: dict[str, Any], dataset: str) -> dict[str, str]:
    frozen = p["frozen_inputs"][dataset]
    hashes = {
        "frozen_archive": p["frozen_inputs"]["archive_sha256"],
        "frozen_selection": frozen["frozen_selection_sha256"],
        "valid_truth": frozen["valid_truth_sha256"],
    }
    if dataset == "forest10":
        hashes["coefficients"] = frozen["coefficient_artifact_sha256"]
        hashes["model_builder"] = frozen["model_builder_sha256"]
        hashes["exact_selector"] = frozen["exact_selector_sha256"]
    else:
        hashes["plan"] = frozen["plan_sha256"]
        hashes["coefficient_digest"] = frozen["coefficient_digest_sha256"]
        for index, value in enumerate(frozen["valid_observation_sha256"]):
            hashes[f"worker{index}_observations"] = value
    return hashes


def input_hashes(
    request: dict[str, Any] | None, p: dict[str, Any], dataset: str
) -> dict[str, str]:
    hashes = frozen_input_hashes(p, dataset)
    if request is not None:
        provenance = request.get("input_provenance", {})
        if isinstance(provenance, dict):
            for name, value in provenance.items():
                if "sha256" in name and isinstance(value, str) and len(value) == 64:
                    hashes[name] = value
    return hashes


def work_counters(response: dict[str, Any] | None) -> dict[str, int]:
    greedy = response.get("greedy", {}) if response else {}
    if not isinstance(greedy, dict):
        greedy = {}
    inner = greedy.get("inner_oracle_work", {})
    if not isinstance(inner, dict):
        inner = {}

    def count(value: Any) -> int:
        return value if isinstance(value, int) and value >= 0 else 0

    return {
        "candidate_attempts": count(greedy.get("candidate_attempts")),
        "fixed_set_evaluation_calls": count(greedy.get("fixed_set_evaluation_calls")),
        "completed_fixed_set_evaluations": count(
            greedy.get("completed_fixed_set_evaluations")
        ),
        "matching_subsets_examined": count(inner.get("matching_subsets_examined")),
        "maximal_matchings_scored": count(inner.get("maximal_matchings_scored")),
    }


def case_record(
    case: dict[str, Any],
    p: dict[str, Any],
    run_commit: str,
    request: dict[str, Any] | None,
    request_raw: bytes | None,
    response: dict[str, Any] | None,
    response_raw: bytes | None,
    invoked: dict[str, Any],
    failure_reasons: list[str],
) -> dict[str, Any]:
    dataset, objective = case["dataset"], case["objective"]
    frozen = p["frozen_inputs"][dataset]
    selected = None
    prefix = None
    addition_order = None
    objective_fraction = None
    complete = (
        not failure_reasons
        and request is not None
        and response is not None
        and response.get("status") == "heuristic_completed"
        and isinstance(response.get("incumbent"), dict)
        and isinstance(response.get("greedy"), dict)
    )
    incumbent: dict[str, Any] = {}
    greedy: dict[str, Any] = {}
    if response is not None:
        value = response.get("incumbent", {})
        incumbent = value if isinstance(value, dict) else {}
        value = response.get("greedy", {})
        greedy = value if isinstance(value, dict) else {}
        if complete:
            selected = incumbent.get("selected")
            addition_order = greedy.get("addition_order")
            objective_fraction = incumbent.get("objective_value")
        else:
            prefix = greedy.get("addition_order") or incumbent.get("selected")
    if complete:
        selected = response["incumbent"]["selected"]
    budget_used = incumbent.get("maintenance_cost") if response else None
    budget_unused = incumbent.get("unused_budget") if response else None
    req_provenance = request.get("input_provenance", {}) if request else {}
    if not isinstance(req_provenance, dict):
        req_provenance = {}
    systemd = invoked.get("systemd_status", {})
    properties = systemd.get("properties", {}) if systemd.get("available") else {}
    time_data = invoked.get("time_report") or {}
    request_sha = sha256_bytes(request_raw) if request_raw is not None else None
    response_sha = sha256_bytes(response_raw) if response_raw else None
    objective_trace = []
    if response and isinstance(greedy.get("steps"), list):
        objective_trace = [
            {
                "candidate_id": step["candidate_id"],
                "objective_before_fraction": step["objective_before"],
                "objective_after_fraction": step["objective_after"],
                "improvement_fraction": step["improvement"],
            }
            for step in greedy["steps"]
            if isinstance(step, dict)
            and {
                "candidate_id",
                "objective_before",
                "objective_after",
                "improvement",
            }
            <= set(step)
        ]
    if selected is not None and request is not None:
        overlap = _overlap(request, selected)
    else:
        overlap = None
    limits = p["resource_limits"]
    return {
        "schema_version": RECORD_VERSION,
        "case_id": case["case_id"],
        "dataset": dataset,
        "model_version": frozen["model_version"],
        "objective": objective,
        "backend": "add_only_greedy",
        "budget": case["budget"],
        "task_count": len(request["instance"]["tasks"])
        if request
        else frozen["valid_task_count"],
        "candidate_count": len(request["instance"]["candidates"])
        if request
        else frozen["candidate_count"],
        "candidate_order_sha256": frozen["candidate_order_sha256"],
        "nominal_priority_order_sha256": (
            candidate_order_sha256(request["priority_order"])
            if request is not None and objective == "nominal"
            else None
        ),
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "process_exit_status": invoked.get("returncode"),
        "termination_reason": (
            ";".join(failure_reasons)
            if not complete
            else response.get("termination_reason", "unknown")
        ),
        "selected_ids": sorted(selected) if selected is not None else None,
        "last_completed_prefix": prefix,
        "addition_order": addition_order,
        "objective_fraction": objective_fraction,
        "objective_trace": objective_trace,
        "budget_used": budget_used,
        "budget_unused": budget_unused,
        "outer_global_optimum_claim": False,
        "resource_overlap": overlap,
        "wall_seconds": time_data.get("wall_seconds", invoked.get("wall_seconds", 0.0)),
        "peak_rss_bytes": time_data.get("peak_rss_bytes"),
        "resource_limits": {
            "advisor_total_time_seconds": limits["advisor_total_time_seconds"],
            "outer_hard_wall_seconds": limits["outer_hard_wall_seconds"],
            "memory_limit_bytes": limits["memory_limit_bytes"],
            "processes": limits["processes"],
            "cpu_threads": limits["cpu_threads"],
            "thread_environment": limits["thread_environment"],
            "max_evaluations": request.get("limits", {}).get("max_evaluations")
            if request
            else None,
            "max_inner_matching_subsets": request.get("limits", {}).get(
                "max_inner_matching_subsets"
            )
            if request
            else None,
            "effective_systemd": properties,
        },
        "work_counters": work_counters(response),
        "input_hashes": input_hashes(request, p, dataset),
        "advisor_source_commit": req_provenance.get(
            "advisor_source_commit", p["immutable_software"]["advisor_source_commit"]
        ),
        "research_adapter_source_sha256": p["immutable_software"][
            "new_issue87_adapter_sha256"
        ],
        "issue87_run_source_commit": req_provenance.get(
            "issue87_run_source_commit", run_commit
        ),
        "request_sha256": request_sha,
        "response_sha256": response_sha,
    }


def unstarted_case_record(
    case: dict[str, Any], p: dict[str, Any], run_commit: str
) -> dict[str, Any]:
    record = case_record(
        case,
        p,
        run_commit,
        None,
        None,
        None,
        None,
        {"wall_seconds": 0.0},
        ["not_started_after_prior_failure"],
    )
    return record


def contrast_record(
    dataset: str,
    budget: int,
    p: dict[str, Any],
    nominal: dict[str, Any] | None,
    pess: dict[str, Any] | None,
    cross: dict[str, Any] | None,
    failure_reason: str | None,
) -> dict[str, Any]:
    n_complete = nominal is not None and nominal.get("status") == "COMPLETE"
    p_complete = pess is not None and pess.get("status") == "COMPLETE"
    both_complete = n_complete and p_complete
    n_ids = nominal["selected_ids"] if n_complete else None
    p_ids = pess["selected_ids"] if p_complete else None
    same = n_ids == p_ids if both_complete else None
    n_count = len(n_ids) if n_ids is not None else None
    p_count = len(p_ids) if p_ids is not None else None
    values: dict[str, str | None] = {
        "nominal_objective_on_nominal_set_fraction": None,
        "nominal_objective_on_pess_set_fraction": None,
        "pess_objective_on_nominal_set_fraction": None,
        "pess_objective_on_pess_set_fraction": None,
    }
    work: dict[str, Any] = {
        "fixed_set_evaluation_calls": 0,
        "matching_subsets_examined": 0,
        "maximal_matchings_scored": 0,
        "wall_seconds": 0.0,
    }
    if cross is not None:
        for key in values:
            values[key] = cross.get(key)
        work.update(cross.get("cross_evaluation_work", {}))
    if failure_reason is not None or not both_complete or cross is None:
        classification = "incomplete_or_censored"
        status = "INCOMPLETE_OR_CENSORED"
        gap = None
    else:
        status = "COMPLETE"
        pess_on_nominal = Fraction(values["pess_objective_on_nominal_set_fraction"])
        pess_on_pess = Fraction(values["pess_objective_on_pess_set_fraction"])
        gap = str(pess_on_nominal - pess_on_pess)
        if same:
            classification = "same_set"
        elif Fraction(gap) == 0:
            classification = "different_set_equal_pess_objective"
        elif Fraction(gap) > 0:
            classification = (
                "different_set_positive_pess_regret_vs_pess_heuristic_incumbent"
            )
        else:
            classification = (
                "different_set_negative_pess_gap_vs_pess_heuristic_incumbent"
            )
    n_budget = nominal.get("budget_used") if n_complete else None
    p_budget = pess.get("budget_used") if p_complete else None

    def relation(
        left: int | Fraction | None, right: int | Fraction | None
    ) -> str | None:
        if left is None or right is None:
            return None
        return "more" if left > right else "fewer" if left < right else "equal"

    return {
        "schema_version": CONTRAST_VERSION,
        "contrast_id": f"{dataset}-b{budget}",
        "dataset": dataset,
        "model_version": p["frozen_inputs"][dataset]["model_version"],
        "budget": budget,
        "status": status,
        "nominal_selected_ids": n_ids,
        "pess_selected_ids": p_ids,
        "same_set": same,
        "nominal_selected_count": n_count,
        "pess_selected_count": p_count,
        "nominal_budget_used_fraction": n_budget,
        "pess_budget_used_fraction": p_budget,
        "nominal_vs_pess_resource_count_relation": relation(n_count, p_count),
        "nominal_vs_pess_proxy_budget_use_relation": relation(
            Fraction(n_budget) if n_budget is not None else None,
            Fraction(p_budget) if p_budget is not None else None,
        ),
        **values,
        "pess_gap_nominal_minus_pess_incumbent_fraction": gap,
        "classification": classification,
        "cross_evaluation_work": work,
        "failure_reason": failure_reason,
    }


def _scope_invocation(
    repo: Path,
    run_id: str,
    case_id: str,
    directory: Path,
    child_args: list[str],
    p: dict[str, Any],
) -> dict[str, Any]:
    unit = systemd_unit_name(run_id, case_id)
    stdout_path = directory / "response.json"
    stderr_path = directory / "stderr.txt"
    time_path = directory / "resource-usage.txt"
    enforcement_path = directory / "scope-enforcement.json"
    child_args = [*child_args, "--scope-unit", unit]
    command = scope_command(unit, time_path, child_args, p)
    started = monotonic()
    launch_error = None
    returncode = None
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            completed = subprocess.run(
                command,
                cwd=repo,
                stdout=stdout,
                stderr=stderr,
                check=False,
                timeout=p["resource_limits"]["outer_hard_wall_seconds"] + 30,
            )
            returncode = completed.returncode
    except subprocess.TimeoutExpired:
        launch_error = "systemd-run client exceeded the outer wait timeout"
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", unit],
                check=False,
                capture_output=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            launch_error += f"; scope stop failed: {type(exc).__name__}: {exc}"
    except (OSError, subprocess.SubprocessError) as exc:
        launch_error = f"{type(exc).__name__}: {exc}"
    elapsed = max(0.0, monotonic() - started)
    status = scope_status(unit)
    write_json(directory / "systemd-status.json", status)
    try:
        live_enforcement = read_json(enforcement_path)
    except (OSError, ValueError):
        live_enforcement = None
    measured = time_report(time_path)
    invocation = {
        "unit": unit,
        "command": command,
        "returncode": returncode,
        "launch_error": launch_error,
        "wall_seconds": elapsed,
        "time_report": measured,
        "systemd_status": status,
        "live_scope_enforcement": live_enforcement,
    }
    write_json(directory / "execution.json", invocation)
    return invocation


def _read_response(
    path: Path,
) -> tuple[dict[str, Any] | None, bytes | None, str | None]:
    if not path.is_file():
        return None, None, "advisor_response_missing"
    raw = path.read_bytes()
    if not raw:
        return None, raw, "advisor_response_empty"
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, raw, f"advisor_response_invalid_json:{type(exc).__name__}"
    if not isinstance(value, dict):
        return None, raw, "advisor_response_not_object"
    return value, raw, None


def _case_attempt(
    repo: Path,
    run_root: Path,
    run_id: str,
    case: dict[str, Any],
    base_request_path: Path | None,
    run_commit: str,
    p: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    directory = run_root / "cases" / case["case_id"]
    directory.mkdir(parents=True)
    if base_request_path is None:
        worker_args = [
            "_case",
            "--repo",
            str(repo),
            "--case-dir",
            str(directory),
            "--dataset",
            case["dataset"],
            "--budget",
            str(case["budget"]),
            "--objective",
            case["objective"],
            "--build-frozen-input",
        ]
    else:
        worker_args = [
            "_case",
            "--repo",
            str(repo),
            "--case-dir",
            str(directory),
            "--dataset",
            case["dataset"],
            "--budget",
            str(case["budget"]),
            "--objective",
            case["objective"],
            "--base-request",
            str(base_request_path),
        ]
    invoked = _scope_invocation(
        repo, run_id, case["case_id"], directory, worker_args, p
    )
    request_path = directory / "request.json"
    request_raw = request_path.read_bytes() if request_path.is_file() else None
    request = None
    request_error = None
    if request_raw is not None:
        try:
            request = json.loads(request_raw)
            if not isinstance(request, dict):
                request = None
                request_error = "request_json_not_object"
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            request_error = f"request_json_invalid:{type(exc).__name__}"
    response, response_raw, response_error = _read_response(directory / "response.json")
    errors = scope_errors(invoked, p)
    if request_error:
        errors.append(request_error)
    if request is None:
        errors.append("complete_request_missing")
    if response_error:
        errors.append(response_error)
    if request is not None and response is not None:
        request_failures = request_errors(case, request, p)
        errors.extend(request_failures)
        if not request_failures:
            errors.extend(response_errors(request, response, p))
    record = case_record(
        case,
        p,
        run_commit,
        request,
        request_raw,
        response,
        response_raw,
        invoked,
        errors,
    )
    if record["status"] == "COMPLETE":
        write_json(directory / "result.json", record)
    else:
        write_json(
            directory / "failure.json",
            {
                "format": "ess-issue87-greedy-failure-v1",
                "case_id": case["case_id"],
                "failure_reasons": errors,
                "systemd_returncode": invoked.get("returncode"),
                "systemd_launch_error": invoked.get("launch_error"),
                "systemd_status": invoked.get("systemd_status"),
                "stderr_file": "stderr.txt",
                "response_file": "response.json" if response_raw else None,
                "request_file": "request.json" if request_raw else None,
                "last_completed_prefix": record["last_completed_prefix"],
            },
        )
    append_jsonl(run_root / "case-results.jsonl", record)
    return record, request_path


def _cross_attempt(
    repo: Path,
    run_root: Path,
    run_id: str,
    dataset: str,
    budget: int,
    nominal_request: Path,
    nominal_result: Path,
    pess_result: Path,
    p: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    case_id = f"{dataset}-cross-b{budget}"
    directory = run_root / "contrasts" / case_id
    directory.mkdir(parents=True)
    child_args = [
        "_cross",
        "--case-dir",
        str(directory),
        "--request",
        str(nominal_request),
        "--nominal-result",
        str(nominal_result),
        "--pess-result",
        str(pess_result),
    ]
    invoked = _scope_invocation(repo, run_id, case_id, directory, child_args, p)
    raw = (
        (directory / "response.json").read_bytes()
        if (directory / "response.json").is_file()
        else b""
    )
    errors = scope_errors(invoked, p)
    try:
        response = json.loads(raw) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        response = None
        errors.append("cross_evaluation_response_invalid_json")
    if not isinstance(response, dict):
        errors.append("cross_evaluation_response_missing")
        response = None
    else:
        expected_fields = (
            "nominal_objective_on_nominal_set_fraction",
            "nominal_objective_on_pess_set_fraction",
            "pess_objective_on_nominal_set_fraction",
            "pess_objective_on_pess_set_fraction",
        )
        try:
            for field in expected_fields:
                value = response[field]
                if str(Fraction(value)) != value:
                    raise ValueError(field)
            work = response["cross_evaluation_work"]
            if work["fixed_set_evaluation_calls"] != 4:
                raise ValueError("fixed_set_evaluation_calls")
            subset_cap = (
                2 * p["frozen_inputs"][dataset]["valid_task_count"] * (1 << budget)
            )
            if work["matching_subsets_examined"] > subset_cap:
                raise ValueError("max_inner_matching_subsets")
            if (
                work["wall_seconds"]
                > p["resource_limits"]["fixed_set_cross_evaluation"][
                    "total_time_seconds"
                ]
            ):
                raise ValueError("cross_evaluation_deadline")
        except (KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
            errors.append(f"cross_evaluation_contract_invalid:{exc}")
    if errors:
        write_json(
            directory / "failure.json",
            {
                "format": "ess-issue87-greedy-failure-v1",
                "case_id": case_id,
                "failure_reasons": errors,
                "systemd_returncode": invoked.get("returncode"),
                "systemd_status": invoked.get("systemd_status"),
                "response_file": "response.json" if raw else None,
                "stderr_file": "stderr.txt",
            },
        )
        return response, invoked, ";".join(errors)
    write_json(
        directory / "result.json",
        {
            "response_sha256": sha256_bytes(raw),
            "cross_evaluation": response,
            "systemd_status": invoked["systemd_status"],
            "wall_seconds": invoked["time_report"]["wall_seconds"],
            "peak_rss_bytes": invoked["time_report"]["peak_rss_bytes"],
        },
    )
    return response, invoked, None


def _unstarted_contrast(dataset: str, budget: int, p: dict[str, Any]) -> dict[str, Any]:
    record = contrast_record(
        dataset, budget, p, None, None, None, "not_started_after_prior_failure"
    )
    return record


def run(
    repo: Path,
    run_id: str,
    runtime_parent: Path | None = None,
) -> int:
    p = protocol()
    require_execution_authorized(p)
    run_commit = verify_source_checkout(repo, p)
    environment = verify_run_environment(p)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id):
        raise ValueError(
            "run-id must contain 1-64 letters, digits, dots, underscores or hyphens"
        )
    runtime_parent = runtime_parent or Path(os.environ["ESS_RUNTIME_PARENT"])
    run_root = runtime_parent.resolve() / "ess-research" / "issue87" / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    metadata = {
        "format": "ess-issue87-greedy-run-v1",
        "status": "STARTED",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "run_source_commit": run_commit,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "adapter_sha256": sha256_file(ADAPTER_PATH),
        "advisor": environment,
        "host": {
            "hostname": platform.node(),
            "cpu_model": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo")
                    .read_text(encoding="utf-8", errors="replace")
                    .splitlines()
                    if line.lower().startswith("model name") and ":" in line
                ),
                None,
            ),
            "logical_cpu_count": os.cpu_count(),
            "cpu_affinity": sorted(os.sched_getaffinity(0))
            if hasattr(os, "sched_getaffinity")
            else None,
        },
        "resource_limits": p["resource_limits"],
        "case_order": case_plan(p),
        "execution_authorized": p["execution_authorized"],
    }
    write_json(run_root / "run-metadata.json", metadata)
    cases = case_plan(p)
    attempted = 0
    failure_reason: str | None = None
    case_index = 0
    while case_index < len(cases):
        first = cases[case_index]
        dataset, budget = first["dataset"], first["budget"]
        current_pair: dict[str, dict[str, Any]] = {}
        nominal_request_path: Path | None = None
        for offset, objective in enumerate(("nominal", "pess")):
            case = cases[case_index + offset]
            base_path = None
            if objective == "pess":
                nominal_request_path = (
                    run_root / "cases" / f"{dataset}-nominal-b0" / "request.json"
                )
                base_path = nominal_request_path
            if budget > 0 and objective == "nominal":
                base_path = (
                    run_root / "cases" / f"{dataset}-nominal-b0" / "request.json"
                )
            record, request_path = _case_attempt(
                repo, run_root, run_id, case, base_path, run_commit, p
            )
            attempted += 1
            current_pair[objective] = record
            if record["status"] == "COMPLETE" and objective == "nominal":
                nominal_request_path = request_path
            if record["status"] != "COMPLETE":
                failure_reason = record["termination_reason"]
                append_jsonl(
                    run_root / "contrasts.jsonl",
                    contrast_record(
                        dataset,
                        budget,
                        p,
                        current_pair.get("nominal"),
                        current_pair.get("pess"),
                        None,
                        failure_reason,
                    ),
                )
                case_index += offset + 1
                break
        if failure_reason:
            break
        nominal_record = current_pair["nominal"]
        pess_record = current_pair["pess"]
        cross, _, cross_error = _cross_attempt(
            repo,
            run_root,
            run_id,
            dataset,
            budget,
            nominal_request_path,
            run_root / "cases" / nominal_record["case_id"] / "result.json",
            run_root / "cases" / pess_record["case_id"] / "result.json",
            p,
        )
        contrast = contrast_record(
            dataset,
            budget,
            p,
            nominal_record,
            pess_record,
            cross,
            cross_error,
        )
        append_jsonl(run_root / "contrasts.jsonl", contrast)
        if cross_error:
            failure_reason = cross_error
            case_index += 2
            break
        case_index += 2

    unstarted = cases[case_index:]
    if failure_reason:
        for case in unstarted:
            record = unstarted_case_record(case, p, run_commit)
            append_jsonl(run_root / "case-results.jsonl", record)
        completed_pairs = {
            (item["dataset"], item["budget"]) for item in case_plan(p)[:case_index]
        }
        for dataset in p["scope"]["datasets"]:
            for budget in p["scope"]["budget_sequence"]:
                pair = (dataset, budget)
                if pair not in completed_pairs:
                    append_jsonl(
                        run_root / "contrasts.jsonl",
                        _unstarted_contrast(dataset, budget, p),
                    )
    summary = {
        "format": "ess-issue87-greedy-run-summary-v1",
        "status": "STOPPED_INCOMPLETE"
        if failure_reason
        else "ALL_CASES_AND_CONTRASTS_COMPLETE",
        "attempted_cases": attempted,
        "not_started_case_ids": [case["case_id"] for case in unstarted],
        "failure_reason": failure_reason,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_root / "run-summary.json", summary)
    metadata.update(
        {
            "status": summary["status"],
            "finished_at_utc": summary["finished_at_utc"],
            "attempted_cases": attempted,
            "not_started_case_ids": summary["not_started_case_ids"],
            "failure_reason": failure_reason,
            "terminal_status_source": "run-summary.json",
        }
    )
    write_json(run_root / "run-metadata.json", metadata)
    return 2 if failure_reason else 0


def _worker_case(args: argparse.Namespace) -> int:
    require_execution_authorized()
    if os.environ.get(SCOPE_ENV) != "1":
        raise RuntimeError("case child must run inside the systemd scope")
    write_active_scope_enforcement(
        args.scope_unit, args.case_dir / "scope-enforcement.json", protocol()
    )
    if args.build_frozen_input:
        base = adapter.build_frozen_dataset_payload(
            args.repo, args.dataset, 0, "nominal"
        )
    else:
        base = read_json(args.base_request)
    request = request_for_case(base, args.budget, args.objective)
    request_path = args.case_dir / "request.json"
    write_json(request_path, request)
    os.execv(sys.executable, [sys.executable, "-m", "pess_ess.cli", str(request_path)])
    return 127


def _worker_cross(args: argparse.Namespace) -> int:
    require_execution_authorized()
    if os.environ.get(SCOPE_ENV) != "1":
        raise RuntimeError("cross-evaluation child must run inside the systemd scope")
    write_active_scope_enforcement(
        args.scope_unit, args.case_dir / "scope-enforcement.json", protocol()
    )
    request = read_json(args.request)
    nominal = read_json(args.nominal_result)
    pess = read_json(args.pess_result)
    try:
        result = adapter.reevaluate_greedy_contrast(
            request,
            nominal["selected_ids"],
            pess["selected_ids"],
        )
    except adapter.CrossEvaluationIncomplete as exc:
        result = {
            "status": "incomplete",
            "failure_reason": str(exc),
            "completed_fixed_set_evaluations": exc.completed_fixed_set_evaluations,
            "cross_evaluation_work": {
                "matching_subsets_examined": exc.matching_subsets_examined,
                "maximal_matchings_scored": exc.maximal_matchings_scored,
            },
        }
        sys.stdout.buffer.write(json_bytes(result))
        return 1
    sys.stdout.buffer.write(json_bytes(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run the frozen 20-case sequence")
    run_parser.add_argument("--repo", type=Path, default=ROOT)
    run_parser.add_argument("--run-id", required=True)
    child = subparsers.add_parser("_case", help=argparse.SUPPRESS)
    child.add_argument("--repo", type=Path, required=True)
    child.add_argument("--case-dir", type=Path, required=True)
    child.add_argument("--dataset", choices=("forest10", "census13"), required=True)
    child.add_argument("--budget", type=int, choices=(0, 2, 3, 4, 5), required=True)
    child.add_argument("--objective", choices=("nominal", "pess"), required=True)
    child.add_argument("--scope-unit", required=True)
    source = child.add_mutually_exclusive_group(required=True)
    source.add_argument("--build-frozen-input", action="store_true")
    source.add_argument("--base-request", type=Path)
    cross = subparsers.add_parser("_cross", help=argparse.SUPPRESS)
    cross.add_argument("--case-dir", type=Path, required=True)
    cross.add_argument("--request", type=Path, required=True)
    cross.add_argument("--nominal-result", type=Path, required=True)
    cross.add_argument("--pess-result", type=Path, required=True)
    cross.add_argument("--scope-unit", required=True)
    probe = subparsers.add_parser("_scope_probe", help=argparse.SUPPRESS)
    probe.add_argument("--scope-unit", required=True)
    probe.add_argument("--evidence", type=Path, required=True)
    probe.add_argument("--child", choices=("/bin/true", "/bin/false"), required=True)
    args = parser.parse_args()
    if args.command == "_case":
        return _worker_case(args)
    if args.command == "_cross":
        return _worker_cross(args)
    if args.command == "_scope_probe":
        evidence = active_scope_enforcement(args.scope_unit, protocol())
        result = subprocess.run([args.child], check=False)
        evidence["probe_child"] = args.child
        evidence["probe_child_returncode"] = result.returncode
        write_json(args.evidence, evidence)
        if not evidence.get("verified"):
            return 90
        return result.returncode
    return run(args.repo.resolve(), args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
