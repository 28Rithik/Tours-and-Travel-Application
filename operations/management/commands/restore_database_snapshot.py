import os
import sys
import json
import shutil
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Safely verifies checksums and restores the TravelERP database from a snapshot backup."

    def add_arguments(self, parser):
        parser.add_argument(
            'snapshot_file',
            type=str,
            help='Path to the .sqlite3 snapshot file or snapshot name in backups/ directory.'
        )
        parser.add_argument(
            '--skip-checksum',
            action='store_true',
            help='Bypass SHA-256 metadata integrity verification.'
        )
        parser.add_argument(
            '--no-safety-backup',
            action='store_true',
            help='Skip creating an emergency pre-restore copy of the active database.'
        )

    def handle(self, *args, **options):
        snapshot_arg = options['snapshot_file']
        snapshot_path = Path(snapshot_arg)

        # Allow passing relative filename or full path
        if not snapshot_path.exists():
            candidate = Path(settings.BASE_DIR) / 'backups' / snapshot_arg
            if candidate.exists():
                snapshot_path = candidate
            else:
                raise CommandError(f"Snapshot file not found: {snapshot_arg}")

        # Check for matching metadata manifest
        meta_path = snapshot_path.with_suffix('.meta.json')
        if not options['skip_checksum'] and meta_path.exists():
            self.stdout.write(self.style.NOTICE(f"Verifying SHA-256 integrity from {meta_path.name}..."))
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                expected_sha256 = manifest.get('checksum_sha256')

                hasher = hashlib.sha256()
                with open(snapshot_path, 'rb') as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                actual_sha256 = hasher.hexdigest()

                if expected_sha256 != actual_sha256:
                    raise CommandError(
                        f"Checksum mismatch! Expected {expected_sha256}, got {actual_sha256}. "
                        "Snapshot may be corrupted. Use --skip-checksum to override."
                    )
                self.stdout.write(self.style.SUCCESS(f"✓ SHA-256 checksum verified: {actual_sha256[:16]}..."))
            except Exception as e:
                if isinstance(e, CommandError):
                    raise
                self.stdout.write(self.style.WARNING(f"Warning: Could not verify metadata ({e})"))

        # Verify snapshot integrity using SQLite PRAGMA
        self.stdout.write(self.style.NOTICE("Testing snapshot internal integrity..."))
        try:
            test_conn = sqlite3.connect(snapshot_path)
            cursor = test_conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            check_result = cursor.fetchone()[0]
            test_conn.close()
            if check_result != 'ok':
                raise CommandError(f"SQLite integrity check failed on snapshot: {check_result}")
            self.stdout.write(self.style.SUCCESS("✓ Snapshot SQLite integrity check: OK"))
        except Exception as e:
            if isinstance(e, CommandError):
                raise
            raise CommandError(f"Error checking snapshot: {e}")

        # Determine target database path
        db_conf = settings.DATABASES['default']
        if 'sqlite' not in db_conf.get('ENGINE', ''):
            raise CommandError(
                "Active database is not SQLite (e.g. PostgreSQL). "
                "For PostgreSQL, use pg_restore or psql. Refer to documentation/13_BACKUP_AND_DISASTER_RECOVERY_RUNBOOK.md."
            )

        active_db_path = Path(db_conf['NAME'])

        # Create emergency pre-restore safety copy of current DB
        if not options['no_safety_backup'] and active_db_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safety_copy = active_db_path.parent / f"db.pre_restore_safety_{timestamp}.sqlite3"
            self.stdout.write(self.style.NOTICE(f"Creating pre-restore safety copy: {safety_copy.name}"))
            shutil.copy2(active_db_path, safety_copy)

        # Close any open connections
        connection.close()

        # Perform atomic online restore using SQLite backup API
        self.stdout.write(self.style.NOTICE(f"Restoring {snapshot_path.name} -> {active_db_path.name}..."))
        src_conn = sqlite3.connect(snapshot_path)
        dst_conn = sqlite3.connect(active_db_path)

        with dst_conn:
            src_conn.backup(dst_conn, pages=100)

        dst_conn.close()
        src_conn.close()

        # Remove WAL & SHM files to ensure fresh clean connection
        for ext in ['-wal', '-shm']:
            aux = Path(str(active_db_path) + ext)
            if aux.exists():
                try:
                    aux.unlink()
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS(f"✓ Database successfully restored from {snapshot_path.name}!"))
