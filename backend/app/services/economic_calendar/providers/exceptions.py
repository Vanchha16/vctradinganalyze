class EconomicCalendarProviderError(Exception):
    """Base class for economic-calendar-provider-level failures (docs/47
    §8, ADR-056). Mirrors
    `app.services.news.providers.exceptions.NewsProviderError`'s
    hierarchy shape - the extension point for a future real vendor's own
    provider-specific exceptions (e.g. `TradingEconomicsAuthenticationError`)."""


class TransientEconomicCalendarProviderError(EconomicCalendarProviderError):
    """A provider failure worth retrying (timeout, 5xx, rate limit)."""


class PermanentEconomicCalendarProviderError(EconomicCalendarProviderError):
    """A provider failure not worth retrying (bad API key, invalid request)."""


class EconomicCalendarProviderConfigurationError(EconomicCalendarProviderError):
    """The provider is misconfigured (unknown provider name, missing
    required settings/API key) - a setup problem, not a runtime failure."""


class AllEconomicCalendarProvidersFailedError(EconomicCalendarProviderError):
    """Every configured economic calendar provider failed for a given
    ingestion run."""
