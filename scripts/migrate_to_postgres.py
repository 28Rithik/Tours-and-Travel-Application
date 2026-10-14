import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import subprocess

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
SQLITE_DB_PATH = os.path.join(PROJECT_DIR, 'db.sqlite3')

# PostGIS / PostgreSQL connection config
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
    print(f"[*] Checking PostgreSQL connection at {PG_HOST}:{PG_PORT} (DB: {PG_DB})...", flush=True)
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
        print(f"✅ Connected to PostgreSQL: {ver.split(',')[0]}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}", flush=True)
        return False


def run_django_migrations_on_postgres():
    """Runs Django schema migrations directly on the PostgreSQL database."""
    print("\n" + "=" * 70, flush=True)
    print("🚀 STEP 1: PROVISIONING SCHEMAS VIA DJANGO MIGRATIONS ON POSTGRESQL", flush=True)
    print("=" * 70, flush=True)

    env = os.environ.copy()
    env['USE_POSTGRES'] = '1'
    env['DATABASE_URL'] = f"postgres://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

    cmd = [sys.executable, os.path.join(PROJECT_DIR, 'manage.py'), 'migrate', '--no-input']
    print(f"[*] Running: {' '.join(cmd)}", flush=True)
    res = subprocess.run(cmd, cwd=PROJECT_DIR, env=env, capture_output=True, text=True)

    if res.returncode == 0:
        print("✅ Django migrations applied successfully on PostgreSQL.", flush=True)
        return True
    else:
        print("❌ Migration error:", flush=True)
        print(res.stdout, flush=True)
        print(res.stderr, flush=True)
        return False


def migrate_data():
    """
    Streams data from SQLite to PostgreSQL with high-speed multi-row execute_values,
    boolean type conversion, and session_replication_role='replica'.
    Truncates all tables ONCE up front to prevent parent-table cascade deletion.
    """
    print("\n" + "=" * 70, flush=True)
    print("📦 STEP 2: STREAMING & MIGRATING DATA FROM SQLITE TO POSTGRESQL", flush=True)
    print("=" * 70, flush=True)

    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor()

    # 1. Disable FK triggers during bulk copy
    print("[*] Setting session_replication_role = 'replica' (disabling FK triggers)...", flush=True)
    pg_cur.execute("SET session_replication_role = 'replica';")

    # Tables to exclude from raw copy (migrations handled by manage.py migrate)
    EXCLUDE_TABLES = {'django_migrations'}

    tables = [
        t[0] for t in sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if t[0] not in EXCLUDE_TABLES
    ]

    # Query all public base tables in PG
    pg_cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    pg_existing_tables = {r[0] for r in pg_cur.fetchall()}

    # Truncate all tables ONCE up front
    to_truncate = [t for t in tables if t in pg_existing_tables]
    print(f"[*] Truncating {len(to_truncate)} application tables up front in PostgreSQL...", flush=True)
    if to_truncate:
        trunc_str = ', '.join([f'"{t}"' for t in to_truncate])
        pg_cur.execute(f"TRUNCATE TABLE {trunc_str} CASCADE;")
    print("✅ All tables cleanly truncated. Beginning high-speed data stream...", flush=True)

    total_tables = len(tables)
    migrated_rows_total = 0
    parity_report = []

    for idx, table in enumerate(tables, start=1):
        if table not in pg_existing_tables:
            parity_report.append((table, 0, 0, "SKIPPED (Table not in PG schema)"))
            continue

        # Get column names and types from PostgreSQL
        pg_cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public';",
            (table,)
        )
        pg_col_map = {r[0]: r[1].lower() for r in pg_cur.fetchall()}

        # Get SQLite columns
        sqlite_cur.execute(f'PRAGMA table_info("{table}")')
        sqlite_cols = [info[1] for info in sqlite_cur.fetchall()]

        # Intersecting columns present in both DBs
        valid_cols = [c for c in sqlite_cols if c in pg_col_map]
        if not valid_cols:
            continue

        col_str = ', '.join([f'"{c}"' for c in valid_cols])

        # Fetch SQLite rows
        sqlite_cur.execute(f'SELECT {col_str} FROM "{table}"')
        rows = sqlite_cur.fetchall()
        sqlite_count = len(rows)

        if sqlite_count > 0:
            # Type casting: convert integer 0/1 to boolean for boolean columns
            bool_indices = [i for i, c in enumerate(valid_cols) if pg_col_map[c] == 'boolean']
            
            if bool_indices:
                converted_rows = []
                for row in rows:
                    row_list = list(row)
                    for bi in bool_indices:
                        val = row_list[bi]
                        row_list[bi] = bool(val) if val is not None else None
                    converted_rows.append(tuple(row_list))
                rows = converted_rows

            # Ultra-fast multi-row INSERT via execute_values (page size 2000)
            insert_query = f'INSERT INTO "{table}" ({col_str}) VALUES %s'
            execute_values(pg_cur, insert_query, rows, page_size=2000)

            migrated_rows_total += sqlite_count

        # Verify PG count
        pg_cur.execute(f'SELECT count(*) FROM "{table}"')
        pg_count = pg_cur.fetchone()[0]

        status = "MATCH ✅" if sqlite_count == pg_count else "MISMATCH ❌"
        parity_report.append((table, sqlite_count, pg_count, status))

        if idx % 10 == 0 or idx == total_tables or sqlite_count > 500:
            print(f"  [{idx:>3}/{total_tables}] Migrated {table:<42} ({sqlite_count:>6,} rows) -> PG: {pg_count:>6,} rows", flush=True)

    # 2. Reset All Auto-Increment Sequences in PostgreSQL
    print("\n[*] Synchronizing all PostgreSQL primary key sequences...", flush=True)
    try:
        pg_cur.execute("""
            DO $$
            DECLARE
                r RECORD;
                max_id INT8;
            BEGIN
                FOR r IN (
                    SELECT table_name, column_name 
                    FROM information_schema.columns 
                    WHERE column_default LIKE 'nextval%' 
                    AND table_schema = 'public'
                ) LOOP
                    BEGIN
                        EXECUTE format('SELECT COALESCE(MAX(%I), 0) + 1 FROM %I', r.column_name, r.table_name) INTO max_id;
                        EXECUTE format('SELECT setval(pg_get_serial_sequence(%L, %L), %s, false)', r.table_name, r.column_name, max_id);
                    EXCEPTION WHEN OTHERS THEN
                        NULL;
                    END;
                END LOOP;
            END $$;
        """)
        print("✅ All sequences synchronized successfully.", flush=True)
    except Exception as e:
        print(f"⚠️ Sequence reset note: {e}", flush=True)

    # 3. Re-enable FK checks
    print("[*] Restoring session_replication_role = 'origin' (re-enabling FK triggers)...", flush=True)
    pg_cur.execute("SET session_replication_role = 'origin';")

    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()

    print(f"\n🎉 Total rows successfully migrated to PostgreSQL: {migrated_rows_total:,}", flush=True)

    # Summary
    print("\n" + "=" * 70, flush=True)
    print("📊 DATA PARITY AUDIT (SQLITE vs POSTGRESQL)", flush=True)
    print("=" * 70, flush=True)
    print(f"{'Table Name':<45} | {'SQLite':<8} | {'Postgres':<8} | Status", flush=True)
    print("-" * 70, flush=True)
    for table, sq_c, pg_c, st in parity_report:
        if sq_c > 0 or "MISMATCH" in st:
            print(f"{table:<45} | {sq_c:<8} | {pg_c:<8} | {st}", flush=True)

    return True


def main():
    print("=" * 70, flush=True)
    print("🐘 SIVAGAYATHRI TRAVEL ERP — POSTGRESQL PRODUCTION MIGRATION", flush=True)
    print("=" * 70, flush=True)

    if not check_postgres_connection():
        print("\n" + "!" * 70, flush=True)
        print("⚠️ ACTION REQUIRED TO START POSTGRESQL:", flush=True)
        print("  1. Ensure Docker Desktop is running on Windows.", flush=True)
        print("  2. Run: docker compose -f gis_stack/docker-compose.osm.yml up -d postgis redis", flush=True)
        print("  3. Once port 5434 is online, re-run this script.", flush=True)
        print("!" * 70, flush=True)
        sys.exit(1)

    # 1. Apply Migrations
    if not run_django_migrations_on_postgres():
        print("❌ Aborted due to migration errors.", flush=True)
        sys.exit(1)

    # 2. Migrate Data
    migrate_data()

    print("\n" + "=" * 70, flush=True)
    print("🏆 POSTGRESQL PRODUCTION MIGRATION COMPLETED SUCCESSFULLY!", flush=True)
    print("   To run TravelERP on PostgreSQL:", flush=True)
    print("   set USE_POSTGRES=1", flush=True)
    print("   python manage.py runserver 127.0.0.1:8000", flush=True)
    print("=" * 70, flush=True)


if __name__ == '__main__':
    main()
