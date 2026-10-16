"""Run the first fixed-seed synthetic PESS-ESS comparison."""

from __future__ import annotations

import json
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path

import networkx
import numpy
import scipy

from pess_ess.generate import generate_instance
from pess_ess.matchings import enumerate_matchings
from pess_ess.model import Instance, fraction_to_json, write_instance
from pess_ess.reference import solve_exhaustive
from pess_ess.solvers import OuterResult, solve_master_oracle, solve_static


ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = ROOT / "instances"
RESULT_DIR = ROOT / "results"
RESULT_PATH = RESULT_DIR / "suite-results.json"
REPORT_PATH = ROOT / "report.md"


CONFIGS = (
    {
        "instance_id": "tiny_mixed",
        "seed": 101,
        "candidate_count": 5,
        "task_count": 3,
        "attribute_count": 4,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": True,
    },
    {
        "instance_id": "small_shared",
        "seed": 202,
        "candidate_count": 7,
        "task_count": 4,
        "attribute_count": 5,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": True,
    },
    {
        "instance_id": "parallel_zero_cost",
        "seed": 303,
        "candidate_count": 8,
        "task_count": 4,
        "attribute_count": 4,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": True,
        "tight_budget": False,
        "exhaustive": True,
    },
    {
        "instance_id": "positive_sign",
        "seed": 404,
        "candidate_count": 8,
        "task_count": 4,
        "attribute_count": 5,
        "mixed_sign": False,
        "sign_mode": "positive",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": True,
    },
    {
        "instance_id": "medium_dense",
        "seed": 505,
        "candidate_count": 12,
        "task_count": 6,
        "attribute_count": 5,
        "mixed_sign": True,
        "sign_mode": "mixed",
        "zero_cost": False,
        "tight_budget": True,
        "exhaustive": False,
    },
)


def _fraction(value: Fraction | None) -> str | None:
    return fraction_to_json(value) if value is not None else None


def _solver_statuses(result: OuterResult) -> list[dict[str, object]]:
    return [
        {
            "status": item.status,
            "message": item.message,
            "objective": item.objective,
            "mip_gap": item.mip_gap,
            "mip_node_count": item.mip_node_count,
        }
        for item in result.solver_statuses
    ]


def _outer_record(
    instance_id: str,
    solver: str,
    result: OuterResult,
    elapsed: float,
) -> dict[str, object]:
    return {
        "kind": "solver",
        "instance_id": instance_id,
        "solver": solver,
        "status": result.status,
        "termination_reason": result.termination_reason,
        "selected": sorted(result.selected) if result.selected is not None else None,
        "maintenance_cost": _fraction(result.maintenance_cost),
        "objective": _fraction(result.objective),
        "lower_bound": result.lower_bound,
        "upper_bound": result.upper_bound,
        "master_iterations": result.master_iterations,
        "distinct_cuts": result.distinct_cuts,
        "inner_oracle_calls": result.inner_oracle_calls,
        "certified_early_exits": result.certified_early_exits,
        "scenario_count": result.scenario_count,
        "runtime_seconds": elapsed,
        "solver_statuses": _solver_statuses(result),
        "task_details": {
            task_id: {
                "loss": _fraction(loss),
                "witness": sorted(witness),
            }
            for task_id, (loss, witness) in sorted(result.task_details.items())
        },
    }


def _reference_record(instance_id: str, instance: Instance, elapsed: float) -> dict[str, object]:
    result = solve_exhaustive(instance)
    return {
        "kind": "solver",
        "instance_id": instance_id,
        "solver": "exhaustive_reference",
        "status": "optimal",
        "termination_reason": "complete finite enumeration",
        "selected": [sorted(item) for item in result.optimal_sets],
        "maintenance_cost": None,
        "objective": _fraction(result.objective),
        "lower_bound": float(result.objective),
        "upper_bound": float(result.objective),
        "master_iterations": 0,
        "distinct_cuts": 0,
        "inner_oracle_calls": 0,
        "certified_early_exits": 0,
        "scenario_count": None,
        "runtime_seconds": elapsed,
        "evaluated_subsets": result.evaluated_subsets,
        "feasible_subsets": result.feasible_subsets,
    }


def _task_graph_stats(instance: Instance) -> list[dict[str, object]]:
    candidate_map = instance.candidate_map
    rows = []
    for task in instance.tasks:
        endpoints = {
            candidate_id: candidate_map[candidate_id].endpoints
            for candidate_id in task.eligible_candidates
        }
        scenario_count = len(enumerate_matchings(task.eligible_candidates, endpoints))
        rows.append(
            {
                "task_id": task.id,
                "eligible_candidates": len(task.eligible_candidates),
                "distinct_attributes": len(
                    {
                        endpoint
                        for candidate_id in task.eligible_candidates
                        for endpoint in candidate_map[candidate_id].endpoints
                    }
                ),
                "full_matching_scenarios": scenario_count,
            }
        )
    return rows


def run() -> tuple[list[dict[str, object]], dict[str, object]]:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    metadata = {
        "python": sys.version,
        "platform": platform.platform(),
        "dependency_versions": {
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "networkx": networkx.__version__,
        },
        "installation_commands": [
            "python3 -m venv .venv",
            ".venv/bin/python -m pip install -r requirements.txt",
            ".venv/bin/python -m pip install -e /home/wqts/projects/ess-advisor",
        ],
        "configs": CONFIGS,
        "time_limit_seconds": 10.0,
        "inner_time_limit_seconds": 5.0,
    }
    for config in CONFIGS:
        instance_id = str(config["instance_id"])
        instance = generate_instance(
            seed=int(config["seed"]),
            candidate_count=int(config["candidate_count"]),
            task_count=int(config["task_count"]),
            attribute_count=int(config["attribute_count"]),
            mixed_sign=bool(config["mixed_sign"]),
            sign_mode=str(config["sign_mode"]),
            zero_cost=bool(config["zero_cost"]),
            tight_budget=bool(config["tight_budget"]),
        )
        instance_path = INSTANCE_DIR / f"{instance_id}.json"
        write_instance(instance_path, instance)
        stats = {
            "kind": "instance",
            "instance_id": instance_id,
            "seed": config["seed"],
            "candidate_count": len(instance.candidates),
            "task_count": len(instance.tasks),
            "budget": fraction_to_json(instance.budget),
            "task_graphs": _task_graph_stats(instance),
        }
        records.append(stats)
        if bool(config["exhaustive"]):
            started = time.perf_counter()
            records.append(_reference_record(instance_id, instance, time.perf_counter() - started))
        started = time.perf_counter()
        static = solve_static(instance, time_limit=10.0)
        records.append(
            _outer_record(
                instance_id,
                "static_full_conditional",
                static,
                time.perf_counter() - started,
            )
        )
        started = time.perf_counter()
        master = solve_master_oracle(
            instance,
            time_limit=10.0,
            inner_time_limit=5.0,
        )
        records.append(
            _outer_record(
                instance_id,
                "master_oracle",
                master,
                time.perf_counter() - started,
            )
        )
    payload = {"metadata": metadata, "records": records}
    RESULT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return records, metadata


def write_report(records: list[dict[str, object]], metadata: dict[str, object]) -> None:
    instances = [record for record in records if record["kind"] == "instance"]
    by_instance: dict[str, list[dict[str, object]]] = {}
    for record in records:
        by_instance.setdefault(str(record["instance_id"]), []).append(record)
    lines = [
        "# First synthetic PESS-ESS study",
        "",
        "This report is generated from suite-results.json; unresolved solver "
        "statuses are not interpreted as optimal results.",
        "",
        f"- Python: {metadata['python'].splitlines()[0]}",
        f"- Platform: {metadata['platform']}",
        f"- Library versions: {metadata['dependency_versions']}",
        "- Solver backend: SciPy optimize.milp with HiGHS",
        "- Master/inner limits: 10 s / 5 s",
        "- Installation: python3 -m venv .venv; pip install -r requirements.txt; "
        "pip install -e /home/wqts/projects/ess-advisor",
        "",
        "## Results",
        "",
        "| Instance | Candidates | Tasks | Solver | Status | Objective | Runtime (s) | LB | UB | Scenarios/cuts | Inner calls | Early exits |",
        "|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for instance in instances:
        instance_id = str(instance["instance_id"])
        for record in by_instance[instance_id]:
            if record["kind"] == "instance":
                continue
            objective = record.get("objective")
            lines.append(
                f"| {instance_id} | {instance['candidate_count']} | "
                f"{instance['task_count']} | {record['solver']} | "
                f"{record['status']} | {objective or '—'} | "
                f"{record['runtime_seconds']:.4f} | "
                f"{record.get('lower_bound', '—')} | "
                f"{record.get('upper_bound', '—')} | "
                f"{record.get('scenario_count', record.get('distinct_cuts', '—'))} | "
                f"{record.get('inner_oracle_calls', '—')} | "
                f"{record.get('certified_early_exits', '—')} |"
            )
    lines.extend(["", "## Exhaustive agreement", ""])
    for instance in instances:
        instance_id = str(instance["instance_id"])
        records_for_instance = by_instance[instance_id]
        reference = next(
            (
                record
                for record in records_for_instance
                if record.get("solver") == "exhaustive_reference"
            ),
            None,
        )
        if reference is None:
            lines.append(
                f"- {instance_id}: no exhaustive reference; solver objectives "
                "are reported only with their MIP statuses."
            )
            continue
        reference_objective = reference["objective"]
        checked = [
            record
            for record in records_for_instance
            if record.get("solver") in {
                "static_full_conditional",
                "master_oracle",
            }
        ]
        agreement = all(
            record["status"] == "optimal"
            and record["objective"] == reference_objective
            for record in checked
        )
        lines.append(
            f"- {instance_id}: reference objective {reference_objective}; "
            f"static and Master--Oracle exact agreement: {agreement}."
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "For exhaustive instances, the test suite compares both MIP-based "
            "outer methods against an independent Fraction-based reference. "
            "Static formulation scenario counts measure the complete matching "
            "index, while Master–Oracle cut counts measure only generated "
            "conditional scenarios. A non-optimal status, if present, is an "
            "unresolved computational result rather than evidence of an "
            "algorithmic failure.",
            "",
            "These are synthetic measurements only. They do not establish "
            "PostgreSQL behavior, algorithmic superiority, or asymptotic "
            "performance guarantees.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    records, metadata = run()
    write_report(records, metadata)
    print(f"wrote {RESULT_PATH}")
    print(f"wrote {REPORT_PATH}")
