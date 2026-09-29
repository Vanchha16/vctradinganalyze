"""The server-side one-live-order canary (ADR-184).

Armed through the `ea_one_live_order_canary` runtime setting, the first live
`order_placed` or `position_opened` an EA reports switches that token back to
dry run and disarms the canary - in the same request, in one transaction. It
replaces a polling script that stopped whenever the session running it ended:
here the state is a database row and the trigger is the EA's own report, so
no process has to stay alive.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

import structlog

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.system_setting_repository import SystemSettingRepository
from app.schemas.ea import EaEventIn, EaSettings
from app.services import runtime_settings
from app.services.ea_service import EaPrincipal, EaService
from app.services.runtime_settings import BY_FIELD, KEY_PREFIX, env_default, storage_key

logger = structlog.get_logger(__name__)

CANARY_SETTING = "ea_one_live_order_canary"
#: The reports that mean an order reached, or filled at, the broker.
QUALIFYING_EVENTS = frozenset({"order_placed", "position_opened"})
TRIP_REASON = "tripped by the first live order (ADR-184)"


def is_live_order(events: Sequence[EaEventIn]) -> bool:
    """Whether this batch reports a live order or fill. Judged on the batch
    itself, not only on newly stored events: if tripping failed after the
    events were stored, the EA's re-send - all duplicates by then - must
    still be able to trip it."""
    return any(not e.dry_run and e.event_type in QUALIFYING_EVENTS for e in events)


class EaLiveOrderCanary:
    def __init__(
        self,
        setting_repository: SystemSettingRepository,
        audit_log_repository: AuditLogRepository,
        ea_service: EaService,
    ) -> None:
        self._settings = setting_repository
        self._audit = audit_log_repository
        self._ea = ea_service

    def trip_if_armed(
        self, principal: EaPrincipal, events: Sequence[EaEventIn], now: datetime
    ) -> bool:
        """Put `principal.token` back in dry run and disarm, if armed and the
        batch reports a live order. Returns whether it tripped.

        Reads the canary's own row under a lock, not the 30-second settings
        cache: two batches arriving at once trip it exactly once, and an arm
        made seconds ago is honoured."""
        if not is_live_order(events):
            return False

        spec = BY_FIELD[CANARY_SETTING]
        key = storage_key(CANARY_SETTING)
        row = self._settings.get_by_key_for_update(key)
        armed = spec.parse(row.value) if row is not None else bool(env_default(CANARY_SETTING))
        if not armed:
            self._settings.rollback()  # releases the lock; nothing was changed
            return False

        token = principal.token
        # 1. Disarm first, in the same transaction as the revert below.
        disarmed = self._settings.upsert(key, spec.serialize(False))
        event_type = next(
            e.event_type for e in events if not e.dry_run and e.event_type in QUALIFYING_EVENTS
        )
        self._audit.create(
            AuditLog(
                user_id=None,
                action="runtime_setting_changed",
                resource="system_setting",
                resource_id=disarmed.id,
                context={
                    "setting": CANARY_SETTING,
                    "old": spec.serialize(True),
                    "new": spec.serialize(False),
                    "reason": TRIP_REASON,
                    "token_id": str(token.id),
                    "event_type": event_type,
                },
            )
        )
        # 2. Dry run through the Settings page's own path: every other
        #    setting kept, version bumped, `ea_settings_updated` audited.
        lot = Decimal(token.lot_size)
        if token.ea_max_lot is not None and lot > token.ea_max_lot:
            lot = Decimal(token.ea_max_lot)  # update_settings refuses a lot above it
        self._ea.update_settings(
            principal.user,
            token.id,
            EaSettings(
                paused=token.paused,
                dry_run=True,
                lot_size=float(lot),
                max_open_trades=token.max_open_trades,
                max_slippage_points=token.max_slippage_points,
            ),
            now,
        )
        # update_settings commits, except when the token is already in dry
        # run (a no-op there): this commits the disarm in that case too.
        self._settings.commit()
        runtime_settings.refresh(
            force=True,
            loader=lambda: {r.key: r.value for r in self._settings.list_by_prefix(KEY_PREFIX)},
        )
        logger.warning(
            "ea.canary_tripped",
            token_id=str(token.id),
            event_type=event_type,
            settings_version=token.settings_version,
        )
        return True


__all__ = ["CANARY_SETTING", "QUALIFYING_EVENTS", "EaLiveOrderCanary", "is_live_order"]
