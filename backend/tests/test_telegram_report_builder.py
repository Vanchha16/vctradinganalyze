import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services.telegram.report_builder import build_summary_report_text

_TABLES = [Asset.__table__, Signal.__table__, PriceCandle.__table__]


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    with factory() as session:
        yield session


def _make_asset(session: Session, symbol: str = "EURUSD") -> Asset:
    asset = Asset(symbol=symbol, name=symbol, market_type=MarketType.FOREX, is_active=True)
    session.add(asset)
    session.flush()
    return asset


def _make_signal(
    session: Session,
    asset: Asset,
    *,
    status: SignalStatus,
    profit_loss: Decimal | None = None,
    created_at: datetime,
) -> Signal:
    signal = Signal(
        asset_id=asset.id,
        analysis_id=uuid.uuid4(),
        timeframe=Timeframe.H1,
        signal_type=SignalType.BUY,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("115"),
        risk_reward=Decimal("3"),
        confidence=Decimal("80"),
        status=status,
        profit_loss=profit_loss,
        created_at=created_at,
    )
    session.add(signal)
    session.flush()
    return signal


def test_no_signals_and_no_assets_renders_without_error(session: Session) -> None:
    text = build_summary_report_text(
        SignalRepository(session), AssetRepository(session), PriceCandleRepository(session)
    )
    assert "SUMMARY REPORT" in text
    assert "No active assets configured" in text


def test_today_and_week_sections_reflect_signal_status_and_pnl(session: Session) -> None:
    asset = _make_asset(session)
    now = datetime.now(UTC)
    _make_signal(
        session, asset, status=SignalStatus.SUCCESSFUL, profit_loss=Decimal("50"), created_at=now
    )
    _make_signal(
        session,
        asset,
        status=SignalStatus.STOPPED_OUT,
        profit_loss=Decimal("-20"),
        created_at=now - timedelta(days=3),
    )
    # Outside the 7-day window - must not contribute to either section.
    _make_signal(
        session,
        asset,
        status=SignalStatus.SUCCESSFUL,
        profit_loss=Decimal("999"),
        created_at=now - timedelta(days=30),
    )
    session.commit()

    text = build_summary_report_text(
        SignalRepository(session),
        AssetRepository(session),
        PriceCandleRepository(session),
        now=now,
    )
    # MarkdownV2 escapes '.'/'+'/'-' with a leading backslash - strip that
    # before asserting on the underlying numbers/words.
    unescaped = text.replace("\\", "")

    assert "999" not in unescaped
    assert "Won 1" in unescaped  # today's section
    assert "+50.00" in unescaped  # today's P&L: just the SUCCESSFUL signal
    assert "+30.00" in unescaped  # week's P&L: 50 - 20 net across both signals


def test_market_overview_shows_latest_close_and_change(session: Session) -> None:
    asset = _make_asset(session)
    now = datetime.now(UTC)
    session.add(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=now - timedelta(minutes=1),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
        )
    )
    session.add(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=now,
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("100"),
            close=Decimal("102"),
        )
    )
    session.commit()

    text = build_summary_report_text(
        SignalRepository(session), AssetRepository(session), PriceCandleRepository(session)
    )
    unescaped = text.replace("\\", "")

    assert "EURUSD" in unescaped
    assert "102" in unescaped
    assert "2.00%" in unescaped
