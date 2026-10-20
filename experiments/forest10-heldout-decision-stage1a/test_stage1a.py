from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from analyze_heldout import metric
from run_heldout import parse_key_values


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
