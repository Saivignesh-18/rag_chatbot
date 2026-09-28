# ---- AI Document Assistant : Backend image ----
FROM python:3.12-slim

# System deps needed by psycopg2 and general build tooling.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Cache embedding models inside the image/volume.
    FASTEMBED_CACHE_PATH=/app/.fastembed_cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Simple container healthcheck against the API. Uses $PORT when the platform
# (e.g. Render) assigns one, else defaults to 8000 (local docker-compose).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/health" || exit 1

# Bind the platform-provided $PORT in production; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
