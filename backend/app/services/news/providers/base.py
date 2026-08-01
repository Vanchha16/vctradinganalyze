from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawNewsArticle:
    """A news article as returned by a provider, before dedup/classification/
    scoring (docs/46 §3). Values are left as the provider returned them -
    the ingestion pipeline's analyzer modules derive category, importance,
    sentiment, and affected assets from this raw shape."""

    title: str
    url: str
    published_at: datetime
    source_name: str
    summary: str | None = None
    content: str | None = None
    language: str = "en"


@dataclass(frozen=True, slots=True)
class NewsProviderCapabilities:
    """What a news provider can be asked to do (docs/46 §8).

    `supports_push` distinguishes providers that can push breaking news
    (webhook/streaming) from polling-only providers - relevant to docs/10
    §15's breaking-news SLA, which `MockNewsProvider` (polling-only,
    `supports_push=False`) cannot validate (docs/46 §12's explicit
    out-of-scope note).
    """

    supported_languages: frozenset[str]
    max_lookback_days: int | None = None
    supports_push: bool = False


class NewsProvider(Protocol):
    """Interface every news provider implements (docs/46 §8, ADR-050).

    `NewsIngestionPipeline` depends only on this interface, never on a
    concrete provider class - mirrors
    `app.services.market_data.providers.base.MarketDataProvider`.
    """

    name: str

    def fetch_latest(self, since: datetime) -> list[RawNewsArticle]:
        """Fetch articles published at or after `since` (UTC-aware).

        Raises `TransientNewsProviderError` for retryable failures,
        `PermanentNewsProviderError` (or a more specific subclass) for
        failures that should not be retried.
        """
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not fetch real data."""
        ...

    def capabilities(self) -> NewsProviderCapabilities:
        """Declare what this provider supports."""
        ...


__all__ = ["NewsProvider", "NewsProviderCapabilities", "RawNewsArticle"]
