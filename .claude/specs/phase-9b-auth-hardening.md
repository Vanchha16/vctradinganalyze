# Build Spec — Phase 9B: Auth Hardening

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Depends on:** 9A (commits `3e7c9f8`, `0a347fc`, `42b6306`).
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.**
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Do NOT deploy or touch the production box.**
5. **Do NOT read, print, or commit `backend/.env`.**
6. **Start the local backend only via `backend/scripts/run_dev.py api`.**
7. This phase **does** add a migration — the first since `f3a9c1d2e5b7`. See §4's
   landmine before writing it.

---

## 1. Scope

Three items, in priority order. **Item A is the highest-value one and is not the
one the backlog leads with** — read §2 before assuming lockout is the main event.

- **A.** Close the disabled-user access-token window (§2)
- **B.** Failed-login lockout (§3, §4) — `docs/23` §17, BACKLOG §4
- **C.** Record the `jti` denylist decision (§5) — no code

Read `docs/60_PHASE_9_HARDENING_ARCHITECTURE.md` (written in 9A) for where this
sits, and `docs/23_AUTHENTICATION_AND_RBAC.md` §17 for the lockout requirement —
be warned it is four bullet points with no thresholds (§3.1).

---

## 2. Item A — a disabled user keeps working for up to 15 minutes

`app/dependencies/auth.py::get_current_user` decodes the token and calls
`user_service.get_user_by_id(user_id)` — **it already loads the full `User` row
from the database on every authenticated request** — then returns it without
checking `is_active` or `deleted_at`. Its docstring says so explicitly:
*"No authorization (active/verified/role) checks are made here."*

That was a defensible Phase 2C decision. **Phase 8C invalidated it.** Admins can
now disable and soft-delete users, and `AuthenticationService.login` rejects
both — but only *at login*. An already-issued access token keeps working until
natural expiry (15 minutes, `jwt_access_expire_minutes`). So an admin responding
to a compromised or malicious account has no way to actually cut it off.

**Fix:** have `get_current_user` reject a user whose `is_active` is false or
whose `deleted_at` is set, reusing the existing exception the login path raises
for the same condition (`InactiveAccountException` — check how
`authentication_service.py` uses it and stay consistent, including its
deliberate refusal to distinguish "deleted" from "inactive" to the caller).

**This costs nothing.** The `User` object is already in memory; it is a field
check, not a new query, not a Redis call, no added latency.

**But it is a real contract change** and must be treated as one:
- It contradicts `get_current_user`'s docstring and `docs/37` §10's documented
  "authenticates only, never authorizes" design. **Update both.**
- It needs an ADR (§6).
- **Check every existing test that builds a user fixture** — any test using an
  inactive user with an authenticated route will now get rejected. Fix the
  fixtures, do not weaken the check.

---

## 3. Item B — failed-login lockout

### 3.1 `docs/23` §17 specifies almost nothing

It lists four bullets: *Temporary Lock, CAPTCHA (Future), Notify User, Log
Event*. No threshold, no lock duration, no reset rule.

- **"Temporary Lock"** is the one load-bearing word: the lock **must expire on
  its own**. See §3.3.
- **"CAPTCHA (Future)"** — out of scope, stays deferred.
- **"Log Event"** — already done. `login()` audits `login_failed` today; make
  sure a lockout event is distinguishable in the audit trail.
- **"Notify User" is now unbuildable and unwanted.** It requires email, and the
  Phase 9 planning pass **dropped the email subsystem entirely** (docs/60,
  BACKLOG §4/§6). Record it as dropped for that reason — do not build email.

Everything else is inferred and needs the ADR to say so.

### 3.2 Schema

Two columns on `users`, the names BACKLOG §4 already anticipates:
`failed_login_attempts` (integer, default 0, not null) and `locked_until`
(nullable timezone-aware datetime).

### 3.3 Behaviour

- Count consecutive failed password attempts per user; reset to zero on any
  successful login.
- At the threshold, set `locked_until` to now + the lock duration.
- While locked, reject login **without** verifying the password.
- **The lock must auto-expire** — once `locked_until` has passed, login is
  attemptable again and the counter resets. This is what makes §3.1's
  "Temporary" load-bearing, and it is also the recovery path: **there is
  exactly one admin account on a fresh deployment and
  `backend/scripts/create_admin.py` refuses a second run**, so a permanent lock
  would be unrecoverable without DB surgery. Do not add an admin-unlock
  endpoint; auto-expiry is sufficient and simpler.
- Threshold and duration **go in settings**, defaulted conservatively. They are
  hand-picked starting points — say so in the ADR, as every prior threshold ADR
  in this project does.
- A locked account must not be distinguishable from a wrong password to an
  unauthenticated caller — reuse the existing `InvalidCredentialsException`
  rather than adding a "your account is locked" message that confirms the
  address exists.

### 3.4 A related weakness — decide and record

`login()` currently reads:

```python
if user is None or not verify_password(password, user.password_hash):
```

When the email does not exist, `verify_password` is **never called**. Argon2id
verification is deliberately slow, so a nonexistent address returns
measurably faster than a real one — a timing oracle for **user enumeration**,
which matters more now that registration is closed and every account is an
admin-provisioned target.

The standard mitigation is to verify against a dummy hash when the user is
missing, so both paths cost the same. **Either fix it here or record it in
BACKLOG with the reasoning — your judgment, but say which you chose and why.**
Do not silently leave it unaddressed.

---

## 4. Migration — the landmine

This is the first migration since `f3a9c1d2e5b7` and it **alters an existing
table**, which is exactly the case this project has been bitten by:

- **You MUST use `op.batch_alter_table("users")`.** Plain `op.add_column` for a
  constraint, or `op.create_foreign_key`, raises
  `NotImplementedError: No support for ALTER of constraints in SQLite dialect`.
  Recorded as institutional knowledge in BACKLOG §26 — `f3a9c1d2e5b7` hit this
  exact wall.
- **Check `server_default` rendering before committing.** Autogenerate compiles
  it against the connected dialect; generating against SQLite has twice produced
  `sa.text('(CURRENT_TIMESTAMP)')`, invalid on Postgres. BACKLOG §5/§9.
- Round-trip it: `upgrade head` → `downgrade -1` → `upgrade head`.

**A second landmine, which has now bitten this codebase twice:** comparing
`locked_until` (read from the DB) against `datetime.now(UTC)` will raise
`TypeError: can't subtract offset-naive and offset-aware datetimes` on SQLite,
which returns naive datetimes for `DateTime(timezone=True)` columns. There is an
established fix used in **two** places already — `authentication_service.
_as_aware_utc` and `news_sentiment/dedup_detector._as_aware_utc`. **Reuse that
pattern; do not write a third variant.** Consider whether it should be promoted
to one shared helper and say so in your report.

---

## 5. Item C — the `jti` decision (documentation only)

Access tokens carry an unused `jti` claim. BACKLOG §4 has tracked a Redis
denylist for revocation since Phase 2A.

**Decision: stays deferred.** Item A closes the practical risk — a disabled or
deleted account is now cut off on its next request, which was the real exposure.
A denylist would add a Redis read to **every authenticated request** to close a
narrower remaining window (e.g. a role *downgrade* mid-session). That is not
worth the per-request cost today.

Record this in the ADR and update BACKLOG §4's entry so it reflects the reduced
risk rather than the original framing. **Do not build the denylist.**

---

## 6. ADR-133

Append to `docs/36_DECISION_RECORDS.md` after ADR-132, matching the neighbouring
format. Cover: Item A as a deliberate narrowing of `get_current_user`'s
authenticate-only contract, and why Phase 8C made it necessary; the lockout
threshold/duration as inferred beyond `docs/23` §17, with auto-expiry as the
recovery mechanism given `create_admin.py`'s single-run guard; that "Notify
User" is dropped because the email subsystem is dropped; the `jti` deferral and
its reasoning; and whatever you decided on §3.4.

Also update: `docs/37_AUTHENTICATION_FLOW.md` §10 (the authenticate-only claim),
`docs/23` §17 if it needs a note, `docs/30` (9B), `BACKLOG.md` §4, `CHANGELOG.md`.

---

## 7. Tests

Follow `tests/test_rbac.py` and the existing auth tests. Cover:
- **Item A:** an authenticated request with a valid token for a user who has
  since been disabled is rejected; likewise `deleted_at` set; an active user is
  unaffected
- lockout triggers at the threshold, and not before
- a locked account is rejected **without** the password being verified
- **the lock auto-expires** and the counter resets
- a successful login resets the counter
- a locked account is indistinguishable from a wrong password in the response
- the lockout is visible in the audit trail
- if you fixed §3.4, a test that both paths do the equal work

---

## 8. Verification — report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Baseline: 970 passed, 0 failed** (after 9A). Item A may legitimately break
existing fixtures — **fix the fixtures, never the check**, and report exactly
which ones you touched and why.

```
cd backend && .venv/Scripts/python.exe -m alembic upgrade head
cd backend && .venv/Scripts/python.exe -m alembic downgrade -1
cd backend && .venv/Scripts/python.exe -m alembic upgrade head
cd backend && .venv/Scripts/python.exe -m alembic check
```
Expect only the pre-existing `telegram_accounts` drift. Confirm your new
migration contributes no drift and uses `sa.func.now()` if it defaults anything.

```
cd frontend && npm run typecheck && npm run lint && npm run build
```
(Expected untouched — say so if you changed nothing there.)

**Manual:** trip the lockout against the local dev DB with a throwaway account
you create for the purpose, confirm the lock, confirm auto-expiry, and confirm
the audit rows. **Do not lock out the dev super-admin** — if you do, say so
plainly and document the recovery you used.

---

## 9. Done criteria

- Disabled/soft-deleted users are cut off at the next authenticated request.
- Lockout works, auto-expires, resets on success, and leaks nothing to an
  unauthenticated caller.
- Migration uses `batch_alter_table`, round-trips, no new drift.
- No third `_as_aware_utc` copy.
- ADR-133 written; docs/37 §10 corrected; docs/23, docs/30, BACKLOG, CHANGELOG
  updated.
- `jti` denylist **not** built; its deferral recorded with current reasoning.
- Suite green at 970 + new tests.
- **Two commits**: Item A (contract change + docs), then Item B (lockout +
  migration). `feat:`/`fix:` as appropriate, each ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 10. Report back

Both commit SHAs, exact pytest/alembic output, **which existing test fixtures
Item A broke and how you fixed them**, your decision on §3.4 and why, the
threshold/duration you chose and your reasoning, what you observed in the manual
lockout test, whether you promoted `_as_aware_utc` to a shared helper, the
commit SHAs, and **anything in this spec that turned out to be wrong about the
repo, or any judgment call you had to make.**

If Item A's check breaks a large number of tests, that is a signal worth
reporting rather than grinding through — it would mean inactive-user fixtures
are load-bearing somewhere unexpected, and I want to know that.
