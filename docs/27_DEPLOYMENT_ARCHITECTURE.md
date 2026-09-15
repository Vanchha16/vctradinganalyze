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

## Daily Database

A systemd timer dumps Postgres every 24h at 03:00 UTC (ADR-173). Units and
script live in `deploy/`:

| File | Role |
|---|---|
| `deploy/backup_production.sh` | dump, prune, optional S3 upload |
| `deploy/claudetrading-backup.service` | oneshot unit that runs it |
| `deploy/claudetrading-backup.timer` | daily schedule, `Persistent=true` |

Output is `~/deploy_backups/auto_<ts>.dump` (`pg_dump -Fc`, ~41MB).

Check it is scheduled and see the last run:

```bash
systemctl list-timers claudetrading-backup.timer
sudo journalctl -u claudetrading-backup --since "2 days ago"
```

Run one on demand: `sudo systemctl start claudetrading-backup`.

## Off-Box Copy

The same run uploads to **Cloudflare R2** - deliberately outside AWS, so an
AWS account suspension cannot lock the backups at the same moment it takes
the site down (ADR-173). S3 would not survive that case.

Config and credentials live in `/etc/claudetrading-backup.env`, root-owned
and `chmod 600`, never in `backend/.env`:

```bash
BACKUP_S3_BUCKET=claudetrading-backups
BACKUP_S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
BACKUP_S3_PREFIX=db
AWS_ACCESS_KEY_ID=<r2 token access key id>
AWS_SECRET_ACCESS_KEY=<r2 token secret>
AWS_DEFAULT_REGION=auto
```

The R2 token is scoped to this one bucket. Rotate it by editing this file
alone; nothing else reads it.

List what has been uploaded:

```bash
aws s3 ls s3://claudetrading-backups/db/   --endpoint-url https://<account-id>.r2.cloudflarestorage.com
```

With no bucket set, the dump is still taken and kept locally. An upload
failure is logged and tolerated; only a `pg_dump` failure fails the unit.

## Configuration Backup

`backend/.env` is **not** in the dump and not in git. It holds
`CREDENTIAL_ENCRYPTION_KEY`, without which the `api_credentials` rows cannot
be decrypted - **a database dump alone is not a complete backup.** Copy it
off the box whenever it changes, to `.backup/` locally (gitignored).

## Logs

Journald only, not backed up. Nothing depends on log history for recovery.

## Retention Policy

The newest 7 `auto_*.dump` files are kept, older ones deleted on each run.
Pruning matches the `auto_` prefix only, so manual `pre_<change>_*` and
`rescue_*` dumps are never removed automatically - delete those by hand.

---

# 9. Disaster Recovery

## Recovery Procedures

**Restore the database onto a working box:**

```bash
# 1. Stop anything writing to it
sudo systemctl stop claudetrading-worker claudetrading-beat claudetrading-backend

# 2. Restore (--clean drops existing objects first)
pg_restore --clean --if-exists -d "$URL" ~/deploy_backups/auto_<ts>.dump

# 3. Bring the schema to head, in case the dump predates a migration
cd ~/ClaudeTradingAI/backend && venv/bin/python -m alembic upgrade head

# 4. Restart
sudo systemctl start claudetrading-backend claudetrading-worker claudetrading-beat
```

`$URL` is `settings.database_url` with the `postgresql+psycopg` prefix
stripped to `postgresql`.

**Rebuilding from nothing** (no dump available): the repo restores the
schema but not the rows. `alembic upgrade head`, then
`python -m scripts.seed_prod_assets`, then re-enter credentials in
Admin -> Credentials, regenerate the EA token and re-pair the terminal.
`signals`, `ai_analysis` and `ea_execution_events` cannot be regenerated.

## Recovery Objectives

| Objective | Value |
|---|---|
| RPO (data loss window) | 24h - the gap between nightly dumps |
| RTO, restore onto the existing box | ~15 min |
| RTO, rebuild onto a new host | hours, and the rows are lost |

## Backup Verification

**A dump that has never been restored is not a backup.** The timer does not
verify its own output. Quarterly, restore the newest dump into a scratch
database and check it opens.

**Last verified: 2026-09-15** - `auto_20260915_092406.dump`, downloaded from
R2 (not the local copy, so the whole chain was exercised) and restored into a
scratch database. 25 tables, `alembic_version` `b4e7d2a91c35`, and row counts
matching production for `signals` (104), `ea_execution_events` (18) and
`users` (6). `price_candles` was lower than production by the candles written
after the dump was taken, as expected.

Restore as the `postgres` superuser: `claudetrading_user` has neither
`rolcreatedb` nor superuser, so it cannot create the scratch database.

```bash
createdb ct_restore_test
pg_restore --no-owner -d ct_restore_test ~/deploy_backups/auto_<ts>.dump
psql -d ct_restore_test -c "select count(*) from signals;"
dropdb ct_restore_test
```

---

# 10. Future

Kubernetes

Auto Scaling

Multi-Region

CDN

Object Storage
