from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class SystemSetting(Base, UUIDMixin, TimestampMixin):
    """A single configurable key/value pair (see docs/03 §15)."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
