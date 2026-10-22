from __future__ import annotations

import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_forest10_full_valid_observations as verifier


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Forest10ObservationVerifierTests(unittest.TestCase):
    def _fixture(self, root: Path, *, corrupt_schedule: bool = False) -> tuple[dict, dict]:
        rows = [
            {"sequence": 1, "query_id": "q0", "config_id": "Empty", "static_eligible": None,
             "status": "SUCCESS", "diagnostics_status": "complete", "nrows_preclamp": "2.5",
             "relation_oid": 42, "mcv_diagnostics_status": "NO_MCV_EVENTS", "mcv_events": []},
            {"sequence": 2, "query_id": "q0", "config_id": "e00_01", "static_eligible": True,
             "status": "SUCCESS", "diagnostics_status": "complete", "nrows_preclamp": "3.5",
             "relation_oid": 42, "mcv_diagnostics_status": "VERIFIED",
             "mcv_events": [{"statistic_oid": 43, "clause_indexes": [0, 1]}]},
        ]
        if corrupt_schedule:
            rows[1]["query_id"] = "wrong"
        raw = b"".join((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode() for row in rows)
        member = gzip.compress(raw, compresslevel=6, mtime=0)
        obs = root / "observations"
        obs.mkdir()
        part_name = "observations-0001.jsonl.gz"
        (obs / part_name).write_bytes(member)
        manifest = {
            "format": "ess-issue64-forest10-json-full-collection-v1",
            "status": "SUCCESS", "completion": "ALL_174088_CALLS_AND_46_CONFIGURATIONS_COMPLETE",
            "truth_objective_selection_test_access": False,
            "expected_calls": 2, "attempted_calls": 2, "completed_calls": 2,
            "committed_observation_count": 2, "failed_calls": 0, "unattempted_calls": 0,
            "parts": [{"path": part_name, "compressed_bytes": len(member), "sha256": digest(member),
                       "first_sequence": 1, "last_sequence": 2}],
            "durable_blocks": [{"part": part_name, "byte_offset": 0, "compressed_bytes": len(member),
                                "gzip_member_sha256": digest(member), "uncompressed_sha256": digest(raw),
                                "rows": 2, "first_sequence": 1, "last_sequence": 2}],
        }
        (root / verifier.collector.MANIFEST).write_text(json.dumps(manifest))
        workload = {"dataset": "forest10", "split": "valid", "queries": []}
        discovery = {}
        return workload, discovery

    def test_checksums_order_and_outcome_free_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workload, discovery = self._fixture(root)
            with patch.object(verifier.collector, "build_schedule", return_value=(
                [{"query_id": "q0"}], [("e00_01", ("a", "b"))], {"e00_01": ("q0",)}
            )):
                result = verifier.verify(root, workload, discovery)
            self.assertEqual((result["status"], result["rows"], result["mcv_events"], result["no_mcv_events"]),
                             ("PASS", 2, 1, 1))

    def test_rejects_schedule_mismatch_and_modified_part(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workload, discovery = self._fixture(root, corrupt_schedule=True)
            schedule = ([{"query_id": "q0"}], [("e00_01", ("a", "b"))], {"e00_01": ("q0",)})
            with patch.object(verifier.collector, "build_schedule", return_value=schedule):
                with self.assertRaisesRegex(ValueError, "schedule/order mismatch"):
                    verifier.verify(root, workload, discovery)
            with patch.object(verifier.collector, "build_schedule", return_value=schedule):
                (root / "observations" / "observations-0001.jsonl.gz").write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "checksum/size mismatch"):
                    verifier.verify(root, workload, discovery)


if __name__ == "__main__":
    unittest.main()
