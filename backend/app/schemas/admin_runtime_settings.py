from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeSettingResponse(BaseModel):
    """One manageable setting (ADR-178). `value` is what the system uses
    now; `default` is the `.env` value a reset returns to."""

    key: str
    group: str
    label: str
    help: str
    kind: str
    value: Any
    default: Any
    overridden: bool
    minimum: str | None = None
    maximum: str | None = None
    choices: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class RuntimeSettingListResponse(BaseModel):
    #: How long other processes may take to see a change. Shown in the UI
    #: rather than left as a surprise, as ADR-156 does for API keys.
    propagation_seconds: int
    items: list[RuntimeSettingResponse]


class RuntimeSettingUpdateRequest(BaseModel):
    """A batch, validated as a whole. `null` resets a setting to `.env`."""

    changes: dict[str, Any] = Field(min_length=1)
