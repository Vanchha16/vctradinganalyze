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

# ADR-056

Title

Economic Calendar Provider Abstraction Uses `fetch_events(start, end)`, Not News's `fetch_latest(since)`

Status

Accepted

Context

`NewsProvider.fetch_latest(since)` (ADR-050) fetches articles already published - news only exists once it happens. Economic events are fundamentally different: a provider publishes a *schedule* of known future release times (with `forecast`/`previous` populated and `actual` still `None`) well before the event occurs, and the same event's `actual`/`status` change in place once released (and occasionally again on revision). A `fetch_latest(since)`-shaped provider interface cannot express "give me both the events already released in the recent past and the events scheduled in the near future" in one call.

Decision

`EconomicCalendarProvider` (`app/services/economic_calendar/providers/base.py`) is a `typing.Protocol` with `fetch_events(start: datetime, end: datetime) -> list[RawEconomicEvent]`, `health_check()`, and `capabilities()` - mirroring `MarketDataProvider`'s/`NewsProvider`'s shape everywhere except this one method's window-based signature. `MockEconomicCalendarProvider` is the only implementation shipped in Phase 5B (mirrors ADR-050's mock-first pattern); a real vendor (TradingEconomics, per the user's earlier stated preference) is explicitly deferred to a follow-up sub-phase.

Reason

Reusing `fetch_latest(since)` verbatim would either miss upcoming scheduled events entirely (if `since` is interpreted as "articles published after this time," there's no way to also ask for events scheduled ahead) or require a second, differently-shaped method bolted on - both worse than naming the actual contract this domain needs from the start. The rest of the provider abstraction (exception hierarchy, capabilities dataclass, mock-first-then-real-vendor pattern, skipping `RateLimitedProvider` for the mock) is reused unchanged from News (ADR-050) - only this one method's signature diverges, and only because the domain genuinely requires it.

Alternatives Considered

Option A: Reuse `fetch_latest(since)` and let the provider internally decide how far ahead to look - rejected, hides a meaningful behavioral parameter (the lookahead window) inside the provider instead of the caller, making the ingestion pipeline's window-tuning (ADR-058) impossible to control from one place.

Option B (chosen): `fetch_events(start, end)`, an explicit window.

Trade-offs

Pros

The ingestion pipeline (not the provider) controls the lookback/lookahead window, matching where `settings.economic_calendar_lookback_days`/`..._lookahead_days` actually live (ADR-058).

Every other part of the provider abstraction (exceptions, capabilities, mock-first) is reused unchanged from News, minimizing new surface area.

Cons

`EconomicCalendarProvider` is not a drop-in duck-type-compatible replacement for `NewsProvider` - a hypothetical shared `Provider` protocol across domains isn't possible without further abstraction, which isn't attempted here since it isn't needed.

Future Review

Revisit if a third data-source domain needs yet another window/latest shape - only generalize into a shared base Protocol once three real domains exist to compare, not speculatively from two.

---

# ADR-057

Title

`economic_events` Is a Single Mutable Table, No Separate `economic_sources` Table

Status

Accepted

Context

News Sentiment (ADR-052) has a normalized `news_sources` table because different outlets have genuinely different credibility tiers (Reuters vs. an unverified blog) that matter for scoring (ADR-055's importance rule table uses source tier as an axis). Economic data has no equivalent: a country's CPI release has exactly one canonical actual/forecast/previous value regardless of which provider reports it - there's no competing-outlet credibility question to model.

Decision

`EconomicEvent` (`app/models/economic_event.py`) is the only new table - `UUIDMixin` + `TimestampMixin`, with a plain `source: str` column (the ingesting provider's name, e.g. `"mock"`, later `"trading_economics"`) instead of a normalized sources table. `TimestampMixin` (not `CreatedAtMixin`, unlike News's `news_articles`) because `actual`/`surprise`/`status` are updated in place as an event moves through its lifecycle (ADR-058) - the closest persistence analog is `SMCEvent`'s mutable pattern (ADR-032/033), not News's append-only articles.

Reason

Per the project's "don't invent unnecessary tables" principle: a `economic_sources` table would exist only to hold a name and would add a join to every calendar query for no behavioral benefit, since importance/category classification here doesn't have a source-tier axis (ADR-059) the way News's does.

Alternatives Considered

Option A: Normalized `economic_sources` table, mirroring `news_sources` exactly for consistency - rejected; consistency-for-its-own-sake isn't a reason to model a distinction (source credibility tiers) that doesn't exist in this domain.

Option B (chosen): Single `economic_events` table with a plain `source: str` column.

Trade-offs

Pros

One fewer table and join for every query in this engine.

`TimestampMixin`'s mutability matches the domain directly - no contradiction between the mixin and the table's actual update pattern (the same "does this table's real mutability match its mixin" test already applied in ADR-053).

Cons

If a genuine multi-vendor-with-diverging-values scenario arises later (e.g. two providers reporting different `actual` values for the same release), this schema has no place to record provenance beyond the single `source` string - would need a follow-up migration.

Future Review

Revisit only if a second real provider is integrated and reports materially different values for the same event - until then, one canonical row per event is sufficient.

---

# ADR-058

Title

Ingestion Is Upsert-by-Natural-Key, Not News's Skip-on-Duplicate

Status

Accepted

Context

News's ingestion pipeline (ADR-054) skips a candidate article if it's a duplicate of an already-stored one - articles are immutable once published, so "already have it" means "nothing to do." Economic events are the opposite: the *same* event (identified by `(country, currency, event_name, release_time)`) is expected to be re-fetched repeatedly as it moves `SCHEDULED -> RELEASED` (actual value populates) and occasionally `-> REVISED` (a later re-fetch reports a changed `actual`) - re-fetching and skipping would mean forecast/actual/status data is silently never captured after the initial scheduling fetch.

Decision

`EconomicCalendarIngestionPipeline` fetches a window `[now - lookback_days, now + lookahead_days]` on every scheduled run (defaults: 7 days back, 30 days forward - `settings.economic_calendar_lookback_days`/`..._lookahead_days`) and **upserts** each returned event by its natural key via `EconomicEventRepository.get_by_natural_key` + update-in-place-or-create, rather than skip-if-exists. Only columns that actually changed are written (avoiding a no-op `updated_at` bump on every re-fetch of an unchanged scheduled event). A `status` transition to `REVISED` is set when `actual` changes on a row that already had a non-null `actual`.

Reason

This is the single most important behavioral divergence from News's ingestion pattern, and it exists because the domain's write semantics are genuinely different (mutable lifecycle vs. immutable published fact) - not a stylistic choice. The bounded window keeps the upsert payload small regardless of how much historical data eventually accumulates (docs/47 §14 performance note).

Alternatives Considered

Option A: Skip-if-exists, matching News exactly - rejected; would mean `actual`/`surprise`/`status` are never populated after an event's first (schedule-only) fetch, defeating the entire purpose of the engine.

Option B (chosen): Upsert-by-natural-key on every scheduled run.

Trade-offs

Pros

Correctly captures the full lifecycle (scheduled → released → occasionally revised) of every event with one simple, idempotent operation.

Bounded window keeps each run's payload small and predictable regardless of how far back historical data grows.

Cons

Every scheduled run re-writes/re-compares every event in the window, more DB work per run than News's insert-only-new-articles pattern - acceptable given the low event volume (dozens per day, not thousands) and the 15-minute default interval (ADR §6).

Future Review

Revisit the window sizes once real usage data shows how far in advance providers reliably schedule events and how often revisions occur.

---

# ADR-059

Title

Category and Importance Classification via Event-Name/Category Rule Tables, No Source-Tier Axis

Status

Accepted

Context

docs/14_ECONOMIC_CALENDAR_ENGINE.md §3 defines 7 category buckets (Inflation, Employment, Growth, Central Banks, Consumer, Housing, Other) and §4 defines 4 importance levels with worked examples only (e.g. "FOMC -> Critical", "PMI -> High"), not a formula - the same class of gap ADR-055 resolved for News, but without News's source-tier dimension (ADR-057: economic data has one canonical value per event, not competing outlets).

Decision

`category_classifier.classify(event_name) -> EconomicEventCategory` matches standardized event names/keywords (`"CPI"`, `"Non-Farm Payroll"`, `"FOMC"`, etc.) against the 7 buckets - closer to an exact/keyword lookup than News's scored classifier, since provider-supplied event names are standardized, not free-text headlines. `importance_scorer.score(category, event_name) -> EconomicEventImportance` derives importance from a rule table with event-name-specific overrides checked first (FOMC/Rate Decision/NFP/CPI/GDP always `CRITICAL` even though their bare categories alone wouldn't guarantee it), falling back to category-level defaults otherwise - the concrete rule table is specified in docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md §5.

Reason

Consistent with ADR-055's deterministic-classification precedent and every other analyzer in this codebase - and it directly encodes docs/14 §4's worked examples as testable rule-table entries instead of prose illustrations, the same benefit ADR-055 established for News.

Alternatives Considered

Option A: Reuse `NewsImportance`/a shared importance enum across News and Economic Calendar - rejected; ADR-048 already established that similarly-purposed types get disambiguated names to prevent conflation across engines with genuinely different scoring inputs (News: source tier + category; Economic Calendar: event-name overrides + category, no tier). `EconomicEventImportance` is a distinct enum.

Option B (chosen): Deterministic event-name/category rule tables, dedicated enum.

Trade-offs

Pros

Testable directly against docs/14 §4's own worked examples.

No source-tier axis to maintain, since it doesn't apply to this domain (ADR-057).

Cons

Rule tables are hand-tuned starting points, not empirically calibrated - consistent with every prior scoring ADR's caveat (028/030/035/036/037/042/046/055).

Future Review

Revisit once real usage data exists to inform rule-table tuning, consistent with every prior scoring engine's Future Review note.

---

# ADR-060

Title

Market Bias Is a Deterministic `(category, surprise_direction)` Rule Table, "Potentially" Language Only

Status

Accepted

Context

docs/14_ECONOMIC_CALENDAR_ENGINE.md §7 ("Market Bias") gives only two worked examples (lower CPI -> potentially weaker USD/stronger Gold/stronger Equities; higher CPI -> the inverse) and explicitly states "the engine stores the potential impact rather than guaranteeing market direction" - but no general algorithm exists for categories beyond Inflation, and no formal schema exists for the bias output beyond the §9 output example's ad hoc `{"USD": "Potentially Bearish", ...}` shape.

Decision

`bias_analyzer.analyze(category, surprise_direction) -> dict[str, MarketBias]` is a deterministic table keyed by `(category, surprise_direction)` generalizing docs/14 §7's CPI example across all 7 categories, returning a currency/asset-class-keyed bias map using only `POTENTIALLY_BULLISH`/`POTENTIALLY_BEARISH`/`NEUTRAL` values (never a bare `BULLISH`/`BEARISH`, preserving docs/14 §7's own "potential impact, not guaranteed direction" language) - the concrete table is specified in docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md §5. This is evidence output only - never a BUY/SELL/WAIT recommendation, consistent with ADR-031/ADR-043's project-wide precedent, and explicitly reserved from Confidence Engine/Risk Engine integration in this phase (ADR-047's boundary, docs/14 §11's "Risk Rules" belong to a future Risk Engine, not this one).

Reason

Without this table, docs/14 §7's concept would remain an unbuildable two-example illustration - the same situation ADR-051/ADR-055 resolved for News's sentiment/category/importance scoring. Generalizing the CPI example to all 7 categories, rather than only implementing Inflation and leaving the rest unhandled, keeps the engine's behavior uniform across every event category it classifies.

Alternatives Considered

Option A: Only implement bias for Inflation (the one category docs/14 §7 actually gives an example for), leave other categories without a bias output - rejected, would make the API's bias field unpredictably present/absent depending on category, worse than a uniform (if hand-tuned) table.

Option B (chosen): Generalize docs/14 §7's example into a full `(category, surprise_direction)` table covering all 7 categories.

Trade-offs

Pros

Uniform behavior across every event category the engine classifies.

Stays strictly in "potentially" language, preserving docs/14 §7's own stated boundary and this project's no-recommendation principle.

Cons

Bias mappings beyond the one documented CPI example are this project's own hand-tuned extrapolation, not sourced from docs/14 - flagged here explicitly as a starting point, not an authoritative macro-finance claim.

Future Review

Revisit once real usage/feedback exists to refine the bias table, and explicitly when a future Confidence Engine/Risk Engine integration ADR (per ADR-047) needs this evidence reframed into a weighted component.

---

# ADR-061

Title

Risk Window Is Computed at Read Time, Never Persisted

Status

Accepted

Context

docs/14_ECONOMIC_CALENDAR_ENGINE.md §8 defines a pre-event "risk window" (Critical: ±30min around release, High: -60min before) and §9's output example shows `"risk_window": true` as if it were a stored field. But whether "now" falls inside an event's risk window is a function of `(current time, release_time, importance)` that changes continuously as real time passes - a boolean column would be correct only at the instant it was last computed and stale immediately after, with no write ever triggered to keep it current (nothing "happens" at the moment a risk window opens or closes that would prompt an update).

Decision

`risk_window.is_in_risk_window(now: datetime, release_time: datetime, importance: EconomicEventImportance) -> bool` is a pure function with no persistence - computed fresh in the read path (`EconomicCalendarEngine`/the API response) every time an event is returned, never written to the `economic_events` table or cached.

Reason

Storing a time-relative boolean would be a correctness bug waiting to happen (return a stale `true` long after the window closed, or a stale `false` moments before it opens) for a value that costs nothing to compute on every read. This mirrors the general principle already applied to `MarketRegimeResult`/`ConfidenceResult`'s `calculated_at`-relative freshness reasoning (docs/45 §10) - anything that changes with wall-clock time and doesn't need to survive between requests shouldn't be a DB column.

Alternatives Considered

Option A: Store `risk_window: bool`, updated by a periodic job re-evaluating every row - rejected, adds a redundant background job and staleness window for a value that's already trivially cheap to compute per-read.

Option B (chosen): Pure read-time function.

Trade-offs

Pros

Always correct at the instant it's read - no staleness window, no extra background job.

Trivially unit-testable with fixed `now`/`release_time` inputs (`test_economic_risk_window.py`).

Cons

None identified - this is strictly simpler than the persisted alternative.

Future Review

None expected - revisit only if risk-window evaluation becomes expensive enough to need caching, which a boolean-from-two-timestamps comparison never will.

---

# ADR-062

Title

Risk Management Engine Evaluates a Caller-Supplied Candidate Trade Setup, Not a Persisted Signal

Status

Accepted

Context

docs/12_RISK_MANAGEMENT_ENGINE.md §1 frames the engine as evaluating "a potential trading signal" - but `signals` (docs/03 §11) is a Phase 6/7 table that doesn't exist yet, and no Signal Engine exists to produce one. This is the same category of gap ADR-047 resolved for the Confidence Engine: docs/15 v1.0 assumed inputs (News Sentiment, Economic Calendar, Risk Management) that didn't exist yet when Phase 4D was scoped.

Decision

`RiskManagementEngine.evaluate()` (`app/services/risk_management_engine.py`) takes a caller-supplied candidate trade setup directly as parameters - `asset`, `timeframe`, `direction`, `entry_price`, `stop_loss`, `take_profit`, and an optional `spread` - passed in the `POST /risk/evaluate` request body (docs/48 §4). No `Signal` object, persisted or otherwise, is read or required.

Reason

Restricting scope to what's actually buildable, and stating the assumption explicitly rather than silently, keeps the boundary clear for whoever builds the Signal Engine (Phase 6/7) later - the same reasoning ADR-047 used. A caller (a future Signal Engine, or a human testing a hypothesis) supplies the specific price levels it wants evaluated; this engine's job is exactly what docs/12 §1 says - judging whether *that* setup is safe, not inventing one.

Alternatives Considered

Option A: Wait until the Signal Engine exists and consume its output - rejected, blocks Phase 5C indefinitely on a phase (6/7) with no defined timeline, and the Risk Engine's own filters (volatility/spread/liquidity/correlation/RR/stop-loss) don't actually require a persisted Signal to evaluate - they only need specific price levels, which any caller can supply directly.

Option B (chosen): Accept the candidate setup as direct request parameters.

Trade-offs

Pros

Phase 5C is buildable and testable now, independent of the Signal Engine's timeline.

When the Signal Engine is eventually built, it becomes just another caller of this same `evaluate()` method - no redesign needed, it already accepts exactly the parameters a signal would carry (direction, entry, stop, target).

Cons

Until a Signal Engine exists, this endpoint's only callers are human/manual testing or a future Phase 6+ integration - no automated production caller yet.

Future Review

Revisit only if the eventual Signal Engine's candidate-setup shape diverges from `evaluate()`'s current parameters in a way that needs a wrapper or adapter.

---

# ADR-063

Title

Risk Management Engine Is Stateless - No New Table

Status

Accepted

Context

Unlike News (Phase 5A) and Economic Calendar (Phase 5B), which persist real entities, docs/03_DATABASE_DESIGN.md reserves no table for Risk Management at all - `risk_level`/`risk_reward` exist only as fields on `ai_analysis` (§10) and `signals` (§11), both Phase 6/7 tables. docs/12 §18 requires "Logging" (Trade Quality, Risk Level, Warnings, Rejected Reason, Execution Time) for every evaluation.

Decision

`RiskManagementEngine` is fully stateless (mirrors ADR-045's Confidence Engine precedent) - no new model, no migration, no repository. Every `evaluate()` call recomputes fresh from `AnalysisConfidenceEngine`, `NewsSentimentEngine`, `EconomicCalendarEngine`, and current candle data. docs/12 §18's logging requirement is satisfied by structured `structlog` logging of every evaluation (asset, setup, trade_quality, risk_level, warnings, rejected_reasons, execution time) - not a new database table.

Reason

docs/03 already tells us where this evidence eventually lives (`ai_analysis`/`signals`, Phase 6/7) - inventing an interim `risk_evaluations` table now would mean either migrating that data later or maintaining two homes for the same evidence. Consistent with "don't invent unnecessary tables" (ADR-057's precedent).

Alternatives Considered

Option A: A new `risk_evaluations` audit table, mirroring News/Economic's persisted pattern - rejected; docs/03 gives no indication this engine owns persisted state, and a query need for historical evaluations hasn't been demonstrated.

Option B (chosen): Stateless, structured logging only.

Trade-offs

Pros

No schema to maintain, no migration, no risk of stale/orphaned evaluation rows.

Matches the eventual home for this evidence (`ai_analysis`/`signals`) rather than creating a table that would need retiring later.

Cons

No queryable history of past evaluations until Phase 6/7 builds `ai_analysis`/`signals` and starts writing to them.

Future Review

Revisit when Phase 6/7 builds `ai_analysis`/`signals` - Risk Management's evidence becomes an input to what gets written there, not a table of its own even then.

---

# ADR-064

Title

Risk Management Engine Is Reuse-First: `AnalysisConfidenceEngine` Is the Primary Dependency

Status

Accepted

Context

docs/12 §3 lists Technical Score, SMC Score, Volatility, and Confidence Score as inputs. A code audit found every one of these already computed: `TechnicalAnalysisResult.technical_score`/`.strength` (`TrendStrengthLevel`), `SMCAnalysisResult.smc_score`/`.order_blocks`/`.liquidity_zones`, and - critically - `MarketRegimeResult.volatility.state` (`VolatilityRegimeState`: VERY_LOW/LOW/NORMAL/HIGH/EXTREME), which is an *exact* match for docs/12 §6's Volatility Filter scale, already built in Phase 4C. `AnalysisConfidenceEngine.analyze()` already computes all three (TA, SMC, Market Regime) in one call via ADR-049's pre-computation chaining, plus `overall_confidence`.

Decision

`RiskManagementEngine`'s primary dependency is `AnalysisConfidenceEngine`, not `TechnicalAnalysisEngine`/`SMCEngine`/`MarketRegimeEngine` individually. One `AnalysisConfidenceEngine.analyze(asset, timeframe)` call yields Technical Score, Trend Quality (`TrendStrengthLevel`), SMC Score, Order Blocks/Liquidity Zones, Volatility (`VolatilityRegimeState`), and Confidence Score in a single call. Docs/12 §6's Volatility Filter reuses `VolatilityRegimeState` directly - no new volatility classification is invented. Docs/12 §11's Trend Quality reuses `TrendStrengthLevel` (WEAK/MODERATE/STRONG/VERY_STRONG - four levels) rather than inventing docs/12's illustrative fifth "Very Weak" tier, which no upstream engine produces.

Reason

Mirrors docs/44 §5's "Market Regime is almost entirely derived from Technical Analysis's and SMC's already-computed evidence" reuse-first philosophy, and ADR-049's precedent of accepting pre-computed upstream results rather than re-deriving them. Inventing a second volatility or trend-strength classification scale that happens to look similar to an existing one would be a maintenance liability (two sources of truth for the same concept) for no benefit.

Alternatives Considered

Option A: Call `TechnicalAnalysisEngine`/`SMCEngine`/`MarketRegimeEngine` independently and re-derive a Risk-Engine-specific volatility/trend scale - rejected, duplicates already-solved classification work and risks the two scales silently drifting apart over time.

Option B (chosen): Depend on `AnalysisConfidenceEngine`, reuse its evidence and enums directly.

Trade-offs

Pros

Zero duplicate computation - `AnalysisConfidenceEngine` already computes TA/SMC/Regime exactly once each per call (ADR-049).

`VolatilityRegimeState`'s five values map onto docs/12 §6 with no translation layer needed.

Cons

`RiskManagementEngine` inherits `AnalysisConfidenceEngine`'s graceful-degradation behavior (missing upstream data becomes `None`, not a 404) - filters that need TA/SMC/Regime evidence must handle `None` gracefully too, propagating the same pattern one level further.

Docs/12 §11's five-level Trend Quality illustration is simplified to the four levels `TrendStrengthLevel` actually has - a deliberate simplification, not a literal implementation of the vision doc's example scale.

Future Review

None expected - revisit only if a Risk-Engine-specific need for volatility/trend granularity beyond `VolatilityRegimeState`/`TrendStrengthLevel` is demonstrated.

---

# ADR-065

Title

Spread Is an Optional Caller-Supplied Request Field, Never Internally Sourced

Status

Accepted

Context

docs/12 §7's Spread Filter requires a spread value, but no `spread` field exists anywhere in this project's data model - `app/schemas/market_data.py`'s `CandleResponse` docstring already documents this explicitly ("No `spread` field - it isn't part of the data model... so it's omitted rather than fabricated"). Spread is a live bid/ask-quote concept this platform has never sourced from any provider.

Decision

`spread` is an optional field on the `POST /risk/evaluate` request body (`app/schemas/risk_management.py`) - the caller supplies a live quote if it has one. `spread_filter.py` classifies it via price-relative percentage bands (Excellent/Acceptable/High/Extreme, docs/48 §5) when provided. When omitted, the Spread Filter is skipped entirely (neutral contribution to the Risk component, a `warnings` entry noting it was skipped) - never fabricated or defaulted to an assumed value.

Reason

Directly extends this project's existing "never invent data" precedent (the same reasoning that already kept `spread` out of `CandleResponse`) to the Risk Engine specifically. Classifying by price-relative percentage (not absolute pips) keeps the bands asset-class-agnostic without needing a per-symbol threshold table this project has no sourced data to calibrate.

Alternatives Considered

Option A: Silently default spread to zero or omit the filter's existence from the response - rejected; zero would misrepresent an unknown value as "excellent," and silently omitting the filter without a `warnings` note would hide that a real input was unavailable.

Option B (chosen): Optional request field, skipped-with-warning when absent.

Trade-offs

Pros

Consistent with `CandleResponse`'s existing "never fabricate spread" precedent.

Callers with a real live quote (e.g. a future broker-integrated caller) get full spread-aware evaluation; callers without one still get a complete evaluation of everything else.

Cons

Without a real market-data provider that reports spread, most callers in this phase will omit it and never exercise the Spread Filter's reject/reduce paths outside of tests.

Future Review

Revisit if/when a market-data provider integration (Phase 3B follow-up or beyond) starts reporting live spread - `PriceCandle`/quote data could then supply it automatically instead of requiring the caller to.

---

# ADR-066

Title

Liquidity Filter Uses a Relative-Volume-Ratio Proxy; True Liquidity and Holiday-Calendar Data Are Out of Scope

Status

Accepted

Context

docs/12 §10's Liquidity Filter needs Low/Normal/High/Excellent liquidity classification and rejects trading during "Holiday Sessions, Market Close, Abnormal Conditions" - but no order-book, market-depth, or holiday-calendar data source exists anywhere in this project. `PriceCandle.volume` is the closest available proxy, and it is itself optional/`None` for some providers (Technical Analysis already established a `VolumeState.UNAVAILABLE` precedent for exactly this situation).

Decision

`liquidity_filter.py` classifies liquidity via a relative-volume ratio (the latest candle's volume vs. its own recent rolling average) into Low/Normal/High/Excellent bands (docs/48 §5) when volume data is available; when `PriceCandle.volume` is `None`, the result is `UNKNOWN` (neutral contribution, not fabricated - mirrors `VolumeState.UNAVAILABLE`). "Market Close" is approximated via `session_classifier.py`'s `CLOSED` state (outside every named session) and triggers a hard reject, honoring ADR-014's veto authority. True holiday-calendar detection ("Holiday Sessions") is explicitly out of scope - no such data source exists to build it from.

Reason

A relative-volume ratio is fully deterministic and reuses data this project already stores, rather than fabricating a liquidity score with no underlying data. Approximating "Market Close" via session boundaries is a reasonable, buildable stand-in for a concept docs/12 never fully specifies how to detect.

Alternatives Considered

Option A: Skip the Liquidity Filter entirely until real order-book data exists - rejected; the volume-ratio proxy is a legitimate, deterministic, already-available signal, and skipping it entirely would leave docs/12 §10 completely unaddressed rather than partially and honestly addressed.

Option B (chosen): Volume-ratio proxy + session-based Market-Close approximation; true liquidity/holiday-calendar out of scope.

Trade-offs

Pros

Fully deterministic, uses only data this project already stores.

Consistent with the existing `VolumeState.UNAVAILABLE` precedent rather than inventing a different "missing data" convention for this engine.

Cons

A volume-ratio proxy is a coarser signal than genuine market depth/liquidity - flagged explicitly as a starting point, not a real liquidity model.

Future Review

Revisit if a market-data provider ever supplies genuine liquidity/depth data, or if a holiday-calendar data source is integrated.

---

# ADR-067

Title

Correlation Filter Computes Real Pearson Correlation for a Fixed Curated Pair List, Advisory-Only

Status

Accepted

Context

docs/12 §9's Correlation Filter needs to "avoid multiple highly correlated signals" (examples: EURUSD+GBPUSD, XAUUSD+Silver, BTC+ETH; reduce quality score if correlation > 0.85) - but this project has no portfolio or open-position tracking, so it cannot know whether the caller actually holds a correlated position elsewhere. No correlation data or model exists yet.

Decision

`correlation_analyzer.py` computes real Pearson correlation from stored `PriceCandle.close`-price return series (not raw closes, to avoid trivial correlation from shared scale/trend) over a fixed lookback window, for a fixed curated pair list matching docs/12 §9's own named examples (EURUSD↔GBPUSD, XAUUSD↔XAGUSD, BTCUSD↔ETHUSD). A pair is skipped if its counterpart asset isn't seeded in this deployment. Correlation above 0.85 contributes a `warnings` entry and a minor Risk-component score reduction - **never a hard reject**, since there is no position data to justify blocking a trade outright over a mathematical correlation alone.

Reason

Computing real correlation from real stored data (rather than a static hand-entered coefficient table) keeps this fully deterministic and grounded in this project's "never invent data" principle. Advisory-only (not a hard reject) directly matches docs/12 §9's own wording ("reduce quality score," not "reject") and is honest about what this project can and cannot know (correlation between two assets' price history, yes; whether the caller is actually exposed to both, no).

Alternatives Considered

Option A: A general market-wide correlation matrix computed across every asset pair - rejected as unnecessary complexity and computational cost for a filter that's advisory-only; docs/12 §9 itself only names three illustrative pairs, not a general model.

Option B (chosen): Fixed curated pair list, real Pearson correlation, advisory-only.

Trade-offs

Pros

Fully deterministic, real data, matches docs/12 §9's own illustrative scope exactly.

Bounded, predictable cost (three pair checks, not a market-wide scan) - docs/48 §14's performance note.

Cons

Only catches correlation within the three named pairs - a genuinely correlated pair outside this list (e.g. two minor forex crosses) isn't checked. Accepted as an explicit Phase 5C limitation.

Future Review

Revisit the pair list, or generalize to a broader/dynamic correlation model, once real usage demonstrates a need beyond the three docs/12 §9 examples - and revisit advisory-vs-reject once/if portfolio or open-position tracking exists to justify a harder rule.

---

# ADR-068

Title

Hard-Reject Rules Precede the Trade Quality Score Decision Matrix

Status

Accepted

Context

docs/12 defines both independent hard-reject conditions (§6 Extreme volatility, §7 Extreme spread, §8 Critical event <30min, §12 R:R below minimum, plus §10's Market Close via ADR-066) and a separate score-tier Decision Matrix (§16: 90+ Excellent ... below 60 Reject). ADR-014 already establishes "The Risk Engine has veto authority." Docs/12 doesn't specify how these two mechanisms combine, or whether multiple simultaneous hard-reject reasons should all be reported or just the first found.

Decision

`decision.py` evaluates every hard-reject rule first, independent of and prior to computing the Trade Quality Score's tier: extreme volatility (`VolatilityRegimeState.EXTREME`), extreme spread (only if `spread` was supplied), a critical economic event inside its risk window (`EconomicEventImportance.CRITICAL` + `risk_window=True`), risk/reward below the 1:2 minimum, an unrealistically tight stop-loss (< 0.5x ATR), and session `CLOSED`. **All** triggered hard-reject reasons are collected into `rejected_reasons` (not just the first match), and `approved=False` if the list is non-empty, regardless of the computed Trade Quality Score. Only when no hard-reject rule triggers does the score-tier Decision Matrix (§16) determine the tier (Excellent/Very Good/Good/Average) or a score-based Reject (<60). `trade_quality_aggregator.py` computes the 100-point score (Trend Quality 20 / Technical 20 / SMC 20 / Risk 20 / News 10 / Economic 10, docs/12 §15) independently of the hard-reject outcome, so the response always includes an explainable breakdown even when a setup is hard-rejected (mirrors ADR-041's "Confidence Must Be Explainable" principle extended to this engine).

Reason

Collecting all triggered reasons (not first-match) gives the caller a complete picture of why a setup was rejected in one response, rather than requiring them to fix one issue and resubmit only to discover another. Computing the score even on a hard-rejected setup preserves explainability (ADR-041's precedent) - a rejected setup's breakdown still shows *how close* it was, which is useful diagnostic information.

Alternatives Considered

Option A: First-match-wins hard-reject (stop at the first triggered rule) - rejected, less useful to the caller and inconsistent with how this project's other engines (e.g. `conflict_analyzer.py`) already collect every triggered condition rather than stopping at the first.

Option B: Skip score computation entirely once a hard-reject triggers (short-circuit) - rejected, loses explainability for rejected setups, which is exactly when a caller most wants to understand *why*.

Option C (chosen): Evaluate all hard-reject rules, collect every triggered reason, always compute the full score breakdown.

Trade-offs

Pros

Complete diagnostic information in every response, whether approved or rejected.

Consistent with this project's existing "collect all triggered conditions" pattern (`conflict_analyzer.py`) rather than introducing a new first-match convention.

Cons

Slightly more computation per rejected setup (the full score is still computed even though the setup is already rejected) - negligible given this engine's bounded, single-call cost profile (docs/48 §14).

Future Review

None expected - revisit only if a specific hard-reject rule's precedence or threshold needs adjustment based on real usage.

---

# ADR-069

Title

Strategy Engine (Phase 5D) Is the Consumer ADR-043 Anticipated - `MarketRegimeEngine` Remains Unchanged

Status

Accepted

Context

ADR-043 (Phase 4C) excluded `compatible_strategies`/`recommendation` fields from `MarketRegimeEngine`'s own output, and its Future Review note said this mapping should be "implemented [when] the Signal Engine (Phase 6) is built... not retrofitted onto this engine." But `docs/30_DEVELOPMENT_ROADMAP.md` lists the Strategy Engine as its own Phase 5D sub-phase, distinct from and prior to Phase 6's Signal Engine - and docs/17 §1 itself frames Strategy Engine as providing "structured recommendations *to* the Signal Engine," i.e. upstream of it, not identical to it. ADR-043's loose "Signal Engine (Phase 6)" phrasing didn't anticipate this intermediate phase.

Decision

The Strategy Engine (Phase 5D) is the consumer ADR-043's Future Review note anticipated - strategy-methodology classification (which of docs/17 §4's strategies fits current market evidence) is implemented here, as this engine's sole purpose. `MarketRegimeEngine` itself is **unchanged** - ADR-043 stands exactly as written; `MarketRegimeResult`/`MarketRegimeResponse` still have no `compatible_strategies` or recommendation field. Strategy Engine's own output is strategy-*methodology* classification only (e.g. "Trend Following fits current conditions with score 94") - never a BUY/SELL/WAIT or trade-level recommendation (ADR-031/ADR-043's principle extended here, not relaxed).

Reason

This is a documentation clarification, not an architectural reversal - it resolves an ambiguity in ADR-043's own wording (which conflated "a future engine" with "Phase 6" specifically) using information that didn't exist when ADR-043 was written (Phase 5D's scope wasn't yet defined). The underlying principle ADR-043 protects - deterministic engines don't issue recommendations - is preserved and extended, not weakened: Strategy Engine still stops short of BUY/SELL.

Alternatives Considered

Option A: Retrofit `compatible_strategies` onto `MarketRegimeEngine` directly, treating ADR-043 as overturned - rejected; `MarketRegimeEngine` already shipped (Phase 4C) with a specific evidence-only contract, and adding strategy-selection logic to a regime *classifier* would blur the same boundary ADR-043 was written to protect.

Option B (chosen): Build the classification in a new, dedicated Strategy Engine; leave `MarketRegimeEngine` untouched; clarify ADR-043's intent via this ADR.

Trade-offs

Pros

No breaking change to `MarketRegimeEngine`'s already-shipped, already-tested contract.

Resolves the documentation ambiguity explicitly, for future readers who might otherwise assume ADR-043 blocks Phase 5D entirely.

Cons

None identified - this is a clarification of intent, not a new constraint.

Future Review

None expected - revisit only if a future phase needs `MarketRegimeEngine` itself to expose strategy compatibility, which would require its own new ADR overturning ADR-043 directly.

---

# ADR-070

Title

Strategy Engine Is Stateless - No New Table

Status

Accepted

Context

Like Risk Management (ADR-063), docs/03_DATABASE_DESIGN.md reserves no table for the Strategy Engine - its output is evidence for a future Signal Engine/AI Orchestrator (Phase 6) to consume, not a domain entity this project persists itself. docs/17 §19 requires "Logging" (Selected Strategy, Rejected Strategies, Score, Execution Time, Version).

Decision

`StrategyEngine` is fully stateless (mirrors ADR-045/063) - no new model, no migration, no repository. Every `evaluate()` call recomputes fresh from `AnalysisConfidenceEngine`, `EconomicCalendarEngine`, and current candle data. docs/17 §19's logging requirement is satisfied by structured `structlog` logging of every evaluation, not a new database table.

Reason

Same reasoning as ADR-063: inventing an interim table now would either need migrating later (once Phase 6 defines where this evidence actually lands) or maintain two homes for the same evidence. Consistent with "don't invent unnecessary tables."

Alternatives Considered

Option A: A new `strategy_evaluations` audit table - rejected; no query need for historical evaluations has been demonstrated, and docs/03 gives no indication this engine owns persisted state.

Option B (chosen): Stateless, structured logging only.

Trade-offs

Pros

No schema to maintain, no migration.

Consistent with Risk Management's identical precedent (ADR-063), keeping Phase 5's stateless-engine pattern uniform.

Cons

No queryable history of past evaluations until a future phase defines where this evidence should live.

Future Review

Revisit when Phase 6 (Signal Engine/AI Orchestrator) is built and needs a persisted record of strategy evaluations feeding a signal.

---

# ADR-071

Title

Strategy Engine Reuses Risk Management's Sub-Modules Directly, Not `RiskManagementEngine.evaluate()`

Status

Accepted

Context

docs/17 §3 lists "Risk Management Engine" as an input, but `RiskManagementEngine.evaluate()` (ADR-062) requires a caller-supplied candidate trade setup (direction, entry price, stop-loss, take-profit) - data the Strategy Engine does not have and should not fabricate, since it evaluates *which methodology fits current conditions*, not a specific trade. Fabricating placeholder price levels purely to satisfy `evaluate()`'s signature would violate this project's "never invent data" principle (the same principle that kept `spread` optional rather than defaulted, ADR-065).

Decision

`StrategyEngine` imports and calls `app.services.risk_management`'s deterministic sub-modules directly - `session_classifier.classify()`, `liquidity_filter.classify()`, `economic_filter.analyze()` - none of which require a candidate trade setup, only asset/timeframe-level market evidence already available. `MarketRegimeResult.volatility.state` (already returned by `AnalysisConfidenceEngine.analyze()`) supplies the remaining risk-relevant evidence docs/17 needs. `RiskManagementEngine.evaluate()` itself is never called.

Reason

This satisfies docs/17 §3's "Risk Management Engine" input as "the risk-relevant evidence Risk Management is built from," which is what the vision doc's spirit actually needs (session/liquidity/economic-event/volatility context, not a specific trade's R:R or stop-loss validity) - without inventing data to force-fit a method signature designed for a different purpose (ADR-062's caller-supplied-setup scope).

Alternatives Considered

Option A: Call `RiskManagementEngine.evaluate()` with synthetic/placeholder entry-stop-target values derived from ATR - rejected; any such placeholder would be fabricated data flowing into hard-reject rules (R:R validation, stop-loss-too-tight) that were designed to evaluate a real trade, not a synthetic stand-in - directly against this project's "never invent data" principle.

Option B (chosen): Import and reuse `risk_management`'s asset/timeframe-scoped sub-modules directly; skip `RiskManagementEngine.evaluate()` entirely.

Trade-offs

Pros

No fabricated data anywhere in the evaluation path.

Reuses already-tested, already-shipped deterministic modules (`session_classifier`, `liquidity_filter`, `economic_filter`) with zero duplication.

Cons

Strategy Engine does not get Risk Management's trade-level checks (R:R validation, stop-loss-too-tight, spread) - by design, since those require a specific trade this engine doesn't evaluate.

Future Review

Revisit only if a future Signal Engine (Phase 6) needs Strategy Engine's output combined with a real `RiskManagementEngine.evaluate()` call once it has an actual candidate setup - that composition belongs in the Signal Engine, not retrofitted here.

---

# ADR-072

Title

Buildable Strategy Set: Merge Range Trading/Mean Reversion, Defer Momentum Trading, Resolve "Institutional Trend"

Status

Accepted

Context

docs/17_STRATEGY_ENGINE.md §4 lists 9 strategy names (Trend Following, SMC, Breakout, Pullback, Range Trading, Mean Reversion, Scalping, Swing Trading, Momentum Trading) but only 7 have a requirements section (§7-§13). "Range Trading" and "Mean Reversion" are never separately defined - §11's "Mean Reversion" section (Range Market, Strong/Weak Support-Resistance, Low Trend Strength) is clearly describing one strategy under two names. "Momentum Trading" has zero requirements defined anywhere. §8's SMC strategy names its best market as "Institutional Trend" - no such value exists in `MarketRegimeState`'s eleven values (docs/16 §3).

Decision

Seven strategies are implemented, one enum value each: `TREND_FOLLOWING`, `SMC`, `BREAKOUT`, `PULLBACK`, `MEAN_REVERSION` (merging "Range Trading"/"Mean Reversion" into one, since docs/17 never defines them separately), `SCALPING`, `SWING_TRADING`. `MOMENTUM_TRADING` is explicitly **not implemented** - no requirements exist anywhere in docs/17 to build it from, and inventing thresholds from scratch would violate "never invent architecture." §8's "Institutional Trend" is resolved to the regime set `{TRENDING_BULLISH, TRENDING_BEARISH, ACCUMULATION, DISTRIBUTION}` for the SMC strategy's Market Match gate (docs/49 §4) - the four `MarketRegimeState` values most consistent with SMC's own vocabulary (structural trend and accumulation/distribution phases, ADR-040's existing definition), not an invented fifth regime value.

Reason

Building only what docs/17 actually specifies (rather than inventing Momentum Trading's requirements or guessing which single regime value "Institutional Trend" meant) keeps this phase's deterministic rules traceable to the source document, consistent with every prior phase's practice of flagging vision-doc gaps rather than silently filling them with invented specifics.

Alternatives Considered

Option A: Invent requirements for Momentum Trading (e.g. RSI/MACD momentum thresholds) - rejected; nothing in docs/17 specifies what "Momentum Trading" requires beyond its name, and inventing a full requirements checklist from nothing would be architecture invention, not implementation.

Option B: Treat "Institutional Trend" as literally matching zero regime values (SMC strategy always gets 0 Market Match) - rejected; unhelpful, and inconsistent with docs/17 §8's clear intent that SMC strategy is meant to be viable under real market conditions.

Option C (chosen): Seven strategies with docs/17-sourced requirements; Momentum Trading deferred; "Institutional Trend" mapped to the four most SMC-consistent regime values.

Trade-offs

Pros

Every implemented strategy's requirements trace directly to docs/17's text - no invented thresholds.

Momentum Trading being absent is an honest gap, not a silently-wrong guess.

Cons

Users expecting all 9 named strategies (docs/17 §4) will find "Range Trading" and "Momentum Trading" unavailable as distinct results - documented explicitly in docs/17's own update (docs/49 §3) and the API's out-of-scope note.

Future Review

Revisit Momentum Trading once docs/17 is updated with real, specific requirements (not this project's own invention) - likely alongside a broader Strategy Engine v2 pass.

---

# ADR-073

Title

Market Match Scoring: Regime-Compatibility Gate With Timeframe Partial Credit

Status

Accepted

Context

docs/17 §14 allocates 30 of 100 points to "Market Match" but never specifies how it's computed - only §15's worked example implies a mismatched strategy still scores nonzero overall (Mean Reversion scores 42 in what's presumably a trending market, not 0), meaning Market Match itself, or the overall score, isn't a hard binary gate to zero.

Decision

`market_match.py` scores each strategy 0-30 via: 30 points if the current `MarketRegimeState` (from `AnalysisConfidenceEngine`'s `.market_regime`) is in the strategy's compatible-regime set (docs/49 §4's table) AND the requested timeframe is in the strategy's preferred-timeframes list (docs/17 §7/§8/§12/§13); 20 points if regime-compatible but the timeframe isn't preferred; 0 points if the regime itself is incompatible. A strategy scoring 0 on Market Match is not automatically rejected outright (ADR-076 handles rejection via the *total* score and Market Match specifically) - its Evidence Quality/Confidence/Risk/Historical Performance components still contribute, matching docs/17 §15's own worked example.

Reason

A hard "Market Match=0 means total=0" rule would make docs/17 §15's Mean Reversion=42 example impossible to reproduce - the components must be independently additive, with Market Match as one weighted contribution among several, not a multiplicative gate.

Alternatives Considered

Option A: Market Match=0 forces total score to 0 (multiplicative gate) - rejected, contradicts docs/17 §15's own worked example directly.

Option B (chosen): Market Match is one additive component (0/20/30); rejection (ADR-076) is a separate downstream decision based on the total score and/or Market Match specifically being 0.

Trade-offs

Pros

Reproduces docs/17 §15's own worked example's shape (a regime-mismatched strategy still scores meaningfully above zero).

Timeframe partial credit (20 vs 30) rewards regime-correct-but-suboptimal-timeframe strategies more than a binary pass/fail would.

Cons

The 20-point partial-credit threshold is a starting point, not calibrated against real trading outcomes - same caveat as every prior scoring table.

Future Review

Revisit the partial-credit split (20/30) once real usage data exists to inform tuning, consistent with every prior scoring ADR's caveat.

---

# ADR-074

Title

Evidence Quality Scoring: Deterministic Per-Strategy Checklists From Already-Computed Evidence

Status

Accepted

Context

docs/17 §7-§13 give each strategy a bullet-point "Requirements" list (e.g. Trend Following: EMA Alignment, Strong ADX, Healthy Volume, High Confidence) but no scoring formula. A code audit (docs/49 §2) found every requirement maps onto an already-computed field from Technical Analysis, SMC, or Market Regime - none require new computation.

Decision

Each of the seven strategies (ADR-072) gets a dedicated requirements-checklist module (`app/services/strategy/requirements/<strategy>.py`) that checks its docs/17-specified requirements against the shared `AnalysisConfidenceEngine` evidence bundle, returning `(met_count, total_count)` for Evidence Quality's 25-point component (`25 * met_count / total_count`). Requirements docs/17 mentions but this project has no data source for (Spread for Scalping, Risk/Reward for Swing Trading) are **excluded from the denominator entirely** - never defaulted to met or unmet, since fabricating either would misrepresent unavailable data as evidence (mirrors ADR-065's "never fabricate spread" precedent).

Reason

Consistent with every deterministic-rule-table ADR in this project (051/055/059/060/064) - build from what's genuinely computable, exclude what isn't, never fabricate. Excluding ungateable requirements from the denominator (rather than counting them as automatically failed) avoids unfairly penalizing every strategy for a project-wide data gap that has nothing to do with that specific evaluation.

Alternatives Considered

Option A: Count Spread/RR as automatically "not met" since no data exists - rejected; this would systematically and artificially lower Scalping's and Swing Trading's Evidence Quality scores for a project-wide data gap unrelated to actual market conditions, not a genuine strategy mismatch.

Option B (chosen): Exclude ungateable requirements from the denominator; score is `met / (total - ungateable)`.

Trade-offs

Pros

No strategy is unfairly penalized for a project-wide data gap (no spread/RR source) that isn't specific to its own requirements quality.

Every requirement actually checked traces directly to docs/17's own bullet list for that strategy.

Cons

Scalping's and Swing Trading's Evidence Quality is measured against a smaller checklist than docs/17 literally lists - documented explicitly here and in docs/49, not silently narrowed.

Future Review

Revisit once a market-data provider reports live spread (ADR-065's follow-up) - Scalping's Spread requirement could then rejoin the denominator.

---

# ADR-075

Title

Historical Performance Defaults to a Uniform Neutral Score - No Data Source Exists

Status

Accepted

Context

docs/17 §14 allocates 10 of 100 points to "Historical Performance," but this project has no persisted trade outcomes, signals, or backtest data anywhere (confirmed: no `signals`/`trades` table exists, Phase 6/7 territory) - there is nothing to compute a real historical performance score from for any strategy.

Decision

`historical_performance.py` returns a uniform neutral score (5 of 10 points) for every strategy, regardless of which strategy is being evaluated - not tuned per-strategy, since there's no data to differentiate them by.

Reason

Mirrors the Confidence Engine's docs/15 v1.0 §10 deferred-historical-calibration precedent exactly: "requires a persisted trade-outcomes dataset that doesn't exist... needs its own design pass (and likely a Signal Engine, Phase 6) before it's buildable" (BACKLOG.md §15). A uniform neutral placeholder is honest about the absence of real data, unlike a fabricated per-strategy score that would look like real historical evidence but isn't.

Alternatives Considered

Option A: Omit the Historical Performance component entirely, rescaling the other four to sum to 100 - rejected; docs/17 §14 explicitly allocates 10 points to it, and silently redistributing weights would diverge from the documented formula without an ADR specifically justifying that redistribution.

Option B (chosen): Keep the 10-point component in the formula; populate it with a uniform neutral placeholder (5/10) until real data exists.

Trade-offs

Pros

Preserves docs/17 §14's documented 100-point formula shape exactly (30/25/20/15/10), so a future real implementation is a drop-in replacement, not a formula redesign.

Explicit and honest about the placeholder nature - never presented as if it were real historical data.

Cons

Every strategy's total score is currently capped at 95 (100 - 5 points of "used but uninformative" placeholder), a minor but real ceiling until real data exists.

Future Review

Revisit once a trade-outcomes/backtest dataset exists (likely alongside a future Signal Engine, Phase 6/7) - implement real historical performance scoring then, replacing this placeholder.

---

# ADR-076

Title

Strategy Rejection and Ranking Rules

Status

Accepted

Context

docs/17 §15/§16 show worked examples of ranking (Trend Following 94, SMC 91, Pullback 82, Breakout 78, Mean Reversion 42) and a primary/alternative/rejected split, but never specifies the actual rejection threshold or ranking tie-break rule.

Decision

`ranking.py` rejects a strategy if either its Market Match component (ADR-073) is 0 (regime-incompatible - a strategy fundamentally wrong for current conditions, regardless of its other components) or its total score falls below 50 (a strategy that's regime-compatible but weak on every other dimension). Every rejected strategy carries an explicit reason string (e.g. "Market regime (ranging) is incompatible with Trend Following" or "Total score 38 is below the minimum threshold of 50"). Among non-rejected strategies, the primary strategy is the highest-scoring one; all other non-rejected strategies become `alternative_strategies`, ranked by score descending. Ties are broken by enum declaration order (deterministic, no randomness).

Reason

A dual rejection rule (regime-incompatible OR too-weak-overall) matches docs/17 §16's own worked example, where Mean Reversion (score 42, presumably regime-mismatched) is explicitly listed as "Rejected" while Breakout (score 78) is not - a single fixed score threshold alone wouldn't distinguish "wrong methodology for this market" from "right methodology, mediocre setup," but this project's evidence-quality/confidence/risk components could theoretically produce a low total for a regime-compatible strategy too, which the 50-point floor catches independently.

Alternatives Considered

Option A: Reject only below a fixed score threshold (e.g. 60, matching docs/12's Trade Quality Reject tier) - rejected; doesn't independently catch a Market-Match=0 strategy that happens to score above the threshold from its other components alone, which would misleadingly present a regime-incompatible strategy as viable.

Option B (chosen): Reject on Market Match=0 OR total score below 50; rank remaining by score descending.

Trade-offs

Pros

Catches both failure modes (wrong methodology for the regime; right methodology but weak setup) independently.

Deterministic tie-breaking (enum order) avoids nondeterministic output for equal scores.

Cons

The 50-point floor is a starting point, not empirically calibrated - same caveat as every prior scoring/threshold ADR.

Future Review

Revisit the 50-point floor once real usage data exists to inform tuning, consistent with every prior scoring engine's Future Review note.

---

# ADR-077

Title

Single `AIOrchestratorEngine` Class Resolves the "AI Orchestrator" vs "AI Reasoning Engine" Naming Ambiguity

Status

Accepted

Context

docs/07_AI_ORCHESTRATOR.md §3's pipeline lists "AI Reasoning Engine" as a distinct step, while §7's priority list separately names "AI Explanation." docs/13_AI_REASONING_ENGINE.md is titled and scoped as its own component ("transforms structured evidence into a professional market analysis"). Read together, the two vision docs describe two conceptually distinct responsibilities - collecting/combining engine outputs (docs/07) and narrating them (docs/13) - but never state whether these are two deployable components or one.

Decision

Phase 6A implements **one** engine class, `AIOrchestratorEngine` (`app/services/ai_orchestrator_engine.py`), combining both responsibilities. "Orchestration" (docs/07: collect context, compute the deterministic recommendation) and "reasoning" (docs/13: narrate that recommendation in prose) are sequential steps inside a single `generate(asset, timeframe)` call, not two separate services calling each other. docs/07's "AI Reasoning Engine" pipeline step and "AI Explanation" priority-list entry, and docs/13's entire scope, all refer to the same component in this implementation.

Reason

Splitting these into two classes would add a service boundary (and likely a second HTTP hop or in-process call) with no corresponding architectural benefit - both steps share the same input (`AnalysisContext`), run in the same request, and have no independent failure mode worth isolating behind a separate interface (unlike, say, the provider abstraction, which genuinely benefits from being swappable). One class keeps the "context in, `AIAnalysisResult` out" contract simple and mirrors every prior phase's single-top-level-engine convention (`RiskManagementEngine`, `StrategyEngine`, etc.).

Alternatives Considered

Option A: Two classes, `AIOrchestrator` (context/decision) and `AIReasoningEngine` (LLM narration), with the orchestrator calling the reasoning engine - rejected; adds an internal service boundary with no corresponding testing or reuse benefit, since nothing else in this codebase calls "reasoning" independently of "orchestration."

Option B (chosen): One `AIOrchestratorEngine` class internally composed of the deterministic modules (§ADR-078 onward) plus the provider call.

Trade-offs

Pros

Simpler dependency graph, one top-level engine to inject and test, consistent with every prior phase's convention.

Resolves the docs/07-vs-docs/13 naming ambiguity explicitly rather than leaving it open to reinterpretation each time this code is touched.

Cons

The class has more internal collaborators (context builder, recommendation decision, candidate setup builder, invalidation builder, evidence extractor, prompt builder, provider, response parser, repository) than any prior single engine - mitigated by each collaborator being its own small, independently-tested module (ADR-078 onward), with the engine class itself only sequencing calls.

Future Review

Revisit only if a genuine need arises to call "reasoning" independently of "orchestration" (e.g. a future batch endpoint that pre-computes context separately) - not anticipated in 6A.

---

# ADR-078

Title

Recommendation (BUY/SELL/WAIT) Is Computed by a Deterministic Decision Module, Never the LLM

Status

Accepted

Context

docs/13_AI_REASONING_ENGINE.md §6 gives BUY/SELL/WAIT conditions only in prose ("Bullish evidence dominates," "Risk acceptable," "No critical conflicts") with no algorithm. This session's explicit constraint states the AI "must NOT... invent strategies" and must "consume deterministic outputs only," and ADR-005/006/007 already establish that business rules remain deterministic and AI receives structured evidence only. Phase 6 is nonetheless the first phase authorized to actually produce a recommendation (BACKLOG.md §19) - the question is whether that recommendation is computed by the LLM (reasoning over evidence) or by code (evaluating evidence against fixed rules), with the LLM only narrating the result.

Decision

A new deterministic module, `recommendation_decision.py` (`app/services/ai_orchestrator/recommendation_decision.py`), computes BUY/SELL/WAIT from the already-built `AnalysisContext` via a fixed decision tree (docs/50 §5): no viable candidate setup → WAIT; `RiskEvaluation.approved is False` → WAIT (honoring ADR-014's pre-existing Risk Engine veto authority); `ConfidenceLevel` in {VERY_LOW, LOW} → WAIT; `conflict_severity is HIGH` → WAIT (directly implementing docs/13 §9's worked conflict example); otherwise BUY or SELL matching the candidate direction. The LLM is never asked to decide the recommendation - it receives the already-decided value and narrates why, mirroring exactly how `ai_summary_generator.py` (ADR-051) never influences News Sentiment's already-computed label.

Reason

This is the single most important boundary decision in Phase 6: it lets the project cross into recommendation-generation (a genuinely new capability) without violating "AI performs reasoning only" (ADR-005) even once. A deterministic decision tree is also testable with fixed inputs/outputs the same way every prior phase's scoring/decision modules have been (`risk_management/decision.py`, `strategy/ranking.py`) - an LLM-generated recommendation would not be.

Alternatives Considered

Option A: Let the LLM generate the recommendation directly from the serialized context, with a prompt instructing it to follow docs/13 §6's rules - rejected; even a well-instructed LLM call is not deterministic or reliably testable, and would be the first place in this entire project where a business decision (not just narrative text) depends on a non-deterministic call, directly contradicting ADR-005/006.

Option B (chosen): Deterministic decision tree computes the recommendation; the LLM narrates it.

Trade-offs

Pros

Recommendation generation is fully deterministic, testable, and auditable - the same value is produced for the same inputs regardless of LLM availability or variance.

The system can still return a complete, correct recommendation even if the LLM call fails entirely (ADR-081's graceful degradation) - only the narrative prose is affected.

Cons

The decision tree's specific thresholds (confidence bands, conflict severity gate) are starting points, not empirically calibrated - same caveat as every prior scoring/threshold ADR in this project.

Future Review

Revisit the decision tree's thresholds once real usage data exists to inform tuning, consistent with every prior scoring engine's Future Review note.

---

# ADR-079

Title

Confidence, Risk Level, and Execution Guidance Are Reused Verbatim, Never Recomputed or AI-Narrated Into a Number

Status

Accepted

Context

docs/07_AI_ORCHESTRATOR.md §11 says "Confidence is calculated from evidence" without specifying by whom or how - this session's explicit constraint states the AI must not "compute confidence" or "compute risk." `AnalysisConfidenceEngine` (Phase 4D) and `RiskManagementEngine` (Phase 5C) already compute these values deterministically and are already fully tested.

Decision

`AIOrchestratorEngine` never recomputes confidence, risk level, or position/execution guidance. `confidence_score`/`confidence_level` come directly from `AnalysisConfidenceEngine.analyze().overall_confidence`/`.confidence_level`; `risk_level` and `execution_guidance` come directly from `RiskManagementEngine.evaluate().risk_level`/`.position_guidance` (only when a candidate setup exists, ADR-080). The LLM's involvement with these values is limited to writing a prose sentence *about* an already-fixed number (e.g. "confidence is 78%, driven by strong technical/SMC alignment") - it never outputs a confidence value of its own, and the response parser (ADR-081) does not accept one even if the model tries.

Reason

Directly satisfies this session's explicit constraint and extends ADR-005/006/007's established boundary (AI never computes what a deterministic engine already computes) to the two fields most likely to be conflated with "AI judgment" in a recommendation system. Reusing Phase 4D/5C's already-shipped, already-tested engines is also simply less work and more reliable than reimplementing equivalent logic inside the orchestrator.

Alternatives Considered

Option A: Let the LLM produce its own confidence estimate to "double-check" or blend with the engine's score - rejected; introduces a second, non-deterministic confidence signal that could disagree with the deterministic one, undermining trust in either, and violates this session's explicit constraint outright.

Option B (chosen): Single source of truth per field, always the deterministic engine, never the LLM.

Trade-offs

Pros

Zero risk of the LLM producing a confidence/risk value that disagrees with, or is more/less conservative than, the deterministic engines' already-validated output.

Cons

None identified - this is a direct extension of an already-established project-wide principle.

Future Review

None expected - revisit only if a future phase deliberately wants an LLM-blended confidence score, which would need its own ADR explicitly overturning this one.

---

# ADR-080

Title

`candidate_setup_builder.py` Deterministically Resolves the Risk-Management-Needs-a-Setup Chicken-and-Egg Problem

Status

Accepted

Context

`RiskManagementEngine.evaluate()` (ADR-062) requires a caller-supplied candidate trade setup (direction, entry price, stop-loss, take-profit) to evaluate - but nothing upstream of the AI Orchestrator produces one. Strategy Engine (Phase 5D) faced the same shape of problem and resolved it by not calling `RiskManagementEngine.evaluate()` at all (ADR-071, reusing only its sub-modules). The AI Orchestrator's job is different: it must actually reach a BUY/SELL/WAIT recommendation, which - if not WAIT - genuinely requires real entry/stop/target prices to be useful at all (docs/07 §5's documented output includes them).

Decision

A new deterministic module, `candidate_setup_builder.py` (`app/services/ai_orchestrator/candidate_setup_builder.py`), builds a candidate trade setup **only if** `StrategyEvaluation.primary_strategy` is non-null and its implied direction (derived from `MarketRegimeResult.trend_regime.direction`) is unambiguous. `entry_price` = latest close; `stop_loss` = beyond the nearest support/resistance level or 1.5x ATR, whichever is more conservative (reuses `TechnicalAnalysisResult.support`/`.resistance`/`.volatility.atr`, invents no new data); `take_profit` = entry ± the greater of a 2:1 risk/reward multiple or the nearest opposing SMC structure. If Strategy Engine rejected every strategy, or direction is ambiguous, no candidate is built and `RiskManagementEngine.evaluate()` is never called - the recommendation is WAIT (ADR-078).

Reason

This is genuinely new deterministic logic this project didn't need before Phase 6, because no prior engine needed to propose a *specific* trade - only evaluate one already given to it (Risk Management, ADR-062) or judge methodology fit in the abstract (Strategy Engine, ADR-071). Building the candidate from already-computed Technical Analysis/SMC evidence (never inventing a price) keeps it consistent with every prior "never invent data" precedent in this project.

Alternatives Considered

Option A: Skip Risk Management entirely in the AI Orchestrator, the same way Strategy Engine does (ADR-071) - rejected; unlike Strategy Engine (which only judges methodology fit), the AI Orchestrator's whole purpose is to reach an actionable recommendation, and docs/07 §7/docs/13 §8 both rank Risk Engine as the highest-priority evidence source - skipping its actual `evaluate()` call (not just its sub-modules) would mean the recommendation never receives a genuine hard-reject check against a real, specific trade.

Option B (chosen): Build a genuine candidate setup deterministically, then call the real `RiskManagementEngine.evaluate()` against it.

Trade-offs

Pros

The recommendation's entry/stop/target prices, when present, have actually passed Risk Management's real hard-reject rules (extreme volatility, extreme spread-if-supplied, critical economic events, R:R below minimum, unrealistic stop distance) - not just Strategy Engine's softer methodology-fit checks.

Cons

The candidate-setup construction rules (stop distance, target multiple) are this project's own reasonable starting point, not sourced from any docs/12/17 formula written for this exact purpose - flagged explicitly, same caveat class as every prior hand-tuned rule table.

Future Review

Revisit the specific stop/target construction rules once real usage data exists to inform tuning.

---

# ADR-081

Title

`AIProvider` Protocol Abstraction; OpenAI Structured Output Enforced; One Retry Then Graceful Template Fallback

Status

Accepted

Context

docs/35_AI_PROMPT_ARCHITECTURE.md names a "Model Routing" concept with categories (Reasoning, Summarization, Educational, Conversation, Future Multi-Agent) but no routing logic, and never names a concrete provider. This session's review explicitly asks for a provider abstraction supporting future providers (Anthropic, Gemini, local) without changing orchestration logic. `app/services/news_sentiment/ai_summary_generator.py` (ADR-051) is this project's only existing LLM-call precedent: an isolated httpx-based OpenAI client with an injectable `transport` for testing, graceful `None` on any failure, never blocking its caller.

Decision

`AIProvider` (`app/services/ai_orchestrator/providers/base.py`) is a `typing.Protocol` (`name`, `generate(request) -> AIGenerationResponse`, `health_check()`), mirroring `NewsProvider`/`EconomicCalendarProvider`'s exact shape. `OpenAIProvider` (`providers/openai_provider.py`) is the sole real implementation for 6A, reusing `ai_summary_generator.py`'s httpx-Client-with-injectable-`transport` pattern, extended to request OpenAI's structured-output mode (`response_format: {"type": "json_schema", ...}`, supported by the already-configured `gpt-4o-mini`) so the model is constrained to the `reasoning` JSON schema at generation time. `MockAIProvider` (`providers/mock.py`) exists purely for test injection, mirroring `httpx.MockTransport`'s role in `test_news_ai_summary_generator.py` - not a production fallback. On a transient failure (timeout, 5xx), the provider is retried once (`ai_retry_max_attempts`/`ai_retry_backoff_seconds` settings, mirroring `market_data_retry_max_attempts`/`..._backoff_seconds`'s naming); on any further failure, or on a still-malformed response after one "return valid JSON" follow-up, the orchestrator falls back to a deterministic template `reasoning` (`summary_fallback.py`, mirrors `analysis_confidence/summary_builder.py`'s no-AI-text precedent) and sets `ai_available=False` - the request never fails outright.

Reason

The Protocol shape directly reuses a pattern already proven twice in this codebase (News, Economic Calendar); a future Anthropic/Gemini/local provider is a pure addition to `_PROVIDER_FACTORIES`, zero change to `AIOrchestratorEngine`. Structured output at the API level is strictly better than prompt-only JSON instructions for reducing malformed-response risk at the source, not just catching it after the fact. Graceful degradation (never a hard failure) is the direct, load-bearing consequence of "AI must never replace deterministic engines" (this session's core principle) - every field except `reasoning` is already fully computed before the provider is even called.

Alternatives Considered

Option A: No retry, fail the whole request if the LLM call fails - rejected; would make the entire recommendation (which is otherwise fully computed and correct) unavailable due to a transient LLM outage, directly contradicting the principle that deterministic engines remain authoritative regardless of AI availability.

Option B: Unlimited retries until success - rejected; unbounded latency/cost for a non-critical-path field (narrative prose only), with no benefit over one retry plus a safe fallback.

Option C (chosen): One retry, then graceful template fallback, never a hard failure.

Trade-offs

Pros

The response is always complete and correct on every field except `reasoning`, regardless of LLM/provider health.

Future providers require zero orchestration-logic changes, mirroring this project's two prior provider-abstraction precedents exactly.

Cons

`OpenAIProvider` is the only real (non-mock) implementation shipped in 6A - Anthropic/Gemini/local remain unimplemented until a real need and API key exist, the same "mock/real-provider split, real one deferred until needed" shape as ADR-050/056, except here the first real provider (OpenAI) already exists from Phase 5A rather than being deferred.

Future Review

Revisit when a second real provider is actually needed (cost, redundancy, or a specific model capability) - add it to `_PROVIDER_FACTORIES` following `OpenAIProvider`'s shape, no orchestration change required.

---

# ADR-082

Title

`ai_analysis` Is Persisted With `CreatedAtMixin` - the First Engine Output This Project Persists for Genuine Non-Reproducibility

Status

Accepted

Context

Every Phase 4/5 engine is stateless (or, for SMC/News/Economic Calendar, persists only genuinely new upstream facts) because re-running the same deterministic code against the same candle/event data reproduces the exact same result - there was never a reason to persist an *engine's own computed output* purely for later retrieval. An LLM call is different: even at low temperature, the exact narrative text is not perfectly reproducible on replay, and ADR-015 already requires "every AI decision must be replayable." `docs/03_DATABASE_DESIGN.md` §1 requires every table to have both `created_at` and `updated_at`, but §10's `ai_analysis` field list shows only `created_at` - the same class of contradiction already resolved case-by-case for `news_articles` (ADR-053), `smc_events`, and others.

Decision

`ai_analysis` (`app/models/ai_analysis.py`) is a new, genuinely persisted table using `UUIDMixin` + `CreatedAtMixin` (not `TimestampMixin`) - once generated, an analysis row represents "what was recommended at time X," never rewritten in place, the same append-only reasoning already applied to `news_articles`. Fields: `id`, `asset_id`, `timeframe`, `recommendation`, `confidence_score`, `confidence_level`, `risk_level`, `entry_price`/`stop_loss`/`take_profit` (nullable - null for WAIT), `reasoning` (JSON, the seven-section structure), `supporting_evidence`/`conflicting_evidence`/`risks`/`invalidation_conditions` (JSON lists), `execution_guidance`, `model_name`, `prompt_version`, `ai_available` (bool), `latency_ms`, `warnings` (JSON list), `created_at`. `signals` (docs/03 §11) is explicitly out of scope for 6A (ADR-084) - a future Signal Engine's own table.

Reason

This is the first engine output in the project where persistence is justified by genuine non-reproducibility, not mere convenience - resolves docs/03 §1's contradiction for this specific table using the same append-only reasoning already established, rather than leaving it open or defaulting to `TimestampMixin` without justification.

Alternatives Considered

Option A: Stay stateless like every prior engine, recompute on every request - rejected; the LLM-narrated portion is not reproducible, so "recompute on demand" would silently change historical analyses' wording on every re-fetch, directly undermining ADR-015's replayability requirement.

Option B (chosen): Persist with `CreatedAtMixin`, append-only.

Trade-offs

Pros

Satisfies ADR-015/ADR-018's replayability/versioning requirements directly (`prompt_version`/`model_name` recorded per row).

Consistent with the project's existing append-only-vs-mutable mixin decision framework (ADR-053/058), not a new convention.

Cons

First new migration since Phase 5B's `economic_events` - a real schema change, unlike every Phase 5C/5D engine (no new table).

Future Review

Revisit if a future need arises to mutate a stored analysis in place (e.g. marking it as acted-upon) - would need `TimestampMixin` or a separate mutable status table at that point, not retrofitted onto this append-only design speculatively now.

---

# ADR-083

Title

`POST /analysis/ai/{symbol}` Requires Authentication - the First Analysis-Family Route to Do So

Status

Accepted

Context

Every analysis-family route built so far (Technical Analysis, SMC, Market Regime, Confidence, News, Economic Calendar, Risk Management, Strategy) is public with no authentication. Phase 6A's endpoint is the first to invoke a real, paid LLM call on every request and the first to persist a new database row per request - both first-of-their-kind cost/abuse surfaces in this project.

Decision

`POST /analysis/ai/{symbol}` and `GET /analysis/ai/{id}` require an authenticated user, reusing the existing `get_current_user` dependency (`app/dependencies/auth.py`, Phase 2C) - no new authentication mechanism is built. `GET /analysis/history` is likewise authenticated and scoped to the requesting user.

Reason

Ties LLM cost to an identifiable account, a reasonable first checkpoint before any dedicated rate-limiting/quota infrastructure exists (BACKLOG.md already tracks that as unimplemented project-wide). Reuses the project's existing, already-tested authentication dependency rather than inventing a new authorization mechanism specific to this one route.

Alternatives Considered

Option A: Keep it public, consistent with every prior analysis route - rejected; unlike every prior route, this one has a real, non-negligible marginal cost per call and writes a new row per call, both of which are reasonable justifications for a different security posture than the free deterministic engines.

Option B (chosen): Require authentication via the existing `get_current_user` dependency.

Trade-offs

Pros

Ties cost to an identifiable account without inventing new rate-limiting infrastructure.

Reuses an already-shipped, already-tested dependency - zero new authentication code.

Cons

Breaks this project's prior "every analysis route is public" pattern - a deliberate, explicitly-flagged first exception, not an oversight.

Future Review

Revisit once real rate-limiting/quota infrastructure exists (tracked in BACKLOG) - authentication may then be paired with a per-user quota rather than being the sole cost-control mechanism.

---

# ADR-084

Title

Phase 6A Scope Boundary: AI Orchestrator and AI Reasoning Only; Signal Engine and AI Chat Assistant Deferred

Status

Accepted

Context

`docs/30_DEVELOPMENT_ROADMAP.md`'s Phase 6 lists four items - AI Orchestrator, AI Reasoning, Signal Engine, AI Chat - as one undifferentiated block, unlike every prior phase (1 through 5), which had explicit sub-phase decomposition (e.g. 5A-5D). The user's request for this session explicitly scoped work to "AI Orchestrator / AI Reasoning Engine."

Decision

Phase 6 is decomposed into sub-phases for the first time, mirroring the 4A-4D/5A-5D convention: **6A** (AI Orchestrator + AI Reasoning Engine, this session, one combined engine per ADR-077), **6B** (Signal Engine, not started), **6C** (AI Chat Assistant, not started), with a **6D** placeholder reserved if a further split proves necessary. `signals` (docs/03 §11), any batch analysis endpoint, and any chat/conversational interface are explicitly out of scope for 6A.

Reason

Every prior multi-part phase in this project was decomposed into sub-phases with their own documentation-first review before implementation (Phase 4: TA/SMC/Regime/Confidence; Phase 5: News/Economic/Risk/Strategy) - applying the same discipline to Phase 6 keeps scope bounded and each sub-phase's ADRs/architecture doc focused on one coherent unit of work, consistent with how this project has operated throughout.

Alternatives Considered

Option A: Build all four Phase 6 items in one undifferentiated pass - rejected; Signal Engine's and AI Chat Assistant's own architecture (persistence model, API surface, guardrails) haven't been documented or reviewed yet, and building them without that review would violate this project's consistent documentation-first practice.

Option B (chosen): Sub-phase decomposition (6A/6B/6C), each with its own documentation-first review.

Trade-offs

Pros

Keeps each sub-phase's scope, ADRs, and architecture doc focused and reviewable, consistent with every prior phase.

Cons

None identified - this is process discipline, not a technical trade-off.

Future Review

None expected - 6B (Signal Engine) and 6C (AI Chat Assistant) each begin with their own documentation review and implementation plan when scheduled, following this same process.

---

# ADR-085

Title

Signal Engine Is a Thin Wrapper Over AI Orchestrator, Not an Independent Evidence-Weighting Pipeline

Status

Accepted

Context

`docs/11_SIGNAL_ENGINE.md` (written before Phase 4-6 existed) describes the Signal Engine as an independent pipeline that collects raw evidence from every engine, applies its own weight distribution (Technical 35% / SMC 30% / Economic 15% / News 10% / Risk 10%), computes its own confidence score, resolves conflicts, and generates entry/stop/target from scratch (docs/11 §2-§13). Phase 6A's `AIOrchestratorEngine` (docs/50) already does almost all of this: `AnalysisConfidenceEngine` (ADR-046) owns cross-engine confidence weighting (a different, already-implemented scheme - Technical 25/SMC 25/Regime 20/Cross-Engine Agreement 20/Completeness 5/Freshness 5), `recommendation_decision.py` (ADR-078) owns the deterministic BUY/SELL/WAIT decision tree, and `candidate_setup_builder.py` (ADR-080) owns entry/stop/target construction. Building docs/11's pipeline as literally described would duplicate all of this.

Decision

`SignalEngine` (`app/services/signal_engine.py`) calls `AIOrchestratorEngine.generate()` exactly once and persists its result as a `Signal` row (docs/03 §11) - it introduces no new evidence weighting, confidence computation, or recommendation logic of its own. docs/11 §5's weight-distribution table and §16's flat output format are documented (docs/51 §1) as superseded by the already-implemented Confidence Engine + AI Orchestrator decision tree, the same treatment as docs/08 §9, docs/12's Signal-premise conflict, and docs/17's strategy-list corrections in prior phases.

Reason

This project's strongest precedent - reuse-first design - was already established by Strategy Engine (ADR-071, zero new external data sources) and AI Orchestrator itself (docs/50 §4, "no bespoke re-derivation of anything Phase 4A-5D already computes"). Signal Engine sits at the very top of the evidence pipeline (docs/02 §7's "Signal Generation" is the pipeline's last step), so by the time it runs, every input it could possibly want has already been computed by an upstream engine - there is nothing left for it to independently derive.

Alternatives Considered

Option A: Implement docs/11's independent weighted-evidence pipeline as literally written - rejected, this directly duplicates Phase 6A's already-built and already-tested decision logic, and would produce two different, potentially conflicting BUY/SELL/WAIT verdicts for the same market conditions (one from `AIOrchestratorEngine`, one from `SignalEngine`) with no principled way to reconcile them.

Option B (chosen): Thin wrapper over `AIOrchestratorEngine`, persisting its already-decided output.

Trade-offs

Pros

Zero duplicated decision logic; a signal's recommendation is always identical to its underlying `ai_analysis` row's recommendation, by construction.

Consequences

Positive

The strongest reuse ratio of any engine in this project - Phase 6B adds no new evidence source at all (docs/51 §7).

Negative

docs/11's independently-designed weight distribution and confidence formula are never implemented as written - acceptable since they were superseded by a more thoroughly reviewed, already-shipped design (ADR-046/078), not abandoned without replacement.

Future Review

None expected unless a future requirement genuinely needs a second, independent recommendation source to cross-validate against AI Orchestrator's - not currently anticipated.

---

# ADR-086

Title

A Signal Is a Persisted BUY/SELL Trade Call Only; WAIT Recommendations Produce No Signal Row

Status

Accepted

Context

`AIOrchestratorEngine.generate()` can return `Recommendation.WAIT` (ADR-011 - WAIT is a valid recommendation), with `entry_price`/`stop_loss`/`take_profit` all null (docs/03 §10). `docs/03 §11`'s `signals` table has no field capable of representing "no trade" - `signal_type`, `entry`, `stop_loss`, `take_profit` all presume an actionable direction.

Decision

`SignalEngine.generate()` persists a `Signal` row only when the wrapped `AIOrchestratorEngine.generate()` result is `BUY` or `SELL`. A `WAIT` result returns a `SignalGenerationResult` with `signal=None` - no row is written.

Reason

A "signal" is definitionally an actionable trade call (docs/11 §1: "generating the final trading recommendation" in the context of §9-§12's entry/stop/target generation) - a WAIT outcome is the *absence* of one, not a degenerate signal with null fields. The full reasoning for *why* a WAIT was reached remains fully available via the `analysis_id` (every `AIOrchestratorEngine.generate()` call persists an `ai_analysis` row regardless of recommendation, ADR-082) - nothing is lost by not also creating a `signals` row for it.

Alternatives Considered

Option A: Persist a `Signal` row for every recommendation including WAIT, with `signal_type=WAIT` and null entry/stop/target - rejected, `docs/03 §11`'s field list has no precedent for a directionless signal, and every downstream consumer of `GET /signals` (dashboard "latest signals," Telegram notification, bookmarking) expects an actionable trade, not a null one.

Option B (chosen): No row for WAIT; caller inspects `SignalGenerationResult.recommendation` directly.

Trade-offs

Pros

`signals` table stays exactly what its schema implies - actionable calls only. No nullable-signal_type special-casing needed anywhere downstream.

Cons

A caller polling `POST /signals/generate/{symbol}` on every WAIT outcome accumulates no persisted history of "we checked and it was WAIT" - only the underlying `ai_analysis` row (via `GET /analysis/history`) has that trail.

Future Review

Revisit only if a future requirement needs a queryable history of WAIT outcomes specifically through the `/signals` surface rather than `/analysis/history`.

---

# ADR-087

Title

Single Take-Profit Reused from AI Orchestrator; TP1/TP2/TP3 Splitting Deferred

Status

Accepted

Context

`docs/11_SIGNAL_ENGINE.md` §11 lists TP1/TP2/TP3 as the Take Profit output shape, but defines no formula for splitting a single target into three - no document anywhere in this project specifies one. `AIOrchestratorEngine`'s `candidate_setup_builder.py` (ADR-080) produces exactly one `take_profit` value (`entry -+ max(2x risk distance, nearest opposing SMC structure)`).

Decision

`Signal.take_profit` stores the single value reused verbatim from `AIAnalysisResult.take_profit`. TP1/TP2/TP3 splitting is not implemented.

Reason

Inventing a three-way split (e.g. 1x/2x/3x risk distance, or partial-close percentages) with no sourced formula would violate this project's "never invent architecture" rule - the same reasoning already applied to Strategy Engine's deferred Momentum Trading (ADR-072, zero defined requirements) and Risk Management's excluded Spread/RR requirements (ADR-074).

Alternatives Considered

Option A: Invent a TP1/TP2/TP3 formula now (e.g. 1x/2x/3x risk distance) - rejected, not sourced from any doc; would need to be recorded as an arbitrary starting point with no basis, unlike every prior scoring/threshold constant in this project (ADR-028/030/035 etc.), which at least extrapolated from a stated example or partial specification.

Option B (chosen): Single TP, matching AI Orchestrator exactly, deferred multi-target splitting.

Trade-offs

Pros

No arbitrary, undocumented formula introduced. `Signal.take_profit` is guaranteed consistent with the underlying `ai_analysis` row it derives from.

Cons

Does not fulfill docs/11 §11's literal three-level output - a real, acknowledged gap versus the original vision document.

Future Review

Revisit once a real requirement (e.g. a specific partial-close/scale-out strategy) defines a concrete TP1/TP2/TP3 formula to implement against.

---

# ADR-088

Title

Signal Status: ACTIVE (Written) and EXPIRED (Read-Time-Computed) Only; Remaining docs/11 §18 States Deferred

Status

Accepted

Context

`docs/11_SIGNAL_ENGINE.md` §18 defines eight signal statuses (Draft, Active, Triggered, Expired, Cancelled, Closed, Successful, Stopped Out). Reaching Triggered/Closed/Successful/Stopped Out requires live price-monitoring infrastructure that doesn't exist anywhere in this project (no scheduled task compares stored entry/stop/target against incoming candles), and their exact trigger semantics are undefined - `candidate_setup_builder.py` (ADR-080) always uses "latest close" as `entry_price`, so there is no meaningful distinction between a signal being "placed" and being "triggered" the way a genuine limit/stop order would have. Cancelled requires an admin/user action endpoint `docs/04` never specifies for signals.

Decision

`Signal.status` is written as `ACTIVE` at creation - the only value 6B's code ever writes. `EXPIRED` is computed at read time only (`app/services/signal/status_resolver.py`), comparing `created_at` against `settings.signal_ttl_hours` (default 24) - never persisted back to the row. The remaining six `SignalStatus` enum values are reserved (defined on the enum, reachable by a future phase without a migration) but unreachable through any 6B code path.

Reason

This mirrors Economic Calendar's `risk_window`/`market_bias` precedent exactly (ADR-060/061): a value that is a function of continuously-advancing wall-clock time is correct only at the instant it's computed and stale immediately after, so it must never be stored. Building genuine trigger/close/outcome detection now would mean inventing trigger semantics (touch vs. close, tolerance) with no specification to build against - the same category of gap already deferred for Risk Management's position tracking (ADR-067) and Strategy Engine's historical performance (ADR-075).

Alternatives Considered

Option A: Build full live-price auto-monitoring now (a new Celery task polling candles per open signal, transitioning status automatically) - rejected, requires inventing undefined trigger semantics, and is closer to Phase 7 (notifications/dashboard) territory than Phase 6B's scope.

Option B (chosen): ACTIVE (written) + EXPIRED (read-time-computed) only, remaining states reserved.

Trade-offs

Pros

No invented trigger semantics. Enum values reserved now mean a future phase can start writing them without a schema migration.

Cons

`GET /signals?status=successful` (or similar) returns nothing until a future phase implements outcome tracking - `signals` table's `triggered_at`/`closed_at`/`profit_loss` columns stay null indefinitely under 6B.

Future Review

Revisit once a live price-monitoring design (touch-vs-close trigger rule, tolerance, timeframe to monitor against) is specified - this needs its own design pass, not a quiet addition.

---

# ADR-089

Title

On-Demand Signal Generation via New Endpoint `POST /signals/generate/{symbol}`

Status

Accepted

Context

`docs/04_API_SPECIFICATION.md`'s original Signals section (added during Phase 6A's drafting, deferred per ADR-084) lists only `GET /signals`, `GET /signals/{id}`, `POST /signals/bookmark`, `DELETE /signals/bookmark/{id}` - all presuming signals already exist, implying a scheduled/proactive background generation model (matching docs/11 §17's lifecycle ending in "Notify Dashboard" / "Send Telegram", and News/Economic Calendar's Celery Beat ingestion-pipeline precedent). But no asset/timeframe "watchlist" or scheduling configuration exists anywhere in this project to drive an unattended generation job, and every prior LLM-cost-incurring action in this project (`POST /analysis/ai/{symbol}`, ADR-083) is a synchronous, caller-initiated, authenticated request - never a background job spending API budget with no request behind it.

Decision

Add `POST /signals/generate/{symbol}?timeframe=` (authenticated, mirrors `POST /analysis/ai/{symbol}`'s pattern exactly) as the mechanism that produces signals. `docs/04` is updated to add this endpoint's contract. A scheduled/proactive Celery Beat generation job is explicitly rejected for 6B.

Reason

An unattended job calling a real, metered LLM provider on a fixed schedule for a configured set of assets has real, ongoing cost implications and needs its own capacity/budget decision - not something to introduce as a side effect of building the persistence layer around an already-decided synchronous pattern. The on-demand model also keeps Signal Engine consistent with every other 6A endpoint a caller has already been using.

Alternatives Considered

Option A: Celery Beat scheduled generation, matching docs/04's literal (GET-only) endpoint list - rejected for 6B; would require a new "which assets/timeframes to auto-generate for" configuration surface that doesn't exist, and commits to an ongoing LLM spend schedule without an explicit budget decision from the user.

Option B (chosen): On-demand `POST /signals/generate/{symbol}`, added to docs/04 as a new endpoint beyond its original draft.

Trade-offs

Pros

Consistent with the already-shipped `POST /analysis/ai/{symbol}` pattern callers already understand. No new unattended-spend surface introduced without an explicit decision.

Cons

Diverges from docs/04's original (pre-implementation) Signals section, which assumed signals would already exist by the time `GET /signals` is called - `docs/04` is corrected accordingly (see docs/51 §6), the same "update docs to match the reviewed, implemented reality" practice as BACKLOG.md §7's prior examples.

Future Review

Revisit if a real requirement for proactive, unattended signal generation emerges (e.g. a dashboard "watchlist auto-scan" feature) - that would need its own budget/scheduling design, layered on top of this same `SignalEngine.generate()` method rather than replacing it.

---

# ADR-090

Title

`signal_bookmarks` Is an Inferred Join Table, Not Specified in docs/03

Status

Accepted

Context

`docs/04_API_SPECIFICATION.md` lists `POST /signals/bookmark` / `DELETE /signals/bookmark/{id}` (drafted during Phase 6A, deferred per ADR-084), but `docs/03_DATABASE_DESIGN.md` reserves no table for per-user signal bookmarks - `signals` itself has no `user_id` column (it is asset-scoped like every other analysis-engine output, not user-scoped).

Decision

Add `signal_bookmarks` (`app/models/signal_bookmark.py`): `id`, `user_id` (FK `users.id`, cascade), `signal_id` (FK `signals.id`, cascade), `created_at`, with a unique constraint on `(user_id, signal_id)`.

Reason

Follows `OAuthAccount`'s `(provider, provider_user_id)` uniqueness precedent (ADR-022) exactly - the same "inferred correctness requirement, not literally specified, recorded here per CLAUDE.md's 'never invent architecture' rule so the schema decision stays traceable" pattern.

Alternatives Considered

Option A: A `bookmarked_signal_ids` JSON array column on `User` - rejected, doesn't scale to indexed lookups ("is this signal bookmarked by this user," "list this user's bookmarks") the way a proper join table with a unique constraint does, and has no precedent anywhere else in this schema (every other many-to-many-shaped relationship in this project uses a real table, e.g. `watchlist_items`).

Option B (chosen): Dedicated `signal_bookmarks` join table with a uniqueness constraint.

Trade-offs

Pros

Standard, indexable many-to-many shape; prevents duplicate bookmarks at the database level, not just in application logic.

Cons

None identified; a unique constraint on this pair has no legitimate case for duplication, same reasoning as ADR-022.

Future Review

None expected unless bookmarks need their own metadata (e.g. a user note) beyond simple presence/absence.

---

# ADR-091

Title

`signals` Uses `CreatedAtMixin`; `created_at` Is an Inferred Addition Beyond docs/03 §11's Field List

Status

Accepted

Context

`docs/03_DATABASE_DESIGN.md` §11's `signals` field list (`id`, `analysis_id`, `asset_id`, `signal_type`, `entry`, `stop_loss`, `take_profit`, `risk_reward`, `confidence`, `status`, `triggered_at`, `closed_at`, `profit_loss`) includes no timestamp at all - the same class of gap BACKLOG.md §1 already tracks for several other tables against docs/03 §1's stated "every table needs created_at" default.

Decision

`Signal` (`app/models/signal.py`) uses `UUIDMixin` + `CreatedAtMixin`. `created_at` is written at generation time.

Reason

Needed for two concrete, load-bearing purposes, not just to satisfy docs/03 §1's general default: ordering `GET /signals`' "latest signals" response, and computing TTL-based `EXPIRED` status (ADR-088) - `status_resolver.py` has no other timestamp to compare against. A signal row is "what was generated at time X," never rewritten in place by 6B (ADR-086/088 - `triggered_at`/`closed_at` are separate, distinct timestamps for a future phase's outcome tracking, not an `updated_at`), the same append-only reasoning as `ai_analysis` (ADR-082) and `news_articles` (ADR-053).

Alternatives Considered

Option A: No timestamp column at all, matching docs/03 §11's literal (incomplete) field list - rejected, `EXPIRED` status computation and `GET /signals`' implicit recency ordering both have a genuine, immediate need for one; this is not a speculative addition.

Option B: `TimestampMixin` (created_at + updated_at) - rejected, a signal row's `status` is intentionally never rewritten by 6B's own code (ADR-088's `EXPIRED` is read-time-computed, never stored), and `triggered_at`/`closed_at` already serve as the future phase's mutation timestamps once outcome tracking is built - a generic `updated_at` would add no additional information.

Option C (chosen): `CreatedAtMixin` only.

Trade-offs

Pros

Matches the append-only precedent already established for `ai_analysis`/`news_articles`. Sufficient for both of 6B's actual needs (ordering, TTL expiry).

Cons

None identified.

Future Review

Revisit if a future phase's outcome-tracking work (ADR-088's deferred states) finds it needs a genuine `updated_at` beyond `triggered_at`/`closed_at` - not currently anticipated.

---

# ADR-092

Title

AI Chat Extends the Existing `AIProvider` Protocol with `generate_chat_reply()`, Not a New OpenAI Client

Status

Accepted

Context

`AIProvider.generate()` (Phase 6A, ADR-081) always forces OpenAI's structured-output JSON-schema mode and always sends exactly a fixed system+user message pair - built specifically for the seven-section `reasoning` document. AI Chat needs free-text, multi-turn replies (system prompt + prior conversation turns + a new question) - a genuinely different request shape, not a variant that could reuse `AIGenerationRequest`/`generate()` unmodified. The user's explicit instruction for this phase: reuse the existing OpenAI integration, do not build a second client, do not duplicate prompt-building logic.

Decision

Add one new method to the same `AIProvider` Protocol and the same `OpenAIProvider` class: `generate_chat_reply(request: AIChatRequest) -> AIChatResponse`, where `AIChatRequest` carries a `messages: list[ChatTurn]` (role + content) and `max_tokens`, with no `json_schema` field. `OpenAIProvider.generate_chat_reply()` shares the exact same `httpx.Client` construction (base URL, auth header, timeout, injectable transport) and the exact same status-code-to-exception classification as `generate()`, factored into a shared private helper - the two methods differ only in the request body sent to `/chat/completions` (a full message list, no `response_format`). `MockAIProvider` gains a matching method for test injection, mirroring its existing `generate()` mock.

Reason

`generate()` and `generate_chat_reply()` are two capabilities of the same integration (same API key, same base URL, same timeout, same error taxonomy), not two integrations - splitting them into a separate `ChatOpenAIProvider` class would duplicate every line of connection/error-handling logic that already exists and is already tested (`test_ai_openai_provider.py`). Extending the Protocol additively (a new method, `generate()` untouched) mirrors this project's established pattern for growing an interface without breaking existing callers (`MarketRegimeEngine.analyze()`'s optional keyword-only parameters, ADR-049).

Alternatives Considered

Option A: Force chat replies through `generate()`'s existing structured-output shape (e.g. a trivial one-field JSON schema wrapping the reply text) - rejected, forces every chat call through response_format machinery that exists specifically to constrain the seven-section reasoning document, and awkwardly encodes a free-text multi-turn conversation as a single user_prompt string, losing genuine multi-turn structure.

Option B: A new, separate `ChatAIProvider`/`ChatOpenAIProvider` class with its own `httpx.Client` construction - rejected, explicitly against this phase's brief ("do not create another OpenAI client"); would duplicate `OpenAIProvider`'s connection/auth/timeout/error-classification code for no benefit.

Option C (chosen): One new Protocol method, one shared client, one shared error-classification helper.

Trade-offs

Pros

Zero duplicated HTTP/auth/error-handling code. `AIProvider` remains the single interface every AI-dependent engine (`AIOrchestratorEngine`, now `AIChatEngine`) depends on, never a concrete provider class.

Cons

`AIProvider` now has two methods instead of one - a caller implementing the Protocol (e.g. a future Anthropic/Gemini provider, docs/50 §8) must implement both, even if a given use case only needs one. Judged acceptable since both existing use cases (Phase 6A, Phase 6C) are core to this project, not optional extensions.

Consequences

Positive

`AIOrchestratorEngine`'s existing `generate()` call path and every Phase 6A test are completely unaffected - purely additive.

Negative

None identified beyond the Protocol-surface growth noted above.

Future Review

Revisit if a third, materially different AI capability (e.g. embeddings, image analysis) is ever needed - at that point, consider whether `AIProvider` should split into narrower, capability-specific Protocols rather than continuing to grow one interface.

---

# ADR-093

Title

AI Chat Reuses `ContextBuilder` for All Engine Grounding - No New Evidence-Gathering Code

Status

Accepted

Context

This phase's brief requires AI Chat to be able to explain Technical Analysis, SMC, Market Regime, Analysis Confidence, News Sentiment, Economic Calendar, Risk Management, and Strategy Engine output - eight engines. `app.services.ai_orchestrator.context_builder.ContextBuilder.build(asset, timeframe)` (Phase 6A, docs/50 §3) already composes exactly this set (via `AnalysisConfidenceEngine`, which itself composes Technical Analysis/SMC/Market Regime; plus `NewsSentimentEngine`, `EconomicCalendarEngine`, `StrategyEngine`, and conditionally `RiskManagementEngine`) into one `AnalysisContext`, calling each engine at most once.

Decision

`AIChatEngine` calls `ContextBuilder.build(asset, timeframe)` directly - the identical call `AIOrchestratorEngine` itself makes - whenever a message resolves to a symbol/timeframe. No new evidence-gathering module, no bespoke per-engine calls, no re-derivation of any evidence field.

Reason

`ContextBuilder` already solves "give me everything Technical/SMC/Regime/Confidence/News/Economic/Strategy/Risk currently know about this asset/timeframe" - the exact question Chat needs answered before it can ground a reply. Writing a second context-assembly module would duplicate `ContextBuilder`'s composition logic (which engine to call, in what order, with what lookback windows) for no functional difference, directly contradicting this phase's explicit reuse-first instruction.

Alternatives Considered

Option A: Have `AIChatEngine` call each of the eight engines individually, selecting only what a given question seems to need - rejected, requires inventing a "which engines does this question need" classifier (no such taxonomy exists anywhere in this project, and building one is explicitly deferred per docs/22 §14's "Question Type" logging, ADR-098) and would still duplicate `ContextBuilder`'s existing composition.

Option B (chosen): Always call the same `ContextBuilder.build()` AI Orchestrator already calls, when a symbol/timeframe is resolved.

Trade-offs

Pros

Zero new evidence-gathering code. Grounding data is guaranteed to be exactly as fresh/consistent as what `AIOrchestratorEngine` itself would compute right now, since it's the literal same call.

Cons

Every symbol-scoped chat message pays the same computation cost as a full `AIOrchestratorEngine` context build (Technical/SMC/Regime/Confidence/News/Economic/Strategy, plus Risk if a candidate exists) even for a narrow question - judged acceptable given docs/50 §10's precedent that this cost is already fast enough not to need caching, and consistent scope beats a speculative "only fetch what's needed" optimization with no specified selection rule.

Future Review

Revisit if real usage shows most chat questions only need a small subset of `AnalysisContext` and the full build's cost becomes measurable - at that point, a documented question-classification rule (not an invented one) would be needed first.

---

# ADR-094

Title

AI Chat Explains Persisted `ai_analysis`/`signals` Rows - It Never Computes a New Recommendation

Status

Accepted

Context

"Why is this a BUY?" and "Explain this signal" both require an already-decided recommendation to explain. `AIOrchestratorEngine`/`SignalEngine` already own recommendation computation (ADR-078/085) - `AnalysisConfidenceEngine`'s confidence and `ContextBuilder`'s `AnalysisContext` (reused per ADR-093) do not by themselves include a BUY/SELL/WAIT verdict, since that verdict is `recommendation_decision.py`'s deterministic output, computed only inside `AIOrchestratorEngine.generate()`.

Decision

When a question is about a recommendation or a signal, `AIChatEngine` looks up the most recent persisted `ai_analysis`/`signals` row for the resolved asset/timeframe (via `AIAnalysisRepository`/`SignalRepository`, both read-only lookups) and gives that row's already-decided fields to the model as fixed facts to narrate - it never calls `AIOrchestratorEngine.generate()` or `SignalEngine.generate()` itself, and never re-derives a recommendation from `AnalysisContext`. If no persisted row exists yet, the assistant states that explicitly (docs/22 §13) rather than computing one on the fly.

Reason

Calling `AIOrchestratorEngine.generate()`/`SignalEngine.generate()` from inside a chat turn would mean every "why is this a BUY" question silently spends real LLM budget on a second, redundant reasoning generation (Phase 6A's own narration) just to answer a question about an *existing* decision, and could in principle produce an `ai_analysis` row with different reasoning prose than the one the user is actually asking about (a live market re-evaluation could disagree with the analysis from five minutes ago). Reading the already-persisted row, unmodified, is the only way to guarantee Chat's explanation matches what was actually decided.

Alternatives Considered

Option A: Trigger a fresh `AIOrchestratorEngine.generate()`/`SignalEngine.generate()` call whenever a question needs a recommendation, so the answer is always "current" - rejected, doubles LLM cost per relevant question, and risks the explained recommendation drifting from whatever the user is actually looking at on a dashboard (which would show the most recent persisted row, not a chat-triggered fresh one).

Option B (chosen): Read the most recent persisted row only; explicitly state unavailability if none exists.

Trade-offs

Pros

No duplicate recommendation-computation entry point. Guaranteed consistency between what Chat explains and what `GET /analysis/ai/{id}`/`GET /signals/{id}` would themselves return for the same row.

Cons

If no `ai_analysis`/`signals` row has ever been generated for an asset/timeframe, Chat cannot answer "why is this a BUY" - it can only state that no analysis exists yet and suggest generating one via the existing endpoints. Judged acceptable and honest (docs/22 §13's explicit unavailability-over-guessing rule) rather than silently triggering a hidden generation.

Future Review

Revisit only if a future UX requirement wants Chat to be able to trigger `POST /analysis/ai/{symbol}`/`POST /signals/generate/{symbol}` on the user's behalf mid-conversation - that would be a new, explicit action-taking capability requiring its own design and cost/authorization review, not a quiet default.

---

# ADR-095

Title

Two-Level Symbol/Timeframe Scoping - Conversation-Level "Current" (Mutable) + Message-Level "Referenced" (Immutable); Client-Supplied, Never NLP-Parsed

Status

Accepted

Context

docs/22 §10 expects the assistant to remember a "current asset"/"current timeframe" across a session (multi-turn continuity, e.g. "Compare with GBPUSD" after discussing EURUSD). This phase's brief (§6) separately requires each message to store its own "referenced symbol/timeframe." Neither document specifies how a symbol is identified from a user's free-text question (e.g. resolving "Gold" to `XAUUSD`, or extracting "EURUSD" from a full sentence) - no entity-recognition/symbol-resolution component exists anywhere in this project.

Decision

Two distinct fields, at two levels: `conversations.current_symbol`/`current_timeframe` (mutable - the conversation's current focus, updated whenever a message explicitly supplies a symbol/timeframe) and `messages.symbol`/`timeframe` (immutable once written - an audit-trail record of what actually grounded that specific exchange). The API accepts `symbol`/`timeframe` as **explicit, optional request fields** on `POST /chat/conversations/{id}/messages` - never parsed out of the free-text `content` string. If omitted, a message inherits the conversation's current values; if neither is ever set, the question is treated as general/educational, with no market grounding.

Reason

Building free-text symbol extraction (fuzzy-matching "Gold" to `XAUUSD`, disambiguating a bare "EURUSD" substring from surrounding prose) is a real NLP component this project has no precedent for and no specification of - inventing one now, un-reviewed, would violate "never invent architecture." Requiring the caller (the frontend, which already has a symbol picker for every other analysis endpoint) to supply the symbol explicitly is both simpler and matches every other endpoint in this project, none of which parse a symbol out of natural language.

Alternatives Considered

Option A: NLP-based symbol extraction from message text - rejected, no specification, no precedent, real risk of silent mis-resolution (extracting the wrong asset) feeding into a response the user trusts as grounded fact.

Option B: Single symbol/timeframe field on `conversations` only, no per-message record - rejected, doesn't satisfy this phase's explicit requirement (§6) that each message store its own referenced symbol/timeframe, and would make conversation history ambiguous once `current_symbol` changes mid-conversation (a past message's grounding would become unrecoverable).

Option C (chosen): Two-level fields, client-supplied only.

Trade-offs

Pros

No invented NLP component. Conversation history stays an accurate, non-retroactively-ambiguous record even as the "current" focus changes turn by turn.

Cons

The calling client is responsible for supplying `symbol`/`timeframe` explicitly (e.g. via UI selection) rather than the assistant "figuring it out" from a free-text question the way a more sophisticated system might - a real UX limitation versus docs/22's more conversational examples ("Analyze EURUSD" implicitly extracting "EURUSD").

Multi-asset comparison ("Compare Gold and Silver," docs/22 §5) is out of scope for the same reason - grounding is single-symbol-per-message.

Future Review

Revisit if a real symbol-resolution/entity-recognition component is designed and reviewed for this project (would likely also benefit search/watchlist features, not just Chat) - at that point free-text symbol inference could be layered on top of this same explicit-field mechanism as a convenience, not a replacement for it.

---

# ADR-096

Title

`conversations` and `messages` Are Inferred Tables, Not Specified in docs/03

Status

Accepted

Context

`docs/03_DATABASE_DESIGN.md` has no entry for a chat/conversation table anywhere, unlike `ai_analysis`/`signals`, which docs/03 v1.0 at least stubbed out before their respective phases built them. This phase's brief (§6) specifies what must be stored (conversation, messages, prompts/responses, timestamps, referenced symbol/timeframe, optional linked `ai_analysis`, optional linked `signal`) without a schema.

Decision

Add `conversations` (`UUIDMixin` + `TimestampMixin` - `title`/`current_symbol`/`current_timeframe`/`status` all mutate after creation, unlike every append-only table in this project) and `messages` (`UUIDMixin` + `CreatedAtMixin` - a sent message is never edited). `messages.ai_analysis_id`/`signal_id` are nullable FKs with `ON DELETE SET NULL` (not `CASCADE`) - see docs/52 §6 for the full field list and the reasoning for `SET NULL` specifically.

Reason

Follows this project's established practice (ADR-022/024/032/090/091) of building inferred schema explicitly, documented via ADR, when a phase's brief requires persistence docs/03 never specified - never invented silently.

Alternatives Considered

Option A: Single `messages` table with no separate `conversations` parent (each message a standalone row with a `session_id` string) - rejected, this phase's brief explicitly asks for `create conversation`/`list conversations`/`get conversation`/`delete conversation` API operations (§7), which need a first-class `conversations` entity with its own lifecycle (title, status, current focus), not just a grouping key on `messages`.

Option B (chosen): `conversations` parent + `messages` child, standard one-to-many.

Trade-offs

Pros

Matches every other parent/child persistence shape in this project (`ai_analysis` has no children, but `smc_events`/`price_candles` are asset-scoped the same way `messages` are conversation-scoped). Conversation-level mutable state (`current_symbol`, `title`, `status`) has an obvious home.

Cons

None identified.

Future Review

None expected unless a future requirement needs conversation-level metadata beyond what's listed here (e.g. shared/collaborative conversations) - not currently anticipated.

---

# ADR-097

Title

Conversation Deletion Supports Both Hard Delete and Archive

Status

Accepted

Context

This phase's brief (§7) asks for a "delete/archive conversation" endpoint without specifying which, or both. Every prior soft-deletable entity in this project (`SMCEvent`, `EconomicEvent`) uses status-transition-only, never a real SQL delete, because that data is market evidence this project's own architecture never lets a user destroy. Conversations are different: they are private, per-user data (like a user's own account, docs/23's `DELETE /users/account`, listed in docs/04 though not yet built) - a user has a legitimate interest in genuinely removing their own conversation history, not merely hiding it.

Decision

Both are implemented: `POST /chat/conversations/{id}/archive` (soft - `status=ARCHIVED`, excluded from the default `GET /chat/conversations` listing, still retrievable by id) and `DELETE /chat/conversations/{id}` (hard - a real delete, cascading to every `messages` row via `ON DELETE CASCADE`).

Reason

"Archive" and "delete" answer different real needs (declutter a conversation list vs. genuinely remove private data) and this project already has a clean precedent for each shape (`SMCEvent`'s status lifecycle for archive; standard cascade-delete FKs, e.g. `AIAnalysis`→`Signal`, for hard delete) - implementing only one would leave the other need unmet without a documented reason to exclude it.

Alternatives Considered

Option A: Archive only, no hard delete - rejected, conversations are private user data, not shared market evidence; a user should be able to actually remove their own chat history, consistent with `docs/04`'s already-listed (if not yet built) `DELETE /users/account`.

Option B: Hard delete only, no archive - rejected, doesn't give a lightweight "get this out of my active list without losing it" option, which docs/22 §10's session-continuity framing implies users may want (returning to an old conversation later).

Option C (chosen): Both, as two distinct endpoints.

Trade-offs

Pros

Covers both real use cases without conflating them into one ambiguous "delete" action.

Cons

Two endpoints to build/test instead of one - judged worth it given the two behaviors are genuinely different (reversible vs. not).

Future Review

None expected.

---

# ADR-098

Title

Feedback Rating, Question-Type Classification, and Engines-Used Logging Deferred (docs/22 §14/§15)

Status

Accepted

Context

docs/22 §14 ("Logging") asks for "Question Type," "Engines Used," and "Feedback Score" to be stored alongside every conversation turn; §15 ("User Feedback") asks for a Helpful/Not Helpful/Report Issue rating users can attach to a response, intended to "improve future prompts and explanations." Neither this phase's brief (which lists a concrete, narrower persistence/API scope in §6/§7) nor any other document in this project specifies a question-type taxonomy, a rule for which engines were "used" for a given free-text question, or what mechanism would actually consume feedback scores to improve prompts.

Decision

None of the three are implemented in Phase 6C. `messages` stores `model_name` (satisfying the one concrete, buildable piece of §14 - "Model Version") and relies on this project's existing structured-logging convention (ADR-019) for execution-time observability at the request-handling layer. Question-type classification, engines-used tracking, and feedback rating are explicitly deferred.

Reason

Each of the three would require inventing something this project has no basis for: a question-type taxonomy (what are the categories, and how is a free-text question classified into one - the same "no NLP component exists" gap as ADR-095), an "engines used" rule (§2's `ContextBuilder` reuse means every symbol-scoped question always touches the same eight engines - there's no per-question variation to log meaningfully yet), and a feedback-consumption pipeline (§15 says feedback "may improve future prompts" without saying how - storing a rating with no defined consumer would be dead data). This mirrors this project's consistent practice of deferring components a phase's brief doesn't concretely specify (Strategy Engine's Momentum Trading, ADR-072; Risk Management's position tracking, ADR-067) rather than building a speculative placeholder.

Alternatives Considered

Option A: Add a `feedback_score` column to `messages` now, with no consuming logic, for future use - rejected, dead data with no defined meaning is worse than no column; matches this project's general aversion to speculative schema (BACKLOG.md's repeated "don't add placeholder scoring speculatively" notes, e.g. §15/§16 on Confidence/News Engine).

Option B (chosen): Defer all three, document the gap explicitly.

Trade-offs

Pros

No speculative, unconsumed schema. Every column added in this phase has a concrete, currently-exercised purpose.

Cons

docs/22 §14/§15 remain unimplemented - a real, acknowledged gap versus the original vision document, same category as Signal Engine's TP1/TP2/TP3 deferral (ADR-087).

Future Review

Revisit once a concrete question-type taxonomy and a real feedback-consumption mechanism (e.g. feeding low-rated exchanges into prompt refinement) are specified - this needs its own design pass.

---

# ADR-099

Title

Frontend Auth Token Storage: Client-Side (In-Memory Access Token + localStorage Refresh Token), No Backend Cookie Changes

Status

Accepted

Context

Phase 7A needs session persistence, protected routing, and automatic redirect for the Next.js App Router frontend. The backend (Phase 2C, docs/37 §10) issues tokens only via `Authorization: Bearer` and a JSON response body - no `Set-Cookie` header exists anywhere, "no cookies, per approved Phase 2C scope." Next.js's most robust route-protection mechanism (`middleware.ts`, edge runtime) can only read cookies, not `localStorage` - a genuine mismatch between how the backend issues credentials and how the framework's strongest protection mechanism consumes them.

Decision

Store the access token in memory only (not persisted - lost on full page reload, re-derived via refresh) and the refresh token in `localStorage`. A client-side `AuthProvider`/`useAuth()` hook restores the session on mount (calls `POST /auth/refresh` using the stored refresh token, then `GET /auth/me`), and gates rendering of protected routes behind a resolved-auth-state check, redirecting unauthenticated users via `useRouter`. No changes to the backend's token-issuance mechanism.

Reason

The backend's Bearer-only design was itself an approved, documented decision (docs/37 §10) - changing it (e.g. adding cookie support) is out of scope for a frontend phase and would mean inventing new backend behavior mid-flight, contradicting "do not invent new endpoints." A pure client-side approach requires zero backend changes and ships this phase's actual requirement (session persistence, protected routing, redirect) without a new architectural layer.

Alternatives Considered

Option A: A Next.js Route Handler proxy (BFF) that calls FastAPI's auth endpoints and sets httpOnly cookies, with `middleware.ts` gating routes server-side - rejected for 7A. True SSR-level protection and better XSS resistance (refresh token never touches client JS), but introduces a new proxy layer between browser and backend that every other endpoint would need to either duplicate or bypass, and commits the project to a second auth transport (cookies via Next.js) alongside the backend's existing Bearer design - a bigger architectural change than this foundation phase's brief calls for.

Option B (chosen): Client-side storage, client-guarded routes, unmodified backend.

Trade-offs

Pros

Zero backend changes. Directly reuses the already-approved Bearer-token design. Simple mental model: one token transport, one place tokens live.

Cons

No true SSR-level route protection - a protected page's shell can begin rendering before the client-side auth check resolves, mitigated with an explicit loading gate (render nothing/a skeleton until `AuthProvider` has resolved session state) rather than a flash of real protected content. `localStorage`-held refresh tokens carry standard SPA XSS exposure - accepted as the same trade-off implicit in the backend's own Bearer-only design, not a new risk introduced here.

Consequences

Positive

Ships this phase's full scope (persistence, protected routing, redirect, refresh) without any backend involvement.

Negative

If a future phase decides httpOnly-cookie-based auth is worth the added complexity (e.g. once XSS-hardening becomes a priority), this is a real migration - the storage mechanism is not free to change later without touching every consumer of `useAuth()`.

Future Review

Revisit if a real XSS-hardening requirement emerges, or if server-side rendering of authenticated data (not just gating) becomes a real product need - at that point a BFF/cookie approach should be reconsidered as its own design pass.

---

# ADR-100

Title

Forgot Password Is an Informational Stub; Reset Password Is Entirely Deferred

Status

Accepted

Context

`POST /auth/forgot-password` and `POST /auth/reset-password` do not exist on the backend - deliberately excluded from Phase 2C, blocked on SMTP/Celery email infrastructure that doesn't exist anywhere in this project (docs/04, BACKLOG.md). Phase 7A's brief lists "Forgot Password" and "Reset Password" pages while also instructing "do not invent new endpoints" - a direct conflict, since neither page can have a real, working submission path today.

Decision

Build a `/forgot-password` page reachable from `/login` (matching conventional auth UX - users expect the link to exist) that displays an informational message ("password reset isn't available yet") rather than calling any endpoint - no form submission, no fabricated success/error states. Do not build `/reset-password` at all - it fundamentally requires a working forgot-password email flow to be reachable (a real user cannot land on it without a valid token from an email that will never be sent), so there is nothing meaningful to stub.

Reason

Omitting the "Forgot Password" link entirely would look broken to a user familiar with any conventional login page; showing it and being honest about unavailability (docs/22's project-wide "state what is missing, don't guess" principle, previously applied to the AI Chat Assistant, ADR-094) is more honest than a fake form that silently does nothing or a full page removed from the project's mental map of "this exists, just not usable yet." `/reset-password` has no equivalent reachability problem to solve for - it needs a real, working upstream flow before there is any UX to design.

Alternatives Considered

Option A: Skip both pages entirely - rejected, `/reset-password` genuinely has nothing to show without a token-issuing flow, but `/forgot-password` is reachable today (a user can always click "forgot password" from login) and leaving that link absent is worse UX than a clear "not yet" message.

Option B (chosen): Stub `/forgot-password` only, honestly labeled; omit `/reset-password`.

Trade-offs

Pros

Matches conventional login-page UX without inventing backend behavior. Honest about the current limitation rather than silently broken or fully absent.

Cons

`/forgot-password` ships now but does nothing functional - a real (if small) piece of dead-end UX until the backend adds email infrastructure.

Future Review

Revisit both pages together once `POST /auth/forgot-password`/`POST /auth/reset-password` are actually built (tracked in BACKLOG.md §4/§6) - `/forgot-password` gets a real form, `/reset-password` gets built for the first time.

---

# ADR-101

Title

The Existing Dev Dashboard Shell Evolves Into the Authenticated Product Shell

Status

Accepted

Context

The current `frontend/app/dashboard/*` tree is an unauthenticated developer/API-testing dashboard (commit "add developer dashboard frontend for analysis engines") - its `Sidebar` is labeled "ClaudeTrading Dev" with dev-tool-flavored nav (Technical Analysis, SMC, Market Regime, API Explorer), not the product navigation docs/05 §7 specifies (Dashboard, Markets, Signals, News, Economic Calendar, AI Analysis, Watchlists, Profile, Settings, Admin). Phase 7A needs a real authenticated product shell (Sidebar, Top Navigation, User Menu, per this phase's brief §3).

Decision

Replace the existing dashboard shell's navigation with the real product navigation (docs/05 §7), reusing already-established layout primitives (`PageContainer`, the `Sidebar` component's structure/responsive behavior, `QueryProvider`) rather than building a second, parallel shell. The existing Technical Analysis/SMC/Market Regime pages remain reachable - docs/05 §7 already names "API Explorer"-equivalent tooling as a legitimate nav destination, so these become sub-pages of the real product shell rather than a separate unauthenticated area. The whole shell moves behind the new protected-route gate (ADR-099).

Reason

This project's explicit reuse-first instruction ("reuse existing frontend architecture," "do not duplicate components," "create reusable layouts") applies here exactly as it has to every backend engine so far - a second, parallel shell would duplicate the layout/responsive/navigation logic Phase 7A is meant to establish once, for the whole product, not per-area.

Alternatives Considered

Option A: Build a fully separate authenticated shell under a new route group, leave `/dashboard/*` untouched and still public - rejected, produces two parallel shells (dev and product) with duplicated layout logic, directly contradicting this phase's "do not duplicate components" instruction; the existing dev pages have real, working functionality worth keeping reachable, not worth abandoning behind a second unmaintained shell.

Option B (chosen): Evolve the existing shell in place.

Trade-offs

Pros

One shell, one set of layout/responsive/navigation primitives, matching this project's consistent reuse-first practice. Existing working Technical Analysis/SMC/Market Regime pages aren't orphaned.

Cons

Directly modifies existing, working prototype code rather than leaving it untouched - a real (if low) risk versus building purely additively. Mitigated by the existing dashboard having no users yet (an internal dev tool, not a shipped product surface) and full test/typecheck/lint verification before considering the change complete.

Future Review

None expected - this is the shell every future page (Markets, Signals, News, Watchlists, etc.) will build on, per this phase's stated objective.

---

# ADR-102

Title

Adopt the Full docs/05 §2 Frontend Stack (zustand, next-themes, react-hook-form, zod, framer-motion, sonner) in Phase 7A

Status

Accepted

Context

`docs/05_FRONTEND_GUIDELINES.md` §2 names zustand, next-themes, react-hook-form, zod, and Framer Motion as this project's intended frontend stack, alongside TanStack Query (already installed, Phase 6's dev dashboard). None of the others are installed yet - Phase 7A is the first phase whose scope (auth forms, theme system, protected-route state, layout animation) actually needs them.

Decision

Install zustand (auth/UI state), next-themes (dark/light/system theme, wired to the already-configured `darkMode: ["class"]` Tailwind setting), react-hook-form + zod + @hookform/resolvers (auth forms), framer-motion (layout/dialog/dropdown transitions, per docs/05 §19's stated animation scope), and sonner (toast notifications, this phase's brief §4). Add the shadcn/Radix primitives this phase's scope requires: dialog, dropdown-menu, avatar, label, input, form, separator, sheet (mobile nav drawer).

Reason

These are not new technology decisions - they were already specified in docs/05 §2 before this phase began. Installing them now fulfills an existing, reviewed specification rather than inventing one; deferring them further would mean building auth forms/theming/toasts with ad hoc alternatives (manual validation, custom Context-based theme toggling, a hand-rolled toast system) that would need replacing later anyway once a phase needing the "real" stack arrives - and that phase is this one.

Alternatives Considered

Option A: Minimize new dependencies (native Context instead of zustand, manual form validation instead of react-hook-form/zod, CSS transitions instead of Framer Motion) - rejected, diverges from the already-documented stack for no durability benefit, and this phase's own scope (multiple auth forms, a theme system, protected-route state) is exactly the kind of complexity these libraries exist to manage well.

Option B (chosen): Install the full documented stack now.

Trade-offs

Pros

Matches docs/05 §2 exactly - no new undocumented technology choices. Every future phase building forms/state/theme/motion reuses the same, already-proven libraries rather than rediscovering the question.

Cons

A larger one-time dependency-footprint increase than a minimal approach - judged acceptable since these are one-time, well-established, actively-maintained libraries already anticipated by this project's own guidelines, not speculative additions.

Future Review

None expected - this is the stack every future frontend phase builds on.

---

# ADR-103

Title

Watchlists Ships as a Coming-Soon Placeholder - No Backend Exists

Status

Accepted

Context

Phase 7B's brief lists Watchlists among the ten pages to build. `docs/04_API_SPECIFICATION.md`'s Watchlists section (`GET/POST/PUT/DELETE /watchlists`, `POST/DELETE /watchlists/{id}/assets`) is a bare stub - unlike every implemented section, it has zero request/response shape documented. No model, table, repository, service, or route exists anywhere in the backend (confirmed against `app/api/v1/router.py` and `docs/03_DATABASE_DESIGN.md`) - this was never built in any prior phase, unlike `signals`/`ai_analysis`/`conversations`, which were each built in their own dedicated backend phase before a frontend page consumed them.

Decision

Add a real `/watchlists` nav item and route, but the page renders `EmptyState` ("Watchlists coming soon") with no functional CRUD - no fake data, no calls to a nonexistent endpoint, no client-side-only fake persistence.

Reason

Mirrors this project's `/forgot-password` stub precedent (ADR-100) and its project-wide "state what is missing, don't guess" principle (first established for AI Chat, ADR-094): omitting the nav item entirely would make the product feel incomplete in a way that contradicts "professional, production-quality" framing, but building fake functionality (e.g. persisting a watchlist to `localStorage` as a stand-in) would misrepresent a feature as real when no backend exists to make it durable, shareable across devices, or survive the pattern every other persisted entity in this project follows.

Alternatives Considered

Option A: Omit Watchlists from navigation entirely until a real backend exists - considered and available, but not chosen for 7B (see the architecture doc for the specific scope decision made).

Option B (chosen): Coming-soon placeholder with a real nav item and route.

Option C: Build a minimal `localStorage`-only "watchlist" as a client-side-only feature - rejected, creates a feature that looks identical to every other page but silently doesn't survive a cleared cache, a new device, or a new browser; indistinguishable from a real feature to the user until it unexpectedly fails, which is worse than an honest "coming soon."

Trade-offs

Pros

Honest about the current limitation. Nav/IA stays complete per docs/05 §7 without inventing backend behavior.

Cons

A real page ships with zero functionality this phase - a genuine, acknowledged gap.

Future Review

Revisit once a dedicated Watchlists backend phase (model, table, repository, service, routes) is built - this needs its own documentation-first session, per every prior phase's practice, not a quiet frontend-only addition.

---

# ADR-104

Title

Profile Is Read-Only; Settings Repurposes Only Already-Existing Client-Side Capabilities

Status

Accepted

Context

`docs/04`'s Users section (`GET/PUT /users/profile`, `POST /users/avatar`, `DELETE /users/account`) is the same kind of bare, unimplemented stub as Watchlists (ADR-103) - only `GET /auth/me` (Phase 2C) actually exists and works, returning read-only account data already consumed by `useAuth()`. No user-level "settings" concept (notification preferences, trading preferences, etc.) exists anywhere in the backend - only `system_settings`, which is admin/system-level configuration, not per-user preferences.

Decision

`/profile` shows read-only account information (email, username, full name, role, verification status, member-since date) sourced from `GET /auth/me` - no edit form, no avatar upload. `/settings` contains only what already genuinely exists and works: an Appearance section (the dark/light/system theme picker already built in Phase 7A, relocated into a dedicated page in addition to its `UserMenu` entry), a read-only Account summary (reusing the same data as `/profile`), and a Logout action (reusing `useAuth().logout()`).

Reason

Same reasoning as ADR-103 - building edit forms whose submit button would either do nothing or silently fail against a nonexistent endpoint misrepresents working functionality, violating this project's "never invent, state what's missing" principle. Settings specifically avoids becoming an empty placeholder (unlike Watchlists) because genuine, already-built functionality (theming) has a natural home there that doesn't currently have a dedicated page - `UserMenu`'s theme toggle is a quick-access convenience, not this feature's canonical home.

Alternatives Considered

Option A: Build Profile with an edit form UI, disabled or with a "coming soon" toast on submit - rejected, indistinguishable at a glance from a working form, actively misleading rather than honestly absent (worse than Watchlists' EmptyState, which is unambiguous).

Option B: Skip both pages entirely - considered and available; not chosen because Settings has genuine content to show (Appearance) even without new backend work, and Profile's read-only view is a real, low-cost, honest use of already-existing data (`GET /auth/me`).

Option C (chosen): Profile read-only; Settings repurposes only what's already real.

Trade-offs

Pros

Zero fabricated functionality. Settings gets genuine content (Appearance) without inventing backend work.

Cons

Neither page offers the editing capability a "Profile"/"Settings" page conventionally implies - a real, acknowledged gap versus a full account-management experience.

Future Review

Revisit both together once `PUT /users/profile`/`POST /users/avatar`/`DELETE /users/account` (or a genuine user-preferences backend) are built - that phase would add real edit forms to both pages, not replace them.

---

# ADR-105

Title

Trading Chart Scope: `lightweight-charts` Candlesticks + Support/Resistance + Order Block Overlays; Drawing Tools, Live Updates, and Fullscreen Deferred

Status

Accepted

Context

`docs/05_FRONTEND_GUIDELINES.md` §10 specifies a Trading Chart supporting Multi-Timeframe, Indicators, Drawing Tools, Fullscreen, Theme Sync, Live Updates, Signal Overlay, and SMC Overlay. Phase 7B's brief specifies using TradingView's `lightweight-charts` (the free, open-source library - distinct from `docs/05` §2's separately-listed "TradingView Advanced Charts," a licensed embed product requiring its own approval/hosting agreement, never installed or discussed as approved for use). `lightweight-charts` has no built-in drawing-tools UI. No live-price data source exists anywhere in this project - `docs/04`'s `/ws/prices` WebSocket endpoint is an unimplemented stub (tracked in BACKLOG.md §3 since Phase 3), so "Live Updates" would require inventing new backend streaming infrastructure, out of scope for a frontend phase.

Decision

`components/shared/price-chart.tsx` renders a `lightweight-charts` candlestick series from `GET /market/{symbol}/candles`, with a timeframe switcher and theme-sync (light/dark series colors matching `next-themes`' resolved theme). It additionally draws price-line overlays for Technical Analysis's support/resistance levels (`GET /analysis/technical/{symbol}`) and SMC's order block zones (`GET /analysis/smc/{symbol}`) - both already-available from existing endpoints, requiring no new backend work. Drawing tools, a fullscreen toggle, and live tick updates are not built this phase.

Reason

Support/resistance and order-block overlays are genuinely free - the data is already returned by endpoints this project has had since Phase 4A/4B, and rendering them as horizontal price lines is a `lightweight-charts` primitive with no new dependency or backend work. Drawing tools and live updates are not achievable without either a different (licensed) charting product or new backend streaming infrastructure - neither is something a "Dashboard & Core Pages" frontend phase should silently take on.

Alternatives Considered

Option A: Minimal candlestick chart only, no overlays - considered and available (would have been chosen had overlay data required new backend work); not chosen because the overlay data already exists and adds real value for a small, well-scoped addition.

Option B (chosen): Candlesticks + timeframe switcher + S/R + Order Block overlays, explicitly deferring drawing tools/live updates/fullscreen.

Option C: Attempt full `docs/05` §10 compliance now (drawing tools via a custom canvas layer, live updates via short-interval polling as a live-update substitute) - rejected; a hand-rolled drawing-tools UI is a substantial, undocumented feature investment beyond this phase's "core pages" framing, and polling every few seconds to fake "live" updates would need its own rate-limit/cost analysis against the market-data provider (`docs/40`'s quota-tracking concerns) not undertaken here.

Trade-offs

Pros

Real, functioning chart with genuine SMC/Technical Analysis context, using only already-existing endpoints and one new, well-established open-source dependency.

Cons

`docs/05` §10's Drawing Tools/Fullscreen/Live Updates remain unimplemented - acknowledged gaps, not silently dropped.

Future Review

Revisit Live Updates once a real price-streaming backend exists (would need its own documentation-first session, mirroring every prior new-capability phase). Revisit Drawing Tools/Fullscreen as pure frontend polish once the base chart is proven in real use - no backend dependency blocks either, unlike Live Updates.

---

# ADR-106

Title

Dashboard Is Composed Client-Side from Existing Per-Domain Endpoints - `GET /dashboard` Stub Not Implemented

Status

Accepted

Context

`docs/04`'s Dashboard section (`GET /dashboard` returning Portfolio Summary/Latest Signals/Market Overview/Economic Calendar/Watchlist/News) is, like Watchlists and Users, a bare stub with no backend implementation and no route in `app/api/v1/router.py`. Every one of its constituent pieces, however, already has a real, working endpoint of its own: `GET /signals` (latest signals), `GET /calendar/upcoming` (economic events), `GET /news` (breaking news), `GET /assets` (market overview). Portfolio Summary and Watchlist depend on features that don't exist yet (no portfolio/position tracking anywhere in this project; Watchlists itself is a placeholder per ADR-103).

Decision

The Dashboard page fetches from each already-existing per-domain endpoint in parallel (mirrors the existing Phase 6 dev-dashboard's `Promise`-parallel pattern for Technical/SMC/Regime, and `ContextBuilder`'s "call each dependency once" backend precedent), composing the results into `docs/05` §9's widget layout (Market Overview, Latest Signals, Economic Events, Breaking News; AI Insights shows the most recent `GET /analysis/history` entries). Portfolio Summary and Watchlist widgets are omitted - not stubbed - since the former has no underlying feature anywhere in this project and the latter would just re-embed the Watchlists placeholder redundantly.

Reason

Building a real `POST/GET /dashboard` composite backend endpoint now would mean inventing new backend surface area for a frontend phase explicitly scoped to avoid backend changes - and would just re-fetch/re-combine data every one of its constituent endpoints already serves independently, duplicating logic for no benefit (the same reasoning this project has applied to every prior "should this be one composite call or several already-existing ones" decision, e.g. AI Chat's `ContextBuilder` reuse, ADR-093).

Alternatives Considered

Option A: Build a real backend `GET /dashboard` aggregator - rejected, out of scope for a frontend-only phase, and duplicates logic already exposed by existing endpoints.

Option B (chosen): Client-side composition from existing per-domain endpoints, mirroring the existing dev-dashboard's parallel-fetch pattern.

Trade-offs

Pros

Zero new backend surface area. Each widget's data is exactly as fresh as calling that domain's own page would show - no second, possibly-stale aggregation layer.

Cons

The Dashboard page makes several parallel requests instead of one - acceptable given every one of this project's existing multi-engine consumers (Confidence Engine, AI Orchestrator, AI Chat) already accepts this cost, and no caching precedent exists anywhere in this project to optimize it further speculatively.

Future Review

Revisit if Portfolio/Watchlist tracking is ever built (would need its own phase) - the Dashboard's widget composition pattern established here would extend to include them, not be redesigned.

---

# ADR-107

Title

Extend `PriceChart` Overlay Model With Zones + Time Markers for SMC Concepts

Status

Accepted

Context

Phase 7B's `PriceChart` (docs/54 §4, ADR-105) only supports a single overlay shape - `PriceLineOverlay` (`{price, color, title}`), a horizontal line spanning the full chart width, used for Support/Resistance and the top-3 Order Blocks (as a single line at `zone_high`). Phase 7C needs to draw the rest of the SMC concepts already returned by `GET /analysis/smc/{symbol}` (docs/04 §Smart Money Concepts): Order Blocks and Fair Value Gaps are price *ranges* (`zone_high`/`zone_low`, `gap_high`/`gap_low`), and BOS/CHoCH/Liquidity Sweeps are point-in-time *events* (a specific break/confirmation time, not a price at all in CHoCH's case - it only carries `previous_trend`/`new_trend`/`confidence`/`confirmation_time`). Neither shape fits a chart-wide horizontal line.

Decision

Two new optional `PriceChart` props, both built on `lightweight-charts` features already present in the dependency (no new package):

- `zones?: ZoneOverlay[]` (`{high, low, color, label}`) - rendered as a *paired* top/bottom `series.createPriceLine()` call (the same primitive `PriceLineOverlay` already uses, just two lines sharing a color/label instead of one). Used for Order Blocks and Fair Value Gaps.
- `markers?: ChartMarkerOverlay[]` (`{time, position: "aboveBar" | "belowBar", color, shape, text}`) - rendered via the native `createSeriesMarkers(series, markers)` plugin API (`lightweight-charts` v5). Positioned relative to the bar (`aboveBar`/`belowBar`), not an exact price - CHoCH events have no price field to place an exact marker at, only a confirmation time and trend change, so bar-relative positioning (derived from the event's bullish/bearish direction) is used uniformly for BOS/CHoCH rather than mixing an exact-price marker type for BOS and a bar-relative one for CHoCH.

A shared `lib/smc-overlays.ts` (`buildSmcOverlays(smc, enabledKinds)`) maps a `SMCAnalysisResponse` to `{zones, markers, lines}` once, reused by every page that draws SMC overlays (Markets detail, Signal detail, AI Analysis detail) - each page also gets a `SmcOverlayToggles` checkbox-group component so charts don't dump every overlay at once, capping each kind at the top-3 by strength/freshness/touch-count (same convention Phase 7B's Order Block overlay already established).

Reason

Reusing `createPriceLine` for zones keeps the implementation inside the same mental model and API surface Phase 7B already shipped and battle-tested (including its `ResizeObserver`-race fix), rather than reaching for a custom canvas/primitive plugin to draw actual shaded rectangles - which `lightweight-charts` has no first-party support for. `createSeriesMarkers` is a first-party, built-in API (not a drawing tool a user interacts with), so it doesn't touch ADR-105's "no drawing tools" boundary.

Alternatives Considered

Option A: Custom `ISeriesPrimitive` canvas plugin for true shaded rectangles - rejected, meaningfully more implementation and maintenance surface for a purely cosmetic upgrade over two dashed lines, and no such plugin precedent exists anywhere in this codebase to build on.

Option B (chosen): Paired price lines for zones + native `createSeriesMarkers` for events.

Option C: Exact-price markers (`atPriceTop`/`atPriceMiddle`/`atPriceBottom`) for BOS (which does have a `break_price`) and a fallback for CHoCH - rejected for consistency; mixing marker-positioning strategies within the same overlay kind (events) would complicate `buildSmcOverlays` and the toggle UI for a marginal visual difference bar-relative positioning already conveys (bullish above/below the candle).

Trade-offs

Pros

No new dependency. Reuses the exact primitive and lifecycle-cleanup pattern (`useEffect` return function removing what it added) Phase 7B already proved correct. Toggle UI prevents overlay clutter and keeps chart render cost bounded regardless of how many SMC events a symbol has.

Cons

Zones are visually two dashed lines, not a filled rectangle - a materially different (if directionally similar) rendering than a "real" trading platform's shaded order-block box. Deferred deliberately (see Alternatives, Option A) rather than accepted as a permanent ceiling.

Future Review

Revisit if a custom primitives plugin is ever justified by a broader charting overhaul (e.g. live ticks, drawing tools - both still deferred per ADR-105) - the zone data shape (`ZoneOverlay`) would carry over unchanged, only the rendering call would change from two price lines to a filled rectangle primitive.

---

# ADR-108

Title

Adopt `react-markdown` + `remark-gfm` for AI-Generated Text Rendering

Status

Accepted

Context

AI Analysis reasoning (`AIAnalysisResponse.reasoning.{summary,technical,smc,economic,news,risk,conclusion}`, the one AI-generated field on that response per ADR-079) and AI Chat message content (`MessageResponse.content`) are LLM-generated free text. Through Phase 7B they were rendered as raw strings via `whitespace-pre-wrap`, with any markdown-style formatting the LLM produced (lists, emphasis, headings) showing up as literal asterisks/hashes. Neither `docs/05` nor `package.json` specified a markdown library.

Decision

Add `react-markdown` + `remark-gfm` (GitHub-flavored markdown: tables, strikethrough, task lists). A single shared `components/shared/markdown.tsx` wraps `ReactMarkdown` with manual Tailwind-class `components` overrides (no `@tailwindcss/typography` plugin - not installed, and adding it wasn't necessary for the handful of element types LLM output actually produces: paragraphs, lists, emphasis, headings, inline code, links). Both AI Analysis reasoning (`ReasoningSections`) and AI Chat assistant messages (`MessageThread`) render through this one component rather than duplicating styling. Loaded via `next/dynamic` (`components/shared/markdown-lazy.tsx`) to keep it out of the initial JS bundle, since most pages never render markdown at all.

Deliberately **not** adding `rehype-raw` - no raw HTML rendering. Content originates from an LLM (AI Analysis reasoning) or from either the LLM or the authenticated user themselves (AI Chat), never from an untrusted third party with a different trust boundary, but this still keeps zero HTML-injection surface without needing a sanitizer, since `react-markdown` already refuses to render raw HTML tags as anything but literal text by default.

Reason

The alternative - fixing this by asking the LLM to stop producing markdown syntax - isn't reliably enforceable through prompting alone and would fight the model's natural output style; rendering what it already produces is simpler and more robust than suppressing it.

Alternatives Considered

Option A: Strip markdown syntax server-side or via a prompt-engineering-only fix - rejected, unreliable and out of scope for a frontend-only phase (would require a backend/prompt change).

Option B (chosen): `react-markdown` + `remark-gfm`, no raw HTML.

Trade-offs

Pros

Correctly renders whatever formatting the LLM already produces. Small, well-established, actively maintained library. Zero HTML-injection surface (no `rehype-raw`).

Cons

Two new dependencies. Manual `components` overrides (not a `prose` class) means new markdown element types the LLM starts producing (e.g. blockquotes, tables it doesn't currently emit) render with browser-default styling until explicitly styled.

Future Review

Add `@tailwindcss/typography` and switch to a `prose` class if LLM output style becomes visibly richer (tables, blockquotes) than the current manual overrides cover.

---

# ADR-109

Title

AI Chat "Streaming-Ready" via Optimistic Pending-Message Placeholder, Not Real Token Streaming

Status

Accepted

Context

Phase 6C's AI Chat backend (docs/52, ADR-092 through ADR-098) is request/response only - `POST /chat/conversations/{id}/messages` returns the full `assistant_message` in one response, with no SSE or WebSocket endpoint anywhere in the backend. Phase 7C's requirements ask for a "streaming-ready architecture... without requiring backend streaming yet" - i.e. the frontend should be structured so a future streaming backend could be adopted without a component-contract rewrite, while today's UX shouldn't fake something it can't yet do.

Decision

`MessageThread` accepts two optional trailing-item props: `pendingUserContent` (the just-submitted user message, shown immediately, before the round trip resolves) and `showTypingIndicator` (an animated three-dot indicator standing in for the assistant's still-in-flight reply). The chat thread page sets `pendingUserContent` the instant `handleSend` is called and clears it in the mutation's `finally` block, once the real, persisted `user_message`/`assistant_message` pair has replaced it via the `conversation` query invalidation `useSendMessage` already triggers.

No polling, and no fake token-by-token animation of the final text once it arrives (typing out the already-complete response character-by-character would misrepresent actual latency rather than reflect it).

Reason

A future SSE backend would only need to swap the static typing indicator for progressively-appended text in a `pendingAssistantContent`-shaped prop - `MessageThread`'s contract (a message list plus one optional trailing pending pair) does not need to change, which is what "streaming-ready" means operationally here: the seam is already in the right place, not that streaming is simulated today.

Alternatives Considered

Option A: Client-side polling of the conversation endpoint at a short interval to simulate "live" updates - rejected, adds request volume for no actual new information (the backend has nothing partial to return between the request and its single response).

Option B: Fake token-by-token reveal of the completed response text - rejected, misrepresents latency the user already experienced waiting for the request to resolve, and is a worse UX than an honest "typing" indicator for the actual wait.

Option C (chosen): Optimistic pending-message placeholder (user bubble + typing indicator), real content swapped in via existing query invalidation once the response resolves.

Trade-offs

Pros

Zero backend changes. Matches the actual request/response latency honestly rather than performing a synthetic streaming illusion. The component seam is already where a real streaming implementation would need it.

Cons

Still a single request/response round trip under the hood - a user cannot see partial reasoning as the model produces it, only a generic "typing" signal, until the backend gains real streaming.

Future Review

Revisit when/if the backend adds SSE or WebSocket streaming support to `POST /chat/conversations/{id}/messages` (or a dedicated streaming variant) - `MessageThread`'s pending-item contract is designed to absorb that without a rewrite.

---

# ADR-110

Title

Telegram Automation Scoped to Signal Delivery Only, Not Full docs/19/20

Status

Accepted

Context

`docs/19_TELEGRAM_BOT.md` and `docs/20_NOTIFICATION_SYSTEM.md` are Phase-0 vision documents describing a full multi-channel notification system (email, in-app, Telegram, quiet hours, ten-plus bot commands, dedup/retry queue, admin escalation). Building all of it in one pass is a much larger surface than "connect Signal Generation to Telegram," which is the actual requested pipeline stage.

Decision

Build exactly one slice: account linking + delivering the existing `Signal` model to a linked Telegram chat, using the docs/19 §5 message format. Every other docs/19/20 feature is named explicitly in docs/57 §8 as deferred, not silently dropped.

Reason

Matches this project's established reuse-first, narrow-scope-per-phase precedent (Signal Engine narrowing docs/11's original vision, ADR-085; Risk Management reusing rather than rebuilding, ADR-064). Shipping a smaller, fully-working slice is lower-risk than a partially-working full system.

Alternatives Considered

Option A: Build the full docs/19/20 system now - rejected, multiplies scope (email provider, quiet-hours scheduler, preference UI, ten commands) well beyond what was asked.

Option B (chosen): Signal delivery only, explicit deferral list.

Trade-offs

Pros

Small, reviewable, working end-to-end slice. Every deferred feature has a clear landing spot (docs/57 §8) for a future phase.

Cons

Users cannot yet mute Telegram delivery, control quiet hours, or receive non-signal alerts (news/economic/regime-change) via this channel.

Future Review

Revisit once Signal delivery has been used in production; expand toward docs/20's full preference/channel model incrementally.

---

# ADR-111

Title

Telegram Account Linking via Short-Lived Lookup Code, Not a New Auth Mechanism

Status

Accepted

Context

docs/19 §3 specifies a "Generate Secure Link Code -> Open Telegram Bot -> Verify Account" flow. This project already has two precedents for linking an external identity to a platform account: `oauth_account.py` (OAuth linking) and `user_session.py`'s refresh tokens (opaque, stored, looked-up tokens - not self-verifying JWTs).

Decision

`telegram_accounts.link_code` is a `secrets.token_urlsafe` random string, stored server-side with a 10-minute expiry, looked up (not decoded/verified like a JWT) when `/start <code>` arrives. One row per user, upserted on each `POST /telegram/link` call (issuing a fresh code invalidates any prior unused one).

Reason

Nothing about this flow needs a self-verifying token (no third party needs to validate it independently) - a stored, looked-up code is simpler and matches the existing refresh-token precedent (ADR-022) rather than inventing a JWT-based linking mechanism with no consumer that needs JWT's properties.

Alternatives Considered

Option A: Signed JWT containing user_id, verified on `/start` - rejected, adds complexity (signing, expiry-in-payload, revocation-before-expiry problem) with no benefit over a stored lookup code for a single first-party consumer (this bot).

Option B (chosen): Random opaque code, server-side lookup + expiry check.

Trade-offs

Pros

Simple, revocable (just delete/overwrite the row), consistent with existing session-token precedent.

Cons

Requires a DB round-trip to validate (negligible at this volume - link events are rare, one-time-per-user).

Future Review

None expected - this is a low-stakes, low-volume flow.

---

# ADR-112

Title

Telegram Provider via Long-Polling `getUpdates`, Not a Public Webhook

Status

Accepted

Context

Telegram's Bot API supports either a webhook (Telegram pushes updates to a public HTTPS URL) or `getUpdates` long-polling (the bot pulls updates on an interval). This project's `docker-compose.yml` exposes the backend on `localhost` only in development, with no public HTTPS endpoint configured anywhere.

Decision

`app/services/telegram/providers/bot_api.py` uses `getUpdates` polling via a new Celery Beat task, not a webhook route. Same three-file provider shape (`base.py` Protocol + `mock.py` + `bot_api.py`) as every other integration (market data, news, economic calendar).

Reason

A webhook requires a publicly reachable HTTPS URL with a valid certificate - infrastructure that doesn't exist in this project's current deployment (docs/27) and is out of scope to stand up just for this feature. Polling is simpler to run identically in dev and prod, at the cost of a small latency window (bounded by the poll interval) on `/start` command processing - acceptable since linking is a one-time, non-time-critical action.

Alternatives Considered

Option A: Public webhook - rejected, requires new public-ingress infrastructure not otherwise needed by this project yet.

Option B (chosen): `getUpdates` long-polling via Celery Beat.

Trade-offs

Pros

No new infrastructure, works identically in every environment, matches the existing provider-abstraction shape.

Cons

Small polling latency (not real-time push); a continuously-running poll task consumes a small, constant amount of API quota even when idle.

Future Review

Revisit if this project stands up a public ingress for other reasons (e.g. real payment webhooks, docs/24) - webhook delivery could then be adopted for lower latency.

---

# ADR-113

Title

Telegram Delivery Broadcasts to All Linked Accounts, No Per-User Filtering Yet

Status

Accepted

Context

docs/20 §6 specifies per-user notification preferences (which types, which channels). No preference model exists yet, and none is being built in this phase (ADR-110's scope narrowing).

Decision

`send_signal_telegram_task` sends every generated Signal to every account with `linked_at is not null` - no asset/timeframe/preference filtering.

Reason

Building a preference model is real, separate scope (docs/20 §6) larger than "deliver a Signal to Telegram." Broadcasting to all linked accounts is the simplest behavior that is still honest (a linked user gets every signal, not a silent subset) rather than half-building a filtering system with no UI to configure it.

Alternatives Considered

Option A: Build a minimal preference flag now - rejected, "minimal" preference UI/API is still new surface beyond this phase's scope, and a single boolean would need to be revisited anyway once docs/20's real preference model is built.

Option B (chosen): Broadcast to all linked accounts.

Trade-offs

Pros

Zero new preference infrastructure; every linked user's experience is simple and predictable ("I linked, I get signals").

Cons

No opt-out short of unlinking; not viable once user count grows past a handful without docs/20's real preference system.

Future Review

Required before any production rollout beyond internal testing - revisit alongside docs/20's full notification-preferences phase.

---

# ADR-114

Title

Watchlists Scoped to docs/03's Minimal Schema, docs/21's Richer Features Deferred

Status

Accepted

Context

docs/21_WATCHLIST_SYSTEM.md describes custom alerts, tags, pinning, an AI
watchlist summary, and performance history. `docs/03_DATABASE_DESIGN.md` §12
only ever reserved two minimal tables (`watchlists`: id/user_id/name/created_at;
`watchlist_items`: id/watchlist_id/asset_id/created_at) - none of docs/21's
richer fields were ever specified in the schema.

Decision

Phase 7D-A/7D-B build exactly docs/03 §12's two tables and docs/04's six
literal endpoints - a named list plus asset membership. Nothing else.

Reason

Building alerts/tags/pinning/AI summary now would mean inventing new schema
from a vision document that was never reconciled with docs/03, violating
"never invent architecture." Each of those is a real, separable feature
(alerts need a rule-evaluation + delivery mechanism; AI summary needs its own
LLM-cost decision like ADR-051/ADR-082) deserving its own documentation-first
pass, not a quiet addition to a CRUD phase.

Alternatives Considered

Option A: Build alerts/tags now since they're "just a few columns" - rejected,
alerts specifically require a background evaluation job and a delivery
channel decision (Notifications? Telegram? both?) that doesn't exist yet.

Option B (chosen): Ship the minimal schema; treat richer features as a
future phase requiring their own docs/03 amendment and ADR.

Trade-offs

Pros

Matches documented schema exactly; no architecture invented; fast to ship
and verify.

Cons

The shipped Watchlists feature is noticeably thinner than docs/21's vision -
users get list management only, no alerting/AI insight.

Future Review

Revisit once Notifications (docs/20) exists as a real delivery channel -
alerts need somewhere to deliver to before they're worth building.

---

# ADR-115

Title

Admin RBAC Uses the Existing Simple `UserRole` Enum, Not a Permission-Table Model

Status

Accepted

Context

docs/23_AUTHENTICATION_AND_RBAC.md §12-14 describes a granular permission
model (roles *have* permissions, e.g. `signals.publish`, `admin.dashboard`).
This was explicitly deferred at Phase 2A (BACKLOG.md §2) in favor of a simple
`UserRole` enum column on `users` - no `roles`/`permissions`/
`role_permissions` tables exist anywhere in the schema, unchanged since.

Decision

The first RBAC-enforcement dependency this project ever builds
(`require_role`, `app/dependencies/rbac.py`) checks `current_user.role`
against a fixed set of `UserRole` values per route - no granular permission
strings, no permission table, no permission-checking indirection.

Reason

Phase 2A's deferral was never revisited because nothing needed enforcement
until now. Admin (7D-C) is the first phase that actually needs a
role-checking dependency; building the full permission-table model now,
years of scope after the enum was chosen, would be a bigger architectural
change than this phase's actual need (7 endpoints, 2 required roles) justifies.

Alternatives Considered

Option A: Build the full `roles`/`permissions`/`role_permissions` schema
now, migrate `UserRole` off - rejected, no requirement in this phase needs
per-permission granularity (every one of the 7 admin endpoints is
Admin-or-SuperAdmin-only, not split by finer permission).

Option B (chosen): Simple `require_role(*roles)` dependency over the
existing enum.

Trade-offs

Pros

Minimal new surface area; reuses a column that has existed since Phase 2A
unchanged; matches every admin route's actual (coarse) authorization need.

Cons

Doesn't unblock docs/23 §13's Moderator/Support tiers (their listed
permissions - "Manage Reports," "Assist Users" - have no matching endpoint
in docs/04 yet regardless of enforcement model). A future phase that
genuinely needs per-permission granularity still has to do the full
migration this ADR declined to do now.

Future Review

Revisit if/when a route genuinely needs finer-than-role granularity (e.g. a
Moderator who can view but not suspend users) - that's the trigger for the
full permission-table migration, not this phase.

---

# ADR-116

Title

Admin Backend Limited to docs/04's 7 Documented Endpoints, docs/25's Monitoring/Feature-Flag Vision Deferred

Status

Accepted

Context

docs/25_ADMIN_PANEL.md describes live CPU/memory/disk/Redis/queue metrics,
feature flags, maintenance actions ("restart workers," "clear cache,"
"rebuild indicators"), and A/B prompt testing. `docs/04_API_SPECIFICATION.md`
§Admin only ever committed to 7 endpoints: `GET /admin/{users,signals,
system,logs,analytics}`, `POST /admin/{news,maintenance}`. No metrics
collection, feature-flag table, or worker-management infrastructure exists
anywhere in this codebase.

Decision

Phase 7D-C builds only the 7 documented endpoints. `GET /admin/system`
reuses the existing `/health`/`/health/ready` liveness checks (Phase 1) plus
simple `COUNT` queries for "today's" figures - it does not report live
CPU/memory/disk/Redis-memory/queue-depth telemetry.

Reason

docs/25 is a Phase-0 vision document never reconciled against docs/04, the
same category of gap already resolved for News/Economic/Signal/Chat in
earlier phases (BACKLOG.md §1, §7) - docs/04 is the concrete contract,
docs/25 is aspirational. Building real system telemetry requires new
infrastructure (a metrics library, Celery `inspect()` wiring, Redis `INFO`
parsing) that is real, separate scope - tracked already as the `GET /metrics`
gap in BACKLOG.md §3.

Alternatives Considered

Option A: Build basic `psutil`-based CPU/memory reporting now since it's
"just a library call" - rejected, still new infrastructure with its own
deployment/permission implications (reading host-level system stats from
inside a container), out of proportion to this phase's actual scope.

Option B (chosen): Ship the 7 documented endpoints only; `/admin/system`
reports liveness + counts, not telemetry.

Trade-offs

Pros

Matches the concrete API contract exactly; zero new infrastructure
dependencies; ships fast.

Cons

`GET /admin/system` is noticeably thinner than docs/25 §3/§12's vision - an
operator still can't see real CPU/queue-depth from this UI, only up/down +
today's counts.

Future Review

Revisit once BACKLOG.md §3's `GET /metrics` (Prometheus) work is picked
up - real system telemetry should be built once, then surfaced here, not
built twice (once ad hoc for Admin, once properly for Prometheus).

---

# ADR-117

Title

`POST /admin/maintenance` Limited to Actions With an Existing Concrete Implementation

Status

Accepted

Context

docs/25 §17 lists seven maintenance actions: Clear Cache, Restart Workers,
Rebuild Indicators, Recalculate Confidence, Refresh News, Refresh Calendar,
Health Check. Only two have any existing code to call - `NewsIngestionPipeline`
(Phase 5A) and the Economic Calendar ingestion pipeline (Phase 5B) already
exist and are already triggered on a Celery Beat schedule; "refresh" here
just means admin-invoked instead of schedule-invoked.

Decision

`POST /admin/maintenance` accepts `{"action": "refresh_news" |
"refresh_calendar"}` only, each calling the existing ingestion pipeline
directly. Every other docs/25 §17 action is rejected (`400`, not silently
ignored) until it has a real implementation to call.

Reason

"Restart Workers" has no process-management access from inside a FastAPI
request handler in this deployment. "Clear Cache" has nothing to clear - no
Redis-backed response caching exists anywhere (BACKLOG.md §11's explicit
prior decision). "Rebuild Indicators"/"Recalculate Confidence" are
meaningless for this project's stateless engines (ADR-027, ADR-046) - there
is nothing persisted to "rebuild," every request already recomputes fresh.
"Health Check" already exists as `GET /health/ready`, not a `POST` action.

Alternatives Considered

Option A: Accept all seven actions and return "not implemented" for five of
them - rejected, `POST /admin/maintenance` would present a control that does
nothing, worse than not offering it.

Option B (chosen): Only accept actions with a real, callable implementation.

Trade-offs

Pros

No fake/no-op admin controls; every accepted action does exactly what it
says.

Cons

The Admin UI's maintenance panel is far narrower than docs/25 §17's vision.

Future Review

Revisit each rejected action individually as its underlying capability gets
built (e.g. once response caching exists, "Clear Cache" becomes buildable).

---

# ADR-118

Title

Admin Nav Item Is Role-Gated Client-Side Only, No Server-Rendered Gating

Status

Accepted

Context

Phase 7A (ADR-101) considered and dropped a role-gated Admin nav item since
no `/admin` destination existed yet. This project's auth model is entirely
client-side (ADR-099, no BFF/httpOnly cookies) - every route-protection
decision so far (`AuthGuard`/`GuestGuard`) has been a client-side check
against the in-memory/localStorage session, not server-rendered.

Decision

`Sidebar`'s Admin nav item is rendered conditionally on
`useAuth().user.role` being `admin`/`super_admin`, the same pattern as every
other conditional UI element in this project. The `/admin/*` routes
themselves are additionally protected by the real `require_role` backend
dependency (ADR-115) - the nav item's visibility is a UX convenience, not
the security boundary.

Reason

Consistent with ADR-099's already-accepted trade-off: this project has never
had server-rendered route gating, and introducing one just for Admin would
be a bigger architectural change (a real BFF or edge middleware layer) than
this phase's scope justifies. The actual security boundary is, as with every
other protected route, the backend's authorization check - a non-admin user
manually navigating to `/admin/users` gets a real `403` from the API, not
just a hidden nav link.

Alternatives Considered

Option A: Add `middleware.ts`-based edge gating for `/admin/*` specifically -
rejected, introduces a second, inconsistent gating mechanism alongside every
other route's client-side `AuthGuard`, for a marginal benefit (hiding a URL
that still 403s on request).

Option B (chosen): Client-side conditional nav rendering + real backend
enforcement, same layering as every other protected feature.

Trade-offs

Pros

Consistent with every existing route-protection pattern; zero new
infrastructure.

Cons

A non-admin user who knows/guesses the `/admin` URL sees the page shell
before its data fetches 403 (a brief flash), rather than never reaching it -
same class of trade-off already accepted project-wide since ADR-099.

Future Review

Revisit alongside ADR-099 itself if a real XSS-hardening or SSR-gating
requirement ever emerges - this is not an Admin-specific decision, it
inherits the whole project's existing auth-architecture trade-off.

---

# ADR-119

Title

Admin-Only Account Provisioning Supersedes Public Self-Registration

Status

Accepted

Context

Every prior auth phase (2A/2B/2C/7A) was built assuming public
self-registration (`POST /auth/register`, docs/23 §3). Phase 8 changes the
product requirement: only administrators may create accounts.

Decision

`POST /auth/register` is gated behind `settings.allow_public_registration`
(default `False`). When disabled it raises a new `RegistrationDisabledException`
(`403`, explicit message). `UserService.register_user` is not deleted or
duplicated - `AdminUserService.create_user` calls the same underlying
method, so validation never drifts between the two entry points. `/register`
becomes an informational stub (same precedent as `/forgot-password`,
ADR-100) rather than a removed route.

Reason

A config flag (not a route deletion) keeps the change reversible and keeps
exactly one implementation of registration validation. A `403` with an
explicit message is consistent with this project's typed-exception
convention - every other boundary in this app fails with a clear typed
error, never silent `404`.

Alternatives Considered

Option A: Delete the register route/page entirely - rejected, an
unexpectedly-vanished route is a worse failure mode than an explicit,
informative error, and forecloses reversibility without a code change.

Option B (chosen): Config-gated `403` + informational frontend stub.

Trade-offs

Pros

Reversible via config; single source of registration-validation logic;
consistent, honest error behavior.

Cons

The `POST /auth/register` endpoint remains reachable (returning `403`)
rather than genuinely absent - a deliberate, documented trade-off, not an
oversight.

Future Review

Revisit if a genuine "invite a new tenant with self-service registration
re-enabled" requirement ever emerges (e.g. multi-tenant SaaS pivot).

---

# ADR-120

Title

`User` Gains `deleted_at`/`must_change_password`/`created_by_admin_id`; Soft Delete Only

Status

Accepted

Context

Admin user management needs to delete accounts, track who created them, and
force a password change after an admin sets one on a user's behalf. `User`
is a `CASCADE` FK target for `watchlists`, `telegram_accounts`,
`conversations`, and `ai_analysis`.

Decision

Three new nullable `User` columns (`deleted_at`, `must_change_password`,
`created_by_admin_id`). Deletion is soft (`deleted_at` set, no cascade)
only - hard delete is not offered.

Reason

A hard delete would silently destroy a user's entire history (chat
conversations, linked Telegram account, watchlists) via cascade, with no
undo - unacceptable for an admin-panel action a single click away. Soft
delete preserves everything for audit/compliance while still excluding the
account from listings and blocking login.

Alternatives Considered

Option A: Hard delete with an "are you sure" confirmation only - rejected,
a confirmation dialog doesn't mitigate the actual risk (accidental clicks,
or a genuinely-intended delete that didn't anticipate the cascade).

Option B (chosen): Soft delete via `deleted_at`, no hard-delete option in
this phase.

Trade-offs

Pros

No accidental, irreversible data loss; deleted users remain available for
audit/dispute resolution.

Cons

No true "erase my data" capability yet - deferred as its own future design
pass (needs a real decision on what must be erased vs. anonymized vs.
retained for legal reasons, e.g. GDPR).

Future Review

Revisit if a genuine data-erasure (not just account-deactivation)
requirement emerges.

---

# ADR-121

Title

RBAC Enforcement Extended with a Vertical-Access Check: Target Role, Not Just Actor Role

Status

Accepted

Context

`require_admin`/`require_super_admin` (ADR-115's extension) check the
*actor's* role. Without an additional check, any `admin` could edit,
disable, or delete any other `admin` or `super_admin` account - a
privilege/peer-tampering gap route-level role checks alone don't close.

Decision

`AdminUserService` checks the *target* user's role on every mutation, not
just the actor's. An `admin` actor may only act on `guest`/`registered`/
`premium`/`moderator`/`support` targets. Only a `super_admin` may act on
`admin`/`super_admin` targets. Role-grant/role-change is further isolated
to its own `require_super_admin`-only endpoint (`PATCH /admin/users/{id}/role`).

Reason

Route-level `require_admin` alone answers "can this caller reach any
`/admin/users` endpoint," not "can this caller act on *this specific*
target" - the two are different questions, and only the service layer has
the target loaded to answer the second one.

Alternatives Considered

Option A: Rely on route-level role checks only - rejected, leaves the
admin-tampering-admin gap open entirely.

Option B (chosen): Service-layer target-role check on every mutating method.

Trade-offs

Pros

Closes a real vertical-access gap; single, auditable enforcement point per
mutation type.

Cons

One more check every mutating method must remember to include - mitigated
by putting it in `AdminUserService`'s shared base logic rather than
duplicating it per method.

Future Review

None anticipated - this is a permanent, not provisional, control.

---

# ADR-122

Title

`Permission`/`ROLE_PERMISSIONS` In-Code Seam Added Alongside `require_role`

Status

Accepted

Context

Phase 8's authorization requirement explicitly asked for "future
extensibility" beyond simple role checks (e.g. a Moderator who can view but
not suspend users, docs/23 §13, still with no matching endpoint). ADR-115
already deferred the full `roles`/`permissions`/`role_permissions` DB schema.

Decision

A `Permission` `StrEnum` + `ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]]`
in-code mapping ships in Phase 8B alongside `require_role`. `require_permission(...)`
reads from this dict. No new database table.

Reason

The extensibility ask is real, but Phase 8's actual routes only need
role-level granularity - a ~15-line in-code dict satisfies "extensible
later" without the larger migration ADR-115 already declined to do
prematurely. If real permission-table requirements appear later,
`ROLE_PERMISSIONS` is the one place that changes from a hardcoded dict to a
DB-backed lookup; every `Depends(require_permission(...))` call site is
unaffected.

Alternatives Considered

Option A: Build the full permission-table schema now since "future
extensibility" was requested - rejected, no route in this phase needs
finer-than-role granularity; this would be building ahead of demonstrated
need, reversing ADR-115's already-accepted reasoning without new
justification.

Option B (chosen): In-code `Permission` enum/dict seam, no schema change.

Trade-offs

Pros

Cheap, real extensibility seam; zero new infrastructure; doesn't reverse
ADR-115.

Cons

Not dynamically configurable (a `ROLE_PERMISSIONS` change requires a code
deploy, not an admin-panel edit) - acceptable since no requirement asks for
runtime-configurable permissions.

Future Review

Revisit if/when a route genuinely needs a permission not cleanly aligned to
the existing role tiers - same trigger condition ADR-115 already named.

---

# ADR-123

Title

First Super-Admin Bootstrapped via Operator-Run CLI Script, Not Auto-Bootstrap

Status

Accepted

Context

Phase 8 removes public registration, but this project has zero admin
accounts. Something must create the first `super_admin` before the
registration gate closes, or login becomes permanently unreachable without
direct database access.

Decision

`backend/scripts/create_admin.py`, a one-off, operator-run CLI script
(mirrors the existing `backend/scripts/seed_dev_data.py` precedent) - not
automatic startup-time bootstrap from environment variables.

Reason

Auto-bootstrap (`BOOTSTRAP_ADMIN_EMAIL`/`PASSWORD` env vars, checked on
every app start) is standing logic with a permanent (if narrow) attack
surface for what is fundamentally a one-time operational need. An
operator-run script is explicit and auditable - someone had to deliberately
run it - and adds zero always-on code paths.

Alternatives Considered

Option A: Env-var auto-bootstrap on startup - rejected per the reasoning
above.

Option B (chosen): Operator-run CLI script.

Trade-offs

Pros

No standing bootstrap code path; explicit, auditable, one-time action.

Cons

Requires direct server/container access to run once per environment
(acceptable - deployment automation can still invoke the script as part of
a provisioning step, it just isn't baked into the app's own startup).

Future Review

None anticipated.

---

# ADR-124

Title

Admin "API Usage" Page Ships as a Labeled AI-Analysis/Signal-Count Proxy, Not Deferred

Status

Accepted

Context

docs/25's Admin vision includes an API Usage view, but no request-metrics
collection infrastructure exists anywhere in this project (`GET /metrics`
remains an open BACKLOG.md §3 item, same gap already noted for `/admin/system`
in ADR-116).

Decision

The page ships in Phase 8D showing real per-day `ai_analysis`/`signals` row
counts, explicitly labeled as a usage proxy, not true per-endpoint API
request metrics.

Reason

Real, already-persisted data (`ai_analysis`/`signals` creation timestamps)
gives a genuinely useful signal (how much AI-orchestrator/signal-generation
activity is happening) without fabricating numbers or requiring new
metrics infrastructure - closer to the spirit of the request than an empty
placeholder, as long as the label is honest about what it is and isn't.

Alternatives Considered

Option A: Defer the page entirely with an empty state - considered
reasonable, but rejected since real (if narrower) data already exists and
costs nothing new to surface.

Option B (chosen): Labeled proxy view.

Trade-offs

Pros

Ships something real and useful now; zero new infrastructure.

Cons

Not true API-request-level metrics (rate, latency, per-endpoint
breakdowns) - still gated on the pre-existing `GET /metrics` gap.

Future Review

Revisit once BACKLOG.md §3's Prometheus `/metrics` work is picked up - real
telemetry should replace this proxy, not sit alongside it indefinitely.

---

# ADR-125

Title

Hourly Watchlist Signal Generation Skips Assets With an Open Call

Status

Accepted

Context

`signals.generate_for_watchlist` (`app/workers/signal_tasks.py`, ADR-089/
docs/51 §6, docs/57 §1) re-runs the full AI orchestration for every
active/seeded asset every hour regardless of whether that asset already
has an unresolved BUY/SELL call outstanding. Because H1 candles rarely
move enough between runs to flip the AI's recommendation, this produced
the same asset+direction signal being generated and broadcast to Telegram
again on the very next run, often several times before the original call
ever resolved (docs/57 §8 already flagged "deduplication" as a deferred
gap).

Decision

Before calling `SignalEngine.generate()` for an asset, the task checks
`_has_open_signal()`: does that asset already have a `Signal` on
`Timeframe.H1` whose `effective_status` (`status_resolver.py`, ADR-088) is
still `ACTIVE` right now? If so, skip the asset for this run entirely -
no AI call, no new `Signal` row, no Telegram send. Generation resumes for
that asset once the open call closes (TP/SL hit, via
`signal_monitoring_tasks.py`) or expires (`signal_ttl_hours` TTL).

Reason

The confirmation gate is scoped to asset+timeframe, not asset+direction:
an asset with an open BUY call shouldn't also get a contradicting SELL
call broadcast an hour later either. Reusing `effective_status` (rather
than trusting the stored `status` column) means a stored-ACTIVE-but-
TTL-expired row can't wedge an asset out of generation forever - it's the
exact same read-time check `signal_monitoring_tasks.py` already applies.
This is a generation-time gate, not a new per-user notification
preference, so the broadcast-to-all-linked-accounts delivery model (docs/57
§5) is unchanged.

Alternatives Considered

Option A: Confidence threshold (only send if `confidence_score` above some
cutoff) - rejected for this pass; doesn't address the core issue (an
unchanged setup re-alerting every hour) and requires picking an arbitrary
number with no product input.

Option B: Require N consecutive hourly runs to agree before sending -
rejected for this pass; adds cross-run state tracking for a benefit
(filtering one-off noise) distinct from the reported problem (repeat
alerts for the same already-open call).

Option C (chosen): Skip generation entirely while an open call exists for
that asset/timeframe.

Trade-offs

Pros

Directly fixes the reported spam; saves AI-orchestration/API cost on
assets that would just re-confirm the same call; minimal, localized
change (`app/workers/signal_tasks.py` only).

Cons

An asset can still only ever have one open call at a time on H1 - by
design, but means a genuinely new, stronger setup on the same asset won't
generate a second signal until the first resolves or expires.

Future Review

If users want faster reaction to a strengthening/reversing setup while a
call is still open, revisit with either Option A or B above as an
addition, not a replacement.

---

# ADR-126

Title

Chart Data Uses Interval Polling, Narrowing ADR-105's Live-Update
Deferral

Status

Accepted

Context

ADR-105 (Phase 7B, docs/54) deferred "live/streaming updates" alongside
drawing tools and fullscreen, on the grounds that no live-price WebSocket
backend exists - `docs/04`'s `/ws/prices` endpoint is still an
unimplemented stub, tracked in BACKLOG.md §3 since Phase 3. That
deferral remains true: this project still has no streaming price
infrastructure.

Decision

`use-candles.ts` and `use-latest-candle.ts` poll `GET
/market/{symbol}/candles` and `GET /market/{symbol}/latest` on a 15s
`refetchInterval`, restricted to the M1 and M5 timeframes only, with
`refetchIntervalInBackground: false`. The two hooks' shared
`LIVE_TIMEFRAMES`/`LIVE_POLL_INTERVAL_MS` constants live in one module,
`frontend/hooks/live-polling.ts`.

Reason

This is polling, not streaming - it does not implement or presuppose
`/ws/prices`, so ADR-105's WebSocket deferral stands unchanged. M1/M5
are the only timeframes Celery Beat's `collect_market_data_task`
refreshes often enough (every 60s/300s respectively, see
`app/workers/market_data_tasks.py`) for polling to surface genuinely new
rows - anything H1 and above would just re-fetch identical data, so
polling is scoped out for those timeframes. This is also a plain DB read
against our own API, not an external provider call, so it costs nothing
against the Twelve Data daily/per-minute quota (docs/40, ADR-025).
Drawing tools and fullscreen from ADR-105 remain deferred and untouched
by this change.

Alternatives Considered

Option A: Leave chart data static until the user manually refreshes -
rejected; M1/M5 candles go stale within a minute, and the underlying
data already refreshes on that cadence server-side, so not surfacing it
client-side is needless staleness for free.

Option B: Poll all timeframes uniformly - rejected; H1 and above only
get new rows on a much longer cadence, so polling them every 15s would
just re-fetch identical data for no benefit.

Option C (chosen): Poll M1/M5 only, at 15s, via a shared
`live-polling.ts` constants module used by both chart hooks.

Trade-offs

Pros

Chart data on the two shortest timeframes stays close to current without
any new backend work, streaming infrastructure, or provider cost; the
polling constants live in one place instead of being duplicated across
hooks.

Cons

Still not true live/streaming updates - a genuinely live tick feed still
requires the deferred `/ws/prices` work from ADR-105. M15 and above see
no improvement.

Future Review

The 15s interval is a starting point, not empirically calibrated - same
caveat as every prior scoring/threshold ADR in this project. Revisit
ADR-105's Live Updates deferral itself (true streaming) once a
`/ws/prices` backend exists.

---

# ADR-127

Title

Per-User Fixed-Window Quota on the Two LLM-Token-Spending Endpoints

Status

Accepted

Context

`POST /analysis/ai/{symbol}` and `POST /chat/conversations/{id}/messages`
are the only two routes in this project that spend real OpenAI tokens per
call, and until now both were gated by authentication only - `get_current_
user` (Phase 2C) has only ever authenticated, never throttled. With
production about to run with a live OpenAI API key, an authenticated user
could call either endpoint an unbounded number of times and run up
unbounded spend. This is the first *inbound* throttle this project has
ever built. All prior "rate limit" code (`RateLimitedProvider`, ADR-025)
governs *outbound* calls to market-data/news providers to stay under
their quota - a completely different concern from protecting our own
spend against our own users. BACKLOG.md §20 and §22 flagged this exact
gap for the AI Signal Engine and AI Chat Assistant respectively; §3
separately tracks general-purpose API rate limiting (e.g. for the public,
unauthenticated market-data routes) as still deferred - that is a much
larger design question this change does not attempt to answer.

Decision

`app/dependencies/quota.py` adds `require_quota(bucket, limit,
window_seconds)`, a dependency factory mirroring `app/dependencies/
rbac.py`'s shape: it composes `get_current_user` via `Depends()` and does
not modify it. It maintains a per-user fixed-window counter in Redis
keyed on `quota:{bucket}:{user_id}`, using the module-level Redis client
already established by `app/api/v1/routes/health.py` (but created once,
not per-request, since this sits on a hot path rather than a healthcheck).
The counter's TTL is set to the window length so keys expire on their own.
Two independent buckets are wired up via `app/config/settings.py`:
`ai_analysis_quota_limit`/`ai_analysis_quota_window_seconds` on `POST
/analysis/ai/{symbol}`, and `ai_chat_quota_limit`/`ai_chat_quota_window_
seconds` on `POST /chat/conversations/{id}/messages`. Exceeding the limit
raises the new `QuotaExceededException` (`app/exceptions/quota.py`),
mapped to HTTP 429 through the project's standard `{"error", "message"}`
envelope the same way `InsufficientRoleException` already is. If Redis is
unreachable or raises any exception, the dependency logs a warning and
allows the request through (fail open). No role, including Super Admin,
is exempt.

Reason

Fail-open beats fail-closed here because this is a soft cost guard on a
core product feature, not a security control - a Redis outage taking down
AI analysis or chat for every user would be a strictly worse outcome than
occasionally letting a burst of requests through uncounted. This mirrors
the degrade-rather-than-block precedent already set by `app/services/
news_sentiment/ai_summary_generator.py` (ADR-051), which returns `None`
on any OpenAI failure rather than blocking news ingestion. No admin
exemption was a deliberate choice: an Admin or Super Admin account is not
inherently less likely to be compromised or scripted against, and the
quota is protecting the project's OpenAI bill, not gating a privileged
capability, so role has no bearing on it. This is intentionally not a
general rate limiter - it does not touch the public, unauthenticated
market-data routes (still tracked in BACKLOG.md §3), does not use a
sliding window or token-bucket algorithm, and exposes no reusable
middleware; it is two narrowly-scoped `Depends()` calls on the two routes
that actually cost money per call. Separately, the hourly Celery task
`signals.generate_for_watchlist` (ADR-125) calls `SignalEngine.generate()`
in-process, not over HTTP, so it never passes through `get_current_user`
or this dependency at all - ADR-125's `_has_open_signal()` gate remains
its only cost control. The two are complementary, not redundant: ADR-125
bounds AI-orchestration spend from scheduled, system-initiated generation,
while this ADR bounds it from user-initiated, per-call requests.

Alternatives Considered

Option A: Sliding-window or token-bucket rate limiting - rejected for
this pass; a fixed window is simpler to reason about and implement
correctly with two Redis calls, and the goal here is a hard per-window
cost ceiling, not smoothing burst traffic.

Option B: A general-purpose rate-limiting middleware applied project-wide
- rejected; the two AI endpoints are the only ones with a real per-call
cost, and applying throttling to routes that don't need it (including the
public market-data routes) is a separate, larger design question
(BACKLOG.md §3) that shouldn't be bundled into a narrow production-safety
fix.

Option C: Exempt Admin/Super Admin from the quota - rejected; an explicit
user decision that the quota is a cost guard, not a privilege gate, so it
applies uniformly.

Option D (chosen): Per-user fixed-window Redis counters, fail-open, no
role exemption, applied to exactly the two per-call-costed routes.

Trade-offs

Pros

Directly bounds unbounded per-user spend on the only two token-costed
endpoints before live OpenAI keys go into production; minimal, localized
change (`app/dependencies/quota.py`, `app/exceptions/quota.py`, two route
files, settings); reuses the existing Redis connection and exception-
envelope patterns rather than inventing new ones.

Cons

Fixed windows allow a burst at the window boundary (e.g. a user could
send `limit` requests at the end of one window and another `limit` just
after it rolls over). Fail-open means a sustained Redis outage
temporarily removes the cost guard entirely, trading spend protection for
availability. The chosen limits are not derived from any observed usage
data.

Future Review

The default limits (`ai_analysis_quota_limit`, `ai_chat_quota_limit`, and
their window lengths) are hand-picked starting points, not empirically
calibrated - the same caveat as every prior threshold ADR in this
project. Revisit once real production usage data exists. If burst-at-
boundary behavior proves to be a real problem, revisit with a sliding-
window or token-bucket algorithm (Option A) as a replacement. If the
public market-data routes ever need protection, that is BACKLOG.md §3's
separate, larger scope - not an extension of this dependency.

---

# ADR-128

Title

Watchlists Backend (7D-A): `GET /watchlists/{id}`, Item Uniqueness, and
`CreatedAtMixin` Choice

Status

Accepted

Context

Phase 7D-A builds exactly `docs/03` §12's two tables
(`watchlists`/`watchlist_items`) and `docs/58` §2's contract, per ADR-114's
scope decision. Three schema/API details in this build are inferred
beyond the literal text of `docs/03`/`docs/04` and need recording here per
CLAUDE.md's "never invent architecture" rule, the same practice already
applied to `signals.created_at` (ADR-091) and `signal_bookmarks`'
uniqueness (ADR-090).

Decision

1. `GET /watchlists/{id}` is added as a new endpoint returning a single
   watchlist with its member assets resolved to full `AssetResponse` rows
   - `docs/04`'s literal Watchlists section only lists `GET /watchlists`,
   `POST /watchlists`, `PUT /watchlists/{id}`, `DELETE /watchlists/{id}`,
   and the two `.../assets` routes. `docs/58` §2.3 already anticipated
   this addition for the 7D-B detail view; this ADR is what makes it
   official per the "inferred addition" pattern ADR-091 established.
2. `watchlist_items` gets a unique constraint on `(watchlist_id,
   asset_id)` (`uq_watchlist_items_watchlist_asset`) - an asset cannot be
   added to the same watchlist twice. Follows `OAuthAccount`'s
   `(provider, provider_user_id)` precedent (ADR-022) and
   `signal_bookmarks`' `(user_id, signal_id)` precedent (ADR-090)
   directly; `docs/03` §12 lists the columns but never states a
   uniqueness rule.
3. Both `watchlists` and `watchlist_items` use `CreatedAtMixin`, not
   `TimestampMixin` - `watchlists.name` is the only column either table
   ever mutates after creation (renaming), and `watchlist_items` rows are
   never updated in place at all (an item is either present or absent,
   the same append-only reasoning as `signal_bookmarks`, ADR-090). Neither
   table needs `updated_at`.

Reason

All three are the same class of decision this project has made
repeatedly: `docs/03`/`docs/04` specify the columns/routes a table or
endpoint set needs at the level of "what data, what shape," not every
uniqueness constraint or supporting read endpoint a working
implementation requires. Rather than silently adding these or, worse,
leaving `GET /watchlists/{id}` unbuilt and blocking 7D-B's detail view,
each is recorded here so the schema/API stays traceable back to an
explicit decision instead of an implementation detail no one chose on
purpose.

Alternatives Considered

Option A (`GET /watchlists/{id}`): Have the frontend compose a detail
view purely from `GET /watchlists` (list, already has item counts) plus
per-asset `GET /assets/{symbol}` calls - rejected; this means N+1 calls
for every watchlist detail view for no benefit over one endpoint that
already has the watchlist and its items in hand.

Option B (item uniqueness): Allow duplicate `(watchlist_id, asset_id)`
rows and de-duplicate for display - rejected; a duplicate row has no
legitimate meaning (the asset either is or isn't on the list), same
reasoning ADR-090 already gave for `signal_bookmarks`.

Option C (mixin choice): Use `TimestampMixin` on both tables for
consistency with `docs/03` §1's stated default - rejected; §1's default
is already overridden case-by-case throughout this project
(`ai_analysis`, `signals`, `signal_bookmarks`, `news_articles`) wherever a
table is genuinely append-only or has no second mutable column, and
`BACKLOG.md` §1 already flags §1's blanket rule as unreconciled with
per-table reality.

Trade-offs

Pros

Keeps the schema/API exactly as narrow as ADR-114 intends while still
supporting the one read shape 7D-B genuinely needs; the uniqueness
constraint prevents a meaningless duplicate state from ever existing;
consistent with every prior inferred-schema ADR in this project.

Cons

`GET /watchlists/{id}` is one more endpoint than `docs/04`'s literal text
lists, so a reader relying on `docs/04` alone without also checking this
ADR could be surprised by it - mitigated by updating `docs/04` §Watchlists
in the same phase (§2.7 of the build spec).

Future Review

None of ADR-114's excluded features (alerts, tags, pinning, AI summary,
performance history) are touched or made easier/harder to build later by
this ADR - they remain deferred exactly as ADR-114 left them, pending
their own documentation-first pass.

---

# ADR-129

Title

Audit Logs (8F) Is a Read-Only API Over an Already-Written Table, With an
Inferred `GET /admin/logs` Contract

Status

Accepted

Context

`BACKLOG.md`'s 8F entry describes "reuses the existing `AuditLog` table
for every admin mutation," which reads like a wiring task. It is not:
`AuthenticationService` (Phase 2B - `login_success`, `login_failed`,
`logout`, `session_revoked`) and `AdminUserService` (Phase 8C -
`admin_user_created`, `admin_user_updated`, `admin_user_disabled`,
`admin_user_activated`, `admin_role_changed`, `admin_password_reset`,
`admin_user_deleted`) already write every audit row this project
produces today. What was actually missing was the read side:
`AuditLogRepository` had only `list_for_user` (no admin-wide listing,
filtering, or count), no `GET /admin/logs` route existed, and
`docs/04` lists the bare path with no query params or response shape -
the contract is therefore inferred, the same category of gap ADR-091
(`signals.created_at`) and ADR-128 (`GET /watchlists/{id}`) already
covered for other phases.

Decision

1. `AuditLogRepository` gains `list_admin`/`count_admin`, filterable by
   `user_id`, `action`, `resource`, and a `created_at` `from`/`to` range,
   always ordered newest-first. `UserRepository` gains `list_by_ids` (a
   batch lookup) so `AdminAuditLogService.list_logs` can resolve every
   distinct actor on a page in one query instead of one per row.
2. `GET /admin/logs` (`app/api/v1/routes/admin_logs.py`) is the endpoint
   `docs/04` names but never specified - `user_id`/`action`/`resource`/
   `from`/`to`/`page`/`limit` query params, the same
   `{"items", "page", "limit", "total"}` envelope `GET /admin/users`
   already uses, gated by the existing `require_admin` (ADR-115/ADR-122,
   Phase 8B) with no new role-check logic.
3. The API is read-only by construction, not just by convention:
   `AdminAuditLogService` has no create/update/delete method, and no
   route exists that could mutate or remove a row. An audit trail that
   its own viewing API could tamper with would defeat the reason it
   exists.
4. This phase adds zero new audit-write call sites. `docs/25` §14 names
   seven record types - User Action, Admin Action, AI Decision,
   Configuration Change, Login, Logout, Security Events - and only
   Admin Action, Login, and Logout are actually written anywhere in this
   codebase today. "AI Decision" and "Configuration Change" have no
   write call site at all. That gap is recorded here as explicitly
   deferred, not built speculatively now, per "never invent
   architecture" - a real AI Decision/Configuration Change audit trail
   needs its own scoping pass (which mutations count, what the context
   shape is) rather than a guess bundled into a read-side phase.

Reason

Every part of this decision follows an existing precedent rather than
inventing a new one: the inferred-endpoint-needs-an-ADR pattern
(ADR-091/ADR-128), the list/count/pagination shape `AdminUserService`/
`GET /admin/users` already established, and the batch-lookup-over-N+1
reasoning any admin list view with a foreign-key-to-display problem
would need. The read-only constraint is the one genuinely load-bearing
choice: `AuditLog` rows are the evidence trail for every other admin
decision in this system, so the read API is deliberately incapable of
being the thing that erases or edits that evidence.

Alternatives Considered

Option A: Add a `DELETE /admin/logs/{id}` for retention/cleanup purposes
- rejected; no retention policy has been specified anywhere (`docs/03`
§18's general data-retention gap, `BACKLOG.md` §5), and building
deletion before a retention decision exists risks becoming the
mechanism an admin uses to cover their own tracks, which is the exact
failure mode an audit log exists to prevent.

Option B: Build write call sites for "AI Decision"/"Configuration
Change" now, since the table already supports it - rejected; docs/25
§14 names the categories but specifies neither which mutations qualify
nor what `context` shape they'd carry. Guessing both violates "never
invent architecture" for a table that already has real, correctly-
scoped writers; this is real follow-up work needing its own pass, not a
free addition to a read-side phase.

Option C (chosen): Read-only `GET /admin/logs`, filtered/paginated/
newest-first, zero new write call sites, the docs/25 §14 gap recorded
as deferred rather than filled.

Trade-offs

Pros

Closes the actual gap (nobody could browse audit history through the
API before this) without touching the parts of the system that were
already correct; batch actor-resolution keeps the list view from
becoming an N+1 liability; the read-only constraint needs no new
authorization nuance - `require_admin` is sufficient since there is
nothing more dangerous than reading available to gate.

Cons

Four of docs/25 §14's seven record types remain unwritten
(`Configuration Change`, `AI Decision` - two are simply *categories*
`Admin Action` already covers under different phrasing, e.g. `User
Action` overlaps `Admin Action`'s existing rows). An admin cannot yet
see AI recommendation history or configuration changes in this view,
because nothing generates those rows yet.

Future Review

Revisit `Configuration Change`/`AI Decision` write coverage as its own
scoped phase once a concrete need names which mutations qualify and what
`context` they should carry - not by guessing here. Revisit deletion/
retention only alongside a real `docs/03` §18 data-retention policy
decision, never as a bare admin-triggered delete.

---

# ADR-130

Title

Admin Backend (7D-C, Rescoped): Five Inferred Contracts, One Shared
Ingestion Implementation, and a Signal Scoping Correction

Status

Accepted

Context

`docs/58` §3.2 lists seven `/admin/*` endpoints; `GET /admin/users`
(Phase 8C) and `GET /admin/logs` (Phase 8F, ADR-129) already exist. This
phase builds the remaining five - `GET /admin/{signals,system,analytics}`,
`POST /admin/{news,maintenance}` - and resolves three things found while
scoping it that this ADR records rather than re-litigates later:

1. `docs/04` lists all five paths with no query params or response
   shape - the same inferred-contract category ADR-091/ADR-128/ADR-129
   already established.
2. `BACKLOG.md` §16 stated `POST /admin/news` was "explicitly decided
   against," citing `docs/04:567`. That citation actually reads
   "deferred - not built," and `docs/58` §3.2 (later, approved,
   ADR-backed) puts it back in scope. The Phase 5A reasoning BACKLOG
   recorded - "would be the first auth-gated route in an otherwise
   fully-public analysis surface" - is moot now that every `/admin/*`
   route and the quota'd AI endpoints are already auth-gated.
   `BACKLOG.md` §16 is corrected to say "deferred, then brought into
   scope by docs/58," not "decided against."
3. `docs/58` independently specifies both `POST /admin/news` and
   `POST /admin/maintenance {"action": "refresh_news"}`, which do the
   same thing. Docs are the source of truth, so both are built - but
   backed by one shared implementation, not two copies of the ingestion
   trigger.

Decision

1. New `app/api/v1/routes/admin_system.py` and `AdminSystemService`
   (mirrors `AdminUserService`/`AdminAuditLogService`'s shape) cover all
   five endpoints, every route gated by the existing `require_admin`
   (Phase 8B) with no new role-check logic.
2. `GET /admin/signals` reuses `SignalRepository.find_paginated`/
   `count_filtered` verbatim, same `{"items","page","limit","total"}`
   envelope and `symbol`/`status`/`page`/`limit` params `GET /signals`
   already uses. **Signal scoping finding:** `docs/58`'s "admin view (all
   users, not just caller's)" phrasing implies `GET /signals` is
   per-user today. It is not - `app/models/signal.py` has no `user_id`
   column at all (only `signal_bookmarks` is per-user, ADR-090), and the
   existing `GET /signals` route never filters by `current_user`. This
   admin endpoint is therefore scope-identical to the public one; it
   exists to give `/admin/*` a consistent dashboard entry point, not to
   unlock previously-hidden rows. Recorded as a misframing in docs/58,
   not a requirement this phase needs to build against.
3. `GET /admin/system` reuses `/health/ready`'s exact checks (`SELECT 1`,
   Redis `ping()`) plus `SignalRepository.count_since`/`AIAnalysisRepository.
   count_since` for today's activity (ADR-116 reaffirmed: liveness +
   counts, not telemetry). Unlike `/health/ready`, each check is caught
   independently - a dependency failure renders `"down"` in a 200
   response; this endpoint must never 500 the way a bare liveness probe
   is allowed to.
4. `GET /admin/analytics` implements exactly `docs/58`'s two named
   figures: daily active users (`UserSessionRepository.
   count_distinct_users_since`, today's distinct `user_id`) and a
   distribution grouped on `signals`. **Second docs/58 imprecision
   found:** it says "GROUP BY on `signals.recommendation`," but `signals`
   has no `recommendation` column - that field lives on `ai_analysis`.
   `Signal.signal_type` (BUY/SELL) is the only field on `signals` a
   distribution "on signals" can mean, and every `Signal` row is already
   BUY-or-SELL-only by construction (ADR-086 - WAIT produces no row), so
   this reading loses no information the literal wording would have
   captured. `docs/25` §15's longer wishlist (most-viewed assets,
   confidence distribution, average AI response time) is explicitly
   deferred - no view-tracking or latency-recording infrastructure
   exists to source those from.
5. `POST /admin/news` and `POST /admin/maintenance {"action":
   "refresh_news"}` both call `AdminSystemService.refresh_news`; `POST
   /admin/maintenance {"action": "refresh_calendar"}` calls `.
   refresh_calendar`. Each method builds the identical pipeline
   (`NewsIngestionPipeline`/`EconomicCalendarIngestionPipeline`) the
   `news_sentiment.ingest`/`economic_calendar.ingest` Celery tasks
   already use, runs it inline, and writes exactly one `AuditLog` row
   (`admin_news_refreshed`/`admin_calendar_refreshed`) recording the
   acting admin and the outcome counts - following `AdminUserService.
   _audit`'s established pattern, not new architecture.
   `MaintenanceActionRequest.action` is a `Literal["refresh_news",
   "refresh_calendar"]`, so an unknown action is rejected by schema
   validation (422) before the handler runs - no "restart workers"/
   "clear cache"/"rebuild indicators" (ADR-117 reaffirmed: none has a
   concrete implementation to call, and this project's engines are
   stateless).
6. **Known, accepted tradeoff:** `docs/58` specifies calling the
   pipeline directly, which makes both ingestion routes blocking HTTP
   requests running a full ingestion inline - potentially several
   seconds, a candidate for a gateway timeout under load. Dispatching
   the existing Celery task instead (`.delay()`, returning `202`) would
   avoid this, but deviates from the approved spec. This phase follows
   docs/58 and calls directly; if inline latency becomes a real problem,
   the fix is switching to Celery dispatch, not reworking the pipelines
   themselves.

Reason

Every piece follows a precedent already established in this project
rather than inventing one: the inferred-contract-needs-an-ADR pattern,
`AdminUserService`'s constructor-injected/one-method-per-use-case shape,
and `_audit`'s established mutation-logging pattern. The two docs/58
imprecisions (signal scoping, `signals.recommendation`) are resolved by
reading what actually exists in the schema rather than inventing a
`user_id` column or a `recommendation` field neither `docs/03` nor any
migration ever specified - consistent with "never invent architecture."
Building both `POST /admin/news` and `/admin/maintenance` (rather than
dropping the "redundant" one) respects "documentation is the source of
truth" over an engineering judgment that one of them is unnecessary.

Alternatives Considered

Option A (signal scoping): Add a `user_id` column to `signals` to make
docs/58's "all users" phrasing literally true - rejected; no such column
exists in `docs/03`, no phase has ever proposed one, and inventing it
here to match a two-word doc phrase is exactly the "invent architecture"
failure mode this project avoids.

Option B (`signals.recommendation`): Query `ai_analysis.recommendation`
instead, since that field actually has that name - rejected; docs/58
explicitly says "GROUP BY on signals.recommendation" (the table, not
`ai_analysis`), and `ai_analysis` includes WAIT rows that never became a
`Signal`, which would silently change what "signal distribution" means
beyond what a `signals`-scoped query implies.

Option C (ingestion latency): Dispatch via Celery (`.delay()`, `202
Accepted`) instead of calling the pipeline inline - rejected for this
pass; deviates from docs/58's literal spec without a demonstrated need,
and an admin-invoked manual refresh is inherently low-frequency, unlike
the scheduled Beat job this would otherwise resemble.

Option D (chosen): Build all five endpoints exactly as docs/58
specifies, correct the two documentation imprecisions found by reading
the actual schema rather than working around them silently, and record
the synchronous-ingestion tradeoff for future reconsideration rather
than fixing it now.

Trade-offs

Pros

Closes docs/58's remaining scope with zero new schema and zero
duplicated ingestion logic; both documentation inaccuracies (BACKLOG §16,
the `signals.recommendation` field name) are corrected in place rather
than silently worked around, so a future reader doesn't rediscover
either; `GET /admin/system` degrading instead of erroring makes it
usable as an actual liveness dashboard.

Cons

`POST /admin/news`/`/admin/maintenance` remain blocking, multi-second
requests under real provider load (Option C's deferred tradeoff);
`GET /admin/analytics` covers only 2 of docs/25 §15's much longer
wishlist, same gap ADR-129 already recorded for audit-log coverage.

Future Review

Revisit synchronous ingestion (Option C) if a real gateway-timeout
incident occurs. Revisit `docs/25` §15's remaining analytics figures once
view-tracking/latency-recording infrastructure exists to source them
from - not by approximating with data that doesn't measure the same
thing. If a future phase ever needs true per-user signal filtering
(e.g. "signals for assets in my watchlist"), that is a new join against
`watchlist_items` (Phase 7D-A), not a `user_id` column on `signals`.

---

# ADR-131

Title

Admin Frontend (7D-D): No Chart Library, Confirmation-Gated Maintenance
Actions

Status

Accepted

Context

`docs/58` §3.3 describes the Admin frontend as introducing "the first
chart dependency" for Signal Statistics, assuming `docs/25` §15's richer
analytics set (most-viewed assets, confidence distribution, average AI
response time). ADR-130 already deferred all of that for lack of
view-tracking/latency infrastructure - what `GET /admin/analytics`
actually returns is two figures (`daily_active_users: int`,
`signal_type_distribution: dict[str, int]`, roughly two keys), and
`GET /admin/system` returns four scalars. `docs/58` §3.3's chart-library
premise was written against data that was never built and, per ADR-130,
isn't being built now either.

Separately, `POST /admin/news`/`POST /admin/maintenance` (ADR-130) are
real, consequence-bearing actions from this phase's frontend for the
first time: they call a live vendor synchronously and can consume real
production API quota. This project has already had two real-vendor-call
incidents from insufficiently-isolated tooling (Twelve Data quota
exhaustion, a live NewsAPI call during 7D-C manual verification - both
recorded in `BACKLOG.md` §11/§16, mitigated for local dev by commit
`9ccd471`). A frontend button is a third, user-facing way to trigger the
same class of consequence, in production, deliberately - it needs its
own explicit safeguard, not just a "hope the operator reads the docs"
assumption.

Decision

1. **No charting library is added.** `admin/system-health` and
   `admin/signal-statistics` (docs/58 §3.3) render their data as stat
   tiles (`StatCard`, extracted from the existing `admin/page.tsx` for
   reuse rather than duplicated) and a plain CSS proportion bar
   (`SignalTypeDistributionBar`) built from `components/shared/premium`'s
   `Panel`/`PanelHeader` and existing `Badge`/`lib/badge-variants`
   mappings (a new `systemStatusVariant` added there for `"ok"`/`"down"`).
   `lightweight-charts` (already a dependency, Phase 7B) is a financial
   candlestick charting library and is not pressed into service for a
   two-segment bar.
2. `admin/signals`'s stale docstring claim - "the existing `GET /signals`
   is scoped to the caller's own signals" - is corrected. ADR-130 already
   established `Signal` has no `user_id` column at all; `GET /admin/signals`
   is scope-identical to the public `GET /signals`, not a newly-unlocked
   admin-only view.
3. Exactly two maintenance-action buttons exist - Refresh News, Refresh
   Calendar - placed on System Health (the operational liveness page,
   which already shows today's activity counts these actions affect), not
   Settings. Both are gated by the existing `ConfirmActionDialog` (no new
   confirmation component), with copy that states the real consequence
   ("calls the configured \[news/economic calendar\] provider... may
   consume real vendor API quota... runs synchronously and can take
   several seconds") rather than a generic "Are you sure?". Each
   triggering button is disabled for the full in-flight duration (`useMutation`'s
   `isPending`, not just while the dialog is open), and each mutation
   (`use-admin-maintenance-actions.ts`) wraps its `apiPost` call in a
   60-second client-side `AbortController` timeout, so a hung request
   (dropped connection, an unresponsive vendor) surfaces as a toast error
   and re-enables the button instead of leaving it disabled forever. On
   success, the returned counts (`articles_ingested`, or
   `events_created`/`events_updated`) are shown via the existing toast
   pattern and the system-status query is invalidated so
   `signals_today`/`ai_analyses_today` reflect the run without a manual
   reload.
4. `admin/api-usage` remains the Phase 8D placeholder - no request-metrics
   infrastructure exists (`GET /metrics`, `BACKLOG.md` §3), and this phase
   does not fabricate numbers to fill the gap.

Reason

Adding a chart dependency for four scalars and a two-key dictionary would
be exactly the kind of premature-abstraction-for-hypothetical-future-data
this project's own working style avoids - `docs/58` §3.3 scoped the chart
for analytics that were deliberately deferred, not analytics that exist.
Removing a chart dependency once added is real work (component rewrites,
bundle-size regression, a second design pass); not adding one until the
data justifies it costs nothing now. The maintenance-action safeguards
are load-bearing, not decorative, precisely because this codebase has
already demonstrated (twice) that "remember to be careful" is not a
sufficient control for a real-vendor-call trigger - confirmation copy
that states the actual consequence, an enforced disabled-while-in-flight
state, and a bounded timeout are the three concrete failure modes (fired
by accident, fired twice, stuck forever) a button like this can produce.

Alternatives Considered

Option A: Add `recharts` (or equivalent) anyway, per `docs/58` §3.3's
literal text, and render simple bar/line components against the current
two-figure payload - rejected; a chart library for two data points
provides no more information than the tiles/bar it would replace, at the
cost of a new dependency, bundle size, and a second design pass for
almost no analytics currently in scope to chart against.

Option B: Put the maintenance-action buttons on Admin Settings instead of
System Health - considered; System Health was chosen because it already
displays the exact counts (`signals_today`/`ai_analyses_today`... not
directly the ingestion counts, but the operationally-adjacent liveness
view) these actions affect, and is the more natural "trigger an
operational action" destination than a general settings page. Settings
remains untouched and out of scope for this phase either way.

Option C: Skip the client-side timeout, relying on the backend's own
(currently unbounded) synchronous request duration - rejected; ADR-130
already accepted synchronous ingestion as a known tradeoff server-side,
but the frontend has no visibility into whether a hung connection will
ever resolve, and "the button stays disabled forever" is a worse failure
mode than a timeout that might fire slightly early on a genuinely slow
but still-succeeding request.

Option D (chosen): No chart library; confirmation-gated, timeout-bounded,
in-flight-disabled maintenance buttons on System Health.

Trade-offs

Pros

Zero new frontend dependencies or bundle-size cost; the proportion bar
and stat tiles are exactly as informative as the current payload
supports; the maintenance-action safeguards directly address this
project's own documented incident history rather than a hypothetical one.

Cons

If richer analytics ever ship (per `docs/25` §15, still deferred), the
proportion-bar/stat-tile approach will need to be revisited - this is an
explicitly deferred cost, not an oversight. The 60-second timeout is a
hand-picked starting point, not empirically calibrated against real
vendor latency.

Future Review

Revisit the no-chart-library decision the moment `docs/25` §15's richer
analytics figures are actually built (real view-tracking, real latency
recording) - that is the point ADR-130's Future Review already names as
when a charting choice would be justified by real data. Revisit the
60-second maintenance-action timeout if real vendor calls are observed
routinely taking longer (or timing out spuriously sooner) once a real
`TELEGRAM_BOT_TOKEN`/`NEWS_API_KEY`/`ECONOMIC_API_KEY` is in production use.

---

# ADR-132

Title

Phase 9A: Trusted-Proxy Client-IP Resolution, Per-IP Rate Limiting, CORS
Scoping, and Baseline Security Headers

Status

Accepted

Context

Ten route modules (`technical_analysis`, `smc`, `market_regime`,
`analysis_confidence`, `strategy`, `risk_management`, `market_data`,
`news`, `economic_calendar`, `health`) are unauthenticated by design
(docs/60 §2, preserving the Phase 3C "public read-only API" decision),
and six of them run a full engine pass over ~500 candles per request.
None had any rate limit - ADR-127's quota only ever covered the two
LLM-token-spending endpoints. Production runs on a 911MB RAM / 2 vCPU box
already ~330MB into swap (BACKLOG.md §10); an unthrottled loop against
any one of the six engine routes can exhaust it.

Building a per-IP limit exposed a pre-existing bug first: `request.
client.host`, read directly by `admin_system.py`'s and `admin_users.py`'s
identically-named `_client_ip` helpers and an inline expression in
`auth.py`'s login route, resolves to Nginx's own loopback address in
production (docs/27 puts Nginx in front of the app), not the real
client. This meant every audit-trail `ip_address` was almost certainly
wrong in production (BACKLOG.md §4), and - more urgently for this phase -
a per-IP rate limit built directly on top of it would have keyed every
request to the same "client," either tripping instantly for the whole
site or requiring a limit so high it would protect nothing.

Separately, `app/main.py`'s CORS configuration
(`allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True`)
had been flagged as broader than necessary since before Phase 1.1
(BACKLOG.md §4), and the app set no baseline security response headers
at all.

Decision

1. **Client IP resolution goes through uvicorn's own
   `ProxyHeadersMiddleware`**, enabled explicitly via `--proxy-headers
   --forwarded-allow-ips <Settings.trusted_proxy_ips>` (default
   `"127.0.0.1"`) rather than relied on as uvicorn's own default (which
   already happens to match, but depending on an upstream default that
   could change, or that a different ASGI runner might not share, was
   judged not worth the risk). This rewrites `request.client` from
   `X-Forwarded-For` only when the immediate TCP peer matches the
   configured trusted address - an untrusted peer's forged header is
   never applied, so application code never parses that header itself.
   `backend/scripts/run_dev.py` passes both flags for local `api` mode;
   production must add them to the uvicorn `ExecStart` line (operator
   action, not deployed by this change - see the build report).
2. **One shared helper, `app/core/client_ip.py::get_client_ip`**,
   replaces the two duplicate `_client_ip` functions and the inline
   expression in `auth.py`. It is intentionally as simple as the code it
   replaced (`request.client.host if request.client else None`) - all of
   the actual security property comes from (1), not from any logic in
   this function.
3. **Per-IP rate limiting extends `app/dependencies/quota.py`'s existing
   Redis fixed-window pattern** (`app/dependencies/rate_limit.py`) rather
   than adding a library (`slowapi` or otherwise). Keyed by client IP
   instead of user id; applied at router-include time
   (`app/api/v1/router.py`'s `include_router(..., dependencies=[...])`)
   rather than per-handler, since the nine affected modules have roughly
   30 handlers between them; fails open on any Redis exception, same
   rationale as ADR-127. `/health*` is excluded outright. Two tiers -
   `public_engine` (limit 20/60s) for the six expensive modules,
   `public_data` (limit 100/60s) for the three cheap-read modules - sized
   against measured real frontend traffic (docs/60 §4.2), not guessed.
4. **CORS scoped to actual usage**: `allow_methods=["GET", "POST", "PUT",
   "PATCH", "DELETE"]`, `allow_headers=["Content-Type", "Authorization"]`,
   matching `frontend/services/api-client.ts`'s only caller.
   `allow_credentials` changed to `False` - nothing ever set `credentials:
   "include"` on a `fetch()` call, so it was dead configuration, not a
   real requirement.
5. **A new `SecurityHeadersMiddleware`** sets `X-Content-Type-Options:
   nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy:
   strict-origin-when-cross-origin` on every response. A full
   `Content-Security-Policy` is explicitly out of scope for this decision
   - see Trade-offs.

Reason

The client-IP fix has to come before the rate limiter, not alongside it,
because a rate limiter built on the old helper would have been actively
dangerous in production (see Context) rather than merely ineffective.
Reusing `quota.py`'s Redis pattern instead of adding a rate-limiting
library keeps the dependency surface unchanged and reuses an
already-tested fail-open code path; the only genuinely new idea is
keying by IP and attaching at the router level instead of the handler
level, both small, targeted deltas. Two rate-limit tiers (not one) were
chosen because the engine and data route groups have measurably
different real costs and call volumes (docs/60 §4.2) - one shared budget
would have meant either starving legitimate engine-route usage to
protect against abuse of cheap reads, or setting the limit so high on the
expensive routes that it stopped protecting the box at all. CORS and the
security headers were both small, low-risk, already-flagged gaps that
naturally belonged in the same "harden the public-facing surface" pass
as the rate limiter, rather than opening three separate phases for
closely related fixes.

Alternatives Considered

Option A: Trust `X-Forwarded-For` directly in application code (e.g. in
`get_client_ip` itself), with an allowlist check against the immediate
peer implemented by hand - rejected; this duplicates exactly what
uvicorn's `ProxyHeadersMiddleware` already does, correctly, as a
maintained library feature, for no benefit. Reimplementing trusted-proxy
header parsing in application code is the kind of thing that's easy to
get subtly wrong (e.g. trusting the wrong header on a comma-separated
chain, or checking the wrong request attribute after a header is
present) in a way that wouldn't be caught until an actual spoofing
attempt.

Option B: Add a dedicated rate-limiting library (`slowapi`, `fastapi-
limiter`) - rejected per the build spec's explicit instruction and this
project's own precedent: Redis and a working fixed-window implementation
already exist (`quota.py`), and a second, different rate-limiting
mechanism living alongside the first would be two things to reason about
where one already sufficed.

Option C: One rate-limit tier for all public routes instead of two -
considered, and would have been simpler; rejected because the "engine"
and "data" route groups' real costs and call volumes differ enough
(docs/60 §4.2 table) that a single limit would have been wrong for one
group or the other, not a compromise that worked for both.

Option D: Silently ignore `--port`-style irrelevant flags rather than
document CORS/headers as part of this same ADR, splitting them into
their own decision records - rejected; both are small enough, and
directly enough related to "harden the previously-open public surface,"
that a separate ADR each would have fragmented one coherent decision
into three for no reader benefit.

Option E (chosen): Trusted-proxy resolution via uvicorn's built-in
middleware; per-IP rate limiting via `quota.py`'s existing pattern, two
tiers; CORS scoped to real usage; baseline security headers; full CSP
explicitly deferred.

Trade-offs

Pros

Closes a real, demonstrable production vulnerability (unlimited public
engine-route requests against a resource-constrained box) and a real,
demonstrable production bug (wrong audit-trail IPs) with no new runtime
dependency. CORS and header changes are strictly more restrictive than
before with no observed frontend regression (see the build report's
manual verification).

Cons

The rate limits (20/60s engine, 100/60s data) are hand-picked starting
points sized against measured traffic, not calibrated against real
production abuse patterns - the same caveat every prior threshold
decision in this project carries (ADR-127, ADR-130's timeout). A shared
public IP (NAT, a corporate proxy, a future CDN) will share one budget
across all of its real users; this is an inherent limitation of any
per-IP scheme, not specific to this implementation, and is not addressed
here. No `Content-Security-Policy` is added - the app remains vulnerable
to whatever a CSP would have mitigated (e.g. certain injected-script
scenarios) until that dedicated work happens. Production is not actually
protected until the operator applies the two uvicorn flags this ADR
depends on (docs/60 §4.1) - the code change alone is not sufficient.

Future Review

Revisit the two rate-limit tiers' exact numbers once real production
traffic (or a real abuse attempt) provides actual data instead of the
measured-but-synthetic frontend page-load counts this decision was sized
against. Revisit trusting only `127.0.0.1` as the proxy if the Nginx/app
topology ever moves off a single host. Build the deferred
`Content-Security-Policy` as its own dedicated piece of work, not folded
into a future unrelated phase. Revisit per-IP keying generally if a CDN
or corporate-NAT false-positive rate becomes a real, observed problem.

---

# ADR-133

Title

Phase 9B: Disabled/Deleted-User Cutoff at Request Time, Failed-Login
Lockout, and the `jti` Denylist Deferral

Status

Accepted

Context

Phase 8C gave admins the ability to disable (`is_active=False`) or
soft-delete (`deleted_at` set) a `User`, and `AuthenticationService.login`
already rejected both at login. But `get_current_user`
(`app/dependencies/auth.py`) - deliberately minimal since Phase 2C,
per its own docstring and docs/37 §10 - decoded the bearer token, verified
its type, and loaded the `User` without checking either flag. An
already-issued access token kept working for its full remaining lifetime
(up to `jwt_access_expire_minutes`, 15 minutes) regardless of what an
admin did to the account afterward, leaving an admin responding to a
compromised or malicious account with no way to actually cut it off
before natural token expiry.

Separately, docs/23 §17 ("Failed Login Protection") has specified a
failed-login lockout requirement since early in the project, but only as
four bare bullet points - Temporary Lock, CAPTCHA (Future), Notify User,
Log Event - with no threshold, duration, or reset rule, and BACKLOG.md §4
had tracked it as blocked on "Redis-backed attempt tracking/backoff
logic" that this phase's build spec did not end up requiring. Meanwhile
`AuthenticationService.login`'s credential check
(`user is None or not verify_password(password, user.password_hash)`)
never calls `verify_password` when the email doesn't match any user -
since Argon2id verification is deliberately slow, this made a nonexistent
address respond measurably faster than a real one, a timing oracle for
user enumeration that matters more now that registration is closed
(ADR-119) and every account is admin-provisioned.

Decision

1. **`get_current_user` now rejects a user whose `is_active` is `False`
   or whose `deleted_at` is set**, raising the same
   `InactiveAccountException` `AuthenticationService.login` already
   raises for the identical condition. This costs nothing beyond a field
   check - the `User` row is already loaded on every authenticated
   request regardless. This is a deliberate narrowing of
   `get_current_user`'s prior "authenticate only, never authorize"
   contract; both its docstring and docs/37 §10 are corrected to say so.
2. **Failed-login lockout is schema-only, no Redis.** Two new columns on
   `users` - `failed_login_attempts` (int, default 0) and `locked_until`
   (nullable, timezone-aware) - added via `op.batch_alter_table` (the
   established pattern for altering an existing table in this project,
   BACKLOG.md §26, `f3a9c1d2e5b7`). `AuthenticationService.login` rejects
   with the lock in place (without verifying the password), increments
   the counter on each wrong-password attempt, sets `locked_until` on
   crossing the threshold, and resets both on a successful login. This
   supersedes BACKLOG.md §4's older framing of the feature as needing
   Redis-backed tracking - a DB column pair was sufficient once actually
   scoped.
3. **Threshold (`login_lockout_threshold` = 5) and duration
   (`login_lockout_duration_minutes` = 15) are new settings**, hand-picked
   starting points, not calibrated - the same caveat every prior
   threshold decision in this project carries (ADR-127's quotas,
   ADR-132's rate limits, ADR-130's timeout).
4. **The lock auto-expires; there is no admin-unlock endpoint.** The
   first login attempt observed after `locked_until` has passed resets
   both it and the counter before continuing. A fresh deployment has
   exactly one admin account, and `backend/scripts/create_admin.py`
   refuses a second run - a lock with no self-expiry would be
   unrecoverable without direct DB surgery. Auto-expiry is deliberately
   the entire recovery mechanism.
5. **A locked account is rejected via the same `InvalidCredentialsException`
   a wrong password raises**, not a distinct exception or message - an
   unauthenticated caller must not be able to tell "wrong password" apart
   from "this account is currently locked," which would otherwise confirm
   the address exists and is presently under attack.
6. **"Notify User" (docs/23 §17) is dropped, not deferred.** It requires
   email delivery, and the Phase 9 planning pass (docs/60 §2, 2026-08-06)
   already dropped the email subsystem entirely, for reasons unrelated to
   this ADR. There is no remaining path that would ever send this
   notification.
7. **"Log Event" is satisfied with three distinguishable audit actions**:
   `login_failed` (wrong password, unchanged), `login_failed_locked` (an
   attempt against an already-locked account), and `account_locked` (the
   specific attempt that crosses the threshold and sets `locked_until`).
8. **The user-enumeration timing oracle in `login()` is fixed, not
   deferred to BACKLOG.** When `user is None`, `verify_password` now runs
   against a fixed dummy Argon2id hash (`app/core/security.
   DUMMY_PASSWORD_HASH`, generated once offline, not derived from any
   real account) instead of being skipped - both paths now do equal
   Argon2id work. Chosen over recording-and-deferring because the fix is
   small, self-contained, and directly adjacent to the lockout work
   already touching this method.
9. **The `jti` access-token denylist (BACKLOG.md §4, tracked since Phase
   2A) stays deferred**, not built. Item 1 above closes the practical
   risk a denylist would have addressed - a disabled or deleted account
   is now cut off on its very next request. A denylist would add a Redis
   read to every authenticated request to close a narrower remaining
   window (e.g. a role *downgrade*, which doesn't fail the active/deleted
   check, mid-session) that is judged not worth that per-request cost
   today. BACKLOG.md §4's entry is updated to reflect this reduced
   framing rather than the original one.
10. **`_as_aware_utc` (the SQLite-naive-vs-aware-datetime normalization
    helper, BACKLOG.md §9) is promoted from a per-module copy to one
    shared function, `app/utils/time.py::as_aware_utc`.** It had already
    been independently copy-pasted into five modules
    (`authentication_service`, `news_sentiment.dedup_detector`,
    `analysis_confidence.freshness_analyzer`, `economic_calendar.
    risk_window`, `signal.status_resolver`) before this phase - more than
    the build spec assumed going in (it named two). Adding a sixth
    (`locked_until` vs. `datetime.now(UTC)`) was the point past which
    continuing to copy it was no longer defensible; all six call sites
    now import the one function.

Reason

Item 1 is the higher-value fix of the two build items and is not what
docs/23 §17 or BACKLOG.md §4 lead with - lockout only slows down
*guessing* a password, while the disabled/deleted check closes a window
where a *known-correct* credential (or a still-live token from before an
account was compromised or fired) keeps working regardless of admin
action. Both are real gaps Phase 8C's admin-lifecycle work exposed once
it existed; neither was addressable before that phase, since there was no
account lifecycle to invalidate against.

Schema-only lockout (no Redis) was chosen over BACKLOG.md §4's original
framing because nothing about "count consecutive failures, expire after a
duration" requires a separate fast-expiring store - two columns already
co-located with the row being protected, one already-open DB transaction
per login attempt, is simpler than adding a Redis round-trip to the one
path (`login`) that cannot already assume Redis is reachable without
changing its failure semantics (unlike ADR-127/ADR-132's rate limiters,
which fail open on a Redis outage by design - a lockout fail-open would
defeat the feature).

Auto-expiry instead of an admin-unlock endpoint is forced by this
project's own bootstrap constraint, not a general security preference:
`create_admin.py` intentionally refuses to create a second super-admin,
so there is exactly one account capable of unlocking anyone on a fresh
deployment - if lockout ever caught it, only direct DB access could
recover, which is worse than a self-expiring lock ever being slightly
too permissive.

The `jti` deferral is a threat-model judgment call, not a capability
gap: building the denylist was and remains straightforward, but every
authenticated request would pay a Redis read to protect against a
narrower window than existed before Item 1, for a threat (mid-session
privilege change) this project has no evidence is more likely than the
already-closed one.

Alternatives Considered

Option A (lockout storage): Redis-backed attempt tracking, per BACKLOG.
md §4's original framing - rejected; adds a hard Redis dependency to the
one auth path that previously had none, in exchange for no behavior this
phase actually needed that two columns don't already provide.

Option B (§3.4 fix): record the timing-oracle weakness in BACKLOG.md
instead of fixing it now - rejected in favor of fixing it, since the fix
is a few lines directly inside the method already being changed for
lockout, and leaving a known, named, easily-fixed enumeration vector
recorded-but-open serves no one.

Option C (`jti`): build the Redis denylist now, closing the narrower
role-downgrade window Item 9 describes - rejected; that window is real
but wasn't the risk that motivated 9B (the disabled/deleted-account gap,
now closed by Item 1), and paying a Redis read on every authenticated
request is a cost this phase's scope does not justify taking on
speculatively.

Option D (`_as_aware_utc`): leave the fifth-then-sixth copy as-is,
matching the existing (if unintentional) pattern - rejected once a sixth
call site made "not worth consolidating" no longer true; five independent
copies of an identical, non-trivial-to-rederive gotcha is exactly the
kind of institutional-knowledge drift BACKLOG.md §9 exists to prevent
rediscovering.

Trade-offs

Pros

Closes a real, demonstrable gap (a disabled/deleted account's live token
outliving admin action) with no added latency. Lockout stops online
password-guessing against admin-provisioned accounts without any new
runtime dependency. The enumeration timing oracle is closed rather than
merely documented. One `as_aware_utc` implementation instead of six
removes a live risk of the next copy silently drifting from the
original's behavior.

Cons

The lockout threshold/duration (5 attempts / 15 minutes) are, like every
prior threshold in this project, hand-picked rather than calibrated. Lock
auto-expiry means a determined attacker with unlimited time still gets
another five guesses every fifteen minutes indefinitely - this is the
accepted cost of not building an admin-unlock endpoint (see Reason). The
`jti` deferral leaves the role-downgrade-mid-session window open, by
deliberate choice, until a Redis read on every request is judged worth
it. `DUMMY_PASSWORD_HASH` is a module-level constant, not currently
rotated - not a weakness in itself (it is never meant to be guessed, only
to cost the same as a real hash to verify against), but worth naming as a
new small piece of fixed state.

Future Review

Revisit the lockout threshold/duration once real login-failure patterns
exist to calibrate against, same as every other hand-picked number in
this project. Revisit the `jti` deferral if role changes for
currently-logged-in users become a real, observed problem, or if Redis
becomes an unconditional dependency for some other reason that removes
the "adds a new hard dependency to `login`" objection. Build the
Content-Security-Policy and other deferred 9A items per ADR-132's own
Future Review, independently of this ADR.

---

# ADR-134

Title

Phase 9C: Dedicated E2E Database and Seed Script, Rather Than `dev.db`

Status

Accepted

Context

Building a real Playwright E2E suite requires the tests to log in as a
known account. Two paths that would normally provide one are both
closed: public registration returns `403` (`allow_public_registration=
False`, ADR-119), and `backend/scripts/create_admin.py` refuses to run a
second time once any `super_admin` row exists (ADR-123's bootstrap
guard) - `dev.db` already has one from earlier phases. `dev.db` itself
has also been mutated repeatedly by manual verification across this
session (the dev super-admin's password was overwritten during 7D-C; a
throwaway `lockout-9b-verify@example.com` account was added in 9B) - an
E2E suite built against it would be non-deterministic and
order-dependent, asserting against whatever state happened to survive
the last person's manual testing.

Decision

1. **A dedicated SQLite file, `backend/e2e.db`, never `dev.db`.** A new
   shared constant module, `backend/scripts/e2e_db.py`
   (`E2E_DATABASE_URL`), is imported by both `run_dev.py --e2e-db`
   (points a manually-started backend's `DATABASE_URL` at it) and
   `seed_e2e_data.py` (seeds it) - one definition, the same pattern
   `local_env.py` already established for the mock-provider overrides.
2. **`seed_e2e_data.py` resets to a known state by dropping and
   recreating every table on each run**, not by upserting - idempotency
   here means "always ends up identical," not "safe to run twice
   without erroring." This is deliberately more aggressive than
   `seed_dev_data.py` (which only adds what's missing, since `dev.db` is
   meant to *accumulate* manual-verification state across phases) - the
   two scripts now have genuinely different idempotency contracts for a
   genuinely different reason, not an accidental inconsistency.
3. **A safety refusal, `e2e_db.assert_safe_e2e_target`, gates the whole
   script**: it must reject anything that isn't `sqlite:///` (Postgres,
   including production, is rejected by dialect alone) and additionally
   requires the resolved filename to be exactly `e2e.db` - so a
   misconfigured `DATABASE_URL` pointing at `dev.db`, or anything else,
   is refused too, not just non-SQLite targets. Tested directly
   (`tests/test_seed_e2e_data_safety.py`), not just exercised
   incidentally by running the script.
4. **Test credentials are `*.invalid` (RFC 2606) and a fixed, obviously
   fake password**, never derived from or read out of `backend/.env`.
   One seeded `super_admin` and one seeded `registered` account cover
   every flow the build spec's six flows need (§4.3's Admin-tier UI,
   §4.5's role gating) without needing a third role tier.
5. **Schema via `Base.metadata.create_all`, not `alembic upgrade
   head`**, mirroring the existing pytest-session pattern
   (`tests/conftest.py`'s ephemeral SQLite fixtures) rather than
   introducing a second schema-provisioning path. `e2e.db` is a
   throwaway file recreated every seed run, not a database whose
   migration history needs to mean anything.

Reason

The safety refusal is not decorative: a seed script that creates a
known-password admin account is a genuine hazard if it can ever run
against a real database, and the build spec called this out explicitly.
Rejecting by dialect alone (any Postgres URL) would already catch the
most likely real accident (a stray `DATABASE_URL` env var from a real
`.env`), but the additional filename check catches the second most
likely one - a misconfigured pointer at `dev.db` itself, which is also
SQLite and would otherwise pass a dialect-only check. Two independent
checks for two independent, plausible misconfigurations.

Drop-and-recreate instead of upsert was chosen because the E2E suite's
own tests mutate state (watchlist create/rename/delete, admin dialogs)
and the whole point of a dedicated database is that a test run's outcome
must not depend on what a previous run - or a differently-ordered one -
left behind. An upsert-based seed would still need to reconcile
leftover watchlists/assets from prior runs; dropping everything sidesteps
that reconciliation entirely rather than building it.

Alternatives Considered

Option A: Seed `dev.db` directly with known test accounts alongside the
real manual-verification data - rejected; this is exactly the
non-determinism the build spec identified. A test asserting "the user
list shows N accounts" would break every time a future phase's manual
verification adds or removes one.

Option B: A fixture-per-test approach (create a user via direct DB
access at the start of each spec file, delete it at the end) instead of
one upfront seed script - rejected for this first pass; it would
multiply the number of places that need the same safety-refusal logic,
and the six flows in scope share enough fixture data (the same admin,
the same non-admin, the same assets) that one seed script is simpler
than six ad-hoc ones. Revisit if the suite grows enough those flows
diverge.

Option C: Reuse `create_admin.py`'s interactive prompt flow against
`e2e.db` instead of a new non-interactive script - rejected; E2E runs
need to be scriptable/idempotent, and `create_admin.py`'s `getpass`
prompts and one-shot bootstrap guard are both wrong shapes for that.

Trade-offs

Pros

The suite is fully deterministic - any developer, any order, any number
of runs, same starting state. The safety refusal makes the "seed script
points at production" failure mode structurally hard to hit rather than
relying on developer discipline. Sharing `e2e_db.py` between `run_dev.py`
and `seed_e2e_data.py` means the database target can't drift between the
two the way it could if each hardcoded its own URL string.

Cons

A second local SQLite file to know about, alongside `dev.db` - a
developer running the E2E suite for the first time needs to read
README.md's setup steps rather than it being self-evident. `Base.
metadata.create_all` (not `alembic upgrade head`) means `e2e.db`'s
schema could in principle drift from what a real migration chain would
produce if a future migration does something `create_all` can't express
(a data migration, a non-model-derivable constraint) - low risk given
this project's migrations have so far been straightforward column
adds, but worth naming. Drop-and-recreate means the seed script must run
before every E2E session, not just once ever - a minor extra step the
alternative (upsert) would have avoided.

Future Review

Revisit Option B (per-spec-file fixtures) if the E2E suite grows enough
that the six flows' shared fixture data stops being a good fit for one
upfront seed. Revisit `create_all` vs. `alembic upgrade head` if a
future migration ever does something the former can't reproduce
faithfully. Move E2E into CI once the infrastructure work docs/60 §7.3
defers is taken on as its own phase - the database/seeding strategy
here does not need to change for that, `e2e_db.py` and
`seed_e2e_data.py` were both written to run identically in an automated
runner.

---

# ADR-135

Title

Phase 9C-B: E2E Is a Required, Blocking CI Check, Not Advisory

Status

Accepted

Context

Phase 9C built the Playwright suite (ADR-134) but deliberately left it
local-only (docs/60 §7.3) - wiring it into CI was called out explicitly
as the next step. Phase 9C-B does that wiring (`.github/workflows/
ci.yml`'s new `e2e` job). The open question the build spec posed was
whether that job should be allowed to fail a run (a required check, like
`backend`/`frontend` already are) or be advisory (`continue-on-error`,
visible but non-blocking).

Decision

The `e2e` job is a normal job in the same workflow, with no
`continue-on-error`. A failing E2E run fails the check the same way a
failing `backend` or `frontend` job does.

Reason

The suite passed twice locally with zero waits before this phase (docs/
60 §7.1) and a third time here against the CI-equivalent production
build (§7 of this phase's build report) - there is no accumulated
evidence of flakiness to justify treating it as advisory from day one.
An advisory check that nobody is required to look at tends to be
ignored exactly when it matters most (a real regression), which defeats
the purpose of building it. If flakiness is observed in practice on
GitHub's actual runners - genuinely different environment from every
local run so far - the corrective action is fixing the suite (removing
whatever nondeterminism was introduced), not quietly downgrading the
check to advisory. Recorded here so a future maintainer under deadline
pressure doesn't make that downgrade without knowing it reverses a
deliberate decision.

Trade-offs

Pros

A blocking check is the only kind that reliably gets attention - an
advisory one rots the same way local-only E2E was already rotting
(docs/60 §7.3's stated reason for prioritizing this phase). Consistent
with how `backend`/`frontend` already behave, no special-casing to
remember.

Cons

The suite has never run on GitHub's actual runners (Ubuntu, real
network/filesystem timing, cold Chromium install) - if Ubuntu-specific
flakiness exists that none of the Windows-local runs surfaced, the first
few real CI runs could block unrelated merges until it's found and
fixed. Judged an acceptable, temporary cost against the alternative of
building a check nobody has to heed.

Future Review

If the first real CI runs show flakiness that isn't a straightforward
test bug (e.g. genuine timing sensitivity tied to GitHub's runner
environment specifically), revisit - but the default corrective action
remains fixing the suite, not flipping this to advisory.

---

# ADR-136

Title

Phase 9D: `GET /metrics` - Route-Template Cardinality, Fail-Closed
Access Control, Worker Metrics Excluded

Status

Accepted

Context

`docs/04` said, in full, "GET /metrics — Internal monitoring." `docs/06`
§25 listed four bare bullets (Metrics Endpoint, Prometheus Ready,
Structured Logs, Error Tracking, Background Task Monitoring). There was
no contract anywhere - everything concrete in this phase is inferred.
`GET /admin/system` (ADR-116) was explicitly limited to liveness plus
today's counts because "genuine telemetry is gated on the pre-existing
`GET /metrics` gap" - this phase removes that gate. There is no
Prometheus or Grafana deployed, so the near-term consumer is not a
scraper: it is `GET /admin/system` and manual `curl` inspection of a
live box.

Decision

1. **`prometheus_client`**, the standard library for this, not a
   hand-rolled exporter or a FastAPI-specific wrapper - well-maintained,
   does the OpenMetrics text-format encoding correctly, and ships
   default process/GC collectors for free.
2. **Labels are the matched route *template*, never the raw request
   path.** `MetricsMiddleware` (`app/middleware/metrics.py`) reads
   `request.scope["route"].path`, set by Starlette once routing
   resolves. Raw-path labeling would create one time series per symbol
   per timeframe per status - unbounded, held in memory forever, a real
   availability risk on the 911MB production box already ~330MB into
   swap (BACKLOG.md §10), not a theoretical tidiness concern. Verified
   directly (not just argued): two requests to the same route template
   with different path params produce exactly one series with the
   count summed (Phase 9D build report §8 has the pasted proof). Paths
   matching no route at all collapse into a single `"unmatched"`
   bucket, same reasoning.
3. **Fail-closed 404, not `require_admin`.** `settings.
   metrics_auth_token` defaults to `""`; an unconfigured deployment
   gets 404 (not 403, not an empty 200), so the endpoint does not
   advertise its own existence. A static bearer token rather than a
   session/role check because scrapers cannot hold a user session, and
   because this must keep responding when the database is unhealthy -
   exactly when metrics matter most, and exactly when `require_admin`
   (which needs a DB round-trip via `get_current_user`) would be least
   reliable. The real production access boundary is Nginx denying
   external access to `/metrics`; the token is defence in depth, not a
   substitute for it.
4. **Excluded from 9A's per-IP rate limiting and from its own request
   metrics.** Not attached to `_engine_rate_limit`/`_data_rate_limit`
   in `app/api/v1/router.py`, the same mechanism that already excludes
   `/health*` - a scraper polling every 15s must never be throttled.
   `MetricsMiddleware` explicitly skips instrumenting `/metrics`
   itself, so a scrape never inflates the numbers it reports.
5. **Celery worker/beat metrics are explicitly out of scope**, not
   deferred silently. Those are separate processes; exporting their
   metrics needs a multi-process registry or a pushgateway, which is
   its own design pass - and the worker cannot run on this Windows
   sandbox at all (BACKLOG.md §9), so it could not have been verified
   here regardless. `docs/06` §25's "Background Task Monitoring" stays
   open.
6. **CPU/memory/queue-length gauges are not hand-rolled.** Process-level
   resource metrics already come from `prometheus_client`'s default
   collectors (decision 1); queue length needs Celery introspection,
   tied to decision 5's exclusion.

Reason

A monitoring endpoint that becomes the outage cause is a strictly worse
outcome than no endpoint at all - the cardinality decision is the one
that actually matters here, everything else is comparatively
low-stakes. Fail-closed-by-default was chosen over fail-open (e.g.
defaulting to some placeholder token, or serving without auth if none
is configured) because `/metrics` leaks operational internals (route
names, error rates, traffic volumes, latency) that must not be
world-readable on a public site by accident - an operator has to
deliberately opt in, not deliberately opt out.

Trade-offs

Pros

Route-template labeling gives useful, bounded-cardinality dimensions
(is `/analysis/technical/{symbol}` slow in aggregate?) without the
unbounded blow-up per-symbol labeling would cause. The fail-closed
default means this phase cannot itself introduce a new public
information-disclosure surface on the live box, even if the operator
never gets around to configuring a token. Reusing `prometheus_client`'s
default collectors instead of hand-rolling `psutil` sampling avoids a
second, likely-worse implementation of something already solved.

Cons

Per-symbol/per-timeframe breakdowns are not observable in these
metrics (only per-route-template aggregates are) - if that granularity
is ever needed, it requires either a bounded low-cardinality label
(e.g. market type, not raw symbol) or a different mechanism entirely,
not simply un-collapsing this one. A static token is weaker than a
per-caller-scoped credential (any holder of the token can scrape
everything) - judged acceptable for a single internal scraper/operator
use case, revisit if that assumption changes. Worker/queue metrics
remaining unbuilt means Celery-side behavior (task backlog, retry
rates) is still only visible via logs, not metrics.

Future Review

Revisit worker/queue metrics once a real need for them is observed (not
preemptively) and once there's an environment where the worker can
actually run to verify them (BACKLOG.md §9's Windows/`billiard`
limitation, or production). Revisit surfacing these metrics in `GET
/admin/system`/the Admin UI as its own follow-up (BACKLOG.md §3) -
deliberately not bundled into this phase. Revisit the static-token
model if a second consumer with different trust requirements ever needs
scrape access.

---

# Review Policy

Review ADRs:

- Before major releases
- When introducing new infrastructure
- When replacing providers
- When changing AI models
- During annual architecture reviews