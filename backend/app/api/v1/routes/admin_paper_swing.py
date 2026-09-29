"""Swing strategy paper trading - read only (ADR-182).

Super-admin only, like Strategy Settings: this is the evidence the
operator decides live trading on. Nothing here can place, change or send
anything; the switch that starts and stops the paper run is the
`paper_swing_enabled` runtime setting.
"""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.dependencies.admin import get_paper_swing_service
from app.dependencies.rbac import require_super_admin
from app.models.user import User
from app.schemas.admin_paper_swing import (
    PaperSwingStatisticsResponse,
    PaperSwingSummary,
    PaperSwingTradeListResponse,
    PaperSwingTradeResponse,
)
from app.services.paper_swing import rules
from app.services.paper_swing_service import BACKTEST_REFERENCE, PaperSwingService

router = APIRouter(prefix="/admin/paper-swing", tags=["admin"])

_Service = Annotated[PaperSwingService, Depends(get_paper_swing_service)]
_Symbol = Literal["EURUSD", "GBPUSD", "USDJPY"]
_Status = Literal["taken", "open", "win", "loss", "timeout", "rejected", "skipped"]


@router.get("/statistics", response_model=PaperSwingStatisticsResponse)
async def paper_swing_statistics(
    _actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> PaperSwingStatisticsResponse:
    stats = service.statistics(datetime.now(UTC))
    return PaperSwingStatisticsResponse(
        enabled=settings.paper_swing_enabled,
        strategy_version=rules.STRATEGY_VERSION,
        started_at=stats.started_at,
        weeks_running=stats.weeks_running,
        trades_per_week=stats.trades_per_week,
        overall=PaperSwingSummary(**asdict(stats.overall)),
        by_pair={k: PaperSwingSummary(**asdict(v)) for k, v in stats.by_pair.items()},
        by_direction={k: PaperSwingSummary(**asdict(v)) for k, v in stats.by_direction.items()},
        rejected=stats.rejected,
        skipped_trade_open=stats.skipped_trade_open,
        backtest_reference=BACKTEST_REFERENCE,
    )


@router.get("/trades", response_model=PaperSwingTradeListResponse)
async def list_paper_swing_trades(
    _actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
    symbol: _Symbol | None = None,
    status: _Status | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PaperSwingTradeListResponse:
    rows, total = service.list_trades(symbol=symbol, status=status, offset=offset, limit=limit)
    return PaperSwingTradeListResponse(
        items=[PaperSwingTradeResponse.model_validate(r) for r in rows],
        total=total,
        offset=offset,
        limit=limit,
    )
