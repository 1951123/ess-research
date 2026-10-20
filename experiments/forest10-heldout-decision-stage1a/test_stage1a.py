from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from analyze_heldout import metric, query_level_paired_delta
from run_heldout import (
    parse_key_values,
    prepare_fresh_output_dir,
    selected_resource_ids_from_trace,
)


def test_frozen_protocol_retains_all_distinct_issue23_sets_and_quotas() -> None:
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    selected = protocol["heldout_selection"]["selected"]
    assert len(selected) == 60
    assert all(len(protocol["heldout_selection"]["quota_winners_by_candidate"][candidate]) == 10 for candidate in ("e01", "e12", "e23", "e34", "e45", "e56"))
    frozen_sets = protocol["reference_issue23"]["frozen_selection_sets"]["all_distinct_selected_sets"]
    assert len(frozen_sets) == 10
    assert protocol["reference_issue23"]["frozen_selection_sets"]["greedy"]["included"] is False


def test_trace_key_parser_preserves_numeric_fields() -> None:
    parsed = parse_key_values(
        "relid=16384 selected_stat_oid=16400 stat_sel=0.125 query=EXPLAIN"
    )
    assert parsed["relid"] == "16384"
    assert parsed["selected_stat_oid"] == "16400"
    assert parsed["stat_sel"] == "0.125"


def test_metric_uses_nearest_rank_ceiling_for_p90() -> None:
    result = metric([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert result["count"] == 10
    assert result["median"] == "5.5"
    assert result["p90_nearest_rank_ceiling"] == "9.000000"


def test_runner_refuses_existing_evidence_directory(tmp_path: Path) -> None:
    output = tmp_path / "existing-run"
    output.mkdir()
    (output / "measurements.jsonl").write_text("historical\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="existing output path"):
        prepare_fresh_output_dir(output)


def test_unknown_selected_oid_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="absent from the catalog identity ledger"):
        selected_resource_ids_from_trace(["16400", "16499"], {"16400": "ess_forest10_e01"})


def test_query_level_pairing_averages_repetitions() -> None:
    rows = [
        {"query_id": "q1", "repetition": 0, "absolute_log_error": "3"},
        {"query_id": "q1", "repetition": 1, "absolute_log_error": "5"},
        {"query_id": "q2", "repetition": 0, "absolute_log_error": "7"},
        {"query_id": "q2", "repetition": 1, "absolute_log_error": "9"},
    ]
    baseline = [
        {"query_id": "q1", "repetition": 0, "absolute_log_error": "4"},
        {"query_id": "q1", "repetition": 1, "absolute_log_error": "4"},
        {"query_id": "q2", "repetition": 0, "absolute_log_error": "8"},
        {"query_id": "q2", "repetition": 1, "absolute_log_error": "8"},
    ]
    result = query_level_paired_delta(rows, baseline, "absolute_log_error")
    assert result["independent_query_count"] == 2
    assert result["delta_abs_log_error"]["mean"] == "0"
    assert result["delta_abs_log_error"]["tie_zero_delta"] == 2
    assert result["within_query_repeat_delta_spread"]["max"] == "2"
