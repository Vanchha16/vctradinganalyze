# Build Spec — Cleanup: Dev-Runtime Vendor Isolation

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Size:** Small-to-medium. One real gap, plus a secrets-hygiene fix found alongside it.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Rule 9 — never
   expose secrets — is directly relevant to Item D.
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Do NOT read, print, modify, or commit `backend/.env`.** Its secret values
   must never appear in a commit, a log, a test, or your report.
5. **No production behaviour may change.** Nothing here may alter how the
   deployed app loads configuration. If your approach requires editing
   `app/config/settings.py`'s `model_config`, it is the wrong approach — stop
   and report.

---

## 1. The problem

`backend/tests/conftest.py` (commit `dab7e42`) isolates the **pytest session**
from ambient `.env` by writing safe values into `os.environ` before any `app.*`
import, relying on pydantic-settings' precedence (OS env > `.env` file).

**That fix does not reach anything else that runs locally.** A manually started
`uvicorn`, `celery worker`, or `celery beat` reads the real `backend/.env` —
including real vendor API keys — so any local run can call a metered external
service for real.

This has now caused two incidents in two phases:

- **Twelve Data free-tier quota exhausted** (observed "1037–1052 credits used,
  limit 800"). Tests contributed, but a locally running `celery beat` executing
  `collect_market_data_task` on schedule is the likelier bulk consumer — that
  task is scheduled every 60s/300s for M1/M5.
- **A real NewsAPI call went out** during Phase 7D-C manual verification, when
  `POST /admin/news` was exercised against a `uvicorn` started normally.

Both were caught by attentiveness, not by design. The goal of this task is to
make the safe path the **default** path for local development.

---

## 2. Item A — One canonical "safe local config", shared

`conftest.py` currently hardcodes this list:

```
MARKET_DATA_PROVIDERS      -> ["mock"]
NEWS_PROVIDERS             -> ["mock"]
ECONOMIC_CALENDAR_PROVIDERS-> ["mock"]
TELEGRAM_PROVIDERS         -> ["mock"]
TWELVE_DATA_API_KEY        -> ""
NEWS_API_KEY               -> ""
ECONOMIC_API_KEY           -> ""
TELEGRAM_BOT_TOKEN         -> ""
OPENAI_API_KEY             -> ""
```

**This list must exist in exactly one place** and be used by both the test suite
and the local runtime launchers (Item B). A second copy will drift the first
time a provider is added, and the drift will be silent.

Suggested home: a small module such as `backend/scripts/local_env.py` that
defines the mapping and exposes a function to apply it to `os.environ`.

**Critical constraint, carried over from `conftest.py`:** this module must
import **no `app.*` module**, and callers must apply it **before** any `app.*`
import. `app/config/__init__.py` builds a module-level `settings` singleton on
first import; if that happens first, applying the overrides afterwards is a
silent no-op. Document this in the module docstring the way `conftest.py`
already does — read that docstring first, it explains the constraint well.

Note `backend/scripts/` has no `__init__.py` today. If import mechanics get
awkward, **an acceptable fallback is keeping the two copies but adding a test
that asserts they are identical**, so drift fails loudly. Sharing is preferred;
a proven no-drift guarantee is the actual requirement.

Update `conftest.py` to consume the shared definition rather than its own
literals, preserving its existing ordering comments.

---

## 3. Item B — Safe local launchers

Add launcher scripts under `backend/scripts/` (matching the existing
`create_admin.py` / `seed_dev_data.py` / `seed_prod_assets.py` convention —
Python, cross-platform) that apply Item A's overrides and then start:

1. **the API server** (`uvicorn app.main:app --reload`)
2. **the Celery worker**
3. **the Celery beat scheduler**

One script with a mode argument or three small scripts — your call; pick
whichever reads better next to the existing scripts and say which you chose.

Requirements:
- Overrides applied **before** any `app.*` import (§2).
- Each script must **print, on startup, which providers are active**, so it is
  obvious at a glance that mocks are in force. A silent safe mode is only half
  the fix — the operator needs to be able to tell the two modes apart.
- There must be a documented way to opt **into** real providers deliberately
  (e.g. an explicit `--real-providers` flag or an env var), because sometimes
  you genuinely do want to smoke-test a real vendor. **Default is mock. Real
  must be an explicit, visible choice**, never the default and never silent.

Do **not** delete or break the existing ways of starting these processes —
this is an additive, safer path, not a forced migration.

---

## 4. Item C — Documentation

The safe path is worthless if nobody knows it exists.

- Document the launchers in `README.md` (or `CONTRIBUTING.md` — check which
  already covers local setup and follow that; do not create a third location).
  Cover: how to start each process safely, how the override mechanism works in
  one sentence, and how to deliberately opt into real providers.
- `BACKLOG.md` — record both incidents (Twelve Data quota exhaustion, the live
  NewsAPI call) and this mitigation. §11 is the market-data section; §16 is
  news. Note explicitly that `conftest.py` covers tests only and that the
  launchers cover the runtime, so a future reader understands why both exist.
- `docs/30_DEVELOPMENT_ROADMAP.md` needs no change — this is not a phase.

**No ADR** unless you make a genuine architectural decision. A dev-tooling
script is not one. If you end up changing how configuration loads, that *is*
one — but per §0.5 that means you have taken the wrong approach.

---

## 5. Item D — Secrets hygiene in `.env.example` (found while scoping this)

`.env.example` is tracked in git. Line 54 (`TELEGRAM_BOT_TOKEN=`) contains what
appears to be a **real Telegram bot token**, not a placeholder — it has the
structure of a live token, not the `your_api_key`-style placeholder used
elsewhere in the same file.

This is almost certainly the token `docs/30`'s Phase 7E-D entry describes as
**compromised and not to be reused**. It is committed to the repository.

**Do:**
- Replace that value with a placeholder matching the file's own convention
  (e.g. `your_telegram_bot_token`), consistent with how `OPENAI_API_KEY` and
  the others are written on nearby lines.
- Scan the rest of `.env.example` for any other real-looking value and replace
  it the same way. Report anything you find.
- Note in your report that **the token must be revoked by the operator via
  BotFather** — a placeholder in the file does not invalidate a token that is
  already in git history. This is an operator action, not something you do.

**Do NOT:**
- Reproduce the token value in your report, in a commit message, or in any
  file.
- Attempt to rewrite git history, use `git filter-branch`/`filter-repo`, or
  force-push. That is a destructive, coordination-requiring operation and is
  explicitly **out of scope** — flag it as a decision for the operator instead.

---

## 6. Verification — run these and report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Known baseline: 952 passed, 0 failed** as of commit `6b7856a`. The suite is
green — any failure is yours. If you added a no-drift test (§2 fallback), it
must pass.

**Prove the launchers actually work.** Start the API server via the new script
and confirm from its startup output that mock providers are active. Then
exercise an endpoint that would otherwise reach a vendor — `POST /admin/news`
is the exact one that leaked last time — and confirm from the response and
logs that it ran against the mock provider and **no external call was made**.
Report what you actually observed, not "it works."

Do the equivalent sanity check for the worker/beat launchers: confirm they
start and report mock providers. You do **not** need to leave beat running.

**Do NOT test the `--real-providers` path against a live vendor.** Confirm the
flag is wired by inspection and by the startup banner only — the entire point
of this task is not spending vendor quota.

```
cd backend && .venv/Scripts/python.exe -m alembic check
```
Expect only the pre-existing `telegram_accounts` drift. No migration here.

---

## 7. Done criteria

- One canonical safe-config definition, used by both tests and launchers — or a
  test that provably prevents drift between two copies.
- Launchers for API/worker/beat that default to mock providers and announce it.
- Deliberate opt-in to real providers exists, is documented, and is never the
  default.
- `README`/`CONTRIBUTING` documents the safe local workflow.
- `.env.example` contains no real credential.
- `BACKLOG.md` records both incidents and the mitigation.
- `backend/.env` untouched, unread, uncommitted.
- Production config loading byte-identical.
- Suite green at 952 + any new tests, 0 failed.
- **One commit**, `fix:` or `chore:` prefix (your judgment — say which and why),
  matching `git log --oneline -10` style, ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 8. Report back

What you built and which structure you chose for Items A and B (and why), exact
pytest/alembic output, **what you actually observed when you exercised
`POST /admin/news` through the safe launcher**, what you found in `.env.example`
(described, never quoted), the commit SHA, and — most importantly — **anything
in this spec that turned out to be wrong about the repo, or any judgment call
you had to make.** If you disagree with something here, say so rather than
silently working around it.

**State plainly whether any external network call occurred during your
verification.** If one did, say so — that is exactly the failure this task
exists to prevent, and knowing it happened is more valuable than a clean report.
