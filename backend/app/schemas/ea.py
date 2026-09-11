"""MT5 Expert Advisor schemas (ADR-161).

Token responses never carry the raw token except `EaTokenCreatedResponse`,
returned once by the create call. Feed timestamps are Unix epoch seconds,
not ISO-8601: an MQL5 `datetime` *is* epoch seconds, and MQL5 has no
ISO-8601 parser - `StringToTime` expects "yyyy.mm.dd hh:mi" and silently
misreads a "T"/"Z" string rather than failing.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SignalStatus, SignalType, Timeframe


class EaTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    #: Last four characters of the token.
    hint: str
    created_at: datetime
    last_used_at: datetime | None


class EaTokenCreatedResponse(EaTokenResponse):
    #: The only time the raw token ever leaves the server.
    token: str


class EaTokenListResponse(BaseModel):
    items: list[EaTokenResponse]


class EaTokenCreateRequest(BaseModel):
    #: `\S` - a name of only spaces would make two tokens indistinguishable.
    name: str = Field(min_length=1, max_length=64, pattern=r"\S", examples=["Home PC"])


class EaSignalResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    timeframe: Timeframe
    signal_type: SignalType
    #: Floats, not the `Decimal` strings `SignalResponse` serializes to -
    #: the EA converts to `double` regardless, and a JSON number saves it
    #: a string-to-number step per field.
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    #: `active` (no fill yet) or `triggered` (price reached entry). Never
    #: anything else - a signal leaves the feed once it is neither.
    status: SignalStatus
    created_at: int
    triggered_at: int | None
    #: When the pending entry stops being valid (`created_at` +
    #: `SIGNAL_TTL_HOURS`). An EA should not leave an unfilled order at
    #: the broker past this.
    expires_at: int


class EaSignalFeedResponse(BaseModel):
    #: Lets the EA measure its own clock drift instead of trusting the PC.
    server_time: int
    symbol: str
    signals: list[EaSignalResponse]


# --- Execution events (ADR-162) ----------------------------------------

EaEventType = Literal[
    "dry_run_checked",
    "order_placed",
    "order_skipped",
    "order_rejected",
    "order_cancelled",
    "position_opened",
    "position_closed",
]

_MAX_TICKET = 2**63 - 1


class EaEventIn(BaseModel):
    """One event as the EA reports it. Numbers are floats and times are
    epoch seconds, for the same MQL5 reasons as the feed."""

    #: Derived by the EA from what happened (`closed:<deal ticket>`), so a
    #: re-sent batch is recognised rather than stored twice.
    event_key: str = Field(min_length=1, max_length=128)
    event_type: EaEventType
    signal_id: uuid.UUID
    dry_run: bool
    #: Upper bound (2100-01-01) so a garbage value is a 422, not an
    #: `OverflowError` converting it to a datetime.
    occurred_at: int = Field(gt=0, lt=4_102_444_800)
    account_login: str = Field(min_length=1, max_length=32)
    broker_symbol: str = Field(min_length=1, max_length=32)
    order_type: str | None = Field(default=None, max_length=32)
    order_ticket: int | None = Field(default=None, ge=0, le=_MAX_TICKET)
    position_id: int | None = Field(default=None, ge=0, le=_MAX_TICKET)
    volume: float | None = None
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    profit: float | None = None
    currency: str | None = Field(default=None, max_length=8)
    retcode: int | None = None
    close_reason: str | None = Field(default=None, max_length=16)
    message: str | None = None

    @field_validator("message")
    @classmethod
    def _truncate_message(cls, value: str | None) -> str | None:
        """Truncated, not rejected: one over-long broker comment would
        otherwise 422 the whole batch, and the EA cannot fix it by
        retrying - the batch would block its queue forever."""
        return value[:255] if value is not None else None


class EaEventBatchRequest(BaseModel):
    events: list[EaEventIn] = Field(min_length=1, max_length=50)


class EaEventRejection(BaseModel):
    event_key: str
    reason: str


class EaEventBatchResponse(BaseModel):
    accepted: int
    #: Already stored from an earlier send - not an error.
    duplicates: int
    #: Valid in shape but not storable (e.g. an unknown signal). Reported
    #: per event instead of failing the batch, so the good events in it
    #: still land and the EA can drop the batch either way.
    rejected: list[EaEventRejection]


class EaEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    signal_id: uuid.UUID
    #: The signal's direction, for display without a second request.
    #: Null only if the signal row has since gone.
    signal_type: SignalType | None
    dry_run: bool
    occurred_at: datetime
    token_name: str
    account_login: str
    broker_symbol: str
    order_type: str | None
    order_ticket: int | None
    position_id: int | None
    volume: float | None
    price: float | None
    stop_loss: float | None
    take_profit: float | None
    profit: float | None
    currency: str | None
    retcode: int | None
    close_reason: str | None
    message: str | None
    created_at: datetime


class EaEventListResponse(BaseModel):
    items: list[EaEventResponse]
    page: int
    limit: int
    total: int
