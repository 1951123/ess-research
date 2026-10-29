"""Offline checks for the frozen matched-B5 design and paired summary logic."""
from __future__ import annotations

import unittest

import run_b5_control as runner


class FrozenDesignTests(unittest.TestCase):
    def test_frozen_ids_projection_and_order_hash(self) -> None:
        protocol = runner.read_frozen_protocol()
        self.assertEqual(set(protocol["frozen_b5_selection"]["selected_ids"]), runner.B5_IDS)
        self.assertEqual(tuple(protocol["order_matching"]["b5_create_order"]), runner.B5_ORDER)
        self.assertEqual(
            protocol["order_matching"]["random01_nominal_b5_projection"], list(runner.B5_ORDER)
        )
        self.assertNotEqual(
            protocol["order_matching"]["random01_nominal_b5_projection"],
            protocol["order_matching"]["random02_nominal_b5_projection"],
        )
        self.assertEqual(
            runner.sha256_order(runner.B5_ORDER),
            protocol["order_matching"]["b5_create_order_sha256"],
        )

    def test_catalog_signature_distinguishes_payload_state_and_fingerprint(self) -> None:
        base = {
            "attnames": ["elevation", "slope"],
            "kinds": ["m"],
            "stxkind": "{m}",
            "statistics_target": 300,
            "stxkeys": "1 3",
            "mcv_payload_present": True,
            "mcv_item_count": 300,
            "mcv_content_sha256": "a" * 64,
        }
        populated = runner.catalog_row_signature(base)
        null_payload = {**base, "mcv_payload_present": False, "kinds": None,
                        "mcv_item_count": 0, "payload_state": "NULL"}
        changed_payload = {**base, "mcv_content_sha256": "b" * 64}
        self.assertNotEqual(populated, runner.catalog_row_signature(null_payload))
        self.assertNotEqual(populated, runner.catalog_row_signature(changed_payload))


class PairingLogicTests(unittest.TestCase):
    @staticmethod
    def rows(config: str, errors: list[float], plans: list[int], used: list[str]) -> list[dict]:
        result = []
        for index, (error, plan) in enumerate(zip(errors, plans, strict=True)):
            selection_ids = [used[index]] if used[index] else []
            result.append({
                "query_id": f"arecel:forest10:test:{index:06d}",
                "source_index": index,
                "true_cardinality": 1,
                "qerror": error,
                "estimate_plan_rows": plan,
                "mcv_selection_ids": selection_ids,
                "mcv_estimate_ids": selection_ids,
                "mcv_events": ([{"candidate_id": selection_ids[0], "type": "mcv_selection"},
                                {"candidate_id": selection_ids[0], "type": "mcv_estimate"}]
                               if selection_ids else []),
                "configuration_id": config,
            })
        return result

    def test_fixed_workload_pair_counts_and_direction(self) -> None:
        n = 10_000
        all_errors = [1.0] * n
        b5_errors = [1.0] * n
        all_errors[0], b5_errors[0] = 1.0, 2.0  # ALL better
        all_errors[1], b5_errors[1] = 3.0, 2.0  # ALL worse
        all_plans = [1] * n
        b5_plans = [1] * n
        b5_plans[0] = 2
        all_use = [""] * n
        b5_use = [""] * n
        all_use[0] = "e02_08"
        all_use[2] = "e00_01"  # ALL-only candidate
        b5_use[1] = "e02_08"
        a = self.rows(runner.ALL_CONFIGS[0], all_errors, all_plans, all_use)
        b = self.rows(runner.B5_CONFIG, b5_errors, b5_plans, b5_use)
        c = self.rows(runner.ALL_CONFIGS[1], [1.0] * n, [1] * n, [""] * n)
        def metric(p95: float) -> dict:
            return {"qerror": {"p50": 1.0, "p95": p95, "p99": 1.0, "mean": 1.0}}

        comparison = runner._paired_comparison(a, b, c, metric(1.0), metric(1.0), metric(1.0))
        self.assertEqual(comparison["all_minus_b5_p95"], 0.0)
        self.assertEqual(comparison["plan_rows_changed_count"], 1)
        self.assertEqual(comparison["qerror_improved_for_all_count"], 1)
        self.assertEqual(comparison["qerror_degraded_for_all_count"], 1)
        self.assertEqual(comparison["qerror_unchanged_count"], n - 2)
        self.assertEqual(
            comparison["all_new_candidate_usage"][runner.ALL_CONFIGS[0]][
                "queries_with_any_new_candidate_estimated"],
            1,
        )

    def test_pairing_rejects_incomplete_or_mismatched_query_ids(self) -> None:
        a = self.rows(runner.ALL_CONFIGS[0], [1.0], [1], [""])
        b = self.rows(runner.B5_CONFIG, [1.0], [1], [""])
        c = self.rows(runner.ALL_CONFIGS[1], [1.0], [1], [""])
        with self.assertRaises(runner.Inconclusive):
            runner._paired_comparison(a, b, c, {}, {}, {})


if __name__ == "__main__":
    unittest.main()
