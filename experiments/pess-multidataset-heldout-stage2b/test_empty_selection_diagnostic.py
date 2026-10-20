from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from empty_selection_diagnostic import (
    maximal_matchings,
    model_loss,
    nominal_matching,
    quantized_fraction,
)


def graph() -> dict[str, dict[str, object]]:
    return {
        "e01": {"id": "e01", "source_columns": ["a", "b"]},
        "e12": {"id": "e12", "source_columns": ["b", "c"]},
        "e23": {"id": "e23", "source_columns": ["c", "d"]},
    }


def test_maximal_matching_enumeration_keeps_distinct_maximal_matchings() -> None:
    candidates = graph()
    matchings = maximal_matchings(["e01", "e12", "e23"], candidates)
    assert matchings == [("e01", "e23"), ("e12",)]
    assert nominal_matching(["e01", "e12", "e23"], candidates) == ("e01", "e23")


def test_recorded_v4_arithmetic_is_raw_ratio_not_log() -> None:
    assert quantized_fraction(Decimal("0.5")) == Fraction("1/2")


def test_model_loss_distinguishes_nominal_and_pess() -> None:
    candidates = graph()
    task = {
        "alpha": "-1",
        "b": {"e01": "1", "e12": "2", "e23": "0"},
        "available_edges": ["e01", "e12", "e23"],
    }
    assert model_loss(task, ("e01", "e12", "e23"), "Nominal", candidates) == Fraction(0)
    assert model_loss(task, ("e01", "e12", "e23"), "PESS", candidates) == Fraction(1)


def test_empty_loss_is_independent_of_selected_resource_set() -> None:
    candidates = graph()
    task = {
        "alpha": "3",
        "b": {"e01": "4", "e12": "5", "e23": "6"},
        "available_edges": ["e01", "e12", "e23"],
    }
    assert model_loss(task, (), "Empty", candidates) == Fraction(3)
    assert model_loss(task, ("e01", "e23"), "Empty", candidates) == Fraction(3)
