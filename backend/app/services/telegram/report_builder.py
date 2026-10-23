"""Builds the text for the Telegram bot's "Summary Report" button (§13):
today's signal activity, trailing 7-day and 30-day recaps, and a quick
market snapshot of active assets.

Every period counts only engines switched on now: the signals of an engine
with its own switch (SMC v1, SMC v2) are left out while it is off, and the
report says how many it left out, so a retired engine's history neither
blends into nor silently vanishes from the current picture. Broadcast identically to every linked
account on request, same as every other Telegram message this project
sends - `Signal` has no `user_id` column (ADR-130), so there is no
per-user variant to build.

Same presentation discipline as `message_sections.py`: every value here
is read verbatim from already-persisted rows, nothing is scored or
decided in this module.
"""

from collections import Counter
from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.config import settings
from app.models.enums import SignalStatus, Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services.signal.status_resolver import effective_status
from app.services.smc_crt.execution_safety import SMC_STRATEGY_NAME
from app.services.smc_crt_v2.rules import STRATEGY_NAME as SMC_V2_STRATEGY_NAME
from app.services.telegram.message_sections import escape_markdown_v2

_SEPARATOR = "━━━━━━━━━━━━━━━━━━"
#: Trailing windows after "Today", in display order.
_REPORT_WINDOWS_DAYS = (7, 30)
#: Engines with their own on/off setting: (strategy recorded on the signal,
#: name shown, setting). The AI engine's strategies have no such switch.
_SWITCHED_ENGINES = (
    (SMC_STRATEGY_NAME, "SMC v1", "smc_enabled"),
    (SMC_V2_STRATEGY_NAME, "SMC v2", "smc_v2_enabled"),
)


def _switched_off_engines() -> dict[str, str]:
    """{strategy: name} of the engines switched off right now."""
    return {strategy: name for strategy, name, flag in _SWITCHED_ENGINES
            if not getattr(settings, flag)}
#: Up to the last hour of M1 data (docs/38's collection cadence) - a
#: "recent change" figure, deliberately not labelled "24h"/"daily" since
#: that would overstate what two M1 candles up to an hour apart actually
#: measure.
_MARKET_OVERVIEW_LOOKBACK_CANDLES = 60
_MARKET_OVERVIEW_MAX_ASSETS = 10


def _status_counts(
    signal_repository: SignalRepository,
    since: datetime,
    now: datetime,
    exclude: Collection[str] = (),
) -> dict[SignalStatus, int]:
    """Counted by the status each signal shows now, not the stored one: an
    unfilled signal past its TTL is expired, not open (ADR-088)."""
    return dict(
        Counter(
            effective_status(status, created_at, now, triggered_at=triggered_at)
            for status, created_at, triggered_at in signal_repository.list_status_times_since(
                since, exclude_strategies=exclude
            )
        )
    )


def _not_counted_line(
    signal_repository: SignalRepository, since: datetime, off: dict[str, str], days: int
) -> str | None:
    """What the report left out, or None when it left nothing out."""
    counts = signal_repository.count_by_strategy_since(since, off)
    if not counts:
        return None
    parts = ", ".join(f"{off[strategy]} ({count})" for strategy, count in sorted(counts.items()))
    return escape_markdown_v2(f"Not counted - engines switched off, last {days} days: {parts}")


def _status_counts_line(status_counts: dict[SignalStatus, int]) -> str:
    total = sum(status_counts.values())
    wins = status_counts.get(SignalStatus.SUCCESSFUL, 0)
    losses = status_counts.get(SignalStatus.STOPPED_OUT, 0)
    open_count = status_counts.get(SignalStatus.ACTIVE, 0) + status_counts.get(
        SignalStatus.TRIGGERED, 0
    )
    return escape_markdown_v2(
        f"Signals: {total}  (Won {wins} / Lost {losses} / Open {open_count})"
    )


def _period_section(
    label: str, status_counts: dict[SignalStatus, int], profit_loss: Decimal
) -> str:
    lines = [
        escape_markdown_v2(label),
        _status_counts_line(status_counts),
        escape_markdown_v2(f"P&L: {profit_loss:+.2f}"),
    ]
    return "\n".join(lines)


def _market_overview_section(
    asset_repository: AssetRepository, candle_repository: PriceCandleRepository
) -> str:
    assets = asset_repository.list_active(limit=_MARKET_OVERVIEW_MAX_ASSETS)
    lines = [escape_markdown_v2("Market Overview")]
    if not assets:
        lines.append(escape_markdown_v2("No active assets configured."))
        return "\n".join(lines)

    for asset in assets:
        candles = candle_repository.list_recent(
            asset.id, Timeframe.M1, limit=_MARKET_OVERVIEW_LOOKBACK_CANDLES
        )
        if not candles:
            lines.append(escape_markdown_v2(f"{asset.symbol}: no data yet"))
            continue

        latest_close = candles[-1].close
        change_text = "n/a"
        if len(candles) > 1 and candles[0].close:
            change_pct = (latest_close - candles[0].close) / candles[0].close * Decimal(100)
            arrow = "▲" if change_pct >= 0 else "▼"
            change_text = f"{arrow} {change_pct:+.2f}%"
        lines.append(escape_markdown_v2(f"{asset.symbol}: {latest_close}  ({change_text})"))
    return "\n".join(lines)


def build_summary_report_text(
    signal_repository: SignalRepository,
    asset_repository: AssetRepository,
    candle_repository: PriceCandleRepository,
    *,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    periods = [("Today", today_start)] + [
        (f"Last {days} Days", now - timedelta(days=days)) for days in _REPORT_WINDOWS_DAYS
    ]
    off = _switched_off_engines()

    sections = [
        f"{_SEPARATOR}\n📊 SUMMARY REPORT\n{_SEPARATOR}",
        *(
            _period_section(
                label,
                _status_counts(signal_repository, start, now, off),
                signal_repository.sum_profit_loss_since(start, exclude_strategies=off),
            )
            for label, start in periods
        ),
    ]
    longest = max(_REPORT_WINDOWS_DAYS)
    not_counted = _not_counted_line(
        signal_repository, now - timedelta(days=longest), off, longest
    )
    if not_counted is not None:
        sections.append(not_counted)
    sections += [
        _market_overview_section(asset_repository, candle_repository),
        escape_markdown_v2(f"Generated {now.strftime('%Y-%m-%d %H:%M UTC')}"),
    ]
    return "\n\n".join(sections)


__all__ = ["build_summary_report_text"]
