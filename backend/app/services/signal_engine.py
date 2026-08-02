"""Top-level Signal Engine (docs/11, docs/51).

A thin wrapper over `AIOrchestratorEngine` (ADR-085) - introduces no new
evidence weighting, confidence, or recommendation logic. Persists a
`Signal` row only for an actionable BUY/SELL outcome (ADR-086); WAIT
produces no row (docs/50/docs/51 - the full reasoning trail stays
available via `analysis_id`).
"""

import uuid
from dataclasses import dataclass

from app.models.asset import Asset
from app.models.enums import Recommendation, SignalType, Timeframe
from app.models.signal import Signal
from app.repositories.signal_repository import SignalRepository
from app.services.ai_orchestrator.types import AIAnalysisResult
from app.services.ai_orchestrator_engine import AIOrchestratorEngine
from app.services.risk_management import risk_reward_validator


@dataclass(frozen=True, slots=True)
class SignalGenerationResult:
    """docs/51 §6 - the engine's public result. `signal` is `None` when
    `recommendation` is WAIT (ADR-086)."""

    analysis_id: uuid.UUID
    symbol: str
    timeframe: Timeframe
    recommendation: Recommendation
    signal: Signal | None


_SIGNAL_TYPE_BY_RECOMMENDATION = {
    Recommendation.BUY: SignalType.BUY,
    Recommendation.SELL: SignalType.SELL,
}


class SignalEngine:
    def __init__(
        self,
        ai_orchestrator_engine: AIOrchestratorEngine,
        signal_repository: SignalRepository,
    ) -> None:
        self._ai_orchestrator_engine = ai_orchestrator_engine
        self._signal_repository = signal_repository

    def generate(self, asset: Asset, timeframe: Timeframe) -> SignalGenerationResult:
        result = self._ai_orchestrator_engine.generate(asset, timeframe)

        if result.recommendation not in _SIGNAL_TYPE_BY_RECOMMENDATION:
            return SignalGenerationResult(
                analysis_id=result.id,
                symbol=result.symbol,
                timeframe=result.timeframe,
                recommendation=result.recommendation,
                signal=None,
            )

        signal = self._persist(asset, result)
        return SignalGenerationResult(
            analysis_id=result.id,
            symbol=result.symbol,
            timeframe=result.timeframe,
            recommendation=result.recommendation,
            signal=signal,
        )

    def _persist(self, asset: Asset, result: AIAnalysisResult) -> Signal:
        assert result.entry_price is not None
        assert result.stop_loss is not None
        assert result.take_profit is not None

        rr = risk_reward_validator.validate(
            result.entry_price, result.stop_loss, result.take_profit
        )

        signal = Signal(
            analysis_id=result.id,
            asset_id=asset.id,
            timeframe=result.timeframe,
            signal_type=_SIGNAL_TYPE_BY_RECOMMENDATION[result.recommendation],
            entry_price=result.entry_price,
            stop_loss=result.stop_loss,
            take_profit=result.take_profit,
            risk_reward=rr.risk_reward,
            confidence=result.confidence_score,
        )
        self._signal_repository.create(signal)
        self._signal_repository.commit()
        return signal
