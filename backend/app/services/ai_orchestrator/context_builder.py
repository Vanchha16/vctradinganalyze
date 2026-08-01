"""Builds `AnalysisContext` once per `AIOrchestratorEngine.generate()`
call (docs/50 §3/§5) - every upstream engine is called at most once."""

from datetime import UTC, datetime, timedelta

from app.models.asset import Asset
from app.models.enums import Timeframe
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar.types import EconomicCalendarResult
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.news_sentiment_engine import NewsSentimentEngine
from app.services.risk_management_engine import RiskManagementEngine
from app.services.strategy_engine import StrategyEngine

from . import candidate_setup_builder
from .types import AnalysisContext

_NEWS_LOOKBACK_HOURS = 24
_ECONOMIC_LOOKBACK_HOURS = 2
_ECONOMIC_LOOKAHEAD_HOURS = 24


class ContextBuilder:
    def __init__(
        self,
        confidence_engine: AnalysisConfidenceEngine,
        news_sentiment_engine: NewsSentimentEngine,
        economic_calendar_engine: EconomicCalendarEngine,
        strategy_engine: StrategyEngine,
        risk_management_engine: RiskManagementEngine,
    ) -> None:
        self._confidence_engine = confidence_engine
        self._news_sentiment_engine = news_sentiment_engine
        self._economic_calendar_engine = economic_calendar_engine
        self._strategy_engine = strategy_engine
        self._risk_management_engine = risk_management_engine

    def build(self, asset: Asset, timeframe: Timeframe) -> AnalysisContext:
        now = datetime.now(UTC)

        confidence = self._confidence_engine.analyze(asset, timeframe)

        since = now - timedelta(hours=_NEWS_LOOKBACK_HOURS)
        news = self._news_sentiment_engine.get_sentiment_for_asset(asset.symbol, since)

        economic = self._economic_events_for(asset, now)

        strategy = self._strategy_engine.evaluate(asset, timeframe)

        candidate_setup = candidate_setup_builder.build(confidence, strategy)

        risk = None
        if candidate_setup is not None:
            risk = self._risk_management_engine.evaluate(
                asset,
                timeframe,
                candidate_setup.direction,
                candidate_setup.entry_price,
                candidate_setup.stop_loss,
                candidate_setup.take_profit,
            )

        return AnalysisContext(
            asset=asset,
            timeframe=timeframe,
            confidence=confidence,
            news=news,
            economic=economic,
            strategy=strategy,
            candidate_setup=candidate_setup,
            risk=risk,
        )

    def _economic_events_for(self, asset: Asset, now: datetime) -> EconomicCalendarResult:
        start = now - timedelta(hours=_ECONOMIC_LOOKBACK_HOURS)
        end = now + timedelta(hours=_ECONOMIC_LOOKAHEAD_HOURS)
        currencies = {c for c in (asset.base_currency, asset.quote_currency) if c is not None}

        all_events = []
        for currency in currencies:
            result, _ = self._economic_calendar_engine.list_events(
                currency=currency, start=start, end=end, limit=100
            )
            all_events.extend(result.events)

        return EconomicCalendarResult(calculated_at=now, events=all_events, warnings=[])
