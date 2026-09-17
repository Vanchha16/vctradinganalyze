from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

#: Returned verbatim in every response (ADR-174). `profit_loss` is
#: `closed_price - entry_price`, inverted for a SELL - a price distance,
#: not money. Summing it assumes one symbol and one position size, true
#: today and false the moment either changes. The field is named
#: `total_points` for the same reason; do not "improve" either.
POINTS_NOTE = (
    "P&L is price points (close minus entry), not currency. Summing it assumes "
    "every trade carried the same position size and the same tick value - true "
    "while this account trades one symbol at one lot size, and wrong as soon as "
    "it does not. These are not dollars."
)


class PerformanceMetrics(BaseModel):
    """One block of outcome arithmetic, for the whole set or one breakdown
    row (ADR-174).

    Every ratio is optional and is `None`, never `0`, when its denominator
    is zero: a 0% win rate and "no trades yet" are different facts, and a
    reader must be able to tell them apart. `trades` is required, because
    a rate without its denominator is not a result - 28 filled trades
    exist in total, so most breakdowns here have single-digit `n`.
    """

    #: Filled trades only (`triggered_at IS NOT NULL`). May exceed
    #: `wins + losses`: a live trade past its TTL reads as CLOSED with no
    #: P&L and is neither (see `closed` on the response).
    trades: int
    wins: int = 0
    losses: int = 0
    win_rate: float | None = None
    total_points: Decimal | None = None
    avg_win: Decimal | None = None
    avg_loss: Decimal | None = None
    expectancy: Decimal | None = None
    profit_factor: float | None = None


class PerformanceBreakdownRow(BaseModel):
    """A breakdown row: the group it describes, plus its own metrics.

    `key` is `None` for a real group with no value - a signal predating
    the `strategy` column, or an analysis where the risk review never ran.
    Those rows are labelled by the reader, never dropped.
    """

    key: str | None
    metrics: PerformanceMetrics


class FillMetrics(BaseModel):
    """How many signals became trades. `fill_rate` is `None` when nothing
    was created, for the same reason every other ratio here is."""

    created: int
    filled: int
    fill_rate: float | None = None


class FillBreakdownRow(BaseModel):
    key: str | None
    metrics: FillMetrics


class OpenStateCounts(BaseModel):
    """Counts by the status a reader sees at request time (ADR-088),
    never the stored column - an unfilled signal past its TTL is stored
    ACTIVE but is really EXPIRED."""

    active: int
    expired: int
    triggered: int
    #: Live trades past `signal_triggered_ttl_hours` that reached neither
    #: target. Real filled trades with null P&L: counted in `trades`, and
    #: in neither `wins` nor `losses`.
    closed: int


class ReplacementSummary(BaseModel):
    """ADR-168, as far as the schema can actually answer it.

    `signals_replaced` is queryable. The comparison ADR-174 asked for -
    how replacements performed against what they replaced - is not: a
    replaced signal is cancelled and unfilled, so it has no outcome, and
    the signal that replaced it is marked in no column. `comparable` says
    so in the response rather than letting a reader assume the absence of
    a number means zero.
    """

    signals_replaced: int
    comparable: bool = False
    note: str


class AdminPerformanceResponse(BaseModel):
    """`GET /admin/performance` (ADR-174) - did the stored signals work.

    Answers that question and only that one: it reports what happened, it
    does not re-adjudicate trades the monitor already settled, and it
    implies no backtest of any strategy that was not run.

    `epoch` and `points_note` are required and always present. A caller
    must never be able to read a rate without knowing what it excludes or
    what units it is in.
    """

    epoch: datetime
    points_note: str = Field(default=POINTS_NOTE)
    generated_at: datetime

    overall: PerformanceMetrics
    #: Filled trades that reached neither target before their TTL. Stated
    #: separately so a reader can see why `wins + losses` may be less than
    #: `overall.trades`.
    closed_without_outcome: int
    open_state: OpenStateCounts

    fills: FillMetrics
    fills_by_signal_type: list[FillBreakdownRow]

    by_strategy: list[PerformanceBreakdownRow]
    by_timeframe: list[PerformanceBreakdownRow]
    by_signal_type: list[PerformanceBreakdownRow]
    by_confidence: list[PerformanceBreakdownRow]

    #: ADR-167 - outcomes split by the risk review's verdict, the
    #: comparison that decides whether the review is enforced or switched
    #: off.
    risk_review: list[PerformanceBreakdownRow]
    replacements: ReplacementSummary
