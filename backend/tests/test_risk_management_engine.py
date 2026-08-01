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
from app.repositories.asset_repository import AssetRepository
from app.repositories.economic_event_repository import EconomicEventRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.news_sentiment_engine import NewsSentimentEngine
from app.services.risk_management.types import TradeDirection
from app.services.risk_management_engine import RiskManagementEngine
from app.services.smc_engine import SMCEngine
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


def _make_engine(session: Session) -> RiskManagementEngine:
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
    news_sentiment_engine = NewsSentimentEngine(NewsSentimentRepository(session))
    economic_calendar_engine = EconomicCalendarEngine(EconomicEventRepository(session))
    return RiskManagementEngine(
        confidence_engine=confidence_engine,
        news_sentiment_engine=news_sentiment_engine,
        economic_calendar_engine=economic_calendar_engine,
        price_candle_repository=price_candle_repository,
        asset_repository=AssetRepository(session),
    )


def test_evaluate_approves_a_reasonable_setup(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(
        asset,
        Timeframe.H1,
        TradeDirection.LONG,
        entry_price=Decimal("150"),
        stop_loss=Decimal("140"),
        take_profit=Decimal("180"),
    )

    assert result.breakdown.total >= 0
    assert result.risk_reward is not None
    assert result.risk_reward == pytest.approx(3.0)
    assert "Spread not supplied - Spread Filter skipped." in result.warnings


def test_evaluate_rejects_setup_below_minimum_risk_reward(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(
        asset,
        Timeframe.H1,
        TradeDirection.LONG,
        entry_price=Decimal("150"),
        stop_loss=Decimal("140"),
        take_profit=Decimal("155"),  # rr = 0.5, well below 1:2 minimum
    )

    assert result.approved is False
    assert any("risk/reward" in r.lower() for r in result.rejected_reasons)
    assert result.breakdown.total >= 0  # still computed, even when rejected (ADR-068)


def test_evaluate_rejects_extreme_spread(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(
        asset,
        Timeframe.H1,
        TradeDirection.LONG,
        entry_price=Decimal("150"),
        stop_loss=Decimal("140"),
        take_profit=Decimal("180"),
        spread=Decimal("2.0"),  # ~1.3% of price - well above the 0.15% extreme band
    )

    assert result.approved is False
    assert any("spread" in r.lower() for r in result.rejected_reasons)


def test_evaluate_rejects_too_tight_stop_loss(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(
        asset,
        Timeframe.H1,
        TradeDirection.LONG,
        entry_price=Decimal("150"),
        stop_loss=Decimal("149.99"),
        take_profit=Decimal("180"),
    )

    assert result.approved is False
    assert any("tight" in r.lower() for r in result.rejected_reasons)


def test_evaluate_degrades_gracefully_when_no_candles(session: Session, asset: Asset) -> None:
    """Mirrors AnalysisConfidenceEngine's graceful degradation - a
    setup for an asset with no candle history still returns a full
    (if low-quality) evaluation, not a 404/exception."""
    engine = _make_engine(session)

    result = engine.evaluate(
        asset,
        Timeframe.H1,
        TradeDirection.LONG,
        entry_price=Decimal("150"),
        stop_loss=Decimal("140"),
        take_profit=Decimal("180"),
    )

    assert result.breakdown.trend_quality == 0.0
    assert result.breakdown.technical == 0.0
    assert result.breakdown.smc == 0.0


def test_evaluate_breakdown_always_populated_even_when_rejected(
    session: Session, asset: Asset
) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.evaluate(
        asset,
        Timeframe.H1,
        TradeDirection.LONG,
        entry_price=Decimal("150"),
        stop_loss=Decimal("140"),
        take_profit=Decimal("155"),
    )

    assert result.approved is False
    assert result.breakdown.total > 0  # explainable even when rejected (ADR-068)
