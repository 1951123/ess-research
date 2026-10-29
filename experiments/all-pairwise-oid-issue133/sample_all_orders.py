"""Generate the frozen Issue #133 all-candidate OID order schedule.

This module is intentionally standard-library-only. It shuffles one list of
candidate IDs directly; unlike the Issue #107 finite-permutation sampler, it
never materializes the factorial permutation population. It performs no
database, workload, or result access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Sequence


RNG_VERSION = "ess-splitmix64-fisher-yates-direct-v1"
MASK_64 = (1 << 64) - 1
DEFAULT_RANDOM_ORDERS_PER_DATASET = 4


class SplitMix64:
    """SplitMix64 with rejection sampling for unbiased bounded integers."""

    def __init__(self, seed: int):
        if not 0 <= seed <= MASK_64:
            raise ValueError("seed must be an unsigned 64-bit integer")
        self.state = seed

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK_64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK_64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK_64
        return (value ^ (value >> 31)) & MASK_64

    def randbelow(self, upper: int) -> int:
        if not 1 <= upper <= (1 << 64):
            raise ValueError("upper must be in [1, 2**64]")
        limit = (1 << 64) - ((1 << 64) % upper)
        while True:
            value = self.next_u64()
            if value < limit:
                return value % upper


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def derive_seed(root_seed: int, dataset: str, draw_index: int, retry_index: int) -> int:
    material = (
        f"ess-issue133-order-seed-v1\0{root_seed}\0{dataset}\0"
        f"{draw_index}\0{retry_index}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def draw_permutation(ids: Sequence[str], seed: int) -> tuple[str, ...]:
    if not ids or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("candidate IDs must be nonempty strings")
    if len(set(ids)) != len(ids):
        raise ValueError("candidate IDs must be unique")
    values = list(ids)
    rng = SplitMix64(seed)
    for index in range(len(values) - 1, 0, -1):
        other = rng.randbelow(index + 1)
        values[index], values[other] = values[other], values[index]
    return tuple(values)


def order_sha256(order: Sequence[str]) -> str:
    return hashlib.sha256(canonical_bytes(list(order))).hexdigest()


def dataset_schedule(
    dataset: str,
    candidate_ids: Sequence[str],
    root_seed: int,
    random_count: int = DEFAULT_RANDOM_ORDERS_PER_DATASET,
) -> list[dict[str, Any]]:
    ids = tuple(sorted(candidate_ids))
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("candidate IDs must be a nonempty unique collection")
    if random_count < 0:
        raise ValueError("random_count must be nonnegative")

    canonical = ids
    reverse = tuple(reversed(ids))
    seen = {canonical, reverse}
    records = [
        {"order_id": "canonical", "kind": "fixed", "permutation": list(canonical)},
        {"order_id": "reverse", "kind": "fixed", "permutation": list(reverse)},
    ]

    for draw_index in range(random_count):
        retry_index = 0
        while True:
            seed = derive_seed(root_seed, dataset, draw_index, retry_index)
            order = draw_permutation(ids, seed)
            if order not in seen:
                break
            retry_index += 1
        seen.add(order)
        records.append({
            "order_id": f"random-{draw_index + 1:02d}",
            "kind": "random_without_replacement",
            "draw_index": draw_index,
            "retry_index": retry_index,
            "child_seed_hex": f"{seed:016x}",
            "permutation": list(order),
        })

    for record in records:
        record["permutation_sha256"] = order_sha256(record["permutation"])
    return records


def build_schedule(candidate_manifest: dict[str, Any], root_seed: int) -> dict[str, Any]:
    if not 0 <= root_seed <= MASK_64:
        raise ValueError("root_seed must be an unsigned 64-bit integer")
    datasets = candidate_manifest.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("candidate manifest must contain a nonempty datasets mapping")

    schedule = {}
    for dataset, item in datasets.items():
        rows = item.get("candidates")
        if not isinstance(rows, list):
            raise ValueError(f"{dataset} has no candidate list")
        ids = [row["id"] for row in rows]
        schedule[dataset] = dataset_schedule(dataset, ids, root_seed)

    return {
        "format": "ess-issue133-all-order-sample-v1",
        "rng_version": RNG_VERSION,
        "root_seed": root_seed,
        "root_seed_source": "CPython secrets.randbits(64), drawn once before any Issue #133 Test execution",
        "python_version_at_generation": platform.python_version(),
        "generator_path": "experiments/all-pairwise-oid-issue133/sample_all_orders.py",
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "random_orders_per_dataset": DEFAULT_RANDOM_ORDERS_PER_DATASET,
        "fixed_orders": ["canonical ascending candidate ID", "exact reverse"],
        "random_design": "successive uniform Fisher-Yates draws with rejection of fixed/previously drawn orders; hence SRSWOR from S_n excluding the two fixed orders",
        "candidate_universe_sha256": hashlib.sha256(canonical_bytes(candidate_manifest)).hexdigest(),
        "datasets": schedule,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--root-seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    payload = build_schedule(candidate_manifest, args.root_seed)
    args.output.write_bytes(canonical_bytes(payload))
    print(json.dumps({
        "output": str(args.output),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "datasets": {key: len(value) for key, value in payload["datasets"].items()},
        "random_orders": payload["random_orders_per_dataset"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
