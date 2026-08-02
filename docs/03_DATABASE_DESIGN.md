# Database Design

Version: 1.0

Database: PostgreSQL 17+

---

# 1. Design Principles

The database must be:

- Normalized (3NF where practical)
- Optimized for read-heavy workloads
- Support horizontal scaling
- Audit-friendly
- Soft-delete capable where appropriate
- Migration-friendly with Alembic

All tables must include:

- UUID primary key
- created_at
- updated_at

Use UTC timestamps.

---

# 2. Core Domains

The database is divided into the following domains:

Authentication

Users

Subscriptions

Market Data

Trading Signals

AI Analysis

News

Economic Calendar

Notifications

Watchlists

Audit Logs

System Configuration

---

# 3. Authentication

## users

Purpose:

Stores user accounts.

Fields:

id

email

username

password_hash

full_name

avatar_url

is_active

is_verified

role

timezone

language

last_login

created_at

updated_at

---

## user_sessions

Purpose:

Track active sessions.

Fields:

id

user_id

refresh_token_hash

device

ip_address

user_agent

expires_at

created_at

---

## oauth_accounts

Purpose:

Google OAuth and future providers.

Fields:

id

user_id

provider

provider_user_id

access_token

refresh_token

created_at

---

# 4. Subscription

## plans

Fields:

id

name

price

currency

billing_cycle

signal_limit

features

created_at

---

## subscriptions

Fields:

id

user_id

plan_id

status

starts_at

expires_at

renewal_date

created_at

---

## invoices

Fields:

id

subscription_id

amount

currency

status

payment_provider

transaction_reference

paid_at

created_at

---

# 5. Market Data

## assets

Examples:

EURUSD

GBPUSD

XAUUSD

BTCUSD

US30

NAS100

Fields:

id

symbol

name

market_type

exchange

base_currency

quote_currency

is_active

created_at

---

## price_candles

Stores OHLCV.

Fields:

id

asset_id

timeframe

timestamp

open

high

low

close

volume

Indexes:

(asset_id, timeframe, timestamp)

---

# 6. Technical Analysis

## indicator_results

Fields:

id

asset_id

timeframe

indicator

value

metadata

calculated_at

---

# 7. Smart Money Concepts

## smc_events

Fields:

id

asset_id

timeframe

event_type

price

strength

metadata

detected_at

Examples:

BOS

CHOCH

FVG

Order Block

Liquidity Sweep

Mitigation

Breaker Block

---

# 8. News

Phase 5A (docs/46_NEWS_SENTIMENT_ARCHITECTURE.md, ADR-052/ADR-053) resolves the mixin/timestamp gap this section previously left contradicting §1: `news_sources` uses `TimestampMixin` (mutable, admin-managed), `news_articles` uses `CreatedAtMixin` + its own `published_at` (append-only once ingested), `news_sentiment` uses `TimestampMixin` (recomputable on re-scoring).

## news_sources

Fields:

id

name

website

tier (Tier1/Tier2/Tier3, per docs/10 §3)

priority

is_active

created_at

updated_at

---

## news_articles

Fields:

id

source_id

title

summary

content (nullable, full body if provided by the source)

url (unique, indexed - dedup exact-match key)

category (12 values, per docs/10 §5)

published_at

language

importance

created_at

---

## news_sentiment

Fields:

id

article_id (unique FK - one sentiment row per article, ADR-052)

sentiment (Very Bullish/Bullish/Neutral/Bearish/Very Bearish - enum only, no free-text variant)

confidence

reason

affected_assets (JSON list of asset symbols)

ai_summary (nullable - populated only when the AI summary call succeeds, ADR-051)

created_at

updated_at

---

# 9. Economic Calendar

Phase 5B (docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md, ADR-057/ADR-058) resolves the mixin/timestamp gap this section previously left contradicting §1, and adds the fields docs/14's classification/scoring output requires. `economic_events` uses `TimestampMixin` (mutable - `actual`/`surprise`/`status` update in place as an event moves through its lifecycle, ADR-058), not a separate sources table (ADR-057 - `source` is a plain column, since this domain has no source-credibility-tier axis unlike News).

## economic_events

Fields:

id

country (ISO 3166-1 alpha-2)

currency (ISO 4217)

event_name

category (7 values, docs/14 §3, per ADR-059)

importance (renamed from `impact`; 4 values, distinct from `NewsImportance` per ADR-059/ADR-048)

forecast (nullable)

previous (nullable)

actual (nullable - null until released)

surprise (nullable - `actual - forecast`, stored once known)

unit (nullable - e.g. `%`, `K`, `B`)

status (SCHEDULED / RELEASED / REVISED / CANCELLED)

source (provider name)

release_time

created_at

updated_at

Unique natural key: `(country, currency, event_name, release_time)` - upsert target (ADR-058). Indexes: `(currency, release_time)`, `(importance, release_time)`.

Not persisted (computed at read time, ADR-061): `risk_window`. Not persisted (computed at read time, ADR-060): `market_bias`.

---

Phase 5C (docs/48_RISK_MANAGEMENT_ARCHITECTURE.md, ADR-063) - the Risk Management Engine is stateless and owns no table of its own. `risk_level`/`entry_price`/`stop_loss`/`take_profit` below are where its evidence eventually lands, once Phase 6/7 build `ai_analysis`/`signals` and start writing to them - not a table Risk Management persists to itself.

Phase 5D (docs/49_STRATEGY_ARCHITECTURE.md, ADR-070) - the Strategy Engine is likewise stateless and owns no table. `recommendation`'s eventual "which strategy was selected" provenance is future evidence for `ai_analysis`, not a Strategy Engine table of its own.

# 10. AI Analysis

Phase 6A (docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md, ADR-082) - `ai_analysis` is the first genuinely persisted engine output in this project (every Phase 4/5 engine is stateless because deterministic code reproduces identical results on replay; an LLM call does not). Uses `CreatedAtMixin` (not `TimestampMixin`) - resolves §1's created_at/updated_at contradiction the same way `news_articles` did (ADR-053): an analysis row is "what was recommended at time X," never rewritten in place. `market_context`/`technical_summary`/`smc_summary`/`news_summary`/`economic_summary` (docs/03 v1.0's original field list) are superseded by the structured `reasoning` object below, which covers the same narrative ground per section without duplicating it as five separate free-text columns.

## ai_analysis

Stores every AI response. Every field except `reasoning` is deterministic - reused verbatim from an existing engine or computed by a new deterministic module (docs/50 §6); the LLM's only output is `reasoning`'s narrative text.

Fields:

id

asset_id

timeframe

recommendation (BUY / SELL / WAIT - computed deterministically, never by the AI, ADR-078)

confidence_score (reused from `AnalysisConfidenceEngine`, never recomputed, ADR-079)

confidence_level

risk_level (reused from `RiskManagementEngine`, nullable if no candidate setup was built, ADR-079)

entry_price (nullable - null for WAIT)

stop_loss (nullable - null for WAIT)

take_profit (nullable - null for WAIT)

execution_guidance (reused from `RiskManagementEngine.position_guidance`)

reasoning (JSON - seven narrative sections: summary/technical/smc/economic/news/risk/conclusion; the only AI-generated field)

supporting_evidence (JSON list - deterministic)

conflicting_evidence (JSON list - deterministic, sourced from `ConfidenceResult.conflicts`)

risks (JSON list - deterministic)

invalidation_conditions (JSON list - deterministic template)

model_name

prompt_version

ai_available (bool - was the LLM call successful, or is `reasoning` the deterministic template fallback)

latency_ms

warnings (JSON list)

created_at

---

# 11. Trading Signals

Phase 6B (docs/51_SIGNAL_ARCHITECTURE.md, ADR-085 through ADR-091). `signals` uses `CreatedAtMixin` (ADR-091, an inferred addition beyond this section's original field list, which specified no timestamp at all) - a row is only ever created for a BUY/SELL outcome (ADR-086), never for WAIT. `status` is written as `ACTIVE` and never mutated by Phase 6B; `triggered_at`/`closed_at`/`profit_loss` stay null until a future phase builds live price-monitoring (ADR-088).

## signals

Fields:

id

analysis_id

asset_id

timeframe

signal_type (BUY / SELL only, ADR-086)

entry_price

stop_loss

take_profit (single value - TP1/TP2/TP3 deferred, ADR-087)

risk_reward

confidence

status (only ACTIVE is ever written by Phase 6B; EXPIRED is computed at read time, never stored, ADR-088)

triggered_at (nullable, unpopulated by Phase 6B)

closed_at (nullable, unpopulated by Phase 6B)

profit_loss (nullable, unpopulated by Phase 6B)

created_at (ADR-091)

---

## signal_bookmarks

Inferred, not in this document's original schema (ADR-090) - required by `POST/DELETE /signals/bookmark`.

Fields:

id

user_id

signal_id

created_at

Unique constraint: `(user_id, signal_id)`.

---

# 11A. AI Chat Assistant

Phase 6C (docs/52_AI_CHAT_ARCHITECTURE.md, ADR-096). Inferred - not in this document's original schema.

## conversations

`TimestampMixin` (not `CreatedAtMixin` - `title`/`current_symbol`/`current_timeframe`/`status` all mutate after creation).

Fields:

id

user_id

title (nullable, auto-derived from the first user message)

current_symbol (nullable - mutable "current focus," docs/52 §5/ADR-095)

current_timeframe (nullable)

status (`active` / `archived`, ADR-097)

created_at

updated_at

---

## messages

`CreatedAtMixin` (append-only - a sent message is never edited).

Fields:

id

conversation_id

role (`user` / `assistant`)

content

symbol (nullable - this message's own immutable "referenced" scope, ADR-095)

timeframe (nullable)

ai_analysis_id (nullable, `ON DELETE SET NULL` - the analysis this reply grounded itself in, if any)

signal_id (nullable, `ON DELETE SET NULL` - the signal this reply grounded itself in, if any)

model_name (nullable, `null` for `user` rows)

prompt_version (nullable, `null` for `user` rows - mirrors `ai_analysis.prompt_version`, ADR-018)

created_at

---

# 12. User Watchlists

## watchlists

Fields:

id

user_id

name

created_at

---

## watchlist_items

Fields:

id

watchlist_id

asset_id

created_at

---

# 13. Notifications

## notifications

Fields:

id

user_id

title

message

type

is_read

created_at

---

## telegram_subscriptions

Fields:

id

user_id

telegram_chat_id

is_enabled

created_at

---

# 14. Audit Logs

## audit_logs

Purpose:

Track important actions.

Fields:

id

user_id

action

resource

resource_id

ip_address

metadata

created_at

---

# 15. System Settings

## system_settings

Fields:

id

key

value

description

updated_at

---

# 16. Relationships

users
 ├── subscriptions
 ├── watchlists
 ├── notifications
 ├── sessions
 ├── oauth_accounts
 └── telegram_subscriptions

assets
 ├── price_candles
 ├── indicator_results
 ├── smc_events
 ├── ai_analysis
 └── signals

news_sources
 └── news_articles
      └── news_sentiment

ai_analysis
 └── signals

plans
 └── subscriptions

---

# 17. Indexing Strategy

Create indexes for:

- email
- username
- asset_id
- timeframe
- timestamp
- recommendation
- confidence_score
- release_time
- published_at
- signal_type
- status

Use composite indexes for:

(asset_id, timeframe)

(asset_id, timestamp)

(user_id, created_at)

---

# 18. Data Retention

Price candles:

- Keep raw intraday data for 2 years.
- Archive older data.

AI analysis:

- Keep indefinitely.

Audit logs:

- Keep for 5 years.

Notifications:

- Delete after 90 days.

---

# 19. Future Expansion

Reserved for:

- Broker integrations
- Portfolio tracking
- Backtesting
- Copy trading
- Mobile devices
- AI strategy marketplace
- Multi-tenant organizations