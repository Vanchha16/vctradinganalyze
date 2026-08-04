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

7D+ Admin, session/device-management UI, Watchlists CRUD backend, Subscription - Not Started

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

Analytics

Reporting

Monitoring

Logging

---

# Phase 9

Performance

Security

Testing

Bug Fixes

Optimization

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