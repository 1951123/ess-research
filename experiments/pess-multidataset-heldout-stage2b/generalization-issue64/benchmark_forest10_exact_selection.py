"""Synthetic performance probe for exact Forest10 B<=3 selection."""

from __future__ import annotations

import json
import time
from fractions import Fraction
from itertools import combinations

from forest10_exact_selection import TaskModel, exact_select_many


def run(task_count: int = 100) -> dict[str, object]:
    columns = tuple(f"c{i}" for i in range(10))
    candidates = tuple(
        (f"e{i:02}_{j:02}", (left, right))
        for i, left in enumerate(columns)
        for j, right in enumerate(columns[i + 1 :], start=i + 1)
    )
    candidate_ids = tuple(edge for edge, _ in candidates)
    tasks = []
    for task_index in range(task_count):
        available = tuple(
            edge for index, edge in enumerate(candidate_ids)
            if (index * 7 + task_index * 11) % 45 < 16
        )
        b = {
            edge: Fraction(((index + task_index) % 13) - 6, 100)
            for index, edge in enumerate(available)
        }
        tasks.append(TaskModel(Fraction((task_index % 17) - 8, 10), b, available))
    started = time.perf_counter()
    result = exact_select_many(tuple(tasks), candidates, (0, 2, 3))
    elapsed = time.perf_counter() - started
    return {
        "kind": "synthetic_only_not_workload_or_pg_measurement",
        "candidate_count": len(candidates),
        "task_count": task_count,
        "feasible_subsets_b3": result["Nominal"]["3"]["feasible_subset_count"],
        "methods_and_budgets": 6,
        "elapsed_seconds": round(elapsed, 6),
        "linear_projection_10000_tasks_seconds": round(elapsed * 10000 / task_count, 3),
        "projection_limitation": "linear arithmetic projection from synthetic Fraction model inputs; not a runtime guarantee",
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
