"""Offline checks for the frozen Issue #133 Forest10 two-order runner."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_minimal_forest10 as run


class FrozenOrderTests(unittest.TestCase):
    def test_protocol_and_both_orders_match_frozen_m0(self):
        protocol = run.read_protocol()
        inventory, first, second = run.verify_orders(protocol)
        self.assertEqual(inventory["datasets"]["forest10"]["candidate_count"], 45)
        self.assertEqual(len(first["permutation"]), 45)
        self.assertEqual(len(second["permutation"]), 45)
        self.assertNotEqual(first["permutation"], second["permutation"])

    def test_orders_have_same_complete_candidate_set(self):
        protocol = json.loads(run.PROTOCOL_PATH.read_text())
        inventory, first, second = run.verify_orders(protocol)
        candidate_ids = {row["id"] for row in inventory["datasets"]["forest10"]["candidates"]}
        self.assertEqual(set(first["permutation"]), candidate_ids)
        self.assertEqual(set(second["permutation"]), candidate_ids)


class PayloadStateTests(unittest.TestCase):
    def test_null_empty_and_populated_payload_states_are_distinct(self):
        self.assertEqual(run.payload_state({"mcv_payload_present": False, "mcv_item_count": 0}), "NULL")
        self.assertEqual(run.payload_state({"mcv_payload_present": True, "mcv_item_count": 0}), "PRESENT_EMPTY")
        self.assertEqual(run.payload_state({"mcv_payload_present": True, "mcv_item_count": 4}), "POPULATED")

    def test_null_payload_does_not_drop_a_valid_mcv_definition(self):
        row = {
            "attnames": None, "kinds": None, "stxkind": "{m}",
            "statistics_target": 300, "stxkeys": "1 2",
            "mcv_payload_present": False, "mcv_item_count": 0,
            "mcv_content_sha256": "fingerprint-of-null-payload-state",
        }
        run.validate_catalog_definition(row, {
            "id": "e00_01", "catalog_columns": ["elevation", "aspect"]
        })
        self.assertEqual(row["payload_state"], "NULL")
        self.assertEqual(row["resolved_attnames"], ["elevation", "aspect"])

    def test_arm_comparison_is_by_candidate_content_not_numeric_oid(self):
        row = {
            "candidate_id": "e00_01", "attnames": ["elevation", "aspect"],
            "kinds": ["m"], "stxkind": "{m}", "statistics_target": 300,
            "stxkeys": "1 2", "mcv_payload_present": True,
            "mcv_item_count": 3, "mcv_content_sha256": "same-payload",
        }
        a = {"table_logical_identity": {"row_count": 581012, "columns": []},
             "ordinary_column_stats": {"sha256": "ordinary"}, "sample_sha256": "sample",
             "sample_header": {"relation_oid": 1, "relation_identity": "6:public8:forest10",
                               "server_version": "16.14", "sample_target": 90000,
                               "tuple_count": 90000, "natts": 10, "relation_filenode": 111,
                               "relation_pages": 22}, "catalog": [row]}
        b = json.loads(json.dumps(a))
        b["catalog"][0]["oid"] = 90001
        b["sample_header"]["relation_filenode"] = 999
        b["sample_header"]["relation_pages"] = 99
        self.assertEqual(run.audit_signature(a), run.audit_signature(b))

    def test_live_arm_recheck_keeps_table_identity_separate_from_catalog_rows(self):
        candidate_id = "e00_01"
        row = {
            "statistic_name": "forest10_e00_01", "oid": 17000,
            "attnames": ["elevation", "aspect"], "kinds": ["m"],
            "stxkind": "{m}", "statistics_target": 300, "stxkeys": "1 2",
            "mcv_payload_present": True, "mcv_item_count": 2,
            "mcv_content_sha256": "payload",
        }
        table = {"row_count": 581012, "columns": [[1, "elevation", "integer"]]}
        ordinary = {"sha256": "ordinary"}
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.bin"
            sample.write_bytes(b"fixed sample")
            arm = {
                "create_statement_candidate_ids": [candidate_id],
                "catalog": [{**row, "candidate_id": candidate_id}],
                "table_logical_identity": table,
                "ordinary_column_stats": ordinary,
                "sample_sha256": run.sha256_file(sample),
            }
            candidates = {candidate_id: {"statistic_name": row["statistic_name"]}}
            with (patch.object(run.issue105, "query_catalog_audit", return_value=[row]),
                  patch.object(run.issue105, "table_identity", return_value=table),
                  patch.object(run.issue105, "ordinary_stats_audit", return_value=ordinary)):
                run.current_arm_state(arm, object(), Path(tmp), {}, candidates, sample)


if __name__ == "__main__":
    unittest.main()
