# 62 — Cloud Execution: Subscribers Connect a Broker Account and Trade the Signals

**Status: PROPOSED (design only).** Written 2026-11-03 for ADR-187. Nothing
here is built or deployed. Until ADR-187 is accepted, ADR-161 still binds:
the server holds no broker credentials and has no order path.

## 1. Goal

A subscriber opens our app, connects their MT5 broker account, and the
platform places and manages orders on that account following our signals.
This works without a Windows server or a running MT5 terminal, the way
Elirox-type apps work.

**Non-goals for this version:**

- Platforms other than MT5.
- Symbols other than XAUUSD.
- Grid, DCA or martingale behaviour.
- Percentage-risk sizing.
- Modifying or closing a filled position.

## 2. Preconditions (none of these is engineering work)

| # | Gate | Before |
|---|---|---|
| G1 | **Legal advice.** Placing trades on other people's accounts is regulated in most jurisdictions (Cambodia: likely the SERC). Get written advice on licensing, disclosures, terms and liability. | any subscriber trades a **live** account |
| G2 | **Profit gate on new live signals.** Suggested: at least 60 distinct filled signals counted from ADR-187's acceptance, net R > 0 after spread, profit factor ≥ 1.20, positive in both halves. The operator sets the final numbers in ADR-187. | any **live** order, including the operator's |
| G3 | **MetaApi commercial check:** current plan, per-account metering, terms for third-party (subscriber) accounts, and data-processing location. | Phase 2 |
| G4 | **Security review** of this design (§9) by someone other than the author. | Phase 3 code reaches production |

Demo accounts may be used freely from Phase 2 onward. They are how the
system is proven.

## 3. Why MetaApi, and what is reused

- **MetaApi.cloud** runs a cloud MT5 terminal per connected account. The
  provisioning API creates the account from MT5 login, password and server.
  The trade API places and manages orders.
  - The codebase already depends on `metaapi-cloud-sdk` and has a provider
    (`services/execution/providers/metaapi.py`) behind the
    `OrderExecutionProvider` protocol.
  - The provider stays swappable. An alternative REST bridge can replace
    it without touching the executor.
- **Reused from the EA path (ADR-161/170/171/184):**
  - **Signal rules:** act only on `active` signals, at most once per signal
    per account; skip when price is already past the stop or target; limit
    order while price has not reached entry, market at or better once it
    has; broker-side expiry = signal expiry; cancel unfilled orders when the
    signal leaves the feed.
  - **Account controls:** fixed lot; daily loss limit; max open trades;
    dry run first; a one-live-order canary.
- **Replaced from the 2026-08 executor** (ADR-161 review findings):
  - it could not cancel → cancel and expiry are required;
  - it had no switch or UI → switches and screens;
  - it risked 3% of the balance → fixed lot;
  - it served one account from `.env` → per-subscriber connections.
  - Its "a fill rewrites the signal's status" fork (`BrokerOrder` →
    `reconcile_signal`) must **not** be used. One subscriber's fill can
    never change the signal everyone sees.

## 4. Architecture

```
Subscriber app (PWA / APK)
   │  connect broker, settings, positions, history
   ▼
Backend API ── broker_connections, copy_orders, copy_events (our DB)
   │                      ▲
   │ provisioning +        │ reconciliation (poll)
   │ trade calls           │
   ▼                      │
MetaApi.cloud ── cloud MT5 terminal per account ── Broker (e.g. Exness)

Signal pipeline (unchanged) ──► signal ACTIVE/CANCELLED/EXPIRED
   └─► copy.fan_out task ──► per-connection copy.execute (idempotent)
```

- **The signal pipeline is untouched.** Execution listens to signal state
  changes only (draft confirmed → ACTIVE; ACTIVE → CANCELLED/EXPIRED).
- **One Celery task per (signal, connection),** idempotent through a unique
  key. A slow or broken account never delays the others.

## 5. Data model (new tables; the existing `signals` table is unchanged)

**`broker_connections`** — one per connected MT5 account.

- **Identity:**
  - `id`, `user_id`
  - `provider` (`metaapi`), `provider_account_id`
  - `broker_server`, `login_hint` (last 3 digits)
  - `account_kind` (`demo` / `live`, **as the broker reports it**, never as
    the user claims)
  - `currency`
- **State:**
  - `state`: `connecting` / `connected` / `error` / `paused` /
    `disconnected`, with `state_reason`
- **Settings:**
  - `enabled`
  - `mode` (`dry_run` / `live`); new connections start in `dry_run`
  - `lot_size`, capped by the platform's `copy_max_lot`
  - `max_open_trades` (default 1)
  - `daily_loss_limit`
  - `symbols` (XAUUSD)
- **Live consent:**
  - `live_confirmed_at`, `risk_disclosure_version` — the subscriber's
    explicit consent to live mode
- **Timestamps:** `created_at`, `updated_at`

**`copy_orders`** — one per (signal, connection). Unique on
`(connection_id, signal_id)`.

- `state`:
  - `planned` → `dry_run` | `placed` | `skipped` | `rejected`
  - `placed` → `filled` | `cancelled` | `expired`
  - `filled` → `closed`
- **Order:** `order_type` (limit/market), `volume`, `requested_price`,
  `stop_loss`, `take_profit`, `expires_at`
- **Broker ids and outcome:** `provider_order_id`, `provider_position_id`,
  `fill_price`, `close_price`, `close_reason` (tp / sl / manual /
  stop_out), `profit` (account currency), `r`
- **Diagnostics:** `reason` (why skipped or rejected), `attempts`

**`copy_events`** — append-only audit. Every placement, cancel, fill, close,
error, setting change and kill-switch use, with actor and timestamp. It
never holds credentials.

**Credentials:**

- **The MT5 password is never stored, logged or returned.** It is forwarded
  once, over TLS, to MetaApi's provisioning API, then discarded. The request
  body is excluded from logs and error reports.
- **The platform's MetaApi API token** is a platform secret, stored
  encrypted at rest (ADR-156 credential store).
- **Disconnect** undeploys and deletes the MetaApi account, then marks the
  connection `disconnected`.

## 6. Execution rules (per connection, per signal)

1. **Preconditions.**
   - Global `copy_trading_enabled` is on.
   - The connection is `enabled` and `connected`.
   - The symbol is allowed and the signal is `active`.
   - No `copy_orders` row exists yet (idempotent).
2. **Account checks.**
   - Open trades are below `max_open_trades`.
   - Today's realised loss is above `-daily_loss_limit`.
   - The account has margin for `lot_size` (MetaApi margin check).
   - Otherwise `skipped` with the reason.
3. **Price checks.**
   - If price is already past the stop or target → `skipped`.
   - If price has not reached entry → **limit order** at entry, with
     broker-side expiry = signal `expires_at`.
   - If it has → **market order** at or better than entry; stop and target
     are attached.
4. **Mode.**
   - `dry_run`: record the exact order that would be sent (`dry_run`
     state) and stop.
   - `live`: also requires the global `copy_live_allowed` (G1 + G2) and the
     connection's `live_confirmed_at`.
5. **Cancellation.**
   - When the signal leaves `active` (cancelled, replaced, expired),
     cancel every unfilled `placed` order for it.
   - Never cancel because a request failed. Only a confirmed signal state
     means "gone" (ADR-161 §4).
6. **Never** modify or close a filled position. The broker-side stop and
   target exit it. The subscriber may close it by hand; that is recorded
   as `manual`.
7. **Failures.**
   - **Transient:** retried with backoff, bounded.
   - **Permanent:** `rejected` with the broker's reason.
   - **Repeated failures auto-pause** the connection (`paused`, reason),
     and the subscriber is told.

## 7. Reconciliation

- **A poll task every 2 minutes per connected account.** It reads open
  orders, positions and recent deals and moves `copy_orders` through
  `filled` / `closed` with prices and profit.
  - Polling first, because MetaApi meters usage. Streaming is a later
    optimisation once costs are known (G3).
- **Orders the platform did not place are ignored.** They are identified
  by order comment `VC-<copy_order id>`, like the EA's `COMMENT_PREFIX`.
- **Drift is a `copy_events` alert:** an order we think is placed but
  MetaApi does not have, or a position without a row.

## 8. Controls and notifications

- **Global runtime settings** (admin page, audited):
  - `copy_trading_enabled` (default off)
  - `copy_live_allowed` (default off; flipped only after G1 + G2)
  - `copy_max_lot`
  - `copy_canary` — the first live order platform-wide must be confirmed
    by the operator, as in ADR-184
- **Kill switches:**
  - global off cancels all unfilled platform orders;
  - per user and per connection (pause / disable).
- **Per-subscriber notifications** (Telegram to *their own* linked chat,
  plus in-app): connected, order placed, filled, closed (with P&L),
  skipped (with reason), paused, errors. These are personal, never
  broadcast.

## 9. Security (for G4)

- **The worst case** is a bug or a leaked MetaApi token placing orders on
  every connected account.
- **Mitigations:**
  - the token never leaves the backend;
  - no endpoint takes an arbitrary order — only the signal-driven executor
    places orders;
  - per-connection lot cap and daily loss limit are enforced server-side
    before every call;
  - a global kill switch;
  - an alert on anomalous order counts per hour.
- **Subscriber-facing endpoints:**
  - authenticated;
  - ownership-checked on every connection id;
  - rate-limited (connect is expensive at MetaApi).
- **MT5 password handling** (§5): never stored or logged. A test asserts
  that no log record or exception contains the submitted password.
- **Audit:** every state change and setting change goes to `copy_events`
  and `audit_logs`.

## 10. App

- **The existing Next.js site becomes installable (PWA):** manifest, icons,
  service worker and web push.
- **New screens:**
  - Connect broker (MT5 login, password, server, with a demo/live notice)
  - Copy settings (on/off, mode, lot, max trades, daily loss limit)
  - Open trades
  - History with P&L
  - Live-mode consent (risk disclosure)
- **An Android APK** (Trusted Web Activity wrapping the PWA) is a later
  step, if Play Store distribution is wanted.

## 11. Phases (each stops for operator review)

| Phase | Scope | Done when |
|---|---|---|
| 1 | ADR-187 + this document | operator accepts or amends ADR-187 |
| 2 | **Spike on a MetaApi demo account:** provision, limit/market orders with SL/TP, broker-side expiry, cancel, read positions and deals, undeploy and delete. Measure metered cost per account per day. | every §6 operation proven on demo; cost known (G3) |
| 3 | Tables + migration, provider extension (cancel, expiry, market, deals), executor, reconciliation, kill switches, audit, dry run only. Tests and CI green. | dry run on the operator's demo matches the signals for 2 weeks |
| 4 | Connect/settings/positions/history screens, per-user notifications, PWA | a subscriber can connect a demo account end to end |
| 5 | Demo forward test, several accounts | 4+ weeks with no reconciliation drift |
| 6 | Live, in order: operator tiny lot (canary) → subscribers | only after G1 + G2, each step approved |

## 12. Open questions for the operator

1. The G2 numbers (minimum trades, profit factor) and who confirms them.
2. Which subscribers are eligible (role, plan) and whether copy trading is
   a paid feature.
3. Default and maximum lot. Whether lot may scale with balance later (not
   in this version).
4. Behaviour when a subscriber's daily loss limit is hit (skip the rest of
   the day: proposed).
5. Who pays MetaApi per-account costs (platform or subscriber).
6. Data-protection and terms-of-service text (with G1).
