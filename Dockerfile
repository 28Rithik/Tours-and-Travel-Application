# ==============================================================================
# TravelERP Enterprise Production Multi-Stage Dockerfile
# Optimized for minimum image size, non-root security, and high-concurrency ASGI
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies in Isolated Virtualenv
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies for C-extensions (psycopg2, pillow, reportlab, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt


# ------------------------------------------------------------------------------
# Stage 2: Minimal Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=travelerp.settings

# Install runtime shared libraries only (Postgres client, imaging libraries, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    libjpeg62-turbo \
    libfreetype6 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python virtualenv from builder stage
COPY --from=builder /venv /venv

# Copy application codebase
COPY . /app/

# Make entrypoint script executable
RUN chmod +x /app/deploy/entrypoint.sh

# Create non-root user for enterprise security hardening
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media /app/logs /app/backups && \
    chown -R appuser:appuser /app /venv

USER appuser

# Healthcheck monitoring
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/rathasarathi/quick-stats/ || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]

# Launch production server: Gunicorn with Uvicorn worker class or Daphne
CMD ["gunicorn", "travelerp.asgi:application", "-c", "gunicorn.conf.py"]
