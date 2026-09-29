"""ADR-182 - swing strategy paper trading, on the H4 clock.

Collects H4 and D1 candles for the three paper pairs, then lets
`PaperSwingService` settle and decide. Touches no signal, no broker order
and nothing the EA reads.

**When a candle is due is read from the data, not from a fixed clock.**
Twelve Data's forex H4 bars open at 01:00, 05:00 ... UTC in summer and at
00:00, 04:00 ... in winter (both seen in its history), and its D1 bar is
labelled 00:00 UTC. The newest stored candle is the one still forming when
it was fetched, so it closes one bar length after it opened. The task runs
every hour and fetches a timeframe only in the first hour after that close
(or after one of the 4-hour / 1-day steps that follow it, when the provider
had no new bar, e.g. over a weekend). That keeps decisions within minutes of
each close in both seasons, at no more than six H4 and one D1 request per
pair per day.
"""

from datetime import UTC, datetime, timedelta

import structlog
from celery.schedules import crontab

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.market_data import get_market_data_providers
from app.models.enums import Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.paper_swing_trade_repository import PaperSwingTradeRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data_service import MarketDataService
from app.services.paper_swing_service import PaperSwingService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_LENGTH = {Timeframe.H4: timedelta(hours=4), Timeframe.D1: timedelta(days=1)}
#: Hourly runs, so each boundary is seen by exactly one run.
_DUE_WITHIN = timedelta(hours=1)
#: A normal fetch re-reads at least this much, so a bar published late is
#: still picked up.
_WINDOW = {Timeframe.H4: timedelta(days=2), Timeframe.D1: timedelta(days=7)}
#: Newest candle older than this (first run, a long outage): fetch history
#: instead - still one request (`outputsize=5000`). Longer than any weekend
#: gap, so a weekend never triggers it.
_STALE = {Timeframe.H4: timedelta(days=10), Timeframe.D1: timedelta(days=20)}
_BACKFILL = {Timeframe.H4: timedelta(days=120), Timeframe.D1: timedelta(days=450)}


def fetch_start(
    latest_open: datetime | None, timeframe: Timeframe, now: datetime
) -> datetime | None:
    """Where this run should fetch `timeframe` from, or None when no new
    candle can have closed since the last fetch."""
    if latest_open is None or latest_open < now - _STALE[timeframe]:
        return now - _BACKFILL[timeframe]
    length = _LENGTH[timeframe]
    close = latest_open + length
    if now < close or (now - close) % length >= _DUE_WITHIN:
        return None
    return min(latest_open, now - _WINDOW[timeframe])


def _latest_open(
    candles: PriceCandleRepository, asset_id: object, timeframe: Timeframe
) -> datetime | None:
    latest = candles.get_latest(asset_id, timeframe)  # type: ignore[arg-type]
    if latest is None:
        return None
    stamp = latest.timestamp
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


@celery_app.task(name="paper_swing.run")  # type: ignore[untyped-decorator]
def run_paper_swing_task() -> None:
    """Gated on the setting, like the tight M5 task: Beat always enqueues,
    and a disabled run returns having fetched and spent nothing."""
    if not settings.paper_swing_enabled:
        return

    session = SessionLocal()
    try:
        candles = PriceCandleRepository(session)
        service = PaperSwingService(
            AssetRepository(session), candles, PaperSwingTradeRepository(session)
        )
        market = MarketDataService(
            providers=get_market_data_providers(),
            candle_validator=CandleValidator(),
            price_candle_repository=candles,
        )
        pairs = service.ensure_assets()
        session.commit()

        now = datetime.now(UTC)
        for spec, asset in pairs:
            fetched: list[Timeframe] = []
            try:
                # D1 first: at a boundary both share, the H4 decision must
                # see the day that just closed.
                for timeframe in (Timeframe.D1, Timeframe.H4):
                    start = fetch_start(_latest_open(candles, asset.id, timeframe), timeframe, now)
                    if start is None:
                        continue
                    market.collect(asset, timeframe, start=start, end=now)
                    fetched.append(timeframe)
                session.commit()
            except Exception:
                # One pair's failed fetch (quota, provider outage) must not
                # stop the others. Its bars are decided on a later run - the
                # decision window spans 48 hours.
                session.rollback()
                logger.exception("paper_swing.collect_failed", symbol=spec.symbol)
                continue
            if Timeframe.H4 not in fetched:
                continue

            result = service.evaluate(spec, asset, now)
            session.commit()
            logger.info(
                "paper_swing.evaluated",
                symbol=spec.symbol,
                recorded=result.recorded,
                taken=result.taken,
                closed=result.closed,
            )
    finally:
        session.close()


def register_paper_swing_schedule() -> dict[str, dict[str, object]]:
    return {
        "paper-swing": {
            "task": "paper_swing.run",
            "schedule": crontab(minute="4"),
        },
    }
