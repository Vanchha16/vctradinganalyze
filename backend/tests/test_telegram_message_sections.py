"""Unit tests for the Telegram signal message redesign (docs/57 §6) -
each section is pure formatting over already-persisted values, so these
tests construct model instances directly without a database."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.services.telegram.message_sections import (
    compose_signal_message,
    compose_signal_outcome_message,
    compose_signal_triggered_message,
    escape_markdown_v2,
    render_header,
    render_risk_management,
    render_timestamp,
    render_trade_setup,
)

_NOW = datetime(2026, 8, 4, 9, 0, tzinfo=UTC)


def _make_asset() -> Asset:
    return Asset(
        id=uuid.uuid4(),
        symbol="BTCUSD",
        name="Bitcoin",
        market_type=MarketType.CRYPTO,
        base_currency="BTC",
        quote_currency="USD",
    )


def _make_signal(*, analysis_id: uuid.UUID, asset_id: uuid.UUID) -> Signal:
    return Signal(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        asset_id=asset_id,
        timeframe=Timeframe.H1,
        signal_type=SignalType.SELL,
        entry_price=Decimal("63824.500001"),
        stop_loss=Decimal("64112.130652"),
        take_profit=Decimal("63249.244999"),
        risk_reward=2.0,
        confidence=83.0,
    )


def _make_analysis(
    *,
    asset_id: uuid.UUID,
    risk_level: str | None = "high",
    execution_guidance: str | None = "normal",
) -> AIAnalysis:
    return AIAnalysis(
        id=uuid.uuid4(),
        asset_id=asset_id,
        timeframe=Timeframe.H1,
        recommendation=Recommendation.SELL,
        confidence_score=83.0,
        confidence_level="high",
        risk_level=risk_level,
        execution_guidance=execution_guidance,
        reasoning={
            "summary": "s",
            "technical": "t",
            "smc": "m",
            "economic": "e",
            "news": "n",
            "risk": "r",
            "conclusion": "c",
        },
        supporting_evidence=["Bearish BOS confirmed"],
        model_name="mock",
        prompt_version="1.0.0",
    )


def test_render_header_shows_direction_and_base_quote_symbol() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = render_header(signal, asset)

    assert "🔴" in text
    assert "SELL" in text
    assert "BTC/USD" in text


def test_render_trade_setup_shows_two_decimal_places_for_crypto() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = render_trade_setup(signal, asset)

    # Long floating-point noise (63824.500001 etc.) must round to 2dp,
    # not truncate/strip - matches the user's explicit spec.
    assert "63824\\.50" in text
    assert "64112\\.13" in text
    assert "63249\\.24" in text
    assert "1 : 2\\.0" in text
    assert "83%" in text
    assert "⏰ Timeframe" in text
    assert "🎯 Entry" in text
    assert "🛑 Stop Loss" in text
    assert "💰 Take Profit" in text
    # Label and value are on the same line, separated by " : ".
    assert "⏰ Timeframe : H1" in text
    assert "🎯 Entry : 63824\\.50" in text


def _make_forex_asset(*, symbol: str, quote_currency: str) -> Asset:
    return Asset(
        id=uuid.uuid4(),
        symbol=symbol,
        name=symbol,
        market_type=MarketType.FOREX,
        base_currency=symbol[:3],
        quote_currency=quote_currency,
    )


def _make_metal_asset() -> Asset:
    return Asset(
        id=uuid.uuid4(),
        symbol="XAUUSD",
        name="Gold",
        market_type=MarketType.METAL,
        base_currency="XAU",
        quote_currency="USD",
    )


def test_render_trade_setup_shows_five_decimal_places_for_forex() -> None:
    asset = _make_forex_asset(symbol="EURUSD", quote_currency="USD")
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)
    signal.entry_price = Decimal("1.15241000")
    signal.stop_loss = Decimal("1.15241000")
    signal.take_profit = Decimal("1.14800000")

    text = render_trade_setup(signal, asset)

    assert "🎯 Entry : 1\\.15241" in text
    assert "🛑 Stop Loss : 1\\.15241" in text
    assert "💰 Take Profit : 1\\.14800" in text
    # The stored Decimal itself must never be mutated by formatting.
    assert signal.entry_price == Decimal("1.15241000")


def test_render_trade_setup_shows_three_decimal_places_for_jpy_forex_pair() -> None:
    asset = _make_forex_asset(symbol="USDJPY", quote_currency="JPY")
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)
    signal.entry_price = Decimal("151.234500")

    text = render_trade_setup(signal, asset)

    assert "🎯 Entry : 151\\.235" in text
    assert signal.entry_price == Decimal("151.234500")


def test_render_trade_setup_shows_two_decimal_places_for_metal() -> None:
    asset = _make_metal_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = render_trade_setup(signal, asset)

    assert "🎯 Entry : 63824\\.50" in text


def test_render_risk_management_uses_execution_guidance_and_risk_level() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id, risk_level="high", execution_guidance="normal")
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = render_risk_management(signal, analysis)

    assert "🛡️ Risk Management" in text
    assert "📌 Recommended Position : Normal" in text
    assert "⚖️ Expected RR" in text
    assert "1 : 2\\.0" in text
    assert "⚠️ Max Drawdown Risk : High" in text


def test_render_risk_management_handles_missing_values() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id, risk_level=None, execution_guidance=None)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = render_risk_management(signal, analysis)

    assert text.count("Not Available") == 2


def test_render_timestamp_format() -> None:
    text = render_timestamp(_NOW)
    assert text == "🕒 2026\\-08\\-04 09:00 UTC"


def test_escape_markdown_v2_escapes_reserved_characters() -> None:
    assert escape_markdown_v2("1.5 (test) - a_b") == "1\\.5 \\(test\\) \\- a\\_b"


def test_compose_signal_message_matches_expected_layout() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = compose_signal_message(signal, analysis, asset, now=_NOW)

    # Section order per the user's spec: header, trade setup, risk
    # management, timestamp - no footer branding block.
    assert text.index("SELL") < text.index("Timeframe")
    assert text.index("Confidence") < text.index("Risk Management")
    assert text.index("Risk Management") < text.index("🕒")
    assert text.rstrip().endswith("09:00 UTC")
    # Sections not part of the simplified spec must not appear.
    assert "Why this trade" not in text
    assert "Market Context" not in text
    assert "Technical Confirmation" not in text
    assert "Market News" not in text
    assert "Signal Quality" not in text
    assert "ClaudeTrading AI" not in text


def _make_closed_signal(
    *, analysis_id: uuid.UUID, asset_id: uuid.UUID, status: SignalStatus, profit_loss: Decimal
) -> Signal:
    signal = _make_signal(analysis_id=analysis_id, asset_id=asset_id)
    signal.status = status
    signal.profit_loss = profit_loss
    return signal


def test_compose_signal_outcome_message_take_profit_hit() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_closed_signal(
        analysis_id=analysis.id,
        asset_id=asset.id,
        status=SignalStatus.SUCCESSFUL,
        profit_loss=Decimal("574.26"),
    )

    text = compose_signal_outcome_message(signal, asset, now=_NOW)

    assert "✅" in text
    assert "TAKE PROFIT HIT" in text
    assert "STOP LOSS HIT" not in text
    assert "💰 Take Profit : 63249\\.24" in text
    assert "📈 Result : \\+2\\.0R" in text
    assert "💵 P&L : \\+574\\.26" in text
    assert text.rstrip().endswith("09:00 UTC")


def test_compose_signal_outcome_message_stop_loss_hit() -> None:
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_closed_signal(
        analysis_id=analysis.id,
        asset_id=asset.id,
        status=SignalStatus.STOPPED_OUT,
        profit_loss=Decimal("-287.63"),
    )

    text = compose_signal_outcome_message(signal, asset, now=_NOW)

    assert "❌" in text
    assert "STOP LOSS HIT" in text
    assert "TAKE PROFIT HIT" not in text
    assert "🛑 Stop Loss : 64112\\.13" in text
    assert "📉 Result : \\-1\\.0R" in text
    assert "💵 P&L : \\-287\\.63" in text


def test_compose_signal_triggered_message_matches_expected_layout() -> None:
    """(2026-08-07) Entry-confirmed follow-up sent the moment a signal
    transitions ACTIVE -> TRIGGERED - reverses ADR-137 §3.5's original
    "no message" decision per explicit operator request."""
    asset = _make_asset()
    analysis = _make_analysis(asset_id=asset.id)
    signal = _make_signal(analysis_id=analysis.id, asset_id=asset.id)

    text = compose_signal_triggered_message(signal, asset, now=_NOW)

    assert "🔔" in text
    assert "ENTRY CONFIRMED" in text
    assert "BTC/USD" in text
    assert "🎯 Entry : 63824\\.50" in text
    assert "🛑 Stop Loss : 64112\\.13" in text
    assert "💰 Take Profit : 63249\\.24" in text
    assert text.rstrip().endswith("09:00 UTC")
