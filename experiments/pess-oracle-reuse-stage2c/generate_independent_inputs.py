"""Generate the preregistered Stage 2C independent input corpus.

This script is input-only. It never imports or calls a solver. The case list,
seeds, sizes, structures, and signed/zero-cost controls are frozen in
``protocol-v1.json`` before this script is run.
"""

from __future__ import annotations

import hashlib
import json
import random
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "inputs" / "independent"

CASES = (
    ("path_signed_cancel_4901", 4901, 8, 3, "path", True, False),
    ("cycle_signed_cancel_4902", 4902, 10, 3, "cycle", True, False),
    ("star_zero_cost_4903", 4903, 9, 4, "star", True, True),
    ("star_forest_4904", 4904, 14, 4, "star_forest", True, False),
    ("shared_cycle_4905", 4905, 16, 6, "shared_cycle", True, False),
    ("mixed_parallel_4906", 4906, 18, 5, "mixed_parallel", True, True),
    ("conflicting_cycles_4907", 4907, 20, 6, "conflicting_cycles", True, False),
    ("shared_path_4908", 4908, 20, 7, "shared_path", True, True),
)


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def edge_pool(rng: random.Random, count: int, structure: str) -> list[tuple[str, str]]:
    if structure in {"path", "shared_path"}:
        vertex_count = count + 1
    elif structure == "cycle":
        vertex_count = count
    else:
        vertex_count = max(6, count // 2 + 2)
    vertices = [f"a{index}" for index in range(vertex_count)]
    if structure in {"path", "shared_path"}:
        edges = [(vertices[index], vertices[index + 1]) for index in range(count)]
        return edges
    if structure == "cycle":
        return [(vertices[index], vertices[(index + 1) % len(vertices)]) for index in range(count)]
    if structure in {"star", "star_forest"}:
        edges = [(vertices[0], vertices[index + 1]) for index in range(min(count, len(vertices) - 1))]
        while len(edges) < count:
            index = len(edges)
            if structure == "star_forest" and index % 3 == 0:
                edges.append((vertices[-2], vertices[-1]))
            else:
                leaf = 1 + (index * 3) % (len(vertices) - 1)
                edges.append((vertices[0], vertices[leaf]))
        return edges
    if structure == "shared_cycle":
        edges = [(vertices[index], vertices[(index + 1) % len(vertices)]) for index in range(len(vertices))]
        while len(edges) < count:
            index = len(edges)
            edges.append((vertices[index % len(vertices)], vertices[(index + 2) % len(vertices)]))
        return edges[:count]
    if structure == "conflicting_cycles":
        edges = [(vertices[index], vertices[(index + 1) % len(vertices)]) for index in range(min(count, len(vertices)))]
        while len(edges) < count:
            index = len(edges)
            edges.append((vertices[index % len(vertices)], vertices[(index + 2) % len(vertices)]))
        return edges[:count]
    # Mixed parallel labels retain distinct IDs even when endpoints coincide.
    edges = []
    for index in range(count):
        left, right = rng.sample(vertices, 2)
        if index % 5 == 2 and edges:
            left, right = edges[-1]
        edges.append((left, right))
    return edges


def task_candidates(candidate_ids: list[str], task_index: int, task_count: int, structure: str) -> list[str]:
    count = len(candidate_ids)
    if structure in {"path", "cycle", "shared_path"}:
        width = max(4, min(count, count // 2 + 2))
        start = (2 * task_index) % count
        return [candidate_ids[(start + offset) % count] for offset in range(width)]
    if structure == "star":
        return [candidate_id for position, candidate_id in enumerate(candidate_ids) if (position + task_index) % 2 == 0]
    if structure == "star_forest":
        return [candidate_id for position, candidate_id in enumerate(candidate_ids) if (position + task_index) % 3 != 1]
    if structure == "shared_cycle":
        return [candidate_id for position, candidate_id in enumerate(candidate_ids) if (position + 2 * task_index) % 4 != 1]
    if structure == "conflicting_cycles":
        width = max(6, min(count, count // 2 + 3))
        start = (3 * task_index) % count
        return [candidate_ids[(start + offset) % count] for offset in range(width)]
    return [candidate_id for position, candidate_id in enumerate(candidate_ids) if (position + task_index) % 3 != 1]


def make_instance(seed: int, resource_count: int, task_count: int, structure: str, signed_cancellation: bool, zero_cost: bool) -> dict[str, object]:
    rng = random.Random(seed)
    endpoints = edge_pool(rng, resource_count, structure)
    candidates = []
    for index, edge in enumerate(endpoints):
        cost = Fraction(0) if zero_cost and index % 7 == 0 else Fraction(1 + rng.randrange(3))
        candidates.append(
            {
                "id": f"e{index:03d}",
                "table": "t0",
                "endpoints": sorted(edge),
                "maintenance_cost": fraction_text(cost),
            }
        )
    candidate_ids = [candidate["id"] for candidate in candidates]
    tasks = []
    for task_index in range(task_count):
        eligible = sorted(set(task_candidates(candidate_ids, task_index, task_count, structure)))
        alpha = Fraction(0) if task_index % 4 == 0 else Fraction(rng.randrange(-12, 13), 2)
        corrections = {}
        for position, candidate_id in enumerate(eligible):
            if signed_cancellation and position % 5 == 0:
                correction = -alpha
            else:
                correction = Fraction(rng.randrange(-16, 17), 2)
            corrections[candidate_id] = fraction_text(correction)
        tasks.append(
            {
                "id": f"i{task_index:03d}",
                "table": "t0",
                "weight": fraction_text(Fraction(1 + rng.randrange(3))),
                "alpha": fraction_text(alpha),
                "eligible_candidates": eligible,
                "corrections": corrections,
            }
        )
    total_cost = sum((Fraction(candidate["maintenance_cost"]) for candidate in candidates), Fraction())
    return {
        "budget": fraction_text(total_cost / 2),
        "candidates": candidates,
        "tasks": tasks,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for case_id, seed, resource_count, task_count, structure, signed_cancellation, zero_cost in CASES:
        path = OUTPUT / f"{case_id}.json"
        payload = json.dumps(
            make_instance(seed, resource_count, task_count, structure, signed_cancellation, zero_cost),
            indent=2,
            sort_keys=True,
        ) + "\n"
        path.write_text(payload, encoding="utf-8", newline="\n")
        records.append({"file": str(path.relative_to(ROOT)), "case_id": case_id, "seed": seed, "sha256": sha256(path)})
    (ROOT / "independent-input-manifest-v1.json").write_text(
        json.dumps(
            {
                "manifest_id": "pess-oracle-reuse-stage2c-independent-inputs-v1",
                "generator": {"file": "generate_independent_inputs.py", "sha256": sha256(Path(__file__))},
                "records": records,
                "freeze_statement": "Generated input bytes precede all Stage 2C solver invocations and treatment results.",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (ROOT / "SHA256SUMS-independent").write_text(
        "".join(f"{record['sha256']}  {record['file']}\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )
    original_records = [
        {
            "file": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for path in sorted((ROOT / "inputs" / "original-stage1b").glob("*.json"))
    ]
    (ROOT / "input-freeze-v1.json").write_text(
        json.dumps(
            {
                "manifest_id": "pess-oracle-reuse-stage2c-input-freeze-v1",
                "protocol": "protocol-v1.json",
                "advisor_sha": "1052ff4a46270c90414d76b32d6f6b37e5908f6a",
                "original_stage1b": original_records,
                "independent": records,
                "freeze_statement": "All listed input bytes and hashes precede Stage 2C profiling and treatment execution.",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    all_records = original_records + [
        {"file": record["file"], "sha256": record["sha256"]} for record in records
    ]
    (ROOT / "SHA256SUMS-inputs").write_text(
        "".join(f"{record['sha256']}  {record['file']}\n" for record in all_records),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
