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

## news_sources

Fields:

id

name

website

priority

is_active

---

## news_articles

Fields:

id

source_id

title

summary

url

published_at

language

importance

---

## news_sentiment

Fields:

id

article_id

sentiment

confidence

ai_summary

processed_at

---

# 9. Economic Calendar

## economic_events

Fields:

id

country

currency

event_name

impact

forecast

previous

actual

release_time

status

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