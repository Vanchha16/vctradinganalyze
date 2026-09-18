"""Reading and changing runtime strategy/signal settings (ADR-178).

Mirrors `AdminCredentialService`: constructor-injected repositories, one
public method per use case, every change written to the audit log.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.exceptions import ValidationException
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.system_setting_repository import SystemSettingRepository
from app.services import runtime_settings
from app.services.runtime_settings import (
    BY_FIELD,
    KEY_PREFIX,
    REGISTRY,
    RuntimeSetting,
    RuntimeSettingError,
    env_default,
    storage_key,
)


@dataclass(frozen=True)
class RuntimeSettingStatus:
    spec: RuntimeSetting
    value: Any
    default: Any
    overridden: bool
    updated_at: datetime | None


class AdminRuntimeSettingsService:
    def __init__(
        self,
        setting_repository: SystemSettingRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._settings = setting_repository
        self._audit = audit_log_repository

    def list_status(self) -> list[RuntimeSettingStatus]:
        """Every managed setting as the database says it is right now -
        read directly, not from this process's 30-second overlay cache, so
        the page never shows a value that another process has since
        changed."""
        rows = {row.key: row for row in self._settings.list_by_prefix(KEY_PREFIX)}
        statuses = []
        for spec in REGISTRY:
            row = rows.get(storage_key(spec.field))
            value = env_default(spec.field)
            if row is not None:
                try:
                    value = spec.parse(row.value)
                except RuntimeSettingError:
                    row = None  # unreadable stored value: report the default in force
            statuses.append(
                RuntimeSettingStatus(
                    spec=spec,
                    value=value,
                    default=env_default(spec.field),
                    overridden=row is not None,
                    updated_at=row.updated_at if row is not None else None,
                )
            )
        return statuses

    def apply(
        self, actor: User, changes: dict[str, Any], *, ip_address: str | None = None
    ) -> list[RuntimeSettingStatus]:
        """Validate the whole batch, then store it and audit each change.

        `None` resets a setting to `.env`. An invalid batch raises before
        anything is written. A change that would not alter the effective
        value is skipped, so the audit log records only real changes.
        """
        current = {s.spec.field: s.value for s in self.list_status()}
        try:
            parsed = runtime_settings.validate_batch(changes, current)
        except RuntimeSettingError as exc:
            raise ValidationException(str(exc)) from exc

        for name, value in parsed.items():
            spec = BY_FIELD[name]
            row = self._settings.get_by_key(storage_key(name))
            old = current[name]
            if value is None:
                if row is None:
                    continue
                self._settings.delete(row)
                new = env_default(name)
                action, resource_id = "runtime_setting_reset", None
            else:
                if row is not None and spec.parse(row.value) == value:
                    continue
                if row is None and value == old:
                    continue
                row = self._settings.upsert(storage_key(name), spec.serialize(value))
                new = value
                action, resource_id = "runtime_setting_changed", row.id

            self._audit.create(
                AuditLog(
                    user_id=actor.id,
                    action=action,
                    resource="system_setting",
                    resource_id=resource_id,
                    ip_address=ip_address,
                    context={
                        "setting": name,
                        "old": spec.serialize(old),
                        "new": spec.serialize(new),
                    },
                )
            )

        self._settings.commit()
        # This process takes the change at once; the others within the
        # overlay's cache window.
        runtime_settings.refresh(
            force=True,
            loader=lambda: {
                row.key: row.value for row in self._settings.list_by_prefix(KEY_PREFIX)
            },
        )
        return self.list_status()
