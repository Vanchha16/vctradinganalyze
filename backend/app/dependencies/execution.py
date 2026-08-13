from collections.abc import Callable
from decimal import Decimal
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.database import get_db
from app.repositories.broker_order_repository import BrokerOrderRepository
from app.services.execution.exceptions import ExecutionProviderConfigurationError
from app.services.execution.order_execution_service import OrderExecutionService
from app.services.execution.providers.base import OrderExecutionProvider
from app.services.execution.providers.metaapi import MetaApiOrderExecutionProvider
from app.services.execution.providers.mock import MockOrderExecutionProvider
from app.services.execution.providers.rate_limited import RateLimitedExecutionProvider


def _build_metaapi_provider() -> OrderExecutionProvider:
    if not settings.metaapi_token or not settings.metaapi_account_id:
        raise ExecutionProviderConfigurationError(
            "metaapi is configured as execution_provider but METAAPI_TOKEN/"
            "METAAPI_ACCOUNT_ID are not both set (EA Bot spec §0.7)"
        )
    return MetaApiOrderExecutionProvider(
        token=settings.metaapi_token,
        account_id=settings.metaapi_account_id,
        timeout_seconds=settings.metaapi_request_timeout_seconds,
    )


_PROVIDER_FACTORIES: dict[str, Callable[[], OrderExecutionProvider]] = {
    "mock": MockOrderExecutionProvider,
    "metaapi": _build_metaapi_provider,
}


def get_execution_provider() -> OrderExecutionProvider:
    """Builds the single active execution provider (EA Bot spec §1/§2).

    Deliberately not a fan-out list like `get_market_data_providers()` -
    exactly one provider is ever active
    (`settings.execution_provider`), never a failover chain, since a
    fallback firing after a partial failure could double-place a real
    order. Wrapped in `RateLimitedExecutionProvider` unconditionally, same
    convention as market data's uniform `RateLimitedProvider` wrapping.
    """
    factory = _PROVIDER_FACTORIES.get(settings.execution_provider)
    if factory is None:
        raise ExecutionProviderConfigurationError(
            f"Unknown execution provider configured: {settings.execution_provider!r}"
        )
    return RateLimitedExecutionProvider(factory(), settings.execution_rate_limit_per_minute)


def get_broker_order_repository(
    db: Annotated[Session, Depends(get_db)],
) -> BrokerOrderRepository:
    return BrokerOrderRepository(db)


def get_order_execution_service(
    broker_order_repository: Annotated[BrokerOrderRepository, Depends(get_broker_order_repository)],
) -> OrderExecutionService:
    """Composes `OrderExecutionService` (EA Bot spec §3G) - injected into
    `SignalEngine` as an optional dependency (§1), so every existing
    `SignalEngine` construction site that doesn't need execution is
    unaffected."""
    return OrderExecutionService(
        get_execution_provider(),
        broker_order_repository,
        execution_enabled=settings.execution_enabled,
        execution_symbol=settings.execution_symbol,
        risk_percent=Decimal(str(settings.execution_risk_percent)),
        max_open_positions=settings.execution_max_open_positions,
    )
