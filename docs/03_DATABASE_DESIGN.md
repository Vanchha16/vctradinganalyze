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

# 10. AI Analysis

## ai_analysis

Stores every AI response.

Fields:

id

asset_id

timeframe

market_context

technical_summary

smc_summary

news_summary

economic_summary

recommendation

confidence_score

risk_level

entry_price

stop_loss

take_profit

reasoning

model_name

analysis_version

created_at

---

# 11. Trading Signals

## signals

Fields:

id

analysis_id

asset_id

signal_type

entry

stop_loss

take_profit

risk_reward

confidence

status

triggered_at

closed_at

profit_loss

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