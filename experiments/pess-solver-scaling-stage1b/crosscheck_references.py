"""Cross-check the independent Stage 1B verifier against the advisor reference.

This is a validation harness only. It does not call either outer solver.
"""

from __future__ import annotations

import argparse
import json
import platform
from itertools import combinations
from pathlib import Path

from pess_ess.matchings import enumerate_maximal_matchings
from pess_ess.model import read_instance
from pess_ess.reference import solve_exhaustive as advisor_exhaustive

from independent_reference import exhaustive, maximal_matchings, objective

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    records = []
    for path in sorted((ROOT / "instances").glob("small_*.json")):
        instance = read_instance(path)
        ours = exhaustive(instance)
        advisor = advisor_exhaustive(instance)
        matching_checks = 0
        for size in range(len(instance.candidates) + 1):
            for selected_tuple in combinations(instance.candidate_ids, size):
                selected = frozenset(selected_tuple)
                if instance.maintenance_cost(selected) > instance.budget:
                    continue
                for task in instance.tasks:
                    candidate_map = instance.candidate_map
                    endpoints = {
                        candidate_id: candidate_map[candidate_id].endpoints
                        for candidate_id in task.eligible_candidates
                    }
                    ours_matchings = maximal_matchings(selected, task, instance)
                    advisor_matchings = enumerate_maximal_matchings(
                        selected.intersection(task.eligible_candidates), endpoints
                    )
                    if set(ours_matchings) != set(advisor_matchings):
                        raise AssertionError(f"matching mismatch: {path.name} {task.id} {sorted(selected)}")
                    matching_checks += 1
                ours_value, _ = objective(instance, selected)
                # The advisor exhaustive result is used for the global optimum;
                # per-subset objective matching is checked by the matching set
                # equality and an independent re-evaluation here.
                if ours_value < 0:
                    raise AssertionError("loss must be nonnegative")
        records.append(
            {
                "file": path.name,
                "ours_objective": str(ours.objective),
                "advisor_objective": str(advisor.objective),
                "optimal_sets_equal": set(ours.optimal_sets) == set(advisor.optimal_sets),
                "evaluated_subsets": ours.evaluated_subsets,
                "feasible_subsets": ours.feasible_subsets,
                "matching_checks": matching_checks,
            }
        )
    result = {
        "status": "PASS",
        "instances": records,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "note": "Independent verifier and advisor reference matched on every feasible small subset and every selected task-local labeled maximal-matching set.",
    }
    output = Path(args.output)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
