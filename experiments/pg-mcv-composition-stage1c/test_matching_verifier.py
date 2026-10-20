import unittest

from matching_verifier import MatchingVerificationError, verify_maximal_matching


EDGES = [
    {"id": "e01", "columns": ["0", "1"]},
    {"id": "p01", "columns": ["0", "1"]},
    {"id": "e12", "columns": ["1", "2"]},
    {"id": "e23", "columns": ["2", "3"]},
    {"id": "e34", "columns": ["3", "4"]},
]


class MatchingVerifierTests(unittest.TestCase):
    def test_empty_graph_has_empty_maximal_matching(self):
        result = verify_maximal_matching(EDGES, [], [])
        self.assertTrue(result["is_inclusion_wise_maximal"])

    def test_path_choice_is_maximal_not_maximum_cardinality(self):
        result = verify_maximal_matching(EDGES, ["e12", "e23", "e34"], ["e12", "e34"])
        self.assertEqual(result["selected_ids"], ["e12", "e34"])

    def test_nonmaximal_set_is_rejected(self):
        with self.assertRaisesRegex(MatchingVerificationError, "not inclusion-wise maximal"):
            verify_maximal_matching(EDGES, ["e12", "e23", "e34"], ["e12"])

    def test_overlapping_selected_edges_are_rejected(self):
        with self.assertRaisesRegex(MatchingVerificationError, "not a matching"):
            verify_maximal_matching(EDGES, ["e12", "e23"], ["e12", "e23"])

    def test_parallel_labels_are_distinct_but_not_selectable_together(self):
        result = verify_maximal_matching(EDGES, ["e01", "p01"], ["p01"])
        self.assertEqual(result["selected_ids"], ["p01"])
        with self.assertRaisesRegex(MatchingVerificationError, "not a matching"):
            verify_maximal_matching(EDGES, ["e01", "p01"], ["e01", "p01"])


if __name__ == "__main__":
    unittest.main()

