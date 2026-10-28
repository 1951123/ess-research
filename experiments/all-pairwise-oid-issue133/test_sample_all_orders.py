"""Synthetic tests for the Issue #133 order sampler; no database is used."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import unittest

from sample_all_orders import (
    DEFAULT_RANDOM_ORDERS_PER_DATASET,
    RNG_VERSION,
    build_schedule,
    canonical_bytes,
    dataset_schedule,
    draw_permutation,
    order_sha256,
)


class Issue133OrderSamplerTests(unittest.TestCase):
    def test_frozen_inventory_and_order_file_are_self_consistent(self) -> None:
        folder = Path(__file__).resolve().parent
        manifest_path = folder / "candidate-universe-manifest.json"
        sample_path = folder / "all-order-sample-v1.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(manifest_bytes).hexdigest(),
            "20fd045a1391e6b0308d36ec581e128db185b892bc6e7384540e77c483572104",
        )
        self.assertEqual(
            hashlib.sha256(sample_path.read_bytes()).hexdigest(),
            "6e53e60083426a0f6fedb7147eae418ceb69aa826e01484d8794b95a80546d9c",
        )
        self.assertEqual(
            sample["candidate_universe_sha256"],
            hashlib.sha256(canonical_bytes(manifest)).hexdigest(),
        )
        self.assertEqual(
            sample["generator_sha256"],
            hashlib.sha256((folder / "sample_all_orders.py").read_bytes()).hexdigest(),
        )
        expected_counts = {"forest10": 45, "census13": 78, "dmv11": 55, "power7": 21}
        self.assertEqual(set(manifest["datasets"]), set(expected_counts))
        self.assertEqual(set(sample["datasets"]), set(expected_counts))
        for dataset, expected_count in expected_counts.items():
            dataset_manifest = manifest["datasets"][dataset]
            candidates = dataset_manifest["candidates"]
            self.assertEqual(len(candidates), expected_count)
            schema_count = len(dataset_manifest["schema_columns"])
            self.assertEqual(len(candidates), schema_count * (schema_count - 1) // 2)
            rows = [{"id": row["id"], "endpoints": row["source_columns"]} for row in candidates]
            compact = json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode()
            self.assertEqual(
                hashlib.sha256(compact).hexdigest(),
                dataset_manifest["candidate_map_sha256_compact_json"],
            )
            ids = [row["id"] for row in candidates]
            self.assertEqual(ids, sorted(ids))
            expected_pairs = list(itertools.combinations(range(schema_count), 2))
            self.assertEqual([tuple(row["column_indices_zero_based"]) for row in candidates], expected_pairs)
            orders = sample["datasets"][dataset]
            self.assertEqual(len(orders), 6)
            self.assertEqual(orders[0]["permutation"], ids)
            self.assertEqual(orders[1]["permutation"], list(reversed(ids)))
            self.assertEqual(sum(row["kind"] == "random_without_replacement" for row in orders), 4)
            self.assertEqual(len({tuple(row["permutation"]) for row in orders}), len(orders))
            for order in orders:
                self.assertEqual(len(order["permutation"]), expected_count)
                self.assertEqual(set(order["permutation"]), set(ids))
                self.assertEqual(order_sha256(order["permutation"]), order["permutation_sha256"])

    def test_full_universe_permutations_have_expected_identity(self) -> None:
        ids = [f"e00_{index:02d}" for index in range(1, 9)]
        rows = dataset_schedule("synthetic", ids, 123456789)
        self.assertEqual(len(rows), 2 + DEFAULT_RANDOM_ORDERS_PER_DATASET)
        self.assertEqual(rows[0]["permutation"], sorted(ids))
        self.assertEqual(rows[1]["permutation"], sorted(ids, reverse=True))
        self.assertEqual(len({tuple(row["permutation"]) for row in rows}), len(rows))
        for row in rows:
            self.assertEqual(len(row["permutation"]), len(ids))
            self.assertEqual(set(row["permutation"]), set(ids))
            self.assertEqual(len(row["permutation_sha256"]), 64)

    def test_fixed_seed_reproduces_same_schedule(self) -> None:
        ids = [f"candidate-{index}" for index in range(12)]
        first = dataset_schedule("synthetic", ids, 987654321)
        second = dataset_schedule("synthetic", list(reversed(ids)), 987654321)
        self.assertEqual(first, second)
        self.assertEqual(RNG_VERSION, "ess-splitmix64-fisher-yates-direct-v1")

    def test_direct_shuffle_handles_199_ids_without_factorial_enumeration(self) -> None:
        ids = [f"candidate-{index:03d}" for index in range(199)]
        order = draw_permutation(ids, 111)
        self.assertEqual(len(ids), 199)
        self.assertEqual(len(order), len(ids))
        self.assertEqual(set(order), set(ids))

    def test_manifest_requires_candidate_lists(self) -> None:
        with self.assertRaisesRegex(ValueError, "datasets"):
            build_schedule({}, 1)
        with self.assertRaisesRegex(ValueError, "candidate list"):
            build_schedule({"datasets": {"synthetic": {}}}, 1)


if __name__ == "__main__":
    unittest.main()
