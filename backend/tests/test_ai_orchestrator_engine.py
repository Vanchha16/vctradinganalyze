import math
import uuid
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
from app.models.enums import (
    EconomicEventCategory,
    EconomicEventImportance,
    EconomicEventStatus,
    MarketType,
    Recommendation,
    Timeframe,
)
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
        price_candle_repository=price_candle_repository,
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


def test_generate_persists_the_token_usage_the_provider_reported(
    session: Session, asset: Asset
) -> None:
    """ADR-149 - without this column there is no way to know what a
    signal costs, which is what makes any model comparison possible."""
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session, MockAIProvider(input_tokens=3120, output_tokens=480))

    result = engine.generate(asset, Timeframe.H1)

    row = session.get(AIAnalysis, result.id)
    assert row is not None
    assert row.input_tokens == 3120
    assert row.output_tokens == 480


def test_generate_leaves_token_usage_null_when_the_provider_reports_none(
    session: Session, asset: Asset
) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session, MockAIProvider())

    result = engine.generate(asset, Timeframe.H1)

    row = session.get(AIAnalysis, result.id)
    assert row is not None
    assert row.input_tokens is None
    assert row.output_tokens is None


def test_fallback_narration_records_no_token_usage(session: Session, asset: Asset) -> None:
    """The deterministic fallback runs when the LLM call failed, so no
    tokens were billed - recording zero would understate the real cost
    of a retried-then-failed analysis just as badly as guessing."""
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session, MockAIProvider(raises=PermanentAIProviderError("boom")))

    result = engine.generate(asset, Timeframe.H1)

    row = session.get(AIAnalysis, result.id)
    assert row is not None
    assert row.ai_available is False
    assert row.input_tokens is None
    assert row.output_tokens is None


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


def test_focus_event_reaches_the_prompt_without_touching_the_scored_events(
    session: Session, asset: Asset
) -> None:
    """ADR-152 - the focus event is looked up separately and deliberately
    kept OUT of `economic.events`, which feeds the deterministic risk and
    confidence scoring. Clicking a calendar row must change what the
    narration talks about, never what was decided (ADR-079)."""
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    event = EconomicEvent(
        country="US",
        currency="USD",
        event_name="Core CPI m/m",
        category=EconomicEventCategory.INFLATION,
        importance=EconomicEventImportance.CRITICAL,
        status=EconomicEventStatus.SCHEDULED,
        source="forexfactory",
        # Deliberately far outside ContextBuilder's +24h window: this is
        # exactly the case the button hits, and the reason a click on
        # Thursday's CPI used to be answered with today's bond auction.
        release_time=datetime.now(UTC) + timedelta(days=3),
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    provider = MockAIProvider()
    engine = _make_engine(session, provider)

    baseline = engine.generate(asset, Timeframe.H1)
    focused = engine.generate(asset, Timeframe.H1, focus_event_id=event.id)

    prompt = provider.calls[-1].user_prompt
    assert "Core CPI m/m" in prompt
    assert "in 3 days" in prompt
    # The deterministic half is identical either way.
    assert focused.recommendation == baseline.recommendation
    assert focused.confidence_score == baseline.confidence_score


def test_an_unknown_focus_event_id_still_returns_an_analysis(
    session: Session, asset: Asset
) -> None:
    """A stale calendar tab pointing at a deleted event should degrade to
    an ordinary analysis, not a 500."""
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    provider = MockAIProvider()
    engine = _make_engine(session, provider)

    result = engine.generate(asset, Timeframe.H1, focus_event_id=uuid.uuid4())

    assert result.ai_available is True
    assert "asking specifically about" not in provider.calls[-1].user_prompt
