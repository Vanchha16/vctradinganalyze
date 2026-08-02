from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, SignalStatus, Timeframe
from app.models.signal import Signal
from app.models.signal_bookmark import SignalBookmark
from app.models.user import User

_TABLES = [
    User.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    SignalBookmark.__table__,
]


def _sqlite_engine_with_fk_enforcement() -> Engine:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture
def session() -> Session:
    engine = _sqlite_engine_with_fk_enforcement()
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_asset(session: Session) -> Asset:
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


def _make_analysis(session: Session, asset: Asset) -> AIAnalysis:
    analysis = AIAnalysis(
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        recommendation=Recommendation.BUY,
        confidence_score=87.0,
        confidence_level="high",
        risk_level="medium",
        entry_price=Decimal("1.17540"),
        stop_loss=Decimal("1.17120"),
        take_profit=Decimal("1.18150"),
        execution_guidance="normal",
        reasoning={
            "summary": "s",
            "technical": "t",
            "smc": "m",
            "economic": "e",
            "news": "n",
            "risk": "r",
            "conclusion": "c",
        },
        model_name="mock",
        prompt_version="1.0.0",
        ai_available=True,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def _make_user(session: Session) -> User:
    user = User(email="trader@example.com", username="trader", password_hash="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_signal(session: Session, asset: Asset, analysis: AIAnalysis) -> Signal:
    signal = Signal(
        analysis_id=analysis.id,
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        signal_type="buy",
        entry_price=Decimal("1.17540"),
        stop_loss=Decimal("1.17120"),
        take_profit=Decimal("1.18150"),
        risk_reward=3.15,
        confidence=87.0,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


def test_signal_defaults_to_active_status(session: Session) -> None:
    asset = _make_asset(session)
    analysis = _make_analysis(session, asset)
    signal = _make_signal(session, asset, analysis)

    assert signal.status is SignalStatus.ACTIVE
    assert signal.triggered_at is None
    assert signal.closed_at is None
    assert signal.profit_loss is None
    assert isinstance(signal.created_at, datetime)


def test_signal_cascade_deletes_with_analysis(session: Session) -> None:
    asset = _make_asset(session)
    analysis = _make_analysis(session, asset)
    _make_signal(session, asset, analysis)

    session.delete(analysis)
    session.commit()
    session.expunge_all()

    assert session.query(Signal).count() == 0


def test_signal_bookmark_unique_per_user_and_signal(session: Session) -> None:
    asset = _make_asset(session)
    analysis = _make_analysis(session, asset)
    signal = _make_signal(session, asset, analysis)
    user = _make_user(session)

    session.add(SignalBookmark(user_id=user.id, signal_id=signal.id))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(SignalBookmark(user_id=user.id, signal_id=signal.id))
        session.flush()


def test_signal_bookmark_cascade_deletes_with_signal(session: Session) -> None:
    asset = _make_asset(session)
    analysis = _make_analysis(session, asset)
    signal = _make_signal(session, asset, analysis)
    user = _make_user(session)

    bookmark = SignalBookmark(user_id=user.id, signal_id=signal.id)
    session.add(bookmark)
    session.commit()

    session.delete(signal)
    session.commit()
    session.expunge_all()

    assert session.query(SignalBookmark).count() == 0
