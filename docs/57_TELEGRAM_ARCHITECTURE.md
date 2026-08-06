# Telegram Architecture

# 1. Scope

`docs/19_TELEGRAM_BOT.md` and `docs/20_NOTIFICATION_SYSTEM.md` are Phase-0
vision documents describing a full multi-channel notification system: email,
in-app, Telegram, quiet hours, per-type user preferences, deduplication, a
retry/backoff queue, ten-plus bot commands, and admin escalation. None of that
exists in this codebase yet - no models, no service directory, no routes, only
a `TELEGRAM_BOT_TOKEN` placeholder in `.env.example`.

This phase narrows that vision to exactly one slice, matching the requested
pipeline (`Signal Generation → Chart Annotation → Telegram Automation`):

**A user links their Telegram account once. From then on, every Signal this
project generates (on-demand via `POST /signals/generate/{symbol}`, or
automatically via `signals.generate_for_watchlist`, `app/workers/signal_tasks.py`)
is delivered to their linked chat as a formatted message.**

Explicitly out of scope for this phase (real docs/19/20 scope, deferred, not
forgotten): `/help`, `/status`, `/signals`, `/analyze`, `/watchlist`, `/settings`
and other bot commands; quiet hours; email/in-app/push channels; per-type
notification preferences; retry queue; admin escalation. ADR-110.

**Deduplication (ADR-125):** `signals.generate_for_watchlist`
(`app/workers/signal_tasks.py`) skips re-running AI orchestration for any
asset that already has an unresolved BUY/SELL call on `Timeframe.H1` -
checked via `_has_open_signal()`, which reuses `status_resolver.effective_status`
(ADR-088) so a stored-ACTIVE-but-TTL-expired row doesn't block a fresh
signal. This is asset+timeframe scoped, not per-user, so it's a generation-time
gate rather than a delivery-time notification preference (the broadcast
model in §5 is unchanged). Without it, the hourly job would re-confirm the
same open call every run and re-broadcast a near-duplicate Telegram
message each time.

---

# 2. Persistence Model

New table `telegram_accounts` (`app/models/telegram_account.py`), `UUIDMixin` +
`CreatedAtMixin`, one row per linked user - mirrors `oauth_account.py`'s shape
(a user linking an external identity to their existing account), not a new
auth mechanism (ADR-111).

| Field | Notes |
|---|---|
| `id` | generated |
| `user_id` | FK to `users`, unique - one Telegram chat per platform account |
| `telegram_chat_id` | nullable until linking completes |
| `link_code` | short random token, unique, set on `POST /telegram/link` |
| `link_code_expires_at` | `POST /telegram/link` time + 10 minutes |
| `linked_at` | nullable; set when `/start <code>` resolves the code |
| `created_at` | row creation time |

A row exists from the moment `POST /telegram/link` is called (code issued,
`telegram_chat_id`/`linked_at` null) through to a completed link. This mirrors
`user_session.py`'s "create the row, then fill in the rest as the flow
progresses" shape rather than inventing a new lifecycle pattern.

---

# 3. Linking Flow (docs/19 §3, ADR-111)

```
User (authenticated, in Settings)
  -> POST /telegram/link
       generates `link_code` (secrets.token_urlsafe, 10 min expiry)
       upserts telegram_accounts row for current_user
       <- { link_code, bot_username }
  -> user opens Telegram, sends "/start <link_code>" to the bot
  -> TelegramProvider webhook/poll receives the update
  -> resolve link_code -> telegram_accounts row (must be unexpired, unlinked)
  -> set telegram_chat_id + linked_at
  -> bot replies "Linked to ClaudeTrading AI as <username>."
```

No new signed-token format: `link_code` is a single-use, short-TTL random
string checked against the stored row, the same class of primitive
`user_session.py`'s refresh tokens already use (ADR-022) - not a JWT, since
nothing needs to be self-verifying here (the code is looked up, not decoded).

---

# 4. Provider Abstraction (ADR-112)

`app/services/telegram/providers/base.py` - a `TelegramProvider` Protocol,
same three-piece shape (`base.py` + `mock.py` + one real implementation) as
every other external integration in this codebase
(`app.services.market_data.providers`, `app.services.news.providers`,
`app.services.economic_calendar.providers`):

```python
class TelegramProvider(Protocol):
    name: str
    def send_message(self, chat_id: str, text: str) -> None: ...
    def get_updates(self, offset: int | None) -> list[RawTelegramUpdate]: ...
    def health_check(self) -> bool: ...
```

`app/services/telegram/providers/bot_api.py` - real implementation against the
Telegram Bot API (`https://api.telegram.org/bot<token>/...`), using long-polling
`getUpdates` (not a public webhook - no HTTPS-reachable public URL exists for
this project yet, and polling matches the low volume of `/start` events this
phase handles). `send_message` uses `parseMode: "MarkdownV2"`.

`app/services/telegram/providers/mock.py` - records sent messages in memory,
never calls the network, for tests (mirrors every other provider's `mock.py`).

Configuration mirrors the existing `xxx_providers`/`xxx_api_key` settings
pattern exactly: `telegram_bot_token: str = ""`, `telegram_providers: list[str]
= ["mock"]`, registered in a new `app/dependencies/telegram.py`
`_PROVIDER_FACTORIES` dict identical in shape to
`app/dependencies/news.py`'s.

**The bot token pasted into this project's chat history earlier is
compromised and must be revoked via @BotFather; a fresh token is required
before this phase can be activated with `telegram_providers = ["bot_api"]`.**

---

# 5. Delivery Path (ADR-113)

```
SignalEngine.generate(asset, timeframe)          [unchanged, docs/51]
  -> Signal persisted (BUY/SELL only, WAIT produces no Signal - ADR-086)
  -> new: send_signal_telegram_task.delay(signal_id)
       [Celery task, app/workers/telegram_tasks.py]
       -> find all telegram_accounts where linked_at is not null
          (Phase 1: broadcast to every linked account - no per-user
          asset/timeframe subscription filtering exists yet; that is
          real docs/20 §6 "user preferences" scope, deferred)
       -> render docs/19 §5's message template from the Signal + its
          linked AIAnalysis (symbol, direction, confidence, entry/SL/TP,
          reasoning bullets from `AIAnalysisResult.supporting_evidence`)
       -> TelegramProvider.send_message(chat_id, text) per linked account
```

This hook is called from exactly two places, both already producing a
`Signal`: `POST /signals/generate/{symbol}` (`app/api/v1/routes/signals.py`)
and `signals.generate_for_watchlist` (`app/workers/signal_tasks.py`). Neither
gains new decision logic - only a `.delay()` call after the existing
`engine.generate()` returns a non-null `signal`.

---

# 6. Message Template (docs/19 §5, verbatim format)

```
📈 {BUY|SELL} {symbol}

Confidence: {confidence_score}%
Entry: {entry_price}
Stop Loss: {stop_loss}
Take Profit: {take_profit}
Risk: {risk_level}

Reason:
• {supporting_evidence[0]}
• {supporting_evidence[1]}
• {supporting_evidence[2]}
```

Every value is read verbatim from the already-persisted `Signal`/`AIAnalysis`
row - no new formatting/scoring logic, matching this project's "AI never
computes the deterministic parts, deterministic code never fabricates the
narrative parts" boundary (ADR-078/079).

---

# 7. New Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/telegram/link` | Authenticated; issues a `link_code`, returns it + the bot's `@username` |
| `GET` | `/telegram/status` | Authenticated; whether the current user has a linked, active Telegram account |
| `DELETE` | `/telegram/link` | Authenticated; unlink (clears `telegram_chat_id`/`linked_at`) |

No public/unauthenticated endpoint receives Telegram traffic in this phase -
`get_updates` is polled outbound by a new Celery Beat task
(`telegram.poll_updates`, short interval, e.g. every 5s while the token is
configured), not an inbound webhook route.

---

# 8. Explicitly Deferred (real docs/19/20 scope, later phase)

- `/help`, `/status`, `/signals`, `/calendar`, `/news`, `/watchlist`,
  `/analyze`, `/profile`, `/settings` bot commands (docs/19 §10)
- Economic alert / breaking news / market summary / AI insight message types
  (docs/19 §6-9) - this phase is Signal delivery only
- Quiet hours, per-type notification preferences, deduplication, retry queue,
  priority levels (docs/20 §4-10)
- Email and in-app channels (docs/20 §2)
- Per-user asset/timeframe subscription filtering (§5 above notes broadcast-
  to-all-linked-accounts as the Phase 1 behavior)
- Admin escalation on critical delivery failure (docs/19 §16)
