from decimal import Decimal

from app.services.economic_calendar.surprise_calculator import calculate, direction_of
from app.services.economic_calendar.types import SurpriseDirection


def test_calculate_returns_actual_minus_forecast() -> None:
    assert calculate(Decimal("2.8"), Decimal("3.2")) == Decimal("-0.4")


def test_calculate_returns_none_when_actual_missing() -> None:
    assert calculate(None, Decimal("3.2")) is None


def test_calculate_returns_none_when_forecast_missing() -> None:
    assert calculate(Decimal("2.8"), None) is None


def test_direction_of_higher_than_forecast() -> None:
    assert direction_of(Decimal("0.4")) == SurpriseDirection.HIGHER_THAN_FORECAST


def test_direction_of_lower_than_forecast() -> None:
    assert direction_of(Decimal("-0.4")) == SurpriseDirection.LOWER_THAN_FORECAST


def test_direction_of_in_line_when_zero() -> None:
    assert direction_of(Decimal("0")) == SurpriseDirection.IN_LINE


def test_direction_of_in_line_when_none() -> None:
    assert direction_of(None) == SurpriseDirection.IN_LINE
