"""Synthetic tests for source-identity reconciliation; no benchmark outcomes."""

from __future__ import annotations

import unittest

from rebuild_historical_fingerprints import (
    protocol_v4_exact_fingerprint,
    reconcile_claims,
    split_overlap_summary,
)


def row(dataset: str, split: str, index: int, exact: str, template: str) -> dict[str, object]:
    return {
        "dataset": dataset,
        "split": split,
        "query_id": f"arecel:{dataset}:{split}:{index:06d}",
        "source_index": index,
        "source_sql_sha256": f"sql-{dataset}-{split}-{index}",
        "exact_fingerprint_sha256": exact,
        "protocol_v4_exact_fingerprint_sha256": exact,
        "template_fingerprint_sha256": template,
        "historical_sources": [f"arecel:{split}"],
    }


class HistoricalFingerprintTests(unittest.TestCase):
    def test_protocol_claim_matches_identity_and_adds_provenance(self) -> None:
        source = row("forest10", "test", 7, "exact-7", "template-7")
        claim = {
            "source": "stage1a-issue38:heldout_selection",
            "dataset": "forest10",
            "query_id": source["query_id"],
            "source_index": 7,
            "source_sql_sha256": source["source_sql_sha256"],
            "protocol_v4_exact_fingerprint_sha256": None,
            "template_fingerprint_sha256": None,
        }
        result = reconcile_claims([source], [claim])
        self.assertEqual(result["verified_count"], 1)
        self.assertEqual(result["errors"], [])
        self.assertIn(claim["source"], source["historical_sources"])

    def test_index_mismatch_fails_closed(self) -> None:
        source = row("forest10", "test", 7, "exact-7", "template-7")
        claim = {
            "source": "issue48:test_cohort",
            "dataset": "forest10",
            "query_id": source["query_id"],
            "source_index": 8,
            "source_sql_sha256": source["source_sql_sha256"],
            "protocol_v4_exact_fingerprint_sha256": "wrong-exact",
            "template_fingerprint_sha256": "wrong-template",
        }
        result = reconcile_claims([source], [claim])
        self.assertEqual(result["verified_count"], 0)
        self.assertEqual(result["errors"][0]["reason"], "source_index_mismatch")

    def test_exact_fingerprint_mismatch_fails_closed(self) -> None:
        source = row("forest10", "test", 7, "issue59-exact", "template-7")
        claim = {
            "source": "issue48:test_cohort",
            "dataset": "forest10",
            "query_id": source["query_id"],
            "source_index": 7,
            "source_sql_sha256": source["source_sql_sha256"],
            "protocol_v4_exact_fingerprint_sha256": "wrong-v4-exact",
            "template_fingerprint_sha256": "template-7",
        }
        result = reconcile_claims([source], [claim])
        self.assertEqual(result["verified_count"], 0)
        self.assertEqual(
            result["errors"][0]["reason"], "protocol_v4_exact_fingerprint_mismatch"
        )

    def test_template_fingerprint_mismatch_fails_closed(self) -> None:
        source = row("census13", "valid", 4, "exact-4", "template-4")
        claim = {
            "source": "issue48:validation_calibration",
            "dataset": "census13",
            "query_id": source["query_id"],
            "source_index": 4,
            "source_sql_sha256": source["source_sql_sha256"],
            "protocol_v4_exact_fingerprint_sha256": "exact-4",
            "template_fingerprint_sha256": "wrong-template",
        }
        result = reconcile_claims([source], [claim])
        self.assertEqual(result["verified_count"], 0)
        self.assertEqual(result["errors"][0]["reason"], "template_fingerprint_mismatch")

    def test_duplicate_protocol_claim_fails_closed(self) -> None:
        source = row("census13", "test", 3, "exact-3", "template-3")
        claim = {
            "source": "issue48:test_cohort",
            "dataset": "census13",
            "query_id": source["query_id"],
            "source_index": 3,
            "source_sql_sha256": source["source_sql_sha256"],
            "protocol_v4_exact_fingerprint_sha256": "exact-3",
            "template_fingerprint_sha256": "template-3",
        }
        result = reconcile_claims([source], [claim, claim])
        self.assertEqual(result["verified_count"], 0)
        self.assertTrue(all(item["reason"] == "duplicate_claim_within_source" for item in result["errors"]))

    def test_cross_split_overlaps_are_counted_without_dropping_rows(self) -> None:
        rows = [
            row("power7", "train", 1, "same-exact", "same-template"),
            row("power7", "valid", 2, "same-exact", "same-template"),
            row("power7", "test", 3, "different-exact", "same-template"),
        ]
        result = split_overlap_summary(rows)["power7"]
        self.assertEqual(result["train__valid"]["exact_fingerprint"]["shared_distinct_fingerprints"], 1)
        self.assertEqual(result["valid__test"]["exact_fingerprint"]["shared_distinct_fingerprints"], 0)
        self.assertEqual(result["train__test"]["template_fingerprint"]["shared_distinct_fingerprints"], 1)

    def test_protocol_v4_sorted_exact_contract_is_order_independent(self) -> None:
        left = [
            {"column": "z", "operator": "=", "value": 1.5},
            {"column": "a", "operator": "[]", "value": [2.0, 3.0]},
        ]
        right = list(reversed(left))
        self.assertEqual(protocol_v4_exact_fingerprint(left), protocol_v4_exact_fingerprint(right))


if __name__ == "__main__":
    unittest.main()
