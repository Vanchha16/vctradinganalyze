from datetime import UTC, datetime


def as_aware_utc(value: datetime) -> datetime:
    """Normalize a datetime read from the DB to UTC-aware.

    SQLite (used for local/test verification, see BACKLOG.md §9) has no
    native timezone-aware datetime type, so `DateTime(timezone=True)`
    columns come back naive when read through it even though Postgres
    preserves the offset. Treat a naive value as already UTC rather than
    letting a comparison against an aware `datetime.now(UTC)` raise
    `TypeError: can't subtract offset-naive and offset-aware datetimes`.

    Promoted to a shared helper in Phase 9B (ADR-133) after the same
    function had been independently copy-pasted into five modules
    (`authentication_service`, `news_sentiment.dedup_detector`,
    `analysis_confidence.freshness_analyzer`, `economic_calendar.
    risk_window`, `signal.status_resolver`) - do not add a sixth copy.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
