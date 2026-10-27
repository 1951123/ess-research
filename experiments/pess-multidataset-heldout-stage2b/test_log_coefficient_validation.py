from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from validate_log_coefficient_fix import (
    maximal_matchings,
    reference_rational_log,
    resource_sets,
)


def candidates() -> dict[str, dict[str, object]]:
    return {
        "e01": {"id": "e01", "source_columns": ["a", "b"]},
        "e12": {"id": "e12", "source_columns": ["b", "c"]},
        "e23": {"id": "e23", "source_columns": ["c", "d"]},
    }


def test_independent_log_reference_handles_all_ratio_strata() -> None:
    assert reference_rational_log(Decimal(1)) == Fraction("0")
    assert reference_rational_log(Decimal("0.5")) == Fraction("-0.693147180559945309")
    assert reference_rational_log(Decimal(2)) == Fraction("0.693147180559945309")
    assert reference_rational_log(Decimal("1.000000000000000001")) == Fraction(
        "0.000000000000000001"
    )


def test_independent_reference_rejects_nonpositive() -> None:
    for value in (Decimal(0), Decimal(-1)):
        try:
            reference_rational_log(value)
        except ValueError:
            pass
        else:
            raise AssertionError("nonpositive input was accepted")


def test_small_instance_enumerates_all_budget_sets_and_maximal_matchings() -> None:
    graph = candidates()
    assert len(resource_sets(list(graph), 0)) == 1
    assert len(resource_sets(list(graph), 2)) == 7
    assert maximal_matchings(list(graph), graph) == [("e01", "e23"), ("e12",)]
