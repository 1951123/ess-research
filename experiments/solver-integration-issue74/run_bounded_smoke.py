"""Run a tiny, explicitly truncated advisor integration smoke against frozen inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

from pess_ess import solve_payload
from pess_ess.model import instance_from_dict
from pess_ess.reference import solve_exhaustive, solve_nominal_exhaustive

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(repo: Path, output: Path, task_limit: int, candidate_limit: int) -> dict:
    results = []
    for dataset, loader in (("forest10", adapter.forest10_request),
                            ("census13", adapter.census13_request)):
        source = loader(repo, budget=0, task_limit=task_limit)
        candidate_ids = source["_candidate_ids"][:candidate_limit]
        order = [e for e in source["_nominal_priority_order"] if e in set(candidate_ids)]
        source["instance"]["candidates"] = [c for c in source["instance"]["candidates"]
                                              if c["id"] in set(candidate_ids)]
        for task in source["instance"]["tasks"]:
            task["corrections"] = {k: v for k, v in task["corrections"].items()
                                    if k in set(candidate_ids)}
            task["eligible_candidates"] = [k for k in task["eligible_candidates"]
                                            if k in set(candidate_ids)]
        source["_nominal_priority_order"] = order
        for budget in (0, 2, 3):
            source["instance"]["budget"] = str(budget)
            instance = instance_from_dict(source["instance"])
            for objective in ("nominal", "pess"):
                payload = adapter.advisor_request_payload(source, objective,
                    priority_order=order if objective == "nominal" else None)
                payload["limits"] = ({"time_seconds": 5, "inner_time_seconds": 2,
                                      "total_time_seconds": 8} if objective == "pess" else
                                     {"time_seconds": 5, "total_time_seconds": 8})
                raw_request = canonical(payload)
                response = solve_payload(payload)
                raw_response = canonical(response)
                if not response["incumbent"]["validated_feasible"]:
                    raise RuntimeError(f"{dataset}/{objective}/B{budget}: no validated feasible result")
                selected = frozenset(response["incumbent"]["selected"])
                reference = (solve_nominal_exhaustive(instance, tuple(order))
                             if objective == "nominal" else solve_exhaustive(instance))
                if selected not in reference.optimal_sets:
                    raise AssertionError(f"{dataset}/{objective}/B{budget}: selected set is outside exact ties")
                advisor_objective = response["incumbent"].get(
                    "witness_aggregate", response["incumbent"].get("objective_value"))
                objective_matches = (advisor_objective is not None and
                                     Fraction(advisor_objective) == reference.objective)
                if not objective_matches:
                    raise AssertionError(f"{dataset}/{objective}/B{budget}: objective differs from exact reference")
                results.append({
                    "dataset": dataset, "objective": objective, "budget": budget,
                    "tasks": len(instance.tasks), "candidate_count": len(instance.candidates),
                    "reference_selected_sets": [sorted(s) for s in reference.optimal_sets],
                    "advisor_selected": sorted(selected),
                    "reference_objective_fraction": str(reference.objective),
                    "advisor_objective": advisor_objective,
                    "objective_matches_reference": objective_matches,
                    "advisor_status": response["status"],
                    "solver_reported_optimal": response["optimality"]["solver_reported_optimal"],
                    "selected_pess_value_fraction_certified": response["objective_evidence"].get(
                        "selected_pess_value_fraction_certified"),
                    "request_sha256": sha(raw_request),
                    "response_sha256": sha(raw_response),
                    "response": response,
                })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"format": "ess-issue74-bounded-smoke-v1", "results": results},
                                 indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"format": "ess-issue74-bounded-smoke-v1", "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-limit", type=int, default=12)
    parser.add_argument("--candidate-limit", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.task_limit <= 12 or not 1 <= args.candidate_limit <= 8:
        parser.error("the committed smoke is bounded to at most 12 tasks and 8 candidates")
    result = run(args.repo.resolve(), args.output.resolve(), args.task_limit, args.candidate_limit)
    print(json.dumps({"status": "PASS", "records": len(result["results"]),
                      "output": str(args.output.resolve())}, sort_keys=True))


if __name__ == "__main__":
    main()
