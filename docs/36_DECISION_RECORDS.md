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

# ADR-038

Title

Market Regime Engine is Stateless

Status

Accepted

Context

Phase 4C needed a persistence decision, as SMC (ADR-032) and Technical Analysis (ADR-027) each did. docs/03 has no `market_regime`/`regime_events` table - unlike SMC's situation, matching Technical Analysis's instead.

Decision

`MarketRegimeEngine` persists nothing. Every call to `analyze()`/`analyze_multi_timeframe()` fetches recent candles, calls `TechnicalAnalysisEngine.analyze()` and `SMCEngine.analyze()` (each exactly once), runs the regime analyzers, and returns a plain in-memory result. No new database table exists for this phase.

Reason

A regime classification is a fresh synthesis of evidence two other engines have already computed and (in SMC's case) already persisted - it has no genuine per-zone lifecycle of its own, unlike an Order Block or FVG. Recomputing it is cheap precisely because the expensive detection work lives upstream.

Alternatives Considered

Option A: Persist regime classifications, mirroring SMC's ADR-032 - rejected, no documented table exists, and a regime classification has no lifecycle state to track (it doesn't get "mitigated" or "touched" the way a zone does).

Option B (chosen): Stateless, matching ADR-027's precedent.

Trade-offs

Pros

No new table/migration/repository for something with no genuine lifecycle.

Consistent with the "no table documented -> stateless" pattern already established.

Cons

No persisted regime history for future backtesting without re-running the engine over historical candles.

Future Review

Revisit if a future phase (backtesting, Confidence Engine) needs queryable regime history rather than point-in-time recomputation.

---

# ADR-039

Title

Regime Classification Precedence Order

Status

Accepted

Context

docs/16 §3 lists eleven possible regime values but never states a rule for choosing among them when multiple conditions hold simultaneously (e.g. a strong bullish trend during high volatility near a breakout) - a genuine missing deterministic rule.

Decision

Per Phase 4C's approved refinement: every candidate regime's confidence is evaluated first (`RegimeClassifier.build_candidates`), independent of precedence. Candidates below `MIN_CONFIDENCE_TO_QUALIFY` (60.0, matching docs/16 §14's confidence-band boundary) are discarded. Only among the qualifying survivors is this precedence order applied: Reversal > Breakout > Distribution/Accumulation > Trending Bullish/Bearish > Pullback > Ranging > High/Low Volatility > Uncertain (fallback).

Reason

Evaluating confidence before applying precedence (rather than a naive "first matching condition wins" scan) reduces false positives - a weak, barely-qualifying Reversal signal should not automatically outrank a strong, clearly-qualifying Trending Bullish signal just because Reversal is earlier in the list; both must clear the confidence bar first, and only then does precedence break ties among genuine candidates.

Alternatives Considered

Option A: First-match-wins scan through the precedence order, no confidence-qualification step - rejected per Phase 4C's explicit refinement request, since it would let a barely-detected condition outrank robust evidence lower in the list.

Option B (chosen): Confidence-qualify first, precedence second.

Trade-offs

Pros

Reduces false positives from weak evidence in a high-precedence category.

Precedence order remains simple and fully documented, not a black-box weighted vote.

Cons

The precedence order itself, and the 60.0 qualification threshold, are considered starting points, not derived from a formal model.

Future Review

Revisit the precedence order and threshold once real classification outcomes can inform tuning.

---

# ADR-040

Title

Accumulation/Distribution Deterministic Definition

Status

Accepted

Context

docs/16 §9/§10 give characteristics ("Institutional Buying/Selling Evidence," "Increasing Volume," "Sideways Movement") but no algorithm for computing an Accumulation Score/Distribution Score.

Decision

Accumulation score sums: range confirmation (40 pts) + increasing volume trend (30 pts, recent-half vs. baseline-half candle volume average) + "institutional buying evidence" (30 pts) - defined as an ACTIVE bullish SMC Order Block, or a **sell-side** liquidity sweep. Distribution score mirrors this with bearish Order Blocks / **buy-side** sweeps. Implemented in `app/services/market_regime/accumulation_distribution_analyzer.py`.

Reason

A liquidity sweep's directionality has a standard, well-known interpretation in Smart Money Concepts practice: a sell-side sweep (price wicks below an old low then reverses up) represents smart money buying from retail stop-losses - an accumulation signal - and a buy-side sweep is the mirror (distribution). Reusing SMC's already-persisted Order Block/sweep evidence avoids re-scanning candles for institutional footprints SMC has already detected.

Alternatives Considered

Option A: Re-scan raw candles for volume/price-action patterns independent of SMC's evidence - rejected, duplicates detection work SMC already performs and persists.

Option B (chosen): Reuse SMC's Order Block/liquidity-sweep evidence with the standard ICT sweep-directionality interpretation.

Trade-offs

Pros

No duplicated institutional-footprint detection logic.

Reuses evidence practitioners already understand semantically.

Cons

The specific point weights (40/30/30) and the 1.1x volume-increase threshold are considered starting points, not derived from a formal model.

Future Review

Revisit the weights/threshold once real outcomes can inform tuning, alongside ADR-028/ADR-036.

---

# ADR-041

Title

Pullback Depth Classification (Distinct from SMC's Multi-Timeframe Pullback)

Status

Accepted

Context

docs/16 §11 requires classifying pullback depth (Healthy/Deep/Potential Reversal) but gives no measurement algorithm. SMC already has its own "Pullback" concept (docs/09 §16, ADR-036) - a **multi-timeframe** classification for when a lower timeframe disagrees with a higher timeframe's structure. These are easily conflated but answer different questions.

Decision

Market Regime's Pullback Depth is a **single-timeframe** retracement-depth measurement: using the most recently classified SMC swing high/low (from `MarketStructureEvidence.classifications`, not re-detected), measure how far current price has retraced against the dominant trend as a fraction of that swing's range. Fibonacci-style bands: ≤0.382 Healthy, ≤0.618 Deep, beyond that Potential Reversal. Implemented in `app/services/market_regime/pullback_reversal_analyzer.py`.

Reason

The two "Pullback" concepts are legitimately different (one about timeframe agreement, one about retracement magnitude within one timeframe) and both are useful - renaming either to avoid the name collision would obscure their docs/09/docs/16 origins. Explicit documentation of the distinction (here and in docs/44 §9) prevents future confusion.

Alternatives Considered

Option A: Reuse SMC's multi-timeframe Pullback flag directly as Market Regime's Pullback evidence - rejected, answers a different question (timeframe agreement, not retracement depth) and docs/16 §11 explicitly wants a depth classification.

Option B (chosen): A new, single-timeframe retracement-depth measurement, explicitly distinguished from SMC's concept in documentation.

Trade-offs

Pros

Answers docs/16 §11's actual question (how deep is this pullback) rather than repurposing an unrelated multi-timeframe signal.

Reuses SMC's already-classified swing points rather than re-detecting them.

Cons

The Fibonacci-style band boundaries (0.382/0.618) are a considered but not empirically-derived convention, and docs/16 never mentions Fibonacci levels itself.

Future Review

Revisit the band boundaries once real outcomes can inform tuning.

---

# ADR-042

Title

Regime Confidence is Distinct from `technical_score`/`smc_score`; "Uncertain" Fallback Semantics

Status

Accepted

Context

docs/16 §14 gives a confidence-banding table (95-100 Extremely Reliable ... below 60 Uncertain) but doesn't clarify whether this is a third scoring system alongside `technical_score`/`smc_score`, or something conceptually different. Separately, docs/16 §3 lists "Uncertain" as one of eleven regimes, while §14 implies it's simply what any regime is called below 60 confidence - these readings conflict unless resolved.

Decision

The Market Regime Engine produces `RegimeConfidenceBreakdown` (deliberately not named "*Score*" per Phase 4C refinement) - `confidence` measures **how reliable this specific classification is** (trend clarity + volatility clarity + structural confirmation, minus stability/conflict penalties), never combined with `technical_score` (indicator agreement strength) or `smc_score` (institutional structure evidence strength). "Uncertain" is exclusively the fallback value returned when no candidate regime clears `MIN_CONFIDENCE_TO_QUALIFY` (ADR-039) - it is never a positively-detected condition in its own right.

Reason

Three engines now each produce a distinct measure (`technical_score`, `smc_score`, regime `confidence`) answering three different questions. Conflating any of them - or leaving "Uncertain" ambiguous between "a real market state" and "we're not sure" - would undermine the explainability every prior scoring ADR (ADR-028, ADR-036) has established as this project's convention.

Alternatives Considered

Option A: Treat "Uncertain" as a positively-detected regime with its own criteria - rejected, docs/16 never defines what would make a market genuinely "Uncertain" as opposed to simply low-confidence in every other category.

Option B (chosen): "Uncertain" as pure fallback; `confidence` as a distinct, non-competing classification-reliability measure.

Trade-offs

Pros

Removes the docs/16 §3-vs-§14 ambiguity cleanly.

Consistent three-engine separation of concerns (structure evidence vs. indicator evidence vs. classification reliability).

Cons

None identified - this is a clarifying, not a functional, decision.

Future Review

None expected.

---

# ADR-043

Title

Strategy Compatibility and AI Integration Are Documentation Guidance, Not Engine Output

Status

Accepted

Context

docs/16 §16 ("Strategy Compatibility": e.g. "Ranging -> Recommended: Mean Reversion") and §17 ("AI Integration," a narrative example combining regime with reasoning) both describe strategy-selection guidance - arguably a recommendation, which the Core Principle for this phase explicitly forbids ("No BUY/SELL recommendations. The engine classifies market conditions only.").

Decision

Confirmed on Phase 4C approval: §16 and §17 are excluded from `MarketRegimeEngine`'s output entirely. `MarketRegimeResult`/`MarketRegimeResponse` have no `compatible_strategies`, `recommendation`, or narrative field. They remain documentation notes in docs/16 for whichever future engine (Signal Engine, AI Orchestrator - Phase 6) decides what to do with a given regime classification.

Reason

Even an "evidence-only, non-binding" strategy list would still encode an opinion about what should be *done* with a regime, which is squarely the Signal Engine's/AI Orchestrator's job (ADR-005, ADR-008, ADR-031), not this classifier's. Keeping the boundary sharp here mirrors the same boundary already drawn for Technical Analysis (ADR-031) and SMC (implicitly, via evidence-only output).

Alternatives Considered

Option A: Include a non-binding `compatible_strategies` list, framed as descriptive metadata - considered, but rejected as still encoding a recommendation in substance if not in name.

Option B (chosen): Exclude both sections from engine output; retain them purely as documentation guidance.

Trade-offs

Pros

Unambiguous compliance with the "classification only, no recommendations" principle.

Cons

A future Signal Engine will need to independently re-derive strategy compatibility from docs/16 §16's guidance rather than reading it off this engine's response.

Future Review

Revisit only when the Signal Engine (Phase 6) is built and needs this mapping - implemented there, referencing docs/16 §16, not retrofitted onto this engine.

---

# ADR-044

Title

Market Regime Classification Stability

Status

Accepted

Context

Phase 4C's approval requested explicit documentation of hysteresis, minimum confidence before switching regimes, anti-oscillation behavior, and fallback handling - standard concerns for any classifier whose output could otherwise flicker between nearly-tied categories on small input changes. This sits in tension with ADR-038's statelessness decision, since true hysteresis conventionally requires remembering the previous classification.

Decision

Given the engine is stateless (ADR-038), true cross-request hysteresis (comparing to a persisted prior classification) is **not** implemented this phase. Instead, a same-request, fully deterministic anti-oscillation safeguard is implemented in `RegimeClassifier.classify()`:

- **Minimum confidence before switching**: only candidates at or above `MIN_CONFIDENCE_TO_QUALIFY` (60.0) are eligible to win at all (ADR-039).
- **Anti-oscillation margin**: the winning candidate is compared to the next-best *other* qualifying candidate (`runner_up`). If the margin is below `MIN_MARGIN` (10.0), the classification is still reported (no forced downgrade), but `RegimeConfidenceBreakdown.stability_penalty` is reduced proportionally and a `warnings` entry names both candidates near the boundary.
- **Fallback handling**: when no candidate qualifies, `regime` is `Uncertain` (ADR-039/ADR-042) with `confidence` reflecting the absence of any confirmed structural evidence.

Reason

Genuine hysteresis - resisting a *change* from the previously reported regime - needs memory of that previous call, which contradicts ADR-038's stateless decision. Rather than silently ignoring the stability requirement, or quietly reversing the persistence decision to support it, this ADR implements the strongest anti-oscillation safeguard available without persistence: requiring a clear margin of victory within the current evidence window, which still meaningfully dampens flicker on genuinely marginal/tied evidence (the case most likely to flip between adjacent, similarly-priced requests), while being honest that it does not reproduce true request-to-request memory.

Alternatives Considered

Option A: Add a minimal persisted "last regime" cache (not full event history) specifically to support true hysteresis - considered, but rejected for this phase since it would partially reverse ADR-038 for a benefit not yet demonstrated to be needed; revisitable if real request patterns show flip-flopping.

Option B (chosen): Same-request margin-based anti-oscillation, explicitly documented as distinct from true cross-request hysteresis.

Trade-offs

Pros

Fully deterministic and reproducible - the same candle window always produces the same stability outcome.

No persistence added for a benefit not yet observed as necessary.

Cons

Does not prevent flicker across genuinely different candle windows over time (e.g. as new candles roll into the lookback window) the way true hysteresis would.

Future Review

Revisit if real-world usage shows request-to-request regime flicker; the natural next step would be a minimal last-regime cache (per asset/timeframe) specifically for a hysteresis check, without adopting SMC-style full event persistence.

---

# ADR-045

Title

Confidence Engine Is Stateless (No Persisted Snapshot Table)

Status

Accepted

Context

Phase 4D's Confidence Engine (docs/15, docs/45) synthesizes a confidence result from Technical Analysis's, SMC's, and Market Regime's already-computed evidence. As with Technical Analysis (ADR-027) and Market Regime (ADR-038), a choice existed between persisting each computed confidence result or recomputing fresh on every request.

Decision

`AnalysisConfidenceEngine.analyze()`/`analyze_multi_timeframe()` are fully stateless - no new table, no migration. Every call recomputes from fresh Technical Analysis, SMC, and Market Regime results.

Reason

There is no "genuinely evolving single entity" here to justify persistence, the criterion this project has used consistently since SMC's persistence decision (ADR-032, BACKLOG.md §13) - a confidence result is a derived snapshot of three other engines' current state, not an entity with its own lifecycle. Persisting it would create a second source of truth with no clear rule for which is authoritative, the same reasoning ADR-027 already established for Technical Analysis.

Alternatives Considered

Option A: Persist every computed confidence result in a new `confidence_results` table - rejected, same reasoning as ADR-027: no clear benefit at this phase, and nothing downstream needs historical confidence snapshots yet.

Option B (chosen): Fully stateless, computed fresh per request.

Trade-offs

Pros

No schema/migration needed.

Guaranteed freshness - consistent with Technical Analysis's and Market Regime's statelessness.

Single source of truth (the three upstream engines' current output), not two.

Cons

Every request recomputes rather than reading a cached row - acceptable given the upstream engines are already fast enough for Technical Analysis's and Market Regime's own stateless designs.

No historical audit trail of past confidence results.

Future Review

Revisit only if a future phase (e.g. a Signal Engine wanting historical confidence trends) needs persisted confidence history - would need its own ADR, not a quiet addition.

---

# ADR-046

Title

Confidence Scoring Algorithm - Modular Weighted Components

Status

Accepted

Context

docs/15 v1.0's original scoring design assumed six weighted inputs (Technical Analysis, SMC, Economic Calendar, News Sentiment, Risk Management, Market Regime), three of which don't exist yet (Phase 5/6). A concrete, implementable formula was needed for the three engines that do exist, without hard-coding an assumption that no more will ever be added.

Decision

Seven weighted components, implemented in `app/services/analysis_confidence/confidence_aggregator.py`:

- Technical Analysis alignment: 25 (`technical_score / 100 * 25`)
- SMC alignment: 25 (`smc_score / 100 * 25`)
- Market Regime confirmation: 20 (`confidence / 100 * 20`)
- Cross-engine agreement: 20 (`agreement_ratio * 20`)
- Data completeness: 5
- Freshness: 5
- Conflict penalty: floored at -15

`combine()` accepts a list of named `WeightedComponent(name, score)` values rather than positional arguments, so Phase 5/6 (News Sentiment, Economic Calendar, Risk Management) can add new named components by extending the component list and `ConfidenceBreakdown`'s fields, without restructuring how components are summed/floored/capped.

Market Regime is weighted at 20, not equal to Technical Analysis's/SMC's 25, because `MarketRegimeEngine.analyze()` already consumes Technical Analysis's and SMC's evidence internally - equal weighting would double-count the same underlying evidence through two paths. For the same reason, volatility is not scored as an independent confidence factor here; it flows in only via Market Regime's own `confidence_breakdown.volatility_clarity` (folded into `regime_confirmation`), preventing a second, independent volatility penalty from double-counting the same market condition.

Reason

docs/15 v1.0's weighting table could not be implemented as-is (half its inputs don't exist). A complete formula for the three real inputs was required, designed to be extensible rather than requiring a rewrite when Phase 5/6's inputs arrive.

Alternatives Considered

Option A: Hardcode exactly three positional weight arguments (technical, smc, regime) - rejected, would require restructuring `combine()`'s signature (and every call site) the moment a fourth input is added.

Option B (chosen): Generic named-component list, extensible by construction.

Trade-offs

Pros

Phase 5/6 additions are additive (new components, new `ConfidenceBreakdown` fields), not a rewrite of the aggregation function.

Explainable per-component breakdown, matching the pattern established by ADR-028/036/042.

Cons

The exact point allocations (25/25/20/20/5/5/-15) are a considered but ultimately somewhat arbitrary judgment call, like every prior scoring ADR's weights - not derived from a backtest or statistical model.

Future Review

Revisit the weight allocation once real usage data exists to inform tuning, and when Phase 5/6 adds News Sentiment/Economic Calendar/Risk Management as new weighted components.

---

# ADR-047

Title

Confidence Engine Scope Limited to Technical Analysis, SMC, and Market Regime for Phase 4D

Status

Accepted

Context

docs/15 v1.0 listed Technical Analysis, SMC, News Sentiment, Economic Calendar, Risk Management, and Market Regime as inputs, and included BUY/SELL-oriented "Agreement Score" examples and penalty rules referencing data that doesn't exist (spread, upcoming economic events). This directly conflicted with the explicit Core Principle for this phase: the Confidence Engine evaluates evidence quality, it does not predict trade outcomes or issue recommendations.

Decision

Phase 4D's Confidence Engine consumes only Technical Analysis, SMC, and Market Regime - the three engines that exist. News Sentiment, Economic Calendar, and Risk Management are documented as future inputs (docs/15 §3), not implemented, not weighted, and not referenced as available. Every BUY/SELL-oriented example and formula in docs/15 v1.0 is removed and replaced with evidence-quality language consistent with ADR-031/ADR-043.

Reason

Implementing docs/15 v1.0 as written would have required either inventing data sources that don't exist (spread, economic events) or silently reintroducing BUY/SELL-style reasoning this project has deliberately kept out of every deterministic engine so far (ADR-031, ADR-043). Restricting scope to what's actually buildable, and stating the future inputs explicitly rather than silently, keeps the boundary clear for whoever builds Phase 5/6.

Alternatives Considered

Option A: Implement placeholder/stub scoring for News/Economic/Risk (e.g. always-neutral contributions) so the six-input structure could be "completed" now - rejected, adds complexity for inputs that don't exist and risks the stubs being mistaken for real evidence.

Option B (chosen): Three real inputs only; explicitly documented future inputs.

Trade-offs

Pros

Every input has real, implemented evidence behind it - no placeholder/stub scoring to be mistaken for real signal.

Matches this project's "never invent architecture" principle - Phase 5/6's actual News/Economic/Risk engines will define their own real evidence shape when built.

Cons

The weighting table will need revision when Phase 5/6 inputs arrive (mitigated by ADR-046's modular aggregation design).

Future Review

Revisit when News Sentiment, Economic Calendar, and/or Risk Management engines are built (Phase 5/6) - add their evidence as new weighted components per ADR-046, with a new ADR for the specific weight rebalancing.

---

# ADR-048

Title

`AnalysisConfidenceEngine` Naming Distinguishes It From `RegimeConfidenceEngine`

Status

Accepted

Context

`app/services/market_regime/confidence_engine.py`'s `RegimeConfidenceEngine` (Phase 4C) already exists and computes regime-classification confidence only (ADR-042). BACKLOG.md §14 explicitly flagged this naming collision risk when Phase 4C was approved: a bare `ConfidenceEngine` class for Phase 4D would be easily confused with it in imports, log messages, and conversation.

Decision

Phase 4D's top-level orchestrator is named `AnalysisConfidenceEngine` (`app/services/analysis_confidence_engine.py`), not `ConfidenceEngine`. The HTTP-facing route path (`/analysis/confidence/{symbol}`) is unaffected - user-facing naming and internal class naming aren't required to match 1:1 elsewhere in this codebase either (e.g. `MarketRegimeEngine` backs `/analysis/market-regime/{symbol}`, not `/analysis/market-regime-engine/{symbol}`).

Reason

`RegimeConfidenceEngine` answers "how reliable is this specific regime classification?" `AnalysisConfidenceEngine` answers "how trustworthy is the overall analysis across all three engines?" These are different questions with different callers, and a naming collision between them would be a recurring source of confusion for every future contributor and for AI-assisted development sessions re-deriving context.

Alternatives Considered

Option A: Rename `RegimeConfidenceEngine` instead, freeing up `ConfidenceEngine` for Phase 4D - rejected, would be a gratuitous breaking rename of already-shipped Phase 4C code for a naming preference, not a functional need.

Option B (chosen): New engine gets the disambiguating name; existing Phase 4C code is untouched.

Trade-offs

Pros

Zero risk of import/log confusion between the two engines.

No changes to already-shipped Phase 4C code.

Cons

Slightly longer class name than the original docs/15 sketch's bare `ConfidenceEngine`.

Future Review

None expected - revisit only if a future rename of either engine is independently justified.

---

# ADR-049

Title

`MarketRegimeEngine.analyze()` Accepts Optional Pre-Computed Technical Analysis/SMC Results

Status

Accepted

Context

`MarketRegimeEngine.analyze()` (Phase 4C) always calls `TechnicalAnalysisEngine.analyze()` and `SMCEngine.analyze()` internally. Phase 4D's `AnalysisConfidenceEngine` also needs both results directly (to reframe their scores into confidence terms) and additionally calls `MarketRegimeEngine.analyze()` for the third input - a naive implementation would compute Technical Analysis and SMC twice per confidence request.

Decision

`MarketRegimeEngine.analyze()` gains two new keyword-only parameters, both defaulting to `None`:

```python
def analyze(self, asset, timeframe, *, technical_analysis=None, smc=None) -> MarketRegimeResult:
    technical_analysis = technical_analysis or self._technical_analysis_engine.analyze(asset, timeframe)
    smc = smc or self._smc_engine.analyze(asset, timeframe)
    ...
```

`AnalysisConfidenceEngine` computes Technical Analysis and SMC once each and passes them in; every existing caller (the `/analysis/market-regime/*` routes, `analyze_multi_timeframe`) is unaffected since both parameters default to `None`, preserving the original always-recompute behavior exactly.

Reason

This is a small, additive, backward-compatible extension to already-shipped Phase 4C code, chosen over the alternative of accepting duplicate computation. Market Regime's own docstring already establishes the precedent of caching upstream results within one execution ("Both upstream engines are called exactly once per (asset, timeframe) within a single `analyze()` execution") - this ADR extends that same principle one level up, to cross-engine calls from Confidence.

Alternatives Considered

Option A: Accept the duplicate computation (Confidence Engine calls Technical Analysis/SMC/Market Regime independently, Market Regime recomputes Technical Analysis/SMC itself) - rejected, wastes work on every confidence request for no benefit, and both engines are non-trivial (Technical Analysis runs nine analyzers, SMC persists to `smc_events`).

Option B (chosen): Extend `MarketRegimeEngine.analyze()` with optional pre-computed parameters.

Trade-offs

Pros

Technical Analysis and SMC are each computed exactly once per confidence request (regression-tested in both `test_market_regime_engine.py` and `test_analysis_confidence_engine.py`).

Zero behavior change for any existing caller.

Cons

`MarketRegimeEngine.analyze()`'s signature is slightly more complex (two optional keyword-only parameters) for a need specific to one caller (Confidence Engine).

Future Review

None expected - revisit only if a future third caller needs a different pre-computation pattern.

---

# ADR-050

Title

News Provider Abstraction With Mock-First Implementation for Phase 5A

Status

Accepted

Context

docs/10_NEWS_SENTIMENT_ENGINE.md §3 lists 11+ candidate sources across three tiers (Reuters, Bloomberg, Associated Press, Forex Factory, Trading Economics, CoinDesk, and others), but no vendor, API, or cost has ever been confirmed anywhere in the documentation. docs/34_DATA_PROVIDER_SPECIFICATION.md's News section is a flat, unordered list of four names with no primary/fallback designation - unlike its own Economic Calendar section, which does distinguish Primary/Fallback. Phase 3A/3B already established a working precedent for exactly this situation: ship the engine against a deterministic mock provider first, then add a real vendor once one is chosen and provisioned.

Decision

Phase 5A defines a `NewsProvider` `Protocol` (`app/services/news/providers/base.py`), mirroring `MarketDataProvider`'s shape, with a single implementation shipped in Phase 5A: `MockNewsProvider` (`app/services/news/providers/mock.py`), a deterministic seeded generator that never fails. Real vendor integration (e.g. NewsAPI, Benzinga, Alpha Vantage News, GDELT) is explicitly deferred to a follow-up sub-phase, chosen with the user once a vendor is selected and an API key provisioned.

Reason

Building against an undecided, unconfirmed, and potentially enterprise-only-paid vendor (Reuters/Bloomberg) would either block Phase 5A indefinitely or force an uninformed vendor choice. Mirroring the Phase 3A (`MockMarketDataProvider`)/3B (`TwelveDataProvider`) split lets the engine, persistence model, and API contract be built and tested now, with the provider swapped in later behind the same Protocol - consistent with "never invent architecture" (no vendor is silently assumed) and with the project's own prior precedent for this exact situation.

Alternatives Considered

Option A: Pick a vendor now (e.g. NewsAPI's free tier) and integrate it directly in Phase 5A - rejected for this pass; the user was asked and chose to defer, keeping Phase 5A's scope focused on the engine/persistence/API design rather than also carrying a new external dependency's rate limits, auth, and normalization quirks in the same phase.

Option B (chosen): Mock-only for Phase 5A; real vendor is separate, explicitly scoped follow-up work.

Trade-offs

Pros

Phase 5A's engine, persistence, and API surface can be fully built and tested without waiting on vendor selection or key provisioning.

Directly reuses the Phase 3A/3B pattern and the `Protocol`-based provider abstraction already proven in `app/services/market_data/providers/`.

Cons

docs/10 §15's real-world SLA targets (breaking news <30s, normal <2min) cannot be validated against a mock provider - see ADR-051's Future Review and the architecture doc's explicit deferral of SLA validation.

Future Review

Revisit when a real news vendor is chosen and provisioned - add a real `NewsProvider` implementation (e.g. `app/services/news/providers/newsapi.py`) following `TwelveDataProvider`'s pattern (dedicated HTTP client module, provider-specific exception subclasses, `RateLimitedProvider` wrapping), and validate docs/10 §15's performance targets against it for the first time.

---

# ADR-051

Title

Deterministic Lexicon-Based Sentiment Scoring; AI Reserved Solely for the Narrative Summary

Status

Accepted

Context

docs/10_NEWS_SENTIMENT_ENGINE.md §7 defines a 5-value sentiment enum (Very Bullish/Bullish/Neutral/Bearish/Very Bearish) with confidence and reason, but never specifies a scoring method for it - §18 lists FinBERT only under "Future Enhancements." Every deterministic analyzer built so far (Technical Analysis, SMC, Market Regime, Confidence Engine) is fully deterministic; `app/services/analysis_confidence/summary_builder.py` additionally established a "template-only, no AI-generated text" precedent for narrative output. docs/10 §9 separately requires a maximum-150-word AI Summary (Summary/Market Impact/Affected Assets/Risk/Confidence) for each article, which is not naturally satisfiable by a template given it must synthesize free-form article content.

Decision

The 5-value sentiment label and its confidence score are computed by a deterministic keyword/lexicon-based scorer (`app/services/news_sentiment/sentiment_scorer.py`) - a hand-built financial polarity table with category-aware weighting - consistent with every other analyzer in the codebase. The required AI Summary (docs/10 §9) is generated by a single, isolated module (`app/services/news_sentiment/ai_summary_generator.py`) that calls OpenAI (`OPENAI_API_KEY`, already configured project-wide) only for that narrative text, under strict guardrails (never invent facts/quotes/numbers, must reference the source article, 150-word cap enforced), and degrades gracefully to `None` on any failure rather than blocking ingestion. The AI call never influences the sentiment label, confidence, category, importance, or affected-assets fields - those remain fully deterministic and unit-testable without live API calls.

Reason

This was presented to the user as an open decision (deterministic sentiment vs. AI-driven sentiment vs. no AI summary at all) precisely because it introduces the project's first non-deterministic, cost-per-call, harder-to-test code path, in direct tension with `summary_builder.py`'s established precedent. The user selected this option: keep sentiment scoring itself deterministic (preserving testability and the project's established analyzer pattern), and confine AI usage to the one requirement (docs/10 §9) that cannot reasonably be satisfied by a template, isolating the non-determinism to a single, narrowly-scoped, independently-mockable module.

Alternatives Considered

Option A: Deterministic lexicon scoring, no AI summary at all (defer docs/10 §9 entirely to Phase 6's AI Orchestrator) - considered and presented to the user; not chosen, since docs/10 §9 is an explicit Phase 5A requirement and Phase 6 does not yet exist to pick it up.

Option B: AI-driven sentiment scoring (OpenAI classifies sentiment directly, not just the summary) - considered and presented to the user; not chosen, since it would make every other engine's determinism inconsistent with this one and complicate testing (non-deterministic assertions, per-article API cost, harder CI reliability).

Option C (chosen): Deterministic lexicon scoring for sentiment; isolated AI call solely for the narrative summary.

Trade-offs

Pros

Sentiment/confidence/category/importance/affected-assets remain fully deterministic, unit-testable, and consistent with every other analyzer in the codebase.

The one AI-touching module is isolated, independently mockable in tests (`test_news_ai_summary_generator.py` never calls the real OpenAI API), and fails gracefully without blocking ingestion.

Cons

Introduces the project's first per-article LLM call and its associated cost, latency, and non-determinism, scoped narrowly to summary text only.

Future Review

Revisit if a future phase (e.g. Phase 6 AI Orchestrator) wants to consolidate all AI-generated narrative text (News summaries, future AI Reasoning Engine output) behind a single shared prompt/guardrail module rather than duplicating guardrail logic per engine.

---

# ADR-052

Title

News Persistence Model: Persisted Entities, One `news_sentiment` Row Per `news_article`

Status

Accepted

Context

Unlike Technical Analysis, SMC's stateless-analyzer-only aspects, Market Regime, and the Confidence Engine (all stateless per ADR-027/ADR-038/ADR-045), docs/03_DATABASE_DESIGN.md already reserves dedicated `news_sources`/`news_articles`/`news_sentiment` tables - raw articles and their sentiment results are real entities that must be queried after ingestion (`GET /news`, `GET /news/{id}`, `GET /analysis/news/{symbol}`), not recomputed per request. This makes News architecturally closer to SMC's persisted-`smc_events` pattern (ADR-032/033) than to the three stateless engines. Separately, docs/10 §7/§12 treats `affected_assets` as a list per article, raising a design question: one `news_sentiment` row per article (with `affected_assets` as a list column), or one row per (article, asset) pair.

Decision

News Sentiment follows SMC's persisted-entity pattern: `NewsSource`, `NewsArticle`, `NewsSentiment` are real SQLAlchemy models with dedicated repositories (`app/repositories/news_source_repository.py`, `news_article_repository.py`, `news_sentiment_repository.py`), not stateless recomputation. `news_sentiment` stores exactly one row per `news_article` (`article_id` is a unique foreign key), with `affected_assets` stored as a JSON list column - mirroring `SMCEvent.context`'s JSON-column pattern (mapped to a `metadata` DB column) rather than introducing a new normalized join table.

Reason

A per-article-per-asset table would be the "more normalized" choice, but nothing in docs/10 demonstrates a need for per-asset-divergent sentiment/confidence/reason within a single article (the vision doc's own worked example gives one sentiment for the whole article, with a list of affected assets) - introducing that complexity now would be speculative. The one-row-per-article design is simpler, matches the existing (if field-incomplete) docs/03 schema shape most closely, and is a strictly additive migration if per-asset divergence is needed later.

Alternatives Considered

Option A: One `news_sentiment` row per (article, asset) pair, via a normalized child table or composite key - rejected for Phase 5A as unsupported by any concrete requirement in docs/10; would add a table and query complexity for a need that hasn't been demonstrated.

Option B (chosen): One row per article; `affected_assets` as a JSON list column.

Trade-offs

Pros

Matches docs/03's existing table shape and SMC's proven JSON-metadata-column precedent.

Simpler queries (`GET /analysis/news/{symbol}` becomes a JSON-list-containment filter on one table, not a join).

Cons

If a future requirement needs per-asset-divergent sentiment from the same article (e.g. "Bullish USD, Bearish EUR" from one CPI release), this design would need a follow-up migration to a normalized child table.

Future Review

Revisit if per-asset sentiment divergence within a single article becomes a real, demonstrated product need.

---

# ADR-053

Title

Mixin Choice Per News Table

Status

Accepted

Context

BACKLOG.md §1 already tracks a project-wide documentation contradiction: docs/03 §1 requires every table to have both `created_at` and `updated_at`, but multiple per-table field lists (including, until this ADR, `news_sources`/`news_articles`/`news_sentiment`) show incomplete or no timestamp fields, resolved case-by-case via `CreatedAtMixin` (append-only/immutable rows) vs. `TimestampMixin` (mutable rows), per `app/database/mixins.py`.

Decision

- `news_sources` uses `TimestampMixin` - it is a small, admin-managed list where `priority`/`is_active`/`tier` can change after creation.
- `news_articles` uses `CreatedAtMixin` plus an explicit `published_at` column - once ingested, an article's own content and the source's publish timestamp are immutable historical facts; `created_at` (from the mixin) separately tracks our own ingestion time, `published_at` tracks the source's original publish time.
- `news_sentiment` uses `TimestampMixin` - a sentiment row can be recomputed in place (e.g. if scoring logic changes and historical articles are re-scored), so `updated_at` is meaningful here in a way it is not for `news_articles`.

Reason

This applies the same append-only-vs-mutable test already used for `SMCEvent` (ADR-033/037, mutable via status transitions) and the project's other `CreatedAtMixin` tables (audit logs, immutable-once-written), extended to the three News tables for the first time.

Alternatives Considered

Option A: `TimestampMixin` on all three tables uniformly, for consistency - rejected; `news_articles` genuinely has no legitimate "updated" state once ingested, and adding an unused `updated_at` would misrepresent the table's actual semantics, the same reasoning that justified `CreatedAtMixin`'s introduction for audit logs.

Option B (chosen): Mixin choice per table, based on each table's actual mutability.

Trade-offs

Pros

Resolves the news tables' entry in the project-wide timestamp-mixin contradiction (BACKLOG.md §1) rather than leaving a fourth undocumented instance of it.

Each table's mixin accurately reflects its real mutability.

Cons

None identified - this is a documentation/schema clarification consistent with existing precedent, not a new pattern.

Future Review

None expected - revisit only if `news_articles` gains a legitimate post-ingestion mutation path (e.g. manual admin correction), at which point it would need to move to `TimestampMixin`.

---

# ADR-054

Title

Deterministic Duplicate Detection: Normalized URL Match or Title-Similarity-Within-Time-Window

Status

Accepted

Context

docs/10_NEWS_SENTIMENT_ENGINE.md §10 specifies duplicate detection as "Same URL, Same Headline, Same Event, Same AI Hash" but never defines what an "AI Hash" is, what algorithm computes it, or what "Same Event" means distinct from URL/headline matching.

Decision

Duplicate detection (`app/services/news_sentiment/dedup_detector.py`) uses two concrete, deterministic checks, either of which marks a candidate article as a duplicate of an existing one: (1) exact match on a normalized URL (scheme-insensitive, tracking parameters stripped, trailing slash removed); or (2) normalized-title similarity above a fixed threshold AND `published_at` within a fixed time window of an existing article. No "AI Hash" or ML/LLM-based similarity is used.

Reason

The undefined "AI Hash" concept would either require inventing an undocumented algorithm or introducing a non-deterministic ML dependency for a task (near-duplicate detection) that is well-served by deterministic string similarity - consistent with every other analyzer in this codebase being deterministic (ADR-051).

Alternatives Considered

Option A: Implement some form of ML/embedding-based semantic similarity to catch "Same Event" duplicates that don't share a similar title - rejected for Phase 5A as unnecessary complexity without a demonstrated need; URL and title-similarity matching covers the dominant real-world duplicate case (the same wire story republished by multiple outlets with a near-identical headline).

Option B (chosen): Normalized URL exact match OR title-similarity-within-time-window.

Trade-offs

Pros

Fully deterministic and unit-testable with fixed input/output pairs.

Covers the dominant duplicate case (same story, multiple outlets) without any external dependency.

Cons

Will not catch genuine "same event, differently-worded headline" duplicates - accepted as an explicit limitation for Phase 5A.

Future Review

Revisit if false-negative duplicates (same event, dissimilar headlines) prove to be a real, measured problem once a real news provider is integrated (see ADR-050).

---

# ADR-055

Title

Category and Importance Classification via Deterministic Rule Tables

Status

Accepted

Context

docs/10_NEWS_SENTIMENT_ENGINE.md §5 defines 12 news categories and §8 defines a 5-value importance scale (Critical/High/Medium/Low/Ignore) with only worked examples (e.g. "FOMC → Critical"), not a formula.

Decision

Both classifications are computed deterministically: `category_classifier.py` assigns one of the 12 categories via keyword/pattern matching against title and content; `importance_scorer.py` derives importance from a rule table combining source tier (ADR-050/§3 of docs/10, now `NewsSource.tier`), category, and keyword-triggered escalation (e.g. any Tier-1-sourced Central Bank or War article floors at High regardless of other factors) - the concrete rule table is specified in docs/46_NEWS_SENTIMENT_ARCHITECTURE.md §5.

Reason

Consistent with ADR-051's deterministic-sentiment and ADR-054's deterministic-dedup decisions, and with every other analyzer in the codebase - this also makes docs/10 §8's worked examples testable as concrete unit test cases rather than left as prose illustrations.

Alternatives Considered

Option A: ML-based classification (e.g. a trained category/importance classifier) - rejected for Phase 5A as unnecessary complexity without training data or a demonstrated deterministic-rules shortfall.

Option B (chosen): Deterministic rule tables (source tier + category + keyword escalation).

Trade-offs

Pros

Fully deterministic, testable against docs/10 §8's own worked examples directly.

No training data or ML dependency required.

Cons

Rule tables are hand-tuned starting points, not empirically calibrated - consistent with every prior scoring ADR's caveat (028/030/035/036/037/042/046).

Future Review

Revisit once real usage data exists to inform rule-table tuning, consistent with every prior scoring engine's Future Review note.

---

# Review Policy

Review ADRs:

- Before major releases
- When introducing new infrastructure
- When replacing providers
- When changing AI models
- During annual architecture reviews