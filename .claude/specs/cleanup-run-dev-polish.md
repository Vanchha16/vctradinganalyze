# Build Spec — Cleanup: `run_dev.py` Polish + Windows Worker Note

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Size:** Small. Three independent items, none architectural.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.**
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Do NOT read, print, modify, or commit `backend/.env`** or
   `frontend/.env.local`. Both are local, gitignored, and none of this task's
   business.
5. **No ADR.** None of these are architectural decisions. If you think one is,
   stop and report rather than writing it.

---

## Item A — The startup banner is invisible when output is redirected

`backend/scripts/run_dev.py` prints its provider-mode banner (lines ~83–95)
using bare `print()`. Python fully buffers stdout when it is not a TTY, so
**piping or redirecting the launcher to a log file shows no banner** until the
buffer flushes — which for a long-running server may be never.

This defeats the launcher's own safety requirement: the banner exists so the
operator can tell mock mode from `--real-providers` mode at a glance. It is
least visible exactly when someone is running unattended and most needs it.

This was discovered during the Phase 7D-C/9ccd471 verification (the banner did
not appear until `-u` was passed) and diagnosed as Python buffering — correctly,
but the script should not depend on the caller remembering `-u`.

**Fix:** make the banner flush unconditionally. Either `flush=True` on those
`print()` calls, or reconfigure stdout line-buffering once at the top of the
banner function. Pick one and be consistent — do not mix.

**Verify by actually redirecting**, e.g. run the launcher with stdout piped to a
file, and confirm the banner appears there promptly. Do not verify only on a
terminal, which buffers differently and will pass either way.

---

## Item B — Add a `--port` option

**Correction to an earlier assumption: `run_dev.py`'s hardcoded `8000` is
correct, not a bug.** 8000 is this project's canonical backend port — it is the
default in `frontend/services/api-client.ts:4`, in `.env.example:15`, and in
`docker-compose.yml` (both the `uvicorn` command and the `${BACKEND_PORT:-8000}`
mapping). A local `frontend/.env.local` pointing at 8001 is a machine-specific
override, not the project convention.

So **do not change the default.** The gap is that the launcher offers no way to
match a non-default local setup, which during 7D-D verification forced a
temporary edit of a gitignored config file just to run the app.

**Fix:** add an optional `--port` argument (default `8000`) to the existing
`argparse` parser, and use it for the `api` mode's `uvicorn --port` value.

Note the structural wrinkle: the commands currently live in a module-level
`_COMMANDS` dict with the port baked in as a literal. You will need to build the
`api` command after parsing args — a small function or building the dict inside
`main()` both work. Keep the `worker`/`beat` entries unchanged; `--port` is
meaningless for them, so either ignore it there or reject it with a clear error.
Say which you chose.

Include the port in the startup banner so it is unambiguous which one is live.

Update the `README.md` section that documents these commands (around lines
76–99) to show the new flag alongside the existing `--real-providers` example.

---

## Item C — Record the Windows Celery worker failure

`run_dev.py worker` starts, connects to Redis, registers all 8 tasks, and then
fails with `PermissionError: [WinError 5] Access is denied` inside billiard's
Windows multiprocessing semaphore handling. This is a **pre-existing
Windows/billiard incompatibility**, not caused by the launcher — running
`celery worker` directly in this environment fails identically.

It was observed and correctly scoped as out-of-task during the `9ccd471` work,
but never written down. The consequence matters and belongs in the backlog:
**the Celery worker cannot run on this Windows development machine at all.**
Beat runs fine and dispatches, but nothing consumes the queue — so automatic
signal generation, Telegram delivery, and scheduled market-data collection
cannot be tested end-to-end locally. Production is Linux and unaffected.

**Fix:** add an entry to `BACKLOG.md` **§9** (Development Environment
Differences — its stated purpose is exactly this kind of local-vs-other
behavioural difference; it already holds the SQLite/Postgres notes and the
`.env` test-bleed entry). Follow the section's existing entry style: bold lead
sentence, then the detail and the consequence.

Cover: the exact error and where it originates, that it is pre-existing and
reproduces without the launcher, what it blocks locally, that production is
unaffected, and that the workaround if end-to-end worker testing is ever needed
is WSL/Linux or `--pool=solo` (**note the latter as an untested suggestion, not
a verified fix — do not claim you validated it unless you actually do**).

**Do not attempt to fix the billiard issue.** It is out of scope.

---

## Verification — run these and report exact output

```
cd backend && .venv/Scripts/python.exe -m pytest -q
```
**Known baseline: 952 passed, 0 failed** as of commit `509e590`. No test change
is expected from this task — any failure is yours.

Launcher checks:
- `run_dev.py api --port <some other port>` starts on that port and the banner
  says so.
- `run_dev.py api` still defaults to 8000.
- Banner appears promptly **when stdout is redirected to a file** (Item A).
- `--real-providers` still short-circuits the overrides — **verify by
  inspection and the banner only. Do NOT run it against a live vendor.**

You do not need to run `worker`/`beat` for this task beyond confirming `--port`
did not break their invocation. **Do not re-trigger the billiard failure
deliberately** — it is already characterised.

No frontend change is expected. If you touch nothing under `frontend/`, you may
skip the npm checks; say so explicitly in your report.

---

## Done criteria

- Banner flushes; verified with redirected stdout, not just a terminal.
- `--port` works, defaults to 8000, shown in the banner, documented in `README.md`.
- `worker`/`beat` invocation unchanged.
- `BACKLOG.md` §9 records the Windows worker limitation.
- No ADR, no migration, no `.env`/`.env.local` file touched or committed.
- Suite still 952 passed, 0 failed.
- **One commit**, `chore:` or `fix:` prefix (your judgment — say which and why;
  this is closer to tooling polish than to fixing a live incident), matching
  `git log --oneline -10` style, ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Report back

What you changed, how you verified the banner flush **specifically under
redirection**, which approach you took for `--port` on the `worker`/`beat`
modes, exact pytest output, the commit SHA, and **anything in this spec that
turned out to be wrong about the repo, or any judgment call you had to make.**
If you disagree with something here, say so rather than silently working around
it.
