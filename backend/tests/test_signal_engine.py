"""SignalEngine is a thin wrapper over AIOrchestratorEngine (ADR-085) - a
fake `AIOrchestratorEngine` (not the real upstream engine stack, already
covered by `test_ai_orchestrator_engine.py`) is enough to verify the
wrapping/persistence/WAIT-produces-no-signal behavior in isolation."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, Timeframe
from app.models.signal import Signal
from app.repositories.signal_repository import SignalRepository
from app.services.ai_orchestrator.types import AIAnalysisResult, ReasoningSections
from app.services.signal_engine import SignalEngine

_TABLES = [Asset.__table__, Signal.__table__]
_CALCULATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_REASONING = ReasoningSections(
    summary="s", technical="t", smc="m", economic="e", news="n", risk="r", conclusion="c"
)


class _FakeAIOrchestratorEngine:
    def __init__(self, result: AIAnalysisResult) -> None:
        self._result = result
        self.call_count = 0

    def generate(self, asset: Asset, timeframe: Timeframe) -> AIAnalysisResult:
        self.call_count += 1
        return self._result


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture
def asset(session: Session) -> Asset:
    asset = Asset(
        symbol="EURUSD",
        name="Euro / US Dollar",
        market_type=MarketType.FOREX,
        base_currency="EUR",
        quote_currency="USD",
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _make_result(
    *,
    recommendation: Recommendation,
    entry_price: Decimal | None = None,
    stop_loss: Decimal | None = None,
    take_profit: Decimal | None = None,
) -> AIAnalysisResult:
    return AIAnalysisResult(
        id=uuid.uuid4(),
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        recommendation=recommendation,
        confidence_score=87.0,
        confidence_level="high",
        risk_level="medium" if recommendation is not Recommendation.WAIT else None,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        execution_guidance="normal" if recommendation is not Recommendation.WAIT else None,
        reasoning=_REASONING,
        model_name="mock",
        prompt_version="1.0.0",
        ai_available=True,
        calculated_at=_CALCULATED_AT,
    )


def test_buy_recommendation_persists_a_signal(session: Session, asset: Asset) -> None:
    result = _make_result(
        recommendation=Recommendation.BUY,
        entry_price=Decimal("1.17540"),
        stop_loss=Decimal("1.17120"),
        take_profit=Decimal("1.18150"),
    )
    fake_engine = _FakeAIOrchestratorEngine(result)
    engine = SignalEngine(fake_engine, SignalRepository(session))

    generation = engine.generate(asset, Timeframe.H1)

    assert generation.recommendation is Recommendation.BUY
    assert generation.signal is not None
    assert generation.signal.entry_price == Decimal("1.17540")
    assert generation.signal.risk_reward == pytest.approx(1.4524, abs=0.01)
    assert generation.signal.confidence == 87.0

    row = session.get(Signal, generation.signal.id)
    assert row is not None
    assert row.asset_id == asset.id
    assert row.analysis_id == result.id


def test_sell_recommendation_persists_a_signal(session: Session, asset: Asset) -> None:
    result = _make_result(
        recommendation=Recommendation.SELL,
        entry_price=Decimal("1.18000"),
        stop_loss=Decimal("1.18400"),
        take_profit=Decimal("1.17200"),
    )
    fake_engine = _FakeAIOrchestratorEngine(result)
    engine = SignalEngine(fake_engine, SignalRepository(session))

    generation = engine.generate(asset, Timeframe.H1)

    assert generation.signal is not None
    assert generation.signal.signal_type.value == "sell"


def test_wait_recommendation_produces_no_signal(session: Session, asset: Asset) -> None:
    result = _make_result(recommendation=Recommendation.WAIT)
    fake_engine = _FakeAIOrchestratorEngine(result)
    engine = SignalEngine(fake_engine, SignalRepository(session))

    generation = engine.generate(asset, Timeframe.H1)

    assert generation.recommendation is Recommendation.WAIT
    assert generation.signal is None
    assert session.query(Signal).count() == 0


def test_ai_orchestrator_engine_called_exactly_once(session: Session, asset: Asset) -> None:
    result = _make_result(
        recommendation=Recommendation.BUY,
        entry_price=Decimal("1.17540"),
        stop_loss=Decimal("1.17120"),
        take_profit=Decimal("1.18150"),
    )
    fake_engine = _FakeAIOrchestratorEngine(result)
    engine = SignalEngine(fake_engine, SignalRepository(session))

    engine.generate(asset, Timeframe.H1)

    assert fake_engine.call_count == 1
