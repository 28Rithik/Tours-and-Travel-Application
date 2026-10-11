# ==============================================================================
# TravelERP Enterprise Production Multi-Stage Dockerfile
# Optimized for minimum image size, security, and fast cold-start
# ==============================================================================

# Stage 1: Build Dependencies
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies for C-extensions (mysqlclient, pillow, reportlab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Minimal Production Runtime
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH=/root/.local/bin:$PATH \
    DJANGO_SETTINGS_MODULE=travelerp.settings

# Install runtime shared libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-mysql-client \
    libjpeg62-turbo \
    libfreetype6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application codebase
COPY . /app/

# Create non-root user for security hardening
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Healthcheck monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

EXPOSE 8000

# Launch Gunicorn with ASGI Uvicorn workers and production config
CMD ["gunicorn", "travelerp.asgi:application", "-c", "gunicorn.conf.py"]
