# Build Spec — Phase 8F: Audit Logs

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Most relevant here:
   never violate an accepted ADR; documentation is the source of truth; never
   invent architecture; prefer improving existing files over creating new ones.
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **No new schema. No migration.** The `audit_logs` table has existed since
   Phase 2B and is correct as-is. If you believe a column is needed, **STOP and
   report it** — do not add one.
5. **This is a READ-side phase.** See §1, which is the single most important
   thing to understand before you start.

---

## 1. Critical context — most of the write side already exists

`BACKLOG.md` describes 8F as "reuses the existing `AuditLog` table for every
admin mutation." That is easy to misread as "wire up audit logging." **Audit
logging is already wired up.** Verify this yourself before writing anything:

Already writing audit rows today:
- `app/services/authentication_service.py` — `login_success`, `login_failed`,
  `logout`, `session_revoked`
- `app/services/admin_user_service.py` — `admin_user_created`,
  `admin_user_updated`, `admin_user_disabled`, `admin_user_activated`,
  `admin_role_changed`, `admin_password_reset`, `admin_user_deleted`

**What is actually missing is the read side:**
- `AuditLogRepository` has only `list_for_user(user_id, ...)` — no admin-wide
  listing, no filtering, no count.
- There is no `GET /admin/logs` route. `docs/04` lists the path and **nothing
  else** — no query params, no response shape. The contract is therefore
  inferred and needs an ADR (§4).
- `frontend/app/(protected)/admin/audit-logs/page.tsx` is a Phase 8D
  placeholder.

**Do not add new audit-write call sites in this phase.** If you spot a mutation
that arguably should be audited but isn't, record it in `BACKLOG.md` and move
on — expanding write coverage is a separate scoping decision.

---

## 2. Model reference (read `app/models/audit_log.py`; do not change it)

| Field | Notes |
|---|---|
| `id` | |
| `user_id` | FK → `users`, **`ON DELETE SET NULL`**, nullable — the **actor** |
| `action` | `String(255)`, e.g. `login_success`, `admin_role_changed` |
| `resource` | `String(255)`, e.g. `user`, `user_session` |
| `resource_id` | nullable UUID — the **target** |
| `ip_address` | `String(45)`, nullable |
| `context` | **Python attribute is `context`, DB column is `metadata`** — JSON, nullable |
| `created_at` | `CreatedAtMixin`; append-only, no `updated_at` |

Three things that will bite you:

- **`context` vs `metadata`.** The attribute is `context` (`metadata` is
  reserved by SQLAlchemy's declarative base). Use `AuditLog.context` in queries
  and decide deliberately what the API field is called.
- **`user_id` is nullable and `SET NULL` on user delete.** A log row can have no
  actor — either a failed login before the user resolved, or a since-deleted
  user. The API and UI must render that without crashing. **Test this case.**
- **`user_id` is the actor, `resource_id` is the target.** On
  `admin_role_changed`, `user_id` is the admin who acted and `resource_id` is
  the user whose role changed. Do not mix these up in the UI.

There is an existing index on `(user_id, created_at)`.

---

## 3. Backend deliverables

### 3.1 `AuditLogRepository` — add admin-wide query methods

Extend the existing file. Add a filtered list plus a matching count, following
how `UserRepository`'s filtering/pagination methods work (read them first —
`AdminUserService` consumes them and is your model for shape).

Filters to support: `user_id`, `action`, `resource`, and a `from`/`to`
`created_at` range. All optional and combinable.

**Ordering: newest first** (`created_at` descending). Audit logs are read
newest-first essentially always.

`BaseRepository._count` is generically typed to the repository's own model —
here that is `AuditLog`, so unlike 7D-A's `WatchlistItem` case (BACKLOG §26)
you **can** reuse `_count` directly.

### 3.2 `AdminAuditLogService` (new) — `app/services/`

Mirror `AdminUserService`'s shape (constructor takes repositories; one public
method per use case). Read it first.

Read-only. **No create, update, or delete methods.** Audit logs are append-only
evidence; an admin API that could mutate or delete them would defeat their
purpose. There must be no `DELETE /admin/logs` route.

The service should resolve the actor's email/name for display so the UI isn't
forced into N+1 lookups per row. Handle the null-actor case explicitly.

### 3.3 Route — `GET /admin/logs`

New file `app/api/v1/routes/admin_logs.py`, mirroring
`app/api/v1/routes/admin_users.py`'s structure. Register it in
`app/api/v1/router.py`.

**Gate it with the existing `require_admin` from `app/dependencies/rbac.py`**
(Phase 8B). Do not write a new role check and do not modify `get_current_user`.

Query params: `user_id`, `action`, `resource`, `from`, `to`, `page`, `limit`
— all optional. **Match `GET /admin/users`' existing pagination convention
exactly** (same param names, same response envelope shape). Read it and copy
the pattern rather than inventing a second convention.

**Security requirement:** the `context` JSON is developer-controlled and may
carry detail not intended for display. `docs/59` §11 already establishes that
plaintext passwords must never enter the audit context, and
`admin_user_service.py:256` has an explicit comment enforcing it. Before
returning `context` in the API response, **read every existing `_audit(...)`
call site** and confirm nothing sensitive is in there today. State in your
report what you found. If anything sensitive is present, do not return the
field — report it instead.

### 3.4 Tests

New tests under `backend/tests/`. Read `tests/test_rbac.py` and
`tests/test_admin_users*.py` first and follow their structure and fixtures.

Cover at minimum:
- returns logs newest-first
- each filter works (`user_id`, `action`, `resource`, date range) and they combine
- pagination works and total count is correct
- **a log row whose `user_id` is NULL serializes without error** (§2)
- **a non-admin authenticated user gets 403**
- **an unauthenticated request gets 401**
- there is no route that mutates or deletes an audit log

---

## 4. ADR-129

Append to `docs/36_DECISION_RECORDS.md` after ADR-128, matching the
neighbouring ADRs' full format (Title / Status / Context / Decision / Reason /
Alternatives Considered / Trade-offs / Future Review — read ADR-125 through
ADR-128 for style and wrap width).

Must cover:
- The `GET /admin/logs` contract (params, response shape, ordering) is
  **inferred** — `docs/04` lists only the path. Same category of inference as
  `GET /watchlists/{id}` (ADR-128) and `signals.created_at` (ADR-091).
- Read-only by design: no mutation or deletion endpoint, and why.
- That the write side already existed (Phase 2B/8C) and this phase deliberately
  did not expand it.
- **`docs/25` §14 lists seven record types: User Action, Admin Action, AI
  Decision, Configuration Change, Login, Logout, Security Events. Only Admin
  Action, Login, and Logout are actually written today.** "AI Decision" and
  "Configuration Change" have no write call sites anywhere. Record this gap
  explicitly as deferred — do **not** invent logging for them in this phase
  ("never invent architecture").

---

## 5. Frontend deliverables

**Commit the backend first (§7), then do this.** A frontend failure must not
strand a working backend.

Replace the Phase 8D placeholder at
`frontend/app/(protected)/admin/audit-logs/page.tsx` with a real page.

- `frontend/services/admin.ts` — extend with the logs endpoint (do not create a
  second admin service module).
- Types into `frontend/services/types.ts` alongside the existing `Admin*` types.
- A hook following `use-admin-users.ts`'s shape.
- **Reuse the existing admin table/filter-bar/pagination components** from
  `frontend/features/admin/components/` (`user-table.tsx`,
  `user-filter-bar.tsx` are your models). No new UI primitives.
- Columns: timestamp, actor, action, resource, resource id, IP. Render a
  null actor as something honest like "system / deleted user" — not a blank
  cell or a crash.
- Loading, error, and empty states consistent with the rest of the admin area.
- Leave the other three placeholder pages (System Health, API Usage, Signal
  Statistics) **untouched** — they are still gated on backends that do not exist.

---

## 6. Verification — run these and report exact output

Backend:
```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Known baseline: 918 passed, 1 failed** as of commit `13ef42a`. The one failure
is `tests/test_market_data_dependencies.py::test_get_market_data_providers_returns_rate_limited_mock`
(local `.env` sets `MARKET_DATA_PROVIDERS=["twelve_data"]`; BACKLOG §9). **Do NOT
fix it, do NOT touch `.env`.** Any *other* failure means stop and report.

```
cd backend && .venv/Scripts/python.exe -m alembic check
```
Expect only the pre-existing `telegram_accounts` drift (BACKLOG §26). **This
phase adds no migration** — if `alembic check` shows anything about
`audit_logs`, you changed a model you shouldn't have. Stop and report.

Frontend:
```
cd frontend && npm run typecheck && npm run lint && npm run build
```
**Do NOT run `npm run format:check`** — it fails on ~55 pre-existing files
(BACKLOG §23) unrelated to your work.

**Manual check (required — there is no frontend test suite).** Backend running,
logged in as an admin. Report what you actually observed:
- the page lists real audit rows, newest first
- performing an admin action (e.g. disable a user) then reloading shows the new
  row with the correct actor and target
- each filter narrows results correctly
- pagination works past page 1
- a non-admin user cannot reach the page or the endpoint

Use the local dev environment. **Do NOT test against production.**

---

## 7. Done criteria

- `GET /admin/logs` works, admin-gated, filtered, paginated, newest-first.
- No migration, no model change, no new audit-write call sites.
- No route can mutate or delete an audit log.
- ADR-129 written, including the docs/25 §14 coverage gap.
- Tests green against the stated baseline; null-actor and 403/401 cases covered.
- Admin Audit Logs page is real; the other three placeholders untouched.
- `docs/30` (mark 8F complete), `docs/04` (fill in the `GET /admin/logs`
  contract), `BACKLOG.md`, `CHANGELOG.md` updated.
- **Two commits** — backend, then frontend — `feat:` prefix, matching
  `git log --oneline -10` style, each ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 8. Report back

What you built, **both** commit SHAs, exact pytest/alembic/typecheck/lint/build
output, what you actually observed in the manual walkthrough (not "it works"),
your findings from the §3.3 sensitive-context audit, and — most importantly —
**anything in this spec that turned out to be wrong about the repo, or any
judgment call you had to make.** If you disagree with something here, say so
rather than silently working around it. If a doc contradicts this spec, the doc
wins; stop and report the conflict.
