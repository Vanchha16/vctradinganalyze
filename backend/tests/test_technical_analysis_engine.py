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
from app.models.indicator_result import IndicatorResult
from app.models.price_candle import PriceCandle
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.technical_analysis.types import MultiTimeframeVerdict, TrendDirection
from app.services.technical_analysis_engine import TechnicalAnalysisEngine

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__]


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
    session: Session, asset: Asset, timeframe: Timeframe, count: int, *, direction: int = 1
) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    price = Decimal("100")
    step = Decimal("0.5") * direction
    for i in range(count):
        price += step
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=base + timedelta(minutes=i),
                open=price - Decimal("0.1"),
                high=price + Decimal("0.2"),
                low=price - Decimal("0.3"),
                close=price,
                volume=Decimal(str(1000 + i)),
            )
        )
    session.commit()


def test_analyze_raises_when_no_candles_exist(session: Session, asset: Asset) -> None:
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    with pytest.raises(ResourceNotFoundException):
        engine.analyze(asset, Timeframe.M1)


def test_analyze_detects_uptrend(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=1)
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze(asset, Timeframe.M1)

    assert result.trend == TrendDirection.BULLISH
    assert result.technical_score >= 0
    assert result.technical_score <= 100
    assert result.symbol == "EURUSD"
    assert result.timeframe == Timeframe.M1
    assert "ema_20" in result.indicators


def test_analyze_detects_downtrend(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=-1)
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze(asset, Timeframe.M1)

    assert result.trend == TrendDirection.BEARISH


def test_analyze_reports_warnings_for_insufficient_history(session: Session, asset: Asset) -> None:
    _seed_trending_candles(
        session, asset, Timeframe.M1, 10, direction=1
    )  # far too little for sma_200
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze(asset, Timeframe.M1)

    assert any("sma_200" in warning for warning in result.warnings)


def test_analyze_score_breakdown_matches_total(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=1)
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze(asset, Timeframe.M1)

    assert result.score_breakdown.total == result.technical_score


def test_analyze_multi_timeframe_combines_available_timeframes(
    session: Session, asset: Asset
) -> None:
    for timeframe in (Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15):
        _seed_trending_candles(session, asset, timeframe, 260, direction=1)
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze_multi_timeframe(asset)

    assert result.verdict == MultiTimeframeVerdict.BULLISH_ALIGNMENT
    assert len(result.timeframes) == 4


def test_analyze_multi_timeframe_skips_unavailable_timeframes(
    session: Session, asset: Asset
) -> None:
    _seed_trending_candles(session, asset, Timeframe.D1, 260, direction=1)
    # H4/H1/M15 intentionally left empty
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze_multi_timeframe(asset)

    assert len(result.timeframes) == 1
    assert result.timeframes[0].timeframe == Timeframe.D1


def test_analyze_execution_time_is_reasonable(session: Session, asset: Asset) -> None:
    """Soft performance check (docs/08 §13) - a generous CI-safe upper
    bound rather than the doc's exact 500ms target, to avoid flakiness
    from machine variance."""
    import time

    _seed_trending_candles(session, asset, Timeframe.M1, 500, direction=1)
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    start = time.monotonic()
    engine.analyze(asset, Timeframe.M1)
    duration = time.monotonic() - start

    assert duration < 2.0, f"analysis took {duration:.2f}s, expected well under 2s"


def test_analyze_indicator_values_are_finite(session: Session, asset: Asset) -> None:
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=1)
    engine = TechnicalAnalysisEngine(PriceCandleRepository(session))

    result = engine.analyze(asset, Timeframe.M1)

    for name, value in result.indicators.items():
        assert math.isfinite(value), f"{name} produced a non-finite value"
