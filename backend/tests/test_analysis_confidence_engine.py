import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.analysis_confidence.types import ConfidenceLevel, ConfidenceMultiTimeframeVerdict
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.smc_engine import SMCEngine
from app.services.technical_analysis_engine import TechnicalAnalysisEngine

_TABLES = [
    Asset.__table__,
    PriceCandle.__table__,
    SMCEvent.__table__,
    SMCProcessingState.__table__,
]


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture
def asset(session: Session) -> Asset:
    asset = Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX)
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


def _make_engine(session: Session) -> AnalysisConfidenceEngine:
    price_candle_repository = PriceCandleRepository(session)
    technical_analysis_engine = TechnicalAnalysisEngine(price_candle_repository)
    smc_engine = SMCEngine(
        price_candle_repository, SMCEventRepository(session), SMCProcessingStateRepository(session)
    )
    market_regime_engine = MarketRegimeEngine(
        price_candle_repository, technical_analysis_engine, smc_engine
    )
    return AnalysisConfidenceEngine(technical_analysis_engine, smc_engine, market_regime_engine)


def test_analyze_returns_graceful_result_when_no_candles(session: Session, asset: Asset) -> None:
    engine = _make_engine(session)

    result = engine.analyze(asset, Timeframe.H1)

    assert result.confidence_level == ConfidenceLevel.VERY_LOW
    assert "technical_analysis_unavailable" in result.missing_data
    assert "smc_unavailable" in result.missing_data
    assert "market_regime_unavailable" in result.missing_data
    assert result.technical is None
    assert result.smc is None
    assert result.market_regime is None


def test_analyze_returns_structured_evidence_with_real_data(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.analyze(asset, Timeframe.H1)

    assert 0.0 <= result.overall_confidence <= 100.0
    assert result.confidence_level in list(ConfidenceLevel)
    assert result.technical is not None
    assert result.smc is not None
    assert result.market_regime is not None
    assert result.missing_data == []
    assert result.summary != ""


def test_technical_and_smc_are_each_computed_exactly_once(session: Session, asset: Asset) -> None:
    """Regression for ADR-049: the Confidence Engine must not cause
    Market Regime to recompute TA/SMC a second time."""
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)

    price_candle_repository = PriceCandleRepository(session)
    ta_engine = TechnicalAnalysisEngine(price_candle_repository)
    smc_engine = SMCEngine(
        price_candle_repository, SMCEventRepository(session), SMCProcessingStateRepository(session)
    )
    market_regime_engine = MarketRegimeEngine(price_candle_repository, ta_engine, smc_engine)

    ta_calls = 0
    smc_calls = 0
    original_ta_analyze = ta_engine.analyze
    original_smc_analyze = smc_engine.analyze

    def counted_ta_analyze(*args: object, **kwargs: object):
        nonlocal ta_calls
        ta_calls += 1
        return original_ta_analyze(*args, **kwargs)  # type: ignore[arg-type]

    def counted_smc_analyze(*args: object, **kwargs: object):
        nonlocal smc_calls
        smc_calls += 1
        return original_smc_analyze(*args, **kwargs)  # type: ignore[arg-type]

    ta_engine.analyze = counted_ta_analyze  # type: ignore[method-assign]
    smc_engine.analyze = counted_smc_analyze  # type: ignore[method-assign]

    engine = AnalysisConfidenceEngine(ta_engine, smc_engine, market_regime_engine)
    engine.analyze(asset, Timeframe.H1)

    assert ta_calls == 1
    assert smc_calls == 1


def test_multi_timeframe_returns_all_five_timeframes(session: Session, asset: Asset) -> None:
    for timeframe in (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15):
        _seed_trending_candles(session, asset, timeframe, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.analyze_multi_timeframe(asset)

    assert len(result.timeframes) == 5
    assert result.verdict in list(ConfidenceMultiTimeframeVerdict)


def test_multi_timeframe_with_no_data_is_mixed(session: Session, asset: Asset) -> None:
    engine = _make_engine(session)

    result = engine.analyze_multi_timeframe(asset)

    assert len(result.timeframes) == 5
    assert result.verdict == ConfidenceMultiTimeframeVerdict.MIXED
