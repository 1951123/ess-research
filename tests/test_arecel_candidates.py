import io
import pickle
import tarfile
import tempfile
import unittest
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from ess_research.arecel import archive as arecel_archive
from ess_research.arecel.candidates import _run, discover_candidates


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

    def test_any_unsupported_predicate_excludes_that_column_for_the_query(self):
        result = discover_candidates(
            [query(predicate("a"), predicate("a", "~~"), predicate("b"))], SCHEMA
        )
        self.assertEqual(result["candidates"], [])
        self.assertEqual(
            result["cooccurring_pair_query_count_excluded_by_reason"],
            {"unsupported_operator": 1},
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

    def test_entrypoint_prepares_valid_workload_without_loading_label_pickle(self):
        source_columns, _schema, _relation = arecel_archive._schema("forest10")
        source_query = arecel_archive.Query(
            OrderedDict(
                (column, ("=", 1.0)) for column in source_columns[:2]
            ),
            2,
        )
        workload_bytes = pickle.dumps({"valid": [source_query]})
        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode="w:gz") as archive:
            for name, payload in (
                ("data/forest10/workload/base.pkl", workload_bytes),
                # Any attempt to deserialize labels fails this test.
                ("data/forest10/workload/base-original-label.pkl", b"not a pickle"),
            ):
                member = tarfile.TarInfo(name)
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

        @contextmanager
        def verified_archive(_cache):
            yield io.BytesIO(tar_bytes.getvalue())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configured = {
                "ESS_DATA_ROOT": root / "cache",
                "ESS_RUNTIME_PARENT": root / "runtime",
            }
            with (
                patch.object(
                    arecel_archive,
                    "configured_root",
                    side_effect=lambda name: configured[name],
                ),
                patch.object(
                    arecel_archive,
                    "runtime_runs",
                    return_value=root / "runtime" / "runs",
                ),
                patch.object(arecel_archive, "_archive", side_effect=verified_archive),
            ):
                result = _run("forest10")

        self.assertEqual(result["valid_query_count"], 1)
        self.assertEqual(result["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
