"""Create the frozen deterministic Stage 0B input corpus."""

from __future__ import annotations

import random
from fractions import Fraction
from pathlib import Path

from reference import Edge, Instance, Task
from serialization import write_json, instance_to_json


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "instances"


def task(
    name: str,
    weight: str,
    alpha: str,
    edges: tuple[Edge, ...],
    coefficients: tuple[str, ...],
) -> Task:
    return Task(
        name,
        Fraction(weight),
        Fraction(alpha),
        edges,
        {edge[0]: Fraction(value) for edge, value in zip(edges, coefficients)},
    )


def make(
    name: str,
    resources: tuple[str, ...],
    tasks: tuple[Task, ...],
    maintenance: tuple[str, ...],
    budget: str,
    tier: str = "small",
) -> Instance:
    return Instance(
        name,
        resources,
        tasks,
        {label: Fraction(value) for label, value in zip(resources, maintenance)},
        Fraction(budget),
        tier,
    )


def deterministic_cases() -> list[Instance]:
    return [
        make(
            "path_strong_cancellation",
            ("e0", "e1", "e2", "e3"),
            (task("t0", "1", "1", (("e0", "a", "b"), ("e1", "b", "c"), ("e2", "c", "d"), ("e3", "d", "e")), ("-1", "1", "-2", "2")),),
            ("1", "1", "1", "1"),
            "2",
        ),
        make(
            "star_zero_near_optimum",
            ("e0", "e1", "e2", "e3", "e4"),
            (task("t0", "1", "1/2", tuple((f"e{i}", "hub", f"v{i}") for i in range(5)), ("-1/2", "1", "-2", "1/4", "3")),),
            ("0", "1", "1", "2", "2"),
            "2",
        ),
        make(
            "disjoint_zero_cost_budget_zero",
            ("e0", "e1", "e2", "e3"),
            (task("t0", "2", "-1", (("e0", "a", "b"), ("e1", "c", "d"), ("e2", "e", "f"), ("e3", "g", "h")), ("1", "0", "-1", "2")),),
            ("0", "0", "1", "2"),
            "0",
        ),
        make(
            "cycle_signed_mixed",
            ("e0", "e1", "e2", "e3", "e4", "e5"),
            (
                task("t0", "1", "-1/3", (("e0", "a", "b"), ("e1", "b", "c"), ("e2", "c", "d"), ("e3", "d", "e"), ("e4", "e", "f"), ("e5", "f", "a")), ("2", "-3", "1/2", "-1", "2", "-1/2")),
                task("t1", "1/2", "2", (("e0", "a", "b"), ("e2", "c", "d"), ("e4", "e", "f")), ("-2", "1", "-1")),
            ),
            ("1", "1", "1", "1", "1", "1"),
            "3",
        ),
        make(
            "parallel_duplicate_endpoints",
            ("e0", "e1", "e2", "e3"),
            (task("t0", "1", "0", (("e0", "a", "b"), ("e1", "a", "b"), ("e2", "b", "c"), ("e3", "c", "d")), ("3", "-2", "1", "-1")),),
            ("1", "1", "1", "1"),
            "2",
        ),
        make(
            "rounded_zero_selected_edge",
            ("e0", "e1", "e2", "e3"),
            (task("t0", "1", "1/3", (("e0", "a", "b"),), ("-1/3",)),),
            ("1", "0", "0", "0"),
            "1",
        ),
        make(
            "shared_resources_separate_task_adversaries",
            ("e0", "e1", "e2", "e3"),
            (
                task("t0", "1", "1", (("e0", "a", "b"), ("e1", "b", "c")), ("-1", "3")),
                task("t1", "2", "-1", (("e0", "x", "y"), ("e2", "y", "z"), ("e3", "z", "q")), ("1", "-2", "1/2")),
            ),
            ("1", "1", "0", "2"),
            "2",
        ),
        make(
            "empty_selection_and_empty_task_graph",
            ("e0", "e1", "e2", "e3"),
            (
                task("empty", "1", "-2", (), ()),
                task("t1", "1", "0", (("e0", "a", "b"),), ("0",)),
            ),
            ("0", "1", "1", "1"),
            "0",
        ),
    ]


def random_case(seed: int, index: int) -> Instance:
    rng = random.Random(seed)
    n = 4 + (seed % 7)
    resources = tuple(f"e{i}" for i in range(n))
    vertices = tuple(f"v{i}" for i in range(max(3, n)))
    shapes = [
        (vertices[i % len(vertices)], vertices[(i + 1) % len(vertices)])
        for i in range(n)
    ]
    if index % 2 == 1:
        shapes[2] = shapes[0]  # labeled parallel endpoints
    tasks = []
    for task_index in range(1 + seed % 4):
        chosen = [i for i in range(n) if rng.random() < 0.7]
        if not chosen:
            chosen = [task_index % n]
        edges = tuple((resources[i], *shapes[i]) for i in chosen)
        values = tuple(rng.choice(("-3", "-1/3", "-1", "0", "1/4", "1", "2", "3")) for _ in edges)
        tasks.append(task(f"t{task_index}", rng.choice(("1/2", "1", "2")), rng.choice(("-2", "-1/3", "0", "1/2", "2")), edges, values))
    maintenance = tuple(rng.choice(("0", "1/2", "1", "2")) for _ in resources)
    budget = rng.choice(("0", "1/2", "1", "2", "3", "4", "6", "8"))
    return make(f"random_{seed}", resources, tuple(tasks), maintenance, budget)


def stress_case(resource_count: int, task_count: int, seed: int) -> Instance:
    rng = random.Random(seed)
    resources = tuple(f"e{i}" for i in range(resource_count))
    vertices = tuple(f"v{i}" for i in range(resource_count))
    edges = tuple((label, vertices[i], vertices[(i + 1) % resource_count]) for i, label in enumerate(resources))
    tasks = []
    for task_index in range(task_count):
        chosen = tuple(i for i in range(resource_count) if (i + task_index) % 3 != 0)
        task_edges = tuple(edges[i] for i in chosen)
        coefficients = tuple(rng.choice(("-2", "-1", "-1/3", "0", "1/4", "1", "2")) for _ in task_edges)
        tasks.append(task(f"t{task_index}", rng.choice(("1/2", "1", "2")), rng.choice(("-1", "-1/3", "0", "1")), task_edges, coefficients))
    maintenance = tuple(rng.choice(("0", "1/2", "1")) for _ in resources)
    return make(f"stress_{resource_count}_{task_count}", resources, tuple(tasks), maintenance, "6", "stress")


def main() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    instances = deterministic_cases() + [random_case(seed, index) for index, seed in enumerate((33101, 33102, 33103, 33104))]
    instances += [stress_case(12, 2, 33201), stress_case(14, 4, 33202), stress_case(16, 4, 33203)]
    for instance in instances:
        write_json(INPUT_DIR / f"{instance.name}.json", instance_to_json(instance))
    print(f"wrote {len(instances)} frozen instances to {INPUT_DIR}")


if __name__ == "__main__":
    main()
