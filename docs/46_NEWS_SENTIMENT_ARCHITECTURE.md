# News Sentiment Architecture

# 1. Scope

Phase 5A's `NewsSentimentEngine` (`app/services/news_sentiment_engine.py`) collects, deduplicates, classifies, and scores financial news articles, publishing structured sentiment evidence - it never generates a BUY/SELL/WAIT recommendation (docs/10 §1, ADR-031/ADR-043's no-recommendation precedent extended here).

Unlike Phase 4's four engines, News Sentiment is **not** wired into `AnalysisConfidenceEngine` in this phase - ADR-047 explicitly reserved that integration for a future ADR once News Sentiment (this engine) actually exists. Do not add News as a `confidence_aggregator.combine()` component as part of Phase 5A.

See docs/10_NEWS_SENTIMENT_ENGINE.md for the product-level vision this document implements (and narrows into concrete, buildable decisions).

---

# 2. Persistence Model (ADR-052, ADR-053)

News Sentiment persists real entities - it is **not** stateless like Technical Analysis (ADR-027), Market Regime (ADR-038), or the Confidence Engine (ADR-045). It is closer to SMC's persisted-`smc_events` pattern (ADR-032/033), but with its own mixin choices per table (ADR-053), since articles and sentiment have different mutability than SMC's status-transitioning events:

| Table | Mixin | Rationale |
|---|---|---|
| `news_sources` | `TimestampMixin` | Small, admin-managed list; `priority`/`is_active`/`tier` can change after creation. |
| `news_articles` | `CreatedAtMixin` + `published_at` | Append-only once ingested; `created_at` = our ingestion time, `published_at` = source's own publish time. |
| `news_sentiment` | `TimestampMixin` | Recomputable in place if scoring logic changes and historical articles are re-scored. |

One `news_sentiment` row per `news_article` (`article_id` unique FK), with `affected_assets` stored as a JSON list column - mirrors `SMCEvent.context`'s JSON-column pattern rather than a normalized per-asset child table (ADR-052).

---

# 3. Data Flow

Unlike every Phase 4 engine (one read-only `analyze()` call per request), News Sentiment has **two distinct paths**:

```
Ingestion path (Celery Beat scheduled, write path):
NewsIngestionPipeline.run()
  -> NewsProvider.fetch_latest(since)          [MockNewsProvider in Phase 5A, ADR-050]
  -> dedup_detector.is_duplicate(candidate, existing)   [ADR-054]
  -> category_classifier.classify(article)              [ADR-055]
  -> importance_scorer.score(article, source_tier, category)  [ADR-055]
  -> sentiment_scorer.score(article)            [ADR-051, deterministic]
  -> asset_detector.detect(article)             [matches against AssetRepository]
  -> ai_summary_generator.generate(article, sentiment_evidence)  [ADR-051, isolated AI call, may return None]
  -> scoring_engine.aggregate(...)              [-> NewsSentimentEvidence]
  -> NewsArticleRepository.create(...)
  -> NewsSentimentRepository.create(...)

Read path (on-demand, API-triggered):
NewsSentimentEngine.get_sentiment_for_asset(asset, since)
  -> NewsSentimentRepository.find_by_asset_since(asset.symbol, since)
  -> NewsSentimentResult
```

The ingestion path never blocks on the AI summary call - if `ai_summary_generator.generate()` fails or times out, ingestion proceeds with `ai_summary = None` and every other field populated normally (docs/10 §1's "no BUY/SELL" and never-block-on-AI principle extended to availability).

---

# 4. Module List

```
app/models/news_source.py                  # NewsSource(Base, UUIDMixin, TimestampMixin)
app/models/news_article.py                 # NewsArticle(Base, UUIDMixin, CreatedAtMixin)
app/models/news_sentiment.py                # NewsSentiment(Base, UUIDMixin, TimestampMixin)
app/models/enums.py                         # + NewsSourceTier, NewsCategory, NewsImportance, NewsSentimentLabel

app/repositories/news_source_repository.py
app/repositories/news_article_repository.py
app/repositories/news_sentiment_repository.py

app/services/news/providers/base.py         # NewsProvider Protocol, RawNewsArticle, NewsProviderCapabilities
app/services/news/providers/mock.py         # MockNewsProvider
app/services/news/providers/exceptions.py   # NewsProviderError hierarchy

app/services/news_sentiment/types.py                  # NewsSentimentEvidence, NewsArticleEvidence
app/services/news_sentiment/dedup_detector.py          # ADR-054
app/services/news_sentiment/category_classifier.py     # ADR-055
app/services/news_sentiment/importance_scorer.py       # ADR-055
app/services/news_sentiment/sentiment_scorer.py        # ADR-051 (deterministic)
app/services/news_sentiment/asset_detector.py          # matches article text against Asset symbols/names
app/services/news_sentiment/ai_summary_generator.py    # ADR-051 (isolated AI call)
app/services/news_sentiment/scoring_engine.py          # aggregates the above into NewsSentimentEvidence

app/services/news_sentiment_engine.py       # top-level read-path orchestrator
app/services/news_ingestion_pipeline.py     # top-level write-path orchestrator (Celery-triggered)

app/dependencies/news.py                    # provider wiring (_PROVIDER_FACTORIES)
app/schemas/news.py                         # NewsSourceOut, NewsArticleOut, NewsArticleDetailOut, NewsSentimentOut
app/api/v1/routes/news.py                   # GET /news, GET /news/{id}, GET /analysis/news/{symbol}
app/workers/news_sentiment_tasks.py         # register_news_schedule(), Celery task
```

---

# 5. Scoring Algorithm (ADR-055)

**Importance** (`importance_scorer.py`) - a floor-and-escalate rule table, evaluated in order, first match wins:

| Rule | Importance |
|---|---|
| Category in {Central Bank, Breaking News} AND Tier-1 source | Critical |
| Category in {Inflation, Employment, GDP, Interest Rates} AND Tier-1 or Tier-2 source | Critical |
| Category in {Central Bank, Breaking News} (any other tier) | High |
| Category in {Politics, War, Energy, Regulation} | High |
| Category in {Inflation, Employment, GDP, Interest Rates} (any other tier) | Medium |
| Category in {Commodities, Crypto, Corporate Earnings} | Medium |
| Tier-3 source, no category rule matched above | Low |
| No rule matched | Low |

`Ignore` is a reserved enum value for future manual/noise-filtering overrides - the deterministic scorer never emits it in Phase 5A, since docs/10 §8 gives no worked example of what should be ignored outright. This directly encodes docs/10 §8's worked examples (FOMC/NFP/CPI/GDP → Critical; PMI/Retail Sales/Consumer Confidence → High) as testable rule-table entries rather than prose illustrations.

**Sentiment** (`sentiment_scorer.py`) - a hand-built financial polarity lexicon scores title + summary text: each matched keyword contributes a signed weight (e.g. "rate hike" -2, "beats expectations" +2, "recession" -3, "stronger than forecast" +2); the summed score maps onto the 5-value enum via fixed bands (`>= 3` Very Bullish, `1..2` Bullish, `0` Neutral, `-1..-2` Bearish, `<= -3` Very Bearish); `confidence` is derived from the number and strength of matched keywords relative to article length (more/stronger matches = higher confidence, starting-point thresholds not yet tuned against real outcomes - same caveat as every prior scoring ADR).

**Category** (`category_classifier.py`) - keyword/pattern matching against the 12 docs/10 §5 categories; first matching category wins, "Corporate Earnings" as the fallback default if no keyword matches (least likely to be systematically wrong for an unclassified financial headline).

---

# 6. Evidence Schema

```
NewsSentimentEvidence:
    article_id: UUID
    headline: str
    category: NewsCategory
    importance: NewsImportance
    sentiment: NewsSentimentLabel
    confidence: float          # 0-100
    reason: str
    affected_assets: list[str] # asset symbols
    ai_summary: str | None     # populated only if ai_summary_generator succeeded
    published_at: datetime
    source: str
```

This is the shape a future Phase 6 AI Orchestrator, or a future Confidence Engine integration ADR (per ADR-047's Future Review), would consume - modeled after `WeightedComponent`/`ConfidenceBreakdown`'s typed-schema precedent (ADR-046) rather than docs/10 §13's informal Source/Evidence/Score/Reason prose example.

---

# 7. Duplicate Detection (ADR-054)

```
is_duplicate(candidate, existing_articles) -> bool:
    for existing in existing_articles:
        if normalize_url(candidate.url) == normalize_url(existing.url):
            return True
        if title_similarity(candidate.title, existing.title) >= 0.85 \
           and abs(candidate.published_at - existing.published_at) <= timedelta(hours=6):
            return True
    return False
```

`normalize_url` strips scheme case, tracking query parameters, and trailing slashes. `title_similarity` uses a token-set based ratio (e.g. Jaccard over lowercased, punctuation-stripped tokens) - no ML/LLM/"AI Hash" involved, fully deterministic and unit-testable with fixed input/output pairs.

---

# 8. Provider Abstraction (ADR-050)

`NewsProvider` is a `typing.Protocol` mirroring `MarketDataProvider`'s shape:

```python
class NewsProvider(Protocol):
    name: str
    def fetch_latest(self, since: datetime) -> list[RawNewsArticle]: ...
    def health_check(self) -> bool: ...
    def capabilities(self) -> NewsProviderCapabilities: ...
```

`MockNewsProvider` (`app/services/news/providers/mock.py`) is the **only** implementation shipped in Phase 5A - a sha256-seeded deterministic generator (mirroring `MockMarketDataProvider`) that never fails and produces plausible articles spanning categories/sources/importance levels for engine and API testing. No real vendor (NewsAPI, Benzinga, etc.) is integrated in this phase - explicitly deferred to a follow-up sub-phase once a vendor is chosen and provisioned (ADR-050).

**Update (Phase 9G, ADR-139):** `NewsIngestionPipeline.run()` no longer returns a bare `int` - it returns `NewsIngestionResult` (`ingested: int`, `provider_outcomes: list[ProviderOutcome]`), and raises `AllNewsProvidersFailedError` if every configured provider failed, rather than silently returning `0`. Production ran with an empty news pipeline for a real stretch of time because a provider failure only ever logged a `warning` and returned that same `0` - indistinguishable from "nothing published today." A provider failure now logs at `ERROR` (`news_ingestion.provider_call`, mirroring `market_data_service.py`'s structured-logging shape). `Pipeline.provider_names`/`.uses_mock` are new read-only properties, surfaced in `GET /admin/system` (docs/58 §3.2) so mock usage is never silently discovered later. `backend/scripts/diagnose_ingestion.py` is a new manual, read-only operator tool for confirming (or ruling out) the real vendor-side cause in production - see ADR-139 for the full design.

---

# 9. AI Summary (ADR-051)

`ai_summary_generator.generate(article, sentiment_evidence) -> str | None` is the **only** AI-touching module in the News Sentiment Engine. Guardrails (docs/10 §14, mirrored from docs/07 §9's project-wide AI guardrails):

- Must reference the source article; never invent facts, quotes, numbers, or forecasts not present in the article text.
- Maximum 150 words (enforced post-generation, truncated/rejected if exceeded rather than trusting the prompt alone).
- Must include: Summary, Market Impact, Affected Assets, Risk, Confidence (docs/10 §9).
- On any failure (API error, timeout, guardrail violation) returns `None` - ingestion proceeds with every other field populated; the AI summary is enrichment, never a blocking dependency.
- Never influences `sentiment`, `confidence`, `category`, `importance`, or `affected_assets` - those are fully deterministic outputs of the other modules, computed independently.

This is the project's first LLM-dependent, non-deterministic, cost-per-call code path (in tension with `app/services/analysis_confidence/summary_builder.py`'s established template-only precedent) - deliberately isolated to this one narrowly-scoped module so the rest of the engine remains deterministic and unit-testable without live API calls (`test_news_ai_summary_generator.py` mocks the OpenAI client).

---

# 10. Not Timeframe-Scoped

Every Phase 4 engine's public method signature is `analyze(asset, timeframe)`. News Sentiment has **no timeframe concept** - news is asset/time-window scoped, not candle-timeframe scoped. `NewsSentimentEngine.get_sentiment_for_asset(asset, since)` takes a `since: datetime` (or a relative window like `24h`), not a `Timeframe` enum. This is a deliberate architectural divergence, not an oversight - documented here explicitly because every reader familiar with Phase 4's pattern will otherwise expect a `timeframe` query param on `GET /analysis/news/{symbol}`, and none exists.

---

# 11. Testing Strategy

| File | Covers |
|---|---|
| `test_news_dedup_detector.py` | URL exact-match, title-similarity threshold boundary, time-window boundary |
| `test_news_category_classifier.py` | Each of the 12 categories, fallback default |
| `test_news_importance_scorer.py` | Each rule-table row, docs/10 §8's worked examples as literal test cases |
| `test_news_sentiment_scorer.py` | Each sentiment band boundary, confidence derivation |
| `test_news_asset_detector.py` | Symbol/name matching against seeded assets, multi-asset articles |
| `test_news_ai_summary_generator.py` | OpenAI client mocked; word-cap enforcement; graceful `None` on failure - never calls the real API |
| `test_news_sentiment_engine.py` | Read-path integration against persisted fixtures |
| `test_news_ingestion_pipeline.py` | Full pipeline integration against `MockNewsProvider`; dedup skip; graceful AI-summary-failure handling |
| `test_news_source_repository.py`, `test_news_article_repository.py`, `test_news_sentiment_repository.py` | Repository query methods |
| `test_news_routes.py` | `GET /news`, `GET /news/{id}`, `GET /analysis/news/{symbol}`; 404 on unknown asset/article; no-auth-required |
| `test_mock_news_provider.py` | Deterministic seeded generation, `health_check()` always true |

Verified by inspection (every analyzer/rule/scenario has a dedicated test), consistent with Phases 4A-4D's practice - coverage tooling is still not installed (BACKLOG.md §4).

---

# 12. Out of Scope for Phase 5A

Real news provider/vendor integration (ADR-050's follow-up); Confidence Engine integration/weight rebalancing (ADR-047's boundary - do not touch `analysis_confidence_engine.py`/`confidence_aggregator.py`); `/ws/news` WebSocket endpoint (BACKLOG.md, tied to features that don't exist yet); true sub-30-second breaking-news SLA validation (unvalidatable without a real push-capable provider - only sentiment-computation latency is testable against the mock); translation/multi-language support; social/X sentiment; FinBERT or any ML-model-based sentiment upgrade (docs/10 §18, ADR-051's deterministic-lexicon decision for v1); `POST /admin/news` manual ingestion endpoint; a `/multi-asset` analysis endpoint.
