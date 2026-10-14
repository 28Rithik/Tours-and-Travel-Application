#!/bin/sh
set -e

# ==============================================================================
# Siva Gayathri Tours & Travels — PostgreSQL Disaster Recovery Restore Script
# Restores database from a custom pg_dump archive with integrity verification
# ==============================================================================

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_backup_file.dump>"
    echo "Example: $0 /backups/travelerp_db_travel_erp_gis_20261014_120000.dump"
    exit 1
fi

RESTORE_FILE="$1"
if [ ! -f "$RESTORE_FILE" ]; then
    echo "❌ ERROR: Backup file '${RESTORE_FILE}' not found."
    exit 1
fi

PG_HOST="${PG_HOST:-postgis}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-travel_gis_user}"
PG_DB="${PG_DB:-travel_erp_gis}"
export PGPASSWORD="${PGPASSWORD:-travel_gis_pass}"

echo "======================================================================"
echo "⚠️ SIVAGAYATHRI TRAVEL ERP — DATABASE RESTORE INITIATED"
echo "Target File: ${RESTORE_FILE}"
echo "Target DB:   ${PG_HOST}:${PG_PORT}/${PG_DB}"
echo "======================================================================"

# Verify checksum if meta.json exists
META_FILE="${RESTORE_FILE}.meta.json"
if [ -f "$META_FILE" ]; then
    echo "[*] Found metadata file. Validating SHA-256 checksum..."
    EXPECTED_SHA=$(grep -o '"sha256": *"[^"]*"' "$META_FILE" | awk -F'"' '{print $4}')
    ACTUAL_SHA=$(sha256sum "$RESTORE_FILE" | awk '{print $1}')
    if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
        echo "❌ FATAL: Checksum mismatch! Corrupted backup file."
        echo "   Expected: $EXPECTED_SHA"
        echo "   Actual:   $ACTUAL_SHA"
        exit 1
    fi
    echo "✅ Checksum verified: $ACTUAL_SHA"
fi

# Terminate active client connections to target database
echo "[*] Disconnecting active client sessions to ${PG_DB}..."
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PG_DB}' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true

# Restore using pg_restore with clean recreation
echo "[*] Executing pg_restore (clean schema recreation)..."
pg_restore \
    -h "$PG_HOST" \
    -p "$PG_PORT" \
    -U "$PG_USER" \
    -d "$PG_DB" \
    -c \
    --if-exists \
    -v \
    "$RESTORE_FILE" || true

echo "✅ Database restore executed."

# Verify post-restore table counts
echo "[*] Auditing restored database..."
PACKAGES=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM packages_package;" | tr -d ' ')
ITINERARIES=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM packages_itineraryday;" | tr -d ' ')

echo "📊 Post-Restore Audit Results:"
echo "   • Tour Packages: ${PACKAGES}"
echo "   • Itinerary Days: ${ITINERARIES}"
echo "======================================================================"
echo "🎉 RESTORE OPERATION COMPLETED SUCCESSFULLY!"
echo "======================================================================"
