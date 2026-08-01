"""Top-level Risk Management Engine orchestrator (docs/12, docs/48).

Evaluates a caller-supplied candidate trade setup (ADR-062) - not a
persisted Signal, since no Signal Engine exists yet. Fully stateless
(ADR-063): every `evaluate()` call recomputes fresh. Reuse-first
(ADR-064): `AnalysisConfidenceEngine` is the primary dependency,
transitively yielding Technical Analysis, SMC, and Market Regime
evidence in one call (ADR-049's pre-computation chaining) - no new
volatility or trend classification is invented here.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.asset import Asset
from app.models.enums import Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar.types import EconomicEventEvidence
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.market_regime.types import VolatilityRegimeState
from app.services.news_sentiment_engine import NewsSentimentEngine
from app.services.risk_management import (
    correlation_analyzer,
    decision,
    economic_filter,
    liquidity_filter,
    news_scorer,
    risk_reward_validator,
    session_classifier,
    spread_filter,
    stop_loss_validator,
    trade_quality_aggregator,
)
from app.services.risk_management.types import (
    LiquidityClassification,
    MarketSession,
    RiskEvaluation,
    SpreadClassification,
    TradeDirection,
)

logger = logging.getLogger(__name__)

_NEWS_LOOKBACK_HOURS = 24
_ECONOMIC_LOOKBACK_HOURS = 2
_ECONOMIC_LOOKAHEAD_HOURS = 24
_CORRELATION_LOOKBACK_CANDLES = 100

_LOW_LIQUIDITY_PENALTY = -3.0
_UNKNOWN_LIQUIDITY_PENALTY = -1.0
_HIGH_SPREAD_PENALTY = -3.0
_CORRELATION_PENALTY_PER_PAIR = -2.0
_CORRELATION_PENALTY_FLOOR = -4.0
_OFF_HOURS_SESSION_PENALTY = -1.0
_OFF_HOURS_SESSIONS = frozenset({MarketSession.ASIAN, MarketSession.SYDNEY})


class RiskManagementEngine:
    def __init__(
        self,
        confidence_engine: AnalysisConfidenceEngine,
        news_sentiment_engine: NewsSentimentEngine,
        economic_calendar_engine: EconomicCalendarEngine,
        price_candle_repository: PriceCandleRepository,
        asset_repository: AssetRepository,
    ) -> None:
        self._confidence_engine = confidence_engine
        self._news_sentiment_engine = news_sentiment_engine
        self._economic_calendar_engine = economic_calendar_engine
        self._price_candle_repository = price_candle_repository
        self._asset_repository = asset_repository

    def evaluate(
        self,
        asset: Asset,
        timeframe: Timeframe,
        direction: TradeDirection,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        spread: Decimal | None = None,
    ) -> RiskEvaluation:
        now = datetime.now(UTC)
        rejected_reasons: list[str] = []
        warnings: list[str] = []

        confidence = self._confidence_engine.analyze(asset, timeframe)
        volatility_state = (
            confidence.market_regime.volatility.state if confidence.market_regime else None
        )
        trend_strength = confidence.technical.strength.value if confidence.technical else None
        technical_score = confidence.technical.technical_score if confidence.technical else None
        smc_score = confidence.smc.smc_score if confidence.smc else None
        atr = confidence.technical.volatility.atr if confidence.technical else None
        order_blocks = confidence.smc.order_blocks if confidence.smc else []
        liquidity_zones = confidence.smc.liquidity_zones if confidence.smc else []

        # Session
        session = session_classifier.classify(now)
        if session is MarketSession.CLOSED:
            rejected_reasons.append("Market is closed (weekend).")

        # Volatility (reused from Market Regime, ADR-064)
        if volatility_state is VolatilityRegimeState.EXTREME:
            rejected_reasons.append("Volatility is extreme.")
        elif volatility_state is VolatilityRegimeState.VERY_LOW:
            warnings.append("Volatility is very low - reduced confidence.")

        # Spread (optional caller input, ADR-065)
        spread_classification: SpreadClassification | None = None
        spread_penalty = 0.0
        if spread is not None:
            spread_classification = spread_filter.classify(spread, entry_price)
            if spread_classification is SpreadClassification.EXTREME:
                rejected_reasons.append("Spread is extreme.")
            elif spread_classification is SpreadClassification.HIGH:
                spread_penalty = _HIGH_SPREAD_PENALTY
                warnings.append("Spread is high.")
        else:
            warnings.append("Spread not supplied - Spread Filter skipped.")

        # Liquidity (relative-volume proxy, ADR-066)
        latest_candle = self._price_candle_repository.get_latest(asset.id, timeframe)
        recent_candles = self._price_candle_repository.list_recent(asset.id, timeframe, limit=20)
        recent_volumes = [c.volume for c in recent_candles if c.volume is not None]
        recent_average_volume: Decimal | None = (
            sum(recent_volumes, start=Decimal(0)) / len(recent_volumes) if recent_volumes else None
        )
        liquidity_classification = liquidity_filter.classify(
            latest_candle.volume if latest_candle is not None else None, recent_average_volume
        )
        liquidity_penalty = 0.0
        if liquidity_classification is LiquidityClassification.LOW:
            liquidity_penalty = _LOW_LIQUIDITY_PENALTY
            warnings.append("Liquidity is low relative to its recent average.")
        elif liquidity_classification is LiquidityClassification.UNKNOWN:
            liquidity_penalty = _UNKNOWN_LIQUIDITY_PENALTY

        # Correlation (fixed curated pairs, ADR-067)
        correlation_penalty = self._correlation_penalty(asset, timeframe, warnings)

        # Session off-hours minor penalty (docs/48 §7)
        session_penalty = _OFF_HOURS_SESSION_PENALTY if session in _OFF_HOURS_SESSIONS else 0.0

        # Economic events (reused from Phase 5B, ADR-064)
        economic_events = self._economic_events_for(asset, now)
        economic_result = economic_filter.analyze(economic_events)
        if economic_result.hard_reject and economic_result.reason:
            rejected_reasons.append(economic_result.reason)

        # Risk/Reward
        rr_result = risk_reward_validator.validate(entry_price, stop_loss, take_profit)
        if rr_result.below_minimum:
            rejected_reasons.append("Risk/reward is below the 1:2 minimum.")

        # Stop-loss
        stop_loss_result = stop_loss_validator.validate(
            entry_price, stop_loss, atr, order_blocks, liquidity_zones
        )
        if stop_loss_result.too_tight:
            rejected_reasons.append("Stop-loss is unrealistically tight relative to ATR.")
        warnings.extend(stop_loss_result.warnings)

        # News score
        since = now - timedelta(hours=_NEWS_LOOKBACK_HOURS)
        news_result = self._news_sentiment_engine.get_sentiment_for_asset(asset.symbol, since)
        news_score = news_scorer.score(news_result.articles, direction)

        # Aggregate
        risk_penalties = [
            spread_penalty,
            liquidity_penalty,
            correlation_penalty,
            session_penalty,
        ]
        breakdown = trade_quality_aggregator.aggregate(
            trend_strength=trend_strength,
            technical_score=technical_score,
            smc_score=smc_score,
            risk_penalties=risk_penalties,
            news_score=news_score,
            economic_score=economic_result.economic_score,
        )

        tier = decision.tier_for_score(breakdown.total)
        approved = decision.is_approved(rejected_reasons, tier)
        risk_level = decision.risk_level_for(volatility_state, tier)
        position_guidance = decision.position_guidance_for(approved, tier, risk_level)

        logger.info(
            "risk_evaluation",
            extra={
                "symbol": asset.symbol,
                "timeframe": timeframe.value,
                "trade_quality": breakdown.total,
                "risk_level": risk_level.value,
                "approved": approved,
                "rejected_reasons": rejected_reasons,
            },
        )

        return RiskEvaluation(
            symbol=asset.symbol,
            timeframe=timeframe,
            direction=direction,
            approved=approved,
            risk_level=risk_level,
            tier=tier,
            breakdown=breakdown,
            risk_reward=rr_result.risk_reward,
            position_guidance=position_guidance,
            calculated_at=now,
            rejected_reasons=rejected_reasons,
            warnings=warnings,
        )

    def _correlation_penalty(
        self, asset: Asset, timeframe: Timeframe, warnings: list[str]
    ) -> float:
        counterparts = correlation_analyzer.counterparts_for(asset.symbol)
        if not counterparts:
            return 0.0

        own_candles = self._price_candle_repository.list_recent(
            asset.id, timeframe, limit=_CORRELATION_LOOKBACK_CANDLES
        )
        own_closes = [c.close for c in own_candles]

        total_penalty = 0.0
        for counterpart_symbol in counterparts:
            counterpart = self._asset_repository.get_by_symbol(counterpart_symbol)
            if counterpart is None:
                continue
            counterpart_candles = self._price_candle_repository.list_recent(
                counterpart.id, timeframe, limit=_CORRELATION_LOOKBACK_CANDLES
            )
            counterpart_closes = [c.close for c in counterpart_candles]

            correlation = correlation_analyzer.pearson_correlation(own_closes, counterpart_closes)
            if correlation_analyzer.is_highly_correlated(correlation):
                total_penalty += _CORRELATION_PENALTY_PER_PAIR
                warnings.append(
                    f"{asset.symbol} is highly correlated ({correlation:.2f}) with "
                    f"{counterpart_symbol} - avoid stacking correlated exposure."
                )

        return max(_CORRELATION_PENALTY_FLOOR, total_penalty)

    def _economic_events_for(self, asset: Asset, now: datetime) -> list[EconomicEventEvidence]:
        start = now - timedelta(hours=_ECONOMIC_LOOKBACK_HOURS)
        end = now + timedelta(hours=_ECONOMIC_LOOKAHEAD_HOURS)
        currencies = {c for c in (asset.base_currency, asset.quote_currency) if c is not None}

        events: list[EconomicEventEvidence] = []
        for currency in currencies:
            result, _ = self._economic_calendar_engine.list_events(
                currency=currency, start=start, end=end, limit=100
            )
            events.extend(result.events)
        return events
