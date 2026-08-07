"""Operator diagnostic for News/Economic Calendar ingestion (Phase 9G,
ADR-139) - read-only, reports what is configured and what a single real
fetch attempt does, without ever printing a secret.

**This is a manual operator tool.** It is never scheduled, never run in
tests. Without `--allow-real-calls`, it refuses to contact any
non-mock provider - it only reports what it can offline (configured
providers, whether each required API key is present, stored counts,
newest timestamp). With `--allow-real-calls`, it makes at most one call
per configured non-mock provider - three accidental real-vendor calls
have already happened in this project (9C Twelve Data, 7D-C NewsAPI, 9G
NewsAPI + Finnhub) from a warning-only version of this exact script; the
flag is a gate, not documentation.

It exists to answer the question this repo cannot answer on its own:
production has zero news articles while the calendar silently serves
mock data, and the most likely cause (NewsAPI's free Developer plan
commonly rejects requests from a deployed server while a local machine
succeeds) can only be confirmed by actually attempting a call from the
box in question.

Usage:
    python scripts/diagnose_ingestion.py                     # offline report only
    python scripts/diagnose_ingestion.py --allow-real-calls   # also calls real providers
"""

import argparse
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.economic_calendar import get_economic_calendar_providers
from app.dependencies.news import get_news_providers
from app.models.economic_event import EconomicEvent
from app.models.news_article import NewsArticle
from app.services.economic_calendar.providers.exceptions import EconomicCalendarProviderError
from app.services.news.providers.exceptions import NewsProviderError


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _diagnose_news(*, allow_real_calls: bool) -> None:
    _print_header("News Ingestion")
    print(f"configured providers: {settings.news_providers}")
    print(f"NEWS_API_KEY present: {bool(settings.news_api_key)}")

    try:
        providers = get_news_providers()
    except Exception as exc:  # noqa: BLE001 - report, don't crash the diagnostic
        print(f"FAILED to build provider chain: {exc}")
        return

    since = datetime.now(UTC) - timedelta(hours=settings.news_lookback_hours)
    for provider in providers:
        print(f"\n--- provider: {provider.name} ---")
        if provider.name != "mock" and not allow_real_calls:
            print(
                "  SKIPPED: this is a real (non-mock) provider. Re-run with "
                "--allow-real-calls to contact it. No call was made."
            )
            continue
        if provider.name != "mock":
            print("  WARNING: contacting a REAL vendor now.")
        try:
            articles = provider.fetch_latest(since)
        except NewsProviderError as exc:
            print(f"  RESULT: FAILED - {exc!r}")
            continue
        print(f"  RESULT: success, {len(articles)} article(s) fetched")

    session = SessionLocal()
    try:
        total = session.execute(select(func.count()).select_from(NewsArticle)).scalar_one()
        newest = session.execute(select(func.max(NewsArticle.published_at))).scalar_one()
        print(f"\narticles currently stored: {total}")
        print(f"newest published_at: {newest}")
    finally:
        session.close()


def _diagnose_calendar(*, allow_real_calls: bool) -> None:
    _print_header("Economic Calendar Ingestion")
    print(f"configured providers: {settings.economic_calendar_providers}")
    print(f"ECONOMIC_API_KEY present: {bool(settings.economic_api_key)}")

    try:
        providers = get_economic_calendar_providers()
    except Exception as exc:  # noqa: BLE001 - report, don't crash the diagnostic
        print(f"FAILED to build provider chain: {exc}")
        return

    now = datetime.now(UTC)
    start = now - timedelta(days=settings.economic_calendar_lookback_days)
    end = now + timedelta(days=settings.economic_calendar_lookahead_days)
    for provider in providers:
        print(f"\n--- provider: {provider.name} ---")
        if provider.name != "mock" and not allow_real_calls:
            print(
                "  SKIPPED: this is a real (non-mock) provider. Re-run with "
                "--allow-real-calls to contact it. No call was made."
            )
            continue
        if provider.name != "mock":
            print("  WARNING: contacting a REAL vendor now.")
        try:
            events = provider.fetch_events(start, end)
        except EconomicCalendarProviderError as exc:
            print(f"  RESULT: FAILED - {exc!r}")
            continue
        print(f"  RESULT: success, {len(events)} event(s) fetched")

    session = SessionLocal()
    try:
        total = session.execute(select(func.count()).select_from(EconomicEvent)).scalar_one()
        newest = session.execute(select(func.max(EconomicEvent.release_time))).scalar_one()
        print(f"\nevents currently stored: {total}")
        print(f"newest release_time: {newest}")
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-real-calls",
        action="store_true",
        help="Required to contact any configured non-mock provider. Without it, "
        "real providers are skipped entirely - no call is made.",
    )
    args = parser.parse_args()

    if args.allow_real_calls:
        print(
            "--allow-real-calls set: this run WILL contact any configured "
            "non-mock provider.\n"
            "No secret value is ever printed - only whether a key is present."
        )
    else:
        print(
            "Offline mode (default): real providers will be reported but NOT "
            "contacted.\n"
            "Pass --allow-real-calls to actually call a configured non-mock provider.\n"
            "No secret value is ever printed - only whether a key is present."
        )

    _diagnose_news(allow_real_calls=args.allow_real_calls)
    _diagnose_calendar(allow_real_calls=args.allow_real_calls)
    print(
        "\nOperator: also check the worker log around the last scheduled run:\n"
        '  journalctl -u claudetrading-worker --since "2 hours ago" | grep -i "news\\|calendar"'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
