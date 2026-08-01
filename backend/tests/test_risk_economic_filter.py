from datetime import UTC, datetime
from uuid import uuid4

from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus
from app.services.economic_calendar.types import EconomicEventEvidence
from app.services.risk_management.economic_filter import analyze

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _event(importance: EconomicEventImportance, *, risk_window: bool) -> EconomicEventEvidence:
    return EconomicEventEvidence(
        id=uuid4(),
        country="US",
        currency="USD",
        event_name="CPI y/y",
        category=EconomicEventCategory.INFLATION,
        importance=importance,
        forecast=None,
        previous=None,
        actual=None,
        surprise=None,
        unit="%",
        status=EconomicEventStatus.SCHEDULED,
        source="mock",
        release_time=_NOW,
        risk_window=risk_window,
        market_bias=None,
    )


def test_analyze_no_events_gives_full_score() -> None:
    result = analyze([])
    assert result.economic_score == 10.0
    assert result.hard_reject is False


def test_analyze_critical_in_window_hard_rejects() -> None:
    events = [_event(EconomicEventImportance.CRITICAL, risk_window=True)]
    result = analyze(events)
    assert result.hard_reject is True
    assert result.economic_score == 0.0
    assert result.reason is not None


def test_analyze_critical_outside_window_does_not_reject() -> None:
    events = [_event(EconomicEventImportance.CRITICAL, risk_window=False)]
    result = analyze(events)
    assert result.hard_reject is False


def test_analyze_high_in_window_caps_score() -> None:
    events = [_event(EconomicEventImportance.HIGH, risk_window=True)]
    result = analyze(events)
    assert result.hard_reject is False
    assert result.economic_score == 4.0


def test_analyze_medium_present_caps_score() -> None:
    events = [_event(EconomicEventImportance.MEDIUM, risk_window=False)]
    result = analyze(events)
    assert result.economic_score == 7.0


def test_analyze_low_importance_does_not_reduce_score() -> None:
    events = [_event(EconomicEventImportance.LOW, risk_window=False)]
    result = analyze(events)
    assert result.economic_score == 10.0
