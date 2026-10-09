"""ADR-185 - persistence for the smc-ict-crt-v2 design-A state machine."""

import uuid
from collections.abc import Iterable, Sequence
from datetime import date, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.ea_execution_event import EaExecutionEvent
from app.models.enums import SignalStatus
from app.models.signal import Signal
from app.models.smc_v2_setup import SmcV2Setup, SmcV2State
from app.repositories.base import BaseRepository

#: Fixed key for the transaction-scoped advisory lock that serialises v2 runs
#: on PostgreSQL ("SMC2A" as an integer). Two overlapping runs - a retry, a
#: slow worker, a second beat - can then never both read "slot free / cap not
#: reached" and both publish.
RUN_LOCK_KEY = 0x534D433241

OPEN_SIGNAL_STATUSES = (SignalStatus.ACTIVE, SignalStatus.TRIGGERED)


def acquire_run_lock(session: Session) -> bool:
    """Take the run lock for the current transaction; True when taken.

    PostgreSQL only - `pg_advisory_xact_lock` blocks until free and releases
    at commit or rollback. SQLite (the test suite) serialises writers itself
    and has no such function, so it is skipped there."""
    if session.get_bind().dialect.name != "postgresql":
        return False
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": RUN_LOCK_KEY})
    return True


class SmcV2SetupRepository(BaseRepository[SmcV2Setup]):
    model = SmcV2Setup

    def create(self, setup: SmcV2Setup) -> SmcV2Setup:
        self.session.add(setup)
        self.session.flush()
        return setup

    def get_by_identity(
        self, asset_id: uuid.UUID, strategy: str, design: str, anchor_timeframe: str,
        anchor_t: datetime,
    ) -> SmcV2Setup | None:
        return self.session.execute(
            select(SmcV2Setup).where(
                SmcV2Setup.asset_id == asset_id, SmcV2Setup.strategy == strategy,
                SmcV2Setup.design == design, SmcV2Setup.anchor_timeframe == anchor_timeframe,
                SmcV2Setup.anchor_t == anchor_t,
            )
        ).scalars().first()

    def in_states(
        self, asset_id: uuid.UUID, strategy: str, states: Iterable[SmcV2State]
    ) -> Sequence[SmcV2Setup]:
        return self.session.execute(
            select(SmcV2Setup)
            .where(SmcV2Setup.asset_id == asset_id, SmcV2Setup.strategy == strategy,
                   SmcV2Setup.state.in_([str(s) for s in states]))
            .order_by(SmcV2Setup.anchor_t.asc())
        ).scalars().all()

    def published_on(self, asset_id: uuid.UUID, strategy: str, day: date) -> int:
        """C14: signals this strategy published on one broker trading day.

        Counted from the setup rows, which are never deleted, so a restart
        or retry sees the same count."""
        return int(self.session.execute(
            select(func.count()).select_from(SmcV2Setup).where(
                SmcV2Setup.asset_id == asset_id, SmcV2Setup.strategy == strategy,
                SmcV2Setup.trading_day == day, SmcV2Setup.signal_id.is_not(None),
            )
        ).scalar_one())

    def open_signal(self, asset_id: uuid.UUID, strategies: Iterable[str]) -> Signal | None:
        """C13: the signal holding the one slot, if any - a pending order
        (ACTIVE) or an open trade (TRIGGERED) of any of `strategies`."""
        return self.session.execute(
            select(Signal).where(
                Signal.asset_id == asset_id, Signal.strategy.in_(list(strategies)),
                Signal.status.in_(OPEN_SIGNAL_STATUSES),
            ).order_by(Signal.created_at.asc()).limit(1)
        ).scalars().first()

    def had_live_position(self, signal_id: uuid.UUID) -> bool:
        """Whether a live (not dry-run) EA ever opened a broker position for
        this signal - a real trade rather than a paper one."""
        return bool(self.session.execute(
            select(func.count()).select_from(EaExecutionEvent).where(
                EaExecutionEvent.signal_id == signal_id,
                EaExecutionEvent.event_type == "position_opened",
                EaExecutionEvent.dry_run.is_(False),
            )
        ).scalar_one())

    def recent(
        self, asset_id: uuid.UUID, strategy: str, *, limit: int = 50
    ) -> Sequence[SmcV2Setup]:
        return self.session.execute(
            select(SmcV2Setup)
            .where(SmcV2Setup.asset_id == asset_id, SmcV2Setup.strategy == strategy)
            .order_by(SmcV2Setup.anchor_t.desc()).limit(limit)
        ).scalars().all()
