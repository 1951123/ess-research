from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent


def test_protocol_is_frozen_before_outcomes_and_has_required_cohorts() -> None:
    protocol = json.loads((HERE / "protocol-v4.json").read_text(encoding="utf-8"))
    assert protocol["status"] == "FROZEN_BEFORE_HELDOUT_OUTCOME_COLLECTION_V4"
    assert protocol["independence_contract"]["test_truth_values_read_before_this_freeze"] is False
    assert protocol["independence_contract"]["stage1a_forest10_ids_excluded"] is True
    assert set(protocol["measurement_contract"]["methods"]) == {"Empty", "Nominal", "PESS"}
    assert protocol["measurement_contract"]["budgets_proxy_units"] == [0, 2, 3, 5]
    assert {dataset: len(spec["test_cohort"]["records"]) for dataset, spec in protocol["datasets"].items()} == {
        "forest10": 60,
        "census13": 52,
    }


def test_protocol_has_no_test_truth_or_outcome_fields() -> None:
    protocol = json.loads((HERE / "protocol-v4.json").read_text(encoding="utf-8"))
    for spec in protocol["datasets"].values():
        for record in spec["test_cohort"]["records"]:
            assert "truth_N" not in record
            assert "true_cardinality" not in record
            assert "estimate" not in record
            assert "absolute_log_error" not in record
    serialized = json.dumps(protocol, sort_keys=True)
    assert "heldout-summary" not in serialized
    assert "measurements.jsonl" not in serialized


def test_stage1a_forest_ids_are_not_selected() -> None:
    old = json.loads((HERE.parent / "forest10-heldout-decision-stage1a" / "protocol.json").read_text())
    old_ids = {item["query_id"] for item in old["heldout_selection"]["selected"]}
    new_ids = {item["query_id"] for item in json.loads((HERE / "protocol-v4.json").read_text())["datasets"]["forest10"]["test_cohort"]["records"]}
    assert len(old_ids) == 60
    assert old_ids.isdisjoint(new_ids)


def test_fingerprint_overlap_is_reported_not_silently_dropped() -> None:
    protocol = json.loads((HERE / "protocol-v4.json").read_text(encoding="utf-8"))
    for spec in protocol["datasets"].values():
        audit = spec["cross_split_fingerprint_audit"]["strict_pairwise_queries"]
        assert audit["template"]["shared_group_count"] > 0
        assert "interpretation" in spec["cross_split_fingerprint_audit"]
