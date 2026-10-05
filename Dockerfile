# ---------------------------------------------------------------------------
# Backend image: Django + DRF, also used for the Celery worker and Celery beat.
# The three services share this image and differ only by their command.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build/runtime system deps.
# libpq5 + gcc are kept because psycopg2 is declared in requirements.txt, so the
# image stays usable if this project ever moves off SQLite.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Directories Django expects to exist. `static` is in STATICFILES_DIRS but is not
# tracked in the project, and the rest are mount points for named volumes.
RUN mkdir -p /app/static /app/staticfiles /app/media /app/logs /app/data

# Normalise line endings so the entrypoint runs when built from a Windows host.
RUN sed -i 's/\r$//' /app/docker/entrypoint.sh && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "config.wsgi:application"]
