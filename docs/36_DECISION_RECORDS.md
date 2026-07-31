# Architecture Decision Records (ADR)

Version: 1.0

---

# Objective

This document records significant architectural and technical decisions made throughout the project.

Each decision must include:

- Context
- Decision
- Reasoning
- Trade-offs
- Consequences
- Status

Architecture decisions should never rely solely on memory.

---

# ADR Template

## ADR-XXX

Title

Date

Status

Accepted

Context

Describe the problem.

Decision

Describe the chosen solution.

Reason

Explain why.

Alternatives Considered

Option A

Option B

Option C

Trade-offs

Pros

Cons

Consequences

Positive

Negative

Future Review

When should this decision be revisited?

---

# ADR-001

Title

Use FastAPI as Backend Framework

Status

Accepted

Context

The backend requires:

- High performance
- Async support
- OpenAPI generation
- Excellent typing
- Modern architecture

Decision

Use FastAPI.

Reason

Excellent async support.

Automatic API documentation.

Strong typing.

Large ecosystem.

Trade-offs

Pros

Fast

Clean

Scalable

Cons

Smaller ecosystem than Django.

Future Review

Review every major FastAPI release.

---

# ADR-002

Title

Use Next.js for Frontend

Status

Accepted

Reason

SSR

Excellent React ecosystem

TypeScript

SEO support

App Router

Future Review

Evaluate major Next.js releases.

---

# ADR-003

Title

Use PostgreSQL

Status

Accepted

Reason

Reliable

Powerful indexing

JSON support

Scalable

Excellent tooling

---

# ADR-004

Title

Use Redis

Status

Accepted

Reason

Caching

Queues

Rate Limiting

WebSocket Support

Fast lookups

---

# ADR-005

Title

Separate AI from Business Logic

Status

Accepted

Decision

AI performs reasoning only.

Business rules remain deterministic.

Reason

Prevent hallucinations.

Improve testing.

Increase explainability.

Trade-offs

Pros

Reliable

Predictable

Auditable

Cons

More engineering effort.

---

# ADR-006

Title

Use Deterministic Technical Engines

Status

Accepted

Decision

Indicators are calculated in code.

Never by AI.

Reason

Accuracy

Repeatability

Testing

Auditability

---

# ADR-007

Title

AI Never Invents Market Data

Status

Accepted

Decision

AI receives structured evidence only.

Reason

Prevent hallucinations.

Increase trust.

Improve consistency.

---

# ADR-008

Title

Evidence-Based Architecture

Status

Accepted

Decision

Every engine publishes evidence.

Signal Engine consumes evidence.

Reason

Loose coupling.

Independent testing.

Better explainability.

---

# ADR-009

Title

Modular Engine Design

Status

Accepted

Decision

Each domain has its own engine.

Examples

Technical

SMC

Risk

News

Economic

Confidence

Reason

Independent development.

Scalable architecture.

Easy maintenance.

---

# ADR-010

Title

Signal Generation Requires Confluence

Status

Accepted

Decision

Signals are never generated from a single indicator.

Reason

Reduce false positives.

Increase signal quality.

Encourage institutional-style analysis.

---

# ADR-011

Title

WAIT is a Valid Recommendation

Status

Accepted

Decision

The platform may recommend WAIT.

Reason

No trade is often better than a poor trade.

Trade-offs

Pros

Protects users.

Builds trust.

Cons

Fewer signals.

---

# ADR-012

Title

Market Regime Before Strategy Selection

Status

Accepted

Decision

Determine market regime before selecting a strategy.

Reason

Different strategies perform better under different conditions.

---

# ADR-013

Title

Confidence Must Be Explainable

Status

Accepted

Decision

Every confidence score must include strengths and penalties.

Reason

Transparency.

User trust.

Debugging.

---

# ADR-014

Title

Risk Engine Can Reject Signals

Status

Accepted

Decision

The Risk Engine has veto authority.

Reason

Protect users during high-risk conditions.

Examples

Major economic events

Extreme volatility

Low liquidity

---

# ADR-015

Title

Admin Replay Capability

Status

Accepted

Decision

Every AI decision must be replayable.

Reason

Debugging.

Compliance.

Continuous improvement.

---

# ADR-016

Title

API-First Architecture

Status

Accepted

Decision

Every feature is exposed through the API before UI implementation.

Reason

Supports web, mobile, Telegram, and future integrations.

---

# ADR-017

Title

Configuration Over Hardcoding

Status

Accepted

Decision

Strategies, providers, thresholds, and feature behavior should be configurable whenever practical.

Reason

Simplifies maintenance.

Supports future expansion.

Reduces code changes.

---

# ADR-018

Title

Version Everything

Status

Accepted

Decision

Version prompts, AI models, APIs, database schema, engines, and configuration.

Reason

Rollback capability.

Reproducibility.

Historical analysis.

---

# ADR-019

Title

Observability by Default

Status

Accepted

Decision

Every critical service must expose metrics, logs, and health checks.

Reason

Simplifies troubleshooting.

Improves reliability.

Supports proactive monitoring.

---

# ADR-020

Title

Security by Design

Status

Accepted

Decision

Security requirements are integrated into architecture from the beginning rather than added later.

Reason

Reduce vulnerabilities.

Simplify compliance.

Protect user trust.

---

# Future ADRs

Every major architectural change requires a new ADR.

Existing ADRs should never be overwritten.

If a decision changes:

Old ADR

↓

Superseded

↓

New ADR

This preserves historical context.

---

# ADR Lifecycle

Proposed

↓

Under Review

↓

Accepted

↓

Implemented

↓

Deprecated (Optional)

↓

Superseded (Optional)

---

# ADR-021

Title

Use uv as Python Dependency Manager

Status

Accepted

Context

The backend needs a fast, reproducible, single-source-of-truth dependency management workflow for Python packages and virtual environments.

Decision

Use uv for all backend dependency management (installing, locking, running scripts). `pyproject.toml` is the single source of dependency declarations; `uv.lock` is committed for reproducible installs. `requirements.txt` is no longer used.

Reason

Significantly faster installs and locking than pip.

Single tool for virtualenv creation, dependency resolution, and locking.

Reproducible builds via a committed lockfile.

Growing ecosystem adoption.

Trade-offs

Pros

Fast

Reproducible

Simple developer workflow

Cons

Newer tool than pip, smaller long-term track record.

Future Review

Review if uv adoption stalls or a superior tool emerges.

---

# ADR-022

Title

Enforce Uniqueness on OAuthAccount (provider, provider_user_id)

Status

Accepted

Context

docs/03_DATABASE_DESIGN.md §3 defines the `oauth_accounts` table but does not specify a uniqueness constraint on the combination of `provider` and `provider_user_id`.

Decision

Add a unique constraint on `(provider, provider_user_id)` in the `oauth_accounts` table.

Reason

Without this constraint, the same external OAuth identity (e.g. the same Google account) could be linked to a ClaudeTrading account more than once, or linked inconsistently across concurrent requests, producing duplicate or ambiguous account-linking records.

This is an inferred correctness requirement, not an explicit item in docs/03 - recorded here per CLAUDE.md's "never invent architecture" rule so schema decisions beyond the literal documentation stay traceable.

Trade-offs

Pros

Prevents duplicate/ambiguous OAuth identity links.

Matches standard practice for OAuth account-linking tables.

Cons

None identified; a unique constraint on this pair has no legitimate case for duplication.

Future Review

Revisit if a provider requires multiple linked identities per (provider, provider_user_id) pair (not currently anticipated).

---

# ADR-023

Title

Hash Refresh Tokens with SHA-256, Distinct from Argon2id Password Hashing

Status

Accepted

Context

docs/23_AUTHENTICATION_AND_RBAC.md §6 requires sessions to be tracked and revocable, and `UserSessionRepository.get_by_refresh_token_hash` looks up a session by an exact hash match on the presented refresh token. docs/23 does not specify a hashing algorithm for this. Argon2id (used for passwords per docs/23 §7) is salted per-hash and designed to be verified against a known plaintext, not looked up by equality - it cannot support this access pattern.

Decision

Hash refresh tokens with SHA-256 (`app.core.security.hash_token`) for storage in `UserSession.refresh_token_hash` and for lookup. Continue using Argon2id exclusively for password hashing.

Reason

Refresh tokens are high-entropy, randomly generated JWTs (not low-entropy user secrets), so a fast deterministic hash is appropriate and enables the required exact-match session lookup. Argon2id remains reserved for passwords, where slow, salted hashing defends against offline brute-force of user-chosen secrets.

Alternatives Considered

Option A: Store refresh tokens in plaintext - rejected, a database read would leak valid session tokens.

Option B: Use Argon2id for refresh tokens too - rejected, salted hashes cannot be looked up by equality without also storing the plaintext or salt separately, defeating the purpose.

Option C: SHA-256 (chosen) - deterministic, fast, appropriate for high-entropy tokens.

Trade-offs

Pros

Enables O(1) session lookup by hash.

Keeps password hashing (Argon2id) and token hashing (SHA-256) each suited to their own threat model.

Cons

SHA-256 alone would be unsuitable for low-entropy secrets; must not be reused for passwords.

Consequences

Positive

Session/refresh-token lookups remain a simple indexed equality query.

Negative

None identified; this is inferred beyond the literal text of docs/23, recorded here per CLAUDE.md's "never invent architecture" rule (same practice as ADR-022).

Future Review

Revisit if refresh tokens are ever generated with lower entropy, or if a token-revocation-by-`jti` scheme (see BACKLOG.md) replaces hash-based session lookup.

---

# ADR-024

Title

Enforce Uniqueness on PriceCandle (asset_id, timeframe, timestamp)

Status

Accepted

Context

docs/03_DATABASE_DESIGN.md §5 specifies an index on `price_candles(asset_id, timeframe, timestamp)` but does not state that the combination must be unique. docs/34_DATA_PROVIDER_SPECIFICATION.md's "Validation" section explicitly requires "Duplicate Detection" for market data, and a candle for a given asset/timeframe/timestamp is logically singular - two rows for the same instant would be ambiguous, not a legitimate case of multiple valid candles.

Decision

Add a unique constraint on `(asset_id, timeframe, timestamp)` in the `price_candles` table. Ingestion (`PriceCandleRepository.upsert`) treats a write to an existing key as a correction (overwrite the OHLCV values), not a rejected duplicate - this handles providers that revise a still-forming candle, and makes re-running a collection job safe to retry.

Reason

Without this constraint, a retried or overlapping collection window could insert duplicate rows for the same candle, corrupting downstream indicator calculations and historical queries.

This is an inferred correctness requirement, not an explicit item in docs/03 - recorded here per CLAUDE.md's "never invent architecture" rule, following the ADR-022/ADR-023 precedent for schema decisions beyond the literal documentation.

Alternatives Considered

Option A: No uniqueness constraint, dedupe only in application logic before insert - rejected, this can't prevent duplicates from concurrent/overlapping collection runs at the database level.

Option B: Unique constraint with hard rejection (reject the whole write on conflict) - rejected, providers legitimately revise still-forming candles, so an overwrite-on-conflict (upsert) is more useful than an error.

Option C (chosen): Unique constraint + upsert-on-conflict in the repository.

Trade-offs

Pros

Prevents duplicate/ambiguous candle rows.

Makes ingestion idempotent and safe to retry.

Cons

None identified; a unique constraint on this triple has no legitimate case for duplication.

Future Review

Revisit if a future provider needs to store multiple revisions of the same candle rather than overwriting (not currently anticipated).

---

# ADR-025

Title

Provider-Agnostic Daily Request-Quota Enforcement in RateLimitedProvider

Status

Accepted

Context

Phase 3.5's `RateLimitedProvider` (docs/40) only enforced a requests-per-minute token bucket. Twelve Data's free tier (the first real provider, Phase 3B) is capped at both 8 requests/minute *and* 800 requests/day - the per-minute bucket alone does not prevent exceeding the daily cap, since even a single actively-scheduled asset/timeframe combination running every minute would reach 1,440 requests/day, well over the daily limit, while staying comfortably under the per-minute cap the whole time.

Decision

Extend `RateLimitedProvider` with an optional `requests_per_day` parameter, tracked against a UTC calendar-day boundary (reset at UTC midnight). Once exhausted, raise `DailyQuotaExceededError` (a `TransientProviderError` subclass, carrying `provider`/`used`/`limit`/`reset_at` for observability) rather than sleeping until the next day - `MarketDataService`'s existing retry/failover logic already handles a `TransientProviderError` sensibly (moves on to the next configured provider, or simply yields no new candles for that collection cycle) without needing new orchestration logic. The daily cap remains entirely inside the decorator - `MarketDataService` and every provider implementation stay unaware of it, consistent with Phase 3.5's original decision to keep rate limiting out of the orchestration layer.

Reason

Sleeping until a daily quota resets could stall a Celery task for hours, which is far worse than failing fast and letting the existing failover/retry path decide what to do next. Raising also makes the daily-exhaustion event observable (structured log via `MarketDataService`'s existing per-call logging) rather than a silent multi-hour pause.

Alternatives Considered

Option A: Sleep until the next UTC day, mirroring the per-minute token bucket's blocking behavior - rejected, an hours-long block inside a Celery task is operationally unacceptable and defeats the purpose of a scheduled, bounded collection cycle.

Option B: Track the daily budget inside each provider implementation instead of the shared decorator - rejected, this would require every provider to reimplement the same bookkeeping, exactly the duplication `RateLimitedProvider` exists to avoid.

Option C (chosen): Daily budget tracked in `RateLimitedProvider`, raising `DailyQuotaExceededError` once exhausted.

Trade-offs

Pros

Prevents exceeding a provider's daily quota regardless of how many assets/timeframes are scheduled against it.

Fails fast and observably instead of blocking silently for hours.

No provider implementation needs to know about daily limits.

Cons

Assumes a UTC-midnight reset boundary - if a provider's actual reset time differs (e.g. a rolling 24h window, or a non-UTC reset), this could under- or over-estimate remaining quota near the boundary. Not currently known to be an issue for Twelve Data specifically; revisit if it is.

Future Review

Revisit if a provider's actual quota-reset behavior is confirmed to differ from a UTC calendar day, or if quota metadata returned by a provider's own API (e.g. a `X-RateLimit-Remaining`-style header) becomes available and should take precedence over locally-tracked counting.

---

# ADR-026

Title

Isolate Raw HTTP Transport Behind a Dedicated Client Per Provider

Status

Accepted

Context

`TwelveDataProvider` (Phase 3B, docs/40/docs/41) needs to make real HTTP requests. Two concerns are tangled together in "call a market-data provider over HTTP": (1) the mechanics of sending a request and getting a response back - base URL, auth header, timeout, network-level failure handling, JSON parsing - and (2) interpreting *that specific provider's* response shape and error codes into the shared `MarketDataProviderError` hierarchy. Neither docs/38 nor docs/40 (both written before any real HTTP-calling provider existed) specified how to split these.

Decision

Every provider that talks to a real HTTP API gets its own dedicated, thin transport class (e.g. `TwelveDataHttpClient`) that does *only* concern (1): perform the request, return `(status_code, json_body)`, and raise a single provider-specific transport exception (e.g. `TwelveDataTransportError`) for network-level failures (timeouts, connection errors, malformed response bodies). It never inspects the provider's own success/error envelope. The provider class itself (`TwelveDataProvider`) owns concern (2) entirely - classifying `(status_code, json_body)` into `TwelveDataAuthenticationError`/`TwelveDataQuotaExceededError`/`TwelveDataInvalidSymbolError`/etc., all subclassing the shared `TransientProviderError`/`PermanentProviderError` categories (docs/40 §5). The transport class accepts an injectable `httpx.BaseTransport`, so tests can substitute `httpx.MockTransport` and never make a real network call (docs/40 §10) - this was the specific requirement that made the split worth doing explicitly rather than leaving it implicit.

Reason

Keeping HTTP mechanics and response-schema interpretation in the same class makes both harder to test and harder to reason about - a test exercising "does this provider correctly classify a 429 as retryable" shouldn't also need to deal with real socket-level mocking, and a test exercising "does the client handle a connection timeout" shouldn't need to know anything about Twelve Data's JSON error shape. Splitting them mirrors the same instinct already applied elsewhere in this codebase - `CandleValidator` isolated from `MarketDataService`'s orchestration (Phase 3.5), `RateLimitedProvider` isolated from provider logic (Phase 3.5) - of keeping a single, narrow, testable responsibility per component rather than one class doing several things adequately.

Alternatives Considered

Option A: One class per provider handling both transport and classification - rejected, this is what Phase 3B avoided; harder to unit-test the classification logic in isolation from real HTTP mechanics.

Option B: A single, fully generic shared HTTP client for all providers - rejected, different providers have different auth schemes, base URLs, and response envelopes; a "generic" client would either leak provider-specific branching back into shared code, or become a thin wrapper providing no real value over just using `httpx.Client` directly per provider (which is what this ADR chooses, just made explicit and named).

Option C (chosen): One dedicated, thin transport class per provider, injectable for testing, with all classification logic left to the provider class itself.

Trade-offs

Pros

Classification logic (the part most likely to need careful testing and to evolve as new error cases are discovered) is testable without any real network dependency.

Each provider's transport class stays trivial - there's very little to get wrong in "send a request, return status+body, wrap network errors."

Consistent, easy-to-follow pattern for whichever provider comes after Twelve Data.

Cons

One extra small class per HTTP-calling provider - a minor amount of additional structure for what could, for a single provider, be inlined. Judged worth it given docs/40 explicitly anticipates more providers being added later.

Future Review

Revisit if enough providers accumulate near-identical transport classes that a genuinely shared base (e.g. a small `HttpProviderTransport` base class handling the common `httpx.Client` construction pattern) becomes worth extracting - not done now, to avoid a premature abstraction over a single example.

---

# ADR-027

Title

Technical Analysis Engine Is Stateless (No Persisted Snapshot Table)

Status

Accepted

Context

Phase 4A's Technical Analysis Engine (docs/08, docs/42) synthesizes trend/strength/technical-score/support-resistance from candles and indicators. docs/03 has no table for this computed output (only `indicator_results` for raw values, built in Phase 3A). Two options existed: persist each computed analysis as a new table/migration, or compute it fresh on every request.

Decision

`TechnicalAnalysisEngine` is fully stateless. `analyze()` and `analyze_multi_timeframe()` recompute trend/score/support-resistance from live `price_candles` and freshly-calculated indicators (via the existing `app/indicators` registry, not persisted `indicator_results` rows) on every call. No new table, no migration.

Reason

Avoids a second source of truth (a stored snapshot could disagree with what fresh computation would produce, with no clear rule for which is authoritative) and avoids staleness (a persisted snapshot would only be as fresh as its last computation, whereas an on-demand request should reflect the current market state). The existing indicator functions are already fast (proven in Phase 3A), so recomputation cost is low. The future AI Orchestrator (Phase 6, per docs/07) is expected to call this engine directly rather than read a stored result.

Alternatives Considered

Option A: Persist every computed analysis in a new `technical_analysis_snapshots` table - rejected, adds a migration and a second source of truth for no clear benefit at this phase, and nothing downstream needs historical technical-analysis snapshots yet.

Option B (chosen): Fully stateless, computed fresh per request.

Trade-offs

Pros

No schema/migration needed.

Guaranteed freshness - no staleness window between a scheduled computation and a request.

Single source of truth (candles + indicators), not two.

Cons

Every request recomputes rather than reading a cached row - acceptable given docs/08 §13's performance target and the existing indicator functions' proven speed.

No historical audit trail of past technical-analysis snapshots.

Future Review

Revisit if the AI Orchestrator (Phase 6) or a future audit/replay requirement (ADR-015's "Admin Replay Capability" is about AI decisions specifically, not this deterministic engine, but the same instinct could extend here) needs historical technical-analysis snapshots, not just the current one.

---

# ADR-028

Title

Definitive Technical Scoring Formula (100-Point Breakdown)

Status

Accepted

Context

docs/08 §9 gives an illustrative scoring example (EMA Alignment +20, MACD Bullish +15, ADX Strong +15, RSI Healthy +10, VWAP Above Price +10, ATR Stable +5) that sums to 75, not the same section's stated "Maximum Technical Score: 100" - an internal inconsistency, not just an incomplete example. A complete, definitive formula was needed.

Decision

A 100-point breakdown across seven components, implemented in `app/services/technical_analysis/scoring_engine.py`:

- Trend alignment: up to 25 (moving-average alignment score, docs/42 §7)
- Trend strength: up to 15 (ADX-derived, docs/42 §9)
- Momentum: up to 15 (MACD direction agreement with trend)
- Oscillator: up to 15 (RSI/Stochastic RSI/CCI health)
- Volume: up to 15 (VWAP position agreement with trend)
- Volatility: up to 10 (Bollinger Band state)
- Support/Resistance: up to 5 (proximity context available)

Each detected conflict (`ConflictAnalyzer`) subtracts a fixed 10 points, floored at 0 overall (never negative). `ScoreBreakdown` reports every component separately, not just the total (Phase 4A refinement - explainability for future AI reasoning).

Reason

docs/08 §9's example could not be implemented as-is (it doesn't reach its own stated maximum), so a complete formula had to be designed rather than merely filled in. Distributing points by "which factor family" (trend/momentum/oscillator/volume/volatility/support-resistance) rather than by individual indicator keeps the breakdown meaningful and stable even as individual indicator interpretations are refined later.

Alternatives Considered

Option A: Keep docs/08 §9's exact weights and simply accept a max of 75 - rejected, contradicts the doc's own stated maximum and under-uses momentum/oscillator/volume signal.

Option B (chosen): A complete, documented 100-point breakdown per factor family, with per-conflict penalties.

Trade-offs

Pros

Actually reaches the documented maximum of 100.

Explainable per-factor breakdown, not just a single opaque number.

Cons

The exact point allocations (25/15/15/15/15/10/5) are a considered but ultimately somewhat arbitrary judgment call, like docs/08's own example was - not derived from a backtest or statistical model.

Future Review

Revisit the weight allocation once real trading outcomes (via the future Signal Engine, Phase 6) can be correlated against these scores - this is a starting point, not a tuned model.

---

# ADR-029

Title

Magnitude-Aware Rounding Heuristic for Round Numbers / Psychological Levels

Status

Accepted

Context

docs/08 §6 names "Round Numbers" and "Psychological Levels" as support/resistance categories but doesn't define how to compute them. A hardcoded per-symbol table (e.g. "EURUSD rounds to 0.0050, XAUUSD rounds to 5.0") wouldn't generalize to new assets without ongoing maintenance.

Decision

`support_resistance_analyzer._round_number_levels` computes a step size proportional to the current price's order of magnitude (`10^floor(log10(price)) / 20`), rounding to the nearest such step above and below the current price - e.g. ~0.005 for a ~1.10 forex pair, ~100 for a ~2400 gold/index price - rather than a per-symbol lookup table.

Reason

A magnitude-based heuristic generalizes automatically to any asset's price scale without needing a maintained table entry per symbol, consistent with docs/38/40/41's preference for adapter logic over persisted/hardcoded per-asset mapping tables where a general rule suffices.

Alternatives Considered

Option A: Hardcoded per-symbol step table - rejected, doesn't scale to new assets without maintenance, the exact failure mode this project has repeatedly avoided elsewhere (docs/38 §3, docs/41 §3).

Option B (chosen): Magnitude-aware proportional step size.

Trade-offs

Pros

Generalizes to any asset/price scale automatically.

No maintenance burden as new assets are added.

Cons

The specific divisor (÷20) is a considered but somewhat arbitrary constant, not derived from market-microstructure research per asset class.

Future Review

Revisit if a specific asset class's real-world round-number conventions (e.g. crypto's preference for round numbers at different scales than forex) are found to diverge meaningfully from this generic heuristic.

---

# ADR-030

Title

Multi-Timeframe Weighted-Combination Algorithm

Status

Accepted

Context

docs/08 §8 gives one narrative example (Daily Bullish, H4 Bullish, H1 Pullback, M15 Bullish → "Bullish Continuation") establishing that higher timeframes carry more weight, but not a general algorithm for combining four timeframes' trend directions into one verdict.

Decision

Weighted combination scoped to exactly the four timeframes docs/08 §8 names - D1 (weight 40), H4 (30), H1 (20), M15 (10), summing to 100, mirroring the scoring engine's pattern. Each timeframe's trend contributes +weight (bullish), -weight (bearish), or 0 (sideways) to a net total; the ratio of net-to-max-possible determines the verdict: ≥0.5 → `bullish_alignment`, ≤-0.5 → `bearish_alignment`, otherwise → `mixed`. Implemented in `app/services/technical_analysis/multi_timeframe_analyzer.py`.

Reason

A ±0.5 threshold requires a genuine majority (not just any positive lean) before declaring full alignment, which matches the intent of docs/08 §8's example (all four timeframes agreeing, or a clear majority with only a "pullback" dissenting) rather than letting a single dissenting higher-timeframe vote be overridden by a bare plurality of lower-timeframe votes.

Alternatives Considered

Option A: Simple majority vote (3 of 4 agree) ignoring weight - rejected, contradicts docs/08 §8's explicit statement that "Higher timeframe always has greater weight."

Option B (chosen): Weighted net score against a 0.5 alignment threshold.

Trade-offs

Pros

Directly reflects the documented "higher timeframe = more weight" rule.

A single dissenting timeframe (like docs/08's own "H1 Pullback" example) doesn't prevent an otherwise-clear alignment.

Cons

The exact weights (40/30/20/10) and the 0.5 threshold are considered judgment calls, not derived from a formal model.

Future Review

Revisit the weights/threshold alongside ADR-028's scoring weights, once real outcomes can inform tuning (Phase 6+).

---

# ADR-031

Title

Technical Analysis Produces Evidence, Not Trading Signals

Status

Accepted

Context

The Technical Analysis Engine (Phase 4A) computes trend direction, strength, a technical score, and support/resistance levels - output that could superficially resemble a trading recommendation. ADR-005 ("Separate AI from Business Logic") and ADR-006 ("Use Deterministic Technical Engines") already establish that indicators are calculated in code, never by AI, but neither explicitly states what this specific engine's output *is* and *is not* for.

Decision

The Technical Analysis Engine produces **structured evidence only** - `TechnicalAnalysisResult`/`MultiTimeframeResult` (trend, strength, score breakdown, support/resistance, warnings). It never produces a BUY/SELL/WAIT recommendation, an entry/stop-loss/take-profit level, or any other trading decision. It is fully deterministic - no AI, no LLM, no probabilistic reasoning anywhere in `app/services/technical_analysis/`. Generating trading decisions from this (and other engines') evidence is explicitly the future Signal Engine's responsibility (docs/30 Phase 6), not this engine's.

Reason

Making this explicit (rather than relying on it being implied by ADR-005/006) matters specifically for this engine because its output - a 0-100 "technical_score" and a directional "trend" - is the closest thing in the codebase so far to something that *looks* like a recommendation. Future contributors (or a future AI Orchestrator integration) must not conflate "high technical_score, bullish trend" with "a signal to buy" - that inference, if made, belongs to the Signal Engine, which will combine this evidence with SMC/News/Economic/Risk evidence from other engines (docs/07 §3's pipeline) before any recommendation is generated.

Alternatives Considered

Option A: Leave this implicit, relying on ADR-005/006 and docs/08 §1's "DOES NOT generate BUY or SELL signals" - rejected, given how easily a "technical_score" could be mistaken for a readiness-to-trade signal by a future integrator skimming the code rather than the docs.

Option B (chosen): An explicit ADR stating the boundary plainly, alongside docs/08 §1's existing statement.

Trade-offs

Pros

Removes ambiguity for whoever builds the Signal Engine (Phase 6) or AI Orchestrator integration (also Phase 6) about what this engine's output means and doesn't mean.

Cons

None identified - this is a clarifying, not a functional, decision.

Future Review

Revisit only if the project's phase boundaries themselves change (e.g. if a future decision merges signal generation into this engine, which would require superseding this ADR explicitly, not just quietly building around it).

---

# ADR-032

Title

SMC Engine Persists Detected Structures (Contrast with ADR-027)

Status

Accepted

Context

The Technical Analysis Engine (Phase 4A, ADR-027) is deliberately stateless - no documented table existed for it, and its output is a point-in-time indicator snapshot with no lifecycle. The SMC Engine (Phase 4B) faces a different situation: docs/03 §7 already specifies an `smc_events` table, and SMC concepts (order blocks, FVGs, liquidity zones) have genuine lifecycle state - fresh, then touched, then mitigated or invalidated - that a stateless recompute-every-time design would discard.

Decision

`SMCEngine` persists detected/updated structures to `smc_events` on every `analyze()` call, de-duplicated against existing rows by natural key (`asset_id`, `timeframe`, `event_type`, `detected_at`) so repeated calls update in place rather than insert duplicates. Each call is bounded to the most recent 500 candles (`_DEFAULT_LOOKBACK`), keeping cost from growing with total asset history even without a full delta-only incremental scan.

Reason

Reversing ADR-027's stateless precedent for this specific engine is justified by two independent facts, not a general preference for persistence: the table is already documented, and the domain concepts are inherently stateful in a way Technical Analysis's indicators are not.

Alternatives Considered

Option A: Stay fully stateless, like Technical Analysis - rejected, would require re-deriving a zone's touch/mitigation history from scratch on every request, discarding information docs/03 §7 already expects to be stored.

Option B (chosen): Persist to `smc_events`, bounded-window analysis, natural-key de-duplication.

Trade-offs

Pros

Zone lifecycle (fresh/touched/mitigated/invalidated/archived) survives across requests, matching what `smc_events` was designed to store.

Bounded-window analysis keeps repeated calls fast without the complexity of a full delta-only scan.

Cons

Not a true incremental scan - each call still re-examines the full bounded window, not just genuinely new candles (see ADR-032's companion note in docs/43 §15).

Future Review

Revisit once real-world history sizes/request volumes justify the added complexity of a true delta-only incremental scan.

---

# ADR-033

Title

`smc_events` Zone Rows Are Mutable, Not Append-Only

Status

Accepted

Context

Every other table with a temporal dimension in this project (`price_candles`, `indicator_results`, `audit_logs`) is append-only/immutable once written (`CreatedAtMixin`, single timestamp). Zone-type SMC concepts (order blocks, FVGs, liquidity zones) don't fit that shape - the same detected zone's state (touched, mitigated, broken) genuinely changes over time as later candles interact with it.

Decision

`SMCEvent` rows for zone-type `event_type`s are mutable: the same row's `status` and `context` (JSON) update in place via `SMCEventRepository.update_status`/direct mutation, looked up by a natural key rather than re-inserted per lifecycle transition. A `status` column (`SMCEventStatus`: ACTIVE/MITIGATED/INVALIDATED/ARCHIVED, ADR-037) was added beyond docs/03 §7's literal field list specifically to make "give me all ACTIVE order blocks" a plain indexed filter rather than a JSON-operator query. Rows are never deleted - even ARCHIVED zones remain queryable.

Reason

Modeling a zone as a sequence of append-only "transition" rows (matching the rest of the project's convention) would require inventing a correlation key linking multiple rows to "the same zone," adding complexity with no benefit over simply updating one row - since a zone is a single entity with evolving state, not a sequence of independent discrete facts like a price candle or an audit log entry.

Alternatives Considered

Option A: Append-only transition rows (matching every other table) - rejected, requires an artificial zone-correlation key and produces no benefit for a genuinely single, evolving entity.

Option B (chosen): Mutable rows, looked up by natural key, status column added beyond docs/03's literal spec.

Trade-offs

Pros

Simple 1:1 mapping between a detected zone and a database row.

Efficient filtering by lifecycle state via a plain column, not JSON-operator queries.

Cons

A deliberate, documented inconsistency with every other table's append-only convention - must not be copied elsewhere without the same justification.

Future Review

None expected - this is scoped specifically to zone-type SMC concepts.

---

# ADR-034

Title

Order Block Candle-Pattern Definition

Status

Accepted

Context

docs/09 §8 lists what an Order Block *stores* (zone high/low, mitigated/touched/broken, strength/freshness scores, volume confirmation) but never defines which candle *is* the order block - a genuine ambiguity flagged during Phase 4B planning.

Decision

An order block is the **last opposite-colored candle before the displacement move that produces a BOS** - for a bullish BOS, the last bearish (`close < open`) candle within a 10-candle lookback preceding the break; for a bearish BOS, the last bullish candle. The zone is that candle's high/low. Breaker Blocks (docs/09 §13) are modeled as a lifecycle flag (`is_breaker`/`breaker_confirmed`/`retest_count`) on the same order-block row, not a separate event type - a broken order block and a confirmed breaker are the same zone at different lifecycle stages, not two different structures.

Reason

This is the standard ICT (Inner Circle Trader) definition for an order block and is the only definition consistent with docs/09 §14's confluence example ("Bullish BOS + Bullish Order Block"), which implies the order block causally precedes/produces the BOS rather than being an independent, separately-detected structure.

Alternatives Considered

Option A: Treat Order Blocks and Breaker Blocks as fully independent detectors, each scanning raw candles - rejected, duplicates work and risks producing two rows for what is conceptually one zone across its lifecycle.

Option B (chosen): One candle-pattern definition tied to BOS detection; Breaker Block as a lifecycle flag on the same row.

Trade-offs

Pros

No duplicate zone rows for the same institutional level across its Order Block / Breaker Block lifecycle.

Matches the ICT convention practitioners and docs/09's confluence example both assume.

Cons

The 10-candle lookback limit is a considered but not empirically-derived constant.

Future Review

Revisit the lookback constant if real market data shows meaningful order blocks forming further back from their BOS than 10 candles.

---

# ADR-035

Title

Equal Highs/Lows Magnitude-Aware Tolerance

Status

Accepted

Context

docs/09 §10 requires detecting "Equal Highs" and "Equal Lows" for liquidity-zone purposes but gives no tolerance for what counts as "equal" - two swing highs are essentially never bit-for-bit identical in real price data.

Decision

Two or more swing highs (or lows) within 5 basis points (0.05%) of each other - proportional to price, not a fixed absolute value - are grouped into one equal-highs/equal-lows liquidity zone. Implemented in `app/services/smc/liquidity_analyzer.py`.

Reason

A proportional tolerance generalizes across a ~1.10 forex pair, a ~2400 gold price, and a ~60000 crypto price without a maintained per-asset-class table, mirroring ADR-029's magnitude-aware rounding heuristic for round-number levels - the same category of decision, applied to a different concept.

Alternatives Considered

Option A: Fixed absolute tolerance (e.g. 0.0005 price units) - rejected, meaningless across wildly different price scales (a forex pair vs. a stock index vs. a crypto asset).

Option B (chosen): 5 basis points of price, proportional.

Trade-offs

Pros

Generalizes to any asset's price scale automatically, consistent with ADR-029's precedent.

Cons

5 basis points is a considered but somewhat arbitrary constant, not derived from market-microstructure research per asset class.

Future Review

Revisit alongside ADR-029 if a specific asset class's real liquidity clustering is found to diverge meaningfully from this generic heuristic.

---

# ADR-036

Title

SMC Multi-Timeframe Weights and `smc_score` Are Distinct From Technical Analysis's

Status

Accepted

Context

docs/09 §15 names five priority timeframes (Weekly, Daily, H4, H1, M15) - one more than Technical Analysis's four (D1, H4, H1, M15, ADR-030). docs/09 §14 and §17 also create ambiguity between a "Confluence Score" (§14, max 100) and an "smc_score" (§17) - unclear whether these are the same number, competing scores, or something else.

Decision

SMC's multi-timeframe combination uses its own weight set - W1=35, D1=30, H4=20, H1=10, M15=5 (sum 100) - not a reuse of ADR-030's four-timeframe weights, since the timeframe set itself differs. Confluence (docs/09 §14) is implemented as **one component** feeding a single `smc_score` (via `SMCScoreBreakdown`, mirroring ADR-028's explainable-breakdown pattern), not a second, competing score. `smc_score` and `technical_score` are never combined by either engine - `smc_score` measures institutional-structure evidence strength (zone freshness, structural alignment, confluence), `technical_score` measures indicator agreement (moving averages, oscillators, volume). Combining them, if ever done, is the future Signal Engine's responsibility (docs/30 Phase 6), extending ADR-031's evidence-not-signals boundary to SMC.

Reason

Reusing ADR-030's weights verbatim would silently under-weight or omit the Weekly timeframe docs/09 explicitly names. Treating confluence as a second score (rather than a scoring component) would create two numbers answering overlapping questions with no defined relationship between them - explainability requires exactly one score with a documented breakdown, matching the project's existing ADR-028 precedent.

Alternatives Considered

Option A: Reuse ADR-030's four-timeframe weights unchanged, dropping Weekly - rejected, contradicts docs/09 §15's explicit five-timeframe priority list.

Option B: Confluence Score and SMC Score as two independent, separately-returned numbers - rejected, no documented relationship between them would leave API consumers to guess which one matters.

Option C (chosen): New five-timeframe weight set; confluence as one `SMCScoreBreakdown` component.

Trade-offs

Pros

Matches docs/09 §15's five-timeframe list exactly.

One explainable score, consistent with ADR-028's established breakdown pattern.

Clear, documented boundary preventing `smc_score`/`technical_score` conflation.

Cons

The specific weight allocation (35/30/20/10/5) is a considered judgment call, not derived from a formal model.

Future Review

Revisit the weights alongside ADR-028/ADR-030 once real outcomes can inform tuning (Phase 6+).

---

# ADR-037

Title

SMC Event Lifecycle

Status

Accepted

Context

Phase 4B's persistence decision (ADR-032) requires a defined set of lifecycle states for mutable zone-type `smc_events` rows (ADR-033), and explicit rules for how a zone moves between them, so historical SMC events are never deleted even once resolved.

Decision

Four lifecycle states, stored in `SMCEvent.status` (`SMCEventStatus`):

```
ACTIVE ──▶ MITIGATED ──▶ ARCHIVED
   └────▶ INVALIDATED ──▶ ARCHIVED
```

- ACTIVE: untouched since detection.
- MITIGATED: price closed within the zone (order blocks/FVGs) or the level was swept (liquidity).
- INVALIDATED: price closed cleanly through the zone's far side (order blocks only).
- ARCHIVED: resolved (MITIGATED/INVALIDATED) for more than 30 days (`_ARCHIVE_AFTER` in `smc_engine.py`) - a housekeeping transition applied on each `analyze()` call, never a deletion.

BOS, CHOCH, and swing-point classification events have no MITIGATED/INVALIDATED transition (they are point-in-time facts) - they remain ACTIVE until archived by age alone.

Reason

An explicit, small, closed set of states and transitions (rather than an open-ended free-text status) makes "is this zone still relevant" a simple, indexed filter for API consumers and future engines, while the never-delete/archive-only rule preserves historical SMC events for audit, backtesting, and future ML validation (docs/09 §22) without unbounded row growth going unacknowledged (ARCHIVED rows are excluded from the default `list_for_asset_timeframe` view, though never removed).

Alternatives Considered

Option A: Two states only (active/resolved) - rejected, loses the meaningful distinction between "worked as expected" (mitigated) and "proven wrong" (invalidated), which future engines (Signal Engine, ML validation) will likely want to distinguish.

Option B: Delete resolved zones after some period - rejected outright per explicit instruction to never delete historical SMC events.

Option C (chosen): Four states, archive-not-delete, as described above.

Trade-offs

Pros

Small, closed, indexed state set - simple filtering, no free-text status drift.

Full historical record preserved for future backtesting/ML work (docs/09 §22).

Cons

The 30-day archive threshold is a considered but not empirically-derived constant, and is time-based rather than candle-count-based (so it behaves differently across timeframes in terms of "how many candles" it represents).

Future Review

Revisit the archive threshold once real usage patterns (or the future Signal Engine's needs) clarify how long a resolved zone remains analytically relevant.

---

# Review Policy

Review ADRs:

- Before major releases
- When introducing new infrastructure
- When replacing providers
- When changing AI models
- During annual architecture reviews