"""Stable JSON serialization for frozen inputs and evidence records."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from stage0b_reference import Edge, Instance, Task


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def parse_fraction(value: str | float) -> Fraction:
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        raise TypeError("JSON inputs must encode exact fractions as strings or integers")
    return Fraction(value)


def instance_to_json(instance: Instance) -> dict[str, Any]:
    return {
        "name": instance.name,
        "tier": instance.tier,
        "resources": list(instance.resources),
        "maintenance": {label: fraction_text(instance.maintenance[label]) for label in instance.resources},
        "budget": fraction_text(instance.budget),
        "tasks": [
            {
                "name": task.name,
                "weight": fraction_text(task.weight),
                "alpha": fraction_text(task.alpha),
                "edges": [list(edge) for edge in task.edges],
                "coefficients": {label: fraction_text(task.coefficients[label]) for label, _, _ in task.edges},
            }
            for task in instance.tasks
        ],
    }


def instance_from_json(data: dict[str, Any]) -> Instance:
    tasks = []
    for raw in data["tasks"]:
        edges: tuple[Edge, ...] = tuple(tuple(edge) for edge in raw["edges"])
        tasks.append(
            Task(
                raw["name"],
                parse_fraction(raw["weight"]),
                parse_fraction(raw["alpha"]),
                edges,
                {label: parse_fraction(value) for label, value in raw["coefficients"].items()},
            )
        )
    return Instance(
        data["name"],
        tuple(data["resources"]),
        tuple(tasks),
        {label: parse_fraction(value) for label, value in data["maintenance"].items()},
        parse_fraction(data["budget"]),
        data.get("tier", "small"),
    )


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
