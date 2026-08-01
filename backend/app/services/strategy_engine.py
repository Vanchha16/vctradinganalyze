"""Top-level Strategy Engine orchestrator (docs/17, docs/49).

Classifies which of seven strategy methodologies fits current market
evidence for a given asset/timeframe - never a BUY/SELL/trade-level
recommendation (ADR-069, extends ADR-031/ADR-043). Fully stateless
(ADR-070). Reuse-first (ADR-071): `AnalysisConfidenceEngine` is the
primary dependency (transitively yields Technical Analysis/SMC/Market
Regime evidence in one call), and `risk_management`'s
`session_classifier`/`liquidity_filter`/`economic_filter` sub-modules
supply the remaining risk-relevant evidence directly - never a full
`RiskManagementEngine.evaluate()` call, which needs a candidate trade
setup this engine doesn't have.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.asset import Asset
from app.models.enums import Timeframe
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar.types import EconomicEventEvidence
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.risk_management import economic_filter, liquidity_filter, session_classifier
from app.services.strategy import ranking, strategy_scorer
from app.services.strategy.types import StrategyEvaluation, StrategyEvidenceBundle, StrategyName

_ECONOMIC_LOOKBACK_HOURS = 2
_ECONOMIC_LOOKAHEAD_HOURS = 24
_LIQUIDITY_LOOKBACK_CANDLES = 20


class StrategyEngine:
    def __init__(
        self,
        confidence_engine: AnalysisConfidenceEngine,
        economic_calendar_engine: EconomicCalendarEngine,
        price_candle_repository: PriceCandleRepository,
    ) -> None:
        self._confidence_engine = confidence_engine
        self._economic_calendar_engine = economic_calendar_engine
        self._price_candle_repository = price_candle_repository

    def evaluate(self, asset: Asset, timeframe: Timeframe) -> StrategyEvaluation:
        now = datetime.now(UTC)
        warnings: list[str] = []

        confidence = self._confidence_engine.analyze(asset, timeframe)

        session = session_classifier.classify(now)

        latest_candle = self._price_candle_repository.get_latest(asset.id, timeframe)
        recent_candles = self._price_candle_repository.list_recent(
            asset.id, timeframe, limit=_LIQUIDITY_LOOKBACK_CANDLES
        )
        recent_volumes = [c.volume for c in recent_candles if c.volume is not None]
        recent_average_volume: Decimal | None = (
            sum(recent_volumes, start=Decimal(0)) / len(recent_volumes) if recent_volumes else None
        )
        liquidity = liquidity_filter.classify(
            latest_candle.volume if latest_candle is not None else None, recent_average_volume
        )

        economic_events = self._economic_events_for(asset, now)
        economic = economic_filter.analyze(economic_events)

        evidence = StrategyEvidenceBundle(
            technical=confidence.technical,
            smc=confidence.smc,
            market_regime=confidence.market_regime,
            overall_confidence=confidence.overall_confidence,
            session=session,
            liquidity=liquidity,
            economic=economic,
        )

        no_evidence = (
            confidence.technical is None
            and confidence.smc is None
            and confidence.market_regime is None
        )
        if no_evidence:
            warnings.append("No candle data available - every strategy's evidence is unavailable.")

        scores = {
            strategy: strategy_scorer.score(strategy, evidence, timeframe)
            for strategy in StrategyName
        }
        primary_strategy, primary_breakdown, alternatives, rejected = ranking.rank(scores)

        return StrategyEvaluation(
            symbol=asset.symbol,
            timeframe=timeframe,
            primary_strategy=primary_strategy,
            strategy_score=primary_breakdown.total if primary_breakdown is not None else None,
            breakdown=primary_breakdown,
            calculated_at=now,
            alternative_strategies=alternatives,
            rejected_strategies=rejected,
            warnings=warnings,
        )

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
