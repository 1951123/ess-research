import unittest

from ess_research.arecel.candidates import discover_candidates


SCHEMA = ("a", "b", "c", "d")


def query(*predicates):
    return {"predicates": list(predicates)}


def predicate(column, operator="="):
    value = [0, 1] if operator == "[]" else 1
    return {"column": column, "operator": operator, "value": value}


class CandidateDiscoveryTests(unittest.TestCase):
    def test_single_predicate_has_no_candidate_pair(self):
        result = discover_candidates([query(predicate("a"))], SCHEMA)
        self.assertEqual(result["valid_query_count"], 1)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["candidates"], [])


    def test_two_predicates_count_the_unordered_pair_once(self):
        result = discover_candidates([query(predicate("b"), predicate("a"))], SCHEMA)
        self.assertEqual(
            result["candidates"],
            [{"column_a": "a", "column_b": "b", "eligible_valid_query_count": 1}],
        )


    def test_three_or_more_predicates_count_every_pair(self):
        result = discover_candidates(
            [query(predicate("a"), predicate("b"), predicate("c"))], SCHEMA
        )
        self.assertEqual(
            [(item["column_a"], item["column_b"]) for item in result["candidates"]],
            [("a", "b"), ("a", "c"), ("b", "c")],
        )


    def test_repeated_column_is_deduplicated_within_query(self):
        result = discover_candidates(
            [query(predicate("a"), predicate("a", ">="), predicate("b"))], SCHEMA
        )
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["eligible_valid_query_count"], 1)


    def test_unsupported_predicate_excludes_pairs_using_its_column_with_reason(self):
        result = discover_candidates(
            [
                {
                    "query_id": "q-unsupported",
                    "predicates": [predicate("a"), predicate("b", "~~"), predicate("c")],
                }
            ],
            SCHEMA,
        )
        self.assertEqual(
            result["candidates"],
            [{"column_a": "a", "column_b": "c", "eligible_valid_query_count": 1}],
        )
        self.assertEqual(
            result["cooccurring_pair_query_count_excluded_by_reason"],
            {"unsupported_operator": 2},
        )
        self.assertEqual(
            result["rejected_predicate_count_by_reason"], {"unsupported_operator": 1}
        )
        self.assertEqual(
            result["rejected_predicates"],
            [
                {
                    "query_id": "q-unsupported",
                    "predicate_index": 1,
                    "column": "b",
                    "operator": "~~",
                    "reason": "unsupported_operator",
                }
            ],
        )

    def test_non_string_operator_is_reported_as_unsupported(self):
        result = discover_candidates(
            [query(predicate("a"), {"column": "b", "operator": ["="], "value": 1})],
            SCHEMA,
        )
        self.assertEqual(
            result["rejected_predicates"][0]["reason"], "unsupported_operator"
        )


    def test_candidate_and_column_order_follow_source_schema(self):
        result = discover_candidates(
            [query(predicate("c"), predicate("a")), query(predicate("d"), predicate("b"))],
            ("d", "c", "b", "a"),
        )
        self.assertEqual(
            [(item["column_a"], item["column_b"]) for item in result["candidates"]],
            [("d", "b"), ("c", "a")],
        )


    def test_inclusive_range_uses_existing_supported_operator_contract(self):
        result = discover_candidates([query(predicate("a", "[]"), predicate("b"))], SCHEMA)
        self.assertEqual(result["candidate_count"], 1)


    def test_unknown_column_is_excluded_and_reported(self):
        result = discover_candidates([query(predicate("a"), predicate("x"))], SCHEMA)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(
            result["cooccurring_pair_query_count_excluded_by_reason"],
            {"unknown_column": 1},
        )


if __name__ == "__main__":
    unittest.main()
