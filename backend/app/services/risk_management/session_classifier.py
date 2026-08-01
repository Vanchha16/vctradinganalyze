"""Deterministic market-session classification (docs/12 §5, docs/48 §5).
Weekend closure is checked before the UTC hour bands, approximating real
forex market hours (Friday 22:00 UTC - Sunday 22:00 UTC) since this
project has no holiday-calendar data source (ADR-066)."""

from datetime import datetime

from app.services.risk_management.types import MarketSession

_FRIDAY = 4
_SATURDAY = 5
_SUNDAY = 6
_WEEKEND_REOPEN_HOUR = 22


def classify(now: datetime) -> MarketSession:
    weekday = now.weekday()
    hour = now.hour

    if weekday == _SATURDAY:
        return MarketSession.CLOSED
    if weekday == _SUNDAY and hour < _WEEKEND_REOPEN_HOUR:
        return MarketSession.CLOSED
    if weekday == _FRIDAY and hour >= _WEEKEND_REOPEN_HOUR:
        return MarketSession.CLOSED

    if 13 <= hour < 17:
        return MarketSession.LONDON_NEW_YORK_OVERLAP
    if 8 <= hour < 17:
        return MarketSession.LONDON
    if 13 <= hour < 22:
        return MarketSession.NEW_YORK
    if 0 <= hour < 9:
        return MarketSession.ASIAN
    if hour >= 22 or hour < 7:
        return MarketSession.SYDNEY
    return MarketSession.CLOSED
