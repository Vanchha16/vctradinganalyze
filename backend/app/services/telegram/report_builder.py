"""Builds the text for the Telegram bot's "Summary Report" button (§13):
today's signal activity, a trailing-7-day recap, and a quick market
snapshot of active assets. Broadcast identically to every linked
account on request, same as every other Telegram message this project
sends - `Signal` has no `user_id` column (ADR-130), so there is no
per-user variant to build.

Same presentation discipline as `message_sections.py`: every value here
is read verbatim from already-persisted rows, nothing is scored or
decided in this module.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.enums import SignalStatus, Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services.telegram.message_sections import escape_markdown_v2

_SEPARATOR = "━━━━━━━━━━━━━━━━━━"
_REPORT_WINDOW_DAYS = 7
#: Up to the last hour of M1 data (docs/38's collection cadence) - a
#: "recent change" figure, deliberately not labelled "24h"/"daily" since
#: that would overstate what two M1 candles up to an hour apart actually
#: measure.
_MARKET_OVERVIEW_LOOKBACK_CANDLES = 60
_MARKET_OVERVIEW_MAX_ASSETS = 10


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
    week_start = now - timedelta(days=_REPORT_WINDOW_DAYS)

    sections = [
        f"{_SEPARATOR}\n📊 SUMMARY REPORT\n{_SEPARATOR}",
        _period_section(
            "Today",
            signal_repository.count_by_status_since(today_start),
            signal_repository.sum_profit_loss_since(today_start),
        ),
        _period_section(
            "Last 7 Days",
            signal_repository.count_by_status_since(week_start),
            signal_repository.sum_profit_loss_since(week_start),
        ),
        _market_overview_section(asset_repository, candle_repository),
        escape_markdown_v2(f"Generated {now.strftime('%Y-%m-%d %H:%M UTC')}"),
    ]
    return "\n\n".join(sections)


__all__ = ["build_summary_report_text"]
