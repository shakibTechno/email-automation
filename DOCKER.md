# Running the stack with Docker

Five containers, all defined in `docker-compose.yml`:

| Service    | Image                    | Purpose                                     | Published port |
|------------|--------------------------|---------------------------------------------|----------------|
| `redis`    | `redis:7-alpine`         | Cache (db 0) + Celery broker/results (db 1) | – (internal)   |
| `backend`  | built from `./Dockerfile`| Django + DRF under gunicorn                 | `8000`         |
| `worker`   | same image as backend    | Celery worker                               | –              |
| `beat`     | same image as backend    | Celery beat scheduler                       | –              |
| `frontend` | built from `./frontend/` | React build served by nginx                 | `3000`         |

The database stays **SQLite**, on a named volume shared by `backend`, `worker` and `beat`.

## Quick start

```bash
docker compose up --build -d
```

Then open **http://localhost:3000**.

nginx serves the SPA and reverse-proxies `/api`, `/admin`, `/static`, `/media`,
`/track`, `/unsubscribe` and `/p` to Django, so the whole app is same-origin and
no CORS is involved. The backend is also published directly on
http://localhost:8000 (admin at `/admin/`, API docs at `/api/docs/`).

## Development mode (live reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Source is bind-mounted, the backend runs `runserver` with autoreload, and the
frontend runs the Vite dev server on **http://localhost:5173** talking to the
backend on port 8000.

## Common commands

```bash
docker compose logs -f backend worker beat     # follow logs
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py migrate
docker compose restart worker beat             # after changing tasks
docker compose down                            # stop (volumes are kept)
docker compose down -v                         # stop and DELETE all data
```

## Data and volumes

| Volume        | Mounted at         | Contents                          |
|---------------|--------------------|-----------------------------------|
| `sqlite_data` | `/app/data`        | `db.sqlite3` + celery beat schedule |
| `media_data`  | `/app/media`       | Uploads (template/landing images) |
| `static_data` | `/app/staticfiles` | `collectstatic` output            |
| `logs_data`   | `/app/logs`        | Django logs                       |
| `redis_data`  | `/data`            | Redis AOF persistence             |

**First boot seeds the database from the project's existing `./db.sqlite3`**, which
is mounted read-only at `/app/seed/db.sqlite3`. Afterwards the volume copy is
authoritative and the host file is ignored. To re-import the host database later:

```bash
docker compose stop backend worker beat
docker compose cp db.sqlite3 backend:/app/data/db.sqlite3
docker compose start backend worker beat
```

To export the container database back to the host:

```bash
docker compose cp backend:/app/data/db.sqlite3 ./db.sqlite3
```

### Why SQLite needs care here

Three containers open the same database file, so the entrypoint sets
`journal_mode=WAL` once and `config/settings/base.py` adds a 30s busy timeout.
Without both, concurrent writes fail with `database is locked`. This is fine for
development; for real concurrency move `DATABASE_URL` to PostgreSQL.

## Ports

Only the frontend (`3000`) and backend (`8000`) are published. Redis is reachable
only inside the compose network -- publishing it clashes with a `redis-server`
already running on the host. Inspect it with:

```bash
docker compose exec redis redis-cli
```

If `3000` or `8000` is taken, override without editing compose -- either inline:

```bash
FRONTEND_PORT=3100 BACKEND_PORT=8100 docker compose up -d
```

or by adding `FRONTEND_PORT` / `BACKEND_PORT` to `.env`.

## Configuration

Environment comes from two files, in order:

1. `.env` — shared settings and secrets (SMTP credentials, `SECRET_KEY`).
2. `.env.docker` — container-only overrides, applied second so they win.

`.env.docker` rewrites the host-oriented values: Redis moves from the WSL bridge
IP to the `redis` service name, and `DATABASE_URL` points at the shared volume
(`sqlite:////app/data/db.sqlite3` — four slashes for an absolute path).

Keep editing `.env` for secrets; it is never baked into an image.
