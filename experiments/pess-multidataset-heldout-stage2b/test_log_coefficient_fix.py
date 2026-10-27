from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest
from run_formal import rational_log


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", "0"),
        ("0.5", "-0.693147180559945309"),
        ("2", "0.693147180559945309"),
        ("1.000000000000000001", "0.000000000000000001"),
        ("0.999999999999999999", "-0.000000000000000001"),
    ],
)
def test_rational_log_uses_high_precision_decimal_ln(value: str, expected: str) -> None:
    assert rational_log(Decimal(value)) == Fraction(expected)


def test_rational_log_rejects_nonpositive_values() -> None:
    for value in (Decimal(0), Decimal(-1), Decimal("-0.001")):
        with pytest.raises(ValueError, match="finite positive"):
            rational_log(value)


def test_rational_log_rejects_nonfinite_values() -> None:
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ValueError, match="finite positive"):
            rational_log(value)
