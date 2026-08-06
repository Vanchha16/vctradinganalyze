# API Specification

Version: 1.0

Base URL

/api/v1

Protocol

HTTPS

Response Format

application/json

Authentication

JWT Bearer Token

---

# Standard Response

Success

Returned as-is (no envelope wrapper). Example, `GET /auth/me`:

{
  "id": "uuid",
  "email": "user@example.com",
  "username": "john",
  ...
}

Error

{
  "error": "invalid_credentials",
  "message": "Invalid email or password."
}

Note (as of Phase 2C): this corrects an earlier draft of this document, which described a `{"success", "message", "data"/"errors"}` envelope that was never implemented. `docs/33_API_CONTRACTS.md` described a third, different shape. Neither matched the exception-handling code already built in Phase 1 (`app/exceptions/handlers.py`), which returns `{"error": <error_code>, "message": <message>}` on failure and the resource itself (unwrapped) on success — see docs/37_AUTHENTICATION_FLOW.md and BACKLOG.md for the decision record.

---

# Authentication

POST /auth/register

Description

Create new account.

Request

{
  "email": "user@example.com",
  "username": "john",
  "password": "********",
  "full_name": "John Doe"
}

Response

201 Created

{
  "id": "uuid",
  "email": "user@example.com",
  "username": "john",
  "full_name": "John Doe",
  "role": "registered",
  "is_active": true,
  "is_verified": false,
  "last_login": null,
  "created_at": "2026-07-31T00:00:00Z"
}

---

POST /auth/login

Request

{
  "email": "user@example.com",
  "password": "********"
}

Response

{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 900
}

`expires_in` is always derived from configuration (`settings.jwt_access_expire_minutes`), never hardcoded — currently 900 seconds (15 minutes).

---

POST /auth/refresh

Generate new access token.

Request

{
  "refresh_token": "..."
}

Response

{
  "access_token": "...",
  "refresh_token": null,
  "expires_in": 900
}

Only a new access token is issued; `refresh_token` is `null` in this response (see docs/37 §4 — refresh-token rotation-on-use is not yet implemented).

---

POST /auth/logout

Invalidate refresh token (deletes the corresponding session; idempotent).

Request

{
  "refresh_token": "..."
}

Response

204 No Content

---

POST /auth/forgot-password

**Not yet implemented.** Blocked on the email-delivery infrastructure this flow depends on (see BACKLOG.md). Listed here as the target contract for when that phase is built.

---

POST /auth/reset-password

**Not yet implemented.** Same dependency as above.

---

GET /auth/me

Return current user profile. Requires `Authorization: Bearer <access_token>`.

Response

{
  "id": "uuid",
  "email": "user@example.com",
  "username": "john",
  "full_name": "John Doe",
  "role": "registered",
  "is_active": true,
  "is_verified": false,
  "last_login": "2026-07-31T00:00:00Z",
  "created_at": "2026-07-30T00:00:00Z"
}

---

Note: session/device-management endpoints (list sessions, revoke one/all — docs/23 §6/§11) are intentionally not yet listed here. The underlying business logic exists (`AuthenticationService.revoke_session`/`revoke_all_sessions`, built in Phase 2B), but no route contract has been designed or approved yet — see BACKLOG.md.

---

# Users

GET /users/profile

Update profile

PUT /users/profile

Upload avatar

POST /users/avatar

Delete account

DELETE /users/account

---

# Dashboard

GET /dashboard

Return:

Portfolio Summary

Latest Signals

Market Overview

Economic Calendar

Watchlist

News

---

# Assets

GET /assets

Return supported assets. Public - no authentication required (docs/23 §12 Guest role: "View Public Pages").

Query parameters

page (default 1)

limit (default 20, max 100)

market_type (forex, metal, crypto, index)

is_active (true/false)

Response

{
  "items": [ { "id", "symbol", "name", "market_type", "exchange", "base_currency", "quote_currency", "is_active" } ],
  "page": 1,
  "limit": 20,
  "total": 42
}

Example symbols

EURUSD

GBPUSD

BTCUSD

XAUUSD

NAS100

US30

---

GET /assets/{symbol}

Return asset details. Public. `{symbol}` is case-insensitive (`eurusd` and `EURUSD` return the same asset). 404 if unknown.

---

# Market Data

GET /market/{symbol}/latest

Public. Renamed from an earlier `GET /market/{symbol}` draft (Phase 3C) to make the endpoint's purpose explicit - it returns only the single most recent candle, not a market snapshot.

Query

timeframe (required)

Response

{
  "timestamp", "open", "high", "low", "close", "volume"
}

Note: "Spread" was listed in an earlier draft of this endpoint, but is not part of the data model (docs/03 §5 `price_candles` doesn't track it, and no integrated provider - Twelve Data included - supplies it in the `time_series` response this project consumes). It is intentionally omitted from the response rather than fabricated. Revisit if a future provider or data source supplies real spread data.

404 if no candles exist yet for that asset/timeframe.

---

GET /market/{symbol}/candles

Public.

Parameters

timeframe (required)

from (optional - ISO 8601 datetime; if omitted, returns the most recent `limit` candles instead of a bounded range)

to (optional - defaults to now)

limit (default 100, max 1000 - higher than the general list-endpoint cap of 100, since time-series/chart data legitimately needs more rows per request)

Response

{
  "symbol", "timeframe",
  "items": [ { "timestamp", "open", "high", "low", "close", "volume" } ]
}

---

GET /market/{symbol}/indicators

Public. Returns **raw** indicator values as calculated and stored (docs/39_INDICATOR_REFERENCE.md) - EMA, RSI, MACD, ADX, ATR, VWAP, etc. This is deliberately distinct from `GET /analysis/technical/{symbol}` below, which returns Phase 4's *synthesized* trend/strength/technical-score output once that engine exists. Do not confuse the two: this endpoint exists today and returns exactly what `indicator_results` stores; `/analysis/technical/{symbol}` does not exist yet.

Parameters

timeframe (required)

indicator (optional - must be a registered indicator name, e.g. `rsi_14`, `macd`; validated against the indicator registry, docs/39 §7 summary table - an unknown name is rejected, not silently ignored)

limit (default 100, max 1000)

Response

{
  "symbol", "timeframe",
  "items": [ { "indicator", "value", "metadata", "calculated_at" } ]
}

---

# Technical Analysis

Implemented (Phase 4A - Technical Analysis Engine, docs/08, docs/42). Deterministic evidence only (ADR-031) - never a BUY/SELL/WAIT recommendation. Public - no authentication required, same rationale as `GET /market/{symbol}/indicators` above (non-personalized reference-style content).

GET /analysis/technical/{symbol}?timeframe=H1

Query parameters

timeframe (required)

Response

{
  "symbol", "timeframe",
  "trend", "strength",
  "technical_score",
  "score_breakdown": { "trend", "momentum", "oscillator", "volume", "volatility", "support_resistance", "penalties", "total" },
  "support": { "price", "source", "strength" },
  "resistance": { "price", "source", "strength" },
  "support_levels": [ { "price", "source", "strength" } ],
  "resistance_levels": [ { "price", "source", "strength" } ],
  "indicators": { "ema_20": "...", "rsi_14": "...", "...": "..." },
  "warnings": [],
  "calculated_at"
}

`score_breakdown` and structured `support`/`resistance` objects (price + source + strength, not bare numbers) are Phase 4A additions beyond docs/08 §11's original sketch - see docs/42 §7/§11 for the full contract and rationale.

404 if the asset is unknown, or if no candles exist yet for that asset/timeframe.

---

GET /analysis/technical/{symbol}/multi-timeframe

Public. Combines Daily/H4/H1/M15 trend classifications into one verdict (docs/08 §8, ADR-030) - distinct from the single-timeframe endpoint above.

Response

{
  "symbol",
  "verdict",
  "timeframes": [ { "timeframe", "trend", "strength" } ]
}

---

# Smart Money Concepts

GET /analysis/smc/{symbol}?timeframe=H1

Public (no authentication, matching Technical Analysis's precedent). `{symbol}` is case-insensitive. Deterministic structured evidence only - no BUY/SELL recommendation (docs/09, docs/43).

Response

{
  "symbol", "timeframe",
  "market_structure": { "state", "classifications": [ { "kind", "price", "timestamp", "index" } ] },
  "bos": [ { "direction", "break_price", "break_time", "strength", "confirmed" } ],
  "choch": [ { "previous_trend", "new_trend", "confidence", "confirmation_time" } ],
  "order_blocks": [ { "direction", "zone_high", "zone_low", "created_at", "status", "touched", "mitigated", "broken", "strength_score", "freshness_score", "volume_confirmed", "is_breaker", "breaker_confirmed", "retest_count" } ],
  "fair_value_gaps": [ { "direction", "gap_high", "gap_low", "created_at", "status", "gap_size", "priority" } ],
  "liquidity_zones": [ { "side", "level", "touch_count", "status", "created_at" } ],
  "liquidity_sweeps": [ { "side", "level", "sweep_time", "false_breakout" } ],
  "premium_discount": { "position", "distance", "range_high", "range_low", "equilibrium" },
  "confluence": { "factors": [], "confluence_score" },
  "smc_score",
  "score_breakdown": { "market_structure", "order_blocks", "fair_value_gaps", "liquidity", "premium_discount", "confluence", "penalties", "total" },
  "warnings": [],
  "calculated_at"
}

This replaces docs/09 §17's flat example (`"bos": true`, single `smc_score` with no breakdown) - see docs/43 §6 for the correction and rationale. `status` values are `active`/`mitigated`/`invalidated`/`archived` (ADR-037). `smc_score` is never combined with `technical_score` (ADR-036).

404 if the asset is unknown, or if no candles exist yet for that asset/timeframe.

---

GET /analysis/smc/{symbol}/multi-timeframe

Public. Combines Weekly/Daily/H4/H1/M15 market-structure classifications into one verdict (docs/09 §15, ADR-036) - distinct from the single-timeframe endpoint above.

Response

{
  "symbol",
  "verdict",
  "timeframes": [ { "timeframe", "state" } ],
  "conflict": { "is_pullback", "conflicts": [] }
}

---

# Market Regime

GET /analysis/market-regime/{symbol}?timeframe=H1

Public (no authentication). `{symbol}` is case-insensitive. Deterministic classification only - no BUY/SELL recommendation, no strategy guidance (docs/16, docs/44, ADR-043).

Response

{
  "symbol", "timeframe",
  "regime",
  "confidence",
  "confidence_breakdown": { "trend_clarity", "volatility_clarity", "structural_confirmation", "stability_penalty", "conflict_penalty", "total" },
  "trend_regime": { "direction", "strength", "structure_state", "aligned" },
  "volatility": { "state", "recent_atr_average", "baseline_atr_average" },
  "range": { "is_ranging", "range_width", "range_strength" },
  "expansion": { "state", "ratio" },
  "transition": { "shifting", "from_hint", "to_hint", "confidence" },
  "accumulation_distribution": { "accumulation_score", "distribution_score" },
  "breakout": { "detected", "direction", "volume_confirmed" },
  "pullback_reversal": { "pullback_depth", "retracement_ratio", "reversal_direction", "reversal_confidence", "exhaustion_warning" },
  "candidates": [ { "regime", "confidence", "precedence" } ],
  "warnings": [],
  "calculated_at"
}

`regime` is one of docs/16 §3's eleven values exactly - never an invented value. `confidence` is distinct from `technical_score`/`smc_score` (ADR-042) - it measures how reliable this classification is, not evidence strength. 404 if the asset is unknown, or if no candles exist yet for that asset/timeframe.

---

GET /analysis/market-regime/{symbol}/multi-timeframe

Public. Combines Weekly/Daily/H4/H1/M15 regime classifications into one verdict (ADR-036's timeframe set, reused per docs/44 §12).

Response

{
  "symbol",
  "verdict",
  "timeframes": [ { "timeframe", "regime" } ]
}

---

# Confidence

GET /analysis/confidence/{symbol}?timeframe=H1

Public (no authentication). `{symbol}` is case-insensitive. Evaluates the quality/completeness/consistency of Technical Analysis's, SMC's, and Market Regime's evidence - no BUY/SELL recommendation, no trade-outcome prediction (docs/15, docs/45, ADR-031, ADR-043, ADR-047).

Response

{
  "symbol", "timeframe",
  "overall_confidence", "confidence_level",
  "summary",
  "technical": { ...TechnicalAnalysisResponse or null... },
  "smc": { ...SMCAnalysisResponse or null... },
  "market_regime": { ...MarketRegimeResponse or null... },
  "alignment": { "technical_direction", "smc_direction", "regime_direction", "agreement_ratio", "agreement_score" },
  "conflicts": [ { "description", "severity", "engines_involved" } ],
  "conflict_severity",
  "missing_data": [],
  "warnings": [],
  "breakdown": { "technical_alignment", "smc_alignment", "regime_confirmation", "cross_engine_agreement", "data_completeness", "freshness", "conflict_penalty", "total" },
  "calculated_at"
}

`confidence_level` is one of `very_low`/`low`/`moderate`/`high`/`very_high` (docs/15 §4). `summary` is a deterministic, template-built 2-3 sentence string - no AI-generated language. Unlike Technical Analysis/SMC/Market Regime, this endpoint does **not** 404 when an upstream engine has no candle data for the timeframe - it degrades gracefully, returning 200 with reduced confidence and the affected engine's field set to `null` plus a `missing_data` entry (docs/15 §15). 404 only if the asset symbol itself is unknown.

---

GET /analysis/confidence/{symbol}/multi-timeframe

Public. Combines Weekly/Daily/H4/H1/M15 confidence results into one verdict (same timeframe set as Market Regime/SMC, docs/45 §12).

Response

{
  "symbol",
  "verdict",
  "timeframes": [ { "timeframe", "overall_confidence", "confidence_level" } ]
}

`verdict` is `aligned` only when every timeframe's `confidence_level` is `high`/`very_high`; otherwise `mixed`. Always returns all 5 timeframes, even ones with no candle data (graceful degradation applies per-timeframe too).

---

# News

Phase 5A (docs/46_NEWS_SENTIMENT_ARCHITECTURE.md, ADR-050 through ADR-055). Public (no authentication) - matches the analysis routes' no-auth convention. `MockNewsProvider`-ingested data only in Phase 5A; no real vendor yet (ADR-050).

GET /news

Parameters

page

limit

importance (Critical/High/Medium/Low/Ignore)

category (one of docs/10 §5's 12 values)

Response

{
  "items": [ { "id", "source", "title", "summary", "category", "importance", "published_at", "sentiment", "confidence" } ],
  "page", "limit", "total"
}

`currency` filtering is dropped - no `news_articles`/`news_sentiment` column ever backed it (this doc's own prior gap). Asset-scoped filtering is `GET /analysis/news/{symbol}` below, not a filter on this list endpoint.

---

GET /news/{id}

Return full article + sentiment detail.

Response

{
  "id", "source", "title", "summary", "content", "url", "category", "importance", "published_at",
  "sentiment": { "sentiment", "confidence", "reason", "affected_assets", "ai_summary" }
}

404 if the article id is unknown. `ai_summary` is `null` if the AI summary call failed or was skipped (ADR-051) - never blocks the rest of the response.

---

# News Sentiment

GET /analysis/news/{symbol}?since=24h

Public. `{symbol}` is case-insensitive. Returns already-ingested sentiment evidence for the asset over the requested window - **no `timeframe` parameter** (News is asset/time-window scoped, not candle-timeframe scoped, docs/46 §10).

Response

{
  "symbol", "since",
  "articles": [ { "id", "headline", "category", "importance", "sentiment", "confidence", "reason", "affected_assets", "ai_summary", "published_at", "source" } ],
  "warnings": [],
  "calculated_at"
}

`sentiment` is one of `very_bullish`/`bullish`/`neutral`/`bearish`/`very_bearish` (docs/10 §7's 5-value enum) - never the free-text `"Bullish USD"` shape this doc previously (incorrectly) implied, and never the binary `Bullish`/`Bearish` this section previously documented. 404 only if the asset symbol is unknown - an empty `articles` list (no matching news in the window) is a valid 200, not a 404. No `/multi-asset` variant exists (deliberately not built, docs/46 §12).

Out of scope for Phase 5A: `POST /admin/news` (deferred, then built in Phase 7D-C - see the Admin section below and ADR-130), `/ws/news` (deferred - not built, tracked in BACKLOG.md).

---

# Economic Calendar

Phase 5B (docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md, ADR-056 through ADR-061). Public (no authentication). Replaces the stale `/economic/*` draft this section previously held - `/calendar` is the final prefix (shorter, matches the user-requested candidate list, mirrors `/analysis/news` not needing an `/economic` echo of the data domain).

GET /calendar

Parameters

country

currency

importance (Critical/High/Medium/Low)

category (one of docs/14 §3's 7 values)

from, to (date range)

range (`today` or `week` - a shortcut over `from`/`to`; `/calendar/today`, `/calendar/week`, `/calendar/high-impact`, `/calendar/currency/{currency}` are deliberately **not** separate routes - this one endpoint's filters absorb them, docs/47 §11)

page, limit

Response

{
  "items": [ { "id", "country", "currency", "event_name", "category", "importance", "forecast", "previous", "actual", "surprise", "unit", "status", "release_time", "risk_window", "market_bias" } ],
  "page", "limit", "total"
}

`risk_window` and `market_bias` are computed at read time, never stored (ADR-061/ADR-060) - `market_bias` is `null` until `actual` is known (no surprise to compute a direction from yet).

---

GET /calendar/{id}

Return full event detail (same shape as one list item). 404 if the id is unknown.

---

GET /calendar/upcoming

Public. Next N high-impact (Critical/High) events ordered by `release_time` ascending - a dedicated convenience route distinct from `GET /calendar`'s general filtering (docs/47 §11).

Response: same item shape as `GET /calendar`.

Out of scope for Phase 5B: `POST /admin/calendar`-style manual ingestion, `/ws/calendar`, any endpoint exposing a trade recommendation derived from calendar evidence.

---

# Risk Management

Phase 5C (docs/48_RISK_MANAGEMENT_ARCHITECTURE.md, ADR-062 through ADR-068). Public (no authentication).

POST /risk/evaluate

The first POST-based endpoint in the analysis-engine family - a candidate trade setup (direction/entry/stop/target) is inherently a request body, not query params. Evaluates a caller-supplied candidate setup (ADR-062) - not a persisted Signal, since no Signal Engine exists yet.

Request

{
  "symbol": "EURUSD", "timeframe": "H1", "direction": "long",
  "entry_price": 1.17540, "stop_loss": 1.17120, "take_profit": 1.18150,
  "spread": 0.00012
}

`spread` is optional (ADR-065) - omitted rather than fabricated when the caller has no live quote; the Spread Filter is skipped (not defaulted) in that case.

Response

{
  "approved": true,
  "risk_level": "medium",
  "trade_quality": 88,
  "breakdown": { "trend_quality", "technical", "smc", "risk", "news", "economic", "total" },
  "risk_reward": 3.15,
  "rejected_reasons": [],
  "warnings": [ "High Impact News in 90 minutes" ],
  "position_guidance": "conservative",
  "calculated_at"
}

`rejected_reasons` collects every triggered hard-reject rule (not just the first, ADR-068) - `approved` is `false` if this list is non-empty, or if `trade_quality` falls below 60 with no hard-reject rule triggered (docs/48 §8's Decision Matrix). `breakdown` is always populated, even when rejected, for explainability. 404 only if the asset symbol is unknown.

Out of scope for Phase 5C: any endpoint that stores/retrieves past evaluations (stateless, no persistence); any position-size-in-lots calculation (`position_guidance` is qualitative only).

---

# Strategy

Phase 5D (docs/49_STRATEGY_ARCHITECTURE.md, ADR-069 through ADR-076). Public (no authentication).

GET /strategy/evaluate/{symbol}?timeframe=H1

Classifies which of seven strategy methodologies fits current market evidence - never a BUY/SELL/trade-level recommendation (ADR-069, extends ADR-031/ADR-043). `{symbol}` is case-insensitive.

Response

{
  "symbol": "EURUSD", "timeframe": "h1",
  "primary_strategy": "trend_following",
  "alternative_strategies": [ { "strategy", "score" } ],
  "rejected_strategies": [ { "strategy", "score", "reason" } ],
  "strategy_score": 94,
  "breakdown": { "market_match", "evidence_quality", "confidence", "risk", "historical_performance", "total" },
  "warnings": [],
  "calculated_at"
}

`breakdown` describes the `primary_strategy` only. A strategy is rejected if its `market_match` is 0 (regime-incompatible) or its total score falls below 50 (docs/49 §8) - `rejected_strategies` always carries an explicit reason. `historical_performance` is currently a uniform placeholder (ADR-075) - no trade-outcomes dataset exists yet. 404 only if the asset symbol is unknown.

Momentum Trading (docs/17 §4) is not available as a result - undefined requirements in docs/17, ADR-072.

Out of scope for Phase 5D: any endpoint returning a trade-level recommendation; AI-generated explanation of the selection (docs/17 §18, Phase 6's job); persistence of evaluations (stateless).

---

# AI Analysis

Phase 6A (docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md, ADR-077 through ADR-084). **Requires authentication** (`get_current_user`, ADR-083) - the first analysis-family routes to do so, given real per-call LLM cost and per-call persistence.

POST /analysis/ai/{symbol}?timeframe=H1

Triggers full orchestration (context build -> deterministic recommendation -> AI narration -> persist), returns the complete result. Not cacheable/idempotent (side effects: cost, a new persisted row) - POST, not GET.

Response

{
  "id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
  "symbol": "EURUSD",
  "timeframe": "h1",
  "recommendation": "buy",
  "confidence_score": 87.0,
  "confidence_level": "high",
  "risk_level": "medium",
  "entry_price": 1.17540,
  "stop_loss": 1.17120,
  "take_profit": 1.18150,
  "execution_guidance": "normal",
  "reasoning": {
    "summary": "...", "technical": "...", "smc": "...", "economic": "...",
    "news": "...", "risk": "...", "conclusion": "..."
  },
  "supporting_evidence": [],
  "conflicting_evidence": [],
  "risks": [],
  "invalidation_conditions": [],
  "model_name": "gpt-4o-mini",
  "prompt_version": "1.0.0",
  "ai_available": true,
  "warnings": [],
  "calculated_at": "2026-08-01T12:00:00Z"
}

`recommendation`/`confidence_score`/`confidence_level`/`risk_level`/`entry_price`/`stop_loss`/`take_profit`/`execution_guidance`/`supporting_evidence`/`conflicting_evidence`/`risks`/`invalidation_conditions` are all deterministic - reused from existing engines or computed by new deterministic modules, never generated by the AI (docs/50 §1/§6). Only `reasoning`'s seven narrative sections are AI-generated. `entry_price`/`stop_loss`/`take_profit`/`risk_level`/`execution_guidance` are `null` when `recommendation` is `"wait"`. If the AI provider call fails after one retry, `ai_available` is `false` and `reasoning` falls back to a deterministic template (never a failed request, docs/50 §9). 404 only if the asset symbol is unknown.

---

GET /analysis/ai/{id}

Return a previously persisted analysis (same response shape as the POST above). 404 if unknown.

---

GET /analysis/history?symbol=&page=&limit=

Paginated list of the authenticated user's past AI analyses, optionally filtered by symbol.

Out of scope for Phase 6A: `POST /analysis/ai/batch` (no demonstrated need yet), any response caching, Signal Engine integration.

---

# Signals

Phase 6B (docs/51_SIGNAL_ARCHITECTURE.md, ADR-085 through ADR-091). `SignalEngine` is a thin wrapper over `AIOrchestratorEngine` (Phase 6A) - no independent evidence weighting, confidence, or recommendation logic (ADR-085). **Requires authentication** (`get_current_user`) on every route - signals derive from auth-gated `ai_analysis` (ADR-083's precedent extended to this whole surface).

POST /signals/generate/{symbol}?timeframe=H1

Not in this document's original draft - added per ADR-089. On-demand generation, mirroring `POST /analysis/ai/{symbol}`'s pattern exactly: calls `AIOrchestratorEngine.generate()` once, and persists a `Signal` row only if the recommendation is BUY or SELL (ADR-086) - WAIT returns `signal: null`, no row is created.

Response

{
  "analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
  "symbol": "EURUSD",
  "timeframe": "h1",
  "recommendation": "buy",
  "signal": {
    "id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
    "analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
    "symbol": "EURUSD",
    "timeframe": "h1",
    "signal_type": "buy",
    "entry_price": 1.17540,
    "stop_loss": 1.17120,
    "take_profit": 1.18150,
    "risk_reward": 1.45,
    "confidence": 87.0,
    "status": "active",
    "triggered_at": null,
    "closed_at": null,
    "profit_loss": null,
    "created_at": "2026-08-02T12:00:00Z"
  }
}

`entry_price`/`stop_loss`/`take_profit`/`confidence` are reused verbatim from the underlying `AIAnalysisResult` (ADR-085) - `risk_reward` is computed by reusing `risk_reward_validator.validate()` (docs/48 §6, Phase 5C), not re-derived. `take_profit` is a single value, not TP1/TP2/TP3 - docs/11 §11's three-level output has no defined splitting formula anywhere and is deliberately deferred (ADR-087). 404 only if the asset symbol is unknown.

---

GET /signals?symbol=&status=&page=&limit=

Latest signals, paginated and optionally filtered by asset symbol and/or `status`. `status` reflects a read-time-computed value (`active`/`expired`) for stored `ACTIVE` rows (ADR-088) - never a stale stored value.

Response: same item shape as `POST /signals/generate/{symbol}`'s `signal` object, wrapped in `{"items", "page", "limit", "total"}`.

---

GET /signals/{id}

Signal details (same shape as one list item). 404 if the id is unknown.

---

POST /signals/bookmark

Bookmark a signal for the current user.

Request

{ "signal_id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b" }

Response

{ "id": "...", "signal_id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b", "created_at": "2026-08-02T12:00:00Z" }

404 if the signal id is unknown. 409 if this user has already bookmarked this signal (ADR-090's `(user_id, signal_id)` uniqueness constraint).

---

DELETE /signals/bookmark/{id}

204 No Content. 404 if the bookmark id is unknown or does not belong to the current user.

Out of scope for Phase 6B: autonomous trading or broker execution; live price-monitoring/auto status transitions beyond read-time-computed EXPIRED (Triggered/Closed/Successful/Stopped Out, `profit_loss` population - ADR-088); TP1/TP2/TP3 (ADR-087); a Cancelled status (no admin/user action endpoint specified); Celery Beat scheduled/proactive generation (ADR-089's rejected alternative); `/ws/signals`; Telegram/Dashboard notification (Phase 7).

---

# AI Chat

Phase 6C (docs/52_AI_CHAT_ARCHITECTURE.md, ADR-092 through ADR-098). `AIChatEngine` is a thin conversational/persistence layer over Phase 4-6B - it computes no new recommendation, confidence, or evidence of its own (ADR-093/094). **Requires authentication** on every route - conversations are private per-user data, and generating a reply calls the same metered LLM provider as Phase 6A (ADR-083's cost rationale extended here).

POST /chat/conversations

Create a conversation, optionally seeded with a starting `symbol`/`timeframe` (both optional).

Request

{ "symbol": "EURUSD", "timeframe": "h1" }

Response

{
  "id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
  "title": null,
  "current_symbol": "EURUSD",
  "current_timeframe": "h1",
  "status": "active",
  "created_at": "2026-08-02T12:00:00Z",
  "updated_at": "2026-08-02T12:00:00Z"
}

---

GET /chat/conversations?status=&page=&limit=

The current user's conversations, paginated. `status` defaults to `active` (excludes archived conversations, ADR-097).

Response: `{ "items": [...same shape as above...], "page", "limit", "total" }`

---

GET /chat/conversations/{id}

Conversation detail, including its full message transcript (chronological, oldest first). 404 if unknown or not owned by the current user.

---

POST /chat/conversations/{id}/messages

Send a message; returns the assistant's reply. `symbol`/`timeframe` are optional - omitted, the conversation's current values (`current_symbol`/`current_timeframe`) are used; if neither is ever set, the question is treated as general/educational, with no market grounding (ADR-095). Symbols are **client-supplied, never parsed from free text** - no NLP entity-extraction component exists in this project (ADR-095).

Request

{ "content": "Why is this a BUY?", "symbol": "EURUSD", "timeframe": "h1" }

Response

{
  "conversation": { "...same shape as POST /chat/conversations..." },
  "user_message": { "id": "...", "role": "user", "content": "Why is this a BUY?", "symbol": "EURUSD", "timeframe": "h1" },
  "assistant_message": {
    "id": "...", "role": "assistant",
    "content": "The current recommendation is BUY because...",
    "symbol": "EURUSD", "timeframe": "h1",
    "ai_analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
    "signal_id": null,
    "model_name": "gpt-4o-mini"
  },
  "warnings": []
}

`ai_analysis_id`/`signal_id` are populated only when the reply grounded itself in a persisted `ai_analysis`/`signals` row (ADR-094) - the assistant never computes a new recommendation itself; if no persisted row exists yet for the resolved asset/timeframe, it states that explicitly rather than guessing. 404 if the resolved symbol is unknown, or if the conversation id is unknown/not owned by the current user.

---

POST /chat/conversations/{id}/archive

Soft-archive (`status=archived`) - excluded from `GET /chat/conversations`' default listing, still retrievable by id (ADR-097).

---

DELETE /chat/conversations/{id}

204 No Content. Hard delete, cascading every message (ADR-097) - distinct from archive; conversations are private user data a user may genuinely remove.

Out of scope for Phase 6C: NLP symbol extraction from free text; multi-asset comparison ("Compare Gold and Silver"); feedback rating (`Helpful`/`Not Helpful`/`Report Issue`, docs/22 §15); "Question Type"/"Engines Used" classification logging (docs/22 §14, ADR-098); voice/chart-screenshot/PDF/multi-language/portfolio features (docs/22 §18); response caching; real rate-limiting/quota infrastructure beyond authentication.

---

# Watchlists

GET /watchlists

GET /watchlists/{id}

Single watchlist with resolved asset rows (ADR-128, inferred addition
for the 7D-B detail view - not in the original literal spec).

POST /watchlists

PUT /watchlists/{id}

DELETE /watchlists/{id}

---

POST /watchlists/{id}/assets

Add asset.

---

DELETE /watchlists/{id}/assets/{asset}

Remove asset.

---

# Notifications

GET /notifications

PUT /notifications/read

DELETE /notifications

---

# Telegram

POST /telegram/connect

POST /telegram/disconnect

GET /telegram/status

---

# Subscription

GET /plans

GET /subscription

POST /subscription/checkout

POST /subscription/cancel

GET /subscription/history

---

# Admin

GET /admin/users

GET /admin/signals

Query params: `symbol`, `status`, `page`, `limit` - identical to `GET
/signals`. Same `{"items","page","limit","total"}` envelope, same
`SignalResponse` item shape. Contract is inferred (ADR-130). Scope note:
`signals` has no `user_id` column, so this returns the same globally-scoped
rows the public `GET /signals` already does - "admin view" means a
consistent `/admin/*` dashboard entry point, not additional visibility.

GET /admin/system

Response: `{"database": "ok"|"down", "redis": "ok"|"down", "signals_today":
int, "ai_analyses_today": int}`. Reuses `/health/ready`'s exact DB/Redis
checks plus simple `COUNT` queries for today's activity - not telemetry
(ADR-116). Always `200`; a dependency being unreachable renders as `"down"`
in the body, never a `500`. Contract is inferred (ADR-130).

GET /admin/logs

Query params: `user_id`, `action`, `resource`, `from`, `to`, `page`, `limit`
(all optional, combinable). Newest first. Response items include a
server-resolved `actor_email`/`actor_username` (both `null` when `user_id`
is `null` - no actor, e.g. a failed login or a since-deleted user). Contract
is inferred (ADR-129) - this project's audit-log write side (Phase 2B/8C)
predates this read endpoint. Read-only: no route mutates or deletes a row.

GET /admin/analytics

Response: `{"daily_active_users": int, "signal_type_distribution":
{"buy": int, "sell": int}}`. `daily_active_users` is distinct
`UserSession.user_id` with a session created today. `signal_type_distribution`
groups on `Signal.signal_type` (`signals` has no `recommendation` column -
see ADR-130 for why this is the intended reading of docs/58 §3.2's
"recommendation distribution" phrasing). Contract is inferred (ADR-130).

POST /admin/news

No request body. Runs the existing `NewsIngestionPipeline` inline (the same
pipeline the `news_sentiment.ingest` Celery task uses) and returns
`{"articles_ingested": int}`. Writes an `AuditLog` row
(`admin_news_refreshed`). Blocking - see ADR-130 for the accepted
synchronous-ingestion tradeoff. Contract is inferred (ADR-130).

POST /admin/maintenance

Body: `{"action": "refresh_news" | "refresh_calendar"}` - any other value is
rejected with `422` (Pydantic `Literal`, ADR-117). `refresh_news` shares
`POST /admin/news`'s exact implementation and response shape
(`{"action": "refresh_news", "news": {"articles_ingested": int}, "calendar":
null}`). `refresh_calendar` runs the existing
`EconomicCalendarIngestionPipeline` inline and returns `{"action":
"refresh_calendar", "news": null, "calendar": {"events_created": int,
"events_updated": int}}`. Both write an `AuditLog` row. Contract is inferred
(ADR-130).

---

# Health

GET /health

Response

{
    "status":"healthy"
}

---

# Metrics

GET /metrics

Prometheus text-format exposition (Phase 9D, ADR-136) - request
count/latency labeled by route template plus the client library's
default process/GC collectors. Not part of the standard `{"success"/
"error"}` response envelope - this returns Prometheus's own
`text/plain; version=0.0.4` format, the same way `GET /health` returns
a bare liveness object rather than the standard envelope.

Auth: `Authorization: Bearer <METRICS_AUTH_TOKEN>`. Fail-closed - if
`METRICS_AUTH_TOKEN` is unset (the default) or the token is missing or
wrong, this returns `404`, not `401`/`403`, so an unconfigured
deployment does not advertise the route's existence. Never rate
limited (matches `GET /health*`) and never counted in its own metrics.

Response (200, token valid)

```
# HELP http_requests_total Total HTTP requests received, labeled by method/route template/status.
# TYPE http_requests_total counter
http_requests_total{method="GET",route="/health",status="200"} 42.0
...
```

Response (404, token unset/missing/wrong)

```json
{"error": "resource_not_found", "message": "Not Found"}
```

---

# WebSocket

/ws/prices

Live market prices.

/ws/signals

Live signals.

/ws/news

Breaking news.

/ws/notifications

User notifications.

---

# HTTP Status Codes

200 OK

201 Created

204 No Content

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

429 Too Many Requests

500 Internal Server Error

503 Service Unavailable

---

# API Versioning

Current

/api/v1

Future

/api/v2

---

# Rate Limits

Guest

60 requests/minute

Free

120 requests/minute

Premium

600 requests/minute

Admin

Unlimited

---

# Pagination

?page=1

&limit=20

---

# Filtering

?market=forex

?timeframe=H1

?recommendation=BUY

?confidence>80

---

# Sorting

?sort=created_at

?order=desc