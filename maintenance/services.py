import datetime
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q

from core.models import Vehicle, Driver
from maintenance.models import (
    ComplianceDocument,
    ServiceRecord,
    VehicleAsset,
    DefectTicket,
    ServiceReminder,
)


def check_compliance_expiries(threshold_days=30):
    """
    Scans all fleet vehicles and drivers for upcoming or overdue document expiries.
    Categories:
      - 'expired': date < today (CRITICAL / ILLEGAL TO OPERATE)
      - 'critical': 0 <= date - today <= 7 days (URGENT RENEWAL)
      - 'warning': 7 < date - today <= threshold_days (UPCOMING RENEWAL)
    """
    today = timezone.now().date()
    max_threshold = today + datetime.timedelta(days=threshold_days)

    alerts = {
        'expired': [],
        'critical': [],
        'warning': [],
        'total_vehicles_scanned': 0,
        'total_drivers_scanned': 0,
        'compliant_vehicles_count': 0,
        'non_compliant_vehicles_count': 0,
    }

    # 1. Scan Vehicles
    vehicles = Vehicle.objects.filter(status__in=['available', 'active', 'on_trip']).prefetch_related('compliance_documents')
    alerts['total_vehicles_scanned'] = vehicles.count()

    doc_fields = [
        ('insurance_expiry', 'Insurance Policy'),
        ('fc_expiry', 'Fitness Certificate (FC)'),
        ('permit_expiry', 'National/State Permit'),
        ('tax_expiry', 'Road Tax'),
        ('pollution_expiry', 'Pollution (PUC)'),
    ]

    for veh in vehicles:
        veh_has_issue = False
        for field_name, doc_label in doc_fields:
            exp_date = getattr(veh, field_name, None)
            if not exp_date:
                continue

            days_left = (exp_date - today).days
            item = {
                'entity_type': 'vehicle',
                'id': veh.id,
                'identifier': veh.registration_number,
                'model_name': veh.vehicle_type.name if veh.vehicle_type else 'Fleet Vehicle',
                'doc_type': doc_label,
                'expiry_date': exp_date,
                'days_left': days_left,
            }

            if days_left < 0:
                item['urgency'] = 'expired'
                alerts['expired'].append(item)
                veh_has_issue = True
            elif days_left <= 7:
                item['urgency'] = 'critical'
                alerts['critical'].append(item)
                veh_has_issue = True
            elif days_left <= threshold_days:
                item['urgency'] = 'warning'
                alerts['warning'].append(item)

        if veh_has_issue:
            alerts['non_compliant_vehicles_count'] += 1
        else:
            alerts['compliant_vehicles_count'] += 1

    # 2. Scan Drivers
    drivers = Driver.objects.filter(status='active')
    alerts['total_drivers_scanned'] = drivers.count()

    driver_fields = [
        ('license_validity_nt', 'Non-Transport License (NT)'),
        ('license_validity_tr', 'Transport License Badge (TR)'),
    ]

    for d in drivers:
        for field_name, doc_label in driver_fields:
            exp_date = getattr(d, field_name, None)
            if not exp_date:
                continue

            days_left = (exp_date - today).days
            item = {
                'entity_type': 'driver',
                'id': d.id,
                'identifier': d.name,
                'model_name': f"Phone: {d.phone or 'N/A'}",
                'doc_type': doc_label,
                'expiry_date': exp_date,
                'days_left': days_left,
            }

            if days_left < 0:
                item['urgency'] = 'expired'
                alerts['expired'].append(item)
            elif days_left <= 7:
                item['urgency'] = 'critical'
                alerts['critical'].append(item)
            elif days_left <= threshold_days:
                item['urgency'] = 'warning'
                alerts['warning'].append(item)

    # Sort each category by days_left ascending
    for cat in ['expired', 'critical', 'warning']:
        alerts[cat].sort(key=lambda x: x['days_left'])

    total_scanned = alerts['total_vehicles_scanned'] + alerts['total_drivers_scanned']
    total_violations = len(alerts['expired'])
    alerts['compliance_rate'] = round(
        ((total_scanned - total_violations) / total_scanned * 100), 1
    ) if total_scanned > 0 else 100.0

    return alerts


def verify_trip_dispatch_compliance(vehicle, driver, start_date, end_date=None):
    """
    Strict safety gate: verifies whether a vehicle and driver are legally compliant
    to operate through the trip's end_date.
    Returns: (is_compliant: bool, violations: list[str])
    """
    violations = []
    effective_end = end_date or start_date
    today = timezone.now().date()

    if not vehicle:
        return False, ["No vehicle assigned to trip."]

    # 1. Vehicle Checks
    if vehicle.status == 'maintenance':
        violations.append(f"Vehicle {vehicle.registration_number} is currently in the workshop under maintenance.")

    # Check unaddressed defect tickets
    open_defects = vehicle.defect_tickets.filter(status__in=['open', 'in_progress'])
    if open_defects.exists():
        defect_descs = ", ".join(d.description[:30] for d in open_defects[:2])
        violations.append(f"Vehicle {vehicle.registration_number} has unresolved defects: {defect_descs}")

    if vehicle.fc_expiry and vehicle.fc_expiry < effective_end:
        violations.append(f"Vehicle FC (Fitness Certificate) expired on {vehicle.fc_expiry} (Trip ends: {effective_end}).")
    if vehicle.insurance_expiry and vehicle.insurance_expiry < effective_end:
        violations.append(f"Vehicle Insurance policy expired on {vehicle.insurance_expiry} (Trip ends: {effective_end}).")
    if vehicle.permit_expiry and vehicle.permit_expiry < effective_end:
        violations.append(f"Vehicle Permit expired on {vehicle.permit_expiry} (Trip ends: {effective_end}).")
    if vehicle.tax_expiry and vehicle.tax_expiry < effective_end:
        violations.append(f"Vehicle Road Tax expired on {vehicle.tax_expiry} (Trip ends: {effective_end}).")
    if vehicle.pollution_expiry and vehicle.pollution_expiry < effective_end:
        violations.append(f"Vehicle Pollution (PUC) certificate expired on {vehicle.pollution_expiry} (Trip ends: {effective_end}).")

    # 2. Driver Checks
    if driver:
        if driver.status != 'active':
            violations.append(f"Driver {driver.name} status is '{driver.status}', not active.")
        if driver.license_validity_tr and driver.license_validity_tr < effective_end:
            violations.append(f"Driver {driver.name}'s Commercial Transport License expired on {driver.license_validity_tr}.")

    return len(violations) == 0, violations


def check_preventive_maintenance_due(vehicle_id=None):
    """
    Checks odometer against ServiceReminder intervals and tyre/battery asset lifespans.
    Returns itemized maintenance tasks due and automatically generates DefectTickets for urgent items.
    """
    reminders = ServiceReminder.objects.filter(is_active=True).select_related('vehicle')
    if vehicle_id:
        reminders = reminders.filter(vehicle_id=vehicle_id)

    tasks_due = []
    for r in reminders:
        veh = r.vehicle
        due_km = r.due_km
        curr_km = veh.current_km
        km_left = due_km - curr_km

        if km_left <= 0:
            status = 'overdue'
        elif km_left <= 500:
            status = 'due_soon'
        else:
            status = 'upcoming'

        if status in ['overdue', 'due_soon']:
            task_info = {
                'reminder_id': r.id,
                'vehicle': veh,
                'task_name': r.service_task,
                'current_km': curr_km,
                'due_km': due_km,
                'km_difference': km_left,
                'status': status,
                'notes': r.notes,
            }
            tasks_due.append(task_info)

            # Auto-create DefectTicket if overdue and no open ticket exists
            if status == 'overdue':
                ticket_desc = f"Preventive Maintenance Due: {r.service_task} (Overdue by {abs(km_left)} KM)"
                existing = DefectTicket.objects.filter(
                    vehicle=veh,
                    description__icontains=r.service_task,
                    status__in=['open', 'in_progress']
                ).exists()
                if not existing:
                    DefectTicket.objects.create(
                        vehicle=veh,
                        reported_by='Maintenance Scheduler Engine',
                        description=ticket_desc,
                        status='open',
                        notes=f"Auto-generated because current KM ({curr_km}) exceeded service threshold ({due_km})."
                    )

    # Check Tyre & Battery Wear
    assets_due = []
    assets = VehicleAsset.objects.filter(status='in_use').select_related('vehicle')
    if vehicle_id:
        assets = assets.filter(vehicle_id=vehicle_id)

    for asset in assets:
        if asset.needs_replacement:
            assets_due.append({
                'asset_id': asset.id,
                'asset_type': asset.get_asset_type_display(),
                'serial_number': asset.serial_number,
                'vehicle': asset.vehicle,
                'position': asset.get_position_display(),
                'current_run_km': asset.current_run_km,
                'expected_life_km': asset.expected_life_km,
            })

    return {
        'services_due': tasks_due,
        'assets_due': assets_due,
        'total_maintenance_alerts': len(tasks_due) + len(assets_due),
    }


def send_compliance_renewal_warnings_alert():
    """
    RTO Compliance Watchdog & Maintenance Alert Engine:
    Scans all vehicles & drivers, compiles imminent RTO expiries (<=7 days, <=30 days)
    plus urgent oil/tyre maintenance tasks, and dispatches proactive alert broadcasts.
    """
    from integrations.communication import send_whatsapp_message, send_email_notification
    from django.conf import settings

    expiries = check_compliance_expiries()
    maintenance = check_preventive_maintenance_due()

    critical_count = len(expiries['critical'])
    warning_count = len(expiries['warning'])
    expired_count = len(expiries['expired'])
    maint_count = maintenance['total_maintenance_alerts']

    if critical_count == 0 and warning_count == 0 and expired_count == 0 and maint_count == 0:
        return {'status': 'all_healthy', 'message': 'All fleet compliance and maintenance schedules are healthy.'}

    control_room_phone = getattr(settings, 'FLEET_CONTROL_ROOM_PHONE', '919876543210')
    control_room_email = getattr(settings, 'FLEET_CONTROL_ROOM_EMAIL', 'ops@sivagayathiritravels.com')

    msg_lines = [
        "🚨 *SIVAGAYATHIRI RTO WATCHDOG & MAINTENANCE ALERT* 🚨\n",
        f"• *Fleet Compliance Rate:* {expiries['compliance_rate']}%",
        f"• *Expired Documents (Hard-Locked):* {expired_count}",
        f"• *Critical Expiries (Due in <= 7 Days):* {critical_count}",
        f"• *Upcoming Expiries (Due in <= 30 Days):* {warning_count}",
        f"• *Oil / Tyre Maintenance Due:* {maint_count}\n"
    ]

    if expiries['critical']:
        msg_lines.append("⚠️ *Critical Document Renewals:*")
        for item in expiries['critical'][:5]:
            msg_lines.append(f"  - {item['entity_name']} ({item['doc_type']}): Due in {item['days_remaining']} days ({item['expiry_date']})")

    if maintenance['services_due']:
        msg_lines.append("\n🛠️ *Preventive Maintenance Due:*")
        for s in maintenance['services_due'][:4]:
            msg_lines.append(f"  - {s['vehicle'].registration_number}: {s['task_name']} ({s['status'].replace('_', ' ').upper()})")

    if maintenance['assets_due']:
        msg_lines.append("\n🚗 *Tyre / Battery Wear Alert:*")
        for a in maintenance['assets_due'][:3]:
            msg_lines.append(f"  - {a['vehicle'].registration_number}: {a['asset_type']} #{a['serial_number']} ({a['position']}) reached life limit")

    msg_lines.append("\n🔗 View live dashboard: http://127.0.0.1:8000/maintenance/compliance/")
    full_message = "\n".join(msg_lines)

    wa_result = send_whatsapp_message(control_room_phone, full_message)
    email_result = send_email_notification(
        control_room_email,
        f"⚠️ RTO Compliance Watchdog: {critical_count + expired_count} Critical Expiries & Maintenance Alerts",
        full_message.replace('\n', '<br>')
    )

    return {
        'status': 'dispatched',
        'expired_count': expired_count,
        'critical_count': critical_count,
        'warning_count': warning_count,
        'maintenance_count': maint_count,
        'whatsapp_result': wa_result,
        'email_result': email_result
    }

