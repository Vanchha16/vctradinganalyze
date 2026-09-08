# Deployment Architecture

Version: 1.0

---

# 1. Objective

Deploy the platform using scalable, containerized infrastructure.

---

# 2. Components

Frontend

Backend API

AI Workers

Redis

PostgreSQL

Nginx

Monitoring

---

# 3. Environment

Development

Testing

Staging

Production

---

# 4. Infrastructure

Internet

↓

Nginx

↓

Frontend

↓

FastAPI

↓

Redis

↓

PostgreSQL

↓

Workers

---

# 5. Docker

Frontend Container

Backend Container

Redis Container

Postgres Container

Worker Container

Scheduler Container

Monitoring Container

---

# 6. Environment Variables

Database

Redis

JWT

OpenAI

Telegram

News Provider

Economic Provider

SMTP

Logging

---

# 7. Deployment Strategy

Blue/Green

Rolling Update

Rollback

Health Checks

## 7.1 Actual Production Procedure (as built, 2026-09-08)

The sections above describe the intended/aspirational strategy. What the
live box (`47.128.179.111`, Ubuntu, native systemd - **not** Docker,
despite §5) actually runs:

App root `~/ClaudeTradingAI`, tracking `main` directly. Backend venv is
`backend/venv` (not `.venv`). Four units: `claudetrading-backend`,
`claudetrading-worker`, `claudetrading-beat`, `claudetrading-frontend`.

**Backend / worker deploy**

1. `pg_dump` to `~/deploy_backups/` before any migration
2. `git pull origin main`
3. `venv/bin/python -m alembic upgrade head` - **before** restarting, or
   a worker on new code hits missing columns every tick
4. `sudo systemctl restart claudetrading-worker claudetrading-beat claudetrading-backend`

**Frontend deploy - the copy step is mandatory**

`claudetrading-frontend` runs Next.js in **standalone** mode
(`WorkingDirectory=frontend/.next/standalone`, `ExecStart=node server.js`).
Standalone output excludes `.next/static`, and `next build` recreates
`.next/standalone` from scratch, deleting anything previously copied
into it. `npm run build` alone therefore takes the entire site down:

```bash
cd ~/ClaudeTradingAI/frontend
npm run build
cp -r .next/static .next/standalone/.next/static   # REQUIRED
sudo systemctl restart claudetrading-frontend
```

There is no `public/` directory in this project today; if one is added,
it needs the same copy.

**Verifying a frontend deploy by HTTP status code does not work.**
Next.js returns `200` for the server-rendered shell even when every
asset it references 404s - the user gets the error boundary
("Something went wrong") on a page the deployer just recorded as
healthy. This happened on 2026-09-08: a rebuild without the copy step
404'd all 46 JS chunks plus CSS and fonts site-wide while
`curl -o /dev/null -w "%{http_code}"` reported `200` for every route.
Verify by requesting a real asset from the new build, or by loading a
page in a browser and reading the console:

```bash
curl -s -o /dev/null -w "%{http_code}
"   http://localhost:3000/_next/static/chunks/$(ls .next/static/chunks | head -1)
```

**Resource note:** disk is not tight (48G, ~39G free). Memory is - 909MB
RAM, ~172MB available, plus a 1GB swapfile that `npm run build` relies
on. BACKLOG.md §10's "~1.2GB free disk" is stale.

---

# 8. Backup

Daily Database

Configuration Backup

Logs

Retention Policy

---

# 9. Disaster Recovery

Recovery Procedures

Recovery Objectives

Backup Verification

---

# 10. Future

Kubernetes

Auto Scaling

Multi-Region

CDN

Object Storage
