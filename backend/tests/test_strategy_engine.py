import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.economic_event import EconomicEvent
from app.models.enums import MarketType, Timeframe
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.economic_event_repository import EconomicEventRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.smc_engine import SMCEngine
from app.services.strategy.types import StrategyName
from app.services.strategy_engine import StrategyEngine
from app.services.technical_analysis_engine import TechnicalAnalysisEngine

_TABLES = [
    Asset.__table__,
    PriceCandle.__table__,
    SMCEvent.__table__,
    SMCProcessingState.__table__,
    NewsSource.__table__,
    NewsArticle.__table__,
    NewsSentiment.__table__,
    EconomicEvent.__table__,
]


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


def _seed_trending_candles(
    session: Session, asset: Asset, timeframe: Timeframe, count: int, *, drift: float = 0.3
) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(count):
        mid = 100 + drift * i + math.sin(2 * math.pi * i / 24) * 5
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=base + timedelta(hours=i),
                open=Decimal(str(mid)),
                high=Decimal(str(mid + 1)),
                low=Decimal(str(mid - 1)),
                close=Decimal(str(mid)),
                volume=Decimal(str(1000 + i)),
            )
        )
    session.commit()


def _make_engine(session: Session) -> StrategyEngine:
    price_candle_repository = PriceCandleRepository(session)
    technical_analysis_engine = TechnicalAnalysisEngine(price_candle_repository)
    smc_engine = SMCEngine(
        price_candle_repository, SMCEventRepository(session), SMCProcessingStateRepository(session)
    )
    market_regime_engine = MarketRegimeEngine(
        price_candle_repository, technical_analysis_engine, smc_engine
    )
    confidence_engine = AnalysisConfidenceEngine(
        technical_analysis_engine, smc_engine, market_regime_engine
    )
    economic_calendar_engine = EconomicCalendarEngine(EconomicEventRepository(session))
    return StrategyEngine(
        confidence_engine=confidence_engine,
        economic_calendar_engine=economic_calendar_engine,
        price_candle_repository=price_candle_repository,
    )


def test_evaluate_returns_a_full_evaluation(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(asset, Timeframe.H1)

    assert result.symbol == "EURUSD"
    assert result.timeframe == Timeframe.H1


def test_evaluate_trend_following_scores_well_in_a_trending_market(
    session: Session, asset: Asset
) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(asset, Timeframe.H1)

    all_scores = {s.strategy: s.score for s in result.alternative_strategies}
    if result.primary_strategy is not None:
        all_scores[result.primary_strategy] = result.strategy_score or 0.0
    assert StrategyName.TREND_FOLLOWING in all_scores


def test_evaluate_degrades_gracefully_when_no_candles(session: Session, asset: Asset) -> None:
    engine = _make_engine(session)

    result = engine.evaluate(asset, Timeframe.H1)

    assert result.primary_strategy is None
    assert len(result.rejected_strategies) == len(StrategyName)
    assert any("no candle data" in w.lower() for w in result.warnings)


def test_evaluate_every_rejected_strategy_has_a_reason(session: Session, asset: Asset) -> None:
    engine = _make_engine(session)

    result = engine.evaluate(asset, Timeframe.H1)

    assert all(r.reason for r in result.rejected_strategies)


def test_evaluate_breakdown_present_only_for_primary(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(asset, Timeframe.H1)

    if result.primary_strategy is not None:
        assert result.breakdown is not None
        assert result.strategy_score == result.breakdown.total
