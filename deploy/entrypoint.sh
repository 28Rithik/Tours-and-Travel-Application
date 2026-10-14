#!/bin/sh
set -e

# ==============================================================================
# TravelERP Production Container Entrypoint Script
# Handles database readiness, automated schema migration, and static collection
# ==============================================================================

echo "======================================================================"
echo "🚀 SIVAGAYATHRI TRAVEL ERP — PRODUCTION CONTAINER INITIALIZATION"
echo "======================================================================"

# Determine Postgres connection parameters from DATABASE_URL or individual env vars
PG_HOST="${PG_HOST:-postgis}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-travel_gis_user}"
PG_DB="${PG_DB:-travel_erp_gis}"

# 1. Wait for PostgreSQL + PostGIS container to be healthy
echo "[*] Waiting for PostgreSQL database at ${PG_HOST}:${PG_PORT} (${PG_DB})..."
MAX_RETRIES=45
COUNT=0

until pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" > /dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
        echo "❌ FATAL: PostgreSQL at ${PG_HOST}:${PG_PORT} did not become ready in time."
        exit 1
    fi
    echo "    ... database not ready yet (attempt $COUNT/$MAX_RETRIES), retrying in 1s"
    sleep 1
done

echo "✅ PostgreSQL is reachable and ready to accept connections!"

# 2. Wait for Redis if configured
if [ -n "$REDIS_HOST" ]; then
    echo "[*] Waiting for Redis at ${REDIS_HOST}:6379..."
    REDIS_COUNT=0
    until python -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('$REDIS_HOST', 6379)); s.close()" > /dev/null 2>&1; do
        REDIS_COUNT=$((REDIS_COUNT + 1))
        if [ "$REDIS_COUNT" -ge 20 ]; then
            echo "⚠️ Warning: Redis at ${REDIS_HOST}:6379 not responding. Continuing with local fallback."
            break
        fi
        sleep 1
    done
    echo "✅ Redis is operational!"
fi

# 3. Apply Django Database Migrations
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "[*] Applying Django schema migrations on PostgreSQL..."
    python manage.py migrate --noinput
    echo "✅ Database migrations applied successfully."
fi

# 4. Collect Static Assets
if [ "${COLLECT_STATIC:-1}" = "1" ]; then
    echo "[*] Collecting static assets into staticfiles directory..."
    python manage.py collectstatic --noinput --clear
    echo "✅ Static assets collected."
fi

echo "======================================================================"
echo "✨ SYSTEM INITIALIZATION COMPLETE. STARTING WEB APPLICATION SERVICE."
echo "======================================================================"

# Execute passed command (e.g. gunicorn / daphne)
exec "$@"
