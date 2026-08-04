from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.conversation import Conversation
from app.models.enums import (
    ConversationStatus,
    MarketType,
    MessageRole,
    Recommendation,
    SignalType,
    Timeframe,
)
from app.models.message import Message
from app.models.oauth_account import OAuthAccount
from app.models.signal import Signal
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.models.user_session import UserSession

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    TelegramAccount.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    Conversation.__table__,
    Message.__table__,
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


def _make_user(session: Session) -> User:
    user = User(email="trader@example.com", username="trader", password_hash="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


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
        reasoning={"summary": "s"},
        model_name="mock",
        prompt_version="1.0.0",
        ai_available=True,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def _make_signal(session: Session, asset: Asset, analysis: AIAnalysis) -> Signal:
    signal = Signal(
        analysis_id=analysis.id,
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        signal_type=SignalType.BUY,
        entry_price=Decimal("1.17540"),
        stop_loss=Decimal("1.17120"),
        take_profit=Decimal("1.18150"),
        risk_reward=1.45,
        confidence=87.0,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


def _make_conversation(session: Session, user: User) -> Conversation:
    conversation = Conversation(user_id=user.id)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def test_conversation_defaults_to_active_status(session: Session) -> None:
    user = _make_user(session)
    conversation = _make_conversation(session, user)

    assert conversation.status is ConversationStatus.ACTIVE
    assert conversation.title is None
    assert conversation.current_symbol is None


def test_conversation_cascade_deletes_messages(session: Session) -> None:
    user = _make_user(session)
    conversation = _make_conversation(session, user)
    session.add(Message(conversation_id=conversation.id, role=MessageRole.USER, content="hi"))
    session.commit()

    session.delete(conversation)
    session.commit()
    session.expunge_all()

    assert session.query(Message).count() == 0


def test_conversation_cascade_deletes_with_user(session: Session) -> None:
    user = _make_user(session)
    _make_conversation(session, user)

    session.delete(user)
    session.commit()
    session.expunge_all()

    assert session.query(Conversation).count() == 0


def test_message_ai_analysis_id_set_null_on_analysis_delete(session: Session) -> None:
    user = _make_user(session)
    asset = _make_asset(session)
    analysis = _make_analysis(session, asset)
    conversation = _make_conversation(session, user)
    message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content="It's a BUY.",
        ai_analysis_id=analysis.id,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    session.delete(analysis)
    session.commit()

    # `message` is expired (not detached) after commit - the next attribute
    # access triggers a fresh SELECT reflecting the DB's own ON DELETE SET
    # NULL action, not a stale in-memory value.
    assert message.ai_analysis_id is None


def test_message_signal_id_set_null_on_signal_delete(session: Session) -> None:
    user = _make_user(session)
    asset = _make_asset(session)
    analysis = _make_analysis(session, asset)
    signal = _make_signal(session, asset, analysis)
    conversation = _make_conversation(session, user)
    message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content="Signal explained.",
        signal_id=signal.id,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    session.delete(signal)
    session.commit()

    assert message.signal_id is None
