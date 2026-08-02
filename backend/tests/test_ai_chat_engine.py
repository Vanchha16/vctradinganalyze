"""AIChatEngine is a thin conversational/persistence layer reusing
ContextBuilder verbatim (ADR-093) - a fake ContextBuilder (not the real
upstream engine stack, already covered by
test_ai_orchestrator_engine.py/test_signal_engine.py) is enough to
verify the engine's own orchestration logic in isolation."""

import uuid
from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.exceptions import ResourceNotFoundException
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.conversation import Conversation
from app.models.enums import MarketType, Recommendation, SignalStatus, SignalType, Timeframe
from app.models.message import Message
from app.models.signal import Signal
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ai_chat_engine import AIChatEngine
from app.services.ai_orchestrator.providers.exceptions import PermanentAIProviderError
from app.services.ai_orchestrator.providers.mock import MockAIProvider
from app.services.ai_orchestrator.types import AnalysisContext
from tests.ai_orchestrator_helpers import make_analysis_context

_TABLES = [
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    Conversation.__table__,
    Message.__table__,
]


class _FakeContextBuilder:
    def __init__(self, context: AnalysisContext) -> None:
        self._context = context
        self.calls = 0

    def build(self, asset: Asset, timeframe: Timeframe) -> AnalysisContext:
        self.calls += 1
        return self._context


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


@pytest.fixture
def conversation(session: Session) -> Conversation:
    conversation = Conversation(user_id=uuid.uuid4())
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def _make_engine(
    session: Session, *, context_calls: MockAIProvider | None = None
) -> tuple[AIChatEngine, _FakeContextBuilder, MockAIProvider]:
    fake_context_builder = _FakeContextBuilder(make_analysis_context())
    provider = MockAIProvider(chat_response_content="It's a BUY because momentum is strong.")
    engine = AIChatEngine(
        context_builder=fake_context_builder,
        provider=provider,
        asset_repository=AssetRepository(session),
        ai_analysis_repository=AIAnalysisRepository(session),
        signal_repository=SignalRepository(session),
        message_repository=MessageRepository(session),
    )
    return engine, fake_context_builder, provider


def test_send_message_without_symbol_answers_generally(
    session: Session, conversation: Conversation
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    exchange = engine.send_message(conversation, "What is a Fair Value Gap?")

    assert fake_context_builder.calls == 0
    assert exchange.user_message.symbol is None
    assert exchange.assistant_message.symbol is None
    assert exchange.assistant_message.content == "It's a BUY because momentum is strong."
    assert exchange.assistant_message.model_name == "mock-model"


def test_send_message_with_explicit_symbol_updates_conversation_current(
    session: Session, conversation: Conversation, asset: Asset
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    engine.send_message(conversation, "Analyze EURUSD", symbol="eurusd", timeframe=Timeframe.H1)

    assert conversation.current_symbol == "EURUSD"
    assert conversation.current_timeframe is Timeframe.H1
    assert fake_context_builder.calls == 1


def test_send_message_inherits_conversation_current_symbol_when_omitted(
    session: Session, conversation: Conversation, asset: Asset
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    engine.send_message(conversation, "Analyze EURUSD", symbol="EURUSD", timeframe=Timeframe.H1)
    exchange = engine.send_message(conversation, "Why?")

    assert exchange.user_message.symbol == "EURUSD"
    assert exchange.user_message.timeframe is Timeframe.H1
    assert fake_context_builder.calls == 2


def test_send_message_with_symbol_but_no_timeframe_defaults_to_h1(
    session: Session, conversation: Conversation, asset: Asset
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    exchange = engine.send_message(conversation, "Analyze EURUSD", symbol="EURUSD")

    assert exchange.user_message.timeframe is Timeframe.H1


def test_send_message_unknown_symbol_raises_not_found(
    session: Session, conversation: Conversation
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    with pytest.raises(ResourceNotFoundException):
        engine.send_message(
            conversation, "Analyze NOTREAL", symbol="NOTREAL", timeframe=Timeframe.H1
        )


def test_context_builder_called_at_most_once_per_send_message(
    session: Session, conversation: Conversation, asset: Asset
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    engine.send_message(conversation, "Analyze EURUSD", symbol="EURUSD", timeframe=Timeframe.H1)

    assert fake_context_builder.calls == 1


def test_send_message_links_latest_analysis_and_signal_to_assistant_message(
    session: Session, conversation: Conversation, asset: Asset
) -> None:
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
        status=SignalStatus.ACTIVE,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)

    engine, fake_context_builder, provider = _make_engine(session)

    exchange = engine.send_message(
        conversation, "Why is this a BUY?", symbol="EURUSD", timeframe=Timeframe.H1
    )

    assert exchange.assistant_message.ai_analysis_id == analysis.id
    assert exchange.assistant_message.signal_id == signal.id


def test_send_message_falls_back_gracefully_on_provider_failure(
    session: Session, conversation: Conversation
) -> None:
    fake_context_builder = _FakeContextBuilder(make_analysis_context())
    provider = MockAIProvider(raises=PermanentAIProviderError("boom"))
    engine = AIChatEngine(
        context_builder=fake_context_builder,
        provider=provider,
        asset_repository=AssetRepository(session),
        ai_analysis_repository=AIAnalysisRepository(session),
        signal_repository=SignalRepository(session),
        message_repository=MessageRepository(session),
    )

    exchange = engine.send_message(conversation, "Why is this a BUY?")

    assert exchange.assistant_message.model_name is None
    assert "unable to generate" in exchange.assistant_message.content.lower()
    assert any("unavailable" in w.lower() for w in exchange.warnings)


def test_send_message_history_included_in_next_prompt(
    session: Session, conversation: Conversation
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)

    engine.send_message(conversation, "Analyze EURUSD")
    engine.send_message(conversation, "Why?")

    second_call_messages = provider.chat_calls[1].messages
    roles_and_content = [(m.role, m.content) for m in second_call_messages]
    assert ("user", "Analyze EURUSD") in roles_and_content
    assert ("assistant", "It's a BUY because momentum is strong.") in roles_and_content


def test_send_message_sets_conversation_title_from_first_message(
    session: Session, conversation: Conversation
) -> None:
    engine, fake_context_builder, provider = _make_engine(session)
    assert conversation.title is None

    engine.send_message(conversation, "What is a Fair Value Gap?")

    assert conversation.title == "What is a Fair Value Gap?"
