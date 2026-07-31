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

# News

GET /news

Parameters

page

limit

importance

currency

---

GET /news/{id}

Return article details.

---

# News Sentiment

GET /analysis/news/{symbol}

Response

Bullish

Bearish

Neutral

Confidence

AI Summary

---

# Economic Calendar

GET /economic/events

Parameters

country

currency

impact

date

---

GET /economic/upcoming

Upcoming high-impact events.

---

# AI Analysis

POST /analysis/ai

Request

{
    "symbol":"EURUSD",
    "timeframe":"H1"
}

Response

{
  "recommendation":"BUY",
  "confidence":87,
  "entry":1.17540,
  "stop_loss":1.17120,
  "take_profit":1.18150,
  "risk":"Medium",
  "reasoning":[]
}

---

GET /analysis/history

User AI history.

---

GET /analysis/{id}

Return complete AI report.

---

# Signals

GET /signals

Latest signals.

---

GET /signals/{id}

Signal details.

---

POST /signals/bookmark

Bookmark signal.

---

DELETE /signals/bookmark/{id}

---

# Watchlists

GET /watchlists

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

GET /admin/system

GET /admin/logs

GET /admin/analytics

POST /admin/news

POST /admin/maintenance

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

Internal monitoring.

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