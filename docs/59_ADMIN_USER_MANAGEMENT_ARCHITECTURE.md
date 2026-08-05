# Admin User Management Architecture (Phase 8)

# 1. Scope

This is a bigger architectural shift than Phase 7D-C/7D-D's original Admin
scoping (`docs/58_WATCHLISTS_ADMIN_ARCHITECTURE.md` §3, ADR-115 through
ADR-118): this project is moving from **open self-service registration** to
**admin-provisioned accounts only**. That reverses an assumption every prior
auth phase (2A/2B/2C/7A) built on top of - `docs/23_AUTHENTICATION_AND_RBAC.md`
§3's "Registration Flow" describes public self-registration; that section
becomes historical once this phase ships, and `docs/23` needs a documentation
update alongside the code (§9.1 below).

Phase 8 **supersedes ADR-116's user-management scope decision specifically**
(it was written when no user-CRUD requirement existed) but leaves ADR-114
(Watchlists), ADR-115 (simple-enum RBAC model), ADR-117 (maintenance-action
scope), and ADR-118 (client-side nav gating) unchanged - this phase extends
those, it doesn't replace them. See §10 for the full relationship to prior
decisions.

Architecture only in this document - no code is written here, per explicit
instruction. Everything below is a proposal awaiting approval before
Phase 8B implementation begins.

Sub-phase order (as requested): 8A (this document) → 8B (Authorization) →
8C (User Management) → 8D (Frontend) → 8E (Registration Removal) → 8F
(Audit Logs, folded into §8 below since it needs no new schema) → 8G
(Security Review, §11).

---

# 2. Database Impact

## 2.1 `User` model - required changes

| Field | Type | Reason |
|---|---|---|
| `deleted_at` | `DateTime(timezone=True)`, nullable, indexed | Soft delete marker (§4). `NULL` = active/visible; non-`NULL` = deleted. Distinct from `is_active` (suspended-but-recoverable) - a deleted user is excluded from every listing by default, a suspended one still appears, just can't log in. |
| `must_change_password` | `Boolean`, default `False` | Set `True` whenever an admin sets a password on the user's behalf (creation or reset) - the user didn't choose it, so it shouldn't remain valid indefinitely without their knowledge. See §7.1 for enforcement scope - flagged as an open decision in §12. |
| `created_by_admin_id` | `Uuid`, nullable, FK `users.id` `ON DELETE SET NULL` | Which admin created this account - `NULL` only for the bootstrap super-admin (§9) and any pre-Phase-8 self-registered users, both of which predate admin-only creation. Same `SET NULL` precedent as `AuditLog.user_id`/`TelegramAccount` FKs - a user record shouldn't become unreadable just because its creator was later deleted. |

`is_active` (existing) is reused unchanged for suspend/activate - no new
"status" enum. `email`/`username`/`password_hash`/`full_name`/`role`/
`is_verified`/`timezone`/`language`/`last_login` are all unchanged.

## 2.2 `UserRole` enum

**No changes.** Reuses the existing 7-value enum (`guest` through
`super_admin`) exactly as-is, consistent with ADR-115's already-accepted
decision to defer the granular `roles`/`permissions`/`role_permissions`
schema (docs/23 §12-14, still deferred, BACKLOG.md §2/§26).

## 2.3 Migrations needed

**Yes - one new Alembic migration**, adding the three `User` columns above.
Mind the two standing gotchas already documented in BACKLOG.md §5/§9:
`server_default` must be checked/corrected if generated against the SQLite
verification DB (Postgres needs `sa.func.now()`, not
`sa.text('(CURRENT_TIMESTAMP)')` - not directly relevant here since none of
these three columns need a `server_default`, but worth restating since it's
this project's most-repeated migration mistake), and the migration should be
round-tripped (upgrade → downgrade → upgrade → `alembic check`) against
SQLite before commit, same as every prior migration.

No changes needed to `AuditLog` - its existing shape (`user_id` = actor,
`action`, `resource`, `resource_id` = target, `ip_address`, `context` JSON)
already covers every field Phase 8F asks for. See §8.

---

# 3. Backend Architecture

```
app/
  dependencies/
    rbac.py                    NEW - require_role/require_admin/require_super_admin
  api/v1/routes/
    admin/
      __init__.py               NEW - sub-router aggregation
      users.py                  NEW - the user-management endpoints (§6)
  services/
    admin_user_service.py       NEW - AdminUserService (business rules, §3.3)
  repositories/
    user_repository.py          EXTENDED - list/count/soft-delete methods (§3.2)
  schemas/
    admin.py                    NEW - AdminUserCreateRequest/UpdateRequest/
                                       ListResponse/PasswordResetResponse
  core/
    security.py                 EXTENDED - generate_temporary_password() (§7.1)
  exceptions/
    admin.py                    NEW - RegistrationDisabledException,
                                       LastSuperAdminException, RoleEscalationException
```

## 3.1 Admin Router

`app/api/v1/routes/admin/users.py`, mounted at prefix `/admin/users`, every
route depends on `require_admin` at minimum (some further restrict to
`require_super_admin`, §6). Registered in `router.py` alongside the existing
routers - no change to how routing is wired, just a new module.

## 3.2 Repository Extensions (`UserRepository`)

New methods, following the existing thin-repository convention (no business
logic, just queries):

- `list_paginated(*, page, limit, search, role, is_active, include_deleted) -> list[User]`
- `count_filtered(*, search, role, is_active, include_deleted) -> int`
- `soft_delete(user: User) -> None` - sets `deleted_at = now()`
- `count_by_role(role: UserRole) -> int` - needed for the "last super admin" guard (§6, §11)

`get_by_id`/`get_by_email`/`get_by_username`/`create` (existing) are
unchanged and reused - `AdminUserService.create_user` calls the same
`UserRepository.create` the public register flow used to call.

## 3.3 `AdminUserService` (new)

Owns every admin-user-management business rule so the route layer stays
thin, mirroring `AuthenticationService`'s existing shape (constructor-injects
`UserRepository` + `AuditLogRepository`, one public method per use case,
private `_audit`/`_commit` helpers - literally the same pattern, not a new
one):

- `list_users(...)` / `get_user(id)` - read paths, no audit entry (reads
  aren't logged anywhere else in this project either - only mutations are)
- `create_user(actor, payload)` - validates email/username uniqueness
  (`DuplicateUserException`, existing), enforces the role-grant ceiling
  (§11 - an `admin` actor cannot create `admin`/`super_admin` accounts),
  generates a temporary password if none supplied, sets
  `must_change_password=True`, `created_by_admin_id=actor.id`
- `update_user(actor, target_id, payload)` - allow-listed fields only
  (`full_name`, `username`, `email`); role changes go through a separate
  `change_role` method so the escalation guard (§11) has one enforcement
  point, not two
- `change_role(actor, target_id, new_role)` - `require_super_admin` at the
  route level already blocks non-super-admins; additionally blocks a
  super-admin from demoting themselves if they're the last one
  (`LastSuperAdminException`, uses `count_by_role`)
- `set_status(actor, target_id, is_active)` - suspending calls
  `AuthenticationService.revoke_all_sessions` (existing, Phase 2B) so a
  suspended user's live sessions die immediately, not just future logins
- `reset_password(actor, target_id)` - generates a new temporary password,
  sets `must_change_password=True`, revokes all sessions (forces re-login
  with the new password), returns the plaintext temp password **once** -
  never persisted, never logged (§11)
- `delete_user(actor, target_id)` - soft delete only (§4); blocks
  self-deletion and blocks deleting the last super admin

Every mutating method ends with one `AuditLogRepository.create(...)` call -
see §8 for the exact fields.

## 3.4 Authorization Dependency

Detailed in §6 (Phase 8B) - `app/dependencies/rbac.py`'s `require_role`/
`require_admin`/`require_super_admin`, composed with the existing
`get_current_user` (unchanged, still authentication-only per its own
docstring).

## 3.5 Audit Logging

No new table. `AdminUserService` reuses `AuditLogRepository` (existing since
Phase 2B) through the same `_audit`/`_commit` pattern
`AuthenticationService` already established - see §8 for the full field
mapping.

---

# 4. Why Soft Delete, Not Hard Delete

`User` is a foreign-key target for `watchlists.user_id`, `telegram_accounts.
user_id`, `conversations.user_id`, `ai_analysis`, and `user_sessions` - most
`CASCADE`, meaning a hard delete would silently destroy a user's entire
history (chat conversations, linked Telegram account, watchlists) the
moment an admin clicks delete, with no undo. Soft delete (`deleted_at`)
preserves all of that data (useful for audit/compliance/dispute resolution)
while removing the account from every user-facing listing and blocking
login (`AuthenticationService.login` gains one more check: `deleted_at is
None`, same shape as the existing `is_active` check).

Hard delete is **not** offered as an option in this phase - if a genuine
GDPR-style "erase my data" requirement ever emerges, that's its own design
pass (which data actually must be erased vs. anonymized vs. retained for
legal/audit reasons is a real decision, not one to make as a side effect of
an admin "delete user" button).

---

# 5. Frontend Architecture

```
frontend/
  components/layout/
    admin-guard.tsx             NEW - AdminGuard, gates the whole /admin route group
    admin-sidebar.tsx           NEW - Admin section's own nav (Dashboard/Users/Audit
                                 Logs/System Health/API Usage/Signal Statistics/
                                 Telegram Status/Settings)
    sidebar.tsx                 EXTENDED - conditional "Admin" link (ADR-118, already
                                 decided last session, now has a real destination)
  app/(protected)/admin/
    layout.tsx                  NEW - wraps every /admin/* page in AdminGuard + AdminSidebar
    page.tsx                    Dashboard (KPI summary - user count, signals today, etc.)
    users/page.tsx               Users list (table, filters, pagination, Add User dialog);
                                 detail is a Sheet-based drawer (§5.2), not a separate route
    audit-logs/page.tsx          Table + filters over the existing AuditLog data
    system-health/page.tsx       Liveness + counts (§10.1)
    api-usage/page.tsx           Deferred or narrowed (§10.1, open decision)
    signal-statistics/page.tsx   Aggregates over the existing signals table
    telegram-status/page.tsx     Aggregates over telegram_accounts
    settings/page.tsx            CRUD over the existing SystemSetting table
  features/admin/
    components/                 UserTable, UserFilterBar, UserDetailDrawer,
                                 AddUserDialog, EditUserDialog, ResetPasswordDialog,
                                 ConfirmDialog (generic, reused by disable/delete/reset)
  services/admin.ts               Thin apiGet/apiPost/apiPatch/apiDelete wrappers,
                                 same shape as every other Phase 7 service module
  hooks/use-admin-users.ts        One TanStack Query hook per query/mutation, same
                                 pattern as every other feature folder
```

## 5.1 Route Protection

`AdminGuard` follows `AuthGuard`'s exact shape (Phase 7A) - render a loading
state until `useAuth()` resolves, then check both authentication *and*
`user.role`. A non-admin authenticated user hitting `/admin/*` is redirected
to `/dashboard` (not shown a 403 page - consistent with how this project
already treats "wrong place," e.g. `GuestGuard` redirecting an
already-logged-in user away from `/login`). As with every route-protection
decision since ADR-099, this is a UX convenience, not the security boundary
- the real boundary is `require_admin` on the backend (§6). A user who
somehow reaches an admin page's UI but whose token fails `require_admin`
server-side simply gets failed API calls / toasts, the same as any other
403 in this app today.

## 5.2 User Detail as a Drawer, Not a Route

A `Sheet`-based drawer (reusing the existing primitive from Phase 7A's
mobile nav) rather than a `users/[id]` page - admins jump between many user
records quickly while keeping the filtered list visible behind it, closer
to how the Signal/News detail pages work when reached from a table, but
without losing list context on navigation. Genuinely deep-linkable detail
(e.g. sharing a direct URL to one user's record) isn't a stated requirement
here; add a route later if that need appears.

## 5.3 New Shared UI Primitive Needed

`components/ui/alert-dialog.tsx` (wraps `@radix-ui/react-alert-dialog`, not
yet a dependency) - the generic `ConfirmDialog` for disable/delete/reset
actions needs a true modal-that-blocks-interaction-until-answered, which
`Dialog` (used for forms) doesn't semantically guarantee the same way
Radix's dedicated `AlertDialog` does. Same "add the primitive only when a
real need appears" precedent as `Tooltip`/`Tabs` in Phase 7B.

## 5.4 Role-Aware Navigation

`Sidebar`'s existing `NAV_GROUPS` structure (Phase 7B) already supports
per-item visibility; the "Admin" entry (already anticipated, ADR-118)
becomes real here: rendered only when `useAuth().user.role` is
`admin`/`super_admin`. Within Admin itself, the Users page's role-change
action is further gated in the UI (hidden/disabled unless
`useAuth().user.role === "super_admin"`) mirroring the backend's
`require_super_admin` on that specific endpoint - UI-level gating here is
purely to avoid showing a control that will just 403, not a second security
boundary.

---

# 6. Phase 8B — Authorization Layer & API Specification

`app/dependencies/rbac.py`:

```python
def require_role(*roles: UserRole):
    def _check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise PermissionDeniedException()   # existing exception, 403
        return current_user
    return _check

require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_role(UserRole.SUPER_ADMIN)
```

`get_current_user` (Phase 2C) is **not modified** - it remains
authentication-only by design (its own docstring says so, and BACKLOG.md
§4/§20 already flagged this as the intentional seam). `require_role` wraps
it via `Depends()`, the same composition pattern every other dependency in
this project already uses (e.g. `get_authentication_service` composing
`get_db`). Authentication already exists and is untouched; this is purely
additive.

## 6.1 "Permission decorators" and future extensibility

FastAPI's idiom is `Depends()`, not decorators - `require_admin`/
`require_super_admin`/`require_role(...)` used as `Depends(require_admin)`
**are** this project's equivalent of a permission decorator. For genuine
future extensibility beyond role-level checks (e.g. a `Moderator` who can
view but not suspend users - docs/23 §13's tier that still has no matching
endpoint in this phase), I'm proposing an **in-code** seam, not a new
database table (consistent with ADR-115's already-accepted "defer the
permission-table schema" decision):

```python
class Permission(StrEnum):
    USERS_READ = "users.read"
    USERS_WRITE = "users.write"
    USERS_DELETE = "users.delete"
    ROLES_MANAGE = "roles.manage"

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset({Permission.USERS_READ, Permission.USERS_WRITE}),
    UserRole.SUPER_ADMIN: frozenset(Permission.__members__.values()),
}

def require_permission(permission: Permission):
    ...  # checks ROLE_PERMISSIONS[current_user.role]
```

This is a plain Python dict, not a schema change - if a real permission-table
requirement ever materializes, `ROLE_PERMISSIONS` is the one place that
changes from a hardcoded dict to a DB-backed lookup, and every route
call-site (`Depends(require_permission(Permission.USERS_WRITE))`) is
unaffected. **This is an open decision** (§12) - Phase 8C's actual routes
only need role-level granularity (`require_admin`/`require_super_admin`), so
building the `Permission` enum now is slightly ahead of demonstrated need.

## 6.2 API Specification

All routes below require `require_admin` unless marked otherwise. All
mutating routes write an `AuditLog` row (§8).

### `GET /admin/users`

List users, paginated. Query params: `page`, `limit` (mirrors every other
paginated list endpoint's `{page, limit, total}` envelope, e.g. `GET
/signals`), `search` (matches email/username/full_name, `ILIKE`), `role`
(filter, `UserRole`), `is_active` (filter, bool), `include_deleted` (bool,
default `False`, **`require_super_admin`-only when `True`** - regular admins
never see deleted accounts, only super admins auditing history can).

### `POST /admin/users`

Create a user. Body: `email`, `username`, `full_name` (optional), `role`
(defaults to `registered`), `password` (optional - if omitted, a
cryptographically random temporary password is generated and returned once
in the response). Response: `AdminUserResponse` (extends `UserResponse` with
`must_change_password`, `created_by_admin_id`, `deleted_at`) plus
`temporary_password` **only if one was generated** (never echoes an
admin-supplied password back). An `admin`-role actor requesting
`role: "admin"` or `"super_admin"` gets `403` (§11) - only `super_admin`
actors may create admin-tier accounts.

### `GET /admin/users/{id}`

Single user detail - same `AdminUserResponse` shape as list rows, plus
counts useful for the detail drawer (`active_session_count`,
`watchlist_count`) computed via existing repositories, no new joins beyond
simple `COUNT`s.

### `PATCH /admin/users/{id}`

Partial update: `full_name`, `username`, `email` only (explicit allow-list,
§11 "mass assignment"). Role changes are **not** accepted here - see
`PATCH /admin/users/{id}/role` below, so the escalation guard has exactly
one code path to review, not a role field buried in a general-purpose PATCH.

### `DELETE /admin/users/{id}`

Soft delete (§4). `404` if already deleted. `409` (`ConflictException`,
existing) if `target_id == actor.id` (no self-delete) or if the target is
the last remaining `super_admin` (`LastSuperAdminException`).

### `POST /admin/users/{id}/reset-password`

Generates and sets a new temporary password, sets `must_change_password =
True`, revokes all of the target's sessions. Response:
`{"temporary_password": "..."}`, shown to the admin exactly once - there is
no email infrastructure in this project (BACKLOG.md §4 dependency,
unchanged) to deliver it any other way, so out-of-band delivery (reading it
off screen, a Slack DM, etc.) is the admin's responsibility, same trust
model as any other admin panel without email.

### `PATCH /admin/users/{id}/status`

Body: `{"is_active": bool}`. Suspending (`false`) revokes all sessions
(reuses `AuthenticationService.revoke_all_sessions`, Phase 2B). `409` if
suspending the last remaining `super_admin` with no other active
super-admin to act (mirrors the delete guard - an org should never be able
to lock itself out of Admin entirely).

### `PATCH /admin/users/{id}/role`

`require_super_admin` only, distinct from the general
`PATCH /admin/users/{id}` (§11's single-enforcement-point reasoning above).
`409` via `LastSuperAdminException` if this would leave zero `super_admin`
accounts. Added beyond the user's literal endpoint list because it's needed
for "Role Changed" audit entries (§8) with its own, stricter authorization.

---

# 7. Phase 8C — User Management Features

| Feature | Why |
|---|---|
| **List** | The base admin capability - without it, no other feature is reachable (can't edit a user you can't find). |
| **Search** | An org with more than a handful of users needs to find one by email/username without paging through everything. |
| **Filter** (role, status) | Answers real operational questions fast - "show me every suspended account," "show me every admin" - that scrolling a flat list can't. |
| **Pagination** | Same reasoning as every other list endpoint in this project (`GET /signals`, `GET /news`, etc.) - required at any real scale, cheap to add now vs. retrofit later. |
| **Create** | The core purpose of this entire phase - registration is admin-only now, so this *is* the only way an account comes into existence. |
| **Edit** | Correcting a typo'd email/username, or updating full name - low-risk, high-frequency admin task. |
| **Disable** | Revoke access without destroying data - the right response to "this employee left" or "this account looks compromised," reversible. |
| **Activate** | The reverse of Disable - a suspended account isn't necessarily gone forever (temporary lockout, resolved dispute). |
| **Reset Password** | The single most common admin-panel support request in any system without self-service password reset (which this project still doesn't have - BACKLOG.md §4, email infra still doesn't exist). This *is* this project's password-reset mechanism until email infrastructure exists. |
| **Delete** (soft) | For accounts that should be fully hidden from normal operation (not just suspended) - see §4 for why soft, not hard. |

## 7.1 `must_change_password` enforcement scope (flagged, see §12)

Setting the flag (on create/reset) is proposed as in-scope for Phase 8C.
**Enforcing** it - blocking API access or forcing a password-change screen
until the flag clears - is a second, separable piece of work (a new
`PATCH /auth/me/password` endpoint, a frontend interstitial, a check
somewhere in the request pipeline). I'm proposing the flag exists and is
visible (`GET /auth/me` gains `must_change_password: bool`) in Phase 8C, but
enforcement is a named follow-up item unless you want it pulled into this
phase.

---

# 8. Phase 8F — Audit Logs

No schema change needed - `AuditLog` (Phase 2B) already has every field
requested:

| Requested | `AuditLog` field | Notes |
|---|---|---|
| Who | `user_id` | The **actor** (the admin performing the action) - same convention `AuthenticationService` already uses |
| When | `created_at` | Automatic, `CreatedAtMixin` |
| Target | `resource_id` | The affected user's `id`; `resource="user"` |
| Old Value / New Value | `context` (JSON) | `{"old": {...}, "new": {...}}` - only the changed fields, not a full user dump (never write `password_hash` into this JSON, even hashed - §11) |
| IP Address | `ip_address` | Same as every existing audit entry - `request.client.host`, passed through from the route the same way `auth.py`'s routes already do |

Actions logged (all new, following the existing lowercase-snake-case
convention `login_success`/`session_revoked` already established):
`admin_user_created`, `admin_user_updated`, `admin_user_disabled`,
`admin_user_activated`, `admin_password_reset`, `admin_user_deleted`,
`admin_role_changed`.

## 8.1 docs/23 update required

`docs/23_AUTHENTICATION_AND_RBAC.md` §3 ("Registration Flow") describes
public self-registration and needs a note that this is superseded by
admin-only provisioning as of Phase 8, per this project's established
practice of updating docs *as part of* the phase that changes the behavior
(BACKLOG.md §7's "update docs before/alongside implementation" precedent),
not as a stale afterthought.

---

# 9. Phase 8E — Removing Public Registration: Safest Migration Path

The core risk here isn't technical, it's operational: this project has
**zero admin accounts today**. Removing public registration without first
solving how the first account gets created would brick login entirely.
Proposed sequence, in order:

1. **Bootstrap the first `super_admin` before touching the register route**
   (§12, open decision - recommending a one-off CLI script,
   `backend/scripts/create_admin.py`, operator-run, mirroring the existing
   `backend/scripts/seed_dev_data.py` precedent).
2. **Add a config flag**, `settings.allow_public_registration: bool = False`
   (new environments default closed; this repo's own `.env` can be
   explicitly set `True` during the bootstrap step above if convenient, then
   flipped back).
3. **Gate `POST /auth/register`** on that flag - when `False`, raise a new
   `RegistrationDisabledException` (`403`, explicit message: "Public
   registration is disabled - contact an administrator"), consistent with
   this project's typed-exception convention rather than silently 404ing
   (§12, open decision on which status code).
4. **`UserService.register_user` is not deleted or duplicated** -
   `AdminUserService.create_user` calls the exact same underlying method the
   public route used to call, so validation (password policy, uniqueness)
   never drifts between the two entry points.
5. **Frontend**: `/register` is not deleted outright (a removed route can
   404 unexpectedly for anyone with the URL bookmarked/linked, and Next.js's
   file-based routing makes "the route silently vanishes" a worse failure
   mode than an explicit message). Instead it becomes an informational stub
   - same precedent as `/forgot-password` (ADR-100) - stating accounts are
   admin-provisioned and directing the visitor to contact an administrator.
   The "Don't have an account? Register" link on `/login` is removed.
6. **`GuestGuard`** is unaffected - it still gates `/login`/`/forgot-password`
   the same way; `/register` simply stops being a functional form.

This order matters specifically because step 1 must complete before step 3
- flipping the flag first with no admin account yet would be an unrecoverable
lockout requiring direct database access to fix.

---

# 10. Relationship to Prior Decisions

| Prior decision | Status under Phase 8 |
|---|---|
| ADR-114 (Watchlists scope) | Unchanged - unrelated |
| ADR-115 (simple `UserRole` enum, no permission tables) | **Extended, not superseded** - `require_role` is built on it exactly as ADR-115 anticipated; §6.1's optional `Permission` seam is the closest this phase comes to finer granularity, and it's still not a DB table |
| ADR-116 (Admin backend limited to docs/04's 7 endpoints) | **Superseded for `/admin/users*`** - that ADR's reasoning ("no user-CRUD requirement existed") no longer holds; its reasoning about `/admin/system` having no real telemetry infrastructure still holds unchanged (§10.1 below) |
| ADR-117 (`/admin/maintenance` scope) | Unchanged - unrelated to user management |
| ADR-118 (client-side-only nav gating) | Extended - the same pattern now gates the whole `/admin` layout, not just a single nav item |
| docs/23 §3 (public registration) | **Superseded** - see §8.1/§9 |
| ADR-099 (client-side auth, no BFF) | Unchanged - Phase 8's `AdminGuard` (§5.1) is client-side, same as `AuthGuard`, consistent with the project's standing trade-off |

## 10.1 Frontend pages without a real data source (flagged, not silently built anyway)

Phase 8D's requested page list includes **System Health** and **API Usage**.
Consistent with ADR-116's unchanged reasoning: no metrics collection, Redis
telemetry, or request-tracking infrastructure exists anywhere in this
project (`GET /metrics` remains an open BACKLOG.md §3 item).

- **System Health** ships using the same liveness-plus-counts approach
  ADR-116 already established (`/health`/`/health/ready` + simple `COUNT`
  queries) - real, just not deep telemetry.
- **API Usage** has genuinely no backing data anywhere in this codebase.
  Rather than fabricate numbers or silently ship an empty page, I'm
  proposing this page either (a) is deferred out of Phase 8D entirely with
  an honest "not yet available, see BACKLOG.md §3" empty state, or (b) is
  narrowed to what's real and derivable today: per-day `ai_analysis`/
  `signals` row counts (a proxy for AI-orchestrator usage, not true API
  request metrics). Open decision, §12.

**Signal Statistics** and **Telegram Status** do have real data (`signals`
table aggregates; `telegram_accounts.linked_at IS NOT NULL` counts) and need
no new infrastructure.

---

# 11. Phase 8G — Security Review

| Risk | Mitigation |
|---|---|
| **Privilege escalation** | Role changes isolated to their own endpoint (`PATCH /admin/users/{id}/role`, §6.2), `require_super_admin`-only. An `admin`-role actor cannot grant `admin`/`super_admin` on `POST /admin/users` either (§6.2's create-endpoint ceiling check) - the only account tier that can create/promote admin-tier accounts is an existing super-admin. |
| **Horizontal access** (a normal user reaching another user's data) | Every `/admin/*` route requires `require_admin`; non-admin users have no route that accepts a `{user_id}` other than their own (`GET /auth/me` is the only self-scoped read, unchanged). |
| **Vertical access** (a lower-privileged admin acting on a higher-privileged account) | `AdminUserService` checks target role, not just actor role, on every mutation - an `admin` actor cannot edit/disable/delete/reset-password an `admin` or `super_admin` target, only `super_admin` can act on admin-tier accounts. This needs to be an explicit service-layer check, not just the route-level `require_admin`/`require_super_admin` split, since e.g. `PATCH /admin/users/{id}` is reachable by any admin but must still reject "admin edits another admin." |
| **Mass assignment** | `PATCH /admin/users/{id}` uses an explicit Pydantic schema with an allow-list (`full_name`, `username`, `email` only) - `role`, `password_hash`, `is_active`, `deleted_at`, `id`, `created_at` are never accepted through it; each has its own single-purpose endpoint instead. |
| **Role spoofing** | Not reachable even in principle: `_create_token` (`app/core/security.py`) never embeds `role` in the JWT payload (only `sub`/`type`/`iat`/`exp`/`jti`) - `get_current_user` always loads the role fresh from the DB on every request. A stale or forged role claim in a token isn't a real attack surface here; this existing property is preserved unchanged, not something Phase 8 needs to newly defend. |
| **Sensitive endpoints** (delete, role change, reset-password) | Frontend requires an explicit `AlertDialog` confirmation (§5.3) before any of these fire. Step-up re-authentication (re-entering the *admin's own* password before a destructive action) has no precedent anywhere in this project and is **not** proposed for Phase 8 - flagged as a possible future hardening pass, not built now, to avoid inventing a new auth pattern beyond what's demonstrated as needed. |
| **Password handling** | Temporary passwords generated via a cryptographically secure generator (`secrets.token_urlsafe`-based, `app/core/security.py`'s new `generate_temporary_password()`), immediately hashed with the existing Argon2id `hash_password` before persistence, returned to the admin exactly once in the API response body, and **never** written into `AuditLog.context` or any log line - the audit entry records that a reset happened, never the value. |
| **JWT** | Unaffected - existing access/refresh design (ADR-023) reused unchanged. Disabling or soft-deleting a user immediately revokes their sessions (`revoke_all_sessions`), so refresh is blocked right away; a still-live access token remains valid until its natural ≤15-minute expiry (pre-existing, documented gap, BACKLOG.md §4 - not newly introduced by this phase). |
| **CSRF** | Not applicable - this project's auth is Bearer-token-in-header only (ADR-099), never cookie-based, and CSRF specifically exploits ambient cookie auth. Unchanged by this phase. |

---

# 12. Decisions — Resolved 2026-08-05

1. **`must_change_password` enforcement** - **flag-only** in Phase 8C. The
   flag is set on create/reset and surfaced on `GET /auth/me`; actual
   enforcement (blocking access until changed) is a named future follow-up,
   not built in this phase.
2. **`Permission` enum seam** (§6.1) - **included**. `Permission`/
   `ROLE_PERMISSIONS` ships in Phase 8B alongside `require_role`.
3. **Bootstrap admin creation** (§9) - **Option A**: a one-off
   `backend/scripts/create_admin.py` CLI script, operator-run, mirroring
   the existing `seed_dev_data.py` precedent. No env-var auto-bootstrap.
4. **API Usage page** (§10.1) - **narrowed proxy**: real per-day
   `ai_analysis`/`signals` row counts, clearly labeled as a usage proxy,
   not true API request metrics.
5. **`POST /auth/register` disabled response** - **`403`** via a new
   `RegistrationDisabledException`, explicit message, consistent with this
   project's typed-exception convention.

Architecture approved. Corresponding ADRs (ADR-119 through ADR-124) recorded
in `docs/36_DECISION_RECORDS.md`. Proceeding to Phase 8B.
