class AIProviderError(Exception):
    """Base class for AI-provider-level failures (docs/50 §8, ADR-081).
    Mirrors `app.services.news.providers.exceptions.NewsProviderError`'s
    hierarchy shape."""


class TransientAIProviderError(AIProviderError):
    """A provider failure worth retrying once (timeout, 5xx, rate limit)."""


class PermanentAIProviderError(AIProviderError):
    """A provider failure not worth retrying (bad API key, invalid request)."""


class AIProviderConfigurationError(AIProviderError):
    """The provider is misconfigured (missing API key) - a setup
    problem, not a runtime failure."""


class MalformedAIResponseError(AIProviderError):
    """The provider returned a response that could not be parsed into
    the expected `reasoning` schema, even after one retry."""
