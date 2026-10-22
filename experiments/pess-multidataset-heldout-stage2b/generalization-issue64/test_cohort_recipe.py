"""Synthetic-only tests for the frozen outcome-free cohort recipe helpers."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cohort_recipe import (
    counter_u64,
    candidate_priority,
    exact_predicate_fingerprint,
    normalized_template,
    query_id,
    randbelow,
    split_for_template,
    template_fingerprint,
)
from verify_reference_pins import RELATIVE_PATHS, verify_files


class CohortRecipeTests(unittest.TestCase):
    def test_template_normalization_matches_issue59_shape_rule(self) -> None:
        q1 = {
            "predicates": [
                {"column": "z", "operator": "[]", "value": [1, 9]},
                {"column": "a", "operator": "=", "value": "x"},
            ]
        }
        q2 = {
            "predicates": [
                {"column": "a", "operator": "=", "value": "different"},
                {"column": "z", "operator": "[]", "value": [3, 6]},
            ]
        }
        expected = json.dumps(
            sorted([("z", "[]", "range"), ("a", "=", "scalar")]),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        self.assertEqual(normalized_template(q1), expected)
        self.assertEqual(template_fingerprint(q1), template_fingerprint(q2))
        self.assertNotEqual(exact_predicate_fingerprint(q1), exact_predicate_fingerprint(q2))

    def test_exact_fingerprint_uses_ordered_canonical_tuples(self) -> None:
        query = {"predicates": [{"column": "x", "operator": "=", "value": 7}]}
        payload = json.dumps(
            [["x", "=", 7]], ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        self.assertEqual(
            exact_predicate_fingerprint(query), hashlib.sha256(payload.encode()).hexdigest()
        )

    def test_group_split_and_query_id_are_stable(self) -> None:
        template = "a" * 64
        split = split_for_template("forest10", template)
        self.assertEqual(split, "heldout")
        self.assertIn(split, {"calibration", "heldout"})
        self.assertEqual(split, split_for_template("forest10", template))
        self.assertEqual(
            query_id("forest10", split, template), f"issue64:forest10:{split}:{template}"
        )
        self.assertEqual(
            candidate_priority("forest10", 6401, template),
            "43ee8797956ac612155c29ef6c00f05c5a5eae90d81282c954bd6cc31fadc9ed",
        )

    def test_hash_counter_draws_are_reproducible_and_bounded(self) -> None:
        word = counter_u64("forest10", 6401, 12, "predicate-count")
        self.assertEqual(word, 17079368635909704243)
        self.assertEqual(word, counter_u64("forest10", 6401, 12, "predicate-count"))
        self.assertGreaterEqual(word, 0)
        self.assertLess(word, 2**64)
        self.assertGreaterEqual(randbelow(13, "forest10", 6401, 12, "predicate-count"), 0)
        self.assertLess(randbelow(13, "forest10", 6401, 12, "predicate-count"), 13)

    def test_bad_fingerprints_and_empty_queries_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            template_fingerprint({"predicates": []})
        with self.assertRaises(ValueError):
            split_for_template("forest10", "not-a-hash")
        with self.assertRaises(ValueError):
            randbelow(0, "forest10", 6401, 0, "bad")

    def test_reference_pin_verifier_is_whitelisted_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected: dict[str, str] = {}
            for key, relative in RELATIVE_PATHS.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"synthetic:{key}".encode())
                expected[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(verify_files(root, expected), [])
            changed = dict(expected)
            changed["frozen_protocol_v4_sha256"] = "0" * 64
            self.assertTrue(verify_files(root, changed))


if __name__ == "__main__":
    unittest.main()
