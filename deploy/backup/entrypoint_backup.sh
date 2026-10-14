#!/bin/sh
set -e

# ==============================================================================
# Siva Gayathri Tours & Travels — Automated Backup Daemon Entrypoint
# Configures daily crond schedule and executes optional boot snapshot
# ==============================================================================

echo "======================================================================"
echo "🛡️ STARTING SIVAGAYATHRI TRAVEL ERP AUTOMATED BACKUP SERVICE"
echo "======================================================================"

BACKUP_CRON="${BACKUP_CRON:-0 2 * * *}"  # Default: 02:00 AM daily
echo "[*] Scheduled backup cron: '${BACKUP_CRON}'"

# Ensure backup script is executable
chmod +x /scripts/backup_postgres.sh /scripts/restore_postgres.sh

# Register cron job
echo "${BACKUP_CRON} /scripts/backup_postgres.sh >> /var/log/cron_backup.log 2>&1" > /etc/crontabs/root

# Optional initial backup on container boot
if [ "${BACKUP_ON_STARTUP:-1}" = "1" ]; then
    echo "[*] Executing initial startup backup in background..."
    /scripts/backup_postgres.sh >> /var/log/cron_backup.log 2>&1 &
fi

echo "✅ Backup daemon configured. Starting crond in foreground..."
touch /var/log/cron_backup.log
tail -f /var/log/cron_backup.log &
exec crond -f -l 2
