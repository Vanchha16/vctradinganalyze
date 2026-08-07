# Signal Architecture

# 1. Scope

Phase 6B's `SignalEngine` (`app/services/signal_engine.py`) is a thin persistence/lifecycle layer over Phase 6A's `AIOrchestratorEngine` - it introduces **zero new evidence weighting, confidence, or recommendation logic** (ADR-085). `docs/11_SIGNAL_ENGINE.md`'s original vision (an independent evidence-collection pipeline with its own Technical 35% / SMC 30% / Economic 15% / News 10% / Risk 10% weight distribution, its own confidence score, its own conflict resolution) predates Phase 4-6's actual implementation and is now **superseded**: `AnalysisConfidenceEngine` (ADR-046) already owns cross-engine confidence weighting, and `AIOrchestratorEngine.generate()` (ADR-078/079/080) already owns the deterministic BUY/SELL/WAIT decision, entry/stop/target construction, and evidence extraction. Rebuilding either would duplicate Phase 6A, contradicting this project's reuse-first precedent (Strategy Engine, ADR-071; Risk Management, ADR-064; AI Orchestrator, docs/50 §4).

What Phase 6B actually adds:

1. A persisted `signals` table (docs/03 §11) turning an `AIAnalysisResult` into a queryable, bookmarkable, lifecycle-tracked trade call - `ai_analysis` rows exist for every generation (including WAIT), but a **signal** is specifically an actionable BUY/SELL call (ADR-086).
2. A minimal status lifecycle: ACTIVE (written at creation) and a read-time-computed EXPIRED (ADR-088) - mirrors Economic Calendar's `risk_window`/`market_bias` computed-property precedent (ADR-060/061), not a stored transition.
3. Read/list/bookmark API surface (`GET /signals`, `GET /signals/{id}`, `POST/DELETE /signals/bookmark/{id}`) plus a new on-demand `POST /signals/generate/{symbol}` (ADR-089, not in docs/04's original draft).

See `docs/11_SIGNAL_ENGINE.md` for the original product-vision document this narrows, and `docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md` for the engine being wrapped.

---

# 2. Persistence Model (ADR-086, ADR-091)

`signals` (`app/models/signal.py`) uses `UUIDMixin` + `CreatedAtMixin` - the same append-only reasoning as `ai_analysis` (ADR-082) and `news_articles` (ADR-053): a signal row represents "what was recommended at time X," never rewritten in place by 6B. `created_at` is an inferred addition beyond docs/03 §11's literal field list (which lists no timestamp at all) - needed both to order `GET /signals`' "latest signals" and to compute TTL-based expiry (ADR-091, same "inferred correctness requirement" pattern as ADR-022/024/032's `status` column on `smc_events`).

A `Signal` row is only ever created for a `Recommendation.BUY` or `Recommendation.SELL` outcome (ADR-086). A `WAIT` recommendation is a valid, fully-formed `AIAnalysisResult` (ADR-011 - WAIT is a valid recommendation) but produces **no** `Signal` row: `entry_price`/`stop_loss`/`take_profit` are null for WAIT (docs/03 §10), and a "signal" is definitionally an actionable trade call, not an abstention.

Fields (docs/03 §11, all sourced from the wrapped `AIAnalysisResult` plus one reused deterministic computation):

| Field | Source |
|---|---|
| `id` | generated |
| `analysis_id` | `AIAnalysisResult.id` (FK to `ai_analysis`, the full reasoning/evidence trail lives there - not duplicated here) |
| `asset_id` | the requested `Asset` |
| `signal_type` | `AIAnalysisResult.recommendation` (BUY/SELL only) |
| `entry_price`, `stop_loss`, `take_profit` | `AIAnalysisResult.entry_price`/`.stop_loss`/`.take_profit` (verbatim, never recomputed) |
| `risk_reward` | `app.services.risk_management.risk_reward_validator.validate()` - reusing the existing pure-arithmetic helper (docs/48 §6) directly, not re-deriving the formula |
| `confidence` | `AIAnalysisResult.confidence_score` (verbatim) |
| `status` | written as `ACTIVE`; `TRIGGERED`/`CANCELLED`/`CLOSED`/`SUCCESSFUL`/`STOPPED_OUT`/`DRAFT` are reserved enum values, not written by 6B (ADR-088) |
| `triggered_at`, `closed_at`, `profit_loss` | nullable, unpopulated by 6B - require live price-monitoring infrastructure that doesn't exist anywhere in this project yet (same class of gap as Risk Management's deferred position tracking, ADR-067) |
| `created_at` | generation time (ADR-091) |

---

# 3. Data Flow

```
SignalEngine.generate(asset, timeframe)
  -> AIOrchestratorEngine.generate(asset, timeframe)   [reused verbatim, docs/50 - one call, persists ai_analysis]
  -> if result.recommendation is WAIT:
       return SignalGenerationResult(analysis_id=result.id, recommendation=WAIT, signal=None)
  -> risk_reward_validator.validate(entry_price, stop_loss, take_profit)   [reused, docs/48 §6]
  -> persist Signal(status=ACTIVE, ...)
  -> return SignalGenerationResult(analysis_id=result.id, recommendation=BUY|SELL, signal=Signal)
```

Read path (`GET /signals`, `GET /signals/{id}`):

```
signal_repository.find_paginated(...) / get_by_id(...)
  -> status_resolver.effective_status(stored_status, created_at, now)   [ADR-088, read-time only, never mutates the row]
  -> SignalResponse
```

`AIOrchestratorEngine` is called **exactly once** per `SignalEngine.generate()` execution - no re-derivation of confidence, risk, or the candidate setup.

---

# 4. Status Lifecycle Scope (ADR-088)

`docs/11_SIGNAL_ENGINE.md` §18 defines eight states (Draft, Active, Triggered, Expired, Cancelled, Closed, Successful, Stopped Out). Reaching most of these requires either live price-monitoring infrastructure (Triggered/Closed/Successful/Stopped Out - comparing incoming candles against stored entry/stop/target, with trigger semantics docs/11 never precisely defines - e.g. touch vs. close, and `candidate_setup_builder`'s entry is always "latest close" per ADR-080, so there is no real distinction between "placed" and "triggered" the way a limit/stop order would have) or an admin/user action surface docs/04 never specifies (Cancelled). None of that exists in this project yet.

Phase 6B implements exactly two states:

- **ACTIVE** - written at creation, the only value 6B's code ever writes to the `status` column.
- **EXPIRED** - computed at read time only (`app/services/signal/status_resolver.py`), based on `settings.signal_ttl_hours` (default 24) compared against `created_at`. Never written back to the row - mirrors `risk_window.py`/`bias_analyzer.py`'s "a function of continuously-advancing wall-clock time, stale the instant it would be stored" reasoning (ADR-061).

The remaining six states are reserved enum values (so a future phase can start writing them without a migration) but are not reachable through any code path in 6B. Building live price-monitoring, trigger-detection, and outcome tracking (Successful/Stopped Out, `profit_loss`) is a real follow-up requiring its own design pass - not built speculatively here.

**Update (Phase 9E, ADR-137):** this follow-up is now built. `TRIGGERED`, `SUCCESSFUL`, and `STOPPED_OUT` are written by `app/workers/signal_monitoring_tasks.py`; `CLOSED` (a `TRIGGERED` signal that never resolved before `signal_triggered_ttl_hours`) is computed read-time-only, the same treatment as `EXPIRED`. The trigger rule fixes a live production defect where SL/TP were evaluated the instant a signal existed, without ever confirming price reached `entry_price` first - see ADR-137 for the full incident and design. `DRAFT`/`CANCELLED` remain unreachable through any current code path.

---

# 5. New Deterministic Module

**`app/services/signal/status_resolver.py`** - `effective_status(stored_status: SignalStatus, created_at: datetime, now: datetime, *, triggered_at: datetime | None = None) -> SignalStatus`: returns `EXPIRED` if `stored_status is ACTIVE` and `now - created_at >= timedelta(hours=settings.signal_ttl_hours)`; returns `CLOSED` if `stored_status is TRIGGERED`, `triggered_at` is given, and `now - triggered_at >= timedelta(hours=settings.signal_triggered_ttl_hours)` (ADR-137); otherwise returns `stored_status` unchanged. Pure function, no side effects, unit tested independently (mirrors `economic_calendar/risk_window.py`'s shape exactly).

**`app/services/signal_monitoring_service.py`** (Phase 9E, ADR-137) - `entry_touched(signal, candle) -> bool`: the touch-based trigger rule, `candle.low <= entry_price <= candle.high`. `evaluate_signal_outcome(signal, candle) -> SignalOutcome | None`: SL/TP touch-detection, valid only once a signal is `TRIGGERED` - callers gate this.

---

# 6. API (ADR-089)

```
POST /signals/generate/{symbol}?timeframe=H1   [authenticated - same LLM-cost rationale as ADR-083, and this endpoint invokes AIOrchestratorEngine]
GET  /signals?symbol=&status=&page=&limit=      [authenticated - signals derive from auth-gated ai_analysis, same surface-wide precedent ADR-083 already established]
GET  /signals/{id}                              [authenticated]
POST /signals/bookmark                          [authenticated, body: {"signal_id": "..."}]
DELETE /signals/bookmark/{id}                   [authenticated]
```

`POST /signals/generate/{symbol}` is **not** in `docs/04`'s original Signals section (which only listed `GET /signals`, `GET /signals/{id}`, `POST/DELETE /signals/bookmark` under "out of scope for Phase 6A"). It is added now because a scheduled/proactive generation job (Celery Beat calling this per configured asset/timeframe) was evaluated and deliberately deferred in favor of an on-demand model matching Phase 6A's existing `POST /analysis/ai/{symbol}` pattern - see ADR-089 for the full reasoning. `docs/04` is updated to add this endpoint's contract (§7 below), following the same "update docs before/alongside implementation" practice as every prior phase (BACKLOG.md §7).

`POST /signals/generate/{symbol}` response:

```json
{
  "analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
  "symbol": "EURUSD",
  "timeframe": "h1",
  "recommendation": "buy",
  "signal": {
    "id": "...", "analysis_id": "...", "symbol": "EURUSD", "timeframe": "h1",
    "signal_type": "buy", "entry_price": 1.17540, "stop_loss": 1.17120,
    "take_profit": 1.18150, "risk_reward": 1.45, "confidence": 87.0,
    "status": "active", "triggered_at": null, "closed_at": null,
    "profit_loss": null, "created_at": "2026-08-02T12:00:00Z"
  }
}
```

When `recommendation` is `"wait"`, `signal` is `null` - no row was created, matching ADR-011's "WAIT is valid" precedent without inventing a fake signal object for it.

---

# 7. Reuse Map

| Field | Source |
|---|---|
| Recommendation, confidence, risk level, entry/stop/target, reasoning, evidence | `AIOrchestratorEngine.generate()` (Phase 6A, unchanged) |
| Risk/reward ratio | `app.services.risk_management.risk_reward_validator.validate()` (Phase 5C, unchanged) |

No bespoke re-derivation of anything Phase 4A-6A already computes - the strongest reuse ratio of any engine in this project (even more so than Strategy Engine, docs/49 §16), since Phase 6B adds no new evidence source at all.

---

# 8. Bookmarks (ADR-090)

`signal_bookmarks` (`app/models/signal_bookmark.py`) is an inferred join table, not present anywhere in `docs/03` - `POST /signals/bookmark`/`DELETE /signals/bookmark/{id}` (docs/04, listed since Phase 6A's draft) require per-user bookmark state that no existing table provides. Follows `OAuthAccount`'s `(provider, provider_user_id)` uniqueness precedent (ADR-022): a unique constraint on `(user_id, signal_id)` prevents duplicate bookmarks. `UUIDMixin` + `CreatedAtMixin` (append-only - a bookmark is either present or absent, no update-in-place state).

---

# 9. Testing Strategy

| File | Covers |
|---|---|
| `test_signal_status_resolver.py` | ACTIVE within TTL, EXPIRED past TTL, non-ACTIVE stored states pass through unchanged |
| `test_signal_engine.py` | BUY/SELL produces a persisted Signal with correct risk_reward; WAIT produces no Signal row; `AIOrchestratorEngine.generate()` called exactly once |
| `test_signal_models.py` | FK behavior, `(user_id, signal_id)` uniqueness on `signal_bookmarks` |
| `test_signal_routes.py` | auth required on every route, 404s, list filtering/pagination, bookmark create/delete/duplicate-conflict, WAIT generation response shape |

Verified by inspection, consistent with every prior phase - coverage tooling is still not installed (BACKLOG.md §4).

---

# 10. Out of Scope for Phase 6B

Autonomous trading or broker execution (explicit user constraint); live price-monitoring / auto status transitions (Triggered/Closed/Successful/Stopped Out, `profit_loss` population); TP1/TP2/TP3 multi-target splitting (ADR-087, no formula specified anywhere); Cancelled status (no admin/user action endpoint specified); Celery Beat scheduled/proactive signal generation (ADR-089's rejected alternative); Telegram/Dashboard notification (Phase 7, downstream services don't exist); WebSocket `/ws/signals` (still tracked in BACKLOG.md §3); a genuine independent evidence-weighting pipeline per docs/11's original vision (ADR-085, superseded by Phase 6A).

**Update (Phase 9E, ADR-137):** live price-monitoring / auto status transitions are now built (§4 above) - no longer out of scope. Cancelled status still has no admin/user *action endpoint* - `backend/scripts/cancel_stale_active_signals.py` is a one-off operator script for the 9E deploy migration, not a general-purpose endpoint. TP1/TP2/TP3 splitting, Telegram/Dashboard notification beyond the existing entry/outcome messages, `/ws/signals`, and the independent evidence-weighting pipeline remain out of scope, unchanged.
