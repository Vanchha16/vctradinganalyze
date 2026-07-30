import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """Gives a model a UUID primary key, generated client-side."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Gives a model UTC-aware created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreatedAtMixin:
    """Gives a model a single UTC-aware created_at column.

    For append-only / immutable rows (e.g. audit logs) where an updated_at
    would contradict the table's purpose.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
