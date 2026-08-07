"""Presentation-only formatting for Telegram signal messages (docs/57 §6).

Every function here reads already-persisted values (`Signal`, `AIAnalysis`,
`Asset`) and turns them into MarkdownV2 text - none of them decide, score,
or recompute anything. Kept intentionally compact/mobile-friendly per the
user's latest layout spec: header, trade setup, risk management,
timestamp, footer - no chart, no evidence bullets, no market/news
context.
"""

import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, SignalStatus, SignalType
from app.models.signal import Signal

_SEPARATOR = "━━━━━━━━━━━━━━━━━━"

# MarkdownV2 requires escaping these literal characters outside of an
# already-applied entity - values interpolated into the signal message
# (symbol, price strings) are free text from elsewhere in the system and
# must be escaped before sending.
_MARKDOWN_V2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"

#: ADR-137: display-only decimal places per asset, standard FX
#: convention (5dp forex, 3dp JPY-quoted pairs) - a forex signal whose
#: stop loss equals its entry at 2dp reads as broken (docs/03's stored
#: `Numeric(20, 8)` carries far more precision than that). Metal/Crypto/
#: Index keep the prior 2dp behaviour, which was already correct for them.
_JPY_QUOTE_CURRENCY = "JPY"
_FOREX_DECIMAL_PLACES = 5
_FOREX_JPY_DECIMAL_PLACES = 3
_DEFAULT_DECIMAL_PLACES = 2


def escape_markdown_v2(text: str) -> str:
    return re.sub(f"([{re.escape(_MARKDOWN_V2_SPECIAL_CHARS)}])", r"\\\1", text)


def _decimal_places(asset: Asset) -> int:
    if asset.market_type != MarketType.FOREX:
        return _DEFAULT_DECIMAL_PLACES
    if asset.quote_currency == _JPY_QUOTE_CURRENCY:
        return _FOREX_JPY_DECIMAL_PLACES
    return _FOREX_DECIMAL_PLACES


def _format_price(value: Decimal, asset: Asset) -> str:
    """Rounds to the asset's display precision (ADR-137) - the
    underlying stored `Decimal` value is untouched, this only affects
    what's rendered into the message text."""
    quantize = Decimal(1).scaleb(-_decimal_places(asset))
    return str(Decimal(value).quantize(quantize, rounding=ROUND_HALF_UP))


def _display_symbol(asset: Asset) -> str:
    if asset.base_currency and asset.quote_currency:
        return f"{asset.base_currency}/{asset.quote_currency}"
    return asset.symbol


def _title_case(raw: str) -> str:
    return raw.replace("_", " ").title()


def render_header(signal: Signal, asset: Asset) -> str:
    emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴"
    direction = escape_markdown_v2(signal.signal_type.value.upper())
    symbol = escape_markdown_v2(_display_symbol(asset))
    return f"{_SEPARATOR}\n{emoji} {direction} • {symbol}\n{_SEPARATOR}"


def _field(label: str, value: str) -> str:
    return f"{label} : {escape_markdown_v2(value)}"


def render_trade_setup(signal: Signal, asset: Asset) -> str:
    lines = [
        _field("⏰ Timeframe", signal.timeframe.value.upper()),
        "",
        _field("🎯 Entry", _format_price(signal.entry_price, asset)),
        "",
        _field("🛑 Stop Loss", _format_price(signal.stop_loss, asset)),
        "",
        _field("💰 Take Profit", _format_price(signal.take_profit, asset)),
        "",
        _field("⚖️ Risk Reward", f"1 : {signal.risk_reward:.1f}"),
        "",
        _field("🎯 Confidence", f"{signal.confidence:.0f}%"),
    ]
    return "\n".join(lines)


def render_risk_management(signal: Signal, analysis: AIAnalysis) -> str:
    position = (
        _title_case(analysis.execution_guidance) if analysis.execution_guidance else "Not Available"
    )
    risk_label = _title_case(analysis.risk_level) if analysis.risk_level else "Not Available"
    lines = [
        _SEPARATOR,
        "🛡️ Risk Management",
        _SEPARATOR,
        "",
        _field("📌 Recommended Position", position),
        "",
        _field("⚖️ Expected RR", f"1 : {signal.risk_reward:.1f}"),
        "",
        _field("⚠️ Max Drawdown Risk", risk_label),
    ]
    return "\n".join(lines)


def render_timestamp(generated_at: datetime) -> str:
    return f"🕒 {escape_markdown_v2(generated_at.strftime('%Y-%m-%d %H:%M UTC'))}"


def compose_signal_message(
    signal: Signal, analysis: AIAnalysis, asset: Asset, *, now: datetime
) -> str:
    """Assembles the full message from independent, individually-testable
    sections (docs/57 §6)."""
    sections = [
        render_header(signal, asset),
        render_trade_setup(signal, asset),
        render_risk_management(signal, analysis),
        render_timestamp(now),
    ]
    return "\n\n".join(sections)


def render_outcome_header(signal: Signal, asset: Asset) -> str:
    hit_tp = signal.status == SignalStatus.SUCCESSFUL
    emoji = "✅" if hit_tp else "❌"
    label = "TAKE PROFIT HIT" if hit_tp else "STOP LOSS HIT"
    symbol = escape_markdown_v2(_display_symbol(asset))
    return f"{_SEPARATOR}\n{emoji} {label} • {symbol}\n{_SEPARATOR}"


def render_outcome_result(signal: Signal, asset: Asset) -> str:
    hit_tp = signal.status == SignalStatus.SUCCESSFUL
    closed_level_label = "💰 Take Profit" if hit_tp else "🛑 Stop Loss"
    closed_price = signal.take_profit if hit_tp else signal.stop_loss
    result_r = f"+{signal.risk_reward:.1f}R" if hit_tp else "-1.0R"

    lines = [
        _field("⏰ Timeframe", signal.timeframe.value.upper()),
        "",
        _field("🎯 Entry", _format_price(signal.entry_price, asset)),
        "",
        _field(closed_level_label, _format_price(closed_price, asset)),
        "",
        _field("📈 Result" if hit_tp else "📉 Result", result_r),
        "",
        _field("💵 P&L", f"{signal.profit_loss:+.2f}" if signal.profit_loss is not None else "N/A"),
    ]
    return "\n".join(lines)


def compose_signal_outcome_message(signal: Signal, asset: Asset, *, now: datetime) -> str:
    """Follow-up message sent when a previously-delivered signal's price
    has touched its Take Profit or Stop Loss (docs/51 §10's deferred
    outcome-tracking work) - same layout style as `compose_signal_message`,
    reusing the same section-composition pattern."""
    sections = [
        render_outcome_header(signal, asset),
        render_outcome_result(signal, asset),
        render_timestamp(now),
    ]
    return "\n\n".join(sections)


__all__ = [
    "compose_signal_message",
    "compose_signal_outcome_message",
    "escape_markdown_v2",
    "render_header",
    "render_outcome_header",
    "render_outcome_result",
    "render_risk_management",
    "render_timestamp",
    "render_trade_setup",
]
