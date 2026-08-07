"""Cleanup (2026-08-07): explicit assertions on the news ingestion
cadence/lookback defaults, so a future edit to either value is a
deliberate, reviewed change rather than an accidental regression back
to values that guarantee zero articles on NewsAPI's free Developer
plan (see settings.py's inline comments and BACKLOG.md §16)."""

from app.config import Settings


def test_news_lookback_hours_default_covers_newsapi_free_tier_delay() -> None:
    assert Settings.model_fields["news_lookback_hours"].default == 72


def test_news_ingestion_interval_seconds_default_fits_newsapi_free_tier_quota() -> None:
    assert Settings.model_fields["news_ingestion_interval_seconds"].default == 1800
