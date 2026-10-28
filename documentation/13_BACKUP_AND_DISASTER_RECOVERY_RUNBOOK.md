# 🛡️ TravelERP — Backup & Disaster Recovery Runbook
**Document ID:** `13_BACKUP_AND_DISASTER_RECOVERY_RUNBOOK`  
**Revision:** 2.0 (Production Hardened)  
**Target Audience:** DevOps, System Administrators, Fleet Operations Directors  

---

## 1. Executive Summary & SLAs

The TravelERP platform handles mission-critical travel operations, corporate fleet commutes, live GPS telematics, customer payments, and statutory GST double-entry ledgers. Loss of database state or corruption causes direct financial, legal, and operational damage.

| Metric | Target SLA | Strategy |
|---|---|---|
| **Recovery Point Objective (RPO)** | **< 15 minutes** | Continuous SQLite WAL mode / PostgreSQL WAL archiving + Hourly snapshots |
| **Recovery Time Objective (RTO)** | **< 5 minutes** | Hot atomic online restore via management commands or `pg_restore` |
| **Integrity Assurance** | **100% SHA-256** | Every snapshot is hashed, metadata-stamped, and checked with `PRAGMA integrity_check` |
| **Retention Policy** | **30 days daily, 12 months monthly** | Automated pruning with immutable offsite backups |

---

## 2. Automated Snapshot Export (SQLite Development / Single-Node)

### Export Command
```bash
python manage.py export_database_snapshot --output-dir backups --prefix travelerp_snapshot
```

### What Happens During Export:
1. **Hot Online Copy:** Uses SQLite's native `sqlite3.backup` API with small page increments (100 pages per burst), allowing active transactions, HTMX requests, and driver pings to execute without locking.
2. **SHA-256 Fingerprint:** Computes cryptographic hash of the snapshot database.
3. **Audit Manifest:** Generates a companion `.meta.json` file recording:
   - Snapshot timestamp
   - Total rows for key models (`Booking`, `Trip`, `Party`, `Vehicle`, `Payment`, `TripExpense`)
   - SHA-256 checksum
   - Database pragma integrity status

---

## 3. Restoring from a Snapshot (SQLite)

### Standard Restore (Safe Mode)
```bash
python manage.py restore_database_snapshot travelerp_snapshot_20261016_124204.sqlite3
```
Or specify the full path:
```bash
python manage.py restore_database_snapshot backups/travelerp_snapshot_20261016_124204.sqlite3
```

### Safeguards Built into `restore_database_snapshot`:
- **Pre-flight Integrity Check:** Runs `PRAGMA integrity_check;` on the backup file *before touching* the live database.
- **SHA-256 Verification:** Validates that the snapshot file has not suffered bit rot or tampering against `.meta.json`.
- **Pre-Restore Safety Backup:** Automatically creates a safety backup `db.pre_restore_safety_<TIMESTAMP>.sqlite3` of the current database before replacement.
- **WAL & SHM Flush:** Automatically unlinks auxiliary `-wal` and `-shm` files to prevent stale page cache reads.

### Emergency Flags:
```bash
# Bypass checksum verification if meta.json was lost
python manage.py restore_database_snapshot <file> --skip-checksum

# Bypass emergency pre-restore safety copy (low disk space)
python manage.py restore_database_snapshot <file> --no-safety-backup
```

---

## 4. Production PostgreSQL / PostGIS Backup & Restore

When running in Docker or Kubernetes with PostgreSQL (`USE_POSTGRES=1`):

### 4.1 Production Export (pg_dump)
```bash
# Docker compose command
docker compose -f docker-compose.prod.yml exec -T postgis pg_dump \
  -U travel_gis_user \
  -F c \
  -b \
  -v \
  -f /var/lib/postgresql/data/backups/travelerp_prod_$(date +%Y%m%d_%H%M%S).dump \
  travel_erp_gis
```

### 4.2 Production Restore (pg_restore)
```bash
# 1. Stop application web workers to terminate active connections
docker compose -f docker-compose.prod.yml stop web

# 2. Run atomic restore with clean drop & recreate
docker compose -f docker-compose.prod.yml exec -T postgis pg_restore \
  -U travel_gis_user \
  -d travel_erp_gis \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  /var/lib/postgresql/data/backups/travelerp_prod_<TIMESTAMP>.dump

# 3. Verify database connectivity
docker compose -f docker-compose.prod.yml exec web python manage.py check

# 4. Restart web service
docker compose -f docker-compose.prod.yml start web
```

---

## 5. Media & Uploaded Document Assets

Customer ID documents, driver licenses, vehicle insurance policies, and digital handover photos are stored in `media/`:

### Backup Media Directory:
```bash
# Linux / Docker
tar -czvf backups/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/

# Windows PowerShell
Compress-Archive -Path media/* -DestinationPath "backups/media_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
```

### Restore Media Directory:
```bash
# Linux
tar -xzvf backups/media_backup_<TIMESTAMP>.tar.gz -C ./

# Windows PowerShell
Expand-Archive -Path "backups/media_backup_<TIMESTAMP>.zip" -DestinationPath media/ -Force
```

---

## 6. Disaster Recovery Checklist

In the event of hardware failure, catastrophic server loss, or ransomware:

1. **Provision New Node:**
   - Clone repo: `git clone <REPO_URL>`
   - Copy `.env.example` to `.env` and populate environment secrets (`DJANGO_SECRET_KEY`, `GROQ_API_KEY`, etc.)
2. **Restore Database:**
   - Place latest snapshot in `backups/`
   - Run `python manage.py restore_database_snapshot <LATEST_SNAPSHOT>`
3. **Restore Media Files:**
   - Extract latest media archive to `media/`
4. **Run System Verifications:**
   ```bash
   python manage.py check --deploy
   python manage.py audit_database_integrity
   curl -f http://localhost:8000/health/
   ```
5. **Start Production Stack:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
