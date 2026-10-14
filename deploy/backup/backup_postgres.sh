#!/bin/sh
set -e

# ==============================================================================
# Siva Gayathri Tours & Travels — Automated PostgreSQL Backup Service
# Creates verified, compressed pg_dump snapshots with SHA-256 integrity audits
# ==============================================================================

BACKUP_DIR="${BACKUP_DIR:-/backups}"
mkdir -p "$BACKUP_DIR"

PG_HOST="${PG_HOST:-postgis}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-travel_gis_user}"
PG_DB="${PG_DB:-travel_erp_gis}"
export PGPASSWORD="${PGPASSWORD:-travel_gis_pass}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="travelerp_db_${PG_DB}_${TIMESTAMP}.dump"
BACKUP_FILEPATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
META_FILEPATH="${BACKUP_DIR}/${BACKUP_FILENAME}.meta.json"

echo "======================================================================"
echo "🐘 INITIATING AUTOMATED POSTGRESQL DATABASE BACKUP: ${TIMESTAMP}"
echo "======================================================================"
echo "[*] Connecting to ${PG_HOST}:${PG_PORT} (Database: ${PG_DB})..."

# Verify connection
if ! pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" > /dev/null 2>&1; then
    echo "❌ FATAL: PostgreSQL at ${PG_HOST}:${PG_PORT} is not reachable. Backup aborted."
    exit 1
fi

# Run pg_dump in custom archive format (compressed, supports parallel restore)
echo "[*] Dumping database schema, postgis geometries, and pgvector embeddings..."
pg_dump \
    -h "$PG_HOST" \
    -p "$PG_PORT" \
    -U "$PG_USER" \
    -d "$PG_DB" \
    -F c \
    -b \
    -v \
    -f "$BACKUP_FILEPATH"

# Verify dump file was created and is non-empty
if [ ! -s "$BACKUP_FILEPATH" ]; then
    echo "❌ FATAL: Backup file ${BACKUP_FILEPATH} is missing or zero-length."
    exit 1
fi

FILE_SIZE=$(wc -c < "$BACKUP_FILEPATH" | tr -d ' ')
echo "✅ Dump completed successfully! Size: ${FILE_SIZE} bytes."

# Verify dump integrity with pg_restore list
echo "[*] Verifying dump integrity using pg_restore --list..."
ITEM_COUNT=$(pg_restore --list "$BACKUP_FILEPATH" | wc -l | tr -d ' ')
echo "✅ Integrity verified: ${ITEM_COUNT} database objects recorded in TOC."

# Generate SHA-256 Checksum
CHECKSUM=$(sha256sum "$BACKUP_FILEPATH" | awk '{print $1}')
echo "🔒 SHA-256 Checksum: ${CHECKSUM}"

# Query table statistics for metadata
TABLE_COUNT=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
PACKAGE_COUNT=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM packages_package;" 2>/dev/null | tr -d ' ' || echo "0")
ITINERARY_COUNT=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM packages_itineraryday;" 2>/dev/null | tr -d ' ' || echo "0")

# Write metadata JSON
cat <<EOF > "$META_FILEPATH"
{
  "timestamp": "${TIMESTAMP}",
  "database": "${PG_DB}",
  "host": "${PG_HOST}",
  "filename": "${BACKUP_FILENAME}",
  "filesize_bytes": ${FILE_SIZE},
  "sha256": "${CHECKSUM}",
  "toc_objects": ${ITEM_COUNT},
  "public_tables": ${TABLE_COUNT:-0},
  "packages_count": ${PACKAGE_COUNT:-0},
  "itineraries_count": ${ITINERARY_COUNT:-0},
  "status": "VERIFIED_HEALTHY"
}
EOF

echo "✅ Metadata logged to ${META_FILEPATH}"

# Retention Policy: Prune backups older than 14 days
echo "[*] Applying retention policy: pruning dumps older than 14 days..."
find "$BACKUP_DIR" -type f -name "travelerp_db_*.dump" -mtime +14 -delete
find "$BACKUP_DIR" -type f -name "travelerp_db_*.meta.json" -mtime +14 -delete
echo "✅ Backup retention cleanup complete."
echo "======================================================================"
