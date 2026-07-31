# Changelog

## Unreleased

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