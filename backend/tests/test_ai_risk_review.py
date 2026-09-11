"""AI risk review (ADR-167).

What must hold: the review runs only on BUY/SELL and only when switched on;
in shadow mode a veto changes nothing; in enforce mode a veto turns the
trade into WAIT - and nothing can turn WAIT into a trade; a failed or
malformed review blocks nothing in any mode; and the parser accepts only a
verdict with reasons, never a price or direction.
"""

import json
from collections.abc import Generator
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, Timeframe
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.services.ai_orchestrator import risk_review
from app.services.ai_orchestrator.providers.exceptions import MalformedAIResponseError
from app.services.ai_orchestrator.providers.mock import MockAIProvider
from app.services.ai_orchestrator.risk_review import RiskReviewMode, RiskReviewVerdict
from app.services.ai_orchestrator.types import AnalysisContext, CandidateSetup
from app.services.ai_orchestrator_engine import AIOrchestratorEngine
from app.services.risk_management.types import TradeDirection
from tests.ai_orchestrator_helpers import make_analysis_context

_VETO = json.dumps(
    {
        "verdict": "veto",
        "reasons": ["D1 trend runs against the long.", "CPI releases in 2 hours."],
        "key_risk": "CPI in 2 hours can gap price through the stop.",
    }
)

_LONG = CandidateSetup(
    direction=TradeDirection.LONG,
    entry_price=Decimal("100"),
    stop_loss=Decimal("95"),
    take_profit=Decimal("110"),
)


# --- Parser -----------------------------------------------------------------


def test_parse_reads_a_verdict_with_reasons() -> None:
    verdict, reasons, key_risk = risk_review.parse(_VETO)

    assert verdict is RiskReviewVerdict.VETO
    assert len(reasons) == 2
    assert key_risk.startswith("CPI in 2 hours")


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        json.dumps(["veto"]),
        json.dumps({"verdict": "buy", "reasons": ["x"], "key_risk": "y"}),
        json.dumps({"verdict": "veto", "reasons": [], "key_risk": "y"}),
        json.dumps({"verdict": "veto", "reasons": "x", "key_risk": "y"}),
        json.dumps({"verdict": "approve", "reasons": ["x"], "key_risk": ""}),
    ],
)
def test_parse_rejects_anything_but_a_reasoned_verdict(payload: str) -> None:
    """"buy" is not a verdict - the review may never propose a trade."""
    with pytest.raises(MalformedAIResponseError):
        risk_review.parse(payload)


def test_parse_caps_reasons_at_four() -> None:
    payload = json.dumps(
        {"verdict": "approve", "reasons": [f"reason {i}" for i in range(7)], "key_risk": "y"}
    )

    _, reasons, _ = risk_review.parse(payload)

    assert len(reasons) == 4


# --- Engine -----------------------------------------------------------------


class _FixedContextBuilder:
    def __init__(self, context: AnalysisContext) -> None:
        self._context = context

    def build(
        self, asset: Asset, timeframe: Timeframe, focus_event_id: UUID | None = None
    ) -> AnalysisContext:
        return self._context


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Asset.__table__, AIAnalysis.__table__])
    with Session(engine) as session:
        yield session


@pytest.fixture
def asset(session: Session) -> Asset:
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _engine(
    session: Session, provider: MockAIProvider, *, candidate: CandidateSetup | None = _LONG
) -> AIOrchestratorEngine:
    return AIOrchestratorEngine(
        context_builder=_FixedContextBuilder(make_analysis_context(candidate_setup=candidate)),  # type: ignore[arg-type]
        provider=provider,
        ai_analysis_repository=AIAnalysisRepository(session),
    )


def _review_calls(provider: MockAIProvider) -> int:
    return sum(1 for call in provider.calls if "verdict" in call.json_schema.get("properties", {}))  # type: ignore[operator]


def test_shadow_veto_is_recorded_and_changes_nothing(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ai_risk_review_mode", "shadow")
    provider = MockAIProvider(review_content=_VETO)

    result = _engine(session, provider).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.BUY
    assert result.risk_review is not None
    assert result.risk_review.verdict is RiskReviewVerdict.VETO
    assert result.risk_review.mode is RiskReviewMode.SHADOW
    row = session.get(AIAnalysis, result.id)
    assert row is not None
    assert row.risk_review_verdict == "veto"
    assert row.risk_review_mode == "shadow"
    assert row.risk_review_reasons == [
        "D1 trend runs against the long.",
        "CPI releases in 2 hours.",
    ]


def test_enforced_veto_turns_the_trade_into_wait(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    """And the explanation is written for the WAIT, naming the veto."""
    monkeypatch.setattr(settings, "ai_risk_review_mode", "enforce")
    provider = MockAIProvider(review_content=_VETO)

    result = _engine(session, provider).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.WAIT
    narration_prompt = provider.calls[-1].user_prompt
    assert "Decided recommendation: WAIT" in narration_prompt
    assert "AI risk review vetoed the setup" in narration_prompt


def test_enforced_approval_keeps_the_trade(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ai_risk_review_mode", "enforce")

    result = _engine(session, MockAIProvider()).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.BUY
    assert result.risk_review is not None
    assert result.risk_review.verdict is RiskReviewVerdict.APPROVE


def test_wait_is_never_reviewed(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to veto, so no tokens spent - and no path from WAIT to a trade."""
    monkeypatch.setattr(settings, "ai_risk_review_mode", "enforce")
    provider = MockAIProvider()

    result = _engine(session, provider, candidate=None).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.WAIT
    assert result.risk_review is None
    assert _review_calls(provider) == 0


def test_off_makes_no_review_call(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ai_risk_review_mode", "off")
    provider = MockAIProvider(review_content=_VETO)

    result = _engine(session, provider).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.BUY
    assert result.risk_review is None
    assert _review_calls(provider) == 0


def test_a_malformed_review_blocks_nothing_even_when_enforced(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An AI failure must never stop a trade the rules approved (ADR-081) -
    it just leaves no verdict, and says so."""
    monkeypatch.setattr(settings, "ai_risk_review_mode", "enforce")
    provider = MockAIProvider(review_content="{not json")

    result = _engine(session, provider).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.BUY
    assert result.risk_review is None
    assert any("AI risk review unavailable" in w for w in result.warnings)


def test_an_unknown_mode_is_treated_as_off(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ai_risk_review_mode", "strict")
    provider = MockAIProvider(review_content=_VETO)

    result = _engine(session, provider).generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.BUY
    assert _review_calls(provider) == 0


def test_the_review_sees_the_same_evidence_as_the_explanation(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ai_risk_review_mode", "shadow")
    provider = MockAIProvider()

    _engine(session, provider).generate(asset, Timeframe.H1)

    review_request = next(c for c in provider.calls if c.system_prompt == risk_review.SYSTEM_PROMPT)
    assert "Decided recommendation: BUY" in review_request.user_prompt
    assert "Candidate setup:" in review_request.user_prompt
    assert "Approve it or veto it" in review_request.user_prompt


def test_review_tokens_are_stored_separately(
    session: Session, asset: Asset, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ai_risk_review_mode", "shadow")
    provider = MockAIProvider(input_tokens=2100, output_tokens=140)

    result = _engine(session, provider).generate(asset, Timeframe.H1)

    row = session.get(AIAnalysis, result.id)
    assert row is not None
    assert row.risk_review_input_tokens == 2100
    assert row.risk_review_output_tokens == 140
