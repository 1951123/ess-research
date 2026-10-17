"""Offline mutation tests for the strict numeric follow-up checker."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_mcv_numeric_followup as checker  # noqa: E402


RUN = Path(__file__).parent / "runs/20261017-numeric/review-followup-20261017"


def parsed() -> tuple[dict, dict, dict, dict]:
    return checker.parse_logs(
        (RUN / "psql.stdout.log").read_text(encoding="utf-8"),
        (RUN / "psql.stderr.log").read_text(encoding="utf-8"),
    )


def set_raw_observation(base: dict, plan_rows: dict, marker: str, selectivity: float) -> None:
    observation = base[marker][0]
    observation["selectivity_preclamp"] = selectivity
    observation["nrows_preclamp"] = observation["R"] * selectivity
    observation["rows_postclamp"] = float(checker.expected_plan_rows(observation["nrows_preclamp"]))
    plan_rows[marker] = [checker.expected_plan_rows(observation["nrows_preclamp"])]


def test_equal_correction_factors_are_rejected() -> None:
    base, mcv, catalog, metadata = parsed()
    base = copy.deepcopy(base)
    metadata = copy.deepcopy(metadata)

    singles = {
        name: checker.raw_sel(base[f"hetero_single_{name}"][0])
        for name in "abcd"
    }
    equal_factor = 2.0
    pairs = {
        "ab": equal_factor * singles["a"] * singles["b"],
        "bc": equal_factor * singles["b"] * singles["c"],
        "cd": equal_factor * singles["c"] * singles["d"],
    }
    for pair, value in pairs.items():
        set_raw_observation(base, metadata["plan_rows"], f"hetero_pair_{pair}", value)

    full_values = {
        "hetero_full_all": pairs["ab"] * pairs["cd"],
        "hetero_full_only_bc": pairs["bc"] * singles["a"] * singles["d"],
        "hetero_full_only_ab": pairs["ab"] * singles["c"] * singles["d"],
        "hetero_full_only_cd": pairs["cd"] * singles["a"] * singles["b"],
        "hetero_full_none": singles["a"] * singles["b"] * singles["c"] * singles["d"],
    }
    for marker, value in full_values.items():
        set_raw_observation(base, metadata["plan_rows"], marker, value)

    with pytest.raises(ValueError, match="materially different"):
        checker.check_fixture("hetero", base, mcv, catalog, metadata)


def test_explain_plan_rows_are_checked_independently() -> None:
    base, mcv, catalog, metadata = parsed()
    metadata = copy.deepcopy(metadata)
    metadata["plan_rows"]["hetero_full_all"] = [184]
    with pytest.raises(ValueError, match="EXPLAIN Plan Rows mismatch"):
        checker.check_fixture("hetero", base, mcv, catalog, metadata)


def test_missing_numeric_mcv_marker_is_rejected() -> None:
    base, mcv, catalog, metadata = parsed()
    mcv = copy.deepcopy(mcv)
    del mcv["hetero_pair_bc"]
    with pytest.raises(ValueError, match="numeric MCV marker set mismatch"):
        checker.check_fixture("hetero", base, mcv, catalog, metadata)


def test_duplicate_numeric_mcv_marker_is_rejected() -> None:
    base, mcv, catalog, metadata = parsed()
    mcv = copy.deepcopy(mcv)
    mcv["hetero_pair_bc"].append(copy.deepcopy(mcv["hetero_pair_bc"][0]))
    with pytest.raises(ValueError, match="expected 1 MCV numeric traces"):
        checker.check_fixture("hetero", base, mcv, catalog, metadata)

