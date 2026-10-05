#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Shared entrypoint for the backend, celery worker and celery beat containers.
#
# Only the container with RUN_MIGRATIONS=1 (the backend) touches the schema.
# The worker and beat wait for the database file to appear so they never race
# the backend on first boot.
# ---------------------------------------------------------------------------
set -euo pipefail

DB_PATH="${SQLITE_PATH:-/app/data/db.sqlite3}"
SEED_PATH="${SQLITE_SEED_PATH:-/app/seed/db.sqlite3}"

log() { echo "[entrypoint] $*"; }

wait_for_redis() {
    local url="${CELERY_BROKER_URL:-${REDIS_URL:-}}"
    [ -z "$url" ] && return 0

    log "waiting for redis..."
    for _ in $(seq 1 60); do
        if python - "$url" <<'PY'
import sys, redis
try:
    redis.from_url(sys.argv[1], socket_connect_timeout=2).ping()
except Exception:
    sys.exit(1)
PY
        then
            log "redis is up"
            return 0
        fi
        sleep 2
    done
    log "ERROR: redis did not become reachable in time"
    return 1
}

seed_database() {
    # First boot only: if the data volume is empty but a seed database was
    # mounted, adopt it so existing local data carries over into Docker.
    if [ ! -f "$DB_PATH" ] && [ -f "$SEED_PATH" ]; then
        log "seeding $DB_PATH from $SEED_PATH"
        cp "$SEED_PATH" "$DB_PATH"
    fi
}

tune_sqlite() {
    # WAL lets the web, worker and beat containers read while one writes.
    # Without it concurrent access raises "database is locked".
    [ -f "$DB_PATH" ] || return 0
    python - "$DB_PATH" <<'PY'
import sys, sqlite3
con = sqlite3.connect(sys.argv[1], timeout=30)
con.execute("PRAGMA journal_mode=WAL;")
con.execute("PRAGMA synchronous=NORMAL;")
con.close()
PY
    log "sqlite journal_mode=WAL"
}

wait_for_database() {
    log "waiting for the database to be initialised by the backend..."
    for _ in $(seq 1 90); do
        [ -f "$DB_PATH" ] && { log "database is ready"; return 0; }
        sleep 2
    done
    log "ERROR: database file $DB_PATH never appeared"
    return 1
}

wait_for_redis

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    seed_database
    log "applying migrations..."
    python manage.py migrate --noinput
    tune_sqlite
    log "collecting static files..."
    python manage.py collectstatic --noinput --clear >/dev/null
    log "static files collected"
else
    wait_for_database
fi

log "starting: $*"
exec "$@"
