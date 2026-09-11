from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import Recommendation, Timeframe
from app.services.ai_orchestrator.recommendation_decision import decide
from app.services.ai_orchestrator.types import CandidateSetup
from app.services.analysis_confidence.types import ConfidenceLevel, ConflictSeverity
from app.services.risk_management.types import (
    PositionGuidance,
    RiskEvaluation,
    RiskLevel,
    TradeDirection,
    TradeQualityBreakdown,
    TradeQualityTier,
)
from app.services.technical_analysis.types import TrendDirection
from tests.ai_orchestrator_helpers import make_analysis_context, make_confidence_result

_CALCULATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_LONG_CANDIDATE = CandidateSetup(
    direction=TradeDirection.LONG,
    entry_price=Decimal("100"),
    stop_loss=Decimal("95"),
    take_profit=Decimal("110"),
)


def _approved_risk() -> RiskEvaluation:
    return RiskEvaluation(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        direction=TradeDirection.LONG,
        approved=True,
        risk_level=RiskLevel.MEDIUM,
        tier=TradeQualityTier.GOOD,
        breakdown=TradeQualityBreakdown(
            trend_quality=17.0, technical=16.0, smc=15.0, risk=17.0, news=6.0, economic=10.0
        ),
        risk_reward=3.0,
        position_guidance=PositionGuidance.NORMAL,
        calculated_at=_CALCULATED_AT,
        rejected_reasons=[],
        warnings=[],
    )


def _rejected_risk(reasons: list[str]) -> RiskEvaluation:
    return replace(_approved_risk(), approved=False, rejected_reasons=reasons)


def test_decide_wait_when_no_candidate_setup() -> None:
    context = make_analysis_context(candidate_setup=None, risk=None)
    decision = decide(context)
    assert decision.recommendation is Recommendation.WAIT
    assert "No viable strategy" in decision.reasons[0]


def test_decide_wait_when_risk_rejects() -> None:
    risk = _rejected_risk(["Extreme volatility."])
    context = make_analysis_context(candidate_setup=_LONG_CANDIDATE, risk=risk)
    decision = decide(context)
    assert decision.recommendation is Recommendation.WAIT
    assert decision.reasons == ["Extreme volatility."]


def test_decide_wait_when_confidence_too_low() -> None:
    confidence = make_confidence_result(confidence_level=ConfidenceLevel.LOW)
    context = make_analysis_context(
        confidence=confidence, candidate_setup=_LONG_CANDIDATE, risk=_approved_risk()
    )
    decision = decide(context)
    assert decision.recommendation is Recommendation.WAIT
    assert "Confidence too low" in decision.reasons[0]


def test_decide_wait_when_conflict_severity_high() -> None:
    confidence = make_confidence_result(conflict_severity=ConflictSeverity.HIGH)
    context = make_analysis_context(
        confidence=confidence, candidate_setup=_LONG_CANDIDATE, risk=_approved_risk()
    )
    decision = decide(context)
    assert decision.recommendation is Recommendation.WAIT
    assert "Conflicting evidence" in decision.reasons[0]


def test_decide_buy_when_everything_favorable() -> None:
    context = make_analysis_context(candidate_setup=_LONG_CANDIDATE, risk=_approved_risk())
    decision = decide(context)
    assert decision.recommendation is Recommendation.BUY
    assert decision.reasons == []


def test_decide_wait_when_a_higher_timeframe_trends_against_the_setup() -> None:
    """ADR-166 - a BUY against a bearish daily trend is held back, and the
    reason names the timeframe that blocked it."""
    context = make_analysis_context(
        candidate_setup=_LONG_CANDIDATE,
        risk=_approved_risk(),
        higher_timeframes=[
            make_confidence_result(timeframe=Timeframe.H4, trend=TrendDirection.BULLISH),
            make_confidence_result(timeframe=Timeframe.D1, trend=TrendDirection.BEARISH),
        ],
    )

    decision = decide(context)

    assert decision.recommendation is Recommendation.WAIT
    assert "D1" in decision.reasons[0]
    assert "H4" not in decision.reasons[0]


def test_a_short_setup_is_blocked_by_a_bullish_higher_timeframe() -> None:
    short_candidate = CandidateSetup(
        direction=TradeDirection.SHORT,
        entry_price=Decimal("100"),
        stop_loss=Decimal("105"),
        take_profit=Decimal("90"),
    )
    context = make_analysis_context(
        candidate_setup=short_candidate,
        risk=replace(_approved_risk(), direction=TradeDirection.SHORT),
        higher_timeframes=[
            make_confidence_result(timeframe=Timeframe.H4, trend=TrendDirection.BULLISH)
        ],
    )

    assert decide(context).recommendation is Recommendation.WAIT


def test_a_sideways_higher_timeframe_does_not_block() -> None:
    """No trend is no objection - blocking on it would block almost always."""
    context = make_analysis_context(
        candidate_setup=_LONG_CANDIDATE,
        risk=_approved_risk(),
        higher_timeframes=[
            make_confidence_result(timeframe=Timeframe.D1, trend=TrendDirection.SIDEWAYS)
        ],
    )

    assert decide(context).recommendation is Recommendation.BUY


def test_a_higher_timeframe_without_data_does_not_block() -> None:
    """D1's history is still thin. Missing data is not evidence against a
    setup, and treating it as such would silence every signal."""
    context = make_analysis_context(
        candidate_setup=_LONG_CANDIDATE,
        risk=_approved_risk(),
        higher_timeframes=[
            make_confidence_result(
                timeframe=Timeframe.D1,
                trend=TrendDirection.BEARISH,
                include_technical=False,
            )
        ],
    )

    assert decide(context).recommendation is Recommendation.BUY


def test_decide_sell_for_short_candidate() -> None:
    short_candidate = CandidateSetup(
        direction=TradeDirection.SHORT,
        entry_price=Decimal("100"),
        stop_loss=Decimal("105"),
        take_profit=Decimal("90"),
    )
    risk = replace(_approved_risk(), direction=TradeDirection.SHORT)
    context = make_analysis_context(candidate_setup=short_candidate, risk=risk)
    decision = decide(context)
    assert decision.recommendation is Recommendation.SELL
