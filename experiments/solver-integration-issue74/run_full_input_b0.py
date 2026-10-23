"""Run one full-input B=0 solver comparison against the exact reference."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time
from fractions import Fraction
from pathlib import Path

from pess_ess import solve_payload
from pess_ess.model import instance_from_dict
from pess_ess.reference import reference_nominal_objective, reference_objective

import adapter

ADVISOR_COMMIT = "d40a57d4704345fef85298dd97192b2d998dc6eb"
SOLVER_LIMIT_SECONDS = 600


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(repo: Path, dataset: str, objective: str) -> dict:
    started = time.monotonic()
    installed_text = importlib.metadata.distribution("pess-ess").read_text("direct_url.json")
    if installed_text is None:
        raise RuntimeError("pess-ess direct_url.json missing; immutable VCS pin cannot be checked")
    installed = json.loads(installed_text)
    installed_sha = installed.get("vcs_info", {}).get("commit_id")
    if installed_sha != ADVISOR_COMMIT:
        raise RuntimeError(f"pess-ess source pin mismatch: {installed_sha}")

    loader = {"forest10": adapter.forest10_request,
              "census13": adapter.census13_request}[dataset]
    source = loader(repo, budget=0)
    source["input_provenance"]["advisor_source_commit"] = ADVISOR_COMMIT
    order = source["_nominal_priority_order"]
    payload = adapter.advisor_request_payload(
        source, objective, priority_order=order if objective == "nominal" else None)
    payload["limits"] = {"time_seconds": SOLVER_LIMIT_SECONDS,
                         "total_time_seconds": SOLVER_LIMIT_SECONDS}
    payload_bytes = canonical(payload)
    instance = instance_from_dict(source["instance"])
    # At B=0 with unit positive costs, the empty set is the sole feasible M.
    # Evaluate that M directly with the Advisor's independent exact Fraction
    # reference; its subset-enumeration wrapper visits all 2^|E| subsets even
    # when all but the empty set violate the budget.
    ref_started = time.monotonic()
    empty = frozenset()
    if objective == "nominal":
        reference_value, _ = reference_nominal_objective(instance, empty, tuple(order))
    else:
        reference_value, _ = reference_objective(instance, empty)
    reference_seconds = time.monotonic() - ref_started

    solver_started = time.monotonic()
    response = solve_payload(payload)
    solver_elapsed = time.monotonic() - solver_started
    response_bytes = canonical(response)
    selected = response["incumbent"].get("selected")
    objective_value = response["incumbent"].get(
        "witness_aggregate", response["incumbent"].get("objective_value"))
    objective_matches = (objective_value is not None and
                         Fraction(objective_value) == reference_value)
    selected_matches = (selected is not None and frozenset(selected) == empty)
    feasible = response["incumbent"].get("validated_feasible") is True
    result = {
        "format": "ess-issue74-full-input-b0-result-v1",
        "dataset": dataset,
        "objective": objective,
        "budget": 0,
        "task_count": len(instance.tasks),
        "candidate_count": len(instance.candidates),
        "advisor_source_commit": ADVISOR_COMMIT,
        "advisor_package_version": response["provenance"]["package_version"],
        "scipy_version": response["provenance"]["scipy_version"],
        "model_version": source["input_provenance"]["model_version"],
        "input_provenance": source["input_provenance"],
        "request_sha256": sha(payload_bytes),
        "response_sha256": sha(response_bytes),
        "reference_objective_fraction": str(reference_value),
        "reference_selected_sets": [[]],
        "selected": selected,
        "objective_value": objective_value,
        "exact_reference_objective_match": objective_matches,
        "selected_set_in_exact_ties": selected_matches,
        "validated_feasible": feasible,
        "advisor_status": response["status"],
        "termination_reason": response["termination_reason"],
        "solver_reported_optimal": response["optimality"]["solver_reported_optimal"],
        "solver_statuses": response["solver_statuses"],
        "objective_evidence": response["objective_evidence"],
        "solver_wall_time_seconds": response["wall_time_seconds"],
        "exact_reference_computation_seconds": reference_seconds,
        "solver_invocation_seconds": solver_elapsed,
        "elapsed_seconds_including_adapter_and_reference": time.monotonic() - started,
        "outcome": ("MATCH" if feasible and objective_matches and selected_matches
                    else "UNRESOLVED_OR_MISMATCH"),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dataset", choices=("forest10", "census13"), required=True)
    parser.add_argument("--objective", choices=("nominal", "pess"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.repo.resolve(), args.dataset, args.objective)
    except Exception as exc:
        result = {"format": "ess-issue74-full-input-b0-result-v1",
                  "dataset": args.dataset, "objective": args.objective,
                  "budget": 0, "outcome": "FAILED", "error": repr(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"outcome": result["outcome"], "output": str(args.output),
                      "dataset": args.dataset, "objective": args.objective},
                     sort_keys=True))
    if result["outcome"] != "MATCH":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
