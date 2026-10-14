"""
Siva Gayathri Tours & Travels — TravelERP Production Stack & Hardening Audit Suite
Validates Docker Compose, Nginx SSL, Daphne ASGI, pgvector, Redis, and Automated Backups.
"""

import os
import sys
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.conf import settings
from django.db import connection


def audit_production_stack():
    print("=" * 80)
    print("🚢 SIVA GAYATHRI TRAVEL ERP — PRODUCTION DOCKER STACK & HARDENING AUDIT")
    print("=" * 80)

    checks_passed = 0
    total_checks = 0

    def assert_check(condition, title, details=""):
        nonlocal checks_passed, total_checks
        total_checks += 1
        if condition:
            checks_passed += 1
            print(f"  ✅ [PASS] {title} {f'({details})' if details else ''}")
        else:
            print(f"  ❌ [FAIL] {title} {f'({details})' if details else ''}")
            sys.exit(1)

    # 1. Docker Compose Configuration Validation
    print("\n📦 STEP 1: DOCKER COMPOSE CONFIGURATION AUDIT")
    compose_file = BASE_DIR / "docker-compose.prod.yml"
    assert_check(compose_file.exists(), "docker-compose.prod.yml file exists")

    res = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.prod.yml", "config", "-q"],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )
    assert_check(res.returncode == 0, "Docker Compose YAML syntax and volume/network topology valid")

    # 2. Nginx Reverse Proxy & SSL TLS Security
    print("\n🔒 STEP 2: NGINX REVERSE PROXY & TLS/SSL AUDIT")
    nginx_conf = BASE_DIR / "deploy" / "nginx" / "travelerp.conf"
    assert_check(nginx_conf.exists(), "Nginx production configuration exists", str(nginx_conf))

    conf_content = nginx_conf.read_text(encoding='utf-8')
    assert_check("upstream travelerp_upstream" in conf_content, "Upstream web cluster defined")
    assert_check("ssl_protocols TLSv1.2 TLSv1.3;" in conf_content, "Modern TLSv1.2 & TLSv1.3 protocols enforced")
    assert_check("limit_req_zone" in conf_content, "DDoS & brute-force rate-limiting zones configured")
    assert_check("proxy_set_header Upgrade $http_upgrade;" in conf_content, "WebSocket upgrade proxy headers configured")
    assert_check("add_header Strict-Transport-Security" in conf_content, "HSTS preloaded security header active")

    certs_dir = BASE_DIR / "deploy" / "nginx" / "certs"
    privkey = certs_dir / "privkey.pem"
    fullchain = certs_dir / "fullchain.pem"
    assert_check(privkey.exists() and fullchain.exists(), "Production SSL Certificates present in deploy/nginx/certs/")

    # 3. PostgreSQL 15 + PostGIS 3.4 + pgvector Live Verification
    print("\n🐘 STEP 3: POSTGRESQL + POSTGIS + PGVECTOR AUDIT")
    with connection.cursor() as cur:
        cur.execute("SELECT version();")
        pg_ver = cur.fetchone()[0]
        assert_check("PostgreSQL" in pg_ver, "Connected to PostgreSQL engine", pg_ver.split(',')[0])

        cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'postgis';")
        postgis_ext = cur.fetchone()
        assert_check(postgis_ext is not None, "PostGIS extension active", f"Version {postgis_ext[1] if postgis_ext else 'N/A'}")

        cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cur.fetchone()
        assert_check(vector_ext is not None, "pgvector extension active", f"Version {vector_ext[1] if vector_ext else 'N/A'}")

        # Test vector similarity calculation in SQL
        cur.execute("SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector AS dist;")
        dist = cur.fetchone()[0]
        assert_check(dist is not None, "pgvector cosine distance operator tested successfully")

    # 4. Daphne ASGI & Gunicorn High-Concurrency Workers
    print("\n⚡ STEP 4: ASGI HIGH-CONCURRENCY WORKERS AUDIT")
    gunicorn_conf = BASE_DIR / "gunicorn.conf.py"
    assert_check(gunicorn_conf.exists(), "Gunicorn production configuration exists", str(gunicorn_conf))
    assert_check("daphne" in settings.INSTALLED_APPS, "Daphne ASGI server in INSTALLED_APPS")
    assert_check("channels" in settings.INSTALLED_APPS, "Django Channels in INSTALLED_APPS")
    assert_check(hasattr(settings, "CHANNEL_LAYERS"), "CHANNEL_LAYERS configured for real-time fleet radar")

    # 5. Automated Backup & Disaster Recovery Scripts
    print("\n🛡️ STEP 5: AUTOMATED BACKUP & DISASTER RECOVERY AUDIT")
    backup_sh = BASE_DIR / "deploy" / "backup" / "backup_postgres.sh"
    restore_sh = BASE_DIR / "deploy" / "backup" / "restore_postgres.sh"
    entrypoint_sh = BASE_DIR / "deploy" / "backup" / "entrypoint_backup.sh"
    assert_check(backup_sh.exists(), "Automated backup script exists", str(backup_sh))
    assert_check(restore_sh.exists(), "Disaster recovery restore script exists", str(restore_sh))
    assert_check(entrypoint_sh.exists(), "Backup cron daemon entrypoint exists", str(entrypoint_sh))

    b_content = backup_sh.read_text(encoding='utf-8')
    assert_check("pg_dump" in b_content and "sha256sum" in b_content, "Backup script includes pg_dump and SHA-256 verification")
    assert_check("-mtime +14 -delete" in b_content, "Backup script implements automated retention pruning")

    # 6. Rathasārathi AI Operations Copilot (Groq Cloud)
    print("\n👑 STEP 6: RATHASĀRATHI AI (GROQ CLOUD) AUDIT")
    groq_key = getattr(settings, 'GROQ_API_KEY', '') or os.environ.get('GROQ_API_KEY', '')
    groq_model = getattr(settings, 'GROQ_MODEL', '') or os.environ.get('GROQ_MODEL', '')
    assert_check(bool(groq_key), "Groq API Key configured in production settings", f"Key length: {len(groq_key)} chars")
    assert_check(bool(groq_model), "Groq production model configured", groq_model)

    print("\n" + "=" * 80)
    print(f"🎉 PRODUCTION HARDENING AUDIT COMPLETE: ALL {checks_passed}/{total_checks} CHECKS PASSED (100%)!")
    print("🏆 SYSTEM IS READY FOR ZERO-DOWNTIME ENTERPRISE DEPLOYMENT!")
    print("=" * 80)


if __name__ == '__main__':
    audit_production_stack()
