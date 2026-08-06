# Phase 9 Hardening Architecture

# 1. Scope

`docs/30_DEVELOPMENT_ROADMAP.md` listed Phase 9 as five bare words
(Performance, Security, Testing, Bug Fixes, Optimization) with no
architecture doc. A planning pass (2026-08-06) broke it into four
sub-phases and made three product decisions (§2). **All four sub-phases
are now complete** - 9A (§3-§6), 9C (§7), 9D (§8) have their own
sections below; 9B is covered in ADR-133 (`docs/36`) and the roadmap
entry (`docs/30`).

- **9A Public Surface Protection** (this phase) - correct client-IP
  resolution behind the production reverse proxy, per-IP rate limiting on
  the public routes, CORS scoped down to actual usage, baseline security
  headers.
- **9B Auth Hardening** - failed-login lockout (needs new `User` columns +
  a migration), and a decision on `jti`-based access-token revocation
  (BACKLOG.md §4).
- **9C Testing Foundation** - Playwright E2E on the core user flows, plus
  wiring up `pytest-cov` (BACKLOG.md §4 already flags coverage tooling as
  missing).
- **9D Measurement** - `GET /metrics`. This is a **prerequisite**, not a
  parallel workstream: Performance and Optimization are deliberately
  **not scheduled** until something actually measures the thing they'd be
  optimizing. `docs/25_ADMIN_PANEL.md`'s richer monitoring vision (live
  CPU/queue/Redis metrics) stays blocked on this same gap
  (BACKLOG.md §3).

---

# 2. Decisions made 2026-08-06 (record, do not re-litigate)

1. **Self-service email flows are DROPPED, not deferred.** Email
   verification, forgot-password, and reset-password are no longer
   wanted. Phase 8E already closed public registration
   (`allow_public_registration=False` by default, ADR-119) and Phase 8C
   shipped an admin-driven alternative
   (`POST /admin/users/{id}/reset-password` + `must_change_password`) -
   between the two, there is no remaining flow that would ever call a
   self-service email endpoint. The "future email delivery architecture"
   design pass BACKLOG.md §4 called for is removed from the roadmap
   entirely, not just postponed. This is reversible: if public
   registration ever reopens, the email subsystem question comes back
   with it, but building it speculatively now would be inventing
   architecture for a flow this project doesn't have.
2. **Public analysis endpoints stay public**, now protected by a per-IP
   rate limit instead of authentication. This preserves the deliberate
   Phase 3C "public read-only API" decision (docs/04) rather than walking
   it back - the problem being fixed is the *absence of any limit*, not
   the publicness itself.
3. **Frontend testing starts with Playwright E2E** on core flows (9C, not
   part of this phase).

---

# 3. The problem 9A fixes

**Ten route modules are unauthenticated and public** - verified by the
absence of any `get_current_user`/`require_admin`/`require_quota`
dependency anywhere in the module: `technical_analysis`, `smc`,
`market_regime`, `analysis_confidence`, `strategy`, `risk_management`,
`market_data`, `news`, `economic_calendar`, `health`.

Six of those (`technical_analysis`, `smc`, `market_regime`,
`analysis_confidence`, `strategy`, `risk_management`) run a **full engine
pass over ~500 candles per request**. None of the ten had any rate limit
before this phase - ADR-127's quota only ever covered the two
LLM-token-spending endpoints. Production is a **911MB RAM / 2 vCPU box
already ~330MB into swap** (BACKLOG.md §10). An unthrottled loop against
`/analysis/smc/{symbol}` can exhaust it.

## 3.1 A pre-existing bug this phase fixes first

`app/api/v1/routes/admin_system.py` (and, identically, `admin_users.py`
and an inline expression in `auth.py`'s login route) resolved the client
IP as:

```python
def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
```

`docs/27_DEPLOYMENT_ARCHITECTURE.md` puts Nginx in front of the app in
production. Behind a reverse proxy, `request.client.host` is **the
proxy's own address, not the real client**, unless something resolves
the real one. Two consequences, both real:

1. **Every `ip_address` recorded in the audit trail was almost certainly
   wrong in production** - `login_success`, `login_failed`, and all seven
   admin mutations logged the proxy's address instead of the actual
   caller. The column exists for security forensics and could not serve
   that purpose. This predates 9A; it is fixed here because 9A's rate
   limiter depends on the same resolution being correct.
2. **A per-IP rate limit built on top of the unfixed helper would have
   treated all production traffic as a single client** - either tripping
   instantly and taking the site down for everyone, or requiring a limit
   set so high it protects nothing. Building the rate limiter before
   fixing this would have been actively dangerous.

**The fix must not naively trust `X-Forwarded-For`.** Any client can send
that header; parsing it unconditionally would let an attacker bypass the
rate limit by rotating a fake value, which is strictly worse than having
no limit, because it also poisons the audit trail with attacker-chosen
values.

### Chosen approach

Uvicorn already ships a `ProxyHeadersMiddleware` that resolves this
correctly: it rewrites `request.client` from `X-Forwarded-For`/
`X-Forwarded-Proto`, but **only when the immediate TCP peer matches a
configured trusted address** - an untrusted peer's header is ignored
outright. This phase turns it on explicitly rather than relying on
uvicorn's own default (uvicorn 0.52 already defaults
`--proxy-headers=True`/`--forwarded-allow-ips=127.0.0.1`, but depending on
an upstream default that could silently change, or that a different
ASGI runner might not share, was judged not worth the risk):

- `backend/scripts/run_dev.py` now passes `--proxy-headers
  --forwarded-allow-ips <trusted_proxy_ips>` to every `api` mode
  invocation.
- **Production must add the same two flags** to whatever starts uvicorn
  (the systemd `ExecStart` line) - see §4.1. This phase does not deploy
  that change; the operator must apply it (see the build report).
- `Settings.trusted_proxy_ips` (default `"127.0.0.1"`) makes the trusted
  address configurable without editing code, matching how Nginx and the
  app currently run on the same host and connect over loopback.

With this in place, application code never needs to parse a forwarded
header itself. `app/core/client_ip.py`'s `get_client_ip(request)` -
the single shared helper now used by the audit-trail path
(`auth.py`, `admin_users.py`, `admin_system.py`) and the rate limiter
alike, replacing three independent copies of the same logic - stays
exactly as simple as the original: `request.client.host if
request.client else None`. It is correct in both the local (no proxy)
and production (trusted proxy) cases because uvicorn has already resolved
`request.client` correctly by the time the app sees the request.

---

# 4. Design

## 4.1 Client IP resolution

One helper, `app/core/client_ip.py::get_client_ip`, used everywhere an IP
is needed: `AuthenticationService.login`'s audit events, every
`AdminUserService`/`AdminSystemService` mutation's audit events, and the
new per-IP rate limiter (§4.2).

`Settings.trusted_proxy_ips: str = "127.0.0.1"` is the single source of
truth for the trusted immediate peer, passed to uvicorn's
`--forwarded-allow-ips`. `backend/scripts/run_dev.py` reads the same
default (duplicated as a literal, not imported, since that script
deliberately never imports any `app.*` module - see its own docstring)
and can be overridden via an OS-level `TRUSTED_PROXY_IPS` environment
variable.

**Production uvicorn flags required** (operator action, not automated by
this phase - see the build report for the exact command):

```
--proxy-headers --forwarded-allow-ips 127.0.0.1
```

assuming Nginx and the app run on the same host, as `docs/27` describes.
If that topology ever changes (Nginx on a different host/container), the
trusted value must change with it - trusting the wrong peer is exactly
the vulnerability this phase closes.

## 4.2 Per-IP rate limiting

`app/dependencies/rate_limit.py::rate_limit_public` extends
`app/dependencies/quota.py`'s existing Redis fixed-window pattern - no
new library. Differences from ADR-127's per-user quota:

- Keyed by client IP (via `get_client_ip`), not user id.
- Applied at **router-include time** in `app/api/v1/router.py`
  (`include_router(..., dependencies=[...])`), not per-handler - the nine
  affected modules have roughly 30 handlers between them, and decorating
  each individually invites omissions.
- Fails open on any Redis exception, identical rationale to ADR-127: a
  cache outage must never take the public site down over an abuse guard.
- `/health*` is excluded entirely - uptime probes must never be rate
  limited.

Two tiers, not one, because the "engine" and "data" route groups have
genuinely different costs (§3) and different realistic call volumes:

- **`public_engine`**: `technical_analysis`, `smc`, `market_regime`,
  `analysis_confidence`, `strategy`, `risk_management`.
- **`public_data`**: `market_data`, `news`, `economic_calendar`.

Limits (`Settings.public_rate_limit_engine_limit=20`,
`public_rate_limit_data_limit=100`, both per
`public_rate_limit_window_seconds=60`) were sized against measured real
frontend traffic, not guessed:

| Page | Engine calls/load | Data calls/load |
|---|---|---|
| Dashboard | 0 | 3 (`/assets`, `/news`, `/calendar/upcoming`) |
| Markets list | 0 | 1 (`/assets`) |
| Asset detail | 2 (`/analysis/technical`, `/analysis/smc`) | 3 (`/assets/{symbol}`, `/market/{symbol}/candles`, `/market/{symbol}/latest`) |

The asset detail page also polls `candles`/`latest` every 15s while
viewing an m1/m5 timeframe - up to 8 data-tier requests/minute from one
open tab alone. `/signals`, `/watchlists`, and the AI endpoints are
authenticated/quota-guarded separately and are not part of this budget.
20 engine / 100 data requests per 60 seconds per IP comfortably covers
several simultaneous asset-detail tabs with live polling, with headroom
left for React Query retries - while still capping a tight loop against
a single engine endpoint to roughly one request every three seconds
sustained. These are starting points, not calibrated against real
production traffic yet (same caveat as every prior threshold decision in
this project, see ADR-132's Future Review).

---

# 5. CORS and security headers

**CORS** (`app/main.py`) was `allow_methods=["*"]`, `allow_headers=["*"]`,
`allow_credentials=True` - flagged before Phase 1.1 and left unfixed
until now (BACKLOG.md §4). `frontend/services/api-client.ts` is the only
caller; it sends `GET`/`POST`/`PUT`/`PATCH`/`DELETE`, only
`Content-Type` and `Authorization` headers, and never sets `credentials:
"include"` on `fetch()` - so `allow_credentials=True` was never actually
in use. All three are now scoped to exactly that.

**Security headers**: a new `SecurityHeadersMiddleware`
(`app/middleware/security_headers.py`), added alongside the existing
`CorrelationIdMiddleware`, sets `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, and `Referrer-Policy:
strict-origin-when-cross-origin` on every response.

**A full `Content-Security-Policy` is explicitly out of scope for this
phase.** Next.js needs careful CSP work around inline styles and
hydration, and a wrong policy breaks the app silently in the browser
without failing any backend test. Recorded as remaining open in
BACKLOG.md §4.

---

# 6. Out of scope for 9A

Everything listed under 9B/9C/9D in §1, plus: a full CSP (§5); calibrating
the rate limits against real production traffic; anything to do with the
Windows/billiard Celery worker limitation (unrelated, tracked separately
in BACKLOG.md §9).

---

# 7. Phase 9C: Testing Foundation (complete)

Two deliverables, per the 9C build spec: Playwright E2E on the core
flows, and a real backend coverage number via `pytest-cov`. See
ADR-134 for the E2E database/seeding strategy in full.

## 7.1 What is covered

`frontend/tests/e2e/` (Chromium only - cross-browser deferred, low value
at this stage), six flows:

1. Auth - login, session persists across reload, logout, protected
   routes redirect to login afterward.
2. Watchlists CRUD (Phase 7D-B) - create, add/remove an asset, rename,
   delete, in one sequential lifecycle test.
3. Admin user management (Phase 8C/8D) - list loads, search narrows,
   Add/Edit dialogs open. Never exercises delete/role-change against the
   seeded admin the whole suite depends on.
4. Admin maintenance actions (Phase 7D-C) - Refresh News's confirm
   dialog, successful completion, and the resulting audit row.
5. Role gating - the seeded non-admin sees no Admin nav group and is
   redirected away from `/admin/*`.
6. A regression guard for 9A's riskiest failure mode (rate limits set
   below real usage): a normal multi-page walk asserts zero `429`
   responses and zero CORS console errors.

Determinism: `workers: 1`, `fullyParallel: false` - tests share one
seeded backend, and the current suite's assertions were not designed
against concurrent mutation of that shared state (judgment call, see the
9C build report). No `waitForTimeout`/arbitrary sleeps anywhere - only
Playwright's web-first assertions, with a raised global `expect` timeout
(10s, 15s for the shared login helper) to absorb `next dev`'s
compile-on-first-request cost per route, not to paper over flakiness.

`pytest-cov` is configured (`backend/pyproject.toml`'s
`[tool.coverage.*]`, `source = ["app"]`). **Measured total: 93%**
(`cd backend && .venv/Scripts/python.exe -m pytest -q --cov=app
--cov-report=term`). **Enforced in CI only as of Phase 9C-B**
(`--cov-fail-under=90`, §7.3) - the local default stays gate-free.

## 7.2 What is not covered

- Component/unit tests (Vitest/RTL) - the planning decision was E2E
  first (§1).
- Cross-browser E2E (Firefox/WebKit) - Chromium only for now.
- Any flow beyond the six above - notably no AI Analysis/AI Chat/Signals
  E2E coverage yet, since those either call the (mocked) AI orchestrator
  or have no equivalent manual-verification precedent driving this
  phase's flow selection.

## 7.3 CI integration (Phase 9C-B, ADR-135)

Wired in the very next phase, as planned. `.github/workflows/ci.yml` gained
a third job, `e2e`, alongside the existing `backend`/`frontend` jobs -
**no Postgres in that runner**, contrary to what this section originally
predicted: the E2E suite runs entirely against the dedicated SQLite
`e2e.db` (ADR-134), so the job only needs Python (via `uv`), Node, and a
Chromium install (`npx playwright install --with-deps chromium`, cached
on the Playwright version).

**Server startup uses Playwright's `webServer` config** (`frontend/
playwright.config.ts`), gated on `process.env.CI` so the local workflow
above is completely unaffected - a developer's manually-started servers
are never touched by this. In CI, Playwright itself starts the E2E-mode
backend (`uv run python scripts/run_dev.py api --e2e-db`) and the
frontend (`npm run start`, i.e. a **production build**, not `next dev`),
polling `/api/v1/health` for backend readiness rather than an arbitrary
sleep - that endpoint deliberately has no DB/Redis dependency and is
excluded from rate limiting (§4.2).

**`NEXT_PUBLIC_API_URL` is exported before the CI workflow's `npm run
build` step**, not before the server-start step - Next.js bakes
`NEXT_PUBLIC_*` values into the client bundle at build time, so setting
it any later would silently do nothing. `BACKEND_CORS_ORIGINS` is set
explicitly to the frontend's serving origin for the same reason CORS
already required care locally (§7's "Backend test coverage" setup notes
above) - a mismatch fails every browser API call with no useful login
error.

**E2E is a required (blocking) check, not advisory** - see ADR-135 for
the full reasoning and the conditions under which that should be
revisited.

**Coverage is now enforced in CI only.** `--cov-fail-under=90` was added
to the `backend` job's `pytest` invocation (docs/06 §21's already-
documented goal, BACKLOG.md §4) - the local default stays gate-free so a
developer running `pytest` casually is never blocked by it.

**What CI cannot verify from a local session**: whether the job actually
passes on GitHub's real Ubuntu runners. Browser install, path handling,
and service startup timing can all differ from every local Windows run
this phase's verification was based on - see the Phase 9C-B build report
for the exact local results and what to watch on the first real push.

# 8. Phase 9D: Measurement (complete)

`GET /metrics` (ADR-136) - the prerequisite §1 flagged: Performance and
Optimization stay unscheduled until something actually measures what
they'd be optimizing.

## 8.1 What is covered

Prometheus text-format exposition via `prometheus_client`
(`app/api/v1/routes/metrics.py`, `app/middleware/metrics.py`):

- `http_requests_total{method, route, status}` and
  `http_request_duration_seconds{method, route}` (a histogram) for
  every request, instrumented by `MetricsMiddleware`.
- The client library's default process/GC collectors (`python_gc_*`,
  `process_*`, `python_info`) - free, not hand-rolled.

**Labeled by matched route template, never the raw path** - the
cardinality landmine the build spec called out. FastAPI records the
matched route on `request.scope["route"]` once routing resolves;
`_route_template()` reads `route.path` from it. **Discovered while
building this**: in the FastAPI version pinned here, `route.path` only
ever reflects prefixes a router applied to *itself*
(`APIRouter(prefix="/analysis/technical")`), never a prefix passed as
an argument to `include_router(router, prefix=...)` - the outermost
`/api/v1` (applied exactly that second way in `app/main.py`) never
appears in the label. This does not reintroduce the cardinality problem
(the label is still a fixed template, not a per-request path) and every
production route already self-prefixes, so labels read like
`/analysis/technical/{symbol}` rather than
`/api/v1/analysis/technical/{symbol}` - cosmetically shorter, not less
safe. Verified directly: two requests to the same route template with
different path params produce exactly one series with the count summed
(Phase 9D build report §8 has the pasted proof). Paths matching no
route at all collapse into a single `"unmatched"` bucket, for the same
cardinality reason.

Access control is fail-closed (`app/dependencies/metrics_auth.py`):
`settings.metrics_auth_token` defaults to `""`, and an unconfigured
deployment gets a 404, not 403 or an empty 200 - the endpoint does not
advertise its own existence. A static bearer token, not `require_admin`
- see ADR-136 for why. Excluded from 9A's per-IP rate limiting
(`app/api/v1/router.py`, same as `/health*`) and from its own request
metrics (a scrape must not inflate the numbers it reports).

This unblocks `GET /admin/system` (ADR-116), which was explicitly
limited to liveness + counts pending this gap.

## 8.2 What is not covered

- **Celery worker/beat metrics** - separate processes, need a
  multi-process registry or pushgateway (its own design pass); the
  worker also cannot run on this Windows sandbox at all (BACKLOG.md
  §9), so it could not have been verified here regardless.
- **CPU/memory/queue-length gauges** (`docs/25` §12-13) - process-level
  resource metrics already come from the client library's default
  collectors (§8.1); queue length needs Celery introspection, tied to
  the worker-metrics gap above.
- **Surfacing metrics in `GET /admin/system` or the Admin UI** -
  follow-up work, not this phase (BACKLOG.md §3).
- Alerting, dashboards, and any new infrastructure - there is no
  Prometheus/Grafana deployed; the near-term consumer is manual `curl`
  inspection and the `GET /admin/system` unblock above, not a scraper.
