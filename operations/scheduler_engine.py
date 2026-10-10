"""
TravelERP Automated Background Scheduler Engine
Sivagayathiri Travels & Tours ERP

Automates critical enterprise background routines:
1. Automated Nightly Point-in-Time SQLite Database Snapshots (via sqlite3.backup API)
2. Automated Snapshot Rotation (Retention: 30 days, auto-prunes older snapshots)
3. Vehicle & Chauffeur Document Compliance Expiry Watchdog (30d, 15d, 7d, expired)
4. Automated Arattai & Email Incident Dispatch to Fleet Management Channels
"""

import os
import glob
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from django.conf import settings
from django.utils import timezone
from django.core.management import call_command
from django.db.models import Q

logger = logging.getLogger(__name__)


class TravelERPScheduler:
    """
    Automated job scheduler and watchdog engine for TravelERP.
    Can be run via cron, Windows Task Scheduler, background daemon, or 1-click admin API.
    """

    @classmethod
    def run_nightly_backup_job(cls, retention_days: int = 30) -> Dict[str, Any]:
        """
        Executes zero-lock database snapshot export and prunes backups older than retention_days.
        """
        start_time = time.time()
        logger.info("Executing scheduled database backup job...")

        try:
            # Call existing snapshot management command
            call_command('export_database_snapshot')
            backup_status = "success"
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": round(time.time() - start_time, 2)
            }

        # Locate latest snapshot and prune old snapshots
        backups_dir = settings.BASE_DIR / 'backups'
        snapshot_files = sorted(glob.glob(str(backups_dir / "*snapshot_*.sqlite3")), key=os.path.getmtime, reverse=True)

        latest_snapshot = snapshot_files[0] if snapshot_files else None
        latest_size_mb = round(os.path.getsize(latest_snapshot) / (1024 * 1024), 2) if latest_snapshot else 0

        # Retention pruning
        pruned_count = 0
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        for snap_path in snapshot_files[10:]:  # Always keep at least 10 latest snapshots
            file_mtime = datetime.fromtimestamp(os.path.getmtime(snap_path))
            if file_mtime < cutoff_date:
                try:
                    os.remove(snap_path)
                    manifest_path = snap_path.replace('.sqlite3', '_manifest.json')
                    if os.path.exists(manifest_path):
                        os.remove(manifest_path)
                    pruned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to prune old snapshot {snap_path}: {e}")

        duration = round(time.time() - start_time, 2)
        return {
            "status": "success",
            "latest_snapshot": os.path.basename(latest_snapshot) if latest_snapshot else None,
            "size_mb": latest_size_mb,
            "total_snapshots_retained": len(snapshot_files) - pruned_count,
            "pruned_old_snapshots": pruned_count,
            "duration_seconds": duration,
        }

    @classmethod
    def run_compliance_watchdog_job(cls) -> Dict[str, Any]:
        """
        Audits all vehicles and chauffeurs for compliance document expiry.
        Logs emergency incidents and dispatches sirens if critical documents expire within 7 days.
        """
        from core.models import Vehicle, Driver
        from operations.models import EmergencyIncidentAlert
        from integrations.arattai_service import ArattaiBusinessService

        today = timezone.localdate()
        date_30d = today + timedelta(days=30)
        date_7d = today + timedelta(days=7)

        vehicle_alerts: List[Dict[str, Any]] = []
        driver_alerts: List[Dict[str, Any]] = []

        # 1. Audit Vehicles
        vehicles = Vehicle.objects.filter(status__in=['available', 'on_trip', 'maintenance'])
        for v in vehicles:
            docs = [
                ('Insurance', getattr(v, 'insurance_expiry', None)),
                ('PUC Pollution', getattr(v, 'pollution_expiry', None)),
                ('Fitness Certificate (FC)', getattr(v, 'fc_expiry', None)),
                ('State Permit', getattr(v, 'permit_expiry', None)),
                ('Road Tax', getattr(v, 'tax_expiry', None)),
                ('RC Registration', getattr(v, 'rc_expiry', None)),
            ]
            for doc_name, expiry in docs:
                if not expiry:
                    continue
                days_left = (expiry - today).days
                if days_left <= 30:
                    severity = 'critical' if days_left <= 7 else ('high' if days_left <= 15 else 'medium')
                    status_text = f"EXPIRED ({abs(days_left)} days ago)" if days_left < 0 else f"Expires in {days_left} days"

                    alert_item = {
                        "type": "vehicle",
                        "vehicle_id": v.id,
                        "reg_no": v.registration_number,
                        "doc_name": doc_name,
                        "expiry_date": str(expiry),
                        "days_left": days_left,
                        "severity": severity,
                        "status_text": status_text,
                    }
                    vehicle_alerts.append(alert_item)

                    # Create Incident Alert for critical (<7 days) if not already created today
                    if days_left <= 7:
                        incident_title = f"{doc_name} {status_text} on {v.registration_number}"
                        assigned_driver = v.default_driver or Driver.objects.first()
                        if assigned_driver:
                            EmergencyIncidentAlert.objects.get_or_create(
                                vehicle=v,
                                driver=assigned_driver,
                                incident_type='other',
                                description=incident_title,
                                defaults={
                                    'severity': 'high' if days_left >= 0 else 'critical',
                                    'status': 'reported',
                                }
                            )

        # 2. Audit Drivers
        drivers = Driver.objects.exclude(status='inactive')
        for d in drivers:
            docs = [
                ('Driving License (TR)', getattr(d, 'license_validity_tr', None)),
                ('Driving License (NT)', getattr(d, 'license_validity_nt', None)),
            ]
            for doc_name, expiry in docs:
                if not expiry:
                    continue
                days_left = (expiry - today).days
                if days_left <= 30:
                    severity = 'critical' if days_left <= 7 else ('high' if days_left <= 15 else 'medium')
                    status_text = f"EXPIRED ({abs(days_left)} days ago)" if days_left < 0 else f"Expires in {days_left} days"

                    alert_item = {
                        "type": "driver",
                        "driver_id": d.id,
                        "name": d.name,
                        "phone": d.phone,
                        "doc_name": doc_name,
                        "expiry_date": str(expiry),
                        "days_left": days_left,
                        "severity": severity,
                        "status_text": status_text,
                    }
                    driver_alerts.append(alert_item)

        # 3. Dispatch to Arattai Fleet Channel if critical alerts exist
        critical_count = sum(1 for a in vehicle_alerts + driver_alerts if a['severity'] == 'critical')
        arattai_dispatched = False
        if critical_count > 0:
            msg = f"🚨 *TRAVELERP COMPLIANCE WATCHDOG ALERT*\n"
            msg += f"Found *{critical_count} critical document expirations* requiring immediate renewal:\n\n"
            for a in (vehicle_alerts + driver_alerts)[:5]:
                if a['type'] == 'vehicle':
                    msg += f"• 🚗 {a['reg_no']}: {a['doc_name']} — *{a['status_text']}*\n"
                else:
                    msg += f"• 👤 {a['name']} ({a['phone']}): {a['doc_name']} — *{a['status_text']}*\n"
            msg += f"\n👉 Review in Admin: /maintenance/compliance/"

            # Dispatch via Arattai Service
            ArattaiBusinessService.send_message(
                phone=getattr(settings, 'FLEET_CONTROL_ROOM_PHONE', '919876543210'),
                text=msg,
                message_type='emergency_sos'
            )
            arattai_dispatched = True

        return {
            "status": "success",
            "total_vehicle_alerts": len(vehicle_alerts),
            "total_driver_alerts": len(driver_alerts),
            "critical_count": critical_count,
            "vehicle_alerts": vehicle_alerts[:10],
            "driver_alerts": driver_alerts[:10],
            "arattai_dispatched": arattai_dispatched,
        }

    @classmethod
    def run_all_scheduled_tasks(cls) -> Dict[str, Any]:
        """Consolidated runner for nightly maintenance batch."""
        started_at = timezone.now()
        backup_result = cls.run_nightly_backup_job()
        watchdog_result = cls.run_compliance_watchdog_job()

        return {
            "status": "completed",
            "executed_at": started_at.isoformat(),
            "backup_job": backup_result,
            "compliance_watchdog": watchdog_result,
        }
