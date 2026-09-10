"""Admin-facing credential management (ADR-156).

Mirrors `AdminUserService`'s shape: injected repositories, one public
method per use case, private `_audit`/`_commit` helpers.

**Read paths never return a secret.** `list_status` reports only whether
a key is set, its last four characters, and who changed it when. There is
deliberately no "reveal" endpoint anywhere in this project: a stored key
travels in one direction, from the operator to a vendor, and a route that
hands it back is a route an attacker can use too.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

import structlog

from app.core import credential_crypto
from app.models.api_credential import ApiCredential
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.api_credential_repository import ApiCredentialRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.services import credential_resolver
from app.services.credential_resolver import FALLBACK_SETTING, CredentialName

logger = structlog.get_logger(__name__)

#: Shown in the UI so an operator knows what each key is for without
#: looking it up. Order here is the display order.
DESCRIPTIONS: dict[CredentialName, str] = {
    "twelve_data": "Market data - candles, prices, indicators.",
    "news_api": "News articles for sentiment analysis.",
    "openai": "AI narration on analyses and signals.",
    "telegram_bot": "Telegram bot that delivers signals.",
}


class CredentialStatus:
    """What the admin UI is allowed to know about one credential."""

    def __init__(
        self,
        name: str,
        description: str,
        is_set: bool,
        source: Literal["database", "environment", "unset"],
        hint: str | None,
        updated_at: datetime | None,
        updated_by: str | None,
    ) -> None:
        self.name = name
        self.description = description
        self.is_set = is_set
        self.source = source
        self.hint = hint
        self.updated_at = updated_at
        self.updated_by = updated_by


class AdminCredentialService:
    def __init__(
        self,
        credential_repository: ApiCredentialRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._credential_repository = credential_repository
        self._audit_log_repository = audit_log_repository

    def list_status(self) -> list[CredentialStatus]:
        """One row per managed credential, whether stored or not.

        Always returns the full set rather than only stored rows, so the
        UI shows "not set" for a key nobody has configured instead of
        silently omitting it.
        """
        stored = {row.name: row for row in self._credential_repository.list_all()}

        statuses: list[CredentialStatus] = []
        for name, description in DESCRIPTIONS.items():
            row = stored.get(name)
            if row is not None:
                statuses.append(
                    CredentialStatus(
                        name=name,
                        description=description,
                        is_set=True,
                        source="database",
                        hint=row.hint,
                        updated_at=row.updated_at,
                        updated_by=self._actor_label(row.updated_by_id),
                    )
                )
                continue

            # No row: the environment is still the live source, and the UI
            # must say so - otherwise "not set" would look like a broken
            # integration when the provider is working fine off `.env`.
            env_value = credential_resolver.resolve(name)
            statuses.append(
                CredentialStatus(
                    name=name,
                    description=description,
                    is_set=bool(env_value),
                    source="environment" if env_value else "unset",
                    hint=credential_crypto.hint_for(env_value) if env_value else None,
                    updated_at=None,
                    updated_by=None,
                )
            )
        return statuses

    def set_credential(
        self,
        actor: User,
        name: CredentialName,
        value: str,
        *,
        ip_address: str | None = None,
    ) -> ApiCredential:
        """Store or replace one key. The plaintext is never logged, never
        audited, and never returned - only its last four characters."""
        row = self._credential_repository.get_by_name(name)
        hint = credential_crypto.hint_for(value)
        encrypted = credential_crypto.encrypt(value)

        if row is None:
            row = ApiCredential(
                name=name, encrypted_value=encrypted, hint=hint, updated_by_id=actor.id
            )
            self._credential_repository.create(row)
            action = "admin_credential_created"
        else:
            row.encrypted_value = encrypted
            row.hint = hint
            row.updated_by_id = actor.id
            action = "admin_credential_updated"

        # `hint` only. An audit trail that recorded the value would put
        # every rotated key permanently in a table the UI can read.
        self._audit(actor.id, action=action, context={"credential": name, "hint": hint})
        self._commit()
        credential_resolver.invalidate(name)
        logger.info("admin.credential_set", actor_id=str(actor.id), credential=name)
        return row

    def clear_credential(
        self, actor: User, name: CredentialName, *, ip_address: str | None = None
    ) -> bool:
        """Delete the stored row, falling the key back to its `.env` value.

        Not the same as setting an empty string: this is "stop overriding
        the environment", which is the only way back once a key has been
        stored.
        """
        row = self._credential_repository.get_by_name(name)
        if row is None:
            return False

        self._credential_repository.delete(row)
        self._audit(
            actor.id,
            action="admin_credential_cleared",
            context={"credential": name, "falls_back_to": FALLBACK_SETTING[name]},
        )
        self._commit()
        credential_resolver.invalidate(name)
        logger.info("admin.credential_cleared", actor_id=str(actor.id), credential=name)
        return True

    def _audit(
        self,
        actor_id: uuid.UUID,
        *,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLog(
                user_id=actor_id,
                action=action,
                resource="api_credential",
                resource_id=None,
                context=context,
            )
        )

    def _actor_label(self, user_id: uuid.UUID | None) -> str | None:
        if user_id is None:
            return None
        user = self._credential_repository.session.get(User, user_id)
        return user.username if user is not None else None

    def _commit(self) -> None:
        self._credential_repository.session.commit()


__all__ = ["DESCRIPTIONS", "AdminCredentialService", "CredentialStatus"]
