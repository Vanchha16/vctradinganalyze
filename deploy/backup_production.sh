#!/usr/bin/env bash
# Nightly production database backup (ADR-173).
#
# Dumps Postgres to ~/deploy_backups/auto_<ts>.dump, prunes to the last
# KEEP automatic dumps, then uploads to S3 if a bucket is configured.
#
# Exits non-zero only when pg_dump itself fails: a broken or unconfigured
# S3 upload is logged and tolerated, because the local dump is the thing
# that must not be lost.
set -o pipefail

APP_DIR="${APP_DIR:-$HOME/ClaudeTradingAI}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/deploy_backups}"
KEEP="${BACKUP_KEEP:-7}"
BUCKET="${BACKUP_S3_BUCKET:-}"
PREFIX="${BACKUP_S3_PREFIX:-db}"
# S3-compatible endpoint. Empty means real AWS S3; set for Cloudflare R2
# (https://<account-id>.r2.cloudflarestorage.com) or any other provider.
ENDPOINT="${BACKUP_S3_ENDPOINT:-}"
# Credentials file sourced only if present, so the token never lives in
# backend/.env (ADR-173). Expected to be root-owned, chmod 600.
CREDS_FILE="${BACKUP_CREDS_FILE:-/etc/claudetrading-backup.env}"

log() { echo "[backup] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

mkdir -p "$BACKUP_DIR"

# The URL lives in backend/.env, which the app already parses. Read it through
# app.config rather than grepping the file, so a prefix or quoting change in
# settings cannot silently produce a wrong URL here.
cd "$APP_DIR/backend" || { log "FATAL: no $APP_DIR/backend"; exit 1; }
URL="$(venv/bin/python -c 'from app.config import settings; print(settings.database_url.replace("postgresql+psycopg","postgresql"))')" || {
    log "FATAL: could not read database_url from app.config"
    exit 1
}

TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/auto_${TS}.dump"

log "dumping to $OUT"
if ! pg_dump "$URL" -Fc -f "$OUT"; then
    log "FATAL: pg_dump failed"
    rm -f "$OUT"
    exit 1
fi
SIZE="$(du -h "$OUT" | cut -f1)"
log "dump ok ($SIZE)"

# Prune only our own automatic dumps. Manual pre_<change>/rescue_ dumps are
# deliberately left alone - an operator took those on purpose.
mapfile -t OLD < <(ls -1t "$BACKUP_DIR"/auto_*.dump 2>/dev/null | tail -n +$((KEEP + 1)))
if [ "${#OLD[@]}" -gt 0 ]; then
    log "pruning ${#OLD[@]} dump(s) older than the newest $KEEP"
    for f in "${OLD[@]}"; do
        rm -f "$f" && log "  removed $(basename "$f")"
    done
fi

# --- Off-site upload (optional) --------------------------------------------
if [ -f "$CREDS_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; . "$CREDS_FILE"; set +a
    BUCKET="${BACKUP_S3_BUCKET:-$BUCKET}"
    ENDPOINT="${BACKUP_S3_ENDPOINT:-$ENDPOINT}"
    PREFIX="${BACKUP_S3_PREFIX:-$PREFIX}"
fi

if [ -z "$BUCKET" ]; then
    log "no BACKUP_S3_BUCKET set - keeping local copy only"
    exit 0
fi
if ! command -v aws >/dev/null 2>&1; then
    log "WARN: BACKUP_S3_BUCKET set but no aws binary - skipping upload"
    exit 0
fi

DEST="s3://$BUCKET/$PREFIX/$(basename "$OUT")"
EP_ARGS=()
[ -n "$ENDPOINT" ] && EP_ARGS=(--endpoint-url "$ENDPOINT")

log "uploading to $DEST${ENDPOINT:+ via $ENDPOINT}"
if aws s3 cp "$OUT" "$DEST" "${EP_ARGS[@]}" --only-show-errors; then
    log "upload ok"
else
    log "WARN: upload failed - local dump retained at $OUT"
fi
exit 0
