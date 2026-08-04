from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.database import get_db
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services.telegram.providers.base import TelegramProvider
from app.services.telegram.providers.bot_api import BotApiProvider
from app.services.telegram.providers.exceptions import TelegramProviderConfigurationError
from app.services.telegram.providers.mock import MockTelegramProvider
from app.services.telegram_service import TelegramService


def _build_bot_api_provider() -> TelegramProvider:
    if not settings.telegram_bot_token:
        raise TelegramProviderConfigurationError(
            "bot_api is configured in telegram_providers but TELEGRAM_BOT_TOKEN is not set"
        )
    return BotApiProvider(
        bot_token=settings.telegram_bot_token,
        base_url=settings.telegram_base_url,
        timeout=settings.telegram_timeout_seconds,
    )


_PROVIDER_FACTORIES: dict[str, Callable[[], TelegramProvider]] = {
    "mock": MockTelegramProvider,
    "bot_api": _build_bot_api_provider,
}


def get_telegram_provider() -> TelegramProvider:
    """Builds the configured Telegram provider (docs/57 §4). Mirrors
    `app.dependencies.ai_orchestrator.get_ai_provider` - only the first
    configured provider is used, no fallback chain."""
    if not settings.telegram_providers:
        raise TelegramProviderConfigurationError("No Telegram provider configured")

    name = settings.telegram_providers[0]
    factory = _PROVIDER_FACTORIES.get(name)
    if factory is None:
        raise TelegramProviderConfigurationError(f"Unknown Telegram provider configured: {name!r}")
    return factory()


def get_telegram_account_repository(
    db: Annotated[Session, Depends(get_db)],
) -> TelegramAccountRepository:
    return TelegramAccountRepository(db)


def get_telegram_service(
    account_repository: Annotated[
        TelegramAccountRepository, Depends(get_telegram_account_repository)
    ],
    provider: Annotated[TelegramProvider, Depends(get_telegram_provider)],
) -> TelegramService:
    return TelegramService(account_repository=account_repository, provider=provider)
