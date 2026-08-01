"""Deterministic surprise calculation (docs/14 §6, docs/47 §3). Stored
once `actual` is known - not recomputed live, since `forecast` may later
be superseded by a different event's forecast for the next release."""

from decimal import Decimal

from app.services.economic_calendar.types import SurpriseDirection


def calculate(actual: Decimal | None, forecast: Decimal | None) -> Decimal | None:
    """`actual - forecast`. `None` if either value is unavailable yet."""
    if actual is None or forecast is None:
        return None
    return actual - forecast


def direction_of(surprise: Decimal | None) -> SurpriseDirection:
    if surprise is None or surprise == 0:
        return SurpriseDirection.IN_LINE
    if surprise > 0:
        return SurpriseDirection.HIGHER_THAN_FORECAST
    return SurpriseDirection.LOWER_THAN_FORECAST
