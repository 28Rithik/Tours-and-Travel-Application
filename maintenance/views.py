from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages

from core.models import Vehicle
from maintenance.services import check_compliance_expiries, check_preventive_maintenance_due
from maintenance.models import ServiceReminder, DefectTicket


@login_required
def compliance_and_maintenance_dashboard(request):
    """
    Control room dashboard for RTO document compliance, upcoming expirations,
    preventive maintenance schedules, and tyre/battery wear alerts.
    """
    threshold = int(request.GET.get('threshold', 30))
    compliance_data = check_compliance_expiries(threshold_days=threshold)
    maintenance_data = check_preventive_maintenance_due()

    open_defect_tickets = DefectTicket.objects.filter(status__in=['open', 'in_progress']).select_related('vehicle').order_by('-date_reported')

    context = {
        'threshold': threshold,
        'compliance': compliance_data,
        'maintenance': maintenance_data,
        'defect_tickets': open_defect_tickets,
        'expired_count': len(compliance_data['expired']),
        'critical_count': len(compliance_data['critical']),
        'warning_count': len(compliance_data['warning']),
        'services_due_count': len(maintenance_data['services_due']),
        'assets_due_count': len(maintenance_data['assets_due']),
    }
    return render(request, 'maintenance/compliance_dashboard.html', context)


@login_required
def api_compliance_summary(request):
    """JSON API endpoint returning real-time compliance health & alert counts."""
    data = check_compliance_expiries(threshold_days=30)
    return JsonResponse({
        'compliance_rate': data['compliance_rate'],
        'expired_count': len(data['expired']),
        'critical_count': len(data['critical']),
        'warning_count': len(data['warning']),
        'total_vehicles': data['total_vehicles_scanned'],
    })


@login_required
def api_send_renewal_warnings(request):
    """Triggers on-demand broadcast of RTO document expiry warnings & oil/tyre maintenance alerts."""
    from maintenance.services import send_compliance_renewal_warnings_alert
    result = send_compliance_renewal_warnings_alert()
    return JsonResponse(result)


# ==============================================================================
# INTERACTIVE 2D VEHICLE DAMAGE MARKER & RENTAL INSPECTION STUDIO
# ==============================================================================

@login_required
def damage_marker_studio_view(request):
    """
    Interactive 2D Vehicle Blueprint Damage Marker Studio.
    Allows vehicle inspectors, drivers, and rental dispatchers to click on body panels
    to tag scratches, dents, cracks, compare check-in vs check-out, and calculate deposit deductions.
    """
    from .models import VehicleDamageInspection
    from core.models import Vehicle
    from operations.models import Trip, Booking

    inspection_id = request.GET.get('inspection_id')
    vehicle_id = request.GET.get('vehicle_id')
    trip_id = request.GET.get('trip_id')
    baseline_id = request.GET.get('baseline_id')

    inspection = None
    if inspection_id:
        inspection = get_object_or_404(VehicleDamageInspection.objects.prefetch_related('markers'), pk=inspection_id)

    baseline_inspection = None
    if baseline_id:
        baseline_inspection = get_object_or_404(VehicleDamageInspection.objects.prefetch_related('markers'), pk=baseline_id)
    elif inspection and inspection.baseline_checkout:
        baseline_inspection = inspection.baseline_checkout

    selected_vehicle = None
    if inspection:
        selected_vehicle = inspection.vehicle
    elif vehicle_id:
        selected_vehicle = Vehicle.objects.filter(pk=vehicle_id).first()

    vehicles = Vehicle.objects.filter(status__in=['available', 'assigned', 'on_trip']).order_by('registration_number')
    recent_inspections = VehicleDamageInspection.objects.select_related('vehicle').order_by('-created_at')[:10]

    context = {
        'title': '2D Vehicle Damage Marker Studio',
        'inspection': inspection,
        'baseline_inspection': baseline_inspection,
        'selected_vehicle': selected_vehicle,
        'vehicles': vehicles,
        'recent_inspections': recent_inspections,
        'trip_id': trip_id,
    }
    return render(request, 'maintenance/damage_marker_studio.html', context)


@login_required
def api_damage_inspection_save(request):
    """
    Saves or updates a Vehicle Damage Inspection along with all pinpoint 2D markers.
    Auto-computes damage deductions against security deposit.
    """
    import json
    from decimal import Decimal
    from .models import VehicleDamageInspection, VehicleDamageMarker
    from core.models import Vehicle

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        vehicle_id = int(data.get('vehicle_id'))
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

        inspection_type = data.get('inspection_type', 'checkout')
        body_style = data.get('vehicle_body_style', 'suv')
        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        inspector_name = data.get('inspector_name', '').strip() or request.user.get_full_name() or request.user.username
        odometer = int(data.get('odometer_reading', vehicle.current_km or 0))
        fuel_pct = int(data.get('fuel_level_percent', 100))
        deposit_held = Decimal(str(data.get('security_deposit_held', '0.00') or '0.00'))
        notes = data.get('notes', '').strip()
        baseline_id = data.get('baseline_checkout_id')
        cust_sig = data.get('customer_signature_data', '')
        insp_sig = data.get('inspector_signature_data', '')

        baseline_checkout = None
        if baseline_id:
            baseline_checkout = VehicleDamageInspection.objects.filter(pk=baseline_id).first()

        inspection = VehicleDamageInspection.objects.create(
            vehicle=vehicle,
            inspection_type=inspection_type,
            vehicle_body_style=body_style,
            customer_name=customer_name,
            customer_phone=customer_phone,
            inspector_name=inspector_name,
            odometer_reading=odometer,
            fuel_level_percent=fuel_pct,
            baseline_checkout=baseline_checkout,
            security_deposit_held=deposit_held,
            deposit_status='held' if deposit_held > 0 else 'none',
            customer_signature_data=cust_sig,
            inspector_signature_data=insp_sig,
            notes=notes
        )

        # Update vehicle current km if higher
        if odometer > (vehicle.current_km or 0):
            vehicle.current_km = odometer
            vehicle.save(update_fields=['current_km'])

        # Save Markers
        markers_data = data.get('markers', [])
        total_new_cost = Decimal('0.00')

        for idx, m in enumerate(markers_data, start=1):
            cost = Decimal(str(m.get('estimated_repair_cost', '0.00') or '0.00'))
            is_new = bool(m.get('is_new_damage', False))
            is_pre = bool(m.get('is_pre_existing', False))
            if is_new:
                total_new_cost += cost

            VehicleDamageMarker.objects.create(
                inspection=inspection,
                marker_number=idx,
                damage_type=m.get('damage_type', 'scratch'),
                severity=m.get('severity', 'minor'),
                panel_zone=m.get('panel_zone', 'front_bumper'),
                x_percent=Decimal(str(round(float(m.get('x_percent', 50)), 2))),
                y_percent=Decimal(str(round(float(m.get('y_percent', 50)), 2))),
                view_angle=m.get('view_angle', 'top'),
                is_pre_existing=is_pre,
                is_new_damage=is_new,
                estimated_repair_cost=cost,
                photo_data_url=m.get('photo_data_url', ''),
                notes=m.get('notes', '')
            )

        # Recompute totals and deposit settlement
        inspection.compute_damage_totals()

        return JsonResponse({
            'status': 'success',
            'inspection_id': inspection.pk,
            'inspection_number': inspection.inspection_number,
            'total_markers': len(markers_data),
            'new_damage_deductions': float(inspection.new_damage_deductions),
            'deposit_refund_amount': float(inspection.deposit_refund_amount),
            'deposit_status': inspection.get_deposit_status_display(),
            'print_url': f"/maintenance/damage-inspection/{inspection.pk}/print/",
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def api_damage_inspection_detail(request, inspection_id):
    """Returns inspection details and all marker pinpoint coordinates for rendering/diff."""
    from .models import VehicleDamageInspection
    inspection = get_object_or_404(VehicleDamageInspection.objects.prefetch_related('markers'), pk=inspection_id)

    markers_list = []
    for m in inspection.markers.all():
        markers_list.append({
            'marker_number': m.marker_number,
            'damage_type': m.damage_type,
            'damage_type_display': m.get_damage_type_display(),
            'severity': m.severity,
            'severity_display': m.get_severity_display(),
            'panel_zone': m.panel_zone,
            'panel_zone_display': m.get_panel_zone_display(),
            'x_percent': float(m.x_percent),
            'y_percent': float(m.y_percent),
            'view_angle': m.view_angle,
            'is_pre_existing': m.is_pre_existing,
            'is_new_damage': m.is_new_damage,
            'estimated_repair_cost': float(m.estimated_repair_cost),
            'photo_data_url': m.photo_data_url,
            'notes': m.notes,
        })

    return JsonResponse({
        'status': 'success',
        'inspection_id': inspection.pk,
        'inspection_number': inspection.inspection_number,
        'vehicle': {
            'id': inspection.vehicle.pk,
            'registration': inspection.vehicle.registration_number,
            'model': f"{inspection.vehicle.brand} {inspection.vehicle.model}".strip(),
            'body_style': inspection.vehicle_body_style,
        },
        'inspection_type': inspection.inspection_type,
        'customer_name': inspection.customer_name,
        'customer_phone': inspection.customer_phone,
        'odometer_reading': inspection.odometer_reading,
        'fuel_level_percent': inspection.fuel_level_percent,
        'security_deposit_held': float(inspection.security_deposit_held),
        'new_damage_deductions': float(inspection.new_damage_deductions),
        'deposit_refund_amount': float(inspection.deposit_refund_amount),
        'deposit_status': inspection.deposit_status,
        'created_at': inspection.created_at.strftime('%Y-%m-%d %H:%M'),
        'markers': markers_list,
    })


@login_required
def damage_inspection_print_certificate(request, inspection_id):
    """Renders a print-ready digital Handover & Vehicle Damage Inspection Certificate."""
    from .models import VehicleDamageInspection
    inspection = get_object_or_404(VehicleDamageInspection.objects.prefetch_related('markers').select_related('vehicle', 'baseline_checkout'), pk=inspection_id)
    return render(request, 'maintenance/damage_inspection_certificate.html', {'inspection': inspection})


