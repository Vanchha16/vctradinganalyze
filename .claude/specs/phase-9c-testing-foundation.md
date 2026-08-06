# Build Spec — Phase 9C: Testing Foundation

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Depends on:** 9A/9B complete (head `edb43f3`).
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.**
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Do NOT deploy, SSH anywhere, or run anything against production.** E2E tests
   run against a local backend started via `backend/scripts/run_dev.py` only.
5. **Do NOT read, print, or commit `backend/.env`.**
6. **Do not modify application code to make tests pass.** If a test reveals a
   real bug, report it — do not fix it inside this phase unless it blocks the
   test from running at all, and say so clearly if you do.

---

## 1. Scope and non-scope

Two deliverables:
- **A.** Playwright E2E covering the core flows (§3–§5)
- **B.** `pytest-cov` producing a real backend coverage number (§6)

**Explicitly NOT in scope:**
- **CI integration.** Wiring Playwright into `.github/workflows/ci.yml` needs
  browsers, a running backend, a served frontend, and a database in the runner —
  a substantial job that would double this phase. **Local-first, CI next.**
  See §7, which requires you to record this as the immediate follow-up, because
  a suite nobody runs automatically will rot.
- **Component/unit tests** (Vitest/RTL). The planning decision was E2E first.
- **A coverage gate.** Measure now, decide a threshold later (§6).

---

## 2. The hard problem: how E2E tests get an account

Read this before designing anything.

**Public registration is closed** — Phase 8E, `allow_public_registration=False`,
`POST /auth/register` returns `403`. And `backend/scripts/create_admin.py`
**refuses to run once any `super_admin` exists** (a deliberate bootstrap guard,
ADR-123). So the tests cannot register a user, and cannot reuse the admin
bootstrap.

They also must not depend on whatever happens to be in `backend/dev.db` — that
file has been mutated repeatedly by manual verification this session (including
the dev super-admin's password being overwritten during 7D-C, and a throwaway
`lockout-9b-verify@example.com` account added in 9B). Tests built on it would be
non-deterministic and order-dependent.

**Required approach:**

- A dedicated seed script, e.g. `backend/scripts/seed_e2e_data.py`, following the
  conventions of the existing `seed_dev_data.py` — read it first. It must create
  a known admin user, a known non-admin user, and deterministic asset/candle data
  the tests can assert against.
- It must target a **separate database** (e.g. an `e2e.db` SQLite file via a
  `DATABASE_URL` override), never `dev.db`. `run_dev.py`'s existing environment
  mechanism is how you point the backend at it — extend that rather than
  inventing a second config path.
- It must be **idempotent**: re-running resets to a known state rather than
  accumulating or failing.
- **Safety requirement:** the script must refuse to run against anything that
  is not an obviously-local database. A seed script that could point at
  production and create a known-password admin is a serious hazard. Make the
  refusal explicit and test it.
- Test credentials must be obviously fake (e.g. `e2e-admin@example.invalid`) and
  clearly marked as test-only. **Never reuse a real password**, never read one
  from `.env`.

---

## 3. Playwright setup

Add Playwright to `frontend/` as a dev dependency, with config, a `tests/e2e/`
directory, and npm scripts (`test:e2e`, plus a headed/debug variant).

**Note:** `.playwright-mcp/` at the repo root is gitignored MCP tooling and is
**unrelated** to this. Do not confuse them or reuse that directory.

Requirements:
- **Chromium only** for now. Cross-browser can come later; it multiplies runtime
  for little value at this stage.
- `baseURL` configurable, defaulting to the frontend dev server. Note the app's
  API URL comes from `frontend/.env.local`
  (`NEXT_PUBLIC_API_URL`, currently `http://localhost:8000/api/v1`) — the tests
  must work against whatever backend that points at, and you must document the
  expected local setup.
- **Deterministic waits only.** Use Playwright's web-first assertions
  (`expect(locator).toBeVisible()` etc.) and auto-waiting. **No arbitrary
  `waitForTimeout`/sleep calls** — they are the primary source of flaky E2E
  suites and will make this whole investment worthless.
- Traces/screenshots on failure, so a CI failure later is diagnosable.
- Playwright browser binaries must not be committed; ensure `.gitignore` covers
  whatever it drops in the working tree.

---

## 4. Flows to cover

These are exactly the walkthroughs that have been done **by hand every phase**
this session. Automating them is the point of 9C.

1. **Auth** — log in as the seeded admin; land on the dashboard; reload and stay
   logged in; log out; confirm a protected route redirects to login afterwards.
2. **Watchlists CRUD** (Phase 7D-B) — empty state → create → appears with count 0
   → open detail → add an asset → count updates → remove → rename → delete.
3. **Admin user management** (Phase 8C/8D) — list loads; search/filter narrows;
   open the Add/Edit dialogs. **Do not exercise destructive actions** (delete,
   role change) against the seeded admin the tests depend on — use the seeded
   non-admin as the target if you test them at all.
4. **Admin maintenance actions** (Phase 7D-C) — Refresh News shows its
   confirmation dialog with the quota warning, confirming succeeds, and an audit
   row appears in Audit Logs. Mock providers make this safe and fast.
5. **Role gating** — the seeded non-admin sees no Admin nav entry and is
   redirected away from an `/admin/*` URL.

**Additionally, one regression guard worth its weight:**

6. **No unintended rate limiting during normal use.** Walk Dashboard → Markets →
   an asset detail → Watchlists → an Admin page and assert **no request returns
   429** and no CORS error appears in the console. This directly protects 9A's
   riskiest failure mode — limits set below real usage — which is currently
   guarded only by a manual check I performed once by hand.

---

## 5. Determinism and hygiene

- Each test must be **independently runnable** and must not depend on another
  test's leftovers. Prefer creating what a test needs and cleaning up after, or
  re-seeding between runs.
- **Do not exhaust 9A's rate limits.** The engine tier is 20 requests/60s per IP.
  A suite that hammers analysis endpoints will trip it and fail confusingly.
  If you hit this, say so — the right answer is likely tests that do not
  repeatedly load engine-backed pages, **not** raising the production limit.
- The backend must be started via `run_dev.py` so **mock providers are in force**
  and no vendor is ever called. State in your report how you started it.

---

## 6. `pytest-cov`

BACKLOG §4 has tracked this since Phase 2A; every phase since has said "verified
by inspection" instead of producing a number. `docs/06` §21 and `docs/31` §10 set
90%/95% goals that have never been measured.

- Add `pytest-cov` to the appropriate dependency group in `backend/pyproject.toml`
  and configure it (`[tool.coverage.*]`), excluding what should be excluded
  (migrations, `__init__` re-exports, scripts — use judgment and say what you chose).
- Add a convenient invocation and document it.
- **Report the actual coverage number.** That number is the deliverable.
- **Do NOT set a failing threshold in this phase.** Nobody knows what the number
  is yet; a gate that fails on day one gets disabled and never re-enabled.
  Measure first; choosing a threshold is a follow-up decision informed by the
  real figure.
- `uv` is unavailable in this sandbox (BACKLOG §4/§11) — you may not be able to
  regenerate `uv.lock` properly. If so, say so plainly and note it needs doing in
  a real dev environment, exactly as the `httpx`/`email-validator` entries record.

---

## 7. Documentation

- `README.md` (or `CONTRIBUTING.md` — follow whichever already covers local
  setup) — how to seed the E2E database, start the backend and frontend, run the
  E2E suite, and run coverage.
- `docs/60_PHASE_9_HARDENING_ARCHITECTURE.md` — fill in 9C: what is covered,
  what is not, and **CI integration as the explicit next step** with the reason
  it was deferred.
- `BACKLOG.md` — close the `pytest-cov` gap (§4) with the measured number; record
  the "no frontend test suite" entries (§23/§24/§25) as partially resolved,
  noting that component/unit tests remain unbuilt.
- `docs/30` — mark 9C.
- `CHANGELOG.md` — entry for 9C. **Also note: no CHANGELOG entry exists for 9A**
  (found during 9B). Add one covering 9A's three commits while you are here.
- **ADR-134** only if you make a genuine architectural decision — the E2E
  database/seeding strategy (§2) probably qualifies, since it introduces a second
  database and a new seeding path. Use judgment; if you write one, match the
  neighbouring ADRs' format.

---

## 8. Verification — report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Baseline: 979 passed, 0 failed** (`edb43f3`). Adding `pytest-cov` must not
change this count.

Coverage run — report the **exact total percentage** and the invocation used.

```
cd frontend && npm run typecheck && npm run lint && npm run build
```

**The E2E suite itself:** run it and report exact pass/fail per spec, plus total
runtime. Then **run it a second time** and confirm identical results — a suite
that passes once and flakes on the second run is not done. Report both runs.

If any E2E test reveals a **real application bug**, report it as a finding.
Do not fix application code in this phase (§0.6).

---

## 9. Done criteria

- Playwright installed and configured; `npm run test:e2e` runs the suite.
- All six flows in §4 covered and passing, **twice in a row**.
- E2E runs against a dedicated seeded database, never `dev.db`; seed script is
  idempotent and refuses non-local targets.
- No arbitrary sleeps anywhere in the tests.
- `pytest-cov` configured; **actual coverage number reported**; no threshold gate.
- Backend suite still 979 passed, 0 failed.
- Docs updated including the missing 9A CHANGELOG entry.
- **Two commits**: E2E foundation, then coverage tooling. `test:` or `chore:`
  prefix as appropriate, each ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 10. Report back

Both commit SHAs, the **measured backend coverage percentage**, exact E2E results
for **both** runs plus runtime, how you started the backend, what your seeding
strategy was and how the safety refusal works, any real application bug the tests
found, whether `uv.lock` could be regenerated, and — most importantly —
**anything in this spec that turned out to be wrong about the repo, or any
judgment call you had to make.**

**If you cannot make the suite pass reliably twice in a row, say so plainly
rather than adding waits to force it green.** A flaky E2E suite is worse than no
E2E suite: it trains everyone to ignore failures, and it will be ignored exactly
when it catches something real.
