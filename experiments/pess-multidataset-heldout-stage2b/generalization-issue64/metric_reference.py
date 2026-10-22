"""Exact small-domain Q-error reference functions for protocol regression tests."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from typing import Sequence


Q1_QUANTUM = Decimal("1e-50")
DECIMAL_PRECISION = 80


def q1(plan_rows: int, truth_rows: int) -> Fraction:
    """One-row-floor Q-error adaptation, valid for nonnegative integer counts."""
    if (
        isinstance(plan_rows, bool)
        or isinstance(truth_rows, bool)
        or not isinstance(plan_rows, int)
        or not isinstance(truth_rows, int)
        or plan_rows < 0
        or truth_rows < 0
    ):
        raise ValueError("Q1 requires nonnegative integer plan/truth row counts")
    return Fraction(max(plan_rows, truth_rows, 1), max(min(plan_rows, truth_rows), 1))


def natural_qerror(plan_rows: int, truth_rows: int) -> Fraction | None:
    """AreCEL's unmodified positive-domain Q-error; undefined if either count is zero."""
    if (
        isinstance(plan_rows, bool)
        or isinstance(truth_rows, bool)
        or not isinstance(plan_rows, int)
        or not isinstance(truth_rows, int)
        or plan_rows < 0
        or truth_rows < 0
    ):
        raise ValueError("natural Q-error requires nonnegative integer counts")
    if plan_rows == 0 or truth_rows == 0:
        return None
    return Fraction(max(plan_rows, truth_rows), min(plan_rows, truth_rows))


def _ln_fraction(value: Fraction) -> Decimal:
    if value <= 0:
        raise ValueError("log-Q1 requires a positive ratio")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        return decimal_value.ln()


def _quantize(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        return value.quantize(Q1_QUANTUM, rounding=ROUND_HALF_EVEN)


def per_query_log_q1(q1_replicates: Sequence[Fraction]) -> Decimal:
    if len(q1_replicates) != 2:
        raise ValueError("the frozen protocol requires exactly two held-out replicates")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        mean_log = sum((_ln_fraction(value) for value in q1_replicates), Decimal(0)) / 2
        return _quantize(mean_log)


def paired_log_q1_delta(
    pess_replicates: Sequence[Fraction], nominal_replicates: Sequence[Fraction]
) -> Decimal:
    if len(pess_replicates) != 2 or len(nominal_replicates) != 2:
        raise ValueError("paired comparison requires both methods in both replicates")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        deltas = [
            _ln_fraction(pess) - _ln_fraction(nominal)
            for pess, nominal in zip(pess_replicates, nominal_replicates, strict=True)
        ]
        return _quantize(sum(deltas, Decimal(0)) / 2)


def paired_classification(delta: Decimal) -> str:
    if not delta.is_finite():
        raise ValueError("paired log-Q1 delta must be finite")
    if delta < 0:
        return "benefit"
    if delta > 0:
        return "harm"
    return "tie"
