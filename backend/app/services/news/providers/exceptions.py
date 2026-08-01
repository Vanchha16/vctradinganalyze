class NewsProviderError(Exception):
    """Base class for news-provider-level failures (docs/46 §8, ADR-050).
    Mirrors `app.services.market_data.exceptions.MarketDataProviderError`'s
    hierarchy shape - the extension point for a future real vendor's own
    provider-specific exceptions (e.g. `NewsApiAuthenticationError`)."""


class TransientNewsProviderError(NewsProviderError):
    """A provider failure worth retrying (timeout, 5xx, rate limit)."""


class PermanentNewsProviderError(NewsProviderError):
    """A provider failure not worth retrying (bad API key, invalid request)."""


class NewsProviderConfigurationError(NewsProviderError):
    """The provider is misconfigured (unknown provider name, missing
    required settings/API key) - a setup problem, not a runtime failure."""


class AllNewsProvidersFailedError(NewsProviderError):
    """Every configured news provider failed for a given ingestion run."""
