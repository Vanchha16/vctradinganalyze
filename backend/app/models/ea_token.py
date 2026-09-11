import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Uuid, false, true
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

    # --- ADR-163: settings the website pushes to this terminal ----------
    #: Defaults match the EA's own input defaults, so a token that was
    #: never configured changes nothing about how its EA behaves.
    paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    dry_run: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    lot_size: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.01"), server_default="0.01"
    )
    max_open_trades: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    max_slippage_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, server_default="50"
    )
    #: Bumped on each change. The EA echoes back the version it applied.
    settings_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    settings_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- ADR-163: what the terminal last reported about itself ----------
    #: Written from `X-EA-*` headers on feed polls; null until an EA 1.20
    #: or later has polled. `effective_*` is what the EA is actually doing
    #: after its own limits - e.g. live saved here, but not allowed there.
    ea_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ea_max_lot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    ea_allow_remote_live: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    applied_settings_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effective_dry_run: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    effective_paused: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
