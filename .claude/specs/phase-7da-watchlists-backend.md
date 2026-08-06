# Build Spec — Phase 7D-A: Watchlists Backend

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Most relevant here:
   never violate an accepted ADR; documentation is the source of truth; never
   invent architecture; keep code modular; keep the project buildable.
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Backend only.** The frontend (`7D-B`) is a separate phase — do not touch
   `frontend/` at all, including the existing `app/(protected)/watchlists`
   placeholder. Leave it as-is.

---

## 1. Read these first (the scope is already decided — do not re-derive it)

- `docs/58_WATCHLISTS_ADMIN_ARCHITECTURE.md` **§2** — the authoritative spec.
  §2.1 persistence, §2.2 service/repository, §2.3 API. This is your contract.
- `docs/36_DECISION_RECORDS.md` — **ADR-114** (Watchlists scope decision),
  plus **ADR-022** and **ADR-090** for the inferred-uniqueness precedent.
- `docs/03_DATABASE_DESIGN.md` **§12** — the original table shape.
- `docs/04_API_SPECIFICATION.md` — the Watchlists section.

**Explicitly out of scope** (ADR-114 — these were deliberately excluded, not
forgotten; building any of them violates the ADR): custom alerts, tags,
pinning, AI watchlist summaries, performance history, sharing between users,
and any admin override.

---

## 2. Deliverables

### 2.1 Models

Exactly `docs/03` §12's fields. **No additions.**

`watchlists` — `UUIDMixin` + `CreatedAtMixin` (name is the only mutable field,
so `updated_at` is deliberately not needed; do not use `TimestampMixin`):

| Field | Notes |
|---|---|
| `id` | generated |
| `user_id` | FK → `users`, `ON DELETE CASCADE` |
| `name` | `String(255)`, **not unique** — a user may have two watchlists with the same name; no doc requires otherwise |
| `created_at` | |

`watchlist_items` — `UUIDMixin` + `CreatedAtMixin`:

| Field | Notes |
|---|---|
| `id` | generated |
| `watchlist_id` | FK → `watchlists`, `ON DELETE CASCADE` |
| `asset_id` | FK → `assets`, `ON DELETE CASCADE` |
| `created_at` | |

**Unique constraint on `(watchlist_id, asset_id)`** — an asset cannot be added
to the same watchlist twice. Follows the `OAuthAccount` `(provider,
provider_user_id)` precedent (ADR-022) and `signal_bookmarks`' equivalent
(ADR-090). Read the `signal_bookmarks` model first — it is the closest
existing analogue to `watchlist_items` and you should mirror its structure.

### 2.2 Migration

One Alembic migration creating both tables.

**Landmine — read this or you will lose time:**
- Use `op.create_table` (which declares FKs inline). If for any reason you
  need to alter an *existing* table, you **must** wrap it in
  `op.batch_alter_table` — SQLite has no `ALTER TABLE ... ADD CONSTRAINT` and
  `op.create_foreign_key` raises `NotImplementedError` against it. Recorded in
  `BACKLOG.md` §26.
- **Check `server_default` rendering before committing.** Autogenerate
  compiles `server_default` against whichever dialect is connected, and
  generating against SQLite has twice produced `sa.text('(CURRENT_TIMESTAMP)')`,
  which is invalid Postgres. Must be `sa.func.now()`. Recorded in `BACKLOG.md`
  §5 and §9 as "institutional knowledge — do not rediscover."

### 2.3 Repository & Service

`WatchlistRepository` and `WatchlistService`, following the existing
repository/service split. Read an existing pair first and mirror its
conventions rather than inventing a new shape.

**Every operation must be scoped to `user_id`.** A user can only see and mutate
their own watchlists. A request for another user's watchlist id must not leak
its existence — return the same not-found response as a genuinely missing id,
not a distinguishable forbidden response.

### 2.4 API routes

Per `docs/58` §2.3. All auth-gated via the existing `get_current_user` — do
**not** modify that dependency; compose it, the way `app/dependencies/rbac.py`
and `app/dependencies/quota.py` do.

```
GET    /watchlists                          list the caller's watchlists (with item counts)
GET    /watchlists/{id}                     single watchlist with resolved asset rows
POST   /watchlists                          create {name}
PUT    /watchlists/{id}                     rename {name}
DELETE /watchlists/{id}                     delete (cascades items)
POST   /watchlists/{id}/assets              add {asset_id}
DELETE /watchlists/{id}/assets/{asset_id}   remove
```

`GET /watchlists/{id}` is an **inferred addition** beyond docs/04's literal
list (needed for the 7D-B detail view) — same category of inference as
`signals.created_at` (ADR-091). Because it is inferred, it needs an ADR (§3).

Do **not** add a quota/rate-limit dependency here — these are plain DB reads
and writes with no LLM cost. ADR-127's quota is scoped to the two token-costed
endpoints only.

Errors must use the project's standard `{"error", "message"}` envelope. Follow
how existing exceptions are defined in `app/exceptions/` and surfaced through
the generic `AppException` handler.

### 2.5 ADR

Append **ADR-128** to `docs/36_DECISION_RECORDS.md`, after ADR-127, matching
the neighbouring ADRs' full format exactly (Title / Status / Context /
Decision / Reason / Alternatives Considered / Trade-offs / Future Review —
read ADR-125/126/127 for style and wrap width).

Cover: the inferred `GET /watchlists/{id}` addition and why; the
`(watchlist_id, asset_id)` uniqueness following ADR-022/ADR-090; the
`CreatedAtMixin`-not-`TimestampMixin` choice on both tables; and that
ADR-114's exclusions (alerts/tags/pinning/AI summary/performance history)
remain deferred and untouched.

### 2.6 Tests

New tests under `backend/tests/`. Read `tests/test_rbac.py` and the existing
API integration tests first and follow their structure and fixtures.

Cover at minimum:
- full CRUD round-trip on watchlists (create → list → rename → delete)
- add/remove asset
- **the `(watchlist_id, asset_id)` unique constraint is enforced** (adding the
  same asset twice fails)
- **cascade behaviour**: deleting a watchlist removes its items; deleting a
  user removes their watchlists. NOTE: SQLite does not enforce FKs unless
  `PRAGMA foreign_keys=ON` is set on the test connection — without it these
  tests will pass even if the constraint would fail on real Postgres
  (`BACKLOG.md` §5/§9). Verify the existing test setup enables it; if not,
  enable it for these tests.
- **user scoping**: user A cannot read, rename, delete, or add assets to user
  B's watchlist, and gets a not-found rather than a distinguishable error
- unauthenticated requests are rejected

### 2.7 Documentation updates

- `docs/30_DEVELOPMENT_ROADMAP.md` — mark 7D-A Completed; leave 7D-B as-is.
- `BACKLOG.md` — update §26 (7D-A is no longer "Not Started"); record any new
  deferred item or gotcha you hit.
- `CHANGELOG.md` — add an entry matching the file's existing format.
- `docs/04_API_SPECIFICATION.md` — if the Watchlists section doesn't already
  match what you built (notably `GET /watchlists/{id}`), update it. This
  project's practice is to keep docs/04 accurate in the same phase that
  implements the change, not as a follow-up.

---

## 3. Verification — run these and report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```

**Known baseline before your work: 907 passed, 1 failed.** The one failure is
`tests/test_market_data_dependencies.py::test_get_market_data_providers_returns_rate_limited_mock`,
caused by the local `backend/.env` setting `MARKET_DATA_PROVIDERS=["twelve_data"]`
while the test asserts the `mock` default (recorded in `BACKLOG.md` §9).
**Do NOT try to fix it and do NOT touch `.env`.** Your result should be that
same single failure plus your new tests passing. Any *other* failure means
stop and report.

```
cd backend && .venv/Scripts/python.exe -m alembic upgrade head
cd backend && .venv/Scripts/python.exe -m alembic check
```

**Known baseline:** `alembic check` already reports a pre-existing drift on
`telegram_accounts` (SQLite renders `UniqueConstraint`s as unique indexes —
`BACKLOG.md` §26). Confirm you introduced no *new* drift beyond that. Also
round-trip the migration: `upgrade head` → `downgrade -1` → `upgrade head`.

There is no `uv` binary in this environment — use the checked-in venv directly.

---

## 4. Done criteria

- All seven endpoints work, auth-gated, user-scoped.
- Migration round-trips cleanly and uses `sa.func.now()`, not `CURRENT_TIMESTAMP`.
- Tests green against the stated baseline; FK/cascade tests genuinely exercise
  the constraint (pragma enabled).
- ADR-128 written; docs/30, docs/04, BACKLOG, CHANGELOG updated.
- One commit, `feat:` prefix, message matching `git log --oneline -10` style,
  ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 5. Report back

What you built, exact pytest and alembic output, the commit SHA, and — most
importantly — **anything in this spec that turned out to be wrong about the
repo, or any judgment call you had to make.** If you disagree with something
here, say so rather than silently working around it. If a doc contradicts this
spec, the doc wins; stop and report the conflict.
