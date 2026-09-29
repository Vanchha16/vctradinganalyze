import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaperSwingSummary(BaseModel):
    """Closed paper trades count toward the result; `open` is only a count."""

    trades: int
    open: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float | None
    total_r: float
    avg_r: float | None
    max_drawdown_r: float
    profit_factor: float | None
    avg_holding_hours: float | None


class PaperSwingStatisticsResponse(BaseModel):
    """ADR-182 - the paper record next to the backtest it is judged against."""

    enabled: bool
    strategy_version: str
    started_at: datetime | None
    weeks_running: float
    trades_per_week: float | None
    overall: PaperSwingSummary
    by_pair: dict[str, PaperSwingSummary]
    by_direction: dict[str, PaperSwingSummary]
    rejected: dict[str, int]
    skipped_trade_open: int
    backtest_reference: dict[str, dict[str, float]]


class PaperSwingTradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    strategy_version: str
    setup: str
    direction: str
    d1_trend: str
    status: str
    reject_reason: str | None
    signal_time: datetime
    pivot_time: datetime
    origin_time: datetime
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_pips: Decimal
    reward_pips: Decimal
    risk_reward: Decimal
    atr_h4_pips: Decimal
    adr_pips: Decimal | None
    spread_pips: Decimal
    closed_at: datetime | None
    exit_price: Decimal | None
    swap_pips: Decimal | None
    result_pips: Decimal | None
    result_r: Decimal | None
    holding_hours: Decimal | None


class PaperSwingTradeListResponse(BaseModel):
    items: list[PaperSwingTradeResponse]
    total: int
    offset: int
    limit: int
