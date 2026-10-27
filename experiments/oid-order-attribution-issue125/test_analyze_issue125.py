from __future__ import annotations

import unittest

import numpy as np

from analyze_issue125 import (
    OrderData,
    compare_pair,
    numeric_estimate_signature,
    require_complete_order_record,
    select_anchor_orders,
    top_query_ids,
    validate_mcv_row,
)


def order_data(name, errors, selections, estimates, values=None):
    if values is None:
        values = [tuple() for _ in errors]
    return OrderData(
        record={"configuration_id": name},
        qerrors=np.asarray(errors, dtype=np.float64),
        selection_sequences=list(selections),
        estimate_sequences=list(estimates),
        estimate_values=list(values),
        estimate_value_signatures=[numeric_estimate_signature(value) for value in values],
    )


class Issue125HelpersTests(unittest.TestCase):
    def test_incomplete_configuration_is_not_accepted_as_an_order_sample(self):
        complete = {"status": "COMPLETE", "configuration_id": "complete"}
        self.assertIs(require_complete_order_record(complete, "complete"), complete)
        with self.assertRaisesRegex(ValueError, "configuration is incomplete"):
            require_complete_order_record({"status": "CONFIGURATION_INVALID"}, "incomplete")

    def test_nominal_certainty_orders_are_separate_from_random_comparisons(self):
        canonical = {"selection": "fixed", "permutation": ["a", "b"]}
        reverse = {"selection": "fixed", "permutation": ["b", "a"]}
        sample = [
            {"selection": "srswor", "permutation": ["a", "c"], "draw_index": 0},
            {"selection": "srswor", "permutation": ["b", "c"], "draw_index": 1},
        ]
        anchor, compared, _ = select_anchor_orders({
            "policy": "nominal", "resource_ids": ["a", "b"],
            "permutations": [canonical, reverse, *sample],
        })
        self.assertIs(anchor, canonical)
        self.assertEqual(compared, sample)

    def test_pess_sample_and_census_anchors_are_deterministic(self):
        first = {"selection": "srswor", "permutation": ["b", "a"], "draw_index": 0}
        second = {"selection": "srswor", "permutation": ["a", "b"], "draw_index": 1}
        anchor, compared, kind = select_anchor_orders({
            "policy": "pess", "resource_ids": ["a", "b"], "permutations": [first, second],
        })
        self.assertIs(anchor, first)
        self.assertEqual(compared, [second])
        self.assertIn("descriptive anchor", kind)

        census = [
            {"selection": "enumerated", "permutation": ["b", "a"]},
            {"selection": "enumerated", "permutation": ["a", "b"]},
        ]
        anchor, compared, kind = select_anchor_orders({
            "policy": "pess", "resource_ids": ["a", "b"], "permutations": census,
        })
        self.assertIs(anchor, census[1])
        self.assertEqual(compared, [census[0]])
        self.assertIn("fully enumerated", kind)

    def test_pair_counts_sequence_counterexamples_and_threshold_ties(self):
        baseline_errors = [1.0] * 20
        changed_errors = [1.0] * 18 + [2.0, 3.0]
        baseline_seq = [("a",)] * 20
        changed_seq = list(baseline_seq)
        changed_seq[0] = ("b",)
        changed_seq[19] = ("b",)
        changed_estimates = list(baseline_seq)
        changed_estimates[0] = ("b",)
        changed_values = [tuple() for _ in range(20)]
        changed_values[2] = (("a", (0.1, 0.2, None, None, 0.2)),)
        result = compare_pair(
            order_data("anchor", baseline_errors, baseline_seq, baseline_seq),
            order_data("other", changed_errors, changed_seq, changed_estimates, changed_values),
            "synthetic",
        )
        self.assertEqual(result["qerror_direction_counts"], {"lower": 0, "higher": 2, "tie": 18})
        self.assertEqual(result["id_sequence_changed_qerror_tie_count"], 1)
        self.assertEqual(result["id_sequence_changed_qerror_changed_count"], 1)
        self.assertEqual(result["id_sequence_same_qerror_changed_count"], 1)
        self.assertEqual(result["estimate_values_changed_count"], 1)
        self.assertEqual(result["tail_entered_count"], 0)
        self.assertEqual(result["tail_exited_count"], 19)
        self.assertEqual(result["examples"]["sequence_changed_qerror_tie"]["query_id"],
                         "arecel:synthetic:test:000000")
        self.assertEqual(result["examples"]["sequence_same_qerror_changed"]["query_id"],
                         "arecel:synthetic:test:000018")

    def test_mcv_events_are_joined_by_candidate_identity_not_oid_position(self):
        row = {
            "diagnostics_status": "complete",
            "diagnostics_event_count": 2,
            "mcv_events": [
                {"sequence": 1, "type": "mcv_selection", "stat_oid": 42,
                 "candidate_id": "edge_a", "key_count": 2},
                {"sequence": 2, "type": "mcv_estimate", "stat_oid": 42,
                 "candidate_id": "edge_a", "simple_sel": 0.1, "mcv_sel": 0.2},
            ],
            "mcv_selection_ids": ["edge_a"],
            "mcv_estimate_ids": ["edge_a"],
        }
        self.assertEqual(validate_mcv_row(row, {42: "edge_a"}, {"edge_a"}, "synthetic")[:2],
                         (("edge_a",), ("edge_a",)))
        with self.assertRaises(ValueError):
            validate_mcv_row(row, {43: "edge_a"}, {"edge_a"}, "synthetic")

    def test_query_frequency_ties_sort_by_query_index(self):
        self.assertEqual(
            top_query_ids({7: 2, 3: 2, 5: 1}, "synthetic", limit=2),
            [
                {"query_id": "arecel:synthetic:test:000003", "order_pair_count": 2},
                {"query_id": "arecel:synthetic:test:000007", "order_pair_count": 2},
            ],
        )

    def test_numeric_estimate_signature_ignores_event_order_but_not_values(self):
        first = (("edge_a", (0.1, 0.2, None, 1.0, 0.2)),
                 ("edge_b", (0.3, 0.4, None, 1.0, 0.4)))
        reordered = tuple(reversed(first))
        changed = (("edge_a", (0.1, 0.25, None, 1.0, 0.25)), first[1])
        self.assertEqual(numeric_estimate_signature(first), numeric_estimate_signature(reordered))
        self.assertNotEqual(numeric_estimate_signature(first), numeric_estimate_signature(changed))


if __name__ == "__main__":
    unittest.main()
