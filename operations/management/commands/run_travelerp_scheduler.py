"""
Django Management Command: run_travelerp_scheduler
Sivagayathiri Travels & Tours ERP

Runs automated background maintenance:
1. Automated Nightly Database Snapshots & Retention Pruning
2. Fleet & Driver Document Compliance Watchdog
3. Arattai & WhatsApp Incident Escalation

Usage:
  python manage.py run_travelerp_scheduler --once
  python manage.py run_travelerp_scheduler --daemon
"""

import time
from datetime import datetime
from django.core.management.base import BaseCommand
from operations.scheduler_engine import TravelERPScheduler


class Command(BaseCommand):
    help = 'Executes automated nightly backup snapshots, compliance watchdog, and alerts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Runs all scheduled tasks once and exits immediately.'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Runs as a background daemon, executing scheduled tasks at 02:00 AM daily.'
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Retention period in days for snapshot backups (default: 30 days).'
        )

    def handle(self, *args, **options):
        once = options.get('once')
        daemon = options.get('daemon')
        retention = options.get('retention_days', 30)

        if not daemon:
            # Run once mode
            self.stdout.write(self.style.MIGRATE_HEADING("== Running TravelERP Automated Maintenance Tasks =="))
            res = TravelERPScheduler.run_all_scheduled_tasks()
            
            b = res.get('backup_job', {})
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Database Backup: {b.get('status')} | File: {b.get('latest_snapshot')} ({b.get('size_mb')} MB) | Retained: {b.get('total_snapshots_retained')} snapshots"
            ))

            w = res.get('compliance_watchdog', {})
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Compliance Watchdog: {w.get('status')} | Vehicle Alerts: {w.get('total_vehicle_alerts')} | Driver Alerts: {w.get('total_driver_alerts')} | Critical: {w.get('critical_count')}"
            ))

            if w.get('arattai_dispatched'):
                self.stdout.write(self.style.NOTICE("   -> Dispatched Critical Expiry Sirens via Zoho Arattai Gateway!"))

            self.stdout.write(self.style.SUCCESS("== Scheduled Maintenance Completed Successfully =="))
            return

        # Daemon mode
        self.stdout.write(self.style.NOTICE("Starting TravelERP Scheduler in daemon mode. Target time: 02:00 AM daily."))
        last_run_day = None

        while True:
            now = datetime.now()
            # Run at 02:00 AM daily
            if now.hour == 2 and now.day != last_run_day:
                self.stdout.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Triggering scheduled nightly maintenance...")
                try:
                    res = TravelERPScheduler.run_all_scheduled_tasks()
                    self.stdout.write(f"[OK] Nightly batch completed: {res.get('status')}")
                    last_run_day = now.day
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error during scheduled batch: {e}"))
            
            # Sleep 60 seconds
            time.sleep(60)
