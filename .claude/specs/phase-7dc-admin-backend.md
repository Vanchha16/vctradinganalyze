# Build Spec — Phase 7D-C: Admin Backend (rescoped)

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Most relevant here:
   never violate an accepted ADR; documentation is the source of truth; **never
   invent architecture**; prefer improving existing files over creating new ones.
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **No new schema, no migration.** Every endpoint here reads existing tables or
   calls existing pipelines. If you think a table or column is needed, **STOP and
   report it.**
5. **Backend only.** 7D-D (the frontend pages) is a separate phase. Do not touch
   `frontend/`.

---

## 1. Scope — five endpoints, not seven

`docs/58` §3.2 lists seven `/admin/*` endpoints. **Two are already built** and
must not be re-implemented:

- `GET /admin/users` — Phase 8C (`AdminUserService`, 9 endpoints)
- `GET /admin/logs` — Phase 8F (`AdminAuditLogService`, ADR-129)

**Your scope is the remaining five:**

```
GET  /admin/signals      paginated signal list, admin view
GET  /admin/system       DB/Redis liveness + today's counts
GET  /admin/analytics    daily active users + recommendation distribution
POST /admin/news         manual news refresh
POST /admin/maintenance  {"action": "refresh_news" | "refresh_calendar"} only
```

Read `docs/58` §3.2 in full for the authoritative description of each, plus
**ADR-115** (RBAC reuse), **ADR-116** (`/admin/system` is not real telemetry),
and **ADR-117** (`/admin/maintenance` is limited to two actions).

---

## 2. Two documentation conflicts — already resolved, do not re-litigate

### 2.1 `POST /admin/news` was NOT "decided against"

`BACKLOG.md` §16 states that `POST /admin/news` was "**explicitly decided
against**, not just deferred vaguely," citing docs/04. **That summary is
wrong.** The source it cites — `docs/04_API_SPECIFICATION.md:567` — actually
says:

> "Out of scope for Phase 5A: `POST /admin/news` (deferred - not built)"

*Deferred*, not rejected. And `docs/58` §3.2 (later, approved, ADR-backed)
explicitly puts it in scope for this phase. The Phase 5A reasoning BACKLOG
records — "would be the first auth-gated route in the otherwise-fully-public
analysis-route surface" — is also now moot: this project has many auth-gated
routes today (all of `/admin/*`, plus the quota'd AI endpoints).

**Resolution: build it.** As part of this phase, **correct BACKLOG §16's
inaccurate "decided against" wording** to match what docs/04 actually says and
note that docs/58 brought it into scope.

### 2.2 `POST /admin/news` and `POST /admin/maintenance` overlap

`POST /admin/news` and `POST /admin/maintenance {"action": "refresh_news"}` do
the same thing. That redundancy is in `docs/58`'s own approved spec.

**Resolution: build both** (docs are source of truth; do not drop one), but
**they must share a single implementation** — one service method, two route
entry points. Do not write the ingestion trigger twice. Record the overlap in
ADR-130 so a future reader knows it was noticed and deliberate, not an
oversight.

---

## 3. Endpoint detail

All five require **`require_admin`** from `app/dependencies/rbac.py` (Phase 8B).
Do not write a new role check and do not modify `get_current_user`.

Put the routes in a new `app/api/v1/routes/admin_system.py` (or similar),
mirroring `admin_users.py`/`admin_logs.py`'s structure. Register in
`app/api/v1/router.py`.

### 3.1 `GET /admin/signals`

Reuse `SignalRepository.find_paginated` / `count_filtered` — they already exist
(Phase 6B). Match `GET /admin/users`' pagination convention exactly (same param
names, same envelope). Read it and copy; do not invent a second convention.

**Check before building:** `docs/58` describes this as "all users, not just
caller's." Verify whether `Signal` is actually user-scoped at all — signals are
generated per *asset*, and `signal_bookmarks` is the per-user table. If signals
are already global, say so in your report and in ADR-130; the docs/58 phrasing
may be a misframing rather than a requirement.

### 3.2 `GET /admin/system`

**This is deliberately NOT live telemetry** (ADR-116). No CPU, memory,
queue-depth, or Prometheus metrics — none of that infrastructure exists
(BACKLOG §3).

Reuse the checks already in `app/api/v1/routes/health.py`'s `/health/ready`:
a `SELECT 1` against the DB and a Redis `ping()`. Plus simple `COUNT` queries
for today's activity (signals generated, AI analyses run).

**Must not 500 when a dependency is down.** The whole point is reporting
liveness, so a Redis outage should render as `redis: down` in a 200 response,
not crash the endpoint. `/health/ready` lets exceptions propagate because it is
a probe; this endpoint is a dashboard and must degrade gracefully. Test this.

### 3.3 `GET /admin/analytics`

Per `docs/58` §3.2, exactly two figures:
- **Daily active users** — distinct `UserSession.user_id` today
- **Recommendation distribution** — `GROUP BY` on `signals.recommendation`

`docs/25` §15 lists a much longer wishlist (most viewed assets, confidence
distribution, average AI response time, etc.). **Do not build those** — there
is no view-tracking or latency-recording infrastructure anywhere. Record the
gap in ADR-130 as deferred.

### 3.4 `POST /admin/news` and `POST /admin/maintenance`

Both call the **existing** ingestion pipelines directly — do not write new
ingestion logic:
- `app/services/news_ingestion_pipeline.py`
- `app/services/economic_calendar_ingestion_pipeline.py`

These are the same pipelines the Celery tasks `news_sentiment.ingest` and
`economic_calendar.ingest` invoke (`app/workers/news_sentiment_tasks.py`,
`economic_calendar_tasks.py`) — read those task bodies first; they show you
exactly how to construct and run each pipeline.

`POST /admin/maintenance` accepts **only** `{"action": "refresh_news"}` or
`{"action": "refresh_calendar"}` (ADR-117). Any other action must be rejected
with a validation error — use a Pydantic enum/`Literal`, not a free string with
an `if` chain. Do **not** add "restart workers", "clear cache", "rebuild
indicators", or "recalculate confidence": none has a concrete implementation to
call, and this project's engines are stateless so there is nothing to rebuild.

**Known tradeoff you must record, not fix:** `docs/58` specifies calling the
pipeline *directly*, which makes this a blocking HTTP request that runs a full
ingestion inline — potentially many seconds, and a candidate for a gateway
timeout. Dispatching the existing Celery task instead (returning `202`) would
avoid that, but it deviates from approved architecture. **Follow docs/58 and
call directly.** Record the tradeoff in ADR-130, naming Celery dispatch as the
shape of the fix if it becomes a real problem.

### 3.5 Audit the two write endpoints

`POST /admin/news` and `POST /admin/maintenance` are actions, not reads. Every
admin mutation in this project already writes an `AuditLog` row —
`AdminUserService._audit` does it for all seven of its operations. Follow that
established pattern: **both endpoints must write an audit row** recording the
acting admin, the action, and the outcome.

This is consistency with an existing pattern, not new architecture. Phase 8F
just shipped the reader for these rows, so they will be visible immediately.

---

## 4. Tests

New tests under `backend/tests/`. Read `tests/test_admin_logs_api.py` (Phase
8F) and `tests/test_rbac.py` first — follow their structure and fixtures.

Note `backend/tests/conftest.py` now forces mock providers and blank API keys,
and a network guard fails any test that opens a non-loopback socket. **Your
tests must not attempt real network calls** — the ingestion endpoints must be
exercised against the mock providers.

Cover at minimum:
- each of the five endpoints returns its documented shape
- **every one rejects a non-admin with 403 and an unauthenticated caller with 401**
- `/admin/signals` pagination and total count are correct
- **`/admin/system` returns 200 with a degraded field when Redis is unreachable**,
  rather than raising (§3.2)
- `/admin/analytics` returns correct DAU and distribution against seeded data,
  including the empty case (no sessions, no signals — must not divide by zero
  or return null-shaped garbage)
- `POST /admin/maintenance` **rejects an unknown action** with a validation error
- both write endpoints **create an `AuditLog` row** with the correct actor
- the news/calendar refresh endpoints work against mock providers

---

## 5. ADR-130

Append to `docs/36_DECISION_RECORDS.md` after ADR-129, matching the neighbouring
ADRs' full format (Title / Status / Context / Decision / Reason / Alternatives
Considered / Trade-offs / Future Review — read ADR-127 through ADR-129 for style
and wrap width).

Must cover:
- The response contracts are **inferred** — `docs/04` lists these paths with no
  params or shapes (same inference category as ADR-128/ADR-129).
- The `POST /admin/news` vs `/admin/maintenance` overlap (§2.2) and the shared
  implementation.
- The correction of BACKLOG §16's "decided against" wording (§2.1).
- `/admin/system` is liveness + counts, not telemetry (reaffirming ADR-116), and
  that real observability stays blocked on the `/metrics` gap (BACKLOG §3).
- `/admin/analytics` implements two of `docs/25` §15's figures; the rest are
  deferred for lack of view-tracking/latency infrastructure.
- The synchronous-ingestion tradeoff (§3.4).
- Whatever you find about signal user-scoping (§3.1).

---

## 6. Verification — run these and report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Known baseline: 931 passed, 0 failed** as of commit `dab7e42`. The suite is
now fully green — **any** failure is yours and must be fixed or reported. Do not
accept a red suite.

```
cd backend && .venv/Scripts/python.exe -m alembic check
```
Expect only the pre-existing `telegram_accounts` drift (BACKLOG §26). This phase
adds no migration — anything else means you changed a model you shouldn't have.

**Manual check.** Backend running, logged in as an admin. Report what you
actually observed for each of the five endpoints (curl or equivalent is fine —
there is no frontend for these yet). Include:
- `POST /admin/maintenance` with `refresh_news`, and with an invalid action
- the resulting audit rows appearing in `GET /admin/logs`

Use the local dev environment. **Do NOT test against production**, and be aware
that a real news/calendar refresh against real providers consumes vendor quota —
keep to the mock providers locally.

---

## 7. Done criteria

- Five endpoints live, all `require_admin`-gated, matching `GET /admin/users`'
  pagination conventions.
- No migration, no model change, no new ingestion logic.
- `POST /admin/news` and `/admin/maintenance` share one implementation and both
  write audit rows.
- Unknown maintenance actions rejected by schema validation.
- `/admin/system` degrades gracefully instead of 500ing.
- ADR-130 written; `docs/04` filled in for all five contracts; `docs/30` marks
  7D-C complete; `BACKLOG.md` §16 corrected per §2.1; `CHANGELOG.md` updated.
- Suite green at 931 + your new tests, 0 failed.
- **One commit**, `feat:` prefix, matching `git log --oneline -10` style, ending
  with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 8. Report back

What you built, exact pytest/alembic output, what you actually observed per
endpoint in the manual check, what you found about signal user-scoping (§3.1),
the commit SHA, and — most importantly — **anything in this spec that turned out
to be wrong about the repo, or any judgment call you had to make.** If you
disagree with something here, say so rather than silently working around it. If
a doc contradicts this spec, the doc wins; stop and report the conflict.
