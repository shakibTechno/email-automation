#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Shared entrypoint for the backend, celery worker and celery beat containers.
#
# Only the container with RUN_MIGRATIONS=1 (the backend) touches the schema.
# The worker and beat wait until the schema exists so they never race the
# backend on first boot.
#
# Works with either database engine, chosen by DATABASE_URL:
#   postgres://...  -> the default; nothing to seed or tune
#   sqlite:///...   -> still supported for a quick local run, with the seeding
#                      and WAL tuning that shared-file access needs
# ---------------------------------------------------------------------------
set -euo pipefail

DB_PATH="${SQLITE_PATH:-/app/data/db.sqlite3}"
SEED_PATH="${SQLITE_SEED_PATH:-/app/seed/db.sqlite3}"
DB_URL="${DATABASE_URL:-}"

log() { echo "[entrypoint] $*"; }

is_sqlite() { case "$DB_URL" in sqlite*|"") return 0 ;; *) return 1 ;; esac; }

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
    # SQLite only, first boot: if the data volume is empty but a seed database
    # was mounted, adopt it so existing local data carries over into Docker.
    is_sqlite || return 0
    if [ ! -f "$DB_PATH" ] && [ -f "$SEED_PATH" ]; then
        log "seeding $DB_PATH from $SEED_PATH"
        cp "$SEED_PATH" "$DB_PATH"
    fi
}

tune_sqlite() {
    # WAL lets the web, worker and beat containers read while one writes.
    # Without it concurrent access raises "database is locked".
    is_sqlite || return 0
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

# Can we open a connection at all? Postgres needs this before migrating;
# compose's healthcheck usually covers it, but a container restart can still
# arrive first.
wait_for_connection() {
    is_sqlite && return 0
    log "waiting for postgres to accept connections..."
    for _ in $(seq 1 90); do
        if python - <<'PY'
import sys, django
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
except Exception:
    sys.exit(1)
PY
        then
            log "postgres is accepting connections"
            return 0
        fi
        sleep 2
    done
    log "ERROR: postgres did not accept connections in time"
    return 1
}

# Worker and beat must not start before the backend has applied migrations,
# or their first query hits a table that does not exist yet. Checking for rows
# in django_migrations works for both engines; the old check watched for the
# SQLite file, which postgres has no equivalent of.
wait_for_migrations() {
    log "waiting for the schema to be initialised by the backend..."
    for _ in $(seq 1 90); do
        if python - <<'PY'
import sys, django
django.setup()
from django.db import connection
try:
    with connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM django_migrations")
        sys.exit(0 if cur.fetchone()[0] > 0 else 1)
except Exception:
    sys.exit(1)
PY
        then
            log "schema is ready"
            return 0
        fi
        sleep 2
    done
    log "ERROR: the schema was not initialised in time"
    return 1
}

wait_for_redis

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    wait_for_connection
    seed_database
    log "applying migrations..."
    python manage.py migrate --noinput
    tune_sqlite
    log "collecting static files..."
    python manage.py collectstatic --noinput --clear >/dev/null
    log "static files collected"
else
    wait_for_connection
    wait_for_migrations
fi

log "starting: $*"
exec "$@"
