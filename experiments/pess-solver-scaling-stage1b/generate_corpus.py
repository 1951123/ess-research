"""Generate the frozen Issue #39 Stage 1B synthetic corpus.

This script only creates input JSON and manifest metadata. It never calls a
solver. Run it once from this directory before the input-freeze commit.
"""

from __future__ import annotations

import hashlib
import json
import random
from fractions import Fraction
from pathlib import Path

from pess_ess.model import Candidate, Instance, Task, instance_to_dict


ROOT = Path(__file__).resolve().parent
INSTANCE_DIR = ROOT / "instances"


CORPUS = [
    ("small", "star_single", 3901, 8, 2, "loose", False, None, None),
    ("small", "path_cycle", 3902, 9, 2, "tight", False, None, None),
    ("small", "mixed_parallel", 3903, 10, 3, "loose", True, None, None),
    ("small", "sharing_cycle", 3904, 7, 4, "tight", True, None, None),
    ("medium", "star_single", 3911, 14, 4, "loose", False, "pair-star", "component split and task sharing"),
    ("medium", "star_forest", 3911, 14, 4, "loose", False, "pair-star", "component split and task sharing"),
    ("medium", "path", 3913, 18, 5, "loose", False, "pair-path", "one edge closes the cycle"),
    ("medium", "cycle", 3913, 18, 5, "loose", False, "pair-path", "one edge closes the cycle"),
    ("medium", "mixed_general", 3915, 20, 5, "loose", True, "pair-parallel", "duplicate labeled endpoints"),
    ("medium", "mixed_parallel", 3915, 20, 5, "loose", True, "pair-parallel", "duplicate labeled endpoints"),
    ("medium", "sharing_low", 3917, 16, 6, "loose", True, "pair-sharing", "task-resource incidence cycle"),
    ("medium", "sharing_cycle", 3917, 16, 6, "loose", True, "pair-sharing", "task-resource incidence cycle"),
    ("large", "star_forest", 3921, 24, 5, "loose", True, None, None),
    ("large", "cycle", 3922, 28, 5, "tight", False, None, None),
    ("large", "mixed_parallel", 3923, 32, 6, "loose", True, None, None),
    ("large", "sharing_cycle", 3924, 36, 7, "tight", True, None, None),
]


def _edge_pool(rng: random.Random, count: int, stratum: str) -> list[tuple[str, str]]:
    attr_count = max(5, min(14, count // 2 + 2))
    attrs = [f"a{index}" for index in range(attr_count)]
    edges: list[tuple[str, str]] = []
    if stratum.startswith("star"):
        center = attrs[0]
        second = attrs[1:]
        for index in range(count):
            if index < len(second):
                edges.append((center, second[index]))
            else:
                left = attrs[1 + ((index * 3) % max(1, len(attrs) - 1))]
                right = attrs[1 + ((index * 5 + 1) % max(1, len(attrs) - 1))]
                if left == right:
                    right = attrs[-1]
                edges.append((left, right))
    elif stratum in {"path", "cycle"}:
        for index in range(count):
            edges.append((attrs[index % len(attrs)], attrs[(index + 1) % len(attrs)]))
        if stratum == "path":
            edges[-1] = (attrs[-2], attrs[-1])
    else:
        for index in range(count):
            left, right = rng.sample(attrs, 2)
            edges.append((left, right))
            if "parallel" in stratum and index % 5 == 2:
                edges[-1] = edges[-2]
    return edges


def _eligible(
    rng: random.Random,
    candidate_ids: list[str],
    task_index: int,
    task_count: int,
    stratum: str,
) -> list[str]:
    if stratum.startswith("star"):
        # Keep task-local stars bounded while allowing a forest task to expose
        # two components. The task index controls a deterministic rotation.
        stride = 2 if "forest" in stratum else 1
        selected = [cid for pos, cid in enumerate(candidate_ids) if (pos + task_index) % stride == 0]
    elif stratum in {"path", "cycle"}:
        width = max(5, min(len(candidate_ids), len(candidate_ids) // 2 + 2))
        start = (task_index * 2) % len(candidate_ids)
        selected = [candidate_ids[(start + offset) % len(candidate_ids)] for offset in range(width)]
    elif stratum == "sharing_low":
        selected = [cid for pos, cid in enumerate(candidate_ids) if (pos + task_index * 7) % 5 < 2]
    else:
        selected = [cid for pos, cid in enumerate(candidate_ids) if (pos + task_index) % 3 != 1]
    if not selected:
        selected = [candidate_ids[task_index % len(candidate_ids)]]
    return list(dict.fromkeys(selected))


def make_instance(seed: int, candidate_count: int, task_count: int, stratum: str, budget_mode: str, zero_cost: bool) -> Instance:
    rng = random.Random(seed)
    edges = _edge_pool(rng, candidate_count, stratum)
    candidates: list[Candidate] = []
    for index, endpoints in enumerate(edges):
        cost = 0 if zero_cost and index % 7 == 0 else 1 + rng.randrange(3)
        candidates.append(Candidate(f"e{index:03d}", "t0", endpoints, Fraction(cost)))
    candidate_ids = [candidate.id for candidate in candidates]
    tasks: list[Task] = []
    for task_index in range(task_count):
        eligible = _eligible(rng, candidate_ids, task_index, task_count, stratum)
        if task_index % 4 == 0:
            alpha = Fraction(0)  # explicit cancellation baseline at empty matching
        else:
            alpha = Fraction(rng.randrange(-6, 7), 2)
        corrections: dict[str, Fraction] = {}
        for position, candidate_id in enumerate(eligible):
            if position % 5 == 0:
                correction = -alpha  # near-zero signed cancellation witness
            else:
                correction = Fraction(rng.randrange(-8, 9), 2)
            corrections[candidate_id] = correction
        tasks.append(
            Task(
                id=f"i{task_index:03d}",
                table="t0",
                weight=Fraction(1 + rng.randrange(3)),
                alpha=alpha,
                eligible_candidates=tuple(eligible),
                corrections=corrections,
            )
        )
    total_cost = sum((candidate.maintenance_cost for candidate in candidates), Fraction())
    divisor = 4 if budget_mode == "tight" else 2
    budget = total_cost / divisor
    return Instance(tuple(candidates), tuple(tasks), budget)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for tier, stratum, seed, candidate_count, task_count, budget_mode, zero_cost, pair_id, changed_feature in CORPUS:
        instance = make_instance(seed, candidate_count, task_count, stratum, budget_mode, zero_cost)
        filename = f"{tier}_{stratum}_{seed}.json"
        path = INSTANCE_DIR / filename
        payload = json.dumps(instance_to_dict(instance), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        path.write_text(payload, encoding="utf-8", newline="\n")
        records.append(
            {
                "file": f"instances/{filename}",
                "tier": tier,
                "stratum": stratum,
                "seed": seed,
                "candidate_count": len(instance.candidates),
                "task_count": len(instance.tasks),
                "budget": str(instance.budget),
                "zero_cost_resources": zero_cost,
                "pair_id": pair_id,
                "changed_feature": changed_feature,
                "sha256": _sha256(path),
            }
        )
    manifest = {
        "manifest_id": "stage1b-v1-frozen-inputs",
        "generator": {"file": "generate_corpus.py", "sha256": _sha256(Path(__file__))},
        "instances": records,
        "counts": {tier: sum(record["tier"] == tier for record in records) for tier in ("small", "medium", "large")},
        "freeze_statement": "These input bytes and metadata precede all Stage 1B solver comparison results.",
    }
    (ROOT / "manifest-v1.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    sums = "\n".join(f"{record['sha256']}  {record['file']}" for record in records) + "\n"
    (ROOT / "SHA256SUMS-inputs").write_text(sums, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
