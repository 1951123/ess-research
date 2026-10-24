"""Explain the frozen Issue #87 Nominal/PESS gaps by exact valid-task witnesses."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from time import monotonic
from typing import Any

from pess_ess.matchings import is_maximal
from pess_ess.model import Instance, Task, instance_from_dict
from pess_ess.reference import (
    ReferenceWork,
    reference_nominal_task_loss,
    reference_task_loss,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
V4 = "issue87-valid-only-20261024-v4"
V4_SOURCE = "386658d7b3895a57bd138b24611672d329edaeda"
ADVISOR = "5d61f75fede37d34027b437c646000a3d78d00c6"
PROTOCOL_SHA = "ef095a12dd1a1ac676acd822e24d93e369b61cbd56297ced87b6771111f07623"
EVIDENCE = HERE / "runs" / V4
MANIFEST_PATH = EVIDENCE / "evidence-sha256.json"
MODELS = {
    "forest10": ("forest10-positive-preclamp-v1", 45),
    "census13": ("census13-clamped-log-v2", 78),
}


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    nominal: Fraction
    pess: Fraction
    risk: Fraction
    nominal_matching: frozenset[str]
    pess_matching: frozenset[str]
    conflicts: tuple[tuple[str, str], ...]
    endpoints: dict[str, tuple[str, str]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def task_result(
    instance: Instance,
    task: Task,
    selected: frozenset[str],
    priority: tuple[str, ...],
    work: ReferenceWork,
) -> TaskResult:
    candidates = instance.candidate_map
    eligible = frozenset(task.eligible_candidates) & selected
    endpoints = {
        resource: candidates[resource].endpoints
        for resource in task.eligible_candidates
    }
    nominal, nominal_matching = reference_nominal_task_loss(
        instance, task, selected, priority
    )
    pess, pess_matching = reference_task_loss(instance, task, selected, work=work)
    if not is_maximal(nominal_matching, eligible, endpoints):
        raise AssertionError(f"Nominal matching is not maximal: {task.id}")
    if not is_maximal(pess_matching, eligible, endpoints):
        raise AssertionError(f"PESS witness is not maximal: {task.id}")
    conflicts = tuple(
        (left, right)
        for left, right in combinations(sorted(eligible), 2)
        if set(endpoints[left]) & set(endpoints[right])
    )
    risk = pess - nominal
    if risk < 0 or (risk > 0 and not conflicts):
        raise AssertionError(f"invalid task-wise PESS risk: {task.id}")
    return TaskResult(
        task.id,
        nominal,
        pess,
        risk,
        nominal_matching,
        pess_matching,
        conflicts,
        {resource: endpoints[resource] for resource in sorted(eligible)},
    )


def analyze_instance(
    instance: Instance,
    selected: frozenset[str],
    priority: tuple[str, ...],
    nominal_total: Fraction,
    pess_total: Fraction,
) -> dict[str, Any]:
    if any(task.weight != 1 for task in instance.tasks):
        raise ValueError("the frozen Issue #87 task weights must all equal one")
    work = ReferenceWork()
    rows = [
        task_result(instance, task, selected, priority, work) for task in instance.tasks
    ]
    nominal_sum = sum((row.nominal for row in rows), Fraction())
    pess_sum = sum((row.pess for row in rows), Fraction())
    risk_sum = sum((row.risk for row in rows), Fraction())
    if (nominal_sum, pess_sum, risk_sum) != (
        nominal_total,
        pess_total,
        pess_total - nominal_total,
    ):
        raise AssertionError("task sums differ from the exact v4 cross-evaluation")

    positive = sorted(
        (row for row in rows if row.risk > 0), key=lambda row: (-row.risk, row.task_id)
    )
    conflict_count = sum(bool(row.conflicts) for row in rows)
    if any(row.risk for row in rows if not row.conflicts):
        raise AssertionError("nonconflicting tasks must have zero PESS risk")

    def top(k: int) -> dict[str, Any]:
        contribution = sum((row.risk for row in positive[:k]), Fraction())
        return {
            "task_count": min(k, len(positive)),
            "risk_sum_fraction": str(contribution),
            "share_of_total_risk_fraction": str(contribution / risk_sum)
            if risk_sum
            else None,
        }

    def witness(row: TaskResult) -> dict[str, Any]:
        return {
            "task_id": row.task_id,
            "nominal_matching_ids": sorted(row.nominal_matching),
            "pess_worst_matching_ids": sorted(row.pess_matching),
            "nominal_loss_fraction": str(row.nominal),
            "pess_loss_fraction": str(row.pess),
            "risk_fraction": str(row.risk),
            "selected_edge_endpoints": {
                key: list(value) for key, value in row.endpoints.items()
            },
            "endpoint_conflict_pairs": [list(pair) for pair in row.conflicts],
        }

    return {
        "task_count": len(rows),
        "nominal_loss_sum_fraction": str(nominal_sum),
        "pess_loss_sum_fraction": str(pess_sum),
        "summed_task_risk_fraction": str(risk_sum),
        "positive_risk_task_count": len(positive),
        "tasks_with_applicable_endpoint_conflict_count": conflict_count,
        "positive_risk_without_conflict_count": 0,
        "zero_risk_with_conflict_count": sum(
            row.risk == 0 and bool(row.conflicts) for row in rows
        ),
        "zero_risk_without_conflict_count": len(rows) - conflict_count,
        "top_10_positive_risk": top(10),
        "top_100_positive_risk": top(100),
        "largest_risk_witnesses": [witness(row) for row in positive[:3]],
        "reference_work": {
            "fixed_set_task_evaluations": len(rows),
            "matching_subsets_examined": work.matching_subsets_examined,
            "maximal_matchings_scored": work.maximal_matchings_scored,
        },
    }


def analyze_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest = read_json(MANIFEST_PATH)
    if (
        run_dir.name != V4
        or Path(manifest["runtime_root"]).resolve() != run_dir
        or manifest["run_id"] != V4
        or manifest["run_source_commit"] != V4_SOURCE
        or manifest["protocol_sha256"] != PROTOCOL_SHA
    ):
        raise ValueError("run path or frozen v4 evidence pin differs")

    metadata = read_json(run_dir / "run-metadata.json")
    terminal = read_json(run_dir / "run-summary.json")
    if (
        sha256_file(HERE / "protocol-v1.json") != PROTOCOL_SHA
        or metadata.get("status") != "ALL_CASES_AND_CONTRASTS_COMPLETE"
        or metadata.get("attempted_cases") != 20
        or metadata.get("run_source_commit") != V4_SOURCE
        or metadata.get("advisor", {}).get("advisor_source_commit") != ADVISOR
        or terminal.get("status") != "ALL_CASES_AND_CONTRASTS_COMPLETE"
        or terminal.get("not_started_case_ids") != []
    ):
        raise ValueError("v4 run is incomplete or does not match its frozen pins")

    hashes = manifest["files"]
    for name in ("run-metadata.json", "run-summary.json", "contrasts.jsonl"):
        if sha256_file(run_dir / name) != hashes[name]:
            raise ValueError(f"v4 evidence hash mismatch: {name}")
    contrasts = {}
    for line in (run_dir / "contrasts.jsonl").read_text().splitlines():
        row = json.loads(line)
        key = (row["dataset"], row["budget"])
        if key in contrasts:
            raise ValueError(f"duplicate v4 contrast: {key}")
        contrasts[key] = row

    advisor_url = importlib.metadata.distribution("pess-ess").read_text(
        "direct_url.json"
    )
    advisor_commit = (
        json.loads(advisor_url or "{}").get("vcs_info", {}).get("commit_id")
    )
    if advisor_commit != ADVISOR:
        raise ValueError("installed Advisor differs from the frozen Issue #87 commit")

    started = monotonic()
    results = []
    for dataset, (model, candidate_count) in MODELS.items():
        for budget in (4, 5):
            case = f"{dataset}-nominal-b{budget}"
            base = run_dir / "cases" / case
            paths = {
                name: base / f"{name}.json"
                for name in ("request", "response", "result")
            }
            for name, path in paths.items():
                if sha256_file(path) != hashes[f"cases/{case}/{name}.json"]:
                    raise ValueError(f"v4 raw case hash mismatch: {case}/{name}.json")
            request, response, result = (read_json(paths[name]) for name in paths)
            provenance = request.get("input_provenance", {})
            data = request["instance"]
            if (
                result.get("status") != "COMPLETE"
                or result.get("process_exit_status") != 0
                or result.get("request_sha256") != sha256_file(paths["request"])
                or result.get("response_sha256") != sha256_file(paths["response"])
                or response.get("status") != "heuristic_completed"
                or response.get("objective") != "nominal"
                or response.get("incumbent", {}).get("selected")
                != result["selected_ids"]
                or response.get("incumbent", {}).get("objective_value")
                != result["objective_fraction"]
                or result.get("dataset") != dataset
                or result.get("budget") != budget
                or result.get("objective") != "nominal"
                or result.get("model_version") != model
                or result.get("candidate_count") != candidate_count
                or result.get("task_count") != 10_000
                or result.get("issue87_run_source_commit") != V4_SOURCE
                or result.get("advisor_source_commit") != ADVISOR
                or result.get("outer_global_optimum_claim") is not False
                or request.get("backend") != "add_only_greedy"
                or request.get("objective") != "nominal"
                or Fraction(data["budget"]) != budget
                or len(data["tasks"]) != 10_000
                or len(data["candidates"]) != candidate_count
                or provenance.get("model_version") != model
                or provenance.get("advisor_source_commit") != ADVISOR
                or provenance.get("issue87_run_source_commit") != V4_SOURCE
                or provenance.get("issue87_dataset") != dataset
                or provenance.get("issue87_valid_task_count") != 10_000
            ):
                raise ValueError(
                    f"v4 case does not match frozen full-valid input: {case}"
                )

            cross = contrasts[(dataset, budget)]
            if (
                cross.get("status") != "COMPLETE"
                or cross.get("model_version") != model
                or cross.get("nominal_selected_ids") != result["selected_ids"]
            ):
                raise ValueError(f"v4 cross-evaluation missing or inconsistent: {case}")
            priority = tuple(request["priority_order"])
            priority_hash = hashlib.sha256(
                json.dumps(list(priority), separators=(",", ":")).encode()
            ).hexdigest()
            if result.get("nominal_priority_order_sha256") != priority_hash:
                raise ValueError(f"Nominal priority hash mismatch: {case}")
            nominal = Fraction(cross["nominal_objective_on_nominal_set_fraction"])
            pess = Fraction(cross["pess_objective_on_nominal_set_fraction"])
            instance = instance_from_dict(data)
            if set(priority) != set(instance.candidate_ids):
                raise ValueError(f"Nominal priority order is incomplete: {case}")
            analysis = analyze_instance(
                instance, frozenset(result["selected_ids"]), priority, nominal, pess
            )
            results.append(
                {
                    "dataset": dataset,
                    "budget": budget,
                    "model_version": model,
                    "selected_nominal_ids": sorted(result["selected_ids"]),
                    "request_sha256": result["request_sha256"],
                    "response_sha256": result["response_sha256"],
                    "nominal_cross_objective_fraction": str(nominal),
                    "pess_cross_objective_on_nominal_set_fraction": str(pess),
                    **analysis,
                }
            )

    return {
        "format": "issue95-task-matching-attribution-v1",
        "claim_scope": "fixed-set model-internal, valid-only; greedy selections",
        "issue87_run_id": V4,
        "issue87_source_commit": V4_SOURCE,
        "advisor_source_commit": ADVISOR,
        "protocol_sha256": PROTOCOL_SHA,
        "v4_manifest_sha256": sha256_file(MANIFEST_PATH),
        "analysis_source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "analysis_script_sha256": sha256_file(Path(__file__).resolve()),
        "command": sys.argv,
        "environment": {
            "python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "networkx": importlib.metadata.version("networkx"),
            "pess_ess": importlib.metadata.version("pess-ess"),
            "pess_ess_commit": advisor_commit,
        },
        "analysis_wall_seconds": round(monotonic() - started, 6),
        "solver_runs": 0,
        "contrasts": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(analyze_run(args.run_dir), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
