# Changelog

## Unreleased

### Added - Phase 4B: Smart Money Concepts (SMC) Engine

`docs/43_SMC_ARCHITECTURE.md` - new architecture document defining the persistence model, analyzer dependency graph, lifecycle states, and all algorithms (market structure, BOS, CHOCH, order blocks, FVG, liquidity, premium/discount, multi-timeframe)

`app/services/market_structure/swing_points.py` - swing-high/low fractal detection extracted from Technical Analysis's private `_find_swing_points`, now shared by both engines rather than duplicated

`app/services/smc/` - twelve deterministic analyzers (`MarketStructureAnalyzer`, `BOSAnalyzer`, `CHOCHAnalyzer`, `OrderBlockAnalyzer`, `MitigationAnalyzer`, `BreakerBlockAnalyzer`, `FairValueGapAnalyzer`, `LiquidityAnalyzer`, `PremiumDiscountAnalyzer`, `ConfluenceAnalyzer`, `SMCConflictAnalyzer`, `MultiTimeframeAnalyzer`) plus `SMCScoringEngine`, each a pure function over plain dataclasses - no database access, no AI, no probabilistic reasoning (ADR-031, ADR-036)

`SMCEngine` (`app/services/smc_engine.py`) - unlike the stateless Technical Analysis Engine, persists detected structures to `smc_events` (ADR-032): bounded to the most recent 500 candles per call, de-duplicated against existing rows by natural key, with a lifecycle-archiving pass and an `SMCProcessingState` checkpoint per asset/timeframe

New models: `SMCEvent` (mutable zone-lifecycle rows - a first for this project, contrasting every other append-only table, ADR-033) and `SMCProcessingState` (recovery/migration bookkeeping: last processed timestamp, engine version)

**ADR-032** through **ADR-037**: SMC persistence and incremental-scan design; mutable `smc_events` rows; Order Block candle-pattern definition; equal-highs/lows magnitude-aware tolerance; SMC multi-timeframe weights and `smc_score` distinct from `technical_score`; SMC Event Lifecycle (ACTIVE/MITIGATED/INVALIDATED/ARCHIVED states and transitions, never deleting historical events)

New public (no auth) endpoints: `GET /analysis/smc/{symbol}?timeframe=` and `GET /analysis/smc/{symbol}/multi-timeframe`

docs/09 and docs/04 updated: docs/09 §17's inconsistent flat boolean example (`"bos": true`) corrected to the list-based Evidence Model actually implemented, and the four concepts referenced during planning but absent from docs/09 (IFVG, Internal/External BOS, Displacement, Market Imbalance) are noted as deliberately excluded; docs/04 documents both new endpoints' concrete contracts

Deliberately excluded (undocumented in docs/09, "never invent architecture"): Inverse Fair Value Gaps (IFVG), an Internal/External BOS distinction, a dedicated Displacement analyzer, Market Imbalance

Tests: `test_swing_points.py`, `test_market_structure_analyzer.py`, `test_bos_analyzer.py`, `test_choch_analyzer.py`, `test_order_block_analyzer.py`, `test_mitigation_analyzer.py`, `test_breaker_block_analyzer.py`, `test_fair_value_gap_analyzer.py`, `test_liquidity_analyzer.py`, `test_premium_discount_analyzer.py`, `test_smc_confluence_analyzer.py`, `test_smc_conflict_analyzer.py`, `test_smc_scoring_engine.py`, `test_smc_multi_timeframe_analyzer.py`, `test_smc_models.py`, `test_smc_engine.py` (integration), `test_smc_api.py` (59 new tests total)

Deliberately out of scope: any BUY/SELL/WAIT recommendation, true delta-only incremental scanning (documented as a future optimization), API filtering query params (`event_type`, `include_mitigated`), News/Economic analysis (Phase 5), AI Orchestrator integration (Phase 6)

### Status

Phase 4B (Smart Money Concepts Engine) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 4A: Technical Analysis Engine

`docs/42_TECHNICAL_ANALYSIS_ARCHITECTURE.md` - new architecture document defining the data flow, analyzer responsibilities, missing-indicator policy, support/resistance algorithm, scoring formula, and multi-timeframe combination algorithm

`app/services/technical_analysis/` - nine deterministic, stateless analyzers (`MovingAverageAnalyzer`, `TrendAnalyzer`, `MomentumAnalyzer`, `OscillatorAnalyzer`, `VolatilityAnalyzer`, `VolumeAnalyzer`, `SupportResistanceAnalyzer`, `MultiTimeframeAnalyzer`, `ConflictAnalyzer`) plus `TechnicalScoringEngine`, each a pure function over plain dataclasses - no database access, no AI, no probabilistic reasoning (ADR-031)

`TechnicalAnalysisEngine` (`app/services/technical_analysis_engine.py`) - the top-level, fully stateless orchestrator (ADR-027): fetches candles via the existing `PriceCandleRepository`, computes every indicator fresh via the Phase 3A `app/indicators` registry (not persisted `indicator_results`, avoiding staleness), runs every analyzer, and assembles one `TechnicalAnalysisResult`

Definitive 100-point technical scoring formula (ADR-028), superseding docs/08 §9's illustrative example, which only summed to 75 despite the same section stating a maximum of 100 - a genuine internal inconsistency in docs/08, not just an incomplete example. Score reported as a full `ScoreBreakdown` (trend/momentum/oscillator/volume/volatility/support_resistance/penalties/total), not just the single total - Phase 4A refinement for explainability

Support/Resistance evidence extended with `source` and `strength` metadata per level (Phase 4A refinement), not just a bare price; round numbers/psychological levels use a magnitude-aware rounding heuristic (ADR-029) rather than a hardcoded per-symbol table

Multi-timeframe combination algorithm (ADR-030): D1/H4/H1/M15 weighted 40/30/20/10, a ±0.5 net-ratio threshold determines `bullish_alignment`/`bearish_alignment`/`mixed` - a missing timeframe is skipped, not treated as neutral

**ADR-031**: "Technical Analysis Produces Evidence, Not Trading Signals" - makes explicit (beyond ADR-005/006) that this engine never produces a BUY/SELL/WAIT recommendation or entry/stop-loss/take-profit level; that remains the future Signal Engine's job (docs/30 Phase 6)

New public (no auth) endpoints: `GET /analysis/technical/{symbol}?timeframe=` and `GET /analysis/technical/{symbol}/multi-timeframe`, matching the Phase 3C precedent for non-personalized market reference data

docs/04 and docs/08 updated: docs/04 documents the two new endpoints' concrete contracts (previously marked "not yet implemented"); docs/08 §9/§10/§11 annotated to point at docs/42/ADR-028 as the canonical scoring source, rather than leaving the internally-inconsistent example uncorrected

Phase-numbering note: tracked as sub-phase **4A** in docs/30 (SMC Engine = 4B, Market Regime Engine = 4C, Confidence Engine = 4D), per docs/30's existing Phase 4 grouping (which includes SMC, unlike an earlier informal framing that treated SMC as a separate later phase)

A real bug was caught during test-writing, not just implementation: an initial `zip(emas, emas[1:], strict=True)` in `MovingAverageAnalyzer` was wrong - the two sequences are intentionally different lengths to produce sliding pairs, and `strict=True` made that fail immediately once real test data was run

Tests: `test_technical_analysis_analyzers.py`, `test_support_resistance_analyzer.py`, `test_scoring_engine.py`, `test_multi_timeframe_analyzer.py`, `test_technical_analysis_engine.py` (integration), `test_technical_analysis_api.py` (53 new tests total)

Deliberately out of scope: any BUY/SELL/WAIT recommendation, Smart Money Concepts (Phase 4B), News/Economic analysis (Phase 5), AI Orchestrator integration (Phase 6), persisted technical-analysis history

### Status

Phase 4A (Technical Analysis Engine) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3C: Market Data API

`GET /assets`, `GET /assets/{symbol}`, `GET /market/{symbol}/latest`, `GET /market/{symbol}/candles`, `GET /market/{symbol}/indicators` - all public, no authentication required (per explicit decision: market reference data isn't user-specific, matching docs/04's Guest rate-limit tier and docs/23 §12's "View Public Pages")

Thin API layer only - every route calls existing repositories (`AssetRepository`, `PriceCandleRepository`, `IndicatorResultRepository`) directly, with new repository methods (`AssetRepository.list_filtered`/`count_filtered`, `PriceCandleRepository.list_range`'s new optional `limit`) added to support filtering/pagination without introducing service-layer logic that wasn't needed for read-only endpoints

`GET /market/{symbol}/indicators` is new - not previously in docs/04 - exposing the raw `indicator_results` values (docs/39) Phase 3A/3B already populate; deliberately distinct from the future `GET /analysis/technical/{symbol}` (Phase 4's synthesized trend/scoring output, still unbuilt). The `indicator` query filter is validated against the indicator registry (`app.indicators.registry`), not an unrestricted string - an unknown indicator name is rejected with a clear error rather than silently returning nothing

`GET /market/{symbol}` renamed to `GET /market/{symbol}/latest` before implementation, to make its single-candle-snapshot purpose explicit and avoid future ambiguity with the candles/indicators endpoints

Symbol path parameters are case-insensitive (`eurusd` and `EURUSD` resolve identically) - shared `get_asset_or_404` dependency normalizes and 404s consistently across every symbol-keyed route

`RequestValidationError` handler added (`app/exceptions/handlers.py`), normalizing FastAPI's built-in `{"detail": [...]}` validation-error shape to the project's standard `{"error", "message"}` envelope - a gap that existed since Phase 2C but was only surfaced now that a phase has meaningfully-validated query parameters (`timeframe`, indicator names) users will routinely get wrong

Spread is intentionally omitted from `GET /market/{symbol}/latest`'s response, not fabricated - it isn't part of the data model (docs/03 §5, no integrated provider supplies it); documented as unavailable in docs/04 rather than invented

docs/04_API_SPECIFICATION.md updated: the five endpoints above with concrete request/response shapes, and `GET /analysis/technical/{symbol}` explicitly marked "not yet implemented" with a note distinguishing it from the new indicators endpoint

A genuinely flaky pre-existing test was found and fixed while running the full suite repeatedly during this phase: `test_decode_token_rejects_tampered_signature` tampered only the *last* character of a JWT signature, which - depending on the signature's byte length - can encode only padding/insignificant bits, occasionally letting the "tampered" token verify successfully anyway (reproduced failing 1-in-3 runs in isolation). Fixed to tamper the *first* character of the signature segment instead, which is always significant

Tests: `test_market_data_api.py` (14 tests) covering pagination, filtering, 404s, symbol-case-normalization, timeframe/indicator validation error envelopes, and candle range/limit behavior

### Status

Phase 3C (Market Data API) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3B: Twelve Data Provider

`docs/41_SYMBOL_NORMALIZATION.md` - new document defining the project's canonical internal symbol representation (plain, uppercase, separator-free `Asset.symbol`) first, then the Twelve Data-specific mapping: a mechanical FOREX/METAL/CRYPTO rule (guarded by a known-currency-code allowlist, not a bare length check), an explicit INDEX override table (left empty - no entries could be confirmed against Twelve Data's own symbol catalog from public documentation alone), and the confirmed timeframe-to-`interval` table

`TwelveDataProvider` (`app/services/market_data/providers/twelve_data.py`) - the first real `MarketDataProvider` implementation, covering FOREX/METAL/CRYPTO (INDEX deliberately excluded from `capabilities()` until docs/41's override table has verified entries); classifies Twelve Data's error responses into `TwelveDataAuthenticationError`/`TwelveDataQuotaExceededError`/`TwelveDataInvalidSymbolError`, each subclassing the shared `PermanentProviderError`/`TransientProviderError` categories

`TwelveDataHttpClient` (`app/services/market_data/providers/twelve_data_http.py`) - isolates raw `httpx` transport concerns (base URL, auth header, timeout, network-level error handling) from `TwelveDataProvider`'s response-classification logic; accepts an injectable `transport` so tests never make real network calls. Recorded as **ADR-026** ("Isolate Raw HTTP Transport Behind a Dedicated Client Per Provider") - the pattern any future HTTP-calling provider should follow

`DailyQuotaExceededError` added to the provider exception hierarchy; `RateLimitedProvider` gained an optional `requests_per_day` parameter (ADR-025) - Twelve Data's free tier is capped at both 8 requests/minute *and* 800/day, and the existing per-minute token bucket alone couldn't prevent exceeding the daily cap. Raises (rather than sleeping for hours) once the UTC-calendar-day budget is exhausted, carrying `used`/`limit`/`reset_at` for observability

`ProviderCapabilities.supported_market_types` is now a required field, not an optional field defaulting to `None`-meaning-"supports everything" - every provider must declare its market types explicitly (`MockMarketDataProvider` updated accordingly)

New settings: `market_data_rate_limits_per_day`, `market_data_default_rate_limit_per_day`, `twelve_data_api_key`, `twelve_data_base_url`, `twelve_data_timeout_seconds`; `TWELVE_DATA_API_KEY=` added to `.env.example`. `twelve_data` is registered in the provider factory but **not** in the default `market_data_providers` list - it only activates when explicitly configured with a real API key

`httpx` promoted from a dev-only to a declared runtime dependency (`pyproject.toml`) - it was already installed transitively via FastAPI's test client, but a real HTTP client is now needed in production code, not just tests

Provider contract-test convention exercised again: `test_twelve_data_provider.py::test_twelve_data_provider_satisfies_provider_contract` runs the same `assert_provider_contract` helper (Phase 3.5) against a mocked-transport `TwelveDataProvider`, alongside dedicated error-classification and symbol-mapping tests - no real Twelve Data API calls are made anywhere in the test suite (docs/40 §10)

A real bug was caught during test-writing, not just implementation: a naive "split any 6-character symbol in half" mechanical rule would have mis-translated `NAS100` into `NAS/100` - fixed with a known-currency-code allowlist before it ever reached production code; documented in docs/40 §3 and docs/41 §3 so it isn't rediscovered

Deliberately still out of scope: enabling `twelve_data` by default, INDEX market-type support (blocked on verifying docs/41's override table against Twelve Data's real symbol catalog), a second real fallback provider, and any Phase 4 work

### Status

Phase 3B (Twelve Data Provider) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3.5: Market Data Integration & Quality Gate

`docs/40_PROVIDER_INTEGRATION_GUIDE.md` - new canonical checklist for integrating any market-data provider: interface requirements, symbol/timeframe mapping, error classification, capability declaration, rate-limit configuration, secrets convention, health-check integration, and testing requirements

`RateLimitedProvider` (`app/services/market_data/providers/rate_limited.py`) - a token-bucket decorator wrapping any `MarketDataProvider`, so rate limiting is applied uniformly without embedding provider-specific throttling logic in `MarketDataService`; configured per-provider via `settings.market_data_rate_limits_per_minute` (falling back to `settings.market_data_default_rate_limit_per_minute`), applied automatically by `get_market_data_providers()`

`ProviderCapabilities` (`app/services/market_data/providers/base.py`) - a structured, extensible value object (`supported_timeframes`, `supported_market_types`, `max_lookback`) replacing a single boolean `supports()` method, so new capability dimensions can be added without breaking existing providers; `MarketDataService` now checks capabilities proactively before calling a provider, rather than discovering an unsupported timeframe reactively

`ProviderConfigurationError` added to the provider exception hierarchy (`app/services/market_data/exceptions.py`) for setup-time misconfiguration (e.g. an unknown provider name), replacing a raw `ValueError`; the hierarchy's extension point for future provider-specific exceptions (e.g. `TwelveDataAuthenticationError`) is now documented

`CandleValidator` gained a timestamp-plausibility rule - a candle whose timestamp falls outside the requested `[start, end]` window (with a small clock-skew tolerance) is now rejected, closing docs/34's "Timestamp" validation requirement

`MarketDataService` now logs provider-call latency (`market_data.provider_call`, with `duration_ms` and `outcome`) for every attempt, success or failure - closing part of ADR-019's "Observability by Default" requirement for this pipeline

`GET /health/ready` now reports each configured provider's `health_check()` result diagnostically (`market_data_providers` in the response body) - a provider being unreachable does not flip overall readiness

CI (`.github/workflows/ci.yml`) now runs a real PostgreSQL 17 service container and executes `alembic upgrade head`/`alembic check` against it before the test suite - closing the long-standing "CI doesn't test the migration path" gap (BACKLOG.md §5/§9)

Provider contract-test convention: `tests/market_data_contract.py::assert_provider_contract`, demonstrated against `MockMarketDataProvider` in `test_mock_provider.py` - every future provider's test suite should call the same helper

Tests: `test_rate_limited_provider.py`, `test_market_data_dependencies.py`, plus additions to `test_market_data_service.py` (capability-based skipping) and `test_candle_validator.py` (timestamp-plausibility rules)

Deliberately still no real market-data provider integrated (Phase 3B); no persisted symbol-mapping table; no metrics/Prometheus endpoint (still tracked separately in BACKLOG.md)

### Status

Phase 3.5 (Market Data Integration & Quality Gate) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 3A: Market Data Foundation

`docs/38_MARKET_DATA_ARCHITECTURE.md` - new architecture document defining the provider abstraction, symbol/timeframe normalization, data validation, duplicate detection, retry/failover, scheduler design, and provider lifecycle for the market-data pipeline

`docs/39_INDICATOR_REFERENCE.md` - new canonical reference for every implemented indicator: mathematical definition, inputs, parameters, output fields, warm-up requirements, numerical precision, and external source, for all 18 registered indicators

`app/models/enums/` restructured from a single `enums.py` into a package (`user_role.py`, `timeframe.py`, `market_type.py`), scaling better as domain enums grow; all existing imports (`from app.models.enums import UserRole`) are unaffected

New models: `Asset` (`TimestampMixin`), `PriceCandle` (`CreatedAtMixin`, unique on `(asset_id, timeframe, timestamp)` - see ADR-024), `IndicatorResult` (own `calculated_at` column) - per docs/03 §5-6

New repositories: `AssetRepository`, `PriceCandleRepository` (`upsert`, `get_latest`, `list_range`, `list_recent`), `IndicatorResultRepository` - data access only

Alembic migration for `assets`/`price_candles`/`indicator_results`, verified via upgrade/downgrade/upgrade round-trip and `alembic check`; the recurring `server_default` SQLite-vs-Postgres gotcha (BACKLOG.md §9) was caught and corrected again before committing

`MarketDataProvider` interface (`app/services/market_data/providers/base.py`) and `MockMarketDataProvider` - a deterministic, seeded synthetic OHLCV generator; no external API integration this phase (Phase 3B adds the first real provider, Twelve Data)

`CandleValidator` - a dedicated component owning candle validation rules (docs/08 §12), kept separate from `MarketDataService`, which only orchestrates the fetch → normalize → validate → persist workflow

`MarketDataService` - retry-with-backoff and provider failover (falling back to already-stored data when every provider fails), idempotent persistence via `PriceCandleRepository.upsert`

Scheduler: a single conceptual Celery task (`market_data.collect_for_timeframe`) parameterized by `Timeframe`, with one Celery Beat schedule entry per timeframe (`app/workers/market_data_tasks.py`) - not a separate task per timeframe

`app/indicators/` package (per docs/06 §3's reserved top-level folder), organized into `trend.py`, `momentum.py`, `volatility.py`, `volume.py`, `trend_strength.py`, with a discovery registry (`app/indicators/registry.py`) - implements the full docs/08 §5 indicator list: EMA (20/50/100/200), SMA (200), RSI (14), MACD (12/26/9), Stochastic RSI (14), CCI (20), Momentum (10), ATR (14), Bollinger Bands (20/2), Standard Deviation (20), VWAP, OBV, Volume SMA (20), Relative Volume (20), ADX/DI+/DI- (14)

`IndicatorService` - populates `indicator_results` with raw indicator values only; deliberately no trend detection, technical scoring, or conflict detection (docs/08 §7-11 remains Phase 4's Technical Analysis Engine)

`ADR-024` - unique constraint + upsert semantics on `PriceCandle`

Tests: `test_indicators.py`, `test_market_data_models.py`, `test_candle_validator.py`, `test_market_data_service.py`, `test_mock_provider.py`, `test_indicator_service.py`, `test_market_data_tasks.py`

Deliberately excluded from this phase: any real market-data provider, a persisted symbol-mapping table, `/health/ready` provider-status integration, indicator synthesis/trend detection/technical scoring, SMC/regime/confidence engines, WebSocket price streaming

### Status

Phase 3A (Market Data Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 2C: Authentication API

`docs/37_AUTHENTICATION_FLOW.md` - new architecture document defining registration/login/refresh/logout/session-revocation flows, JWT lifecycle, audit-logging flow, service vs. API responsibilities, and future email-verification integration points

API routes (`app/api/v1/routes/auth.py`): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, matching `docs/04_API_SPECIFICATION.md`

Pydantic schemas (`app/schemas/auth.py`): `RegisterRequest`, `LoginRequest`, `RefreshRequest`, `LogoutRequest`, `TokenResponse`, `UserResponse` - all with OpenAPI examples; `TokenResponse.expires_in` always derived from `settings.jwt_access_expire_minutes`, never hardcoded

`app/dependencies/auth.py`: `get_user_service`, `get_authentication_service`, and `get_current_user` - the latter deliberately minimal (extract bearer token → decode → verify `type == "access"` → load user), with no authorization checks

`InvalidAccessTokenException` added to `app/exceptions/auth.py` for `get_current_user`'s token-validation failures

`UserService.register_user` now commits its own transaction (previously relied on the caller/tests to commit)

Response envelope conflict resolved: `docs/04` and `docs/33` each described a different, unimplemented `{"success": ...}` envelope; both were corrected to match the shape already implemented in Phase 1 (`app/exceptions/handlers.py`) - unwrapped success bodies, `{"error", "message"}` on failure

`docs/04_API_SPECIFICATION.md` updated with concrete request/response examples for every route, and marked `POST /auth/forgot-password`/`POST /auth/reset-password` as "not yet implemented"

Deliberately excluded from this phase: forgot/reset-password routes, session/device-management routes, OAuth, email verification, RBAC enforcement, rate limiting, CSRF/CSP, cookies

API-level tests: `test_auth_api.py` (11 tests covering all five routes' success and failure paths)

### Status

Phase 2C (Authentication API) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 2B: Authentication Service Layer

`UserService` - registration business logic: password-policy validation (docs/23 §7 — 12+ chars, upper/lower/number/special), email/username uniqueness checks (`DuplicateUserException`), and lookup helpers (`get_user_by_id`, `get_user_by_email`) raising `ResourceNotFoundException` when missing

`AuthenticationService` - `login`, `refresh`, `logout`, `revoke_session`, and `revoke_all_sessions`, with audit-log entries written for `login_success`, `login_failed`, `logout`, and `session_revoked` (docs/23 §18)

Custom authentication exceptions in `app/exceptions/auth.py`: `InvalidCredentialsException`, `InactiveAccountException`, `InvalidRefreshTokenException`, `DuplicateUserException`, `WeakPasswordException`

`hash_token()` added to `app/core/security.py` - deterministic SHA-256 hashing for refresh-token storage/lookup, distinct from Argon2id password hashing (see ADR-023)

Explicit, domain-oriented persistence methods added to `UserRepository`, `UserSessionRepository`, and `AuditLogRepository` (`create`, `get_by_id`, `delete`, `delete_for_user`) to support the new services, without adding generic `add`/`delete` to `BaseRepository`

Login intentionally does not require `User.is_verified` this phase, since email-verification infrastructure is deferred - recorded as a temporary decision in `BACKLOG.md` to revisit once that workflow exists

Unit tests: `test_user_service.py`, `test_authentication_service.py`

API routes, FastAPI dependencies, OAuth login flow, email verification, password reset, RBAC enforcement, middleware, and cookies intentionally out of scope for this phase; see `BACKLOG.md`

### Status

Phase 2B (Authentication Service Layer) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 2A: Authentication Data & Security Primitives

`User`, `OAuthAccount`, `UserSession`, and `AuditLog` models, plus `UserRole` and related enums, completing the auth-related domain models deferred from Phase 1.2B

`(provider, provider_user_id)` uniqueness constraint on `OAuthAccount`, documented as ADR-022 since it was inferred rather than explicitly specified in `docs/03`

OAuth token persistence intentionally omitted from `OAuthAccount` for this phase (only linking fields are stored)

`UserRepository`, `OAuthAccountRepository`, `UserSessionRepository`, `AuditLogRepository` - concrete repositories limited to data access, no business logic

`app/core/security.py` - password hashing and UUID-based JWT helpers with standard claims

Alembic migration for auth tables (`a7dad339df2e_create_auth_tables`), verified via upgrade/downgrade/upgrade round-trip and `alembic check`

Tests covering security utilities, user models, and foreign-key behavior

Business logic, API endpoints, and authentication flows (register/login/refresh/logout) intentionally deferred to a later phase; see `BACKLOG.md`

### Status

Phase 2A (Authentication Data & Security Primitives) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 1.2B: Domain Models

`SystemSetting` model - the first real domain model, with a unique/indexed `key`, `value`, `description`, and full created_at/updated_at

`SystemSettingRepository` - a concrete repository with a single data-access method (`get_by_key`), no business logic

`CreatedAtMixin` - reusable infrastructure for append-only rows (single `created_at`, no `updated_at`)

First real Alembic migration (`2822d8e2e377_create_system_settings_table`), verified via a full upgrade/downgrade/upgrade round-trip and `alembic check` with zero drift

`AuditLog` intentionally deferred to Phase 2, to be modeled together with `User` so its foreign key can be correct from the start

### Status

Phase 1.2B (Domain Models) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 1.2A: Database Foundation

`UUIDMixin` and `TimestampMixin` for SQLAlchemy models (UUID primary keys, UTC created_at/updated_at)

`BaseRepository` generic infrastructure: constructor-injected session, query/filter/pagination helpers, transaction context manager - no CRUD, so concrete repositories define their own operations

Verified Alembic autogeneration against the current (model-free) metadata; migration history intentionally left empty until the first real domain model lands

### Status

Phase 1.2A (Database Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

### Added - Phase 1.1: Project Foundation

Backend skeleton (FastAPI) structured per Clean Architecture layering: api, config, core, database, dependencies, middleware, exceptions, repositories, services, utils, workers

Frontend skeleton (Next.js, TypeScript, Tailwind, shadcn/ui) structured per the documented frontend folder layout

Docker and Docker Compose setup for frontend, backend, worker, PostgreSQL, and Redis, with healthchecks

uv adopted as the official backend dependency manager (ADR-021)

Structured JSON logging via structlog, shared between FastAPI and future Celery workers, with correlation ID propagation and sensitive-data redaction

Liveness (`/health`) and readiness (`/health/ready`) endpoints

Alembic migration scaffolding wired to centralized configuration

CI foundation via GitHub Actions (ruff, mypy, pytest, eslint, typecheck, build)

Development tooling: ruff, mypy, black, pytest (backend); eslint, prettier, TypeScript strict mode (frontend)

### Status

Phase 1 (Project Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

## Version 1.0.0

### Added

Complete software architecture

36 engineering documents

AI architecture

Frontend guidelines

Backend guidelines

Database design

API specification

Development roadmap

---

Future releases will follow Semantic Versioning.