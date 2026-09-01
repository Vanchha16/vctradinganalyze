import uuid

from app.services.telegram.conversation_state import (
    consume_awaiting_chart_symbol,
    mark_awaiting_chart_symbol,
)


def test_mark_then_consume_round_trip() -> None:
    """Requires a real, reachable Redis - same assumption
    `test_websockets.py`'s pub/sub tests make (CI provides one, see
    `.github/workflows/ci.yml`)."""
    chat_id = f"test-{uuid.uuid4()}"

    mark_awaiting_chart_symbol(chat_id)

    assert consume_awaiting_chart_symbol(chat_id) is True
    # The flag is consumed, not just read - a second call must not still
    # see it armed.
    assert consume_awaiting_chart_symbol(chat_id) is False


def test_consume_without_mark_returns_false() -> None:
    chat_id = f"test-{uuid.uuid4()}"

    assert consume_awaiting_chart_symbol(chat_id) is False
