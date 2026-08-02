import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.ai_analysis import AIAnalysis
from app.models.enums import MessageRole, Recommendation, SignalStatus, SignalType, Timeframe
from app.models.message import Message
from app.models.signal import Signal
from app.services.ai_chat import chat_prompt_builder
from tests.ai_orchestrator_helpers import make_analysis_context

_ANALYSIS = AIAnalysis(
    id=uuid.uuid4(),
    asset_id=uuid.uuid4(),
    timeframe=Timeframe.H1,
    recommendation=Recommendation.BUY,
    confidence_score=87.0,
    confidence_level="high",
    risk_level="medium",
    entry_price=Decimal("1.17540"),
    stop_loss=Decimal("1.17120"),
    take_profit=Decimal("1.18150"),
    execution_guidance="normal",
    reasoning={"summary": "Bullish trend with confirmed order block."},
    supporting_evidence=["EMA alignment bullish"],
    conflicting_evidence=[],
    model_name="gpt-4o-mini",
    prompt_version="1.0.0",
    ai_available=True,
)
_ANALYSIS.created_at = datetime(2026, 1, 1, tzinfo=UTC)

_SIGNAL = Signal(
    id=uuid.uuid4(),
    analysis_id=_ANALYSIS.id,
    asset_id=uuid.uuid4(),
    timeframe=Timeframe.H1,
    signal_type=SignalType.BUY,
    entry_price=Decimal("1.17540"),
    stop_loss=Decimal("1.17120"),
    take_profit=Decimal("1.18150"),
    risk_reward=1.45,
    confidence=87.0,
    status=SignalStatus.ACTIVE,
)
_SIGNAL.created_at = datetime(2026, 1, 1, tzinfo=UTC)


def test_build_includes_system_prompt_and_question() -> None:
    request = chat_prompt_builder.build(
        history=[],
        question="Why is this a BUY?",
        context=None,
        latest_analysis=None,
        latest_signal=None,
    )

    assert request.messages[0].role == "system"
    assert "never invent" in request.messages[0].content.lower()
    assert request.messages[-1] == chat_prompt_builder.ChatTurn(
        role="user", content="Why is this a BUY?"
    )


def test_build_with_no_context_states_no_asset_in_scope() -> None:
    request = chat_prompt_builder.build(
        history=[],
        question="What is a Fair Value Gap?",
        context=None,
        latest_analysis=None,
        latest_signal=None,
    )

    system_content = request.messages[0].content
    assert "no specific asset/timeframe is in scope" in system_content.lower()


def test_build_serializes_grounding_facts_from_context() -> None:
    context = make_analysis_context()

    request = chat_prompt_builder.build(
        history=[],
        question="Analyze EURUSD",
        context=context,
        latest_analysis=None,
        latest_signal=None,
    )

    system_content = request.messages[0].content
    assert "Asset: EURUSD" in system_content
    assert "Timeframe: h1" in system_content
    assert "Confidence:" in system_content
    assert "Technical Analysis:" in system_content
    assert "SMC:" in system_content
    assert "Market Regime:" in system_content


def test_build_includes_latest_analysis_facts() -> None:
    context = make_analysis_context()

    request = chat_prompt_builder.build(
        history=[],
        question="Why is this a BUY?",
        context=context,
        latest_analysis=_ANALYSIS,
        latest_signal=None,
    )

    system_content = request.messages[0].content
    assert "BUY" in system_content
    assert "confidence=87" in system_content
    assert "Bullish trend with confirmed order block." in system_content


def test_build_states_no_persisted_analysis_when_none_exists() -> None:
    context = make_analysis_context()

    request = chat_prompt_builder.build(
        history=[],
        question="Why is this a BUY?",
        context=context,
        latest_analysis=None,
        latest_signal=None,
    )

    system_content = request.messages[0].content
    assert "no persisted ai recommendation exists yet" in system_content.lower()


def test_build_includes_latest_signal_facts() -> None:
    context = make_analysis_context()

    request = chat_prompt_builder.build(
        history=[],
        question="Explain this signal",
        context=context,
        latest_analysis=None,
        latest_signal=_SIGNAL,
    )

    system_content = request.messages[0].content
    assert "risk_reward=1.45" in system_content
    assert "status=active" in system_content


def test_build_includes_conversation_history_in_order() -> None:
    history = [
        Message(role=MessageRole.USER, content="Analyze EURUSD"),
        Message(role=MessageRole.ASSISTANT, content="It's currently a BUY."),
    ]

    request = chat_prompt_builder.build(
        history=history, question="Why?", context=None, latest_analysis=None, latest_signal=None
    )

    assert request.messages[1].role == "user"
    assert request.messages[1].content == "Analyze EURUSD"
    assert request.messages[2].role == "assistant"
    assert request.messages[2].content == "It's currently a BUY."
    assert request.messages[3].role == "user"
    assert request.messages[3].content == "Why?"


def test_max_tokens_matches_request() -> None:
    request = chat_prompt_builder.build(
        history=[], question="Hi", context=None, latest_analysis=None, latest_signal=None
    )
    assert request.max_tokens == chat_prompt_builder.max_tokens()
