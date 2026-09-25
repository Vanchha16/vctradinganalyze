"""ADR-183 - persistence for the smc-ict-crt-v1 state machine."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.models.ea_execution_event import EaExecutionEvent
from app.models.enums import SignalStatus
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup, SmcSetupState
from app.repositories.base import BaseRepository

#: A setup that may still do something: it has not reached a terminal state.
PENDING_STATES = (
    SmcSetupState.CRT_ANCHOR_CONFIRMED,
    SmcSetupState.RAID_CONFIRMED,
    SmcSetupState.WAITING_FOR_M5_MSS,
    SmcSetupState.MSS_CONFIRMED,
    SmcSetupState.ENTRY_ZONE_CONFIRMED,
    SmcSetupState.SIGNAL_CREATED,
)


class SmcSetupRepository(BaseRepository[SmcSetup]):
    model = SmcSetup

    def create(self, setup: SmcSetup) -> SmcSetup:
        self.session.add(setup)
        self.session.flush()
        return setup

    def get_by_anchor(self, asset_id: uuid.UUID, anchor_t: datetime) -> SmcSetup | None:
        """The row for one anchor candle - how a restarted worker knows it
        has already evaluated this H4 candle."""
        return self.session.execute(
            select(SmcSetup).where(SmcSetup.asset_id == asset_id, SmcSetup.anchor_t == anchor_t)
        ).scalars().first()

    def pending_with_signal(self, asset_id: uuid.UUID) -> Sequence[SmcSetup]:
        return self.session.execute(
            select(SmcSetup)
            .where(SmcSetup.asset_id == asset_id, SmcSetup.state.in_(PENDING_STATES))
            .order_by(SmcSetup.anchor_t.asc())
        ).scalars().all()

    def open_signal_count(self, asset_id: uuid.UUID, strategy: str) -> int:
        """Open signals belonging to one strategy: the "one trade at a time"
        check, scoped so another strategy's rows never block or unblock
        this one.

        Only ACTIVE (a pending broker order) and TRIGGERED (an open position)
        count. A signal refused at execution is written or moved to CANCELLED
        (audit D2/D3), so it can never hold the one-trade capacity (audit D4)."""
        return int(self.session.execute(
            select(func.count()).select_from(Signal).where(
                Signal.asset_id == asset_id,
                Signal.strategy == strategy,
                Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TRIGGERED]),
            )
        ).scalar_one())

    def had_live_position(self, signal_id: uuid.UUID) -> bool:
        """Whether a live (not dry-run) EA ever opened a broker position for
        this signal - the difference between a real trade and a paper one
        (audit D3). A signal the website marked filled from Twelve Data
        candles alone never had a broker position."""
        return bool(self.session.execute(
            select(func.count()).select_from(EaExecutionEvent).where(
                EaExecutionEvent.signal_id == signal_id,
                EaExecutionEvent.event_type == "position_opened",
                EaExecutionEvent.dry_run.is_(False),
            )
        ).scalar_one())

    def recent(self, asset_id: uuid.UUID, *, limit: int = 50) -> Sequence[SmcSetup]:
        return self.session.execute(
            select(SmcSetup).where(SmcSetup.asset_id == asset_id)
            .order_by(SmcSetup.anchor_t.desc()).limit(limit)
        ).scalars().all()
