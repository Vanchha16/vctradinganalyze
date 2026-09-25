"""smc-ict-crt-v1 production service (ADR-183).

A deterministic path of its own: the frozen rules in `rules.py` decide
everything, and nothing here calls the AI orchestrator, the strategy
scorer, the risk engine or `candidate_setup_builder`. BBMA's code is
neither imported nor affected.

What the frozen specification requires, and where it lives here:

- **closed candles only** - `closed_h4()` / `closed_m5()` drop any candle
  whose period has not finished at `now`. SMC-specific; no shared component
  is changed, so BBMA keeps reading exactly what it read before.
- **H4 anchor + raid, M5 MSS, FVG/OB entry, key level, RR >= 2** - the
  frozen `rules` functions, unmodified.
- **12 h expiry from the raid candle's close** - `Setup.expires_at`; the
  service cancels its own unfilled signal at that moment, well before the
  generic 24 h TTL could apply.
- **exits are stop or the opposite CRT boundary only** - the signal carries
  those two levels and nothing else; no time-based exit is added here.
- **news** - `NEWS_UNKNOWN` unless news data is actually available.

One open trade at a time (P20), and one signal per anchor candle: the
`smc_setups` row is the memory that makes a restart resume rather than
re-decide.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog

from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.enums import Recommendation, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup, SmcSetupState
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services.smc_crt import rules
from app.services.smc_crt.execution_safety import (
    EXECUTION_REJECTED_REASON,
    EXECUTION_SAFETY_REASON,
    SMC_STRATEGY_NAME,
    geometry_violation,
    is_execution_rejection,
)
from app.services.smc_crt.rules import (
    ATR_PERIOD,
    EXPIRY_HOURS,
    KEY_LEVEL_ATR_FRACTION,
    MIN_RR,
    SL_BUFFER_ATR_FRACTION,
    Candle,
    Direction,
    Reason,
)
from app.utils.time import as_aware_utc

logger = structlog.get_logger(__name__)

STRATEGY_NAME = SMC_STRATEGY_NAME
MODEL_NAME = "none"
PROMPT_VERSION = "smc-ict-crt-v1"

#: How much history each timeframe needs: enough for ATR(14), fractal
#: pivots and the key-level lookups, and no more - these are database
#: reads, so they cost no provider requests at all.
_H4_CANDLES = 200
_M5_CANDLES = 1500

_TF_SECONDS = {Timeframe.H4: 4 * 3600, Timeframe.M5: 300}

#: A setup in one of these states can still progress: the M5 shift, and then
#: the entry zone, only appear as candles close after the raid. Anything else
#: is resolved and is never re-decided.
_UNRESOLVED = (
    SmcSetupState.CRT_ANCHOR_CONFIRMED,
    SmcSetupState.RAID_CONFIRMED,
    SmcSetupState.WAITING_FOR_M5_MSS,
    SmcSetupState.MSS_CONFIRMED,
    SmcSetupState.ENTRY_ZONE_CONFIRMED,
)


def _to_candle(row: PriceCandle) -> Candle:
    return Candle(
        as_aware_utc(row.timestamp),
        float(row.open),
        float(row.high),
        float(row.low),
        float(row.close),
    )


def closed_only(rows: Sequence[PriceCandle], timeframe: Timeframe, now: datetime) -> list[Candle]:
    """Frozen rule §3: never decide on a candle that is still forming.

    A candle stamped `t` covers `[t, t + period)`, so it is closed only once
    `now >= t + period`. Applied here, inside the SMC path, rather than in
    the shared repository - BBMA's reads are deliberately left alone.
    """
    period = timedelta(seconds=_TF_SECONDS[timeframe])
    now = as_aware_utc(now)
    return [_to_candle(r) for r in rows if as_aware_utc(r.timestamp) + period <= now]


class SmcCrtService:
    def __init__(
        self,
        setups: SmcSetupRepository,
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
        #: Filled by `run()` for the caller to act on *after* it commits:
        #: signals to deliver (audit D1) and execution rejections to report.
        self.created_signals: list[uuid.UUID] = []
        self.execution_rejections: list[uuid.UUID] = []

    # --- state machine -----------------------------------------------------
    def _move(self, setup: SmcSetup, state: SmcSetupState, reason: str = "") -> None:
        """Every real transition is recorded on the row and in the log.

        A pending setup is re-evaluated on every tick until it resolves, so
        re-reaching the state it is already in is normal and is not logged
        again - only actual changes are."""
        previous = setup.state
        if previous is state:
            setup.reason = reason or setup.reason
            return
        setup.state = state
        setup.reason = reason or setup.reason
        setup.transitions = [
            *(setup.transitions or []),
            {
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                "from": str(previous), "to": str(state), "reason": reason,
            },
        ]
        logger.info(
            "smc.transition", anchor=setup.anchor_t.isoformat(), **{"from": str(previous)},
            to=str(state), reason=reason,
        )

    # --- the run -----------------------------------------------------------
    def run(self, asset: Asset, now: datetime) -> list[SmcSetup]:
        """One pass: expire what is due, then evaluate closed H4 candles.

        Returns the setups touched, newest last. Safe to call as often as
        wanted - it reads the database only, and a setup already recorded in
        a terminal state is never re-evaluated.
        """
        now = as_aware_utc(now)
        touched: list[SmcSetup] = []
        self.created_signals = []
        self.execution_rejections = []

        h4 = closed_only(
            self._candles.list_recent(asset.id, Timeframe.H4, limit=_H4_CANDLES), Timeframe.H4, now
        )
        m5 = closed_only(
            self._candles.list_recent(asset.id, Timeframe.M5, limit=_M5_CANDLES), Timeframe.M5, now
        )
        if len(h4) < ATR_PERIOD + 2:
            logger.warning("smc.not_enough_h4", have=len(h4))
            return touched

        touched.extend(self._expire_due(asset, now))

        for index in range(1, len(h4)):
            existing = self._setups.get_by_anchor(asset.id, h4[index - 1].t)
            if existing is not None and existing.state not in _UNRESOLVED:
                continue  # resolved already - restart-safe, never re-decided
            # An unresolved setup is re-evaluated on each tick: the M5 shift,
            # and then the entry zone, appear candle by candle after the raid.
            setup = self._evaluate(asset, h4, index, m5, now, existing)
            if setup is not None:
                touched.append(setup)
        return touched

    def _evaluate(
        self, asset: Asset, h4: list[Candle], index: int, m5: list[Candle], now: datetime,
        existing: SmcSetup | None = None,
    ) -> SmcSetup | None:
        candidate = rules.crt_candidate(h4, index)
        if candidate is None:
            return None  # no sweep of the anchor's range: not a CRT candidate

        anchor = h4[index - 1]
        # The frozen dataclass types these as optional; `crt_candidate` has
        # just set them, so narrow once here rather than re-checking below.
        raid_t = candidate.raid_t
        raid_extreme = candidate.raid_extreme
        equilibrium = candidate.equilibrium
        assert raid_t is not None and raid_extreme is not None and equilibrium is not None
        row = existing
        if row is None:
            row = SmcSetup(
                asset_id=asset.id, anchor_t=anchor.t, state=SmcSetupState.CRT_ANCHOR_CONFIRMED,
                direction=candidate.direction.value,
                crt_high=Decimal(str(candidate.crt_high)), crt_low=Decimal(str(candidate.crt_low)),
                raid_t=raid_t, raid_extreme=Decimal(str(raid_extreme)),
                closed_back_inside=candidate.closed_back_inside, session=candidate.session,
                location=candidate.location, equilibrium=Decimal(str(equilibrium)),
                news_status="NEWS_UNKNOWN", transitions=[],
            )
            self._setups.create(row)
        self._move(row, SmcSetupState.RAID_CONFIRMED, "raid swept the anchor's range")

        if not candidate.closed_back_inside:
            self._move(row, SmcSetupState.CANCELLED, Reason.NO_CLOSE_BACK_INSIDE)
            return row

        tolerance = rules.atr(h4, index, ATR_PERIOD)
        if tolerance is None:
            self._move(row, SmcSetupState.CANCELLED, "not enough H4 history for ATR")
            return row
        levels = rules.key_levels_for(
            h4, index - 1, raid_extreme, tolerance * KEY_LEVEL_ATR_FRACTION
        )
        row.key_levels = "; ".join(f"{k.name}@{k.price}" for k in levels)[:400] or None
        if not levels:
            self._move(row, SmcSetupState.CANCELLED, Reason.KEY_LEVEL_UNCERTAIN)
            return row

        raid_close = raid_t + timedelta(hours=4)
        expires_at = raid_close + timedelta(hours=EXPIRY_HOURS)
        candidate.expires_at = expires_at
        row.expires_at = expires_at
        self._move(row, SmcSetupState.WAITING_FOR_M5_MSS, "waiting for the M5 shift")

        window = [c for c in m5 if raid_close <= c.t <= expires_at]
        if not window:
            if now >= expires_at:
                self._move(row, SmcSetupState.EXPIRED, Reason.SETUP_EXPIRED)
            return row

        offset = m5.index(window[0])
        found = rules.find_mss(m5, offset, offset + len(window) - 1, candidate.direction)
        if found is None:
            if now >= expires_at:
                self._move(row, SmcSetupState.EXPIRED, Reason.NO_MSS)
            return row
        mss_index, mss_level = found
        candidate.mss_t, candidate.mss_level = m5[mss_index].t, mss_level
        row.mss_t, row.mss_level = candidate.mss_t, Decimal(str(mss_level))
        self._move(row, SmcSetupState.MSS_CONFIRMED, f"M5 close beyond {mss_level}")

        candidate.fvg = rules.find_fvg(m5, offset, mss_index, candidate.direction)
        candidate.ob = rules.find_ob(m5, mss_index, candidate.direction)
        level = rules.entry_level(candidate)
        if level is None:
            self._move(row, SmcSetupState.CANCELLED, Reason.NO_RETEST)
            return row
        candidate.entry, candidate.entry_basis = level

        buffer = (rules.atr(m5, mss_index, ATR_PERIOD) or 0.0) * SL_BUFFER_ATR_FRACTION
        pivots = [
            s for s in rules.swings_range(m5, max(0, offset - 4), mss_index)
            if s.high != (candidate.direction is Direction.BUY)
        ]
        rules.stops_and_targets(candidate, buffer, pivots[-1].price if pivots else None)
        row.entry_basis = candidate.entry_basis
        row.entry = Decimal(str(candidate.entry))
        row.stop_loss = Decimal(str(candidate.sl))
        row.take_profit = Decimal(str(candidate.tp1))
        row.risk_reward = candidate.rr
        self._move(row, SmcSetupState.ENTRY_ZONE_CONFIRMED, f"entry from {candidate.entry_basis}")

        if candidate.rr is None or candidate.rr < MIN_RR:
            self._move(row, SmcSetupState.CANCELLED, Reason.REJECT_RR)
            return row
        if self._open_signal_exists(asset):
            self._move(row, SmcSetupState.CANCELLED, Reason.REJECT_OPEN_TRADE)
            return row
        if now >= expires_at:
            self._move(row, SmcSetupState.EXPIRED, Reason.SETUP_EXPIRED)
            return row

        # --- the strategy has decided; everything below is execution plumbing
        signal, violation = self._publish(asset, candidate, row, expires_at, now)
        row.signal_id = signal.id
        self._move(row, SmcSetupState.SIGNAL_CREATED, f"signal {signal.id}")
        if violation is not None:
            self._move(row, SmcSetupState.EXECUTION_REJECTED,
                        f"{EXECUTION_SAFETY_REASON}: {violation}"[:64])
            self.execution_rejections.append(signal.id)
        else:
            self.created_signals.append(signal.id)
        return row

    # --- signals -----------------------------------------------------------
    def _open_signal_exists(self, asset: Asset) -> bool:
        """P20 - one open trade at a time, counting this strategy's own
        signals only: BBMA's rows are not this strategy's business."""
        return bool(self._setups.open_signal_count(asset.id, STRATEGY_NAME))

    def _publish(
        self, asset: Asset, candidate: rules.Setup, row: SmcSetup, expires_at: datetime,
        now: datetime,
    ) -> tuple[Signal, str | None]:
        """Create the analysis record and the signal; return the signal and
        the execution-safety violation, if any.

        ACTIVE, not DRAFT: the frozen rules confirm on the M5 shift, so the
        generic M1 confirmation task - which only ever looks at DRAFT rows -
        never sees this signal and cannot add a rule the specification does
        not have.

        Execution safety (audit D2): the strategy's entry, stop and target
        are kept exactly as computed. If they cannot form a broker order -
        a BUY with its stop at or above its entry, say - the signal is
        written CANCELLED instead of ACTIVE, in the same transaction. It is
        therefore never visible to the EA feed, never scanned by the M1
        monitor, and never counted as an open trade; the row is kept for
        the audit trail.
        """
        signal_type = SignalType.BUY if candidate.direction is Direction.BUY else SignalType.SELL
        entry = Decimal(str(candidate.entry))
        stop = Decimal(str(candidate.sl))
        target = Decimal(str(candidate.tp1))
        violation = geometry_violation(signal_type, entry, stop, target)
        summary = (
            f"smc-ict-crt-v1 {candidate.direction.value.upper()}: CRT {candidate.crt_low:.3f}-"
            f"{candidate.crt_high:.3f}, raid {candidate.raid_extreme:.3f}, M5 MSS at "
            f"{candidate.mss_level:.3f}, entry from {candidate.entry_basis}, R:R {candidate.rr}."
        )
        analysis = AIAnalysis(
            asset_id=asset.id, timeframe=Timeframe.M5,
            recommendation=Recommendation.BUY if candidate.direction is Direction.BUY
            else Recommendation.SELL,
            confidence_score=0.0, confidence_level="deterministic",
            entry_price=Decimal(str(candidate.entry)), stop_loss=Decimal(str(candidate.sl)),
            take_profit=Decimal(str(candidate.tp1)),
            reasoning={"summary": summary, "technical": summary, "smc": summary,
                       "economic": "Not used by smc-ict-crt-v1.",
                       "news": f"news status: {row.news_status}", "risk": summary,
                       "conclusion": summary},
            supporting_evidence=[f"key levels: {row.key_levels}"],
            conflicting_evidence=[], risks=[], invalidation_conditions=[
                f"stop {candidate.sl:.3f}", f"expiry {expires_at:%Y-%m-%d %H:%M} UTC"],
            model_name=MODEL_NAME, prompt_version=PROMPT_VERSION, ai_available=False,
            warnings=[f"NEWS: {row.news_status}"],
        )
        self._analyses.create(analysis)

        signal = Signal(
            analysis_id=analysis.id, asset_id=asset.id, timeframe=Timeframe.M5,
            signal_type=signal_type, entry_price=entry, stop_loss=stop, take_profit=target,
            risk_reward=float(candidate.rr or 0.0), confidence=0.0, strategy=STRATEGY_NAME,
            status=SignalStatus.ACTIVE if violation is None else SignalStatus.CANCELLED,
            confirmed_at=candidate.mss_t,
            closed_at=None if violation is None else now,
            status_reason=(
                f"M5 MSS at {candidate.mss_level:.3f} (smc-ict-crt-v1)"
                if violation is None else f"{EXECUTION_SAFETY_REASON}: {violation}"
            )[:160],
        )
        self._signals.create(signal)
        if violation is None:
            logger.info(
                "smc.signal_created", signal_id=str(signal.id),
                direction=candidate.direction.value, entry=str(entry), sl=str(stop),
                tp=str(target), rr=candidate.rr, session=candidate.session,
                news=row.news_status, expires_at=expires_at.isoformat(),
            )
        else:
            logger.warning(
                "smc.execution_rejected", signal_id=str(signal.id),
                reason=EXECUTION_SAFETY_REASON, violation=violation,
                direction=candidate.direction.value, entry=str(entry), sl=str(stop),
                tp=str(target),
            )
            self._audit_rejection(signal, row, violation)
        return signal, violation

    def _audit_rejection(self, signal: Signal, row: SmcSetup, why: str) -> None:
        """An audit row for every execution rejection (audit D3). No actor:
        the system refused it, nobody chose to."""
        if self._audit is None:
            return
        self._audit.create(AuditLog(
            user_id=None, action="smc_execution_rejected", resource="signal",
            resource_id=signal.id,
            context={
                "reason": EXECUTION_SAFETY_REASON if why else EXECUTION_REJECTED_REASON,
                "detail": why, "setup_anchor": row.anchor_t.isoformat(),
                "signal_type": signal.signal_type.value,
                "entry": str(signal.entry_price), "stop_loss": str(signal.stop_loss),
                "take_profit": str(signal.take_profit),
            },
        ))

    # --- expiry ------------------------------------------------------------
    def _expire_due(self, asset: Asset, now: datetime) -> list[SmcSetup]:
        """Bring each setup that has a signal in line with that signal.

        Frozen rule §18: a signal whose entry never filled dies 12 h after the
        raid candle closed - not at the generic 24 h TTL. A filled trade is
        never touched here: it exits at its stop or the opposite CRT boundary,
        and at nothing else.

        Audit D3: a signal refused at execution (impossible geometry, or a live
        broker/EA rejection) ends as EXECUTION_REJECTED - never TRADED, never a
        stop-out - and TRADED records whether a live broker position existed.
        """
        out: list[SmcSetup] = []
        for row in self._setups.pending_with_signal(asset.id):
            signal = self._signals.get_by_id(row.signal_id) if row.signal_id else None
            expired = row.expires_at is not None and as_aware_utc(row.expires_at) <= now
            if signal is None:
                if expired:
                    self._move(row, SmcSetupState.EXPIRED, Reason.SETUP_EXPIRED)
                    out.append(row)
                continue
            if signal.status is SignalStatus.ACTIVE:
                if not expired:
                    continue  # still a live pending order
                signal.status = SignalStatus.CANCELLED
                signal.closed_at = now
                signal.status_reason = "smc-ict-crt-v1: 12h setup expiry, never filled"
                self._move(row, SmcSetupState.EXPIRED, Reason.SETUP_EXPIRED)
            elif signal.status is SignalStatus.CANCELLED:
                if is_execution_rejection(signal.status_reason):
                    self._move(row, SmcSetupState.EXECUTION_REJECTED,
                               (signal.status_reason or "")[:64])
                else:  # replaced, or cancelled from the website
                    self._move(row, SmcSetupState.CANCELLED, (signal.status_reason or "")[:64])
            elif signal.status in (SignalStatus.TRIGGERED, SignalStatus.SUCCESSFUL,
                                   SignalStatus.STOPPED_OUT, SignalStatus.CLOSED):
                if signal.status is SignalStatus.TRIGGERED:
                    continue  # the trade is still open: resolve it when it closes
                where = ("live broker position" if self._setups.had_live_position(signal.id)
                         else "paper - no live broker position")
                self._move(row, SmcSetupState.TRADED, f"{signal.status.value}, {where}"[:64])
            else:
                continue
            out.append(row)
        return out


__all__ = ["STRATEGY_NAME", "SmcCrtService", "closed_only"]
