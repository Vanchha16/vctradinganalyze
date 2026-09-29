"""Swing strategy paper trading (ADR-182).

Runs the frozen rules in `paper_swing.rules` on EURUSD, GBPUSD and USDJPY
and records every setup and every paper trade in `paper_swing_trades`.

**Never connected to execution.** Nothing here writes a `signals` row, a
broker order, a Telegram message or anything the EA reads. The three pairs
are kept *inactive* assets, so the live pipeline (H1/M5 generation, full
market-data collection, the EA feed) never sees them either; the paper task
collects their H4 and D1 candles itself.
"""

import statistics
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog

from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.paper_swing_trade import PaperSwingTrade
from app.models.price_candle import PriceCandle
from app.repositories.asset_repository import AssetRepository
from app.repositories.paper_swing_trade_repository import PaperSwingTradeRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.paper_swing import rules
from app.services.paper_swing.rules import PAIRS, Bar, PairSpec, Setup

logger = structlog.get_logger(__name__)

#: How far back each run looks for H4 bars it has not decided yet. Twice the
#: longest gap a missed run or a late candle should cause; the unique index
#: makes looking again harmless.
DECISION_WINDOW = timedelta(hours=48)
#: Enough closed history for the rules: EMA50 on D1 settles well inside
#: 300 bars, and ATR14/pivots on H4 inside 400.
_H4_HISTORY = 400
_D1_HISTORY = 300

#: Twelve Data requests a day: six H4 runs and one D1 run per pair.
REQUESTS_PER_DAY = len(PAIRS) * 7

#: ADR-182 - what the paper record is compared with. "twelve_data" is the
#: fair baseline: the same rules backtested on Twelve Data's own H4 and D1
#: candles - exactly what this task receives, weekend bars and seasonal H4
#: grid included - reproduced trade for trade by this service. "mt5" is
#: ADR-181's original run on broker candles, kept for reference only.
BACKTEST_REFERENCE: dict[str, dict[str, float]] = {
    "twelve_data": {
        "trades": 108,
        "win_rate": 27.8,
        "avg_r": 0.086,
        "total_r": 9.32,
        "max_drawdown_r": 28.46,
        "profit_factor": 1.11,
        "trades_per_week": 0.86,
    },
    "mt5": {
        "trades": 91,
        "win_rate": 30.8,
        "avg_r": 0.23,
        "total_r": 20.9,
        "max_drawdown_r": 19.9,
        "profit_factor": 1.32,
        "trades_per_week": 0.80,
    },
}


def _utc(moment: datetime) -> datetime:
    # SQLite (tests) returns naive datetimes for timezone-aware columns.
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _to_bars(candles: Iterable[PriceCandle]) -> list[Bar]:
    return [
        Bar(_utc(c.timestamp), float(c.open), float(c.high), float(c.low), float(c.close))
        for c in candles
    ]


def _d(value: float, places: str = "0.0001") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


@dataclass
class EvaluationResult:
    recorded: int = 0
    taken: int = 0
    closed: int = 0


@dataclass(frozen=True)
class Summary:
    trades: int
    open: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float | None
    total_r: float
    avg_r: float | None
    max_drawdown_r: float
    #: Gross R won / gross R lost; None with no losing trade yet.
    profit_factor: float | None
    avg_holding_hours: float | None


@dataclass(frozen=True)
class PaperStatistics:
    started_at: datetime | None
    weeks_running: float
    trades_per_week: float | None
    overall: Summary
    by_pair: dict[str, Summary]
    by_direction: dict[str, Summary]
    rejected: dict[str, int] = field(default_factory=dict)
    skipped_trade_open: int = 0


def summarize(trades: Sequence[PaperSwingTrade]) -> Summary:
    """Closed trades count toward the result; open ones are only counted.
    Drawdown runs over closed trades in the order they were entered, as in
    the backtest."""
    closed = [t for t in trades if t.status in ("win", "loss", "timeout")]
    results = [float(t.result_r or 0) for t in closed]
    wins = sum(1 for t in closed if t.status == "win")
    losses = sum(1 for t in closed if t.status == "loss")
    equity = peak = drawdown = 0.0
    for r in results:
        equity += r
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    hours = [float(t.holding_hours) for t in closed if t.holding_hours is not None]
    gross_loss = -sum(r for r in results if r < 0)
    return Summary(
        trades=len(closed),
        open=sum(1 for t in trades if t.status == "open"),
        wins=wins,
        losses=losses,
        timeouts=sum(1 for t in closed if t.status == "timeout"),
        win_rate=round(100 * wins / (wins + losses), 1) if wins + losses else None,
        total_r=round(sum(results), 2),
        avg_r=round(statistics.mean(results), 3) if results else None,
        max_drawdown_r=round(drawdown, 2),
        profit_factor=(
            round(sum(r for r in results if r > 0) / gross_loss, 2) if gross_loss else None
        ),
        avg_holding_hours=round(statistics.mean(hours), 1) if hours else None,
    )


class PaperSwingService:
    def __init__(
        self,
        asset_repository: AssetRepository,
        price_candle_repository: PriceCandleRepository,
        trade_repository: PaperSwingTradeRepository,
    ) -> None:
        self._assets = asset_repository
        self._candles = price_candle_repository
        self._trades = trade_repository

    # --- assets -----------------------------------------------------------

    def ensure_assets(self) -> list[tuple[PairSpec, Asset]]:
        """The three pairs' assets, created *inactive* if missing. An asset
        an administrator has activated is used as it is, with a warning:
        it is then also traded by the live pipeline, which ADR-182 does not
        intend."""
        pairs: list[tuple[PairSpec, Asset]] = []
        for spec in PAIRS:
            asset = self._assets.get_by_symbol(spec.symbol)
            if asset is None:
                asset = Asset(
                    symbol=spec.symbol,
                    name=spec.name,
                    market_type=MarketType.FOREX,
                    base_currency=spec.base_currency,
                    quote_currency=spec.quote_currency,
                    is_active=False,
                )
                self._assets.session.add(asset)
                self._assets.session.flush()
                logger.info("paper_swing.asset_created", symbol=spec.symbol)
            elif asset.is_active:
                logger.warning("paper_swing.asset_is_active", symbol=spec.symbol)
            pairs.append((spec, asset))
        return pairs

    # --- evaluation -------------------------------------------------------

    def evaluate(self, spec: PairSpec, asset: Asset, now: datetime) -> EvaluationResult:
        """Settle this pair's open paper trades, then decide every H4 bar
        closed inside `DECISION_WINDOW` that has not been decided yet."""
        result = EvaluationResult()
        h4 = rules.closed_bars(
            _to_bars(self._candles.list_recent(asset.id, Timeframe.H4, limit=_H4_HISTORY)),
            rules.H4,
            now,
        )
        d1 = rules.closed_bars(
            _to_bars(self._candles.list_recent(asset.id, Timeframe.D1, limit=_D1_HISTORY)),
            rules.D1,
            now,
        )

        for trade in self._trades.list_open(asset.id):
            if self._settle(trade, spec, h4):
                result.closed += 1

        for j, bar in enumerate(h4):
            signal_time = bar.time + rules.H4
            if signal_time <= now - DECISION_WINDOW:
                continue
            d1_then = [b for b in d1 if b.time + rules.D1 <= signal_time]
            for setup in rules.setups_at(h4, d1_then, j):
                if self._trades.exists(asset.id, setup.direction, setup.pivot_time):
                    continue
                trade = self._record(spec, asset, setup, d1_then)
                result.recorded += 1
                if trade.status == "open":
                    result.taken += 1
                    logger.info(
                        "paper_swing.trade_opened",
                        symbol=spec.symbol,
                        direction=setup.direction,
                        entry=setup.entry,
                        stop=setup.stop,
                        target=setup.target,
                        risk_reward=round(setup.risk_reward, 2),
                    )
                    if self._settle(trade, spec, h4):
                        result.closed += 1
        return result

    def _record(
        self, spec: PairSpec, asset: Asset, setup: Setup, d1: Sequence[Bar]
    ) -> PaperSwingTrade:
        reason: str | None
        if setup.decision != "taken":
            status, reason = "rejected", setup.decision
        elif self._trades.has_trade_open_at(asset.id, setup.signal_time):
            status, reason = "skipped", "trade_open"
        else:
            status, reason = "open", None
        adr = rules.average_daily_range(d1, spec.pip)
        trade = PaperSwingTrade(
            id=uuid.uuid4(),
            asset_id=asset.id,
            symbol=spec.symbol,
            strategy_version=rules.STRATEGY_VERSION,
            setup=rules.SETUP_NAME,
            direction=setup.direction,
            d1_trend=setup.d1_trend,
            status=status,
            reject_reason=reason,
            signal_time=setup.signal_time,
            pivot_time=setup.pivot_time,
            origin_time=setup.origin_time,
            pullback_level=_d(setup.pullback_level, "0.00000001"),
            entry_price=_d(setup.entry, "0.00000001"),
            stop_loss=_d(setup.stop, "0.00000001"),
            take_profit=_d(setup.target, "0.00000001"),
            risk_pips=_d(setup.risk / spec.pip),
            reward_pips=_d(setup.reward / spec.pip),
            risk_reward=_d(setup.risk_reward),
            atr_h4_pips=_d(setup.atr / spec.pip),
            adr_pips=_d(adr) if adr is not None else None,
            spread_pips=_d(spec.spread_pips),
        )
        return self._trades.add(trade)

    def _settle(self, trade: PaperSwingTrade, spec: PairSpec, h4: Sequence[Bar]) -> bool:
        exit_ = rules.find_exit(
            h4,
            rules.H4,
            direction=trade.direction,  # type: ignore[arg-type]
            entry_time=_utc(trade.signal_time),
            stop=float(trade.stop_loss),
            target=float(trade.take_profit),
        )
        if exit_ is None:
            return False
        entry = float(trade.entry_price)
        move = (exit_.price - entry) if trade.direction == "buy" else (entry - exit_.price)
        hours = (exit_.time - _utc(trade.signal_time)).total_seconds() / 3600
        swap_rate = spec.swap_long_pips if trade.direction == "buy" else spec.swap_short_pips
        swap = swap_rate * hours / 24
        pips = move / spec.pip + swap - spec.spread_pips
        risk = float(trade.risk_pips)

        trade.status = exit_.outcome
        trade.closed_at = exit_.time
        trade.exit_price = _d(exit_.price, "0.00000001")
        trade.swap_pips = _d(swap)
        trade.result_pips = _d(pips)
        trade.result_r = _d(pips / risk) if risk > 0 else _d(0)
        trade.holding_hours = _d(hours, "0.01")
        self._trades.session.flush()
        logger.info(
            "paper_swing.trade_closed",
            symbol=trade.symbol,
            outcome=exit_.outcome,
            result_r=float(trade.result_r),
        )
        return True

    # --- reading ----------------------------------------------------------

    def list_trades(
        self, *, symbol: str | None, status: str | None, offset: int, limit: int
    ) -> tuple[Sequence[PaperSwingTrade], int]:
        return self._trades.list_page(symbol=symbol, status=status, offset=offset, limit=limit)

    def statistics(self, now: datetime) -> PaperStatistics:
        rows = self._trades.list_all()
        taken = [t for t in rows if t.is_taken]
        started = min((_utc(t.created_at) for t in rows), default=None)
        weeks = (now - started).total_seconds() / (7 * 86400) if started else 0.0
        rejected: dict[str, int] = {}
        for t in rows:
            if t.status == "rejected" and t.reject_reason:
                rejected[t.reject_reason] = rejected.get(t.reject_reason, 0) + 1
        return PaperStatistics(
            started_at=started,
            weeks_running=round(weeks, 1),
            trades_per_week=round(len(taken) / weeks, 2) if weeks >= 1 else None,
            overall=summarize(taken),
            by_pair={
                s.symbol: summarize([t for t in taken if t.symbol == s.symbol]) for s in PAIRS
            },
            by_direction={
                d: summarize([t for t in taken if t.direction == d]) for d in ("buy", "sell")
            },
            rejected=rejected,
            skipped_trade_open=sum(1 for t in rows if t.status == "skipped"),
        )
