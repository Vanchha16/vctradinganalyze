"""Integration tests for the Telegram bot poll loop's menu/button/chart
flow (docs/57 §3/§7, extended by §13) - in-memory SQLite + a
MockTelegramProvider, mirrors test_signal_monitoring_tasks.py's
session-factory monkeypatch pattern. `/start <code>` linking itself is
unit-tested implicitly here too (no prior test file covered it at all).
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.system_setting import SystemSetting
from app.models.telegram_account import TelegramAccount
from app.services.telegram.keyboards import (
    CALLBACK_SHOW_CHART,
    CALLBACK_SUMMARY_REPORT,
    SHOW_CHART_LABEL,
    SUMMARY_REPORT_LABEL,
    build_persistent_menu_keyboard,
)
from app.services.telegram.providers.base import RawTelegramUpdate
from app.services.telegram.providers.mock import MockTelegramProvider
from app.workers import telegram_tasks

_TABLES = [
    Asset.__table__,
    Signal.__table__,
    PriceCandle.__table__,
    SystemSetting.__table__,
    TelegramAccount.__table__,
]
@pytest.fixture
def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    monkeypatch.setattr(telegram_tasks, "SessionLocal", factory)
    monkeypatch.setattr(telegram_tasks.settings, "telegram_bot_token", "test-token")
    yield factory


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> MockTelegramProvider:
    instance = MockTelegramProvider()
    monkeypatch.setattr(telegram_tasks, "get_telegram_provider", lambda: instance)
    return instance


def _run(updates: list[RawTelegramUpdate], provider: MockTelegramProvider) -> None:
    provider.get_updates = lambda offset: updates  # type: ignore[method-assign]
    telegram_tasks.poll_updates_task()


def _seed_linked_account(session_factory: sessionmaker[Session]) -> str:
    """Returns a freshly generated chat id - each test gets its own, so
    the real-Redis-backed conversation state (`consume_awaiting_chart_symbol`)
    can never leak between tests regardless of execution order."""
    chat_id = f"chat-{uuid.uuid4()}"
    with session_factory() as session:
        session.add(
            TelegramAccount(
                user_id=uuid.uuid4(),
                telegram_chat_id=chat_id,
                linked_at=datetime.now(UTC),
                link_code=f"used-{uuid.uuid4()}",
                link_code_expires_at=datetime.now(UTC),
            )
        )
        session.commit()
    return chat_id


def test_menu_command_sends_persistent_menu_keyboard(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    _run(
        [RawTelegramUpdate(update_id=1, chat_id="1", text="/menu")],
        provider,
    )

    assert len(provider.sent_messages) == 1
    _, _, reply_markup = provider.sent_messages[0]
    assert reply_markup is not None
    assert reply_markup["is_persistent"] is True
    labels = {button["text"] for row in reply_markup["keyboard"] for button in row}
    assert labels == {SUMMARY_REPORT_LABEL, SHOW_CHART_LABEL}


def test_summary_report_label_from_unlinked_chat_is_rejected(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    _run(
        [RawTelegramUpdate(update_id=1, chat_id="not-linked", text=SUMMARY_REPORT_LABEL)],
        provider,
    )

    assert len(provider.sent_messages) == 1
    assert "Link your account" in provider.sent_messages[0][1].replace("\\", "")


def test_summary_report_label_from_linked_chat_sends_report(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)

    _run(
        [RawTelegramUpdate(update_id=1, chat_id=chat_id, text=SUMMARY_REPORT_LABEL)],
        provider,
    )

    assert len(provider.sent_messages) == 1
    assert "SUMMARY REPORT" in provider.sent_messages[0][1]


def test_show_chart_label_then_symbol_reply_sends_photo(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)
    with session_factory() as session:
        asset = Asset(symbol="EURUSD", name="EURUSD", market_type=MarketType.FOREX)
        session.add(asset)
        session.flush()
        now = datetime.now(UTC)
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=now,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
            )
        )
        session.commit()

    _run(
        [RawTelegramUpdate(update_id=1, chat_id=chat_id, text=SHOW_CHART_LABEL)],
        provider,
    )
    prompt_chat_id, prompt_text, prompt_markup = provider.sent_messages[-1]
    assert "Choose a symbol" in prompt_text.replace("\\", "")
    assert prompt_markup is not None
    picker_labels = {button["text"] for row in prompt_markup["keyboard"] for button in row}
    assert picker_labels == {"EURUSD"}

    _run(
        [RawTelegramUpdate(update_id=2, chat_id=chat_id, text="eurusd")],
        provider,
    )

    assert len(provider.sent_photos) == 1
    _, _, _, restored_menu = provider.sent_photos[0]
    assert restored_menu == build_persistent_menu_keyboard()


def test_show_chart_prompts_free_text_when_no_active_assets(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)

    _run(
        [RawTelegramUpdate(update_id=1, chat_id=chat_id, text=SHOW_CHART_LABEL)],
        provider,
    )

    _, prompt_text, prompt_markup = provider.sent_messages[-1]
    assert "Send me a symbol" in prompt_text.replace("\\", "")
    assert prompt_markup is None


def test_summary_report_callback_from_unlinked_chat_is_rejected(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    _run(
        [
            RawTelegramUpdate(
                update_id=1,
                chat_id="not-linked",
                text=None,
                callback_query_id="cbq-1",
                callback_data=CALLBACK_SUMMARY_REPORT,
            )
        ],
        provider,
    )

    assert provider.answered_callback_queries == [("cbq-1", None)]
    assert len(provider.sent_messages) == 1
    text = provider.sent_messages[0][1]
    assert "Link your account" in text.replace("\\", "")


def test_summary_report_callback_from_linked_chat_sends_report(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)

    _run(
        [
            RawTelegramUpdate(
                update_id=1,
                chat_id=chat_id,
                text=None,
                callback_query_id="cbq-1",
                callback_data=CALLBACK_SUMMARY_REPORT,
            )
        ],
        provider,
    )

    assert provider.answered_callback_queries == [("cbq-1", None)]
    assert len(provider.sent_messages) == 1
    assert "SUMMARY REPORT" in provider.sent_messages[0][1]


def test_show_chart_callback_then_symbol_reply_sends_photo(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)
    with session_factory() as session:
        asset = Asset(symbol="EURUSD", name="EURUSD", market_type=MarketType.FOREX)
        session.add(asset)
        session.flush()
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
                high=Decimal("103"),
                low=Decimal("100"),
                close=Decimal("103"),
            )
        )
        session.commit()

    _run(
        [
            RawTelegramUpdate(
                update_id=1,
                chat_id=chat_id,
                text=None,
                callback_query_id="cbq-1",
                callback_data=CALLBACK_SHOW_CHART,
            )
        ],
        provider,
    )
    assert "Choose a symbol" in provider.sent_messages[-1][1].replace("\\", "")

    _run(
        [RawTelegramUpdate(update_id=2, chat_id=chat_id, text="eurusd")],
        provider,
    )

    assert len(provider.sent_photos) == 1
    photo_chat_id, photo_bytes, caption, restored_menu = provider.sent_photos[0]
    assert photo_chat_id == chat_id
    assert photo_bytes.startswith(b"\x89PNG")
    assert caption is not None and "EURUSD" in caption
    assert restored_menu == build_persistent_menu_keyboard()


def test_symbol_reply_without_prior_show_chart_tap_is_ignored(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)

    _run(
        [RawTelegramUpdate(update_id=1, chat_id=chat_id, text="eurusd")],
        provider,
    )

    assert provider.sent_messages == []
    assert provider.sent_photos == []


def test_show_chart_unknown_symbol_replies_with_error_not_a_photo(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    chat_id = _seed_linked_account(session_factory)

    _run(
        [
            RawTelegramUpdate(
                update_id=1,
                chat_id=chat_id,
                text=None,
                callback_query_id="cbq-1",
                callback_data=CALLBACK_SHOW_CHART,
            )
        ],
        provider,
    )
    _run(
        [RawTelegramUpdate(update_id=2, chat_id=chat_id, text="NOTREAL")],
        provider,
    )

    assert provider.sent_photos == []
    assert "Unknown symbol" in provider.sent_messages[-1][1].replace("\\", "")


def test_start_with_valid_code_links_account_and_shows_menu(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    with session_factory() as session:
        account = TelegramAccount(
            user_id=uuid.uuid4(),
            link_code="valid-code",
            link_code_expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        session.add(account)
        session.commit()

    _run(
        [RawTelegramUpdate(update_id=1, chat_id="999", text="/start valid-code")],
        provider,
    )

    assert len(provider.sent_messages) == 2
    assert "Linked to ClaudeTrading AI" in provider.sent_messages[0][1].replace("\\", "")
    assert provider.sent_messages[1][2] is not None  # menu keyboard attached

    with session_factory() as session:
        linked = session.query(TelegramAccount).filter_by(link_code="valid-code").one()
        assert linked.telegram_chat_id == "999"
        assert linked.linked_at is not None


def test_start_with_invalid_code_does_not_show_menu(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    _run(
        [RawTelegramUpdate(update_id=1, chat_id="999", text="/start bogus-code")],
        provider,
    )

    assert len(provider.sent_messages) == 1
    assert "invalid or expired" in provider.sent_messages[0][1].replace("\\", "")
