# Changelog

## Unreleased

### Added - Phase 7A: Frontend Foundation (Authentication & User Experience)

`docs/53_FRONTEND_FOUNDATION_ARCHITECTURE.md` - new architecture document defining the reuse map, client-side auth token storage model, route protection, and shell/theme/shared-UI foundation every future frontend page builds on

Core boundary (ADR-099): auth is entirely client-side - access token in memory (zustand `store/auth-store.ts`), refresh token in `localStorage` (`lib/auth/token-storage.ts`). No backend changes anywhere in this phase; the backend's existing Bearer-only design (docs/37 §10) is reused exactly as-is, not modified

`services/auth.ts` (thin wrappers for the five existing `/auth/*` endpoints, mirrors `services/analysis.ts`'s shape) and `services/api-client.ts` extended with `apiPost`/`apiDelete`, automatic `Authorization: Bearer` header injection, and a one-shot silent refresh-and-retry on a `401` (mirrors ADR-081's "one retry, then fail gracefully" precedent) - the pre-existing `apiGet`/`ApiError` used by every Phase 6 dev-dashboard page is untouched

`providers/auth-provider.tsx` (session restore on mount, mirrors `providers/query-provider.tsx`'s shape) and `hooks/use-auth.ts` (the single entry point components use for login/register/logout, mirrors `hooks/use-assets.ts`'s thin-wrapper-over-a-service pattern)

`components/layout/auth-guard.tsx` / `guest-guard.tsx` - eliminate the flash of protected content or a premature redirect during session restoration (render a loading state until auth status resolves, per this phase's explicit LoadingGate/AuthGuard requirement); `AuthGuard` preserves the attempted path as `?next=` for post-login redirect

Auth pages (`app/(auth)/{login,register,forgot-password}`, `features/auth/components/*`): `LoginForm`/`RegisterForm` built with `react-hook-form` + `zod` (`lib/validation/auth.ts`, mirrors the backend's password policy as a UX convenience only - the backend remains the source of truth). `/forgot-password` is an informational stub only, `/reset-password` is not built at all (ADR-100) - neither backend endpoint exists yet (blocked on email infrastructure, tracked since Phase 2C)

The existing Phase 6 dev dashboard shell evolved in place into the authenticated product shell (ADR-101) - `app/dashboard/*` relocated to `app/(protected)/dashboard/*` (same URLs, zero breaking changes) behind `AuthGuard`; `components/layout/{app-shell,sidebar,top-nav,user-menu}.tsx` replace the old "ClaudeTrading Dev" sidebar with the real shell (responsive: persistent sidebar on desktop, `Sheet`-based drawer on mobile). Sidebar nav is deliberately narrower than docs/05 §7's full product IA - only items with a real destination are listed (Overview, Technical Analysis, Smart Money Concepts, Market Regime, API Explorer), mirroring this project's backend precedent of never exposing a route before the logic behind it exists

Dark/light/system theming (`next-themes`, `providers/theme-provider.tsx`, `components/shared/theme-toggle.tsx`) - `globals.css` gained a `.dark` block; both palettes aligned to docs/05 §4's actual hex values (closing the gap tracked in BACKLOG.md §1), default theme is dark (docs/05 §3)

Shared UI: `components/shared/{empty-state,error-page}.tsx`, `app/not-found.tsx`, `app/error.tsx`; `lib/toast.ts` wrapping `sonner` (single seam, mirrors `api-client.ts` wrapping `fetch`), `<Toaster />` mounted once in the root layout

Full docs/05 §2 frontend stack adopted (ADR-102): zustand, next-themes, react-hook-form, zod, @hookform/resolvers, framer-motion, sonner, plus shadcn/Radix primitives (`dialog`, `dropdown-menu`, `avatar`, `label`, `input`, `form`, `separator`, `sheet`) and `tailwindcss-animate` (the standard utility-class partner for their `data-[state=...]` animations)

**ADR-099** through **ADR-102**: client-side token storage (no BFF/cookies); forgot-password stub + reset-password fully deferred; the existing dev shell evolves into the product shell rather than a parallel one; full docs/05 §2 stack adopted now rather than minimized

Deliberately excluded (per Phase 7A approval): `/reset-password`; email-verification pages; Markets/Signals/News/Watchlists/AI Analysis page content (future phases - this is the shell they'll use); a BFF/httpOnly-cookie auth layer; session/device-management UI (backend has the service logic but no API route yet); role-gated Admin nav (no `/admin` page exists yet either); bottom mobile navigation (no page-specific nav to warrant one yet); a frontend automated test suite; any backend changes or new API endpoints

Verified via `npm run typecheck`/`lint`/`build` (all clean, 10 routes building successfully) plus a manual browser-driven round-trip against the real running backend: register → login → session persistence across a full page reload → protected-route redirect with `?next=` preserved → theme toggle (dark/light) → `UserMenu` (profile info + logout) → logout clearing the refresh token → re-visiting a protected route correctly redirecting to `/login` again. No frontend test framework exists yet (BACKLOG.md §23), consistent with this project's practice of not introducing test infrastructure speculatively

docs/30 updated: introduces Phase 7 sub-phase lettering for the first time (7A complete, 7B+ not started)

### Added - Phase 6C: AI Chat Assistant

`docs/52_AI_CHAT_ARCHITECTURE.md` - new architecture document defining `AIChatEngine` as a thin conversational layer over Phase 4-6B, the provider extension, two-level symbol/timeframe scoping, and the persistence model

Core boundary (ADR-093/094): `AIChatEngine` computes **zero new evidence, confidence, or recommendation logic**. Grounding reuses `ContextBuilder` (Phase 6A) verbatim for Technical Analysis/SMC/Market Regime/Analysis Confidence/News Sentiment/Economic Calendar/Strategy Engine/Risk Management; "why is this a BUY"/"explain this signal" questions are answered by looking up the most recent persisted `ai_analysis`/`signals` row (Phase 6A/6B), never by triggering a fresh recommendation computation

`AIProvider` extended (`app/services/ai_orchestrator/providers/base.py`) with `generate_chat_reply()` (ADR-092) - a second capability of the *same* `OpenAIProvider`/`MockAIProvider`, sharing the exact `httpx.Client` construction and status-code-to-exception classification `generate()` already uses (factored into a shared `_post_chat_completion` helper); `generate()` (Phase 6A) is completely unaffected, purely additive

`app/services/ai_chat/chat_prompt_builder.py` - a sibling to `ai_orchestrator/prompt_builder.py`, following its exact conventions (versioned constant `CHAT_PROMPT_VERSION`, explicit guardrail system prompt, deterministic fact-line serialization); `app/services/ai_chat_engine.py` (`AIChatEngine`) - composes `ContextBuilder`, `AIProvider`, `AssetRepository`, `AIAnalysisRepository`, `SignalRepository`, `MessageRepository`; one retry on transient provider failure then a deterministic apology fallback (mirrors ADR-081's precedent), never a hard failure

Two-level symbol/timeframe scoping (ADR-095): `conversations.current_symbol`/`.current_timeframe` (mutable "current focus," docs/22 §10) vs. `messages.symbol`/`.timeframe` (immutable per-turn record). Client-supplied only, never NLP-parsed from free text - no entity-recognition component exists anywhere in this project

`conversations`/`messages` tables (`app/models/conversation.py`, `message.py`; migration `72e726c08dd8_create_conversations_and_messages_tables.py`) - `conversations` uses `TimestampMixin` (`title`/`current_symbol`/`status` all mutate), `messages` uses `CreatedAtMixin` (append-only); `messages.ai_analysis_id`/`.signal_id` use `ON DELETE SET NULL` (not `CASCADE`) - a message outlives the row it once referenced

`AIAnalysisRepository`/`SignalRepository` gained an additive optional `timeframe` filter parameter on `find_paginated`/`count_filtered` (every existing caller unaffected) - used for AI Chat's "latest analysis/signal for this asset/timeframe" grounding lookup

New authenticated endpoints (same LLM-cost rationale as ADR-083): `POST /chat/conversations` (create), `GET /chat/conversations` (list, paginated), `GET /chat/conversations/{id}` (detail + transcript), `POST /chat/conversations/{id}/messages` (send, get reply), `POST /chat/conversations/{id}/archive` (soft), `DELETE /chat/conversations/{id}` (hard, cascades messages) - both archive and hard delete are supported (ADR-097), answering different real needs

**ADR-092** through **ADR-098**: `AIProvider` extended with `generate_chat_reply()` rather than a second OpenAI client; `ContextBuilder` reuse for all eight-engine grounding; never recomputing a recommendation, only explaining persisted `ai_analysis`/`signals` rows; two-level client-supplied symbol/timeframe scoping; `conversations`/`messages` inferred schema; both archive and hard delete supported; feedback rating/question-type/engines-used logging explicitly deferred

Deliberately excluded (per Phase 6C approval): NLP symbol extraction from free text; multi-asset comparison; feedback rating (docs/22 §15); "Question Type"/"Engines Used" classification logging (docs/22 §14); voice/chart-screenshot/PDF/multi-language/portfolio features (docs/22 §18); response caching; real rate-limiting/quota infrastructure beyond authentication

Tests: `test_ai_chat_prompt_builder.py`, `test_ai_chat_engine.py` (fake `ContextBuilder`, `MockAIProvider` - mirrors `test_signal_engine.py`'s thin-wrapper-testing precedent), `test_conversation_models.py` (cascade delete, `SET NULL` behavior), `test_ai_chat_routes.py`, plus new `generate_chat_reply()` coverage added to `test_ai_openai_provider.py`

docs/03, docs/04, docs/30 updated: `docs/03` adds a new §11A for `conversations`/`messages`; `docs/04` adds the full `/chat/*` API contract (previously not drafted at all, unlike Signals' Phase 6A placeholder); `docs/30` marks Phase 6C - and all of Phase 6 - complete

### Status

Phase 6 (AI Orchestrator/AI Reasoning Engine, Signal Engine, AI Chat Assistant) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 6B: Signal Engine

`docs/51_SIGNAL_ARCHITECTURE.md` - new architecture document defining `SignalEngine` as a thin wrapper over `AIOrchestratorEngine` (ADR-085), the persistence model, the two-state status scope, and the reuse map

Core boundary (ADR-085): `SignalEngine` introduces **zero new evidence weighting, confidence, or recommendation logic**. `docs/11_SIGNAL_ENGINE.md`'s original independent-pipeline vision (its own Technical 35%/SMC 30%/Economic 15%/News 10%/Risk 10% weight distribution, its own confidence score, its own conflict resolution) is documented as superseded by Phase 6A's already-implemented `AnalysisConfidenceEngine`/`AIOrchestratorEngine` decision tree - rebuilding it would duplicate Phase 6A

`SignalEngine` (`app/services/signal_engine.py`) - calls `AIOrchestratorEngine.generate()` exactly once; persists a `Signal` row only for a BUY/SELL outcome (ADR-086, WAIT produces no row, the full reasoning trail stays available via `analysis_id`); reuses `risk_management.risk_reward_validator.validate()` (Phase 5C) for `risk_reward`, never re-deriving the formula

`app/services/signal/status_resolver.py` - deterministic, read-time-only `effective_status()` (ADR-088): `ACTIVE` is the only status Phase 6B ever writes; `EXPIRED` is computed at read time from `settings.signal_ttl_hours` (default 24), mirroring `economic_calendar/risk_window.py`'s "never store a value that's a function of continuously-advancing wall-clock time" precedent. The remaining six `docs/11 §18` states (Draft/Triggered/Cancelled/Closed/Successful/Stopped Out) are reserved enum values, unreachable through any 6B code path - live price-monitoring/trigger-detection needed to reach them doesn't exist anywhere in this project

`signals` table (`app/models/signal.py`, `CreatedAtMixin`, ADR-091) and `signal_bookmarks` table (`app/models/signal_bookmark.py`, inferred join table not in docs/03's original schema, `(user_id, signal_id)` uniqueness, ADR-090, mirrors `OAuthAccount`'s ADR-022 precedent)

New authenticated endpoints (mirrors ADR-083's whole-surface auth precedent): `POST /signals/generate/{symbol}?timeframe=` (ADR-089, on-demand generation - added beyond docs/04's original Phase 6A draft, which implied scheduled/proactive generation; rejected in favor of the already-established on-demand pattern to avoid committing to an unattended LLM-spend schedule without an explicit budget decision), `GET /signals` (paginated, filterable by symbol/status), `GET /signals/{id}`, `POST /signals/bookmark`, `DELETE /signals/bookmark/{id}`

**ADR-085** through **ADR-091**: thin-wrapper design over AI Orchestrator; a signal is a persisted BUY/SELL call only, WAIT produces none; single take-profit reused from AI Orchestrator, TP1/TP2/TP3 splitting deferred (no sourced formula); two-state status scope (ACTIVE written, EXPIRED read-time-computed), remaining docs/11 §18 states reserved; on-demand generation endpoint chosen over scheduled Celery Beat generation; `signal_bookmarks` inferred join table; `CreatedAtMixin` choice for `signals`

Deliberately excluded (per Phase 6B approval): autonomous trading or broker execution; live price-monitoring/auto status transitions beyond read-time EXPIRED (Triggered/Closed/Successful/Stopped Out, `profit_loss` population); TP1/TP2/TP3; a Cancelled status (no admin/user action endpoint specified); Celery Beat scheduled/proactive generation; `/ws/signals`; Telegram/Dashboard notification (Phase 7, downstream services don't exist)

Tests: `test_signal_status_resolver.py` (TTL boundary, non-ACTIVE pass-through, naive-datetime handling), `test_signal_engine.py` (BUY/SELL persistence, WAIT produces no row, `AIOrchestratorEngine.generate()` called exactly once, using a fake engine rather than the full upstream stack since `SignalEngine` is a thin wrapper), `test_signal_models.py` (FK cascade behavior, `(user_id, signal_id)` uniqueness), `test_signal_routes.py` (auth required, 404s, list filtering/pagination, bookmark create/delete/409-on-duplicate, WAIT generation response shape)

docs/03, docs/04, docs/30 updated: `docs/03` §11 documents the built `signals`/`signal_bookmarks` schema (superseding the "out of scope for Phase 6A" placeholder); `docs/04` documents the full `/signals/*` API contract (superseding the Phase 6A placeholder that presumed scheduled generation); `docs/30` marks Phase 6B complete

### Added - Phase 6A: AI Orchestrator / AI Reasoning Engine

`docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md` - new architecture document defining the deterministic/AI boundary, the `AnalysisContext` data flow, the reuse map across five Phase 4/5 engines, the four new deterministic modules, prompt architecture, provider abstraction, and structured-output recovery ladder

Core boundary (ADR-078/079): the LLM never computes `recommendation`, `confidence`, `risk_level`, `entry_price`/`stop_loss`/`take_profit`, or `execution_guidance` - every one of those fields is either reused verbatim from an existing Phase 4/5 engine or produced by a new deterministic module. The LLM's only output is `reasoning`'s seven-section narrative prose, and even a total LLM failure never blocks the response - it only degrades `reasoning` to a deterministic template and sets `ai_available=False`

`app/services/ai_orchestrator/` - `candidate_setup_builder.py` (ADR-080, resolves the Risk-Management-needs-a-setup chicken-and-egg problem the same way Strategy Engine's ADR-071 did), `recommendation_decision.py` (ADR-078, the core BUY/SELL/WAIT decision tree), `invalidation_builder.py`, `evidence_extractor.py`, `prompt_builder.py`, `response_parser.py`, `summary_fallback.py`, `providers/` (`base.py` Protocol, `openai_provider.py`, `mock.py` test-only)

`AIOrchestratorEngine` (`app/services/ai_orchestrator_engine.py`) - composes `AnalysisConfidenceEngine`, `NewsSentimentEngine`, `EconomicCalendarEngine`, `StrategyEngine`, `RiskManagementEngine` via `ContextBuilder`; one retry on transient provider failure then graceful template fallback (ADR-081), never a hard failure

`ai_analysis` table (`app/models/ai_analysis.py`, `CreatedAtMixin`, append-only) - the first engine output this project persists for genuine non-reproducibility rather than convenience (ADR-082), since an LLM call is not perfectly reproducible the way every Phase 4/5 deterministic engine is

New authenticated endpoints (ADR-083, the first analysis-family routes requiring auth, given real per-call LLM cost): `POST /analysis/ai/{symbol}?timeframe=` (generates and persists one analysis), `GET /analysis/ai/{id}` (retrieve by id), `GET /analysis/history?symbol=&page=&limit=` (paginated history)

**ADR-077** through **ADR-084**: single `AIOrchestratorEngine` class resolving the "AI Orchestrator" vs "AI Reasoning Engine" naming ambiguity; deterministic recommendation computation; confidence/risk/execution-guidance reuse; candidate setup builder; provider abstraction with structured-output enforcement and retry/fallback; `ai_analysis` persistence; authentication requirement; Phase 6 sub-phase scope boundary (Signal Engine 6B and AI Chat Assistant 6C explicitly deferred)

Deliberately excluded (per Phase 6A approval): Signal Engine (6B); AI Chat Assistant (6C); `signals` table; `POST /analysis/ai/batch`; response caching; real rate-limiting/quota infrastructure; Confidence Engine weight-rebalancing to include News/Economic/Risk (ADR-047's boundary respected, untouched); Anthropic/Gemini/local providers (abstraction supports them, none implemented yet)

Tests: one file per deterministic module (`test_ai_candidate_setup_builder.py`, `test_ai_recommendation_decision.py`, `test_ai_invalidation_builder.py`, `test_ai_evidence_extractor.py`), `test_ai_prompt_builder.py`, `test_ai_response_parser.py`, `test_ai_openai_provider.py` (mirrors `test_news_ai_summary_generator.py`'s `httpx.MockTransport` pattern, never a real API call), `test_ai_orchestrator_engine.py` (integration against real upstream engines on a seeded SQLite session), `test_ai_analysis_routes.py` (auth required, 404s, persisted-row shape, pagination)

docs/03, docs/04, docs/07, docs/13, docs/35, docs/30 updated: resolved `ai_analysis`'s field list and mixin contradiction; added the `/analysis/ai/*` and `/analysis/history` API contracts; bumped docs/07/docs/13/docs/35 to v1.1 pointing at docs/50; introduced Phase 6 sub-phase lettering for the first time (6A complete, 6B/6C not started)

### Added - Phase 5D: Strategy Engine

`docs/49_STRATEGY_ARCHITECTURE.md` - new architecture document defining the reuse-first evidence map, the buildable seven-strategy set, Market Match/Evidence Quality/Historical Performance rule tables, and rejection/ranking rules

`app/services/strategy/` - `market_match.py`, `historical_performance.py`, `strategy_scorer.py`, `ranking.py`, plus seven deterministic per-strategy requirements checklists (`requirements/trend_following.py`, `smc.py`, `breakout.py`, `pullback.py`, `mean_reversion.py`, `scalping.py`, `swing_trading.py`) - fully deterministic, zero AI/GPT, no trade recommendations

`StrategyEngine` (`app/services/strategy_engine.py`) - the strongest reuse-first design in this project yet: `AnalysisConfidenceEngine` is the primary dependency (transitively yields Technical Analysis/SMC/Market Regime evidence in one call, ADR-071), and `app.services.risk_management`'s `session_classifier`/`liquidity_filter`/`economic_filter` sub-modules are reused directly rather than calling `RiskManagementEngine.evaluate()` (which needs a candidate trade setup this engine doesn't have, ADR-062/ADR-071)

Resolves a documentation ambiguity in ADR-043's Future Review note (ADR-069): the Strategy Engine (Phase 5D), not the Signal Engine (Phase 6), is the consumer of strategy-compatibility classification ADR-043 anticipated - `MarketRegimeEngine` itself remains unchanged, ADR-043 stands exactly as written

Resolves three internal inconsistencies in docs/17_STRATEGY_ENGINE.md (ADR-072): "Range Trading"/"Mean Reversion" (never separately defined) merged into one `MEAN_REVERSION` strategy; "Momentum Trading" (zero requirements defined anywhere) deferred rather than invented; SMC strategy's undefined "Institutional Trend" best-market resolved to the four `MarketRegimeState` values most consistent with SMC's own vocabulary

Fully stateless (ADR-070) - no new table, mirrors Risk Management's ADR-063 precedent; Historical Performance (10 of 100 points) is a uniform neutral placeholder (ADR-075) - no trade-outcomes dataset exists anywhere in this project, mirrors the Confidence Engine's docs/15 v1.0 §10 deferred-calibration precedent

New public (no auth) endpoint: `GET /strategy/evaluate/{symbol}?timeframe=` - classifies strategy-methodology compatibility only, never a BUY/SELL/trade-level recommendation (ADR-069, extends ADR-031/ADR-043)

**ADR-069** through **ADR-076**: ADR-043 clarification; statelessness; reuse-first dependency design; buildable strategy set; Market Match regime-compatibility gate with timeframe partial credit; Evidence Quality deterministic per-strategy checklists (ungateable requirements like Spread/RR excluded from the denominator, never fabricated); Historical Performance placeholder; rejection/ranking rules (Market-Match-zero OR sub-50-total rejection, deterministic tie-break)

Deliberately excluded (per Phase 5D approval): Momentum Trading (undefined requirements); User Custom/AI Generated strategies; persistence of evaluations; any trade-level recommendation; AI-generated explanation of strategy selection (Phase 6's job); a true multi-timeframe scan for Swing Trading's "Higher Timeframe Trend"; Confidence Engine integration in the reverse direction; real historical/backtest-based strategy performance

Tests: one file per module (`test_strategy_market_match.py`, `test_strategy_historical_performance.py`, `test_strategy_requirements_*.py` × 7, `test_strategy_scorer.py`, `test_strategy_ranking.py`), `test_strategy_engine.py` (integration against real upstream engines on a seeded SQLite session), `test_strategy_routes.py`

docs/03, docs/04, docs/17, docs/30 updated: noted Strategy Engine's evidence flows into future `ai_analysis`; added the `/strategy/evaluate/{symbol}` API contract; resolved docs/17's strategy-list inconsistencies and "Institutional Trend" gap inline; marked Phase 5D (and all of Phase 5) complete

### Added - Phase 5C: Risk Management Engine

`docs/48_RISK_MANAGEMENT_ARCHITECTURE.md` - new architecture document defining the reuse-first dependency design, session/spread/liquidity/correlation rule tables, R:R and stop-loss validation, the Trade Quality Score, and hard-reject decision precedence

`app/services/risk_management/` - nine deterministic modules (`session_classifier`, `spread_filter`, `liquidity_filter`, `correlation_analyzer`, `economic_filter`, `risk_reward_validator`, `stop_loss_validator`, `news_scorer`, `trade_quality_aggregator`) plus `decision` - fully deterministic, zero AI/GPT usage, no trade recommendations, matching the user's explicit constraint for this phase

`RiskManagementEngine` (`app/services/risk_management_engine.py`) - reuse-first (ADR-064): `AnalysisConfidenceEngine` is the primary dependency, transitively yielding Technical Analysis/SMC/Market Regime evidence in one call (reusing ADR-049's pre-computation chaining); `MarketRegimeResult.volatility.state` is reused directly for the Volatility Filter (an exact match for docs/12 §6's scale, already built in Phase 4C) and `TechnicalAnalysisResult.strength` for Trend Quality - no new classification scale invented. `NewsSentimentEngine` and `EconomicCalendarEngine` (Phase 5A/5B) are called directly - the first engine in this project to depend on a Phase 5 peer rather than deferring it

Evaluates a caller-supplied candidate trade setup (ADR-062) - not a persisted Signal, since no Signal Engine exists yet; the same category of scope-narrowing ADR-047 already applied to the Confidence Engine

Fully stateless (ADR-063) - no new table; `docs/03`'s `risk_level`/`risk_reward` fields already show this evidence's eventual home is the future `ai_analysis`/`signals` tables (Phase 6/7), not a table of its own

New public (no auth) endpoint: `POST /risk/evaluate` - the first POST-based endpoint in this engine family, since a candidate setup (direction/entry/stop/target) is inherently a request body; `spread` is optional and never fabricated (ADR-065, no spread data source exists anywhere in this project)

**ADR-062** through **ADR-068**: caller-supplied-setup scope; statelessness; reuse-first dependency design; spread as optional never-fabricated input; liquidity via relative-volume proxy with session-based Market Close approximation; correlation via real Pearson correlation for a fixed curated pair list, advisory-only; hard-reject rule precedence (all triggered reasons collected, not first-match) ahead of the score-tier Decision Matrix, honoring the project's pre-existing ADR-014 veto-authority decision

Deliberately excluded (per Phase 5C approval): persistence of evaluations; position-size-in-lots calculation (guidance only); Signal Engine/AI Orchestrator integration; Confidence Engine integration in the reverse direction (ADR-047's boundary respected); true liquidity/order-book data; true holiday-calendar detection (weekend-based approximation only); portfolio/daily/weekly exposure limits; a general market-wide correlation model

Tests: one file per deterministic module (`test_risk_session_classifier.py`, `test_risk_spread_filter.py`, `test_risk_liquidity_filter.py`, `test_risk_correlation_analyzer.py`, `test_risk_economic_filter.py`, `test_risk_reward_validator.py`, `test_risk_stop_loss_validator.py`, `test_risk_news_scorer.py`, `test_risk_trade_quality_aggregator.py`, `test_risk_decision.py`), `test_risk_management_engine.py` (integration against real upstream engines on a seeded SQLite session), `test_risk_management_routes.py`

docs/03, docs/04, docs/12, docs/30 updated: noted Risk Management's evidence flows into future `ai_analysis`/`signals` tables; added the `/risk/evaluate` API contract; resolved docs/12's "Signal" premise conflict and documented spread as an optional input; marked Phase 5C complete

### Added - Phase 5B: Economic Calendar Engine

`docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md` - new architecture document defining the upsert-based ingestion path, the read path, the category/importance/market-bias rule tables, and the read-time-only risk window computation

`docs/14_ECONOMIC_CALENDAR_ENGINE.md` bumped to v1.1 - clarified `risk_window` is computed at read time and never stored, and that §11's "Risk Rules" (confidence reduction, WAIT recommendations) belong to a future Risk Engine, not this engine

`app/services/economic_calendar/` - five deterministic modules (`category_classifier`, `importance_scorer`, `surprise_calculator`, `bias_analyzer`, `risk_window`) - fully deterministic, no AI/GPT anywhere in this engine, consistent with the user's explicit constraint for this phase

`EconomicCalendarEngine` (`app/services/economic_calendar_engine.py`, read path) and `EconomicCalendarIngestionPipeline` (`app/services/economic_calendar_ingestion_pipeline.py`, Celery-scheduled write path) - ingestion is **upsert-by-natural-key** (ADR-058), not News's insert-skip-on-duplicate, since the same event is re-fetched repeatedly as it moves SCHEDULED → RELEASED → (rarely) REVISED

`app/services/economic_calendar/providers/` - `EconomicCalendarProvider` Protocol with `fetch_events(start, end)` (not News's `fetch_latest(since)` - ADR-056, since economic events are scheduled ahead of time), `MockEconomicCalendarProvider` (deterministic, seeded, spans past+future); no real vendor in this phase (TradingEconomics deferred to a follow-up sub-phase)

New persisted table `economic_events` (`app/models/economic_event.py`; migration `1e4e1b3c8c7c_create_economic_events_table.py`) - single mutable table (`TimestampMixin`), no separate sources table (ADR-057, `source` is a plain column); unique natural-key index on `(country, currency, event_name, release_time)` plus `(currency, release_time)`/`(importance, release_time)` composite indexes

**ADR-056** through **ADR-061**: provider abstraction shape divergence from News; single-table persistence with no sources table; upsert-by-natural-key ingestion; deterministic category/importance rule tables (no source-tier axis, unlike News); deterministic market-bias rule table generalizing docs/14 §7's CPI example across all 7 categories, "potentially" language only; risk window as a read-time-computed property, never persisted

New public (no auth) endpoints: `GET /calendar` (filters: country/currency/importance/category/from/to/range), `GET /calendar/{id}`, `GET /calendar/upcoming` - `/calendar/today`, `/calendar/week`, `/calendar/high-impact`, `/calendar/currency/{currency}` deliberately not built as separate routes (`GET /calendar`'s filters absorb them)

Celery Beat task `economic_calendar.ingest` (`app/workers/economic_calendar_tasks.py`), merged into the existing `celery_app.conf.beat_schedule`

docs/03, docs/04, docs/30 updated: resolved `economic_events`' field/timestamp gaps, added concrete `/calendar/*` API contracts (replacing the stale `/economic/*` draft), marked Phase 5B complete

Deliberately excluded (per Phase 5B approval): real vendor integration (TradingEconomics); Confidence Engine integration/weight rebalancing (ADR-047's boundary respected); revision-history audit trail (single mutable row only); automated stale-event cleanup; any Risk Engine logic (docs/14 §11); any AI/GPT usage anywhere in this engine; any trade recommendation

Tests: one file per deterministic module (`test_economic_category_classifier.py`, `test_economic_importance_scorer.py`, `test_economic_surprise_calculator.py`, `test_economic_bias_analyzer.py`, `test_economic_risk_window.py`), `test_mock_economic_calendar_provider.py`, `test_economic_calendar_ingestion_pipeline.py` (upsert/revision behavior), `test_economic_calendar_engine.py`, `test_economic_calendar_routes.py`

### Added - Phase 5A: News Sentiment Engine

`docs/46_NEWS_SENTIMENT_ARCHITECTURE.md` - new architecture document defining the two-path data flow (scheduled ingestion write path, on-demand read path), deterministic scoring algorithm, evidence schema, and the explicit divergence from Phase 4's `timeframe`-scoped engine pattern

`docs/10_NEWS_SENTIMENT_ENGINE.md` bumped to v1.1 - removed the internally-inconsistent free-text sentiment example (`"Bullish USD"`), replaced the undefined "AI Hash" duplicate-detection language with a reference to the concrete deterministic algorithm actually implemented

`app/services/news_sentiment/` - six deterministic modules (`dedup_detector`, `category_classifier`, `importance_scorer`, `sentiment_scorer`, `asset_detector`, `scoring_engine`) plus the isolated `ai_summary_generator` - only the last touches an LLM (OpenAI, narrative summary text only); sentiment/category/importance/affected-assets remain fully deterministic and unit-tested without live API calls

`NewsSentimentEngine` (`app/services/news_sentiment_engine.py`, read path) and `NewsIngestionPipeline` (`app/services/news_ingestion_pipeline.py`, Celery-scheduled write path) - split because News persists real entities and has a producer/ingestion shape unlike Phase 4's pure read-only engines

`app/services/news/providers/` - `NewsProvider` Protocol, `MockNewsProvider` (deterministic, seeded); no real vendor in this phase (ADR-050), mirrors the Phase 3A/3B Market Data provider split

New persisted tables `news_sources`, `news_articles`, `news_sentiment` (`app/models/news_source.py`, `news_article.py`, `news_sentiment.py`; migration `3636f44102c0_create_news_tables.py`) - `news_sources` uses `TimestampMixin`, `news_articles` uses `CreatedAtMixin` + its own `published_at`, `news_sentiment` uses `TimestampMixin` (ADR-053); one `news_sentiment` row per article with `affected_assets` as a JSON list, not a normalized per-asset table (ADR-052)

**ADR-050** through **ADR-055**: News provider abstraction is mock-first (real vendor deferred); sentiment scoring is deterministic-lexicon, with AI reserved solely for the narrative summary (tension with the Confidence Engine's no-AI-summary precedent, resolved by isolating the LLM call to one module); persistence model and mixin choices per table; deterministic duplicate detection (exact URL or title-similarity-within-window, replacing docs/10's undefined "AI Hash"); deterministic category/importance rule tables

New public (no auth) endpoints: `GET /news`, `GET /news/{id}`, `GET /analysis/news/{symbol}?since=` - the last has no `timeframe` parameter (News is asset/time-window scoped, not candle-timeframe scoped, docs/46 §10); 404 only on an unknown asset/article, never on an empty result set

Celery Beat task `news_sentiment.ingest` (`app/workers/news_sentiment_tasks.py`), merged into the existing `celery_app.conf.beat_schedule` alongside market data's per-timeframe schedule

docs/03, docs/04, docs/30 updated: resolved the News tables' field/timestamp gaps, added concrete API contracts (replacing the previously stale "Bullish/Bearish"-only response), introduced Phase 5 sub-phase lettering (5A-5D) for the first time

Deliberately excluded (per Phase 5A approval): real news vendor integration; Confidence Engine integration/weight rebalancing (ADR-047's boundary respected); `/ws/news`; true sub-30-second breaking-news SLA validation (unvalidatable against a mock provider); translation/multi-language; social/X sentiment; FinBERT/ML sentiment upgrade; `POST /admin/news`; a `/multi-asset` endpoint

Tests: one file per deterministic analyzer (`test_news_dedup_detector.py`, `test_news_category_classifier.py`, `test_news_importance_scorer.py`, `test_news_sentiment_scorer.py`, `test_news_asset_detector.py`), `test_news_ai_summary_generator.py` (OpenAI client mocked via `httpx.MockTransport`, never a real API call), `test_mock_news_provider.py`, `test_news_ingestion_pipeline.py`, `test_news_sentiment_engine.py`, `test_news_routes.py`

### Added - Phase 4D: Confidence Engine

`docs/45_CONFIDENCE_ARCHITECTURE.md` - new architecture document defining the data flow, modular scoring algorithm, alignment/conflict detection, freshness/completeness evaluation, and multi-timeframe strategy

`docs/15_CONFIDENCE_ENGINE.md` rewritten (v1.0 to v2.0) - v1.0 was a pre-Phase-4 vision document assuming six inputs (three of which don't exist) and BUY/SELL-oriented examples that contradicted its own stated evidence-only objective; v2.0 restricts scope to Technical Analysis/SMC/Market Regime, replaces the unusable formula/schema with the one actually implemented, and states News/Economic/Risk as explicit future inputs

`app/services/analysis_confidence/` - nine deterministic modules (`direction_normalizer`, `technical_confidence_analyzer`, `smc_confidence_analyzer`, `regime_confidence_analyzer`, `alignment_analyzer`, `conflict_analyzer`, `data_quality_analyzer`, `freshness_analyzer`, `summary_builder`) plus `confidence_aggregator` - the three "reframing" analyzers translate each upstream engine's already-computed score into confidence terms without recomputing any evidence; `confidence_aggregator.combine()` accepts a generic named-component list so Phase 5/6 inputs can be added without restructuring the aggregation pipeline

`AnalysisConfidenceEngine` (`app/services/analysis_confidence_engine.py`) - stateless (ADR-045, no new table), named to avoid confusion with `RegimeConfidenceEngine` (ADR-048); calls `TechnicalAnalysisEngine`/`SMCEngine` exactly once per execution and passes both into `MarketRegimeEngine.analyze()` (extended with optional pre-computed parameters, ADR-049) rather than letting it recompute them; degrades gracefully (never a hard failure) when any upstream engine has no candle data, returning reduced confidence with an explicit `missing_data` entry instead

`MarketRegimeEngine.analyze()` extended (additive only, `app/services/market_regime_engine.py`) with optional keyword-only `technical_analysis`/`smc` parameters, both defaulting to `None` - every existing caller unaffected (ADR-049)

**ADR-045** through **ADR-049**: Confidence Engine is stateless; the modular weighted-component scoring algorithm (Technical Analysis 25 / SMC 25 / Market Regime 20 / Cross-Engine Agreement 20 / Data Completeness 5 / Freshness 5 / Conflict Penalty floor -15); Phase 4D scope limited to Technical Analysis/SMC/Market Regime, News/Economic/Risk explicitly deferred to Phase 5/6; `AnalysisConfidenceEngine` naming distinguishes it from `RegimeConfidenceEngine`; `MarketRegimeEngine.analyze()`'s additive optional pre-computed-inputs extension

New public (no auth) endpoints: `GET /analysis/confidence/{symbol}?timeframe=` and `GET /analysis/confidence/{symbol}/multi-timeframe` - unlike Technical Analysis/SMC/Market Regime, does not 404 on missing candle data (graceful degradation instead), only on an unknown asset symbol

Response includes a deterministic, template-built 2-3 sentence `summary` (no AI-generated language) and an overall `conflict_severity` (`NONE`/`LOW`/`MEDIUM`/`HIGH`) alongside the full explainable `breakdown`

docs/04 updated: new "Confidence" section documenting both endpoints' concrete contracts, including the graceful-degradation behavior that distinguishes this endpoint from every prior `/analysis/*` route

Deliberately excluded (per Phase 4D approval): any BUY/SELL/WAIT recommendation or trade-outcome prediction; News Sentiment/Economic Calendar/Risk Management inputs (Phase 5/6, not built); historical calibration (needs a trade-outcomes dataset that doesn't exist); persistence of confidence results

Tests: `test_analysis_confidence_direction_normalizer.py`, `test_analysis_confidence_alignment_analyzer.py`, `test_analysis_confidence_conflict_analyzer.py`, `test_analysis_confidence_data_quality_analyzer.py`, `test_analysis_confidence_freshness_analyzer.py` (including the SQLite naive-datetime gotcha), `test_analysis_confidence_aggregator.py`, `test_analysis_confidence_summary_builder.py`, `test_analysis_confidence_engine.py` (integration, including the TA/SMC-called-exactly-once regression and graceful-degradation scenarios), `test_analysis_confidence_api.py`; `test_market_regime_engine.py` extended with a regression test for the new pre-computed-inputs parameters

### Status

Phase 4D (Confidence Engine) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 4C: Market Regime Engine

`docs/44_MARKET_REGIME_ARCHITECTURE.md` - new architecture document defining the reuse map, classification precedence rule, and classification-stability safeguard

`app/services/market_regime/` - eleven deterministic analyzers (`TrendRegimeAnalyzer`, `VolatilityRegimeAnalyzer`, `RangeAnalyzer`, `ExpansionAnalyzer`, `TransitionAnalyzer`, `AccumulationDistributionAnalyzer`, `BreakoutAnalyzer`, `PullbackReversalAnalyzer`, `RegimeConflictAnalyzer`, `RegimeClassifier`, `MultiTimeframeAnalyzer`) plus `RegimeConfidenceEngine` - almost entirely reusing Technical Analysis's and SMC's already-computed evidence rather than re-deriving it (docs/44 §5)

`MarketRegimeEngine` (`app/services/market_regime_engine.py`) - stateless (ADR-038, no `market_regime` table exists), calling `TechnicalAnalysisEngine` and `SMCEngine` exactly once per execution and passing their results by parameter to every analyzer (no repeated upstream analysis within one request)

`TechnicalAnalysisResult` extended (additive only, `app/services/technical_analysis/types.py`) with `trend_evidence`/`momentum`/`oscillator`/`volatility`/`volume` - analyzer-level evidence (ADX DI+/DI-, Bollinger bounds, state classifications) that was previously computed and discarded before reaching the public dataclass; Market Regime needed it directly rather than re-deriving it

**ADR-038** through **ADR-044**: Market Regime Engine is stateless; the classification precedence rule (evaluate all candidates' confidence first, apply precedence only among qualifiers); Accumulation/Distribution's deterministic definition (SMC Order Blocks/liquidity-sweep directionality); Pullback Depth as a single-timeframe retracement measurement, explicitly distinct from SMC's multi-timeframe Pullback; Regime Confidence's distinction from `technical_score`/`smc_score` and "Uncertain" fallback semantics; Strategy Compatibility/AI Integration as documentation guidance, never engine output; Market Regime Classification Stability (same-request anti-oscillation margin check, explicitly not true cross-request hysteresis given statelessness)

New public (no auth) endpoints: `GET /analysis/market-regime/{symbol}?timeframe=` and `GET /analysis/market-regime/{symbol}/multi-timeframe`

docs/16 and docs/04 updated: docs/16 resolves the "Uncertain" ambiguity and notes "Detect exhaustion" is folded into Pullback/Reversal warnings, not a dedicated output; docs/04 documents both new endpoints' concrete contracts

Deliberately excluded (per Phase 4C approval): `compatible_strategies`/recommendation fields (docs/16 §16/§17 remain documentation guidance only); true cross-request hysteresis (statelessness would need to be partially reversed - deferred)

Tests: `test_trend_regime_analyzer.py`, `test_volatility_regime_analyzer.py`, `test_expansion_analyzer.py`, `test_range_analyzer.py`, `test_transition_analyzer.py`, `test_accumulation_distribution_analyzer.py`, `test_breakout_analyzer.py`, `test_pullback_reversal_analyzer.py`, `test_market_regime_conflict_analyzer.py`, `test_regime_classifier.py` (including the precedence-vs-raw-confidence regression case), `test_confidence_engine.py`, `test_market_regime_multi_timeframe_analyzer.py`, `test_market_regime_engine.py` (integration, including a test proving upstream engines are called exactly once), `test_market_regime_api.py` (59 new tests total)

Deliberately out of scope: any BUY/SELL/WAIT recommendation, strategy-compatibility output, true cross-request hysteresis, Confidence Engine (Phase 4D), News/Economic analysis (Phase 5), AI Orchestrator integration (Phase 6)

### Status

Phase 4C (Market Regime Engine) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 4B: Smart Money Concepts (SMC) Engine

`docs/43_SMC_ARCHITECTURE.md` - new architecture document defining the persistence model, analyzer dependency graph, lifecycle states, and all algorithms (market structure, BOS, CHOCH, order blocks, FVG, liquidity, premium/discount, multi-timeframe)

`app/services/market_structure/swing_points.py` - swing-high/low fractal detection extracted from Technical Analysis's private `_find_swing_points`, now shared by both engines rather than duplicated

`app/services/smc/` - twelve deterministic analyzers (`MarketStructureAnalyzer`, `BOSAnalyzer`, `CHOCHAnalyzer`, `OrderBlockAnalyzer`, `MitigationAnalyzer`, `BreakerBlockAnalyzer`, `FairValueGapAnalyzer`, `LiquidityAnalyzer`, `PremiumDiscountAnalyzer`, `ConfluenceAnalyzer`, `SMCConflictAnalyzer`, `MultiTimeframeAnalyzer`) plus `SMCScoringEngine`, each a pure function over plain dataclasses - no database access, no AI, no probabilistic reasoning (ADR-031, ADR-036)

`SMCEngine` (`app/services/smc_engine.py`) - unlike the stateless Technical Analysis Engine, persists detected structures to `smc_events` (ADR-032): bounded to the most recent 500 candles per call, de-duplicated against existing rows by natural key, with a lifecycle-archiving pass and an `SMCProcessingState` checkpoint per asset/timeframe

New models: `SMCEvent` (mutable zone-lifecycle rows - a first for this project, contrasting every other append-only table, ADR-033) and `SMCProcessingState` (recovery/migration bookkeeping: last processed timestamp, engine version)

**ADR-032** through **ADR-037**: SMC persistence and incremental-scan design; mutable `smc_events` rows; Order Block candle-pattern definition; equal-highs/lows magnitude-aware tolerance; SMC multi-timeframe weights and `smc_score` distinct from `technical_score`; SMC Event Lifecycle (ACTIVE/MITIGATED/INVALIDATED/ARCHIVED states and transitions, never deleting historical events)

New public (no auth) endpoints: `GET /analysis/smc/{symbol}?timeframe=` and `GET /analysis/smc/{symbol}/multi-timeframe`

docs/09 and docs/04 updated: docs/09 §17's inconsistent flat boolean example (`"bos": true`) corrected to the list-based Evidence Model actually implemented, and the four concepts referenced during planning but absent from docs/09 (IFVG, Internal/External BOS, Displacement, Market Imbalance) are noted as deliberately excluded; docs/04 documents both new endpoints' concrete contracts

Deliberately excluded (undocumented in docs/09, "never invent architecture"): Inverse Fair Value Gaps (IFVG), an Internal/External BOS distinction, a dedicated Displacement analyzer, Market Imbalance

Tests: `test_swing_points.py`, `test_market_structure_analyzer.py`, `test_bos_analyzer.py`, `test_choch_analyzer.py`, `test_order_block_analyzer.py`, `test_mitigation_analyzer.py`, `test_breaker_block_analyzer.py`, `test_fair_value_gap_analyzer.py`, `test_liquidity_analyzer.py`, `test_premium_discount_analyzer.py`, `test_smc_confluence_analyzer.py`, `test_smc_conflict_analyzer.py`, `test_smc_scoring_engine.py`, `test_smc_multi_timeframe_analyzer.py`, `test_smc_models.py`, `test_smc_engine.py` (integration), `test_smc_api.py` (59 new tests total)

Deliberately out of scope: any BUY/SELL/WAIT recommendation, true delta-only incremental scanning (documented as a future optimization), API filtering query params (`event_type`, `include_mitigated`), News/Economic analysis (Phase 5), AI Orchestrator integration (Phase 6)

### Status

Phase 4B (Smart Money Concepts Engine) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 4A: Technical Analysis Engine

`docs/42_TECHNICAL_ANALYSIS_ARCHITECTURE.md` - new architecture document defining the data flow, analyzer responsibilities, missing-indicator policy, support/resistance algorithm, scoring formula, and multi-timeframe combination algorithm

`app/services/technical_analysis/` - nine deterministic, stateless analyzers (`MovingAverageAnalyzer`, `TrendAnalyzer`, `MomentumAnalyzer`, `OscillatorAnalyzer`, `VolatilityAnalyzer`, `VolumeAnalyzer`, `SupportResistanceAnalyzer`, `MultiTimeframeAnalyzer`, `ConflictAnalyzer`) plus `TechnicalScoringEngine`, each a pure function over plain dataclasses - no database access, no AI, no probabilistic reasoning (ADR-031)

`TechnicalAnalysisEngine` (`app/services/technical_analysis_engine.py`) - the top-level, fully stateless orchestrator (ADR-027): fetches candles via the existing `PriceCandleRepository`, computes every indicator fresh via the Phase 3A `app/indicators` registry (not persisted `indicator_results`, avoiding staleness), runs every analyzer, and assembles one `TechnicalAnalysisResult`

Definitive 100-point technical scoring formula (ADR-028), superseding docs/08 §9's illustrative example, which only summed to 75 despite the same section stating a maximum of 100 - a genuine internal inconsistency in docs/08, not just an incomplete example. Score reported as a full `ScoreBreakdown` (trend/momentum/oscillator/volume/volatility/support_resistance/penalties/total), not just the single total - Phase 4A refinement for explainability

Support/Resistance evidence extended with `source` and `strength` metadata per level (Phase 4A refinement), not just a bare price; round numbers/psychological levels use a magnitude-aware rounding heuristic (ADR-029) rather than a hardcoded per-symbol table

Multi-timeframe combination algorithm (ADR-030): D1/H4/H1/M15 weighted 40/30/20/10, a ±0.5 net-ratio threshold determines `bullish_alignment`/`bearish_alignment`/`mixed` - a missing timeframe is skipped, not treated as neutral

**ADR-031**: "Technical Analysis Produces Evidence, Not Trading Signals" - makes explicit (beyond ADR-005/006) that this engine never produces a BUY/SELL/WAIT recommendation or entry/stop-loss/take-profit level; that remains the future Signal Engine's job (docs/30 Phase 6)

New public (no auth) endpoints: `GET /analysis/technical/{symbol}?timeframe=` and `GET /analysis/technical/{symbol}/multi-timeframe`, matching the Phase 3C precedent for non-personalized market reference data

docs/04 and docs/08 updated: docs/04 documents the two new endpoints' concrete contracts (previously marked "not yet implemented"); docs/08 §9/§10/§11 annotated to point at docs/42/ADR-028 as the canonical scoring source, rather than leaving the internally-inconsistent example uncorrected

Phase-numbering note: tracked as sub-phase **4A** in docs/30 (SMC Engine = 4B, Market Regime Engine = 4C, Confidence Engine = 4D), per docs/30's existing Phase 4 grouping (which includes SMC, unlike an earlier informal framing that treated SMC as a separate later phase)

A real bug was caught during test-writing, not just implementation: an initial `zip(emas, emas[1:], strict=True)` in `MovingAverageAnalyzer` was wrong - the two sequences are intentionally different lengths to produce sliding pairs, and `strict=True` made that fail immediately once real test data was run

Tests: `test_technical_analysis_analyzers.py`, `test_support_resistance_analyzer.py`, `test_scoring_engine.py`, `test_multi_timeframe_analyzer.py`, `test_technical_analysis_engine.py` (integration), `test_technical_analysis_api.py` (53 new tests total)

Deliberately out of scope: any BUY/SELL/WAIT recommendation, Smart Money Concepts (Phase 4B), News/Economic analysis (Phase 5), AI Orchestrator integration (Phase 6), persisted technical-analysis history

### Status

Phase 4A (Technical Analysis Engine) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3C: Market Data API

`GET /assets`, `GET /assets/{symbol}`, `GET /market/{symbol}/latest`, `GET /market/{symbol}/candles`, `GET /market/{symbol}/indicators` - all public, no authentication required (per explicit decision: market reference data isn't user-specific, matching docs/04's Guest rate-limit tier and docs/23 §12's "View Public Pages")

Thin API layer only - every route calls existing repositories (`AssetRepository`, `PriceCandleRepository`, `IndicatorResultRepository`) directly, with new repository methods (`AssetRepository.list_filtered`/`count_filtered`, `PriceCandleRepository.list_range`'s new optional `limit`) added to support filtering/pagination without introducing service-layer logic that wasn't needed for read-only endpoints

`GET /market/{symbol}/indicators` is new - not previously in docs/04 - exposing the raw `indicator_results` values (docs/39) Phase 3A/3B already populate; deliberately distinct from the future `GET /analysis/technical/{symbol}` (Phase 4's synthesized trend/scoring output, still unbuilt). The `indicator` query filter is validated against the indicator registry (`app.indicators.registry`), not an unrestricted string - an unknown indicator name is rejected with a clear error rather than silently returning nothing

`GET /market/{symbol}` renamed to `GET /market/{symbol}/latest` before implementation, to make its single-candle-snapshot purpose explicit and avoid future ambiguity with the candles/indicators endpoints

Symbol path parameters are case-insensitive (`eurusd` and `EURUSD` resolve identically) - shared `get_asset_or_404` dependency normalizes and 404s consistently across every symbol-keyed route

`RequestValidationError` handler added (`app/exceptions/handlers.py`), normalizing FastAPI's built-in `{"detail": [...]}` validation-error shape to the project's standard `{"error", "message"}` envelope - a gap that existed since Phase 2C but was only surfaced now that a phase has meaningfully-validated query parameters (`timeframe`, indicator names) users will routinely get wrong

Spread is intentionally omitted from `GET /market/{symbol}/latest`'s response, not fabricated - it isn't part of the data model (docs/03 §5, no integrated provider supplies it); documented as unavailable in docs/04 rather than invented

docs/04_API_SPECIFICATION.md updated: the five endpoints above with concrete request/response shapes, and `GET /analysis/technical/{symbol}` explicitly marked "not yet implemented" with a note distinguishing it from the new indicators endpoint

A genuinely flaky pre-existing test was found and fixed while running the full suite repeatedly during this phase: `test_decode_token_rejects_tampered_signature` tampered only the *last* character of a JWT signature, which - depending on the signature's byte length - can encode only padding/insignificant bits, occasionally letting the "tampered" token verify successfully anyway (reproduced failing 1-in-3 runs in isolation). Fixed to tamper the *first* character of the signature segment instead, which is always significant

Tests: `test_market_data_api.py` (14 tests) covering pagination, filtering, 404s, symbol-case-normalization, timeframe/indicator validation error envelopes, and candle range/limit behavior

### Status

Phase 3C (Market Data API) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3B: Twelve Data Provider

`docs/41_SYMBOL_NORMALIZATION.md` - new document defining the project's canonical internal symbol representation (plain, uppercase, separator-free `Asset.symbol`) first, then the Twelve Data-specific mapping: a mechanical FOREX/METAL/CRYPTO rule (guarded by a known-currency-code allowlist, not a bare length check), an explicit INDEX override table (left empty - no entries could be confirmed against Twelve Data's own symbol catalog from public documentation alone), and the confirmed timeframe-to-`interval` table

`TwelveDataProvider` (`app/services/market_data/providers/twelve_data.py`) - the first real `MarketDataProvider` implementation, covering FOREX/METAL/CRYPTO (INDEX deliberately excluded from `capabilities()` until docs/41's override table has verified entries); classifies Twelve Data's error responses into `TwelveDataAuthenticationError`/`TwelveDataQuotaExceededError`/`TwelveDataInvalidSymbolError`, each subclassing the shared `PermanentProviderError`/`TransientProviderError` categories

`TwelveDataHttpClient` (`app/services/market_data/providers/twelve_data_http.py`) - isolates raw `httpx` transport concerns (base URL, auth header, timeout, network-level error handling) from `TwelveDataProvider`'s response-classification logic; accepts an injectable `transport` so tests never make real network calls. Recorded as **ADR-026** ("Isolate Raw HTTP Transport Behind a Dedicated Client Per Provider") - the pattern any future HTTP-calling provider should follow

`DailyQuotaExceededError` added to the provider exception hierarchy; `RateLimitedProvider` gained an optional `requests_per_day` parameter (ADR-025) - Twelve Data's free tier is capped at both 8 requests/minute *and* 800/day, and the existing per-minute token bucket alone couldn't prevent exceeding the daily cap. Raises (rather than sleeping for hours) once the UTC-calendar-day budget is exhausted, carrying `used`/`limit`/`reset_at` for observability

`ProviderCapabilities.supported_market_types` is now a required field, not an optional field defaulting to `None`-meaning-"supports everything" - every provider must declare its market types explicitly (`MockMarketDataProvider` updated accordingly)

New settings: `market_data_rate_limits_per_day`, `market_data_default_rate_limit_per_day`, `twelve_data_api_key`, `twelve_data_base_url`, `twelve_data_timeout_seconds`; `TWELVE_DATA_API_KEY=` added to `.env.example`. `twelve_data` is registered in the provider factory but **not** in the default `market_data_providers` list - it only activates when explicitly configured with a real API key

`httpx` promoted from a dev-only to a declared runtime dependency (`pyproject.toml`) - it was already installed transitively via FastAPI's test client, but a real HTTP client is now needed in production code, not just tests

Provider contract-test convention exercised again: `test_twelve_data_provider.py::test_twelve_data_provider_satisfies_provider_contract` runs the same `assert_provider_contract` helper (Phase 3.5) against a mocked-transport `TwelveDataProvider`, alongside dedicated error-classification and symbol-mapping tests - no real Twelve Data API calls are made anywhere in the test suite (docs/40 §10)

A real bug was caught during test-writing, not just implementation: a naive "split any 6-character symbol in half" mechanical rule would have mis-translated `NAS100` into `NAS/100` - fixed with a known-currency-code allowlist before it ever reached production code; documented in docs/40 §3 and docs/41 §3 so it isn't rediscovered

Deliberately still out of scope: enabling `twelve_data` by default, INDEX market-type support (blocked on verifying docs/41's override table against Twelve Data's real symbol catalog), a second real fallback provider, and any Phase 4 work

### Status

Phase 3B (Twelve Data Provider) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3.5: Market Data Integration & Quality Gate

`docs/40_PROVIDER_INTEGRATION_GUIDE.md` - new canonical checklist for integrating any market-data provider: interface requirements, symbol/timeframe mapping, error classification, capability declaration, rate-limit configuration, secrets convention, health-check integration, and testing requirements

`RateLimitedProvider` (`app/services/market_data/providers/rate_limited.py`) - a token-bucket decorator wrapping any `MarketDataProvider`, so rate limiting is applied uniformly without embedding provider-specific throttling logic in `MarketDataService`; configured per-provider via `settings.market_data_rate_limits_per_minute` (falling back to `settings.market_data_default_rate_limit_per_minute`), applied automatically by `get_market_data_providers()`

`ProviderCapabilities` (`app/services/market_data/providers/base.py`) - a structured, extensible value object (`supported_timeframes`, `supported_market_types`, `max_lookback`) replacing a single boolean `supports()` method, so new capability dimensions can be added without breaking existing providers; `MarketDataService` now checks capabilities proactively before calling a provider, rather than discovering an unsupported timeframe reactively

`ProviderConfigurationError` added to the provider exception hierarchy (`app/services/market_data/exceptions.py`) for setup-time misconfiguration (e.g. an unknown provider name), replacing a raw `ValueError`; the hierarchy's extension point for future provider-specific exceptions (e.g. `TwelveDataAuthenticationError`) is now documented

`CandleValidator` gained a timestamp-plausibility rule - a candle whose timestamp falls outside the requested `[start, end]` window (with a small clock-skew tolerance) is now rejected, closing docs/34's "Timestamp" validation requirement

`MarketDataService` now logs provider-call latency (`market_data.provider_call`, with `duration_ms` and `outcome`) for every attempt, success or failure - closing part of ADR-019's "Observability by Default" requirement for this pipeline

`GET /health/ready` now reports each configured provider's `health_check()` result diagnostically (`market_data_providers` in the response body) - a provider being unreachable does not flip overall readiness

CI (`.github/workflows/ci.yml`) now runs a real PostgreSQL 17 service container and executes `alembic upgrade head`/`alembic check` against it before the test suite - closing the long-standing "CI doesn't test the migration path" gap (BACKLOG.md §5/§9)

Provider contract-test convention: `tests/market_data_contract.py::assert_provider_contract`, demonstrated against `MockMarketDataProvider` in `test_mock_provider.py` - every future provider's test suite should call the same helper

Tests: `test_rate_limited_provider.py`, `test_market_data_dependencies.py`, plus additions to `test_market_data_service.py` (capability-based skipping) and `test_candle_validator.py` (timestamp-plausibility rules)

Deliberately still no real market-data provider integrated (Phase 3B); no persisted symbol-mapping table; no metrics/Prometheus endpoint (still tracked separately in BACKLOG.md)

### Status

Phase 3.5 (Market Data Integration & Quality Gate) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3A: Market Data Foundation

`docs/38_MARKET_DATA_ARCHITECTURE.md` - new architecture document defining the provider abstraction, symbol/timeframe normalization, data validation, duplicate detection, retry/failover, scheduler design, and provider lifecycle for the market-data pipeline

`docs/39_INDICATOR_REFERENCE.md` - new canonical reference for every implemented indicator: mathematical definition, inputs, parameters, output fields, warm-up requirements, numerical precision, and external source, for all 18 registered indicators

`app/models/enums/` restructured from a single `enums.py` into a package (`user_role.py`, `timeframe.py`, `market_type.py`), scaling better as domain enums grow; all existing imports (`from app.models.enums import UserRole`) are unaffected

New models: `Asset` (`TimestampMixin`), `PriceCandle` (`CreatedAtMixin`, unique on `(asset_id, timeframe, timestamp)` - see ADR-024), `IndicatorResult` (own `calculated_at` column) - per docs/03 §5-6

New repositories: `AssetRepository`, `PriceCandleRepository` (`upsert`, `get_latest`, `list_range`, `list_recent`), `IndicatorResultRepository` - data access only

Alembic migration for `assets`/`price_candles`/`indicator_results`, verified via upgrade/downgrade/upgrade round-trip and `alembic check`; the recurring `server_default` SQLite-vs-Postgres gotcha (BACKLOG.md §9) was caught and corrected again before committing

`MarketDataProvider` interface (`app/services/market_data/providers/base.py`) and `MockMarketDataProvider` - a deterministic, seeded synthetic OHLCV generator; no external API integration this phase (Phase 3B adds the first real provider, Twelve Data)

`CandleValidator` - a dedicated component owning candle validation rules (docs/08 §12), kept separate from `MarketDataService`, which only orchestrates the fetch → normalize → validate → persist workflow

`MarketDataService` - retry-with-backoff and provider failover (falling back to already-stored data when every provider fails), idempotent persistence via `PriceCandleRepository.upsert`

Scheduler: a single conceptual Celery task (`market_data.collect_for_timeframe`) parameterized by `Timeframe`, with one Celery Beat schedule entry per timeframe (`app/workers/market_data_tasks.py`) - not a separate task per timeframe

`app/indicators/` package (per docs/06 §3's reserved top-level folder), organized into `trend.py`, `momentum.py`, `volatility.py`, `volume.py`, `trend_strength.py`, with a discovery registry (`app/indicators/registry.py`) - implements the full docs/08 §5 indicator list: EMA (20/50/100/200), SMA (200), RSI (14), MACD (12/26/9), Stochastic RSI (14), CCI (20), Momentum (10), ATR (14), Bollinger Bands (20/2), Standard Deviation (20), VWAP, OBV, Volume SMA (20), Relative Volume (20), ADX/DI+/DI- (14)

`IndicatorService` - populates `indicator_results` with raw indicator values only; deliberately no trend detection, technical scoring, or conflict detection (docs/08 §7-11 remains Phase 4's Technical Analysis Engine)

`ADR-024` - unique constraint + upsert semantics on `PriceCandle`

Tests: `test_indicators.py`, `test_market_data_models.py`, `test_candle_validator.py`, `test_market_data_service.py`, `test_mock_provider.py`, `test_indicator_service.py`, `test_market_data_tasks.py`

Deliberately excluded from this phase: any real market-data provider, a persisted symbol-mapping table, `/health/ready` provider-status integration, indicator synthesis/trend detection/technical scoring, SMC/regime/confidence engines, WebSocket price streaming

### Status

Phase 3A (Market Data Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 2C: Authentication API

`docs/37_AUTHENTICATION_FLOW.md` - new architecture document defining registration/login/refresh/logout/session-revocation flows, JWT lifecycle, audit-logging flow, service vs. API responsibilities, and future email-verification integration points

API routes (`app/api/v1/routes/auth.py`): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, matching `docs/04_API_SPECIFICATION.md`

Pydantic schemas (`app/schemas/auth.py`): `RegisterRequest`, `LoginRequest`, `RefreshRequest`, `LogoutRequest`, `TokenResponse`, `UserResponse` - all with OpenAPI examples; `TokenResponse.expires_in` always derived from `settings.jwt_access_expire_minutes`, never hardcoded

`app/dependencies/auth.py`: `get_user_service`, `get_authentication_service`, and `get_current_user` - the latter deliberately minimal (extract bearer token → decode → verify `type == "access"` → load user), with no authorization checks

`InvalidAccessTokenException` added to `app/exceptions/auth.py` for `get_current_user`'s token-validation failures

`UserService.register_user` now commits its own transaction (previously relied on the caller/tests to commit)

Response envelope conflict resolved: `docs/04` and `docs/33` each described a different, unimplemented `{"success": ...}` envelope; both were corrected to match the shape already implemented in Phase 1 (`app/exceptions/handlers.py`) - unwrapped success bodies, `{"error", "message"}` on failure

`docs/04_API_SPECIFICATION.md` updated with concrete request/response examples for every route, and marked `POST /auth/forgot-password`/`POST /auth/reset-password` as "not yet implemented"

Deliberately excluded from this phase: forgot/reset-password routes, session/device-management routes, OAuth, email verification, RBAC enforcement, rate limiting, CSRF/CSP, cookies

API-level tests: `test_auth_api.py` (11 tests covering all five routes' success and failure paths)

### Status

Phase 2C (Authentication API) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 2B: Authentication Service Layer

`UserService` - registration business logic: password-policy validation (docs/23 §7 — 12+ chars, upper/lower/number/special), email/username uniqueness checks (`DuplicateUserException`), and lookup helpers (`get_user_by_id`, `get_user_by_email`) raising `ResourceNotFoundException` when missing

`AuthenticationService` - `login`, `refresh`, `logout`, `revoke_session`, and `revoke_all_sessions`, with audit-log entries written for `login_success`, `login_failed`, `logout`, and `session_revoked` (docs/23 §18)

Custom authentication exceptions in `app/exceptions/auth.py`: `InvalidCredentialsException`, `InactiveAccountException`, `InvalidRefreshTokenException`, `DuplicateUserException`, `WeakPasswordException`

`hash_token()` added to `app/core/security.py` - deterministic SHA-256 hashing for refresh-token storage/lookup, distinct from Argon2id password hashing (see ADR-023)

Explicit, domain-oriented persistence methods added to `UserRepository`, `UserSessionRepository`, and `AuditLogRepository` (`create`, `get_by_id`, `delete`, `delete_for_user`) to support the new services, without adding generic `add`/`delete` to `BaseRepository`

Login intentionally does not require `User.is_verified` this phase, since email-verification infrastructure is deferred - recorded as a temporary decision in `BACKLOG.md` to revisit once that workflow exists

Unit tests: `test_user_service.py`, `test_authentication_service.py`

API routes, FastAPI dependencies, OAuth login flow, email verification, password reset, RBAC enforcement, middleware, and cookies intentionally out of scope for this phase; see `BACKLOG.md`

### Status

Phase 2B (Authentication Service Layer) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 2A: Authentication Data & Security Primitives

`User`, `OAuthAccount`, `UserSession`, and `AuditLog` models, plus `UserRole` and related enums, completing the auth-related domain models deferred from Phase 1.2B

`(provider, provider_user_id)` uniqueness constraint on `OAuthAccount`, documented as ADR-022 since it was inferred rather than explicitly specified in `docs/03`

OAuth token persistence intentionally omitted from `OAuthAccount` for this phase (only linking fields are stored)

`UserRepository`, `OAuthAccountRepository`, `UserSessionRepository`, `AuditLogRepository` - concrete repositories limited to data access, no business logic

`app/core/security.py` - password hashing and UUID-based JWT helpers with standard claims

Alembic migration for auth tables (`a7dad339df2e_create_auth_tables`), verified via upgrade/downgrade/upgrade round-trip and `alembic check`

Tests covering security utilities, user models, and foreign-key behavior

Business logic, API endpoints, and authentication flows (register/login/refresh/logout) intentionally deferred to a later phase; see `BACKLOG.md`

### Status

Phase 2A (Authentication Data & Security Primitives) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 1.2B: Domain Models

`SystemSetting` model - the first real domain model, with a unique/indexed `key`, `value`, `description`, and full created_at/updated_at

`SystemSettingRepository` - a concrete repository with a single data-access method (`get_by_key`), no business logic

`CreatedAtMixin` - reusable infrastructure for append-only rows (single `created_at`, no `updated_at`)

First real Alembic migration (`2822d8e2e377_create_system_settings_table`), verified via a full upgrade/downgrade/upgrade round-trip and `alembic check` with zero drift

`AuditLog` intentionally deferred to Phase 2, to be modeled together with `User` so its foreign key can be correct from the start

### Status

Phase 1.2B (Domain Models) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 1.2A: Database Foundation

`UUIDMixin` and `TimestampMixin` for SQLAlchemy models (UUID primary keys, UTC created_at/updated_at)

`BaseRepository` generic infrastructure: constructor-injected session, query/filter/pagination helpers, transaction context manager - no CRUD, so concrete repositories define their own operations

Verified Alembic autogeneration against the current (model-free) metadata; migration history intentionally left empty until the first real domain model lands

### Status

Phase 1.2A (Database Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 1.1: Project Foundation

Backend skeleton (FastAPI) structured per Clean Architecture layering: api, config, core, database, dependencies, middleware, exceptions, repositories, services, utils, workers

Frontend skeleton (Next.js, TypeScript, Tailwind, shadcn/ui) structured per the documented frontend folder layout

Docker and Docker Compose setup for frontend, backend, worker, PostgreSQL, and Redis, with healthchecks

uv adopted as the official backend dependency manager (ADR-021)

Structured JSON logging via structlog, shared between FastAPI and future Celery workers, with correlation ID propagation and sensitive-data redaction

Liveness (`/health`) and readiness (`/health/ready`) endpoints

Alembic migration scaffolding wired to centralized configuration

CI foundation via GitHub Actions (ruff, mypy, pytest, eslint, typecheck, build)

Development tooling: ruff, mypy, black, pytest (backend); eslint, prettier, TypeScript strict mode (frontend)

### Status

Phase 1 (Project Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

## Version 1.0.0

### Added

Complete software architecture

36 engineering documents

AI architecture

Frontend guidelines

Backend guidelines

Database design

API specification

Development roadmap

---

Future releases will follow Semantic Versioning.