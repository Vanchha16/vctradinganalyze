"""Operator diagnostic for News/Economic Calendar ingestion (Phase 9G,
ADR-139) - read-only, reports what is configured and what a single real
fetch attempt does, without ever printing a secret.

**This is a manual operator tool.** It is never scheduled, never run in
tests, and makes at most one call per configured provider - if a real
vendor (not `mock`) is configured, that call goes out to the real
vendor. It exists to answer the question this repo cannot answer on its
own: production has zero news articles while the calendar silently
serves mock data, and the most likely cause (NewsAPI's free Developer
plan commonly rejects requests from a deployed server while a local
machine succeeds) can only be confirmed by actually attempting a call
from the box in question.

Usage: python scripts/diagnose_ingestion.py
"""

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


def _diagnose_news() -> None:
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
        if provider.name != "mock":
            print("  WARNING: this will contact a REAL vendor now.")
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


def _diagnose_calendar() -> None:
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
        if provider.name != "mock":
            print("  WARNING: this will contact a REAL vendor now.")
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
    print(
        "This diagnostic makes exactly one fetch call per configured provider.\n"
        "If a real (non-mock) vendor is configured, that call WILL contact it.\n"
        "No secret value is ever printed - only whether a key is present."
    )
    _diagnose_news()
    _diagnose_calendar()
    print(
        "\nOperator: also check the worker log around the last scheduled run:\n"
        '  journalctl -u claudetrading-worker --since "2 hours ago" | grep -i "news\\|calendar"'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
