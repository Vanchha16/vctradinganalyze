# Authentication Flow

Version: 1.0

Status: Describes the service layer (Phase 2A/2B) and the API layer (Phase 2C: `POST /auth/register`, `/login`, `/refresh`, `/logout`, `GET /auth/me`). Email verification remains deferred.

---

# 1. Scope

This document defines how authentication actually works today, service layer and API layer alike, and where the future email-verification workflow (deferred, see BACKLOG.md) will attach to it.

Source of truth for the pieces this document describes:

- `app/models/user.py`, `app/models/user_session.py`, `app/models/audit_log.py`
- `app/schemas/auth.py`, `app/dependencies/auth.py`, `app/api/v1/routes/auth.py`
- `app/core/security.py`
- `app/services/user_service.py`
- `app/services/authentication_service.py`

This document does not introduce new behavior. It records the design already implemented and reviewed in Phase 2A/2B.

---

# 2. Registration Flow

User

↓

`UserService.register_user(email, username, password, full_name=None)`

↓

Validate password policy (docs/23 §7 — 12+ chars, upper, lower, number, special character)

↓

Check email uniqueness → `DuplicateUserException` if taken

↓

Check username uniqueness → `DuplicateUserException` if taken

↓

Hash password (Argon2id, `core.security.hash_password`)

↓

Persist `User` via `UserRepository.create`

↓

Return created `User`

Notes

- No email is sent and no verification token is issued at registration — email delivery infrastructure is deferred (BACKLOG.md).
- `User.is_verified` defaults to `false` and stays `false` until the future email-verification flow sets it.
- No audit-log entry is written for registration — docs/23 §18's audit event list does not name registration, only login/logout/password-reset/role-change/failed-login/session-revocation/account-deletion.

---

# 3. Login Flow

User

↓

`AuthenticationService.login(email, password, device=None, ip_address=None, user_agent=None)`

↓

Look up user by email (`UserRepository.get_by_email`)

↓

Unknown email → audit-log `login_failed` (no `user_id`) → `InvalidCredentialsException`

↓

Verify password (Argon2id) → mismatch → audit-log `login_failed` → `InvalidCredentialsException`

↓

Check `User.is_active` → inactive → audit-log `login_failed` → `InactiveAccountException`

↓

Issue access token + refresh token (see §6 JWT Lifecycle)

↓

Hash refresh token (SHA-256, ADR-023) and persist a `UserSession` (device, ip_address, user_agent, expires_at)

↓

Update `User.last_login`

↓

Audit-log `login_success`

↓

Commit

↓

Return `(User, access_token, refresh_token)`

Notes

- Login intentionally does **not** require `User.is_verified` (temporary decision, recorded in BACKLOG.md, to be revisited once email verification exists). Only `is_active` gates login.
- Failed-login lockout (docs/23 §17) is not implemented — every failed attempt is audit-logged, but there is no counter or temporary lock yet.
- The error returned for "unknown email" and "wrong password" is the same (`InvalidCredentialsException`), to avoid leaking which emails are registered.

---

# 4. Refresh Flow

Client

↓

`AuthenticationService.refresh(refresh_token)`

↓

Decode JWT → invalid signature/expired/malformed → `InvalidRefreshTokenException`

↓

Check token `type` claim is `"refresh"` → otherwise `InvalidRefreshTokenException`

↓

Hash the token (SHA-256) and look up a matching `UserSession` → not found → `InvalidRefreshTokenException`

↓

Check `UserSession.expires_at` has not passed → expired → `InvalidRefreshTokenException`

↓

Look up the owning `User` and check `is_active` → missing/inactive → `InvalidRefreshTokenException`

↓

Issue a new access token

↓

Return the new access token

Notes

- Refresh does not currently rotate the refresh token itself (no new `UserSession` is created, no new refresh token issued) — refresh-token rotation-on-use is an open hardening idea (BACKLOG.md §4), not yet implemented.
- The stored `UserSession.expires_at` is compared using a UTC-aware normalization helper (`AuthenticationService._as_aware_utc`) to account for the SQLite naive-datetime behavior described in BACKLOG.md §9. Production Postgres does not need this normalization, but the code applies it unconditionally since it is a no-op for already-aware values.

---

# 5. Logout Flow

Client

↓

`AuthenticationService.logout(refresh_token)`

↓

Hash the token and look up the matching `UserSession`

↓

Not found → no-op (idempotent — logging out twice, or logging out an already-expired/removed session, does not raise)

↓

Found → delete the `UserSession`

↓

Audit-log `logout`

↓

Commit

Notes

- Logout only invalidates the session tied to the presented refresh token. It does not revoke the access token already issued from that session — see §6 JWT Lifecycle for why access tokens cannot currently be revoked before they expire.

---

# 6. Session Revocation Flow

Two entry points, both usable ahead of any API surface existing for them (see §9):

**Revoke one session**

Caller (the account owner, or a future admin/support flow)

↓

`AuthenticationService.revoke_session(user_id, session_id)`

↓

Look up the `UserSession` by id → missing, or `user_id` mismatch → `ResourceNotFoundException`

↓

Delete the `UserSession`

↓

Audit-log `session_revoked`

↓

Commit

**Revoke all sessions (optionally keeping one)**

Caller

↓

`AuthenticationService.revoke_all_sessions(user_id, except_session_id=None)`

↓

Bulk-delete all `UserSession` rows for the user, excluding `except_session_id` if given

↓

Audit-log `session_revoked` (bulk, with a count in `context`)

↓

Commit

↓

Return count of sessions revoked

Notes

- This maps to docs/23 §6/§11 ("users can revoke individual sessions" / "logout other devices" / "logout all devices"), but there is no API route calling these methods yet (Phase 2C).
- Revoking a session only removes the `UserSession` row (used by the refresh flow); it does not invalidate any access token already issued from that session, for the same reason noted in §5 and §6 below.

---

# 7. JWT Lifecycle

Access Token

Purpose: API authentication (future Phase 2C routes)

Lifetime: 15 minutes (`settings.jwt_access_expire_minutes`)

Claims: `sub` (user id), `type: "access"`, `iat`, `exp`, `jti`

Signing: HS256, `settings.jwt_secret`

Revocation: **not implemented.** The `jti` claim exists on every access token but nothing currently checks it against a denylist, so a compromised or logically-invalidated access token remains valid until natural expiry. This is a known gap (BACKLOG.md §4/§6) — logout/session-revocation only removes the ability to mint a *new* access token, they do not invalidate ones already issued.

---

Refresh Token

Purpose: issue new access tokens (`AuthenticationService.refresh`)

Lifetime: 30 days (`settings.jwt_refresh_expire_days`)

Claims: same shape as the access token, with `type: "refresh"`

Storage: never stored raw. Hashed with SHA-256 (`core.security.hash_token`, ADR-023) and stored as `UserSession.refresh_token_hash` for exact-match lookup. Argon2id is not used here — it is reserved for passwords (see ADR-023 for the reasoning).

Revocation: effective and immediate. Deleting the corresponding `UserSession` (via logout or session revocation) makes the refresh token unusable — `AuthenticationService.refresh` will no longer find a matching session.

---

# 8. Audit Logging Flow

Every audit event is written via `AuthenticationService._audit`, which persists an `AuditLog` row through `AuditLogRepository.create`, in the same transaction as the operation it describes (committed together, not separately).

Events currently written (Phase 2B):

- `login_success` — includes `ip_address` when provided
- `login_failed` — written for unknown email, wrong password, and inactive-account attempts alike; `user_id` is `null` when the email doesn't match any user
- `logout`
- `session_revoked` — both single-session and bulk revocation (bulk includes `{"bulk": true, "count": N}` in `context`)

Events named in docs/23 §18 but **not yet written** (because the flows producing them don't exist yet):

- Password reset
- Permission changes / role changes
- Account deletion

`AuditLog.user_id` uses `ON DELETE SET NULL` (see ADR from Phase 1.2B/2A modeling), so audit history survives user deletion even though the row's `user_id` is later nulled out.

---

# 9. Service Responsibilities

Per docs/06 §4/§7 (Clean Architecture, Service Layer):

`UserService`

- Password-policy validation
- Email/username uniqueness checks
- Password hashing (delegates to `core.security`)
- User lookups, translating "not found" into `ResourceNotFoundException`

`AuthenticationService`

- Credential verification
- Active-account enforcement
- Token issuance and refresh-token hashing/storage
- Session lifecycle: create (login), delete (logout/revocation), bulk-delete (revoke-all)
- Audit-log writing for every event above
- Structured logging (`structlog`) for login success/failure, logout, and revocation — no passwords or raw tokens are ever logged (the shared `_redact_sensitive_keys` processor also redacts common sensitive keys as a backstop)

Neither service contains SQL — all persistence goes through `UserRepository`, `UserSessionRepository`, and `AuditLogRepository`, each of which stays limited to data access (docs/06 §6).

---

# 10. API Responsibilities (Phase 2C)

Per docs/06 §8, the API layer (`app/api/v1/routes/auth.py`, `app/schemas/auth.py`, `app/dependencies/auth.py`) owns:

- Request/response validation via Pydantic schemas in `app/schemas/auth.py` (`RegisterRequest`, `LoginRequest`, `RefreshRequest`, `LogoutRequest`, `TokenResponse`, `UserResponse`) — routes never accept raw dicts or return ORM models directly (docs/06 §9); `UserResponse` uses `from_attributes=True` to serialize the `User` ORM object without ever exposing `password_hash`
- Mapping HTTP requests to the service calls documented above 1:1 (`POST /auth/register` → `UserService.register_user`, `POST /auth/login` → `AuthenticationService.login`, `POST /auth/refresh` → `.refresh`, `POST /auth/logout` → `.logout`, `GET /auth/me` → `get_current_user` → `UserService.get_user_by_id`)
- Extracting `ip_address` (`request.client.host`) and `user_agent` (the `User-Agent` header) for `login`; no `device` value is currently derived (docs/04's login request has no device field)
- Carrying tokens via the `Authorization: Bearer <token>` header (FastAPI's `HTTPBearer` security scheme) — no cookies, per approved Phase 2C scope
- `get_current_user` (`app/dependencies/auth.py`): deliberately minimal — extracts the bearer token, decodes it, verifies `type == "access"`, and loads the `User` via `UserService.get_user_by_id`. It performs **no authorization checks** (`is_active`, `is_verified`, role) — those remain out of scope for this phase, consistent with §3's note that only `login` gates on `is_active`
- Error responses use the shape already implemented in Phase 1's `app/exceptions/handlers.py` — `{"error": <error_code>, "message": <message>}` — and success responses are the resource itself, unwrapped. `docs/04` and `docs/33` previously each described a different, unimplemented `{"success": ...}` envelope; both were corrected in Phase 2C to match this actual behavior. No new exception-to-HTTP mapping was needed — `app/exceptions/auth.py`'s custom exceptions (including the new `InvalidAccessTokenException`, added in Phase 2C for `get_current_user`) all subclass `AppException` and are handled by the existing catch-all handler
- `expires_in` in `TokenResponse` is always computed from `settings.jwt_access_expire_minutes * 60`, never hardcoded
- `POST /auth/register` returns `201 Created`; `POST /auth/logout` returns `204 No Content`

**Deliberately excluded from Phase 2C** (per approved scope): `POST /auth/forgot-password`, `POST /auth/reset-password` (no underlying service logic exists — blocked on email infrastructure), and session/device-management routes (the business logic exists per §6, but docs/04 doesn't yet specify a route contract for it — see BACKLOG.md).

The API layer contains no business logic (docs/06 §8, docs/31 §4) — every route is a thin translation layer over the services documented above.

---

# 11. Future Email Verification Integration Points

Email verification itself remains deferred (BACKLOG.md — blocked on SMTP/Celery email infrastructure). When it is built, it is expected to attach at these points without changing what already exists:

- **Registration**: `UserService.register_user` would additionally trigger issuance of a verification token/email (or a calling API route would do so immediately after registration succeeds) — this does not require changing the uniqueness/password-policy logic already in place.
- **Login**: the temporary decision documented in §3 and BACKLOG.md — that `login` does not check `is_verified` — must be explicitly revisited at that point. Either `AuthenticationService.login` starts enforcing `is_verified`, or the project confirms verification should instead be enforced at the authorization/route-guard level for specific protected endpoints (docs/23 §8 says "required before accessing protected features," which is broader than "required to log in").
- **New endpoints** (not yet in docs/04, flagged in BACKLOG.md): `POST /auth/verify-email`, `POST /auth/resend-verification`, each backed by new service methods (likely on `UserService` or a dedicated verification service) — not designed here, since the workflow itself is out of scope until the email subsystem exists.
- **Audit logging**: email verification and resend events are not in docs/23 §18's list; whether to log them should be decided when the flow is designed, following the same precedent as ADR-022/ADR-023 if the decision is inferred rather than explicit.
