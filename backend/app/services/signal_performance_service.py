from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Row
from sqlalchemy.orm import InstrumentedAttribute

from app.config import settings
from app.models.enums import SignalStatus
from app.models.signal import Signal
from app.repositories.signal_repository import SignalRepository
from app.schemas.admin_performance import (
    AdminPerformanceResponse,
    FillBreakdownRow,
    FillMetrics,
    OpenStateCounts,
    PerformanceBreakdownRow,
    PerformanceMetrics,
    ReplacementSummary,
)
from app.services.signal_confirmation_service import REPLACED_REASON

_ZERO = Decimal("0")

#: Lower inclusive, upper exclusive.
#:
#: `Signal.confidence` is copied straight from `AIAnalysis.confidence_score`
#: (`signal_engine.py`), which is a **0-100** score, not a 0-1 fraction -
#: docs/04's example is `87.0`, and real rows range 56 to 88. Banding it as
#: if it were 0-1 is not a visible failure: every trade simply falls outside
#: every band and lands in the unmatched group, leaving a breakdown that
#: renders perfectly and says nothing. 100.01 as the top bound keeps a
#: perfect 100 inside the highest band rather than dropping it there too.
CONFIDENCE_BANDS: tuple[tuple[str, float, float], ...] = (
    ("<60", 0.0, 60.0),
    ("60-69", 60.0, 70.0),
    ("70-79", 70.0, 80.0),
    ("80+", 80.0, 100.01),
)

#: ADR-168's comparison, stated rather than guessed at. See
#: `SignalRepository.count_replaced`.
REPLACEMENT_NOTE = (
    "Signals replaced before they filled are counted here, but replacement "
    "performance cannot be compared: a replaced signal is cancelled and never "
    "filled, so it has no outcome, and the signal that replaced it is recorded "
    "in no column. Answering ADR-174's replacement question would need a column "
    "marking a signal as a replacement, which ADR-174 did not add."
)


class SignalPerformanceService:
    """Did the stored signals work (ADR-174)?

    Mirrors `AdminSystemService`'s shape: a constructor-injected
    repository, one public method per use case. Owns the arithmetic the
    repository deliberately does not - every ratio here has a
    zero-denominator case that must read as `None` rather than a
    confident-looking `0`.

    Read-only end to end. Nothing is written, nothing is cached, and
    every figure is recomputed per request - a stale win rate is worse
    than a slow one, and at a few hundred rows this is a handful of
    aggregate queries.

    What it does not do: it reports what happened to the signals that
    were stored. It does not re-decide trades the monitor and the EA
    already settled, and it is not a backtest of anything that was not
    actually run.
    """

    def __init__(self, signal_repository: SignalRepository) -> None:
        self._signals = signal_repository

    def get_performance(self, *, now: datetime | None = None) -> AdminPerformanceResponse:
        epoch = settings.signal_metrics_epoch
        as_of = now or datetime.now(UTC)

        fills = self._fill_metrics(self._signals.fill_counts(epoch))

        return AdminPerformanceResponse(
            epoch=epoch,
            generated_at=as_of,
            overall=self._metrics(self._signals.performance_totals(epoch)),
            closed_without_outcome=self._signals.count_by_effective_status(
                epoch, SignalStatus.CLOSED, as_of
            ),
            open_state=OpenStateCounts(
                active=self._signals.count_by_effective_status(epoch, SignalStatus.ACTIVE, as_of),
                expired=self._signals.count_by_effective_status(epoch, SignalStatus.EXPIRED, as_of),
                triggered=self._signals.count_by_effective_status(
                    epoch, SignalStatus.TRIGGERED, as_of
                ),
                closed=self._signals.count_by_effective_status(epoch, SignalStatus.CLOSED, as_of),
            ),
            fills=fills,
            fills_by_signal_type=[
                FillBreakdownRow(key=self._key(row.key), metrics=self._fill_metrics(row))
                for row in self._signals.fill_counts_by_signal_type(epoch)
            ],
            by_strategy=self._breakdown(Signal.strategy, epoch),
            by_timeframe=self._breakdown(Signal.timeframe, epoch),
            by_signal_type=self._breakdown(Signal.signal_type, epoch),
            by_confidence=self._rows(
                self._signals.performance_by_confidence(epoch, CONFIDENCE_BANDS)
            ),
            risk_review=self._rows(self._signals.risk_review_outcomes(epoch)),
            replacements=ReplacementSummary(
                signals_replaced=self._signals.count_replaced(epoch, REPLACED_REASON),
                comparable=False,
                note=REPLACEMENT_NOTE,
            ),
        )

    # --- Arithmetic ------------------------------------------------------

    def _breakdown(
        self, dimension: InstrumentedAttribute[Any], epoch: datetime
    ) -> list[PerformanceBreakdownRow]:
        return self._rows(self._signals.performance_by(epoch, dimension))

    def _rows(self, rows: Sequence[Row[tuple[Any, ...]]]) -> list[PerformanceBreakdownRow]:
        return [
            PerformanceBreakdownRow(key=self._key(row.key), metrics=self._metrics(row))
            for row in rows
        ]

    @staticmethod
    def _key(value: object) -> str | None:
        """A group key as a string, keeping `None` as `None`.

        Enum members (`Timeframe`, `SignalType`) come back from SQLAlchemy
        as the enum, not its value, so they are converted here rather than
        rendering as "SignalType.BUY" in JSON.
        """
        if value is None:
            return None
        if isinstance(value, SignalStatus):
            return value.value
        return getattr(value, "value", None) or str(value)

    @classmethod
    def _metrics(cls, row: Row[tuple[Any, ...]]) -> PerformanceMetrics:
        trades = int(row.trades)
        wins = int(row.wins)
        losses = int(row.losses)
        total_points = cls._decimal(row.total_points)
        win_points = cls._decimal(row.win_points)
        loss_points = cls._decimal(row.loss_points)

        settled = wins + losses
        return PerformanceMetrics(
            trades=trades,
            wins=wins,
            losses=losses,
            # Settled trades only. A CLOSED trade reached neither target,
            # so including it would quietly depress every win rate.
            win_rate=(wins / settled) if settled else None,
            total_points=total_points if trades else None,
            avg_win=(win_points / wins) if wins else None,
            avg_loss=(loss_points / losses) if losses else None,
            expectancy=(total_points / trades) if trades else None,
            # A losing side summing to zero means there is nothing to
            # divide by, not an infinitely good strategy.
            profit_factor=(float(win_points / abs(loss_points)) if loss_points != _ZERO else None),
        )

    @staticmethod
    def _fill_metrics(row: Row[tuple[Any, ...]]) -> FillMetrics:
        created = int(row.created)
        filled = int(row.filled)
        return FillMetrics(
            created=created,
            filled=filled,
            fill_rate=(filled / created) if created else None,
        )

    @staticmethod
    def _decimal(value: object) -> Decimal:
        """`profit_loss` is `Numeric(20, 8)`; SQLite hands the sum back as a
        float, Postgres as a `Decimal`. Normalised here so the arithmetic
        above is exact on both, and rounding is left to the schema."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value or 0))
