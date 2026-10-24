"""Read-only adapter for the frozen Issue #64/#71 models and greedy backend."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from fractions import Fraction
from pathlib import Path
from time import monotonic
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE / "protocol-v1.json"
MODEL_ADAPTER_PATH = ROOT / "experiments/solver-integration-issue74/adapter.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _protocol() -> dict[str, Any]:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _candidate_order_sha256(candidate_ids: list[str]) -> str:
    payload = json.dumps(candidate_ids, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class CrossEvaluationIncomplete(RuntimeError):
    """A fixed-set comparison stopped before all exact Fraction values existed."""

    def __init__(self, reason: str, completed_calls: int, work: Any) -> None:
        super().__init__(reason)
        self.completed_fixed_set_evaluations = completed_calls
        self.matching_subsets_examined = work.matching_subsets_examined
        self.maximal_matchings_scored = work.maximal_matchings_scored


def resource_caps(candidate_count: int, task_count: int, budget: int) -> dict[str, int]:
    """Return the protocol's outcome-independent caps for unit-cost candidates."""
    if candidate_count < 1 or task_count < 1 or budget < 0:
        raise ValueError("invalid dimensions or budget for the greedy cap formula")
    rounds = min(budget, candidate_count)
    max_evaluations = 1 + sum(
        candidate_count - additions for additions in range(rounds)
    )
    max_matching_subsets = task_count * (
        1
        + sum(
            (candidate_count - additions) * (1 << (additions + 1))
            for additions in range(rounds)
        )
    )
    candidate_attempts = sum(
        candidate_count - additions for additions in range(rounds + 1)
    )
    return {
        "max_evaluations": max_evaluations,
        "max_inner_matching_subsets": max_matching_subsets,
        "candidate_attempts_upper_bound": candidate_attempts,
    }


def adapt_request(base_request: dict[str, Any], objective: str) -> dict[str, Any]:
    """Add the pinned backend and derived limits to an existing model request.

    ``base_request`` is returned by the frozen Issue #74 model adapter. This
    function changes no model coefficients, candidate IDs, order, task weights,
    or costs. It never invokes the Advisor solver.
    """
    if objective not in {"nominal", "pess"}:
        raise ValueError("objective must be 'nominal' or 'pess'")
    if (
        sha256(MODEL_ADAPTER_PATH)
        != _protocol()["immutable_software"]["existing_model_adapter_sha256"]
    ):
        raise ValueError("frozen model adapter source SHA-256 mismatch")
    adapter_sha = sha256(Path(__file__))
    expected_adapter_sha = _protocol()["immutable_software"][
        "new_issue87_adapter_sha256"
    ]
    if adapter_sha != expected_adapter_sha:
        raise ValueError("Issue #87 adapter source SHA-256 mismatch")

    instance = base_request.get("instance")
    if not isinstance(instance, dict):
        raise ValueError("base request is missing an instance")
    candidates = instance.get("candidates")
    tasks = instance.get("tasks")
    if not isinstance(candidates, list) or not isinstance(tasks, list):
        raise ValueError("base request has malformed candidate or task lists")
    candidate_ids = [candidate.get("id") for candidate in candidates]
    if any(not isinstance(candidate_id, str) for candidate_id in candidate_ids):
        raise ValueError("base request has a malformed candidate ID")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("base request has duplicate candidate IDs")
    if any(Fraction(candidate["maintenance_cost"]) != 1 for candidate in candidates):
        raise ValueError("frozen experiment requires verified unit candidate costs")

    budget_fraction = Fraction(instance.get("budget", "-1"))
    if budget_fraction.denominator != 1:
        raise ValueError("budget must be an integer in the frozen unit-cost sequence")
    budget = int(budget_fraction)
    if budget not in _protocol()["scope"]["budget_sequence"]:
        raise ValueError("budget is outside the frozen Issue #87 sequence")
    caps = resource_caps(len(candidates), len(tasks), budget)

    payload = {
        key: value for key, value in base_request.items() if not key.startswith("_")
    }
    payload["schema_version"] = "1"
    payload["objective"] = objective
    payload["backend"] = "add_only_greedy"
    limits = {
        "total_time_seconds": _protocol()["resource_limits"][
            "advisor_total_time_seconds"
        ],
        "max_evaluations": caps["max_evaluations"],
    }
    if objective == "pess":
        limits["max_inner_matching_subsets"] = caps["max_inner_matching_subsets"]
    payload["limits"] = limits

    if objective == "nominal":
        priority = base_request.get("priority_order") or base_request.get(
            "_nominal_priority_order"
        )
        if not isinstance(priority, list) or len(priority) != len(candidate_ids):
            raise ValueError(
                "Nominal requires the complete frozen global priority order"
            )
        if len(set(priority)) != len(priority) or set(priority) != set(candidate_ids):
            raise ValueError(
                "Nominal priority order does not match the full candidate set"
            )
        payload["priority_order"] = priority
    else:
        payload.pop("priority_order", None)

    provenance = payload.get("input_provenance")
    if not isinstance(provenance, dict):
        raise ValueError("base request is missing input provenance")
    provenance["advisor_source_commit"] = _protocol()["immutable_software"][
        "advisor_source_commit"
    ]
    provenance["issue87_protocol_sha256"] = sha256(PROTOCOL_PATH)
    provenance["issue87_adapter_source_sha256"] = adapter_sha
    provenance["frozen_model_adapter_sha256"] = sha256(MODEL_ADAPTER_PATH)
    provenance["candidate_order_sha256"] = _candidate_order_sha256(candidate_ids)
    provenance["max_evaluations"] = caps["max_evaluations"]
    if objective == "pess":
        provenance["max_inner_matching_subsets"] = caps["max_inner_matching_subsets"]
    return payload


def _load_frozen_model_adapter():
    expected_sha = _protocol()["immutable_software"]["existing_model_adapter_sha256"]
    if sha256(MODEL_ADAPTER_PATH) != expected_sha:
        raise ValueError("frozen model adapter source SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location(
        "ess_research_issue74_frozen_model_adapter", MODEL_ADAPTER_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load the frozen Issue #74 model adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reevaluate_greedy_contrast(
    base_request: dict[str, Any],
    nominal_selected_ids: list[str],
    pess_selected_ids: list[str],
) -> dict[str, Any]:
    """Exactly score the two completed selected sets under both objectives."""
    from pess_ess.model import instance_from_dict
    from pess_ess.reference import (
        ReferenceEvaluationIncomplete,
        ReferenceWork,
        reference_nominal_objective,
        reference_objective,
    )

    instance = instance_from_dict(base_request["instance"])
    if any(candidate.maintenance_cost != 1 for candidate in instance.candidates):
        raise ValueError("cross-evaluation requires the frozen unit-cost candidates")
    nominal_order = base_request.get("priority_order") or base_request.get(
        "_nominal_priority_order"
    )
    if (
        not isinstance(nominal_order, list)
        or set(nominal_order) != set(instance.candidate_ids)
        or len(nominal_order) != len(instance.candidate_ids)
    ):
        raise ValueError("cross-evaluation requires the complete frozen Nominal order")
    selected_sets = {
        "nominal": frozenset(nominal_selected_ids),
        "pess": frozenset(pess_selected_ids),
    }
    for name, selected in selected_sets.items():
        source_ids = nominal_selected_ids if name == "nominal" else pess_selected_ids
        if len(selected) != len(source_ids):
            raise ValueError(f"{name} selection contains duplicate candidate IDs")
        if instance.maintenance_cost(selected) > instance.budget:
            raise ValueError(f"{name} selection exceeds the frozen budget")

    budget = Fraction(base_request["instance"]["budget"])
    if budget.denominator != 1:
        raise ValueError("cross-evaluation budget must be an integer")
    max_subsets = 2 * len(instance.tasks) * (1 << int(budget))
    time_limit = _protocol()["resource_limits"]["fixed_set_cross_evaluation"][
        "total_time_seconds"
    ]
    started = monotonic()
    deadline = started + time_limit
    work = ReferenceWork()
    completed_calls = 0
    values: dict[str, str] = {}
    try:
        for set_name, selected in selected_sets.items():
            nominal_value, _ = reference_nominal_objective(
                instance, selected, tuple(nominal_order), deadline=deadline
            )
            completed_calls += 1
            values[f"nominal_objective_on_{set_name}_set_fraction"] = str(nominal_value)

            required_subsets = sum(
                1 << len(set(task.eligible_candidates) & selected)
                for task in instance.tasks
            )
            if work.matching_subsets_examined + required_subsets > max_subsets:
                raise CrossEvaluationIncomplete(
                    "max_inner_matching_subsets", completed_calls, work
                )
            pess_value, _ = reference_objective(
                instance, selected, deadline=deadline, work=work
            )
            completed_calls += 1
            values[f"pess_objective_on_{set_name}_set_fraction"] = str(pess_value)
    except ReferenceEvaluationIncomplete as exc:
        raise CrossEvaluationIncomplete(str(exc), completed_calls, work) from exc

    if work.matching_subsets_examined > max_subsets:
        raise CrossEvaluationIncomplete(
            "max_inner_matching_subsets", completed_calls, work
        )
    return {
        **values,
        "cross_evaluation_work": {
            "fixed_set_evaluation_calls": completed_calls,
            "matching_subsets_examined": work.matching_subsets_examined,
            "maximal_matchings_scored": work.maximal_matchings_scored,
            "wall_seconds": max(0.0, monotonic() - started),
        },
    }


def build_frozen_dataset_payload(
    repo_root: Path, dataset: str, budget: int, objective: str
) -> dict[str, Any]:
    """Build, hash-check and adapt one full valid-only request; do not solve it."""
    protocol = _protocol()
    if dataset not in protocol["frozen_inputs"]:
        raise ValueError("dataset is outside the frozen Issue #87 universe")
    if budget not in protocol["scope"]["budget_sequence"]:
        raise ValueError("budget is outside the frozen Issue #87 sequence")
    frozen = protocol["frozen_inputs"][dataset]
    model_adapter = _load_frozen_model_adapter()
    builder = (
        model_adapter.forest10_request
        if dataset == "forest10"
        else model_adapter.census13_request
    )
    request = builder(repo_root, budget)
    expected_model = frozen["model_version"]
    provenance = request["input_provenance"]
    if provenance.get("model_version") != expected_model:
        raise ValueError("frozen model version mismatch")
    if provenance.get("model_source_commit") != frozen["model_source_commit"]:
        raise ValueError("frozen model source commit mismatch")
    if (
        provenance.get("arecel_archive_sha256")
        != protocol["frozen_inputs"]["archive_sha256"]
    ):
        raise ValueError("AreCEL archive SHA-256 mismatch")
    if provenance.get("frozen_reference_sha256") != frozen["frozen_selection_sha256"]:
        raise ValueError("frozen selection artifact SHA-256 mismatch")
    expected_coefficient = frozen.get(
        "coefficient_artifact_sha256", frozen.get("coefficient_digest_sha256")
    )
    observed_coefficient = provenance.get(
        "coefficient_artifact_sha256", provenance.get("coefficient_sha256")
    )
    if observed_coefficient != expected_coefficient:
        raise ValueError("frozen coefficient input SHA-256 mismatch")
    expected_truth = frozen.get(
        "valid_truth_sha256", frozen.get("valid_truth_values_sha256")
    )
    observed_truth = provenance.get(
        "valid_truth_sha256", provenance.get("valid_truth_values_sha256")
    )
    if observed_truth != expected_truth:
        raise ValueError("frozen valid-truth SHA-256 mismatch")
    if dataset == "census13":
        expected_observations = dict(
            zip(("worker0", "worker1"), frozen["valid_observation_sha256"])
        )
        if provenance.get("observation_sha256") != expected_observations:
            raise ValueError("frozen Census13 observation hashes mismatch")
        if provenance.get("plan_sha256") != frozen["plan_sha256"]:
            raise ValueError("frozen Census13 plan SHA-256 mismatch")

    instance = request["instance"]
    candidate_ids = [candidate["id"] for candidate in instance["candidates"]]
    if len(candidate_ids) != frozen["candidate_count"]:
        raise ValueError("candidate count differs from the complete frozen universe")
    if len(instance["tasks"]) != frozen["valid_task_count"]:
        raise ValueError("full 10000-task valid workload is required")
    if _candidate_order_sha256(candidate_ids) != frozen["candidate_order_sha256"]:
        raise ValueError("candidate order differs from the frozen order hash")
    if (
        _candidate_order_sha256(request["_nominal_priority_order"])
        != frozen["candidate_order_sha256"]
    ):
        raise ValueError(
            "Nominal global priority differs from the frozen priority hash"
        )
    if any(
        candidate["maintenance_cost"] != "1" for candidate in instance["candidates"]
    ):
        raise ValueError("frozen instance does not have verified unit costs")
    if any(task["weight"] != "1" for task in instance["tasks"]):
        raise ValueError("task weights differ from the frozen all-ones weights")
    if request["instance"]["budget"] != str(budget):
        raise ValueError("request budget differs from the selected protocol case")

    adapted = adapt_request(request, objective)
    adapted["input_provenance"]["issue87_dataset"] = dataset
    adapted["input_provenance"]["issue87_model_source_commit"] = frozen[
        "model_source_commit"
    ]
    adapted["input_provenance"]["issue87_valid_task_count"] = frozen["valid_task_count"]
    adapted["input_provenance"]["issue87_candidate_count"] = frozen["candidate_count"]
    adapted["input_provenance"]["issue87_run_source_commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return adapted
