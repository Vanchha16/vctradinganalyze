# AI Orchestrator Architecture

# 1. Scope

Phase 6A's `AIOrchestratorEngine` (`app/services/ai_orchestrator_engine.py`) is the first engine in this project authorized to produce a BUY/SELL/WAIT recommendation (ADR-078, extending ADR-005/031/043/069's boundary). Combines what docs/07 calls "orchestration" (collect context, decide) and docs/13 calls "reasoning" (narrate) into one class (ADR-077).

**The AI never computes anything a deterministic engine already computes.** Every numeric/classification field in the final response - recommendation, confidence, risk level, entry/stop/target, execution guidance, supporting/conflicting evidence, risks, invalidation conditions - is either reused verbatim from an existing engine or produced by a new deterministic module (§5). The LLM's sole output is the `reasoning` object's seven narrative-text sections.

Signal Engine (6B) and AI Chat Assistant (6C) are explicitly out of scope (ADR-084) - each requires its own documentation-first session.

See docs/07_AI_ORCHESTRATOR.md and docs/13_AI_REASONING_ENGINE.md for the product-level vision this document implements and narrows into concrete, buildable decisions.

---

# 2. Persistence Model (ADR-082)

`ai_analysis` is the first genuinely persisted engine output in this project - not because persistence is convenient, but because an LLM call is not perfectly reproducible on replay, unlike every Phase 4/5 deterministic engine. `UUIDMixin` + `CreatedAtMixin` (append-only, mirrors `news_articles`' ADR-053 precedent) - an analysis row represents "what was recommended at time X," never rewritten in place.

`signals` (docs/03 §11) is explicitly out of scope for 6A - a future Signal Engine's own table (ADR-084).

---

# 3. Data Flow

```
AIOrchestratorEngine.generate(asset, timeframe)
  -> context_builder.build(asset, timeframe)
       -> AnalysisConfidenceEngine.analyze(asset, timeframe)     [-> .technical, .smc, .market_regime, .overall_confidence, .conflicts]
       -> NewsSentimentEngine.get_sentiment_for_asset(symbol, since=24h)
       -> EconomicCalendarEngine.list_events(currency={base,quote}, window)
       -> StrategyEngine.evaluate(asset, timeframe)
       -> candidate_setup_builder.build(strategy, technical, smc, market_regime)   [ADR-080, None if no viable direction]
       -> RiskManagementEngine.evaluate(candidate)               [only if a candidate exists]
       -> AnalysisContext
  -> recommendation_decision.decide(context)                     [ADR-078, BUY/SELL/WAIT, deterministic]
  -> evidence_extractor.extract(context)                         [supporting_evidence, conflicting_evidence, risks]
  -> invalidation_builder.build(context, recommendation)         [invalidation_conditions]
  -> prompt_builder.build(context, recommendation, evidence)     [-> system prompt, user prompt, JSON schema]
  -> provider.generate(request)                                  [ADR-081, one retry, else fallback]
  -> response_parser.parse(response)                              [validate, or trigger fallback]
       -> summary_fallback.build(context, recommendation)         [if provider/parse failed]
  -> ai_analysis_repository.create(...)                           [persist]
  -> AIAnalysisResult
```

Every upstream engine is called **at most once** per `generate()` execution - `AnalysisConfidenceEngine` already internally computes Technical Analysis/SMC/Market Regime exactly once each (ADR-049's existing chaining); `RiskManagementEngine.evaluate()` is called at most once, only when a candidate setup exists.

---

# 4. Reuse Map

| Field | Source |
|---|---|
| Technical Analysis, SMC, Market Regime, Confidence Score | `AnalysisConfidenceEngine.analyze()` |
| News Sentiment | `NewsSentimentEngine.get_sentiment_for_asset()` |
| Economic Events | `EconomicCalendarEngine.list_events()` |
| Strategy fit | `StrategyEngine.evaluate()` |
| Risk approval, risk level, execution guidance | `RiskManagementEngine.evaluate()` (only when a candidate setup exists, ADR-080) |

No bespoke re-derivation of anything Phase 4A-5D already computes.

---

# 5. AnalysisContext

```
AnalysisContext:
    asset: Asset
    timeframe: Timeframe
    confidence: ConfidenceResult
    news: NewsSentimentResult
    economic: EconomicCalendarResult
    strategy: StrategyEvaluation
    candidate_setup: CandidateSetup | None
    risk: RiskEvaluation | None
```

Built once per `generate()` call by `context_builder.py`, threaded through every deterministic module and the prompt builder - no engine is called twice (mirrors `StrategyEvidenceBundle`'s precedent, Phase 5D).

---

# 6. New Deterministic Modules

**`candidate_setup_builder.py`** (ADR-080) - the chicken-and-egg resolver: Risk Management needs a candidate trade to evaluate, nothing upstream produces one. Builds a candidate only if `StrategyEvaluation.primary_strategy` is non-null and `MarketRegimeResult.trend_regime.direction` is unambiguous (BULLISH or BEARISH, not SIDEWAYS):

```
entry_price = latest close
stop_loss   = beyond nearest support/resistance, or entry -+ 1.5x ATR, whichever is more conservative
take_profit = entry -+ max(2x risk distance, nearest opposing SMC structure)
```

Reuses `TechnicalAnalysisResult.support`/`.resistance`/`.volatility.atr` and `SMCAnalysisResult` structure - never invents a price.

**`recommendation_decision.py`** (ADR-078) - the core decision tree:

| Condition | Recommendation | Reason |
|---|---|---|
| No candidate setup built | WAIT | "No viable strategy for current conditions." |
| `RiskEvaluation.approved is False` | WAIT | `risk.rejected_reasons` (Risk Engine's hard-reject veto, ADR-014) |
| `confidence.confidence_level` in {VERY_LOW, LOW} | WAIT | "Confidence too low for a reliable recommendation." |
| `confidence.conflict_severity is HIGH` | WAIT | "Conflicting evidence across engines." (docs/13 §9) |
| else | BUY or SELL | matches candidate direction |

**`invalidation_builder.py`** - deterministic template sentences from already-known facts: stop-loss breach, an opposing `MarketRegimeState` shift, an upcoming CRITICAL economic event entering its risk window. Never LLM-generated, never invented.

**`evidence_extractor.py`** - deterministic bullet extraction from `AnalysisContext`'s already-typed fields:
- `supporting_evidence`: facts consistent with the recommendation direction (e.g. EMA alignment, confirmed Order Block, matching Strategy).
- `conflicting_evidence`: `ConfidenceResult.conflicts` (already has `.description`/`.severity`) + `RiskEvaluation.rejected_reasons` if any.
- `risks`: `RiskEvaluation.warnings` + in-risk-window `EconomicEventEvidence` + Market Regime volatility state.

---

# 7. Prompt Architecture

`prompt_builder.py`, `PROMPT_VERSION = "1.0.0"` (a plain string constant, git-versioned, no separate prompts table - persisted per `ai_analysis` row satisfying ADR-015/018's replayability requirement):

- **System prompt**: professional/objective/no-hype tone (docs/13 §12); explicit guardrails - never invent facts/prices/numbers not present in the provided context, reference only given evidence, output must match the JSON schema exactly, never output a recommendation/confidence/price field (those are provided as fixed facts, not requested).
- **User prompt**: the serialized `AnalysisContext` **plus** the already-decided `recommendation`, `confidence`, `risk_level`, candidate prices, and every deterministic evidence list - the model is given the decision, asked only to explain it.
- **Output schema**: `reasoning` object with exactly seven string fields (`summary`, `technical`, `smc`, `economic`, `news`, `risk`, `conclusion`), each word-capped (mirrors `ai_summary_generator._enforce_word_cap`'s precedent).

---

# 8. Provider Abstraction (ADR-081)

```python
class AIProvider(Protocol):
    name: str
    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse: ...
    def health_check(self) -> bool: ...
```

`OpenAIProvider` is the sole real implementation - reuses `ai_summary_generator.py`'s httpx-Client-with-injectable-`transport` pattern, extended with OpenAI's structured-output `response_format: {"type": "json_schema", ...}` (supported by the already-configured `gpt-4o-mini`). `MockAIProvider` exists for test injection only (mirrors `httpx.MockTransport`'s role in `test_news_ai_summary_generator.py`).

Future providers (Anthropic/Gemini/local) implement the same `Protocol` and register in `app/dependencies/ai_orchestrator.py`'s `_PROVIDER_FACTORIES` dict - zero change to `AIOrchestratorEngine`.

---

# 9. Structured Output, Parsing, Recovery (ADR-081)

1. OpenAI structured-output mode constrains the model at generation time - malformed JSON should be rare.
2. `response_parser.py` still validates defensively (schema shape, missing keys, word-cap overflow).
3. On a transient provider failure (timeout, 5xx): retry once (`ai_retry_max_attempts`/`ai_retry_backoff_seconds`, mirrors `market_data_retry_*` naming).
4. On a still-malformed response after parsing fails once: one follow-up request with an explicit "return only valid JSON matching the schema" instruction.
5. If all of the above fail: graceful degradation to `summary_fallback.py`'s deterministic template `reasoning` (mirrors `analysis_confidence/summary_builder.py`'s no-AI-text precedent), `ai_available=False`, a `warnings` entry noting AI narration was unavailable - **never an exception surfaced to the caller**. Every field except `reasoning` is already fully computed before the provider is ever called.

---

# 10. Caching

None in 6A. Every deterministic engine in this project recomputes fresh on every call (no caching precedent anywhere, Phase 4-5); the context-building cost (4 engine calls plus at most one Risk evaluation) is fast. Caching the LLM narrative specifically would risk returning stale reasoning for a materially different market moments later. Flagged as a BACKLOG item for future cost optimization once real usage volume is known - not built speculatively.

---

# 11. API (ADR-083)

```
POST /analysis/ai/{symbol}?timeframe=H1     [authenticated - reuses get_current_user]
GET  /analysis/ai/{id}                       [authenticated]
GET  /analysis/history?symbol=&page=&limit=  [authenticated, scoped to requesting user]
```

The first analysis-family routes requiring authentication - ties real per-call LLM cost and per-call persistence to an identifiable account (ADR-083). `POST /analysis/ai/batch` is explicitly deferred (no demonstrated need yet).

---

# 12. Testing Strategy

| File | Covers |
|---|---|
| `test_ai_candidate_setup_builder.py` | Direction resolution, stop/target construction, `None` when no viable direction |
| `test_ai_recommendation_decision.py` | Every branch of the decision tree independently |
| `test_ai_invalidation_builder.py` | Each template condition |
| `test_ai_evidence_extractor.py` | Supporting/conflicting/risks extraction from fixed context fixtures |
| `test_ai_prompt_builder.py` | System/user prompt content, schema shape, version constant |
| `test_ai_response_parser.py` | Valid parse, malformed JSON, missing keys, word-cap overflow, retry-then-recover |
| `test_ai_openai_provider.py` | `httpx.MockTransport`-injected success/failure/timeout - never a real API call, mirrors `test_news_ai_summary_generator.py` exactly |
| `test_ai_orchestrator_engine.py` | Integration against real upstream engines on a seeded SQLite session, `MockAIProvider` injected, mirrors `test_strategy_engine.py` |
| `test_ai_analysis_routes.py` | 401 without auth, 404 on unknown id, persisted-row shape, full response contract |

Verified by inspection, consistent with every prior phase's practice - coverage tooling is still not installed (BACKLOG.md §4).

---

# 13. Out of Scope for Phase 6A

Signal Engine (6B); AI Chat Assistant (6C); `signals` table; `POST /analysis/ai/batch`; response caching; real rate-limiting/quota infrastructure; Confidence Engine weight-rebalancing to include News/Economic/Risk (ADR-047's boundary respected, untouched); prompt A/B testing, multi-agent reasoning, historical calibration (docs/13 §16); Anthropic/Gemini/local providers (abstraction supports them, none implemented); Dashboard/Telegram notification (Phase 7, downstream services don't exist).
