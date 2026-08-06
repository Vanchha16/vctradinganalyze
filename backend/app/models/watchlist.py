import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin


class Watchlist(Base, UUIDMixin, CreatedAtMixin):
    """A user's named list of assets (docs/03 §12, docs/58 §2.1, ADR-114).

    `name` is the only mutable field and no other column ever changes after
    creation, so `CreatedAtMixin` (not `TimestampMixin`) is used - the same
    "nothing here needs `updated_at`" reasoning already applied to
    `SignalBookmark` (ADR-090)."""

    __tablename__ = "watchlists"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
