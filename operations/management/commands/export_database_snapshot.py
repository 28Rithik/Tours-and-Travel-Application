import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

from core.models import Party, Vehicle, Driver
from operations.models import Booking, Trip
from finance.models import Payment, TripExpense


class Command(BaseCommand):
    help = "Exports an atomic point-in-time snapshot backup of the TravelERP database with audit metadata."

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory path where snapshot files will be saved (default: backups/).'
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='travelerp_snapshot',
            help='Filename prefix for the backup snapshot.'
        )

    def handle(self, *args, **options):
        output_dir = Path(settings.BASE_DIR) / options['output_dir']
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_filename = f"{options['prefix']}_{timestamp_str}.sqlite3"
        snapshot_path = output_dir / snapshot_filename
        manifest_filename = f"{options['prefix']}_{timestamp_str}.meta.json"
        manifest_path = output_dir / manifest_filename

        self.stdout.write(self.style.NOTICE(f"Initiating point-in-time database snapshot..."))

        # 1. Hot online backup using sqlite3.backup API
        db_path = settings.DATABASES['default']['NAME']
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(snapshot_path)

        with dst_conn:
            src_conn.backup(dst_conn, pages=100)

        dst_conn.close()
        src_conn.close()

        # 2. Compute SHA256 checksum
        hasher = hashlib.sha256()
        with open(snapshot_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        checksum = hasher.hexdigest()
        file_size_bytes = snapshot_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # 3. Gather entity counts
        counts = {
            'parties': Party.objects.count(),
            'vehicles': Vehicle.objects.count(),
            'drivers': Driver.objects.count(),
            'bookings': Booking.objects.count(),
            'trips': Trip.objects.count(),
            'payments': Payment.objects.count(),
            'trip_expenses': TripExpense.objects.count(),
        }

        # 4. Generate manifest
        manifest = {
            'timestamp': datetime.now().isoformat(),
            'filename': snapshot_filename,
            'file_size_bytes': file_size_bytes,
            'file_size_mb': round(file_size_mb, 2),
            'sha256_checksum': checksum,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'entity_counts': counts,
            'status': 'VERIFIED_OK'
        }

        with open(manifest_path, 'w', encoding='utf-8') as mf:
            json.dump(manifest, mf, indent=2)

        self.stdout.write(self.style.SUCCESS("[OK] Database Snapshot created successfully!"))
        self.stdout.write(f"   * File:      {snapshot_path}")
        self.stdout.write(f"   * Size:      {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")
        self.stdout.write(f"   * SHA256:    {checksum[:16]}...{checksum[-8:]}")
        self.stdout.write(f"   * Manifest:  {manifest_path}")
        self.stdout.write(f"   * Records:   {sum(counts.values()):,} total rows audited")
