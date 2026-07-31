class MarketDataProviderError(Exception):
    """Base class for provider-level failures. Internal to the market-data
    pipeline - not an `AppException` subclass, since Phase 3A exposes no API
    routes for this domain yet."""


class TransientProviderError(MarketDataProviderError):
    """A provider failure worth retrying (timeout, 5xx, rate limit)."""


class PermanentProviderError(MarketDataProviderError):
    """A provider failure not worth retrying (bad API key, invalid symbol)."""


class UnsupportedTimeframeError(PermanentProviderError):
    """The provider has no mapping for the requested canonical timeframe."""


class AllProvidersFailedError(MarketDataProviderError):
    """Every configured provider failed for a given collection request."""
