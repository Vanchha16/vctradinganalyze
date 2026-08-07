# Development Roadmap

Version: 1.0

---

# Phase 0

Architecture

Documentation

Database Design

API Design

UI Design

Complete Specifications

Status

Completed

---

# Phase 1

Project Foundation

Repository

Docker

FastAPI

Next.js

Database

Redis

CI

Status

Completed

Sub-Phases

1.1 Project Foundation (Docker, FastAPI, Next.js, config, logging, CI) - Completed

1.2A Database Foundation (SQLAlchemy base, mixins, repository base) - Completed

1.2B Domain Models (SystemSetting, CreatedAtMixin) - Completed

---

# Phase 2

Authentication

User Management

Admin Panel

Feature Flags

Status

In Progress

Sub-Phases

2A Authentication Data & Security Primitives (User, OAuthAccount, UserSession, AuditLog models; JWT/password hashing utilities; ADR-022) - Completed

2B Authentication Service Layer (UserService, AuthenticationService, audit logging integration, custom auth exceptions; ADR-023) - Completed

2C Authentication API (register/login/refresh/logout/me routes, Pydantic schemas, get_current_user dependency, docs/37_AUTHENTICATION_FLOW.md) - Completed

---

# Phase 3

Market Data Engine

Price Collection

Indicators

Historical Storage

Status

In Progress

Sub-Phases

3A Market Data Foundation (provider abstraction, MockMarketDataProvider, Asset/PriceCandle/IndicatorResult models, indicator-calculation engine + registry, scheduler; docs/38_MARKET_DATA_ARCHITECTURE.md, ADR-024) - Completed

3.5 Market Data Integration & Quality Gate (provider rate limiting, extensible capability declarations, provider-specific exception hierarchy, timestamp validation, latency logging, health-check integration, PostgreSQL CI verification, provider contract-test convention; docs/40_PROVIDER_INTEGRATION_GUIDE.md) - Completed

3B Real Provider Integration (TwelveDataProvider, docs/41_SYMBOL_NORMALIZATION.md, daily quota enforcement per ADR-025) - Completed

3C Market Data API (public GET /assets, /assets/{symbol}, /market/{symbol}/latest, /market/{symbol}/candles, /market/{symbol}/indicators; RequestValidationError envelope normalization; docs/04 updated) - Completed

---

# Phase 4

Technical Analysis Engine

SMC Engine

Market Regime Engine

Confidence Engine

Status

In Progress

Sub-Phases

4A Technical Analysis Engine (nine deterministic analyzers, TechnicalScoringEngine, stateless TechnicalAnalysisEngine; docs/42_TECHNICAL_ANALYSIS_ARCHITECTURE.md, ADR-027 through ADR-031) - Completed

4B SMC Engine (twelve deterministic analyzers, SMCScoringEngine, persistent SMCEngine with lifecycle-managed `smc_events`; docs/43_SMC_ARCHITECTURE.md, ADR-032 through ADR-037) - Completed

4C Market Regime Engine (eleven deterministic analyzers, RegimeConfidenceEngine, stateless MarketRegimeEngine reusing Technical Analysis/SMC evidence; docs/44_MARKET_REGIME_ARCHITECTURE.md, ADR-038 through ADR-044) - Completed

4D Confidence Engine (`AnalysisConfidenceEngine` evaluating quality/completeness/consistency of Technical Analysis's, SMC's, and Market Regime's evidence - no BUY/SELL recommendation, no trade-outcome prediction; docs/45_CONFIDENCE_ARCHITECTURE.md, ADR-045 through ADR-049) - Completed

---

# Phase 5

Economic Engine

News Engine

Risk Engine

Strategy Engine

Status

In Progress

Sub-Phases

5A News Sentiment Engine (`NewsSentimentEngine`/`NewsIngestionPipeline`, persisted `news_sources`/`news_articles`/`news_sentiment`, deterministic dedup/category/importance/sentiment analyzers, isolated AI-only narrative summary, `MockNewsProvider`; docs/46_NEWS_SENTIMENT_ARCHITECTURE.md, ADR-050 through ADR-055) - Completed

5B Economic Calendar Engine (`EconomicCalendarEngine`/`EconomicCalendarIngestionPipeline`, persisted `economic_events` with upsert-by-natural-key, deterministic category/importance/bias/risk-window rules, `MockEconomicCalendarProvider`; docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md, ADR-056 through ADR-061) - Completed

5C Risk Management Engine (`RiskManagementEngine`, stateless, reuse-first design over `AnalysisConfidenceEngine`/`NewsSentimentEngine`/`EconomicCalendarEngine`, deterministic session/spread/liquidity/correlation/RR/stop-loss filters, hard-reject decision + Trade Quality Score; docs/48_RISK_MANAGEMENT_ARCHITECTURE.md, ADR-062 through ADR-068) - Completed

5D Strategy Engine (`StrategyEngine`, stateless, reuse-first design over `AnalysisConfidenceEngine`/`EconomicCalendarEngine`/`risk_management` sub-modules, seven deterministic strategy-requirements checklists, Market Match + Evidence Quality + Confidence + Risk + Historical Performance scoring, rejection/ranking; docs/49_STRATEGY_ARCHITECTURE.md, ADR-069 through ADR-076) - Completed

---

# Phase 6

AI Orchestrator

AI Reasoning

Signal Engine

AI Chat

Status

Completed

Sub-Phases

6A AI Orchestrator / AI Reasoning Engine (single `AIOrchestratorEngine`, deterministic `recommendation_decision`/`candidate_setup_builder`/`invalidation_builder`/`evidence_extractor`, `AIProvider` Protocol with `OpenAIProvider`, structured JSON output, persisted `ai_analysis` with `CreatedAtMixin`; docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md, ADR-077 through ADR-084) - Completed

6B Signal Engine (`SignalEngine`, a thin wrapper over `AIOrchestratorEngine` introducing zero new evidence weighting/confidence/recommendation logic, persisted `signals` with `CreatedAtMixin` for BUY/SELL outcomes only, read-time-computed EXPIRED status, `signal_bookmarks`; docs/51_SIGNAL_ARCHITECTURE.md, ADR-085 through ADR-091) - Completed

6C AI Chat Assistant (`AIChatEngine`, a thin conversational layer over Phase 4-6B introducing zero new evidence/recommendation logic, reusing `ContextBuilder` for grounding and the persisted `ai_analysis`/`signals` rows for recommendation/signal explanations, `AIProvider` extended with `generate_chat_reply()`, persisted `conversations`/`messages` with two-level symbol/timeframe scoping; docs/52_AI_CHAT_ARCHITECTURE.md, ADR-092 through ADR-098) - Completed

---

# Phase 7

Dashboard

TradingView

Watchlists

Notifications

Telegram

Status

In Progress

Sub-Phases

7A Frontend Foundation - Authentication & User Experience (auth pages backed by the real Bearer-token backend - login/register/forgot-password stub; client-side session persistence and protected routing via `AuthGuard`/`GuestGuard`; the existing dev dashboard shell evolved into the authenticated product shell (`AppShell`, `Sidebar`, `TopNav`, `UserMenu`); dark/light/system theming aligned to docs/05 §4's palette; shared empty/error UI; zero new backend endpoints; docs/53_FRONTEND_FOUNDATION_ARCHITECTURE.md, ADR-099 through ADR-102) - Completed

7B Dashboard & Core Pages (Dashboard rebuilt as five reusable widgets - Market Overview/Latest Signals/Economic Events/Breaking News/AI Insights, ADR-106; Markets, Signals, News, Economic Calendar, AI Analysis, AI Chat, Watchlists (placeholder, ADR-103), Profile (read-only, ADR-104), Settings (Appearance + Account, ADR-104); `lightweight-charts` candlestick chart with Support/Resistance/Order Block overlays, ADR-105; Sidebar restructured into grouped nav with a dedicated "Analysis" section preserving the Phase 6 dev pages; zero new backend endpoints; docs/54_DASHBOARD_CORE_PAGES_ARCHITECTURE.md, ADR-103 through ADR-106) - Completed

7C Frontend Experience & Advanced Trading UI (Markets sort/search/quick-actions; AI Analysis guided flow, confidence gauge, evidence timeline, `react-markdown` reasoning; AI Chat conversation search/archive/delete, suggested prompts, optimistic pending-message UX, markdown messages; Signal detail reuses Reasoning/Evidence components, adds chart + status timeline, symbol filter; `PriceChart` extended with zone + time-marker overlays for BOS/CHoCH/Order Blocks/FVG/Liquidity, ADR-107; Dashboard gains a sixth Quick Actions widget; app-wide loading-skeleton/transition/accessibility/code-splitting polish; zero new backend endpoints; docs/55_FRONTEND_EXPERIENCE_ADVANCED_UI.md, ADR-107 through ADR-109) - Completed

7D-A Watchlists Backend (`Watchlist`/`WatchlistItem` models + migration per docs/03 §12's minimal schema, `WatchlistRepository`/`WatchlistService`, `GET/POST/PUT/DELETE /watchlists` + add/remove asset + inferred `GET /watchlists/{id}`, all auth-gated and user-scoped; docs/58_WATCHLISTS_ADMIN_ARCHITECTURE.md, ADR-114, ADR-128) - Completed

7D-B Watchlists Frontend (replaces the ADR-103 placeholder with real CRUD - list/create/rename/delete watchlists, add/remove assets; `services/watchlists.ts`, `apiPut` added to `api-client.ts`, `use-watchlists`/`use-watchlist`/`use-watchlist-actions` hooks, `features/watchlists/` components, Markets' `AssetTable` reused with an additive `onRemove` prop; docs/58 §2.4) - Completed

7D-C Admin Backend (**user-management portion superseded by Phase 8C/docs/59** - the first-ever `require_role` RBAC-enforcement dependency over the existing `UserRole` enum, ADR-115, and the full `/admin/users*` surface (9 endpoints, `AdminUserService`) both shipped there instead; `GET /admin/logs` shipped separately in Phase 8F, ADR-129; this sub-phase completes the remaining five - `GET /admin/{signals,system,analytics}`, `POST /admin/{news,maintenance}` sharing one `AdminSystemService.refresh_news`/`refresh_calendar` implementation between the two write routes; `/admin/system` reuses existing health checks + counts and degrades to `"down"` rather than 500ing, not live telemetry, ADR-116; `/admin/maintenance` limited to refresh-news/refresh-calendar via a `Literal` request body, ADR-117; corrects BACKLOG.md §16's inaccurate "decided against" wording for `POST /admin/news`; docs/58, ADR-130) - Completed

7D-D Admin Frontend (role-gated Admin nav item and pages already existed from Phase 8D - `admin/users`/`admin/audit-logs` already real; this sub-phase replaces the remaining two placeholders over 7D-C's endpoints: `admin/system-health` (`GET /admin/system`, ok/down badges + today's stat tiles + two confirmation-gated maintenance actions) and `admin/signal-statistics` (`GET /admin/signals` paginated table + `GET /admin/analytics` DAU tile and a plain-CSS proportion bar, no chart library, ADR-131); `admin/page.tsx` dashboard extended with a compact system-status summary; `admin/api-usage`/`admin/settings` deliberately left untouched; ADR-118, ADR-131; docs/58) - Completed **(Phase 7D complete)**

7D-E+ Session/device-management UI, Watchlists alerts/tags/pinning/AI summary, Admin system telemetry/feature flags, Subscription - Not Started (still deferred, see docs/58 §5)

---

# Phase 7E

AI Pipeline Activation

Real Providers

Automatic Signals

Telegram

Status

In Progress

Sub-Phases

7E-A Live Market Data + AI Reasoning Activation (`TwelveDataProvider`/`OpenAIProvider` already existed - Phase 3B/6A - config-only activation: `celery beat` service added to `docker-compose.yml`, `MARKET_DATA_PROVIDERS`/`OPENAI_API_KEY` to be set by the operator; no code changed) - In Progress (blocked on real API keys being supplied to `backend/.env`)

7E-B Real News + Economic Calendar Providers (`NewsApiProvider`/`FinnhubProvider`, same `providers/base.py` Protocol shape as `TwelveDataProvider` - zero changes to `NewsSentimentEngine`/`EconomicCalendarEngine`/ingestion pipelines) - Completed (code); activation blocked on `NEWS_API_KEY`/`ECONOMIC_API_KEY`

7E-C Automatic Signal Generation (`app/workers/signal_tasks.py`, hourly Celery Beat task over the active/seeded asset set on H1, calling `SignalEngine.generate()` - the exact path `POST /signals/generate/{symbol}` already used, zero new decision logic) - Completed

7E-D Telegram Automation - Signal Delivery Only (`telegram_accounts` table, `app/services/telegram/` provider abstraction + `TelegramService`, `POST/GET/DELETE /telegram/link(+status)`, `send_signal_telegram_task` hooked into both the on-demand and automatic signal-generation paths; docs/57_TELEGRAM_ARCHITECTURE.md, ADR-110 through ADR-113. Explicitly narrower than docs/19/20's full vision - bot commands, quiet hours, email/in-app channels, notification preferences, and admin escalation are deferred, docs/57 §8) - Completed (code); activation blocked on a freshly-created `TELEGRAM_BOT_TOKEN` (the token pasted into this project's chat history is compromised and must not be reused)

---

# Phase 8

Admin User Management

Status

Proposed - Architecture Complete, Awaiting Approval

Sub-Phases

8A Architecture & Design (docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md - database
impact, backend/frontend architecture, full API spec, RBAC design, registration-removal
migration path, security review; supersedes ADR-116's user-management scope decision,
extends ADR-115/ADR-118 unchanged; ADR-119 through ADR-124) - Completed and Approved
2026-08-05 (architecture only, no code)

8B Authorization (`require_role`/`require_admin`/`require_super_admin`/`require_permission`,
`Permission`/`ROLE_PERMISSIONS` (ADR-122), `app/dependencies/rbac.py`, extends
`get_current_user` without modifying it; `User` gains `deleted_at`/`must_change_password`/
`created_by_admin_id` via migration `f3a9c1d2e5b7`, ADR-120; 19 new tests,
`tests/test_rbac.py`) - Completed (authorization layer + schema only; no admin routes/
service/frontend yet - those are 8C/8D)

8C User Management (list/search/filter/pagination/create/edit/disable/activate/
reset-password/soft-delete/role-change over `/admin/users*` (9 endpoints),
`AdminUserService`, `UserRepository` filtering/soft-delete methods,
`AuthenticationService.login` now rejects `deleted_at`-set accounts, `UserService.
register_user` extended additively for admin-created accounts (role/must_change_password/
created_by_admin_id); 55 new tests across service/API/auth-integration layers) -
Completed

8D Frontend (role-gated Admin nav group + 7 pages - Dashboard/Users/Audit Logs/System
Health/API Usage/Signal Statistics/Settings; Users page is full CRUD - search/filter/
pagination/sort, Add/Edit/Reset-Password/Change-Role dialogs, Disable/Enable/Delete
confirmations, role-aware action visibility; Dashboard composed client-side from real
`GET /admin/users` calls, no fake data; the four pages with no Phase 8C backend
(Audit Logs/System Health/API Usage/Signal Statistics) ship as honest placeholders,
same ADR-103 precedent as Watchlists; new `AlertDialog` primitive (`@radix-ui/
react-alert-dialog`), `apiPatch` added to `api-client.ts`; verified via `npm run
typecheck`/`lint`/`build` only - no live browser screenshots, no admin account exists
yet pending Phase 8E's bootstrap script) - Completed

8E Registration Removal (`settings.allow_public_registration=False` by default,
`POST /auth/register` returns `403 registration_disabled`; `/register` redirects
unconditionally to `/login` rather than an informational stub - explicit instruction
superseded docs/59 §9's original ADR-100-precedent sketch; every register link/footer
removed from the frontend; `backend/scripts/create_admin.py` bootstraps the first
Super Admin, ADR-123, refuses a second run; docs/23 §3 updated to describe the new
flow; 6 new backend tests) - Completed

8F Audit Logs (no new schema - the write side already existed, Phase 2B's
`AuthenticationService` and Phase 8C's `AdminUserService`; this phase adds only
the read side: `AuditLogRepository.list_admin`/`count_admin`,
`UserRepository.list_by_ids` for batch actor resolution, read-only
`AdminAuditLogService`, `GET /admin/logs` mirroring `GET /admin/users`'
pagination convention, and a real `AdminAuditLogsPage` replacing the Phase 8D
placeholder; docs/59 §11, ADR-129) - Completed

**Note:** this phase number was previously an empty placeholder reserved for
"Analytics, Reporting, Monitoring, Logging" (no sub-phases, nothing built). That content
is relocated to Phase 12 below, so it isn't lost, since Admin User Management is the
work actually requested and scoped under the "Phase 8" name. Phase 12 is this
document's final section - it appears further down, after Phase 10, Phase 11, and
Long-Term Vision, in that order.

---

# Phase 9

Broken down 2026-08-06 into four sub-phases - see
`docs/60_PHASE_9_HARDENING_ARCHITECTURE.md` for the full architecture,
scoping, and reasoning behind each.

- **9A Public Surface Protection** - **in progress.** Correct client-IP
  resolution behind the production reverse proxy, per-IP rate limiting on
  the ten previously-unlimited public routes, CORS scoped down, baseline
  security headers.
- **9B Auth Hardening** - **complete.** Disabled/deleted users are now
  cut off at their next authenticated request (`get_current_user`), not
  just at login; failed-login lockout (schema-only, no Redis); the
  `login()` user-enumeration timing oracle fixed; `jti` access-token
  denylist decided against for now, deferral reasoning updated
  (ADR-133).
- **9C Testing Foundation** - **complete.** Playwright E2E (Chromium) on
  the six core flows (auth, watchlists CRUD, admin user management,
  admin maintenance actions, role gating, a 9A rate-limit/CORS
  regression guard), against a dedicated seeded `e2e.db`; `pytest-cov`
  configured, measured at 93% (no threshold gate yet). CI integration
  deliberately deferred to a follow-up (ADR-134, docs/60 §7).
- **9D Measurement** - **complete.** `GET /metrics` (Prometheus text
  format via `prometheus_client`): request count/latency labeled by
  route *template* (never raw path - unbounded-cardinality guard,
  verified directly), plus the client library's default process/GC
  collectors. Fail-closed 404 access control (empty token = endpoint
  doesn't exist), excluded from 9A's rate limiting and from its own
  metrics (ADR-136, docs/60 §8). Unblocks `GET /admin/system`'s
  telemetry limitation (ADR-116). Celery worker/queue metrics and
  surfacing this in the Admin UI remain open (BACKLOG.md §3) -
  Performance/Optimization can now be scheduled against a real number.
- **9E Signal Entry Confirmation** - **complete.** Fixed a live
  production defect: signals closed as losses without price ever
  reaching `entry_price`. `TRIGGERED` (ADR-088's reserved state) is now
  wired up with a touch-based trigger rule; SL/TP only evaluated once
  `TRIGGERED`; a separate `signal_triggered_ttl_hours` closes a live
  trade that never resolves; `_has_open_signal`'s dedup gate now also
  treats `TRIGGERED` as open (ADR-125/137). Also: per-market Telegram
  price precision (5dp forex, 3dp JPY pairs, was a hardcoded 2dp for
  every asset), and the hourly generation interval moved from a module
  constant to a `.env`-tunable setting.
- **9F Admin Symbol Management** - **complete.** Admin CRUD (minus hard
  delete) for `Asset`, the single control point for three production
  pipelines (market data collection, hourly AI signal generation, news
  matching) - deactivating a symbol stops all three immediately, no
  deploy needed, making this the operational cost/blast-radius lever
  for the whole automated system. Symbol immutable after creation
  (natural key for all price/indicator/SMC history); no hard delete
  (cascading history); every mutation audited (ADR-138). New Admin
  Assets page reusing existing table/filter-bar/dialog components, no
  new UI primitives.
- **9G Ingestion Health** - **complete.** Fixed a live production
  defect: News/Economic Calendar provider failures only ever logged a
  `warning` and returned an empty result, indistinguishable from
  "nothing to ingest" - production ran with zero news articles and a
  silently-mocked calendar with nothing surfacing either. Both
  pipelines now return a per-provider result object and raise
  (`AllNewsProvidersFailedError`/`AllEconomicCalendarProvidersFailedError`,
  both pre-existing but previously unraised) if every provider fails -
  Celery reports FAILED, not a clean success. `GET /admin/system` gains
  per-pipeline provider name(s), mock-usage flag, last success, and
  last error (Redis-backed, fail-open, no migration). Startup logging
  makes mock usage explicit; a new manual `diagnose_ingestion.py`
  script lets the operator test the real production network/auth path
  with exactly one call per provider (ADR-139).

---

# Phase 10

Beta Release

Internal Testing

Feedback

Iteration

---

# Phase 11

Public Launch

Marketing

Documentation

Support

Community

---

# Long-Term Vision

Portfolio Management

Backtesting

Mobile Apps

Copy Trading

Broker Integrations

Marketplace

Enterprise Platform

AI Strategy Builder

Autonomous Research Agents

---

# Phase 12

Analytics

Reporting

Monitoring

Logging

Relocated from the original "Phase 8" placeholder when that number was reassigned to
Admin User Management (see Phase 8's note above) - unchanged content, no sub-phases
defined yet, nothing built.