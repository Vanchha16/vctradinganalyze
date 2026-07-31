class MarketDataProviderError(Exception):
    """Base class for provider-level failures. Internal to the market-data
    pipeline - not an `AppException` subclass, since Phase 3A/3.5 expose no
    API routes for this domain yet.

    This is the extension point for future provider-specific exceptions
    (docs/40) - e.g. a Twelve Data implementation might raise
    `TwelveDataAuthenticationError(PermanentProviderError)` or
    `TwelveDataQuotaExceededError(TransientProviderError)` for errors that
    need provider-specific context, while still being caught generically
    by `MarketDataService` via the base categories below.
    """


class TransientProviderError(MarketDataProviderError):
    """A provider failure worth retrying (timeout, 5xx, rate limit)."""


class PermanentProviderError(MarketDataProviderError):
    """A provider failure not worth retrying (bad API key, invalid symbol)."""


class UnsupportedTimeframeError(PermanentProviderError):
    """The provider has no mapping for the requested canonical timeframe.

    Reactive fallback only - `MarketDataService` now checks
    `provider.capabilities()` proactively (docs/40) before calling, so this
    should mainly guard against a capability declaration being wrong/stale.
    """


class ProviderConfigurationError(MarketDataProviderError):
    """The provider is misconfigured (unknown provider name, missing
    required settings/API key) - a setup problem, not a runtime failure."""


class AllProvidersFailedError(MarketDataProviderError):
    """Every configured provider failed for a given collection request."""
