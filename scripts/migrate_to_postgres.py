import os
import sys
import sqlite3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from decimal import Decimal
import subprocess

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
SQLITE_DB_PATH = os.path.join(PROJECT_DIR, 'db.sqlite3')

# Default PostGIS / PostgreSQL connection config
PG_HOST = os.environ.get('PG_HOST', '127.0.0.1')
PG_PORT = int(os.environ.get('PG_PORT', 5434))
PG_DB = os.environ.get('PG_DB', 'travel_erp_gis')
PG_USER = os.environ.get('PG_USER', 'travel_gis_user')
PG_PASS = os.environ.get('PG_PASS', 'travel_gis_pass')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def check_postgres_connection():
    """Verifies whether PostgreSQL is reachable on target port."""
    print(f"[*] Checking PostgreSQL connection at {PG_HOST}:{PG_PORT} (DB: {PG_DB})...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASS,
            connect_timeout=4
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"✅ Connected to PostgreSQL: {ver.split(',')[0]}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def run_django_migrations_on_postgres():
    """Runs Django schema migrations directly on the PostgreSQL database."""
    print("\n" + "=" * 70)
    print("🚀 STEP 1: PROVISIONING SCHEMAS VIA DJANGO MIGRATIONS ON POSTGRESQL")
    print("=" * 70)

    env = os.environ.copy()
    env['USE_POSTGRES'] = '1'
    env['DATABASE_URL'] = f"postgres://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

    cmd = [sys.executable, os.path.join(PROJECT_DIR, 'manage.py'), 'migrate', '--no-input']
    print(f"[*] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=PROJECT_DIR, env=env, capture_output=True, text=True)

    if res.returncode == 0:
        print("✅ Django migrations applied successfully on PostgreSQL.")
        return True
    else:
        print("❌ Migration error:")
        print(res.stdout)
        print(res.stderr)
        return False


def migrate_data():
    """
    Streams data from SQLite to PostgreSQL with session_replication_role='replica'
    to prevent foreign key sequence ordering conflicts during migration.
    """
    print("\n" + "=" * 70)
    print("📦 STEP 2: STREAMING & MIGRATING DATA FROM SQLITE TO POSTGRESQL")
    print("=" * 70)

    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    # 1. Disable FK checks in PostgreSQL during bulk load
    print("[*] Setting session_replication_role = 'replica' (disabling FK triggers)...")
    pg_cur.execute("SET session_replication_role = 'replica';")

    # Tables to exclude from raw copy (migrations table is handled by migrate)
    EXCLUDE_TABLES = {'django_migrations'}

    tables = [
        t[0] for t in sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if t[0] not in EXCLUDE_TABLES
    ]

    total_tables = len(tables)
    migrated_rows_total = 0
    parity_report = []

    print(f"[*] Found {total_tables} application tables in SQLite.")

    for idx, table in enumerate(tables, start=1):
        # Check if table exists in PostgreSQL
        pg_cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
            (table,)
        )
        exists = pg_cur.fetchone()[0]
        if not exists:
            parity_report.append((table, 0, 0, "SKIPPED (Table not in PG schema)"))
            continue

        # Truncate existing rows in PG table
        pg_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')

        # Get column names
        sqlite_cur.execute(f'PRAGMA table_info("{table}")')
        cols = [info[1] for info in sqlite_cur.fetchall()]
        col_str = ', '.join([f'"{c}"' for c in cols])
        placeholders = ', '.join(['%s'] * len(cols))

        # Fetch SQLite rows in chunks
        sqlite_cur.execute(f'SELECT {col_str} FROM "{table}"')
        rows = sqlite_cur.fetchall()
        sqlite_count = len(rows)

        if sqlite_count > 0:
            insert_query = f'INSERT INTO "{table}" ({col_str}) VALUES ({placeholders})'
            # Batch execute
            pg_cur.executemany(insert_query, rows)
            migrated_rows_total += sqlite_count

        # Verify PG count
        pg_cur.execute(f'SELECT count(*) FROM "{table}"')
        pg_count = pg_cur.fetchone()[0]

        status = "MATCH ✅" if sqlite_count == pg_count else "MISMATCH ❌"
        parity_report.append((table, sqlite_count, pg_count, status))

        if idx % 10 == 0 or idx == total_tables:
            print(f"  [{idx}/{total_tables}] Processed {table} ({sqlite_count:,} rows)")

    # 2. Reset Auto-Increment Sequences in PostgreSQL
    print("\n[*] Resetting PostgreSQL primary key sequences to max(id)...")
    for table in tables:
        try:
            pg_cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('"{table}"', 'id'),
                    COALESCE(max(id), 1)
                ) FROM "{table}";
            """)
        except Exception:
            # Table might not have an integer 'id' primary key or sequence
            pass

    # 3. Re-enable FK checks
    print("[*] Restoring session_replication_role = 'origin' (re-enabling FK triggers)...")
    pg_cur.execute("SET session_replication_role = 'origin';")

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()

    print(f"\n🎉 Total rows successfully migrated to PostgreSQL: {migrated_rows_total:,}")

    # Print summary
    print("\n" + "=" * 70)
    print("📊 DATA PARITY AUDIT (SQLITE vs POSTGRESQL)")
    print("=" * 70)
    print(f"{'Table Name':<42} | {'SQLite':<8} | {'Postgres':<8} | Status")
    print("-" * 70)
    for table, sq_c, pg_c, st in parity_report:
        if sq_c > 0 or "MISMATCH" in st:
            print(f"{table:<42} | {sq_c:<8} | {pg_c:<8} | {st}")

    return True


def main():
    print("=" * 70)
    print("🐘 SIVAGAYATHRI TRAVEL ERP — POSTGRESQL PRODUCTION MIGRATION")
    print("=" * 70)

    if not check_postgres_connection():
        print("\n" + "!" * 70)
        print("⚠️ ACTION REQUIRED TO START POSTGRESQL:")
        print("  1. Ensure Docker Desktop is running on Windows.")
        print("  2. Run the GIS stack manager: python scripts/manage_gis_stack.py up")
        print("     Or execute: docker compose -f gis_stack/docker-compose.osm.yml up -d postgis")
        print("  3. Once port 5434 is online, re-run this script: python scripts/migrate_to_postgres.py")
        print("!" * 70)
        sys.exit(1)

    # 1. Apply Migrations
    if not run_django_migrations_on_postgres():
        print("❌ Aborted due to migration errors.")
        sys.exit(1)

    # 2. Migrate Data
    migrate_data()

    print("\n" + "=" * 70)
    print("🏆 POSTGRESQL PRODUCTION MIGRATION COMPLETED SUCCESSFULLY!")
    print("   To run TravelERP on PostgreSQL:")
    print("   set USE_POSTGRES=1")
    print("   python manage.py runserver 127.0.0.1:8000")
    print("=" * 70)


if __name__ == '__main__':
    main()
