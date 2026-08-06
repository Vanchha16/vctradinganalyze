# Build Spec — Cleanup: Test Isolation, ErrorCard Hint, `.claude/` Tracking

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Size:** Small. Three unrelated fixes bundled because each is a few lines.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.**
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Do NOT modify `backend/.env`.** Do not read its secret values, do not print
   them, do not commit them. Item A fixes the tests, not the environment file.
5. **No production behaviour may change.** Item A must affect the test session
   only. If your approach changes how the running app loads configuration,
   it is the wrong approach — stop and report.

---

## Item A — Isolate the test suite from ambient `.env` (the important one)

### The problem

`backend/app/config/settings.py:86` sets
`model_config = SettingsConfigDict(env_file=".env", ...)`, and
`app/config/__init__.py` exports a module-level `settings` singleton. So the
moment any test imports an app module, real local configuration is loaded —
including `MARKET_DATA_PROVIDERS=["twelve_data"]` and a real
`TWELVE_DATA_API_KEY`.

Two consequences, both live today:

1. **Two tests fail on this machine and cannot pass**, while passing in CI
   (which has no `.env`):
   - `tests/test_market_data_dependencies.py::test_get_market_data_providers_returns_rate_limited_mock`
     — asserts the default resolves to `mock`, but `.env` says `twelve_data`.
   - `tests/test_market_data_tasks.py` — same root cause.
   A suite that can never be green is a suite where a real regression hides.

2. **The test suite makes real, quota-consuming calls to the live Twelve Data
   API.** A recent run observed "1037–1052 credits used, limit 800" — the free
   tier's daily quota, exceeded. Tests must never touch a metered external
   service.

**There is currently no `conftest.py` anywhere under `backend/`** — confirm
this yourself. That is why nothing neutralises the ambient environment today.

### The fix

Create `backend/tests/conftest.py`.

**Mechanism.** `pydantic-settings` precedence is: init args > OS environment
variables > `.env` file > field defaults. So setting the relevant variables in
`os.environ` overrides `.env` without touching the file or the app's config
code.

**Timing is the critical part.** `settings` is a module-level singleton built
at first import of `app.config.settings`. Your `os.environ` writes must happen
at `conftest.py` **module top level, before any `app.*` import** — pytest
imports `conftest.py` before collecting test modules, so this is early enough,
but only if you don't import app code above it. Add a comment saying so; it is
exactly the kind of ordering constraint someone later "tidies" and breaks.

**What to override.** At minimum, force the providers back to their documented
test defaults so no real vendor is ever constructed:
- `MARKET_DATA_PROVIDERS` → `["mock"]`
- Any other provider list with a real implementation — check
  `settings.py` for `news_providers`, economic-calendar providers, and any
  Telegram/AI provider selection, and neutralise each the same way.
- Blank out real API keys (`TWELVE_DATA_API_KEY` and the equivalents) so a
  missed path fails loudly rather than silently calling out.

Use the documented default values from `settings.py` field defaults — do not
invent new ones.

If a `get_settings.cache_clear()` call is needed anywhere for the overrides to
take effect, add it, and explain why in a comment.

### Recommended, not required — a network guard

A `conftest.py` autouse fixture that raises if a test opens a real socket would
prevent this whole class of problem recurring. Implement it **only if it is
cheap and does not break existing tests** — note that tests using
`httpx.MockTransport` do not open sockets and must keep working.

**If adding the guard causes any pre-existing test to fail, remove it and
report that instead.** Do not spend time making 900+ tests pass around a
safety net; the `.env` isolation above is the required fix.

### Expected result

Baseline before your work (commit `0204f97`): **929 passed, 2 failed**.
After this fix both failures should pass: **931 passed, 0 failed.**

If either still fails, you have not fully isolated the environment — do not
paper over it by editing the assertions. The tests are correct; the
configuration leak is the defect.

### Documentation

Update `BACKLOG.md` §9's entry about this failure to record it as **resolved**,
noting the mechanism. Also record the Twelve Data quota-exhaustion observation
(§11 is the market-data section) — that tests were consuming real credits is
worth knowing even after it stops happening.

---

## Item B — `ErrorCard`'s 404 hint is hardcoded for market data

`frontend/features/dashboard/components/error-card.tsx:6-9` shows this hint for
**any** `resource_not_found` error, anywhere in the app:

> "This asset likely has no candle data yet for the selected timeframe."

It is correct on a Markets page and misleading everywhere else — it now appears
on the Watchlist detail page's 404, and it is wrong in production too.

**Fix:** make the hint caller-supplied rather than hardcoded. Add an optional
prop (e.g. `notFoundHint?: string`) used only when the error is a
`resource_not_found`; when not supplied, render no hint rather than a wrong one.

Then pass the existing asset-specific text from the Markets/chart call sites
that genuinely want it, so nothing regresses there. Find every `ErrorCard`
usage before changing it, and keep the change additive.

No ADR — this is a bug fix, not an architectural decision.

---

## Item C — `.claude/` tracking

The `.claude/` directory is currently untracked in full. It holds two different
kinds of thing and must not be treated as one:

- `.claude/specs/*.md` — build specs for phases 7D-A, 7D-B, 8F, and this one.
  **Track these.** They are project history: how each phase was scoped and what
  constraints applied.
- `.claude/settings.local.json` — local machine configuration (permission
  allowlists, MCP server toggles). **Do not commit.** Add it to `.gitignore`.

Add a `.gitignore` entry for `.claude/settings.local.json` specifically — not
for `.claude/` as a whole, which would exclude the specs too. Check the file's
existing structure and put it under the appropriate existing section (there is
already a `# Tooling` section near the end).

If `.claude/` contains anything else, list it in your report and leave it
untracked rather than guessing.

---

## Verification — run these and report exact output

Backend:
```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
Target: **931 passed, 0 failed.** Report the exact numbers.

```
cd backend && .venv/Scripts/python.exe -m alembic check
```
Expect only the pre-existing `telegram_accounts` drift (BACKLOG §26). This
change adds no migration.

Frontend:
```
cd frontend && npm run typecheck && npm run lint && npm run build
```
**Do NOT run `npm run format:check`** — it fails on ~55 pre-existing files
(BACKLOG §23), unrelated to this work.

Manual (Item B): confirm a Markets page 404 still shows the asset-specific
hint, and that a Watchlist detail 404 no longer shows it. Report what you saw.

Also confirm with `git status` that `.claude/specs/` is now tracked and
`.claude/settings.local.json` is ignored.

---

## Done criteria

- `backend/tests/conftest.py` exists; both previously-failing tests pass; no
  test constructs a real market-data/news/AI provider or calls a live API.
- Production config loading is unchanged — `settings.py` behaviour outside
  tests is identical.
- `backend/.env` untouched and uncommitted.
- `ErrorCard`'s hint is caller-supplied; Markets keeps its wording, other pages
  show no wrong hint.
- `.claude/specs/` tracked, `.claude/settings.local.json` ignored.
- `BACKLOG.md` §9 marked resolved, §11 records the quota observation;
  `CHANGELOG.md` updated.
- **One commit**, `fix:` prefix, matching `git log --oneline -10` style, ending
  with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Report back

Exact pytest numbers before and after, what you overrode in `conftest.py` and
why, whether you added the network guard (and if not, why not), what you
observed for Item B, the commit SHA, and **anything in this spec that turned
out to be wrong about the repo, or any judgment call you had to make.** If you
disagree with something here, say so rather than silently working around it.

**Do not report success on Item A unless the suite is genuinely 0 failed.** If
something remains red, say so plainly and explain what is still leaking.
