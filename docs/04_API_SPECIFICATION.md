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

Return supported assets.

Example

EURUSD

GBPUSD

BTCUSD

XAUUSD

NAS100

US30

---

GET /assets/{symbol}

Return asset details.

---

# Market Data

GET /market/{symbol}

Query

timeframe=H1

Response

OHLC

Volume

Spread

---

GET /market/{symbol}/candles

Parameters

timeframe

limit

from

to

---

# Technical Analysis

GET /analysis/technical/{symbol}

Returns

EMA

RSI

MACD

ADX

ATR

VWAP

Support

Resistance

Trend

---

# Smart Money Concepts

GET /analysis/smc/{symbol}

Returns

Order Blocks

FVG

Liquidity

CHOCH

BOS

Mitigation

Breaker

Premium Discount

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