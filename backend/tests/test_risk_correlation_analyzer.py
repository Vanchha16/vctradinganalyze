from decimal import Decimal

import pytest

from app.services.risk_management.correlation_analyzer import (
    counterparts_for,
    is_highly_correlated,
    pearson_correlation,
)


def test_counterparts_for_known_symbol() -> None:
    assert counterparts_for("EURUSD") == ("GBPUSD",)
    assert counterparts_for("eurusd") == ("GBPUSD",)


def test_counterparts_for_unknown_symbol_is_empty() -> None:
    assert counterparts_for("USDCAD") == ()


def test_pearson_correlation_perfectly_correlated_series() -> None:
    a = [Decimal(v) for v in ["1.00", "1.01", "1.02", "1.03", "1.04", "1.05"]]
    b = [Decimal(v) for v in ["2.00", "2.02", "2.04", "2.06", "2.08", "2.10"]]
    correlation = pearson_correlation(a, b)
    assert correlation is not None
    assert correlation == 1.0


def test_pearson_correlation_perfectly_anti_correlated_returns() -> None:
    """`b`'s returns are constructed as the exact negation of `a`'s
    returns (not just a visually-decreasing series, which doesn't
    guarantee anti-correlated *returns*)."""
    a = [Decimal(v) for v in ["1.0", "1.010", "0.98980", "1.00464700", "0.9946005300"]]
    b = [Decimal(v) for v in ["2.0", "1.980", "2.01960", "1.98930600", "2.0091990600"]]
    correlation = pearson_correlation(a, b)
    assert correlation is not None
    assert correlation == pytest.approx(-1.0)


def test_pearson_correlation_none_for_too_short_series() -> None:
    assert pearson_correlation([Decimal("1.0")], [Decimal("1.0")]) is None


def test_pearson_correlation_none_for_zero_variance() -> None:
    a = [Decimal("1.0")] * 5
    b = [Decimal(v) for v in ["1.00", "1.01", "1.02", "1.03", "1.04"]]
    assert pearson_correlation(a, b) is None


def test_is_highly_correlated_above_threshold() -> None:
    assert is_highly_correlated(0.9) is True
    assert is_highly_correlated(-0.9) is True


def test_is_highly_correlated_below_threshold() -> None:
    assert is_highly_correlated(0.5) is False
    assert is_highly_correlated(None) is False
