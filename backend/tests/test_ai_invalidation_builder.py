from decimal import Decimal

from app.models.enums import Recommendation
from app.services.ai_orchestrator.invalidation_builder import build
from app.services.ai_orchestrator.types import CandidateSetup
from app.services.risk_management.types import TradeDirection
from tests.ai_orchestrator_helpers import make_analysis_context

_LONG_CANDIDATE = CandidateSetup(
    direction=TradeDirection.LONG,
    entry_price=Decimal("100"),
    stop_loss=Decimal("95"),
    take_profit=Decimal("110"),
)


def test_build_returns_empty_for_wait() -> None:
    context = make_analysis_context(candidate_setup=None)
    assert build(context, Recommendation.WAIT) == []


def test_build_includes_stop_loss_condition_for_long() -> None:
    context = make_analysis_context(candidate_setup=_LONG_CANDIDATE)
    conditions = build(context, Recommendation.BUY)
    assert any("closes below" in c and "95" in c for c in conditions)


def test_build_includes_opposing_regime_condition() -> None:
    context = make_analysis_context(candidate_setup=_LONG_CANDIDATE)
    conditions = build(context, Recommendation.BUY)
    assert any("regime shifts" in c for c in conditions)
