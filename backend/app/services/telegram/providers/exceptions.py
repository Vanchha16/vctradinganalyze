class TelegramProviderError(Exception):
    """Base class for Telegram-provider-level failures (docs/57 §4).
    Mirrors `app.services.news.providers.exceptions.NewsProviderError`'s
    hierarchy shape."""


class TransientTelegramProviderError(TelegramProviderError):
    """A provider failure worth retrying (timeout, 5xx, rate limit)."""


class PermanentTelegramProviderError(TelegramProviderError):
    """A provider failure not worth retrying (bad token, chat not found,
    bot blocked by the user)."""


class TelegramProviderConfigurationError(TelegramProviderError):
    """The provider is misconfigured (unknown provider name, missing
    `TELEGRAM_BOT_TOKEN`) - a setup problem, not a runtime failure."""
