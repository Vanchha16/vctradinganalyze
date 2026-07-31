import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.market_regime.types import MarketRegimeState
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


def _make_engine(session: Session) -> MarketRegimeEngine:
    price_candle_repository = PriceCandleRepository(session)
    technical_analysis_engine = TechnicalAnalysisEngine(price_candle_repository)
    smc_engine = SMCEngine(
        price_candle_repository, SMCEventRepository(session), SMCProcessingStateRepository(session)
    )
    return MarketRegimeEngine(price_candle_repository, technical_analysis_engine, smc_engine)


def test_analyze_raises_when_no_candles(session: Session, asset: Asset) -> None:
    engine = _make_engine(session)

    with pytest.raises(ResourceNotFoundException):
        engine.analyze(asset, Timeframe.H1)


def test_analyze_returns_structured_evidence_with_a_valid_regime(
    session: Session, asset: Asset
) -> None:
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.analyze(asset, Timeframe.H1)

    assert result.regime in list(MarketRegimeState)
    assert 0.0 <= result.confidence <= 100.0
    assert len(result.candidates) == 10  # every non-UNCERTAIN regime is evaluated


def test_analyze_does_not_recompute_upstream_engines_per_analyzer(
    session: Session, asset: Asset
) -> None:
    """Refinement: TA/SMC are each called exactly once per analyze()."""
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)

    price_candle_repository = PriceCandleRepository(session)
    ta_engine = TechnicalAnalysisEngine(price_candle_repository)
    smc_engine = SMCEngine(
        price_candle_repository, SMCEventRepository(session), SMCProcessingStateRepository(session)
    )

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

    engine = MarketRegimeEngine(price_candle_repository, ta_engine, smc_engine)
    engine.analyze(asset, Timeframe.H1)

    assert ta_calls == 1
    assert smc_calls == 1


def test_multi_timeframe_combines_available_timeframes(session: Session, asset: Asset) -> None:
    for timeframe in (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15):
        _seed_trending_candles(session, asset, timeframe, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.analyze_multi_timeframe(asset)

    assert len(result.timeframes) == 5


def test_multi_timeframe_handles_partial_data(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.D1, 300, drift=0.3)
    engine = _make_engine(session)

    result = engine.analyze_multi_timeframe(asset)

    assert len(result.timeframes) == 1
