import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class ApiCredential(Base, UUIDMixin, TimestampMixin):
    """One externally-issued API key, editable from the admin UI (ADR-156).

    Deliberately a separate table from `system_settings`: that one holds
    plain operational bookkeeping (the Telegram polling cursor) and is read
    without ceremony. These rows are **credentials** - encrypted at rest,
    write-only over the API, super-admin gated, and audit-logged on every
    change. Mixing the two would invite a future `get_by_key()` that
    returns a secret to a caller that only wanted a setting.
    """

    __tablename__ = "api_credentials"

    #: Stable identifier, e.g. "twelve_data", "news_api". Matches the
    #: `Settings` field name minus the `_api_key`/`_token` suffix - see
    #: `credential_resolver._FALLBACKS` for the mapping.
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    #: Fernet ciphertext, never the raw key. Decryptable only with
    #: `CREDENTIAL_ENCRYPTION_KEY` from the environment, so a leaked
    #: database dump - `~/deploy_backups` holds one per deploy - does not
    #: hand over live keys.
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)

    #: Last four characters of the plaintext, stored separately so the UI
    #: can show "••••e1og" for recognition without ever decrypting. Four
    #: characters of a 40-character key is not a meaningful disclosure and
    #: is the difference between "which key is this?" and guesswork.
    hint: Mapped[str] = mapped_column(String(8), nullable=False)

    #: Who last wrote it. Nullable because a `SET NULL` on user deletion is
    #: preferable to losing the credential row itself.
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
