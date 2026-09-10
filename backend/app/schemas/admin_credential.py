"""Admin credential schemas (ADR-156).

Note what is absent: no response model anywhere carries the key itself.
`hint` is four characters, enough to tell two keys apart and not enough
to be one.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ApiCredentialResponse(BaseModel):
    name: str
    description: str
    #: True when a usable key exists from either source - the UI shows a
    #: working integration as working even if the value lives in `.env`.
    is_set: bool
    #: Which source is live: "database" (stored here), "environment"
    #: (falling back to `.env`), or "unset". Without this, a key working
    #: fine from `.env` would be indistinguishable from a stored one, and
    #: clearing it would look like a no-op.
    source: Literal["database", "environment", "unset"]
    #: Last four characters, or null when unset.
    hint: str | None
    updated_at: datetime | None
    #: Username of whoever last stored it; null for environment values.
    updated_by: str | None


class ApiCredentialListResponse(BaseModel):
    #: False when `CREDENTIAL_ENCRYPTION_KEY` is unset - editing is
    #: impossible and the UI needs to say why rather than fail on submit.
    storage_enabled: bool
    items: list[ApiCredentialResponse]


class ApiCredentialUpdateRequest(BaseModel):
    #: No maximum: vendor key formats vary and an arbitrary cap would
    #: reject a legitimate key. `min_length` catches an empty submit,
    #: which should be a DELETE (clear) rather than a PUT of "".
    value: str = Field(min_length=8, examples=["your-api-key"])
