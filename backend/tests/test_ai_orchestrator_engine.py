import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.economic_event import EconomicEvent
from app.models.enums import MarketType, Recommendation, Timeframe
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.economic_event_repository import EconomicEventRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.ai_orchestrator.context_builder import ContextBuilder
from app.services.ai_orchestrator.providers.exceptions import PermanentAIProviderError
from app.services.ai_orchestrator.providers.mock import MockAIProvider
from app.services.ai_orchestrator_engine import AIOrchestratorEngine
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.news_sentiment_engine import NewsSentimentEngine
from app.services.risk_management_engine import RiskManagementEngine
from app.services.smc_engine import SMCEngine
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
    AIAnalysis.__table__,
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


def _make_engine(session: Session, provider: MockAIProvider) -> AIOrchestratorEngine:
    price_candle_repository = PriceCandleRepository(session)
    asset_repository = AssetRepository(session)
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
    strategy_engine = StrategyEngine(
        confidence_engine=confidence_engine,
        economic_calendar_engine=economic_calendar_engine,
        price_candle_repository=price_candle_repository,
    )
    risk_management_engine = RiskManagementEngine(
        confidence_engine=confidence_engine,
        news_sentiment_engine=news_sentiment_engine,
        economic_calendar_engine=economic_calendar_engine,
        price_candle_repository=price_candle_repository,
        asset_repository=asset_repository,
    )
    context_builder = ContextBuilder(
        confidence_engine=confidence_engine,
        news_sentiment_engine=news_sentiment_engine,
        economic_calendar_engine=economic_calendar_engine,
        strategy_engine=strategy_engine,
        risk_management_engine=risk_management_engine,
    )
    return AIOrchestratorEngine(
        context_builder=context_builder,
        provider=provider,
        ai_analysis_repository=AIAnalysisRepository(session),
    )


def test_generate_returns_a_full_result(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session, MockAIProvider())

    result = engine.generate(asset, Timeframe.H1)

    assert result.symbol == "EURUSD"
    assert result.timeframe == Timeframe.H1
    assert result.ai_available is True
    assert result.reasoning.summary == "Mock summary."


def test_generate_persists_a_row(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session, MockAIProvider())

    result = engine.generate(asset, Timeframe.H1)

    row = session.get(AIAnalysis, result.id)
    assert row is not None
    assert row.asset_id == asset.id


def test_generate_falls_back_gracefully_when_provider_fails(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    provider = MockAIProvider(raises=PermanentAIProviderError("boom"))
    engine = _make_engine(session, provider)

    result = engine.generate(asset, Timeframe.H1)

    assert result.ai_available is False
    assert result.model_name == "none"
    assert any("AI narration unavailable" in w for w in result.warnings)
    assert result.reasoning.summary != ""


def test_generate_waits_when_no_candle_data(session: Session, asset: Asset) -> None:
    engine = _make_engine(session, MockAIProvider())

    result = engine.generate(asset, Timeframe.H1)

    assert result.recommendation is Recommendation.WAIT
    assert result.entry_price is None
