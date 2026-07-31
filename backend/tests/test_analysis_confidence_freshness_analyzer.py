from datetime import UTC, datetime, timedelta

from app.models.enums import Timeframe
from app.services.analysis_confidence import freshness_analyzer
from tests.analysis_confidence_helpers import make_technical_result

_NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


def test_fresh_result_within_threshold() -> None:
    technical = make_technical_result(calculated_at=_NOW - timedelta(minutes=30))

    result = freshness_analyzer.analyze(technical, None, None, Timeframe.H1, _NOW)

    assert result.is_stale is False
    assert result.freshness_score == freshness_analyzer.FRESHNESS_WEIGHT


def test_stale_result_beyond_threshold() -> None:
    technical = make_technical_result(calculated_at=_NOW - timedelta(hours=5))

    result = freshness_analyzer.analyze(technical, None, None, Timeframe.H1, _NOW)

    assert result.is_stale is True
    assert result.freshness_score < freshness_analyzer.FRESHNESS_WEIGHT


def test_exactly_at_threshold_boundary_is_not_stale() -> None:
    threshold = freshness_analyzer.STALENESS_THRESHOLDS[Timeframe.H1]
    technical = make_technical_result(calculated_at=_NOW - threshold)

    result = freshness_analyzer.analyze(technical, None, None, Timeframe.H1, _NOW)

    assert result.is_stale is False


def test_no_available_engines_has_zero_freshness_score() -> None:
    result = freshness_analyzer.analyze(None, None, None, Timeframe.H1, _NOW)

    assert result.freshness_score == 0.0
    assert result.is_stale is False


def test_every_timeframe_has_a_threshold() -> None:
    for timeframe in Timeframe:
        assert timeframe in freshness_analyzer.STALENESS_THRESHOLDS
