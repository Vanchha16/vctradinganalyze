"""ADR-170's Telegram messages about the operator's EA - pure formatting over
already-stored rows, so no database."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import SignalType
from app.services.telegram.message_sections import (
    compose_ea_back_online_message,
    compose_ea_event_message,
    compose_ea_loss_limit_message,
    compose_ea_offline_message,
)

_NOW = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)


def _event(event_type: str, **fields: object) -> EaExecutionEvent:
    values: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "token_name": "WinserverEA",
        "signal_id": uuid.uuid4(),
        "event_key": "k",
        "event_type": event_type,
        "dry_run": False,
        "occurred_at": _NOW - timedelta(minutes=2),
        "account_login": "160018306",
        "broker_symbol": "XAUUSDc",
    }
    values.update(fields)
    return EaExecutionEvent(**values)


def _token(**fields: object) -> EaToken:
    values: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "name": "WinserverEA",
        "token_hash": "h",
        "hint": "Jk0I",
        "last_used_at": _NOW - timedelta(minutes=12),
        "effective_dry_run": False,
        "effective_paused": False,
    }
    values.update(fields)
    return EaToken(**values)


def test_an_order_placed_message_shows_the_order_as_sent() -> None:
    text = compose_ea_event_message(
        _event(
            "order_placed",
            order_type="sell_limit",
            volume=Decimal("0.40000000"),
            price=Decimal("4339.67000000"),
            stop_loss=Decimal("4345.79000000"),
            take_profit=Decimal("4326.76000000"),
        ),
        SignalType.SELL,
    )

    assert "📥 ORDER PLACED • XAUUSDc" in text
    assert "📌 Signal : SELL" in text
    assert "🧾 Order : SELL LIMIT" in text
    assert "📦 Lot : 0\\.40" in text
    assert "🎯 Price : 4339\\.67" in text
    assert "🛑 Stop Loss : 4345\\.79" in text
    assert "🖥️ Terminal : WinserverEA · 160018306" in text
    assert "2026\\-09\\-16 09:58 UTC" in text  # when it happened, not when it was sent


def test_a_losing_close_shows_the_loss_and_why_it_closed() -> None:
    text = compose_ea_event_message(
        _event(
            "position_closed",
            volume=Decimal("0.40"),
            price=Decimal("4345.790"),
            profit=Decimal("-245.2"),
            currency="USC",
            close_reason="sl",
        ),
        SignalType.SELL,
    )

    assert "❌ TRADE CLOSED" in text
    assert "🏁 Close price : 4345\\.79" in text
    assert "📍 Closed by : Stop loss" in text
    assert "💵 Profit : \\-245\\.20 USC" in text


def test_a_winning_close_is_marked_as_a_win() -> None:
    text = compose_ea_event_message(
        _event("position_closed", profit=Decimal("420"), currency="USC", close_reason="tp"),
        SignalType.BUY,
    )

    assert "✅ TRADE CLOSED" in text
    assert "💵 Profit : \\+420\\.00 USC" in text


def test_a_rejection_explains_itself() -> None:
    text = compose_ea_event_message(
        _event("order_rejected", retcode=10019, message="No money (margin 12.5)"),
        None,
    )

    assert "⛔ ORDER REJECTED" in text
    assert "No money \\(margin 12\\.5\\)" in text
    assert "📌 Signal" not in text


def test_the_offline_alert_says_when_it_was_last_seen_and_its_mode() -> None:
    text = compose_ea_offline_message(_token(), now=_NOW)

    assert "⚠️ EA OFFLINE • WinserverEA" in text
    assert "2026\\-09\\-16 09:48 UTC \\(12 min ago\\)" in text
    assert "⚙️ Mode : LIVE" in text


def test_the_back_online_alert_names_the_terminal() -> None:
    text = compose_ea_back_online_message(
        _token(last_used_at=_NOW - timedelta(seconds=20), effective_dry_run=True), now=_NOW
    )

    assert "✅ EA BACK ONLINE • WinserverEA" in text
    assert "⚙️ Mode : Dry run" in text


def test_the_loss_limit_alert_shows_the_loss_and_the_limit() -> None:
    text = compose_ea_loss_limit_message(
        _token(
            ea_daily_loss=Decimal("520.40"), ea_daily_loss_limit=Decimal("500"), ea_currency="USC"
        ),
        now=_NOW,
    )

    assert "🛑 DAILY LOSS LIMIT REACHED • WinserverEA" in text
    assert "📉 Lost today : 520\\.40 USC" in text
    assert "🧱 Daily limit : 500\\.00 USC" in text


_RESERVED = set(r"_*[]()~`>#+-=|{}.!")


def _unescaped_reserved(text: str) -> list[str]:
    """MarkdownV2 characters not preceded by a backslash. These messages use
    no formatting, so any such character makes Telegram refuse the whole
    message - which silently lost every EA OFFLINE alert in production."""
    found: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char in _RESERVED:
            found.append(char)
    return found


def test_every_ea_message_is_valid_markdown_v2() -> None:
    token = _token(
        name="Win-server_EA (1)",
        ea_daily_loss=Decimal("520.4"),
        ea_daily_loss_limit=Decimal("500"),
        ea_currency="USC",
    )
    messages = [
        compose_ea_offline_message(token, now=_NOW),
        compose_ea_back_online_message(token, now=_NOW),
        compose_ea_loss_limit_message(token, now=_NOW),
    ]
    for event_type in (
        "order_placed",
        "order_skipped",
        "order_rejected",
        "order_cancelled",
        "position_opened",
        "position_closed",
        "dry_run_checked",
    ):
        event = _event(
            event_type,
            token_name="Win-server",
            order_type="sell_limit",
            volume=Decimal("0.4"),
            price=Decimal("4331.607"),
            stop_loss=Decimal("4342.428"),
            take_profit=Decimal("4309.966"),
            profit=Decimal("-12.5"),
            currency="USC",
            close_reason="stop_out",
            message="Invalid price (x=1.5)!",
        )
        messages.append(compose_ea_event_message(event, SignalType.SELL))

    for text in messages:
        assert _unescaped_reserved(text) == [], text
