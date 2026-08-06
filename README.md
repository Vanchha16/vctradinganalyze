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

---

## 🤝 Contributing

Please read:

- `CONTRIBUTING.md`

---

## 📄 License

MIT License