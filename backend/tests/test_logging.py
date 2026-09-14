"""Shared logging setup (`app.core.logging`)."""

import logging

import pytest

from app.core.logging import configure_logging


@pytest.mark.parametrize("library", ["httpx", "httpcore"])
def test_http_clients_do_not_log_request_urls(library: str) -> None:
    """The Telegram Bot API carries the bot token in the URL path, so a
    request URL logged at INFO is a leaked secret (production, 2026-09-14)."""
    configure_logging("INFO")

    logger = logging.getLogger(library)

    assert not logger.isEnabledFor(logging.INFO)
    assert logger.isEnabledFor(logging.WARNING)
