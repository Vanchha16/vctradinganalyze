# ClaudeTrading AI

> AI-powered trading analysis platform built with Clean Architecture, FastAPI, Next.js, and explainable AI.

! Important do not do any action outside this folder
---

## 📖 Overview

ClaudeTrading AI is an intelligent market analysis platform that combines:

- 📈 Technical Analysis
- 🏦 Smart Money Concepts (SMC)
- 📰 Financial News Sentiment
- 📅 Economic Calendar Analysis
- 🤖 AI Reasoning
- 🛡 Risk Management
- 📊 Confidence Scoring

The platform **does not execute trades**. Its purpose is to provide transparent, evidence-based market analysis and trading recommendations.

---

## 🏗 Project Status

**Current Phase:** Architecture & Planning ✅

Implementation has not started yet.

See the roadmap:

- `docs/30_DEVELOPMENT_ROADMAP.md`

---

## 📚 Documentation

Start here:

- `PROJECT_MASTER_INDEX.md`

The complete software architecture is documented in the `docs/` directory.

---

## 🛠 Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy
- Redis
- Celery

### AI

- OpenAI GPT
- Structured Prompting
- Evidence-Based Reasoning

---

## 🚀 Getting Started

### Running the backend locally, safely

Use `backend/scripts/run_dev.py` instead of starting `uvicorn`/`celery` directly:

```
cd backend
.venv/Scripts/python.exe scripts/run_dev.py api      # FastAPI dev server
.venv/Scripts/python.exe scripts/run_dev.py worker   # Celery worker
.venv/Scripts/python.exe scripts/run_dev.py beat     # Celery beat scheduler
```

By default this forces every vendor provider (market data, news, economic
calendar, Telegram, and the corresponding API keys) to the project's mock
implementations, regardless of what `backend/.env` contains, by setting
environment variables that `pydantic-settings` prefers over the `.env` file
(the exact override set lives in `backend/scripts/local_env.py`, shared with
the test suite's `conftest.py`). Each run prints a banner showing which mode
is active. A manually-started `uvicorn`/`celery` process reads real `.env`
values with no such protection - two real vendor calls have already leaked
this way (see `BACKLOG.md` §11/§16), so prefer this script for local work.

If you genuinely need to smoke-test a real vendor, opt in explicitly - it is
never the default:

```
.venv/Scripts/python.exe scripts/run_dev.py api --real-providers
```

The `api` mode defaults to port 8000 (this project's canonical port). Pass
`--port` to match a machine-specific override instead - it has no effect on
`worker`/`beat`:

```
.venv/Scripts/python.exe scripts/run_dev.py api --port 8001
```

The old direct commands (`uvicorn app.main:app --reload`,
`celery -A app.workers.celery_app.celery_app worker`, `... beat`) still work
unchanged - this is an additive, safer alternative, not a replacement.

Implementation otherwise follows the roadmap defined in the architecture documents.

### Running the E2E suite (Phase 9C)

The Playwright suite (`frontend/tests/e2e/`) runs against a **dedicated
seeded database, `backend/e2e.db`** - never `backend/dev.db`. See ADR-134
(`docs/36`) for why. Four steps, in order:

```
# 1. Seed the E2E database (idempotent - safe to re-run any time to reset)
cd backend
.venv/Scripts/python.exe scripts/seed_e2e_data.py

# 2. Start the backend pointed at it (mock providers, never a real vendor call)
.venv/Scripts/python.exe scripts/run_dev.py api --e2e-db

# 3. Start the frontend (reads NEXT_PUBLIC_API_URL from frontend/.env.local -
#    make sure it points at the backend port from step 2)
cd frontend
npm run dev

# 4. Run the suite
npm run test:e2e            # headless
npm run test:e2e:headed     # headed, watch it click through the app
npm run test:e2e:debug      # Playwright's step-through debugger
npm run test:e2e:report     # open the last run's HTML report
```

`E2E_BASE_URL` overrides the frontend URL Playwright targets (default
`http://localhost:3000`) if you're running the frontend on a non-default
port. Chromium only for now; traces/screenshots/video are captured on
failure only (`playwright.config.ts`). Re-run step 1 between sessions to
reset to a known state - the suite itself is self-cleaning (each test
either mutates nothing or undoes its own mutation), but re-seeding is the
fastest way back to a known-good starting point if a run is interrupted
mid-test.

If you run the frontend on a port other than `3000` (the backend's
default `Settings.backend_cors_origins`), also set
`BACKEND_CORS_ORIGINS='["http://localhost:<port>"]'` as an environment
variable before step 2, or the browser's requests will fail CORS.

**This suite also runs in CI** (Phase 9C-B, `.github/workflows/ci.yml`'s
`e2e` job) as a required, blocking check (ADR-135) - it starts both
servers itself (`frontend/playwright.config.ts`'s `webServer`, active only
when `CI` is set) against a **production build** (`next build` + `next
start`), not `next dev`. To reproduce a CI failure locally as closely as
possible, run the four steps above but build+start the frontend instead
of `npm run dev`:

```
cd backend
.venv/Scripts/python.exe scripts/seed_e2e_data.py
.venv/Scripts/python.exe scripts/run_dev.py api --e2e-db

cd frontend
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"; npm run build
npm run start
npm run test:e2e
```

`NEXT_PUBLIC_API_URL` must be set before `npm run build`, not just before
`npm run start` - Next.js bakes `NEXT_PUBLIC_*` values into the client
bundle at build time.

### Backend test coverage (Phase 9C, gated in CI since Phase 9C-B)

```
cd backend
.venv/Scripts/python.exe -m pytest -q --cov=app --cov-report=term --cov-fail-under=90
```

Configured in `backend/pyproject.toml`'s `[tool.coverage.*]`. CI enforces
`--cov-fail-under=90` (docs/06 §21's documented goal, ADR-135's sibling
decision in `.github/workflows/ci.yml`'s `backend` job); running `pytest`
locally without the flag stays gate-free, matching the command above
without `--cov-fail-under`.

### Before committing backend changes

`ruff check .` and `mypy app` are part of the local pre-commit check,
alongside `pytest` above - CI's `backend` job runs all three
(`ci.yml:42-46`), and a change that fails either blocks the PR the same
way a failing test does:

```
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy app
```

---

## 🤝 Contributing

Please read:

- `CONTRIBUTING.md`

---

## 📄 License

MIT License