import uuid
from collections.abc import Collection, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Row, and_, case, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.enums import SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.repositories.base import BaseRepository


def _status_clause(status: SignalStatus, as_of: datetime | None) -> ColumnElement[bool]:
    """Rows with `status` - stored, or as a reader sees it at `as_of`.

    With `as_of` this is `status_resolver.effective_status` in SQL, so a list
    filtered by status agrees with the status each row shows (docs/04
    `GET /signals`). Workers pass no `as_of`: they need stored rows, such as a
    DRAFT past its window that the confirmation task still has to cancel."""
    stored = Signal.status == status
    if as_of is None:
        return stored

    draft_over = and_(
        Signal.status == SignalStatus.DRAFT,
        Signal.created_at <= as_of - timedelta(hours=settings.signal_confirmation_window_hours),
    )
    active_over = and_(
        Signal.status == SignalStatus.ACTIVE,
        Signal.created_at <= as_of - timedelta(hours=settings.signal_ttl_hours),
    )
    triggered_over = and_(
        Signal.status == SignalStatus.TRIGGERED,
        Signal.triggered_at.is_not(None),
        Signal.triggered_at <= as_of - timedelta(hours=settings.signal_triggered_ttl_hours),
    )
    if status is SignalStatus.DRAFT:
        return and_(stored, ~draft_over)
    if status is SignalStatus.CANCELLED:
        return or_(stored, draft_over)
    if status is SignalStatus.ACTIVE:
        return and_(stored, ~active_over)
    if status is SignalStatus.EXPIRED:
        return or_(stored, active_over)
    if status is SignalStatus.TRIGGERED:
        return and_(stored, ~triggered_over)
    if status is SignalStatus.CLOSED:
        return or_(stored, triggered_over)
    return stored


class SignalRepository(BaseRepository[Signal]):
    model = Signal

    def create(self, signal: Signal) -> Signal:
        self.session.add(signal)
        self.session.flush()
        return signal

    def get_by_id(self, signal_id: uuid.UUID) -> Signal | None:
        return self.session.get(Signal, signal_id)

    def find_paginated(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        timeframe: Timeframe | None = None,
        status: SignalStatus | None = None,
        as_of: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Signal]:
        """`timeframe` (docs/52 §2, added for AI Chat's "latest signal for
        this asset/timeframe" grounding lookup) is additive - every
        existing caller omits it and gets the prior unfiltered behavior.
        `as_of` matches `status` as readers see it then (`_status_clause`)."""
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(Signal.timeframe == timeframe)
        if status is not None:
            query = query.where(_status_clause(status, as_of))
        query = query.order_by(Signal.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        timeframe: Timeframe | None = None,
        status: SignalStatus | None = None,
        as_of: datetime | None = None,
    ) -> int:
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(Signal.timeframe == timeframe)
        if status is not None:
            query = query.where(_status_clause(status, as_of))
        return self._count(query)

    def list_by_ids(self, signal_ids: Collection[uuid.UUID]) -> Sequence[Signal]:
        """Batch lookup - one query for a page of EA events or a batch of
        reports, instead of one per row (ADR-162)."""
        if not signal_ids:
            return []
        return self.session.execute(select(Signal).where(Signal.id.in_(signal_ids))).scalars().all()

    def find_open_for_asset(
        self, asset_id: uuid.UUID, *, created_since: datetime
    ) -> Sequence[Signal]:
        """Stored ACTIVE/TRIGGERED signals for one asset, newest first -
        the MT5 EA feed's candidates (ADR-161). Stored status only: the
        caller still applies `status_resolver.effective_status`, since an
        ACTIVE row can already be EXPIRED at read time (ADR-088)."""
        query = (
            select(Signal)
            .where(
                Signal.asset_id == asset_id,
                Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TRIGGERED]),
                Signal.created_at >= created_since,
            )
            .order_by(Signal.created_at.desc())
        )
        return self.session.execute(query).scalars().all()

    def count_since(self, since: datetime) -> int:
        """Today's "signals generated" count (docs/58 §3.2, `GET
        /admin/system`)."""
        query = select(func.count()).select_from(Signal).where(Signal.created_at >= since)
        return self.session.execute(query).scalar_one()

    def list_status_times_since(
        self, since: datetime
    ) -> Sequence[Row[tuple[SignalStatus, datetime, datetime | None]]]:
        """`(status, created_at, triggered_at)` of every signal since `since`,
        for the Telegram bot's Summary Report button (§13). The caller
        counts them by the status a reader sees, which a stored-status
        GROUP BY cannot give: an unfilled signal past its TTL is still
        stored ACTIVE (ADR-088)."""
        query = select(Signal.status, Signal.created_at, Signal.triggered_at).where(
            Signal.created_at >= since
        )
        return self.session.execute(query).all()

    def sum_profit_loss_since(self, since: datetime) -> Decimal:
        """Total realized P&L since `since`, for the same Summary Report
        use case above. `profit_loss` is only ever set once a signal
        closes (SUCCESSFUL/STOPPED_OUT) - still-open signals contribute
        nothing, not a NULL that would poison the sum."""
        query = select(func.coalesce(func.sum(Signal.profit_loss), 0)).where(
            Signal.created_at >= since
        )
        return Decimal(str(self.session.execute(query).scalar_one()))

    def count_by_signal_type(self) -> dict[SignalType, int]:
        """ "Recommendation distribution" (docs/58 §3.2, `GET
        /admin/analytics`) - `signals` has no `recommendation` column
        (that field lives on `ai_analysis`); `signal_type` (BUY/SELL) is
        the closest actual field on this table and the only one a
        distribution grouped "on signals" can mean, since a `Signal` row
        only ever exists for a BUY/SELL outcome in the first place
        (ADR-086 - WAIT produces no `Signal` row to count). Recorded as an
        inferred reading of docs/58's wording, not a literal match, in
        ADR-130."""
        query = select(Signal.signal_type, func.count()).group_by(Signal.signal_type)
        return {signal_type: count for signal_type, count in self.session.execute(query)}

    # --- Performance metrics (ADR-174) -----------------------------------
    #
    # Every method here filters `created_at >= epoch`. Signals before it
    # predate ADR-137's TRIGGERED gate and carry outcomes current code
    # cannot produce; counted in, they drag the BUY fill rate from 56% to
    # 14%. The epoch is `settings.signal_metrics_epoch`, passed in rather
    # than read here so a test can pin it.
    #
    # Aggregated in SQL, not by loading rows into Python. The one thing SQL
    # must not be trusted with is stored status standing in for the status
    # a reader sees (ADR-088) - `_status_clause` above is exactly that
    # resolution expressed in SQL, and the open/expired/closed counts use
    # it.

    @staticmethod
    def _filled(epoch: datetime) -> ColumnElement[bool]:
        """A trade that actually happened: created at or after the epoch,
        and filled. `triggered_at IS NOT NULL` is not optional - it is what
        keeps the pre-epoch rows' impossible state (stored SUCCESSFUL with
        no fill) out of every average."""
        return and_(Signal.created_at >= epoch, Signal.triggered_at.is_not(None))

    @staticmethod
    def _outcome_columns() -> tuple[ColumnElement[Any], ...]:
        """The six raw numbers every performance breakdown is built from.

        Counts and sums only - no ratios. Win rate, expectancy and profit
        factor are the service's job, because each has a zero-denominator
        case that must read as None rather than a misleading 0 (ADR-174),
        and SQL has no way to say "undefined" that survives the trip.
        """
        won = Signal.status == SignalStatus.SUCCESSFUL
        lost = Signal.status == SignalStatus.STOPPED_OUT
        return (
            func.count().label("trades"),
            func.coalesce(func.sum(case((won, 1), else_=0)), 0).label("wins"),
            func.coalesce(func.sum(case((lost, 1), else_=0)), 0).label("losses"),
            func.coalesce(func.sum(Signal.profit_loss), 0).label("total_points"),
            func.coalesce(func.sum(case((won, Signal.profit_loss), else_=0)), 0).label(
                "win_points"
            ),
            func.coalesce(func.sum(case((lost, Signal.profit_loss), else_=0)), 0).label(
                "loss_points"
            ),
        )

    def performance_totals(self, epoch: datetime) -> Row[tuple[Any, ...]]:
        """Every filled trade since `epoch`, as one row of raw counts and
        sums."""
        query = select(*self._outcome_columns()).where(self._filled(epoch))
        return self.session.execute(query).one()

    def performance_by(
        self, epoch: datetime, dimension: InstrumentedAttribute[Any]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        """The same numbers grouped by one column - `Signal.strategy`,
        `Signal.timeframe` or `Signal.signal_type`.

        The dimension is a mapped column, not a string name, so a typo is
        a mypy error rather than a runtime one. A NULL key (a signal
        from before `strategy` existed) comes back as `None` and is the
        caller's to label - it is a real group, not a row to drop.
        """
        query = (
            select(dimension.label("key"), *self._outcome_columns())
            .where(self._filled(epoch))
            .group_by(dimension)
        )
        return self.session.execute(query).all()

    def performance_by_confidence(
        self, epoch: datetime, bands: Sequence[tuple[str, float, float]]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        """The same numbers grouped into `(label, lower, upper)` confidence
        bands - lower inclusive, upper exclusive, in the order given.

        A confidence matching no band lands under `None`, which keeps a
        badly-specified band list visible instead of quietly dropping
        trades out of a breakdown that still looks complete.
        """
        band_case = case(
            *[
                (and_(Signal.confidence >= lower, Signal.confidence < upper), label)
                for label, lower, upper in bands
            ],
            else_=None,
        )
        query = (
            select(band_case.label("key"), *self._outcome_columns())
            .where(self._filled(epoch))
            .group_by(band_case)
        )
        return self.session.execute(query).all()

    def fill_counts(self, epoch: datetime) -> Row[tuple[Any, ...]]:
        """Signals created since `epoch` versus those that filled - the
        fill rate's two numbers, and the pair the pre-epoch rows distort
        most badly."""
        query = select(
            func.count().label("created"),
            func.coalesce(func.sum(case((Signal.triggered_at.is_not(None), 1), else_=0)), 0).label(
                "filled"
            ),
        ).where(Signal.created_at >= epoch)
        return self.session.execute(query).one()

    def fill_counts_by_signal_type(self, epoch: datetime) -> Sequence[Row[tuple[Any, ...]]]:
        """Fill counts split BUY/SELL - the split that exposed the
        pre-epoch problem in the first place."""
        query = (
            select(
                Signal.signal_type.label("key"),
                func.count().label("created"),
                func.coalesce(
                    func.sum(case((Signal.triggered_at.is_not(None), 1), else_=0)), 0
                ).label("filled"),
            )
            .where(Signal.created_at >= epoch)
            .group_by(Signal.signal_type)
        )
        return self.session.execute(query).all()

    def count_by_effective_status(
        self, epoch: datetime, status: SignalStatus, as_of: datetime
    ) -> int:
        """How many signals read as `status` at `as_of` (ADR-088), not how
        many are stored that way. Reading the stored column here is the
        exact bug recorded in BACKLOG.md: an unfilled signal past its TTL
        showed under "active" and never under "expired"."""
        query = (
            select(func.count())
            .select_from(Signal)
            .where(Signal.created_at >= epoch, _status_clause(status, as_of))
        )
        return self.session.execute(query).scalar_one()

    def risk_review_outcomes(self, epoch: datetime) -> Sequence[Row[tuple[Any, ...]]]:
        """Filled-trade outcomes split by the ADR-167 review verdict on the
        analysis behind each signal.

        `risk_review_verdict` is "approve", "veto" or NULL (review off, or
        the call failed). NULL stays its own group rather than being merged
        into either - "we never asked" is not the same claim as "it
        approved", and whether the review's opinion tracks the outcome is
        the entire question.
        """
        query = (
            select(AIAnalysis.risk_review_verdict.label("key"), *self._outcome_columns())
            .join(AIAnalysis, Signal.analysis_id == AIAnalysis.id)
            .where(self._filled(epoch))
            .group_by(AIAnalysis.risk_review_verdict)
        )
        return self.session.execute(query).all()

    def count_replaced(self, epoch: datetime, replaced_reason: str) -> int:
        """How many signals ADR-168 replaced before they filled.

        A count, deliberately not an outcome comparison: a replaced signal
        is cancelled and unfilled by definition, so it has no win or loss
        to compare against. The signal that did the replacing carries only
        its generic confirmation reason and is marked in no column, so
        "did replacements do better than what they replaced" is not
        answerable from this schema. The service says so in the response
        rather than guessing at it.
        """
        query = (
            select(func.count())
            .select_from(Signal)
            .where(Signal.created_at >= epoch, Signal.status_reason == replaced_reason)
        )
        return self.session.execute(query).scalar_one()
