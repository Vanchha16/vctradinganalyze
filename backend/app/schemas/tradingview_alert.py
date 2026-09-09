"""Inbound TradingView webhook payload and admin read models (ADR-146).

The request model is the trust boundary. Everything here arrives from
the public internet, shaped by an alert template a third party edits in
TradingView's UI - so it is validated strictly, bounded in size, and
never mapped onto this project's internal enums.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TradingViewAlertRequest(BaseModel):
    """Matches the `alertcondition()` message the Pine scripts emit
    (`pinescript/claudetrading_signals.pine`).

    Only `symbol` and `direction` are required. Everything else is
    optional because a user can edit the alert message freely in
    TradingView's UI, and a partially-filled alert is still worth
    recording - rejecting it would lose the evidence that something is
    misconfigured.
    """

    #: `{{ticker}}`. Length-bounded to match the column and to stop an
    #: oversized body from reaching the database at all.
    symbol: str = Field(min_length=1, max_length=32)
    direction: Literal["buy", "sell"]
    exchange: str | None = Field(default=None, max_length=32)
    #: TradingView's `{{interval}}` ("60", "15", "1D") - kept verbatim,
    #: never coerced into this project's `Timeframe` enum.
    timeframe: str | None = Field(default=None, max_length=16)
    score: float | None = None
    entry: Decimal | None = None
    #: `{{timenow}}`. Parsed when it is a valid datetime and dropped when
    #: it is not - a malformed clock value must not reject the alert.
    time: datetime | None = None
    source: str | None = Field(default=None, max_length=64)

    @field_validator("direction", mode="before")
    @classmethod
    def _normalize_direction(cls, value: Any) -> Any:
        """TradingView templates are hand-edited, so "BUY"/"Buy"/" buy "
        all show up in practice. Normalizing before the `Literal` check
        accepts them without widening what the column may hold."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("symbol", mode="before")
    @classmethod
    def _strip_symbol(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class TradingViewAlertResponse(BaseModel):
    id: str
    symbol: str
    exchange: str | None
    timeframe: str | None
    direction: str
    score: float | None
    entry_price: Decimal | None
    alert_time: datetime | None
    source: str | None
    #: `None` means the Telegram notification never went out - no linked
    #: accounts, or delivery failed. Delivery is best-effort and never
    #: fails the webhook itself.
    delivered_at: datetime | None
    created_at: datetime


class TradingViewAlertListResponse(BaseModel):
    items: list[TradingViewAlertResponse]
    page: int
    limit: int
    total: int


class TradingViewAlertAcceptedResponse(BaseModel):
    """Deliberately minimal. The response goes back over the public
    internet to a caller that has just proven it holds the shared
    secret - but it should still reveal nothing about what was stored,
    how many alerts exist, or whether anyone received the notification."""

    status: Literal["accepted"] = "accepted"
