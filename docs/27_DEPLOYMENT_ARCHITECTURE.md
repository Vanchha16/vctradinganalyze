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

**`.env` is not the whole truth for strategy settings (ADR-178).** The
strategy on/off switches, tight setup distances and signal pipeline
settings can be overridden from Admin -> Strategy Settings, stored in
`system_settings` under `runtime.*`. A stored override outranks `.env`.
Before editing one of those values in `.env` on the server, check that page
(or `SELECT key, value FROM system_settings WHERE key LIKE 'runtime.%'`) -
otherwise the edit can be silently ignored. Overrides take effect within 30
seconds without a restart.

**Swing paper trading (ADR-182)** is the `paper_swing_enabled` switch on the
same page (`PAPER_SWING_ENABLED`, default off). While on, the
`paper_swing.run` task uses ~21 Twelve Data requests a day for EURUSD,
GBPUSD and USDJPY, which stay **inactive** assets. Do not activate them from
Admin -> Assets: that would put them in the live pipeline and the EA feed.

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
| `deploy/systemd/claudetrading-backup.service` | oneshot unit that runs it |
| `deploy/systemd/claudetrading-backup.timer` | daily schedule, `Persistent=true` |

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
# AWS CLI v2 sends newer integrity checksums by default; keep R2 uploads to
# the classic behaviour.
AWS_REQUEST_CHECKSUM_CALCULATION=when_required
AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
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

# 2. Restore (--clean drops existing objects first). As the app's own user,
#    so it keeps owning every object.
pg_restore --clean --if-exists --no-owner -d "$URL" ~/deploy_backups/auto_<ts>.dump

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

**Last verified: 2026-11-06**, the hard way - production itself was rebuilt
from `auto_20261105_030501.dump` downloaded from R2 (section 10.1): 6 users,
146 signals, `alembic_version` `e4c9a2f7b1d6` already at head, and a manual
`claudetrading-backup` run uploaded `auto_20261106_043606.dump` back to R2.

Previously verified 2026-09-15 - `auto_20260915_092406.dump`, downloaded from
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

# 10. Migrating to a New Host

Written 2026-09-16, after the AWS suspension of 2026-09-15. **Nothing needed
to rebuild lives inside AWS**, which is what makes this possible while the
account is locked:

| Asset | Lives at | Reachable during an AWS suspension |
|---|---|---|
| Code, migrations, these units | GitHub | yes |
| Database dump | Cloudflare R2 | yes |
| `backend/.env` | operator's PC, `.backup/prod.env` | yes |
| DNS | Hostinger (`*.dns-parking.com`), **not Route 53** | yes |

**You cannot take a fresh dump while suspended** - SSH is gone too. You
restore the last nightly, so expect to lose up to 24h (section 9's RPO).

**This procedure was run for real on 2026-11-06** (the 2026-11-05 outage,
section 10.1) and corrected where it had failed. Allow about two hours;
most of it is waiting for the operator's console steps.

## What to provision

**`t3.small`** (2 vCPU, 2GB RAM), Ubuntu **24.04** LTS x86 (not 26.04: every
version below is pinned by 24.04), 30GB gp3, `ap-southeast-1`. The old
`t3.micro` (1GB) was too small to build the frontend without leaning on swap.

Security group: SSH (22) from the operator's IP only; HTTP (80) and HTTPS
(443) from anywhere.

**Attach an Elastic IP before touching DNS.** The auto-assigned public IP
changes on every stop/start, and is released the moment an Elastic IP is
associated - point DNS at the Elastic IP, never at the temporary one.

Stack as built (identical on both rebuilds): PostgreSQL 16.15, Redis 7.0.15,
Python 3.12.3, Node 20.20.2, npm 10.8.2, nginx 1.24.0.

## What the operator must fetch first

| Item | Where | Why only the operator can |
|---|---|---|
| Newest dump | Cloudflare dashboard -> R2 -> `claudetrading-backups` -> `db/` | its R2 keys lived only in `/etc/claudetrading-backup.env` on the dead box |
| `backend/.env` | `.backup/prod.env` on the operator's PC | not in git or the dump |
| Telegram bot token, if changed since `.backup/prod.env` was copied | @BotFather -> /mybots -> API Token | on 2026-11-06 the copy held a revoked token (`401 Unauthorized`) |
| New R2 token (Object Read & Write, this bucket) | Cloudflare -> R2 -> Manage API Tokens | for step 8 |

**Keep `.backup/prod.env` current.** Copy `backend/.env` off the box after
every change to it (section 8); a stale copy is how the revoked Telegram token
came back.

## Steps

```bash
# 1. Packages, swap, clock
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile \
  && sudo swapon /swapfile && echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
sudo timedatectl set-timezone UTC
sudo apt update && sudo apt install -y postgresql redis-server nginx git curl unzip \
  python3-venv python3-pip certbot python3-certbot-nginx
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -   # Ubuntu's node is older
sudo apt install -y nodejs
# AWS CLI v2, used by the backup upload (not in Ubuntu 24.04's apt)
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscliv2.zip \
  && cd /tmp && unzip -q awscliv2.zip && sudo ./aws/install && rm -rf aws awscliv2.zip

# 2. Code
git clone https://github.com/Vanchha16/vctradinganalyze.git ~/ClaudeTradingAI
cd ~/ClaudeTradingAI/backend
python3 -m venv venv          # note: venv, not .venv (section 7)
venv/bin/pip install -e .
mkdir -p ~/deploy_backups

# 3. Secrets - from the operator's PC, NOT from git. Then chmod 600.
scp .backup/prod.env <newhost>:~/ClaudeTradingAI/backend/.env

# 4. Database and role, matching DATABASE_URL in .env exactly. Read the
#    user, password and name through app.config (never print them); the
#    2026-11-06 rebuild did this with a short python snippet.
sudo -u postgres psql -c "CREATE ROLE claudetrading_user LOGIN PASSWORD '<from .env>';"
sudo -u postgres createdb claudetrading --owner claudetrading_user

# 5. Restore the database. Copy the dump the operator downloaded to the box.
#    --role makes claudetrading_user own every object. Without it (plain
#    --no-owner as postgres) the tables belong to postgres and the app
#    cannot read them.
sudo -u postgres pg_restore --no-owner --no-privileges --role=claudetrading_user \
  -d claudetrading /tmp/restore.dump
venv/bin/python -m alembic upgrade head   # in case the dump predates a migration

# 6. Frontend. NEXT_PUBLIC_API_URL is baked in at build time; without it the
#    browser calls localhost:8000 and every page fails. Standalone output
#    excludes .next/static - the copy is mandatory (section 7), and
#    `npm run build` recreates standalone from scratch every time.
cd ~/ClaudeTradingAI/frontend
echo "NEXT_PUBLIC_API_URL=https://vcanalyzetrading.site/api/v1" > .env.production
npm ci && npm run build
cp -r .next/static .next/standalone/.next/static

# 7. Services - only after step 5. A worker started on an empty database
#    makes signals with no history behind them.
sudo cp ~/ClaudeTradingAI/deploy/systemd/*.service /etc/systemd/system/
sudo cp ~/ClaudeTradingAI/deploy/systemd/*.timer   /etc/systemd/system/
chmod +x ~/ClaudeTradingAI/deploy/backup_production.sh
sudo systemctl daemon-reload
sudo systemctl enable --now claudetrading-backend claudetrading-worker \
  claudetrading-beat claudetrading-frontend claudetrading-backup.timer

# 8. Backups - the credentials file (section 8), root:ubuntu 640.
sudo install -o root -g ubuntu -m 640 /dev/null /etc/claudetrading-backup.env
sudo nano /etc/claudetrading-backup.env

# 9. Web server
sudo cp ~/ClaudeTradingAI/deploy/nginx-vcanalyzetrading.conf /etc/nginx/sites-available/claudetrading
sudo ln -sf /etc/nginx/sites-available/claudetrading /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

**Cut DNS over before requesting the certificate.** Certbot validates over
HTTP against the live A record, so it fails if the domain still points at the
old host. At Hostinger, set the **A record `@`** to the Elastic IP (`www` is a
CNAME to the apex and needs no change), check it with
`nslookup vcanalyzetrading.site 8.8.8.8`, then:

```bash
sudo certbot --nginx -d vcanalyzetrading.site -d www.vcanalyzetrading.site \
  --non-interactive --agree-tos --register-unsafely-without-email --redirect
```

`certbot.timer` (installed with the package) renews it.

**The price gap closes by itself** (ADR-188): each collection run starts from
the newest stored candle, so the first run of every timeframe after the
restore fetches the outage window. Before ADR-188 this took a manual backfill.

## By hand afterwards

- **EA token.** Regenerate it and enter it in the MT5 terminal, then re-apply
  that terminal's ADR-163 settings (paused, lot size, ADR-170 daily loss
  limit). Until this is done the EA places no orders.
- **Telegram.** If the log shows `TelegramAuthenticationError`, the token is
  stale: paste the current one on the admin API keys page (ADR-156; takes
  effect within 30s, no restart), or put it in `backend/.env` and restart the
  worker, beat and backend. Re-link the operator account if messages still do
  not arrive.

## Verify

Section 7's warning applies with full force here: **`curl` status codes prove
nothing about a frontend deploy.** Next.js answers 200 for the SSR shell even
when every asset behind it 404s. Fetch a real asset:

```bash
systemctl is-active claudetrading-{backend,worker,beat,frontend}
curl -o /dev/null -w "%{http_code}\n" \
  "http://localhost:3000/_next/static/chunks/$(ls ~/ClaudeTradingAI/frontend/.next/standalone/.next/static/chunks/*.js | head -1 | xargs basename)"
grep -rl "vcanalyzetrading.site/api/v1" ~/ClaudeTradingAI/frontend/.next/standalone/.next/static/chunks | wc -l  # > 0
sudo systemctl start claudetrading-backup   # must log "upload ok"
```

Then confirm in the database that the worker is writing new candles for
every timeframe (not just M1), that the newest `signals` row is recent, and
that `telegram.poll_updates` succeeds in the worker log. From outside:
`https://vcanalyzetrading.site/api/v1/health` returns `{"status":"ok"}` and
`/api/v1/metrics` returns 403.

## Keep the old host until the new one is proven

Do not delete the old instance the moment DNS moves. Keep it until the new
host has generated signals, taken a backup and served real traffic - the DNS
record can point back within minutes if something is wrong.

**Never run two workers.** If the old account comes back, its instance starts
again with the same Telegram token and the same signal schedule: every signal
would be sent twice. Stop its `claudetrading-worker` and `claudetrading-beat`
first.

## 10.1 The 2026-11-05 outage

- **05 Nov ~03:05 UTC:** the production box (AWS account 419212279428) went
  offline. The account was suspended for billing, as on 2026-09-15. The nightly
  dump had uploaded to R2 two minutes earlier, so almost no data was lost.
  The EA's Windows VPS was in another AWS account, suspended 21 Oct and
  closed by AWS on 24 Oct.
- Nobody noticed for about a day: the app had no way to report its own
  outage. ADR-188 adds a stale-price alert for failures the app can see; an
  outside uptime monitor is needed for the box itself.
- **06 Nov:** rebuilt on a `t3.small` in a new AWS account (929405967262),
  Elastic IP `3.1.189.129`, using this section. Corrections it needed, now
  folded in above: the restore ownership (`--role`), the frontend's
  `NEXT_PUBLIC_API_URL`, the AWS CLI install, the R2 checksum variables
  (section 8), a stale Telegram token in `.backup/prod.env`, and a day of
  candles missing on every timeframe above M5 (ADR-188).

---

# 11. Future

Kubernetes

Auto Scaling

Multi-Region

CDN

Object Storage
