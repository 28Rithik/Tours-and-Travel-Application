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


# ==============================================================================
# PHASE 6: 2D AXLE & TIRE HEALTH STUDIO & FLEET PM ENGINE VIEWS
# ==============================================================================

@login_required
def tire_studio_view(request):
    """
    Interactive 2D Axle & Tire Health Studio.
    Provides visual blueprint of vehicle wheel assemblies (Sedan, SUV, Coach),
    real-time tread wear progress gauges, 1-click rotation/retread actions,
    and fleet PM health metrics.
    """
    from decimal import Decimal
    from .models import VehicleAsset, ServiceReminder, DefectTicket, TireInspectionLog
    from .pm_engine import evaluate_fleet_pm_triggers
    from core.models import Vehicle

    vehicle_id = request.GET.get('vehicle_id')
    vehicles = Vehicle.objects.filter(status__in=['available', 'assigned', 'on_trip', 'maintenance']).order_by('registration_number')

    selected_vehicle = None
    if vehicle_id:
        selected_vehicle = Vehicle.objects.filter(pk=vehicle_id).first()
    if not selected_vehicle and vehicles.exists():
        selected_vehicle = vehicles.first()

    # Mounted tires on selected vehicle
    mounted_tires = []
    spare_tires = []
    if selected_vehicle:
        mounted_tires = VehicleAsset.objects.filter(
            vehicle=selected_vehicle,
            asset_type='tyre',
            status='in_use'
        ).order_by('position')

        spare_tires = VehicleAsset.objects.filter(
            vehicle=selected_vehicle,
            asset_type='tyre',
            status='spare'
        )

    # General fleet metrics
    total_tires_monitored = VehicleAsset.objects.filter(asset_type='tyre').count()
    critical_tires_count = VehicleAsset.objects.filter(
        asset_type='tyre',
        status='in_use',
        current_tread_depth_mm__lte=Decimal('2.50')
    ).count()
    retreading_tires_count = VehicleAsset.objects.filter(
        asset_type='tyre',
        status='retreading'
    ).count()
    overdue_pm_count = DefectTicket.objects.filter(
        status__in=['open', 'in_progress'],
        reported_by__in=['Fleet PM Engine', 'Tire Safety Engine']
    ).count()

    # Recent inspections
    recent_inspections = TireInspectionLog.objects.select_related('asset', 'asset__vehicle').order_by('-created_at')[:8]

    context = {
        'title': '2D Axle & Tire Health Studio',
        'vehicles': vehicles,
        'selected_vehicle': selected_vehicle,
        'mounted_tires': mounted_tires,
        'spare_tires': spare_tires,
        'total_tires_monitored': total_tires_monitored,
        'critical_tires_count': critical_tires_count,
        'retreading_tires_count': retreading_tires_count,
        'overdue_pm_count': overdue_pm_count,
        'recent_inspections': recent_inspections,
    }
    return render(request, 'maintenance/tire_studio.html', context)


@login_required
def api_vehicle_tire_schematic(request, vehicle_id):
    """
    Returns JSON array of all mounted & spare tires for a given vehicle
    formatted for the 2D visual chassis diagram.
    """
    from decimal import Decimal
    from core.models import Vehicle
    from .models import VehicleAsset

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    tires = VehicleAsset.objects.filter(vehicle=vehicle, asset_type='tyre').order_by('position')

    tires_data = []
    for t in tires:
        tires_data.append({
            'id': t.id,
            'serial_number': t.serial_number,
            'brand': t.brand or "Standard",
            'size': t.model_or_size or "",
            'position': t.position,
            'position_display': t.get_position_display(),
            'status': t.status,
            'status_display': t.get_status_display(),
            'current_tread_depth_mm': float(t.current_tread_depth_mm or Decimal('12.00')),
            'original_tread_depth_mm': float(t.original_tread_depth_mm or Decimal('12.00')),
            'tread_wear_percent': t.tread_wear_percent,
            'psi_pressure': t.psi_pressure,
            'current_run_km': t.current_run_km,
            'expected_life_km': t.expected_life_km or 40000,
            'retread_count': t.retread_count,
            'cost_per_km': float(t.cost_per_km),
            'health_status': t.health_status,
            'is_critical': t.is_critical_tread,
            'is_warning': t.is_warning_tread,
        })

    return JsonResponse({
        'status': 'success',
        'vehicle': {
            'id': vehicle.id,
            'registration': vehicle.registration_number,
            'brand_model': f"{vehicle.brand} {vehicle.model}".strip(),
            'current_km': vehicle.current_km,
        },
        'tires': tires_data,
        'total_tires': len(tires_data),
    })


@login_required
def api_tire_inspect(request):
    """POST endpoint to log physical tread & PSI inspection for a tyre."""
    import json
    from decimal import Decimal
    from .pm_engine import log_tire_inspection

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        asset_id = int(data.get('asset_id'))
        tread_mm = Decimal(str(data.get('tread_depth_mm', '10.00')))
        psi = int(data.get('psi_pressure')) if data.get('psi_pressure') else None
        odometer = int(data.get('odometer')) if data.get('odometer') else None
        inspector = data.get('inspector_name', '').strip() or request.user.get_full_name() or request.user.username
        notes = data.get('notes', '').strip()
        action = data.get('action_taken', 'none')
        irregular = bool(data.get('has_irregular_wear', False))

        res = log_tire_inspection(
            asset_id=asset_id,
            tread_depth_mm=tread_mm,
            psi_pressure=psi,
            odometer=odometer,
            inspector_name=inspector,
            has_irregular_wear=irregular,
            action_taken=action,
            notes=notes
        )
        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def api_tire_rotate(request):
    """POST endpoint to rotate tyre positions."""
    import json
    from .pm_engine import rotate_tire_asset

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        asset_id = int(data.get('asset_id'))
        to_position = data.get('to_position')
        notes = data.get('notes', '').strip()
        odometer = int(data.get('odometer')) if data.get('odometer') else None

        res = rotate_tire_asset(asset_id=asset_id, to_position=to_position, odometer=odometer, mechanic_notes=notes)
        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def api_tire_retread(request):
    """POST endpoint to send tyre for retread or return from retread."""
    import json
    from decimal import Decimal
    from .pm_engine import send_tire_for_retread, return_tire_from_retread

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        action = data.get('action', 'send')
        asset_id = int(data.get('asset_id'))

        if action == 'send':
            vendor = data.get('vendor_name', '').strip()
            notes = data.get('notes', '').strip()
            res = send_tire_for_retread(asset_id=asset_id, vendor_name=vendor, notes=notes)
        elif action == 'return':
            new_tread = Decimal(str(data.get('new_tread_depth_mm', '10.00')))
            cost = Decimal(str(data.get('cost', '0.00')))
            notes = data.get('notes', '').strip()
            res = return_tire_from_retread(asset_id=asset_id, new_tread_depth_mm=new_tread, cost=cost, notes=notes)
        else:
            return JsonResponse({'status': 'error', 'message': f"Unknown action: {action}"}, status=400)

        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def api_pm_engine_evaluate(request):
    """POST endpoint to trigger fleet-wide preventative maintenance and tire safety evaluation."""
    from .pm_engine import evaluate_fleet_pm_triggers

    vehicle_id = request.POST.get('vehicle_id') or request.GET.get('vehicle_id')
    v_id = int(vehicle_id) if vehicle_id else None

    result = evaluate_fleet_pm_triggers(vehicle_id=v_id, create_tickets=True)
    return JsonResponse(result)


