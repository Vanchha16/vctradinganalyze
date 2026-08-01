"""Evidence dataclasses for the News Sentiment Engine (docs/10, docs/46).

Unlike Technical Analysis/SMC/Market Regime/Confidence, this engine is not
`timeframe`-scoped - it is asset/time-window scoped (docs/46 §10). Every
field here is deterministic except `ai_summary`, which is the isolated
output of `ai_summary_generator.py` (ADR-051) and may be `None`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.models.enums import NewsCategory, NewsImportance, NewsSentimentLabel


@dataclass(frozen=True, slots=True)
class RawArticleClassification:
    """Intermediate output of the deterministic analyzers
    (`category_classifier`, `importance_scorer`, `sentiment_scorer`,
    `asset_detector`) for one candidate article, before persistence -
    consumed by `scoring_engine.aggregate` to build `NewsSentimentEvidence`."""

    category: NewsCategory
    importance: NewsImportance
    sentiment: NewsSentimentLabel
    confidence: float
    reason: str
    affected_assets: list[str]


@dataclass(frozen=True, slots=True)
class NewsSentimentEvidence:
    """docs/46 §6 - the shape a future Phase 6 AI Orchestrator, or a
    future Confidence Engine integration ADR (ADR-047's Future Review),
    would consume."""

    article_id: UUID
    headline: str
    category: NewsCategory
    importance: NewsImportance
    sentiment: NewsSentimentLabel
    confidence: float
    reason: str
    affected_assets: list[str]
    ai_summary: str | None
    published_at: datetime
    source: str


@dataclass(frozen=True, slots=True)
class NewsSentimentResult:
    """Read-path result for `NewsSentimentEngine.get_sentiment_for_asset`
    (docs/46 §3, backs `GET /analysis/news/{symbol}`)."""

    symbol: str
    since: datetime
    calculated_at: datetime
    articles: list[NewsSentimentEvidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
