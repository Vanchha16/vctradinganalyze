import uuid
from typing import Any

import structlog

from app.exceptions import ConflictException, ResourceNotFoundException, ValidationException
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.enums import MarketType
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository

logger = structlog.get_logger(__name__)


class AdminAssetService:
    """Business rules for admin-driven symbol/asset management (Phase 9F).

    Mirrors `AdminUserService`'s shape: constructor-injected repositories,
    one public method per use case, private `_audit`/`_commit` helpers.
    `Asset.is_active` is the single control point for three production
    pipelines (`market_data_tasks.py`, `signal_tasks.py`,
    `news_ingestion_pipeline.py`) - every mutation here is audited, same
    as every other admin write in this project.
    """

    def __init__(
        self,
        asset_repository: AssetRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._asset_repository = asset_repository
        self._audit_log_repository = audit_log_repository

    # --- Reads ---------------------------------------------------------

    def list_assets(
        self,
        *,
        search: str | None = None,
        market_type: MarketType | None = None,
        is_active: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Asset], int]:
        offset = (page - 1) * limit
        items = self._asset_repository.list_filtered(
            search=search,
            market_type=market_type,
            is_active=is_active,
            offset=offset,
            limit=limit,
        )
        total = self._asset_repository.count_filtered(
            search=search, market_type=market_type, is_active=is_active
        )
        return list(items), total

    # --- Mutations -------------------------------------------------------

    def create_asset(
        self,
        actor: User,
        *,
        symbol: str,
        name: str,
        market_type: MarketType,
        exchange: str | None = None,
        base_currency: str | None = None,
        quote_currency: str | None = None,
        ip_address: str | None = None,
    ) -> Asset:
        # Uppercased for the same reason `market_data.py`'s `get_asset_or_404`
        # normalizes lookups ("eurusd" == "EURUSD") - every existing seeded
        # asset is already stored uppercase; a lowercase admin-created row
        # would silently fail every symbol-keyed lookup elsewhere.
        symbol = symbol.upper()

        if self._asset_repository.get_by_symbol(symbol) is not None:
            raise ConflictException(f"Symbol {symbol!r} already exists.")

        asset = self._asset_repository.create(
            Asset(
                symbol=symbol,
                name=name,
                market_type=market_type,
                exchange=exchange,
                base_currency=base_currency,
                quote_currency=quote_currency,
                is_active=True,
            )
        )

        self._audit(
            actor.id,
            action="admin_asset_created",
            resource_id=asset.id,
            ip_address=ip_address,
            context={"new": {"symbol": symbol, "name": name, "market_type": market_type.value}},
        )
        self._commit()
        logger.info("admin.asset_created", actor_id=str(actor.id), target_id=str(asset.id))
        return asset

    def update_asset(
        self,
        actor: User,
        target_id: uuid.UUID,
        *,
        symbol: str | None = None,
        name: str | None = None,
        market_type: MarketType | None = None,
        exchange: str | None = None,
        base_currency: str | None = None,
        quote_currency: str | None = None,
        ip_address: str | None = None,
    ) -> Asset:
        """`symbol` is accepted only so an attempt to change it produces a
        clear rejection rather than a silently-ignored field - it is the
        natural key every `price_candle`/`indicator_result`/`smc_event` row
        is tied to via `asset_id`, and provider symbol mapping keys off it
        (docs/41). Renaming it would silently orphan the meaning of all
        existing history (ADR-138)."""
        target = self._resolve_target(target_id)

        if symbol is not None and symbol.upper() != target.symbol:
            raise ValidationException("Symbol cannot be changed after creation.")

        old: dict[str, Any] = {}
        new: dict[str, Any] = {}

        if name is not None and name != target.name:
            old["name"], new["name"] = target.name, name
            target.name = name

        if market_type is not None and market_type != target.market_type:
            old["market_type"], new["market_type"] = target.market_type.value, market_type.value
            target.market_type = market_type

        if exchange is not None and exchange != target.exchange:
            old["exchange"], new["exchange"] = target.exchange, exchange
            target.exchange = exchange

        if base_currency is not None and base_currency != target.base_currency:
            old["base_currency"], new["base_currency"] = target.base_currency, base_currency
            target.base_currency = base_currency

        if quote_currency is not None and quote_currency != target.quote_currency:
            old["quote_currency"], new["quote_currency"] = target.quote_currency, quote_currency
            target.quote_currency = quote_currency

        if new:
            self._audit(
                actor.id,
                action="admin_asset_updated",
                resource_id=target.id,
                ip_address=ip_address,
                context={"old": old, "new": new},
            )
            self._commit()
            logger.info("admin.asset_updated", actor_id=str(actor.id), target_id=str(target.id))
        return target

    def activate(
        self, actor: User, target_id: uuid.UUID, *, ip_address: str | None = None
    ) -> Asset:
        return self._set_active(actor, target_id, is_active=True, ip_address=ip_address)

    def deactivate(
        self, actor: User, target_id: uuid.UUID, *, ip_address: str | None = None
    ) -> Asset:
        """Stops all three consumers immediately (§1): market data
        collection, hourly AI signal generation, and news matching - all
        filter on `is_active`. Existing `ACTIVE`/`TRIGGERED` signals for
        this asset are deliberately left to resolve naturally (ADR-138
        §3.4) - a live call should not vanish because someone tidied the
        symbol list."""
        return self._set_active(actor, target_id, is_active=False, ip_address=ip_address)

    # --- Internal helpers --------------------------------------------------

    def _resolve_target(self, target_id: uuid.UUID) -> Asset:
        target = self._asset_repository.get_by_id(target_id)
        if target is None:
            raise ResourceNotFoundException("Asset not found.")
        return target

    def _set_active(
        self, actor: User, target_id: uuid.UUID, *, is_active: bool, ip_address: str | None
    ) -> Asset:
        target = self._resolve_target(target_id)
        old_status = target.is_active
        target.is_active = is_active

        self._audit(
            actor.id,
            action="admin_asset_activated" if is_active else "admin_asset_deactivated",
            resource_id=target.id,
            ip_address=ip_address,
            context={"old": {"is_active": old_status}, "new": {"is_active": is_active}},
        )
        self._commit()
        logger.info(
            "admin.asset_status_changed",
            actor_id=str(actor.id),
            target_id=str(target.id),
            is_active=is_active,
        )
        return target

    def _audit(
        self,
        actor_id: uuid.UUID,
        *,
        action: str,
        resource_id: uuid.UUID,
        ip_address: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLog(
                user_id=actor_id,
                action=action,
                resource="asset",
                resource_id=resource_id,
                ip_address=ip_address,
                context=context,
            )
        )

    def _commit(self) -> None:
        self._asset_repository.commit()
