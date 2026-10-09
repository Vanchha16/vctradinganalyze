"""smc-ict-crt-v2 design A - production service (ADR-185).

Deterministic, like v1's path: the rules in `rules.py` (built on the frozen v1
primitives) decide everything; nothing here calls the AI orchestrator, the
strategy scorer or the risk engine. v1's code, tables and P20 are untouched.

One run:

1. take the run lock (PostgreSQL advisory lock, released at commit);
2. read final M5 candles (audit D9, v1's own `closed_only`), admit only
   broker-open ones, build complete H1 candles;
3. bring every published setup in line with its signal (3 h expiry, fills,
   exits, execution rejections);
4. re-evaluate setups still waiting for their M5 shift, then evaluate new
   raids - only recent ones, so enabling v2 never back-fills history;
5. publish qualified setups in decision order, each only if (C13) no v1 or
   v2 signal holds the one slot, (C14) fewer than three were published this
   broker trading day, the decision is fresh (never back-dated or
   retro-published) and the setup has not expired.

Every evaluated setup is stored with its real reason. Decision time
(`decided_at`) and publication time (`published_at`) are separate fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog

from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.enums import Recommendation, SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.models.smc_v2_setup import SmcV2Setup, SmcV2State
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_v2_setup_repository import SmcV2SetupRepository, acquire_run_lock
from app.services.smc_crt.execution_safety import (
    EXECUTION_SAFETY_REASON,
    SMC_STRATEGY_NAME,
    geometry_violation,
    is_execution_rejection,
)
from app.services.smc_crt.rules import Direction, Reason
from app.services.smc_crt.service import closed_only
from app.services.smc_crt_v2 import rules
from app.services.smc_crt_v2.rules import Evaluation, Outcome
from app.utils.time import as_aware_utc

logger = structlog.get_logger(__name__)

STRATEGY_NAME = rules.STRATEGY_NAME
MODEL_NAME = "none"
PROMPT_VERSION = rules.STRATEGY_VERSION
#: C13: the one slot is shared with v1 - during and after the switch-over a
#: v1 signal still pending or open blocks a v2 publication.
SLOT_STRATEGIES = (STRATEGY_NAME, SMC_STRATEGY_NAME)

#: M5 history read per run: H1 swings and the previous day's range come
#: from it. Database reads only; no provider requests.
HISTORY = timedelta(days=60)
#: A qualified decision is published only this soon after its deciding
#: candle closed: the D9 collection lag plus one missed five-minute run. An
#: older decision is recorded NOT_PUBLISHED, never published late at a price
#: that has already moved on.
PUBLISH_WINDOW = timedelta(minutes=10)
#: New raids are evaluated only while they could still publish.
_NEW_RAID_HORIZON = rules.EXPIRY_ANCHOR_CANDLES * rules.ANCHOR + rules.GRACE + rules.ANCHOR

SETUP_EXPIRED = str(Reason.SETUP_EXPIRED)
REJECT_OPEN_TRADE = str(Reason.REJECT_OPEN_TRADE)
REJECT_DAILY_CAP = "REJECT_DAILY_CAP"
STALE_DECISION = "STALE_DECISION"


def _dec(x: float | None) -> Decimal | None:
    return None if x is None else Decimal(str(x))


class SmcCrtV2Service:
    def __init__(
        self,
        setups: SmcV2SetupRepository,
        candles: PriceCandleRepository,
        signals: SignalRepository,
        analyses: AIAnalysisRepository,
        audit: AuditLogRepository | None = None,
    ) -> None:
        self._setups = setups
        self._candles = candles
        self._signals = signals
        self._analyses = analyses
        self._audit = audit
        #: Filled by `run()` for the caller to deliver *after* it commits.
        self.created_signals: list[uuid.UUID] = []

    # --- state machine -----------------------------------------------------
    def _move(self, row: SmcV2Setup, state: SmcV2State, reason: str = "") -> None:
        previous = row.state
        row.reason = (reason or row.reason or "")[:96] or None
        if previous == state:
            return
        row.state = state
        row.transitions = [
            *(row.transitions or []),
            {"at": datetime.now(UTC).isoformat(timespec="seconds"),
             "from": str(previous), "to": str(state), "reason": reason[:96]},
        ]
        logger.info("smc_v2.transition", anchor=row.anchor_t.isoformat(),
                    **{"from": str(previous)}, to=str(state), reason=reason)

    # --- the run -----------------------------------------------------------
    def run(self, asset: Asset, now: datetime) -> list[SmcV2Setup]:
        now = as_aware_utc(now)
        self.created_signals = []
        acquire_run_lock(self._setups.session)
        rows = self._candles.list_range(asset.id, Timeframe.M5, start=now - HISTORY, end=now)
        m5 = rules.admit(closed_only(rows, Timeframe.M5, now))
        times = [c.t for c in m5]
        series = rules.H1Series.from_buckets(rules.aggregate_h1(m5))
        index = rules.KeyLevelIndex(series)
        position = {b.t: i for i, b in enumerate(series.bars)}

        touched = self._sync_published(asset, now)
        qualified: list[tuple[SmcV2Setup, Evaluation]] = []

        for row in self._setups.in_states(asset.id, STRATEGY_NAME, [SmcV2State.WAITING_FOR_MSS]):
            r = position.get(as_aware_utc(row.raid_t))
            if r is None or series.bars[r - 1].t != as_aware_utc(row.anchor_t):
                if row.expires_at is not None and now >= as_aware_utc(row.expires_at) + rules.GRACE:
                    self._move(row, SmcV2State.REJECTED,
                               f"{rules.DATA_INCOMPLETE}: raid candle no longer available")
                    touched.append(row)
                continue
            evaluation = rules.evaluate(series, index, r, m5, times, now)
            if evaluation is not None:
                self._apply(row, evaluation, qualified)
                touched.append(row)

        for r in range(1, len(series.bars)):
            raid = series.bars[r]
            if raid.t < now - _NEW_RAID_HORIZON or raid.t + rules.ANCHOR > now:
                continue
            anchor_t = series.bars[r - 1].t
            if self._setups.get_by_identity(asset.id, STRATEGY_NAME, rules.DESIGN,
                                            rules.ANCHOR_TIMEFRAME, anchor_t) is not None:
                continue  # already recorded - restart- and retry-safe
            evaluation = rules.evaluate(series, index, r, m5, times, now)
            if evaluation is None:
                continue  # not a CRT candidate at all
            row = self._new_row(asset, anchor_t, evaluation)
            self._apply(row, evaluation, qualified)
            touched.append(row)

        for row, evaluation in sorted(qualified, key=lambda q: (q[1].decided_at, q[0].raid_t)):
            self._publish_or_refuse(asset, row, evaluation, now)
        return touched

    # --- recording ------------------------------------------------------------
    def _new_row(self, asset: Asset, anchor_t: datetime, ev: Evaluation) -> SmcV2Setup:
        s = ev.setup
        assert s.raid_t is not None and s.raid_extreme is not None
        row = SmcV2Setup(
            asset_id=asset.id, strategy=STRATEGY_NAME, design=rules.DESIGN,
            anchor_timeframe=rules.ANCHOR_TIMEFRAME, anchor_t=anchor_t, raid_t=s.raid_t,
            state=str(SmcV2State.WAITING_FOR_MSS), direction=s.direction.value,
            crt_high=Decimal(str(s.crt_high)), crt_low=Decimal(str(s.crt_low)),
            raid_extreme=Decimal(str(s.raid_extreme)), closed_back_inside=s.closed_back_inside,
            session=s.session, location=s.location, equilibrium=_dec(s.equilibrium),
            modelled_spread=Decimal(str(rules.MODELLED_SPREAD)), news_status="NEWS_UNKNOWN",
            transitions=[],
        )
        self._setups.create(row)
        return row

    def _apply(
        self, row: SmcV2Setup, ev: Evaluation, qualified: list[tuple[SmcV2Setup, Evaluation]]
    ) -> None:
        s = ev.setup
        row.key_levels = "; ".join(f"{k.name}@{k.price}" for k in s.key_levels)[:400] or None
        row.expires_at = s.expires_at
        if s.mss_t is not None:
            row.mss_t, row.mss_level = s.mss_t, _dec(s.mss_level)
            row.decided_at = ev.decided_at
        if s.entry is not None and s.sl is not None:
            row.entry_basis = s.entry_basis
            row.entry, row.stop_loss, row.take_profit = _dec(s.entry), _dec(s.sl), _dec(s.tp1)
            row.risk_reward = s.rr
            row.stop_distance = _dec(s.sl_distance)
            row.modelled_cost_r = (
                round(rules.MODELLED_SPREAD / s.sl_distance, 4) if s.sl_distance else None
            )
        if ev.outcome is Outcome.WAITING:
            self._move(row, SmcV2State.WAITING_FOR_MSS, ev.reason)
        elif ev.outcome is Outcome.REJECTED:
            self._move(row, SmcV2State.REJECTED, ev.reason)
        else:
            self._move(row, SmcV2State.WAITING_FOR_MSS, "qualified - publication checks")
            qualified.append((row, ev))

    # --- publication --------------------------------------------------------
    def _publish_or_refuse(
        self, asset: Asset, row: SmcV2Setup, ev: Evaluation, now: datetime
    ) -> None:
        assert ev.decided_at is not None and row.expires_at is not None
        if now >= as_aware_utc(row.expires_at):
            self._move(row, SmcV2State.NOT_PUBLISHED, SETUP_EXPIRED)
            return
        if now > ev.decided_at + PUBLISH_WINDOW:
            self._move(row, SmcV2State.NOT_PUBLISHED,
                       f"{STALE_DECISION}: decided {ev.decided_at:%H:%M}, run {now:%H:%M} UTC")
            return
        holder = self._setups.open_signal(asset.id, SLOT_STRATEGIES)
        if holder is not None:
            row.slot_signal_id = holder.id
            self._move(row, SmcV2State.NOT_PUBLISHED,
                       f"{REJECT_OPEN_TRADE}: slot held by {holder.strategy} {holder.id}")
            return
        day = rules.trading_day(now)
        published = self._setups.published_on(asset.id, STRATEGY_NAME, day)
        row.published_today = published
        if published >= rules.DAILY_CAP:
            self._move(row, SmcV2State.NOT_PUBLISHED,
                       f"{REJECT_DAILY_CAP}: {published} published on {day.isoformat()}")
            return

        signal = self._create_signal(asset, row, ev, now)
        row.signal_id = signal.id
        row.published_at = now
        row.trading_day = day
        row.published_today = published + 1
        if signal.status is SignalStatus.CANCELLED:  # defensive: geometry is checked earlier
            self._move(row, SmcV2State.EXECUTION_REJECTED, (signal.status_reason or "")[:96])
            return
        self._move(row, SmcV2State.SIGNAL_CREATED, f"signal {signal.id}")
        self._setups.session.flush()  # the next decision in this run must see it
        self.created_signals.append(signal.id)

    def _create_signal(
        self, asset: Asset, row: SmcV2Setup, ev: Evaluation, now: datetime
    ) -> Signal:
        s = ev.setup
        assert s.entry is not None and s.sl is not None and s.tp1 is not None
        assert s.mss_level is not None and s.raid_extreme is not None
        buy = s.direction is Direction.BUY
        signal_type = SignalType.BUY if buy else SignalType.SELL
        entry, stop, target = Decimal(str(s.entry)), Decimal(str(s.sl)), Decimal(str(s.tp1))
        violation = geometry_violation(signal_type, entry, stop, target)
        summary = (
            f"{PROMPT_VERSION} (experimental, rule-based - no score) {s.direction.value.upper()}: "
            f"H1 CRT {s.crt_low:.3f}-{s.crt_high:.3f}, raid {s.raid_extreme:.3f}, M5 MSS at "
            f"{s.mss_level:.3f}, entry from {s.entry_basis}, R:R {s.rr}."
        )
        analysis = AIAnalysis(
            asset_id=asset.id, timeframe=Timeframe.M5,
            recommendation=Recommendation.BUY if buy else Recommendation.SELL,
            confidence_score=0.0, confidence_level="deterministic",
            entry_price=entry, stop_loss=stop, take_profit=target,
            reasoning={"summary": summary, "technical": summary, "smc": summary,
                       "economic": f"Not used by {PROMPT_VERSION}.",
                       "news": f"news status: {row.news_status}", "risk": summary,
                       "conclusion": summary},
            supporting_evidence=[f"key levels: {row.key_levels}"],
            conflicting_evidence=[
                "Design A's pre-registered backtest did not pass its criteria "
                "(research/smc_ict_crt_v2_3signals/RESULTS.md); run by operator decision."],
            risks=[],
            invalidation_conditions=[f"stop {s.sl:.3f}",
                                     f"expiry {row.expires_at:%Y-%m-%d %H:%M} UTC"],
            model_name=MODEL_NAME, prompt_version=PROMPT_VERSION, ai_available=False,
            warnings=[f"NEWS: {row.news_status}",
                      f"MODELLED COST: spread {rules.MODELLED_SPREAD} is a rule input (C11), "
                      "not the broker's actual spread"],
        )
        self._analyses.create(analysis)
        signal = Signal(
            analysis_id=analysis.id, asset_id=asset.id, timeframe=Timeframe.M5,
            signal_type=signal_type, entry_price=entry, stop_loss=stop, take_profit=target,
            risk_reward=float(s.rr or 0.0), confidence=0.0, strategy=STRATEGY_NAME,
            status=SignalStatus.ACTIVE if violation is None else SignalStatus.CANCELLED,
            confirmed_at=s.mss_t, closed_at=None if violation is None else now,
            status_reason=(
                f"M5 MSS at {s.mss_level:.3f} ({PROMPT_VERSION})"
                if violation is None else f"{EXECUTION_SAFETY_REASON}: {violation}"
            )[:160],
        )
        self._signals.create(signal)
        logger.info(
            "smc_v2.signal_created" if violation is None else "smc_v2.execution_rejected",
            signal_id=str(signal.id), direction=s.direction.value, entry=str(entry),
            sl=str(stop), tp=str(target), rr=s.rr, decided_at=str(ev.decided_at),
            published_at=now.isoformat(), modelled_cost_r=row.modelled_cost_r,
            violation=violation,
        )
        if violation is not None and self._audit is not None:
            self._audit.create(AuditLog(
                user_id=None, action="smc_execution_rejected", resource="signal",
                resource_id=signal.id,
                context={"reason": EXECUTION_SAFETY_REASON, "detail": violation,
                         "strategy": STRATEGY_NAME, "setup_anchor": row.anchor_t.isoformat()},
            ))
        return signal

    # --- lifecycle -----------------------------------------------------------
    def _sync_published(self, asset: Asset, now: datetime) -> list[SmcV2Setup]:
        """Bring each published setup in line with its signal.

        The frozen expiry: an entry never filled ends 3 h after the raid
        candle closed - well before the generic signal TTL. A filled trade
        is never touched: it exits at its stop or target only."""
        out: list[SmcV2Setup] = []
        for row in self._setups.in_states(asset.id, STRATEGY_NAME, [SmcV2State.SIGNAL_CREATED]):
            signal = self._signals.get_by_id(row.signal_id) if row.signal_id else None
            expired = row.expires_at is not None and as_aware_utc(row.expires_at) <= now
            if signal is None:
                if expired:
                    self._move(row, SmcV2State.EXPIRED, SETUP_EXPIRED)
                    out.append(row)
                continue
            if signal.status is SignalStatus.ACTIVE:
                if not expired:
                    continue  # still a live pending order
                signal.status = SignalStatus.CANCELLED
                signal.closed_at = now
                signal.status_reason = f"{PROMPT_VERSION}: 3h setup expiry, never filled"
                self._move(row, SmcV2State.EXPIRED, SETUP_EXPIRED)
            elif signal.status is SignalStatus.TRIGGERED:
                continue  # the trade is still open
            elif signal.status is SignalStatus.CANCELLED:
                if is_execution_rejection(signal.status_reason):
                    self._move(row, SmcV2State.EXECUTION_REJECTED,
                               (signal.status_reason or "")[:96])
                else:
                    self._move(row, SmcV2State.CANCELLED, (signal.status_reason or "")[:96])
            elif signal.status is SignalStatus.EXPIRED:
                self._move(row, SmcV2State.EXPIRED, "signal expired")
            elif signal.status in (SignalStatus.SUCCESSFUL, SignalStatus.STOPPED_OUT,
                                   SignalStatus.CLOSED):
                where = ("live broker position" if self._setups.had_live_position(signal.id)
                         else "paper - no live broker position")
                self._move(row, SmcV2State.TRADED, f"{signal.status.value}, {where}")
            else:
                continue
            out.append(row)
        return out


__all__ = ["PUBLISH_WINDOW", "SLOT_STRATEGIES", "STRATEGY_NAME", "SmcCrtV2Service"]
