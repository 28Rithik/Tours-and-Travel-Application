"""
operations/management/commands/run_geofence_daemon.py

Continuous Autonomous Background Safety Daemon for TravelERP.
Scans active fleet telematics coordinates, checks geofence perimeter violations,
zone overspeeding, and route corridor deviations, triggering automatic alerts.
"""

import time
import sys
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max

from operations.models import VehicleTelematicsPing, GeofenceZone, EmergencyIncidentAlert
from operations.geofence_engine import GeofenceSafetyEngine

logger = logging.getLogger('operations.geofence.daemon')


class Command(BaseCommand):
    help = 'Runs the autonomous 24/7 Geofence & Fleet Safety Watchdog Daemon'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Polling interval in seconds between evaluation cycles (default: 5)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Execute a single evaluation cycle and exit immediately (useful for testing and cron)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print detailed per-vehicle telemetry diagnostics'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        verbose = options['verbose']

        self.stdout.write(self.style.SUCCESS(
            "========================================================================\n"
            "[*] SIVAGAYATHIRI TRAVELS - AUTONOMOUS GEOFENCE & SAFETY DAEMON\n"
            f"    Cycle Interval: {interval}s | Mode: {'Single-Shot' if run_once else 'Continuous Watchdog'}\n"
            "========================================================================"
        ))

        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                now_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

                # Find latest telematics ping per vehicle
                latest_ping_ids = (
                    VehicleTelematicsPing.objects
                    .values('vehicle_id')
                    .annotate(max_id=Max('id'))
                    .values_list('max_id', flat=True)
                )

                latest_pings = (
                    VehicleTelematicsPing.objects
                    .filter(id__in=latest_ping_ids)
                    .select_related('vehicle', 'trip')
                )

                vehicles_scanned = 0
                violations_count = 0
                incidents_created = 0

                for ping in latest_pings:
                    vehicles_scanned += 1
                    try:
                        res = GeofenceSafetyEngine.evaluate_ping(ping)
                        if res.get('violations_count', 0) > 0:
                            violations_count += res['violations_count']
                            if res.get('incident_created_id'):
                                incidents_created += 1
                                self.stdout.write(self.style.ERROR(
                                    f"[{now_str}] [!] CRITICAL INCIDENT RAISED: {res['incident_created_id']} "
                                    f"for {ping.vehicle.registration_number}"
                                ))

                            if verbose:
                                for v in res.get('violations', []):
                                    self.stdout.write(self.style.WARNING(
                                        f"   -> Violation: {v.get('type')} on {ping.vehicle.registration_number} "
                                        f"({v.get('status', 'logged')})"
                                    ))
                    except Exception as err:
                        logger.exception("Error evaluating ping %s: %s", ping.id, err)
                        if verbose:
                            self.stdout.write(self.style.ERROR(f"Error evaluating {ping.vehicle.registration_number}: {err}"))

                # Summary output for cycle
                status_color = self.style.SUCCESS if violations_count == 0 else self.style.WARNING
                self.stdout.write(status_color(
                    f"[{now_str}] Cycle #{cycle_count:04d} Completed: Scanned {vehicles_scanned} vehicles | "
                    f"Violations: {violations_count} | Incidents Raised: {incidents_created}"
                ))

                if run_once:
                    self.stdout.write(self.style.SUCCESS("Single-shot execution finished successfully."))
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.NOTICE("\n[!] Geofence safety daemon terminated by user."))
            sys.exit(0)
