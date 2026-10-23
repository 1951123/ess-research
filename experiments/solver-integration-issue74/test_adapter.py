from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adapter


class AdapterUnitTests(unittest.TestCase):
    def test_candidate_ids_map_to_frozen_schema_columns(self) -> None:
        self.assertEqual(adapter._edge_endpoints("e00_01", adapter.FOREST_COLUMNS),
                         ["Elevation", "Aspect"])
        self.assertEqual(adapter._edge_endpoints("e08_09", adapter.FOREST_COLUMNS),
                         ["Hillshade_3pm", "Horizontal_Distance_To_Fire_Points"])

    def test_candidate_id_rejects_bad_or_out_of_range_indices(self) -> None:
        for value in ("e1_02", "e02_02", "e00_10", "x00_01"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                adapter._edge_endpoints(value, adapter.FOREST_COLUMNS)

    def test_task_keeps_sparse_exact_corrections(self) -> None:
        row = adapter._task("q", "-1/3", {"e00_01": "0", "e01_02": "1/2"}, "t")
        self.assertEqual(row["eligible_candidates"], ["e00_01", "e01_02"])
        self.assertEqual(row["corrections"], {"e00_01": "0", "e01_02": "1/2"})

    def test_payload_uses_schema_v1_and_fixed_nominal_order(self) -> None:
        request = {
            "schema_version": "1", "objective": "pess", "backend": "master_oracle",
            "input_provenance": {"advisor_source_commit": adapter.ADVISOR_COMMIT},
            "instance": {"budget": "2", "candidates": [], "tasks": []},
            "_nominal_priority_order": ["b", "a"], "_frozen_selection": {},
        }
        payload = adapter.advisor_request_payload(request, "nominal")
        self.assertEqual(payload["priority_order"], ["b", "a"])
        self.assertNotIn("_frozen_selection", payload)
        self.assertNotIn("backend", payload)


if __name__ == "__main__":
    unittest.main()
