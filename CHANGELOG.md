# Changelog

## Unreleased

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