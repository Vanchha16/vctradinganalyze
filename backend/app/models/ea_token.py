import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin


class EaToken(Base, UUIDMixin, CreatedAtMixin):
    """A credential a MetaTrader 5 Expert Advisor presents to read the
    signal feed (ADR-161).

    Separate from user sessions on purpose. An EA runs unattended for
    weeks in a terminal the operator may not be watching, so it cannot do
    the login/refresh dance, and a JWT long-lived enough to survive that
    would also be a full session - able to reach every authenticated
    route. This token can reach exactly one: `GET /ea/signals`.
    """

    __tablename__ = "ea_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    #: Operator's label, e.g. "Home PC" or "VPS", so two terminals can be
    #: told apart when revoking one.
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    #: SHA-256 of the raw token (`core.security.hash_token`). Looked up by
    #: exact match, so a salted verify-only hash is ruled out - the same
    #: reasoning as refresh tokens (ADR-023). The raw token is shown once
    #: at creation and never stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    #: Last four characters of the raw token, for recognition only.
    hint: Mapped[str] = mapped_column(String(8), nullable=False)

    #: When an EA last authenticated with this token - how the operator
    #: tells a live terminal from a forgotten one. Written at most once a
    #: minute, not on every poll.
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
