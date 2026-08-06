# Build Spec — Phase 9A: Public Surface Protection

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Priority:** Highest open item. The production site is live and currently
exposed (§2).
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Documentation is the
   source of truth — this phase writes its scoping doc *before* its code (§3).
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Do NOT deploy, SSH anywhere, or touch the production box.** This phase
   produces code plus a documented deployment change the operator applies. Say
   clearly in your report what the operator must do.
5. **Do NOT read, print, or commit `backend/.env`.**
6. **Start the local backend only via `backend/scripts/run_dev.py api`** so mock
   providers are in force.

---

## 1. Context — Phase 9 scope, decided 2026-08-06

`docs/30` lists Phase 9 as five words (Performance, Security, Testing, Bug
Fixes, Optimization) with no architecture doc. A planning pass established this
breakdown and three product decisions. **You are building 9A only**, but you
must record the whole breakdown (§3).

- **9A Public Surface Protection** (this phase) — correct client-IP resolution,
  per-IP rate limiting on the public routes, CORS scoped down, security headers.
- **9B Auth Hardening** — failed-login lockout (needs `User` columns +
  migration), decision on `jti` access-token revocation.
- **9C Testing Foundation** — Playwright E2E on core flows, plus `pytest-cov`.
- **9D Measurement** — `GET /metrics`. A **prerequisite** for any Performance /
  Optimization work, which is deliberately **not scheduled** until something
  measures it.

**Decisions made (record these, do not re-litigate):**
1. **Self-service email flows are DROPPED, not deferred.** Email verification,
   forgot-password, and reset-password are no longer wanted: Phase 8E closed
   public registration and Phase 8C shipped admin-driven reset
   (`POST /admin/users/{id}/reset-password` + `must_change_password`). The
   email subsystem design pass is removed from the roadmap. Reversible if
   registration ever reopens.
2. **Public analysis endpoints stay public**, protected by a per-IP rate limit —
   preserving the deliberate Phase 3C "public read-only API" decision.
3. **Frontend testing starts with Playwright E2E** on core flows (9C, not now).

---

## 2. The problem this phase fixes

**Ten route modules are unauthenticated and public** — verified by absence of
any `get_current_user`/`require_admin`/`require_quota` dependency:
`technical_analysis`, `smc`, `market_regime`, `analysis_confidence`, `strategy`,
`risk_management`, `market_data`, `news`, `economic_calendar`, `health`.

Most run **full engine passes over ~500 candles per request**. None has any rate
limit — ADR-127's quota covers only the two LLM endpoints. Production is a
**911MB RAM / 2 vCPU box already ~330MB into swap** (BACKLOG §10). A loop
against `/analysis/smc/{symbol}` can exhaust it.

### 2.1 A pre-existing bug you must fix first

`app/api/v1/routes/admin_system.py:36` defines:

```python
def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
```

`docs/27` puts **Nginx in front of the app** in production. Behind a reverse
proxy, `request.client.host` is **the proxy's address (loopback), not the real
client**. Two consequences:

1. **Every `ip_address` in the audit trail is probably wrong in production** —
   `login_success`, `login_failed`, and all seven admin mutations record the
   proxy IP. The column exists for security forensics and currently cannot serve
   that purpose. This predates 9A; you are fixing it because 9A depends on it.
2. **A per-IP rate limit built on this would treat all traffic as one client** —
   either instantly tripping and taking the site down for everyone, or set so
   high it protects nothing. **Catastrophic if built naively.**

**The fix must not naively trust `X-Forwarded-For`.** Any client can send that
header, so parsing it unconditionally lets an attacker bypass the rate limit by
rotating a fake value — strictly worse than no limit, because it also poisons
the audit trail. Trust it **only when the immediate peer is a known proxy.**

Recommended approach: run uvicorn with `--proxy-headers` and
`--forwarded-allow-ips` set to the trusted proxy, so Starlette resolves
`request.client.host` correctly and existing call sites keep working unchanged.
Make the trusted-proxy value **configurable via settings**, defaulting to
something safe for local development.

If you take a different approach, it must still satisfy: correct client IP
behind Nginx, unspoofable from outside, and no behaviour change when running
locally without a proxy. Explain your choice in the ADR.

---

## 3. Deliverable 1 — `docs/60_PHASE_9_HARDENING_ARCHITECTURE.md`

**Write this before the code**, following the structure and tone of
`docs/58_WATCHLISTS_ADMIN_ARCHITECTURE.md` and
`docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md` — read both first; they are the
precedent for a phase-scoping architecture doc.

Cover: the §1 breakdown (9A–9D) with what is in and out of each; the three
decisions with their reasoning; the §2 problem statement including the IP bug;
and an explicit statement that Performance/Optimization are unscheduled pending
9D. Note that `docs/25`'s richer monitoring vision stays blocked on the same
`/metrics` gap (BACKLOG §3).

Also update:
- `docs/30_DEVELOPMENT_ROADMAP.md` — replace Phase 9's five bare words with the
  9A–9D sub-phase structure, mark 9A in progress, reference docs/60.
- `BACKLOG.md` §4 and §6 — mark the email-dependent items **dropped** per
  decision 1, with the reasoning. Do not silently delete them; record why they
  closed, consistent with how §1 preserved the response-envelope reasoning.
- `BACKLOG.md` — record the audit-trail IP bug (§2.1) as found-and-fixed here.

**Commit this documentation separately, before the code commits.**

---

## 4. Deliverable 2 — correct client IP + per-IP rate limiting

### 4.1 Client IP

Move IP resolution into one shared helper (the current one is private to
`admin_system.py` while `authentication_service.py` also records IPs — check how
that one obtains its value and unify them). Add the trusted-proxy setting.
Update `backend/scripts/run_dev.py` and document the production uvicorn flags.

### 4.2 Rate limiting

Extend the existing `app/dependencies/quota.py` pattern — **do not add a new
library** (`slowapi` or otherwise); Redis and the working fixed-window
implementation are already there. Reuse `QuotaExceededException` so 429s keep
the standard `{"error", "message"}` envelope.

Key differences from ADR-127's per-user quota:
- Keyed by **client IP**, not user id.
- Applied at the **router level** for the public modules, not per-handler —
  decorating ~30 handlers individually invites omissions.
- **Must fail open on Redis failure**, same as ADR-127.
- **Limits must be generous and configurable per settings.** This ships to a
  live site; the goal is stopping abuse, not throttling real users. The frontend
  makes several calls per page load — Dashboard alone composes five widgets from
  separate endpoints. **Work out the realistic per-page-load request count and
  set limits well above it.** State your reasoning in the report.
- **Exclude `/health*`** — uptime probes must never be rate limited.

Consider a lower limit for the expensive engine routes than for cheap reads
(`/assets`, `/market/*`) if that falls out naturally, but do not over-engineer;
one sensible tier is acceptable if two adds complexity without clear benefit.

---

## 5. Deliverable 3 — CORS and security headers

**CORS** (`app/main.py:32-33`) is still `allow_methods=["*"]`,
`allow_headers=["*"]` with `allow_credentials=True` — flagged before Phase 1.1
and never fixed (BACKLOG §4). The API surface is stable now. Scope both lists to
what is actually used; determine that from the real route surface and the
frontend's `api-client.ts`, not by guessing. **Verify the frontend still works
afterwards** — an over-tightened header list breaks it silently in the browser
while every backend test still passes.

**Security headers:** add a middleware alongside the existing
`CorrelationIdMiddleware` setting at minimum `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY` (or `frame-ancestors`), and `Referrer-Policy`.

**A full `Content-Security-Policy` is NOT in scope** — Next.js requires careful
CSP work (inline styles, hydration) and a wrong policy breaks the app in the
browser without failing any test. Record it in BACKLOG as remaining open.

---

## 6. Tests

Follow `tests/test_quota.py` and `tests/test_rbac.py`. Cover:
- under the limit passes; at the limit returns 429 with the standard envelope
- the window resets
- **fails open when Redis raises**
- **limits are per-IP** — IP A exhausting its budget does not affect IP B
- **`/health` is never rate limited**
- **client IP resolves correctly with proxy headers present from a trusted
  peer, and is NOT trusted from an untrusted peer** — this is the security-
  critical case; test both directions
- security headers present on responses

---

## 7. ADR-132

Append to `docs/36_DECISION_RECORDS.md` after ADR-131, matching the neighbouring
format. Cover: per-IP limiting for public routes and how it differs from
ADR-127's per-user quota; the trusted-proxy IP resolution and why naive
`X-Forwarded-For` parsing was rejected; the audit-trail IP bug this corrects;
CORS scoping; security headers with CSP explicitly out of scope; and that limits
are hand-picked starting points, not calibrated — the same caveat every prior
threshold ADR in this project carries.

---

## 8. Verification — report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Baseline: 952 passed, 0 failed** (commit `3247bd1`). Any failure is yours.

```
cd backend && .venv/Scripts/python.exe -m alembic check
```
Only the pre-existing `telegram_accounts` drift. **This phase adds no migration.**

```
cd frontend && npm run typecheck && npm run lint && npm run build
```

**Manual — required.** Backend via `run_dev.py api`, frontend running:
- Log in and load Dashboard, Markets, an asset detail page, Watchlists, and an
  Admin page. **Confirm nothing is rate limited during normal use** — this is
  the single most important check. If normal browsing trips the limit, the
  limit is wrong.
- Confirm a deliberate burst against one analysis endpoint **does** get a 429
  with the standard envelope.
- Confirm `/health` still responds under that burst.
- Confirm the browser console shows **no CORS errors** anywhere in the app.

Report what you actually observed, and the request counts you measured for a
normal page load.

---

## 9. Done criteria

- `docs/60` written; docs/30 and BACKLOG updated; **committed first**.
- Client IP resolves correctly behind a proxy and is unspoofable; the shared
  helper is used by both the audit path and the rate limiter.
- Public routes rate limited per-IP, fail-open, `/health` excluded, limits in
  settings and generous enough for real use.
- CORS scoped down with the frontend verified working.
- Security headers present; CSP recorded as out of scope.
- ADR-132 written. No migration. No new dependency.
- Suite green at 952 + new tests.
- **Three commits**: docs, then IP + rate limiting, then CORS + headers. `docs:`
  then `feat:`/`fix:` as appropriate, each ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 10. Report back

All three commit SHAs, exact test/build output, the limits you chose **and the
measured per-page-load request counts behind that choice**, what you observed in
the manual check, **the exact production uvicorn flags the operator must apply**
(this phase is not complete on the live box until they do), and — most
importantly — anything in this spec that turned out to be wrong about the repo,
or any judgment call you had to make.

**If you cannot make client-IP resolution genuinely unspoofable, stop and report
rather than shipping a bypassable limit.** A rate limit an attacker can evade by
setting a header is worse than none, because it also corrupts the audit trail.
