"""MT5 Expert Advisor schemas (ADR-161).

Token responses never carry the raw token except `EaTokenCreatedResponse`,
returned once by the create call. Feed timestamps are Unix epoch seconds,
not ISO-8601: an MQL5 `datetime` *is* epoch seconds, and MQL5 has no
ISO-8601 parser - `StringToTime` expects "yyyy.mm.dd hh:mi" and silently
misreads a "T"/"Z" string rather than failing.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
