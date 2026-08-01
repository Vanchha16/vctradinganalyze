"""Deterministic invalidation-condition templates (docs/50 §6). Never
LLM-generated - built from already-known facts on the `AnalysisContext`
and the candidate setup."""

from app.models.enums import EconomicEventImportance, Recommendation
from app.services.economic_calendar.types import EconomicEventEvidence
from app.services.market_regime.types import MarketRegimeState
from app.services.risk_management.types import TradeDirection

from .types import AnalysisContext

_OPPOSING_REGIME: dict[MarketRegimeState, MarketRegimeState] = {
    MarketRegimeState.TRENDING_BULLISH: MarketRegimeState.TRENDING_BEARISH,
    MarketRegimeState.TRENDING_BEARISH: MarketRegimeState.TRENDING_BULLISH,
    MarketRegimeState.ACCUMULATION: MarketRegimeState.DISTRIBUTION,
    MarketRegimeState.DISTRIBUTION: MarketRegimeState.ACCUMULATION,
}


def build(context: AnalysisContext, recommendation: Recommendation) -> list[str]:
    if recommendation is Recommendation.WAIT or context.candidate_setup is None:
        return []

    conditions: list[str] = []
    setup = context.candidate_setup
    side = "closes below" if setup.direction is TradeDirection.LONG else "closes above"
    conditions.append(f"Price {side} the stop-loss level of {setup.stop_loss}.")

    if context.confidence.market_regime is not None:
        current_regime = context.confidence.market_regime.regime
        opposing = _OPPOSING_REGIME.get(current_regime)
        if opposing is not None:
            conditions.append(
                f"Market regime shifts from {current_regime.value} to {opposing.value}."
            )

    critical_events = _upcoming_critical_events(context.economic.events)
    for event in critical_events:
        conditions.append(
            f"{event.event_name} ({event.currency}) enters its risk window before the trade "
            "is closed."
        )

    return conditions


def _upcoming_critical_events(events: list[EconomicEventEvidence]) -> list[EconomicEventEvidence]:
    return [
        e for e in events if e.importance is EconomicEventImportance.CRITICAL and not e.risk_window
    ]
