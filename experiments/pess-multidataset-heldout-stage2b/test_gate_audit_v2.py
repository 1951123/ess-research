"""Offline contract tests for the archive-first Stage 2B Gate A verifier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from gate_audit_v2 import (
    audit_pg_binary,
    compute_overall_status,
    parse_schema_sql,
    write_exclusive_json,
)


HERE = Path(__file__).parent


class Stage2BGateAV2Tests(unittest.TestCase):
    def test_protocol_freezes_archive_first_crosswalk_and_truth_boundary(self) -> None:
        protocol = json.loads((HERE / "protocol-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "FROZEN_BEFORE_GATE_A_OUTCOME_COLLECTION_V2")
        self.assertEqual(protocol["etl_contract"]["archive_sha256"], "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79")
        self.assertFalse(protocol["scope"]["formal_heldout_outcomes_authorized"])
        forest = protocol["datasets"]["forest10"]
        self.assertEqual(forest["relation"], "public.forest10")
        self.assertEqual(forest["candidates"][0]["source_columns"], ["Elevation", "Aspect"])
        self.assertEqual(forest["candidates"][0]["catalog_columns"], ["elevation", "aspect"])
        self.assertTrue(protocol["fixed_sample_contract"]["old_issue38_sample_reuse"] is False)

    def test_schema_parser_preserves_catalog_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "schema.sql"
            path.write_text(
                'CREATE TABLE public.census13 (\n  "age" DOUBLE PRECISION,\n  "workclass" VARCHAR(64)\n);\n',
                encoding="utf-8",
            )
            self.assertEqual(parse_schema_sql(path), {"age": "DOUBLE PRECISION", "workclass": "VARCHAR(64)"})

    def test_readiness_is_fail_closed_until_all_verified(self) -> None:
        inputs = [{"status": "VERIFIED"}, {"status": "VERIFIED"}]
        source = {"status": "VERIFIED"}
        binary = {"status": "VERIFIED"}
        probes = [{"status": "VERIFIED"}, {"status": "BLOCKED"}]
        self.assertEqual(compute_overall_status(inputs, source, binary, probes), "BLOCKED")
        self.assertEqual(
            compute_overall_status(inputs, source, binary, [{"status": "VERIFIED"}, {"status": "VERIFIED"}]),
            "GATE_A_READY",
        )

    def test_missing_or_wrong_binary_manifest_cannot_pass(self) -> None:
        self.assertEqual(audit_pg_binary(None, None)["status"], "BLOCKED")
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.json"
            manifest.write_text(json.dumps({"pg_source_commit": "wrong", "pg_source_worktree_clean": True}), encoding="utf-8")
            self.assertEqual(audit_pg_binary(Path(temporary), manifest)["status"], "INCOMPATIBLE")

    def test_evidence_write_is_exclusive_and_does_not_follow_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "result.json"
            write_exclusive_json(output, {"value": 1})
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                write_exclusive_json(output, {"value": 2})
            self.assertEqual(output.read_bytes(), original)

            dangling = root / "dangling.json"
            os.symlink(root / "missing.json", dangling)
            with self.assertRaises(FileExistsError):
                write_exclusive_json(dangling, {"value": 3})
            self.assertTrue(dangling.is_symlink())


if __name__ == "__main__":
    unittest.main()
