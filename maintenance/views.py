from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from core.decorators import require_staff_capability

from core.models import Vehicle
from maintenance.services import check_compliance_expiries, check_preventive_maintenance_due
from maintenance.models import ServiceReminder, DefectTicket


@login_required
@require_staff_capability('rto_compliance_ledger')
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
@require_staff_capability('tire_health_audit')
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
@require_staff_capability('tire_health_audit')
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
@require_staff_capability('tire_health_audit')
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
@require_staff_capability('tire_health_audit')
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
@require_staff_capability('tire_health_audit')
def api_pm_engine_evaluate(request):
    """POST endpoint to trigger fleet-wide preventative maintenance and tire safety evaluation."""
    from .pm_engine import evaluate_fleet_pm_triggers

    vehicle_id = request.POST.get('vehicle_id') or request.GET.get('vehicle_id')
    v_id = int(vehicle_id) if vehicle_id else None

    result = evaluate_fleet_pm_triggers(vehicle_id=v_id, create_tickets=True)
    return JsonResponse(result)


# ==============================================================================
# WORKSHOP MECHANIC STUDIO & QR BARCODE SPARE PARTS CHECKOUT
# ==============================================================================

@login_required
@require_staff_capability('maintenance_work_orders')
def workshop_mechanic_studio_view(request):
    """
    Mobile-Touch Garage Workshop Studio & QR Barcode Parts Checkout Cockpit.
    Enables garage floor mechanics, store keepers, and fleet managers to track job cards,
    allocate garage bays, scan QR barcodes to check out parts, and prevent parts inventory leakage.
    """
    from decimal import Decimal
    from django.db.models import Sum, Q, F
    from .models import ServiceRecord, PartInventory, SparePart, SparePartUsageLog, PartPurchaseRequisition
    from core.models import Vehicle
    from django.contrib.auth.models import User
    from core.depot_scoping import DEPOT_CHOICES, DEPOT_CHENNAI

    status_filter = request.GET.get('status', 'active')
    depot_filter = request.GET.get('depot', '')
    priority_filter = request.GET.get('priority', '')
    search_q = request.GET.get('q', '').strip()
    selected_job_card_id = request.GET.get('job_card_id')

    qs = ServiceRecord.objects.select_related('vehicle', 'assigned_mechanic', 'defect_ticket').prefetch_related('spare_parts__inventory_item', 'part_usage_logs').order_by('-created_at')

    if status_filter == 'active':
        qs = qs.filter(status__in=['open', 'in_progress', 'awaiting_parts', 'quality_check'])
    elif status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    if depot_filter and depot_filter != 'all':
        qs = qs.filter(base_depot=depot_filter)

    if priority_filter and priority_filter != 'all':
        qs = qs.filter(priority=priority_filter)

    if search_q:
        qs = qs.filter(
            Q(job_card_number__icontains=search_q) |
            Q(vehicle__registration_number__icontains=search_q) |
            Q(mechanic_name__icontains=search_q) |
            Q(garage_name__icontains=search_q) |
            Q(description__icontains=search_q)
        )

    job_cards = list(qs[:50])

    active_job_card = None
    if selected_job_card_id:
        active_job_card = ServiceRecord.objects.filter(pk=selected_job_card_id).prefetch_related('spare_parts__inventory_item', 'part_usage_logs').first()
    if not active_job_card and job_cards:
        active_job_card = job_cards[0]

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    active_job_cards_count = ServiceRecord.objects.filter(status__in=['open', 'in_progress', 'awaiting_parts', 'quality_check']).count()
    grounded_vehicles_count = Vehicle.objects.filter(status='maintenance').count()
    low_stock_parts_count = PartInventory.objects.filter(current_stock__lte=F('minimum_stock_level')).count()
    mtd_parts_spend = SparePartUsageLog.objects.filter(created_at__gte=month_start).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    parts_catalog = PartInventory.objects.all().order_by('part_name')[:100]
    vehicles_list = Vehicle.objects.filter(status__in=['available', 'maintenance']).order_by('registration_number')
    recent_usage_logs = SparePartUsageLog.objects.select_related('inventory_item', 'service_record', 'vehicle').order_by('-created_at')[:8]
    open_requisitions = PartPurchaseRequisition.objects.select_related('inventory_item').filter(status__in=['draft', 'auto_triggered', 'approved'])[:5]

    context = {
        'title': 'Workshop Mechanic Studio & QR Barcode Checkout',
        'job_cards': job_cards,
        'active_job_card': active_job_card,
        'status_filter': status_filter,
        'depot_filter': depot_filter,
        'priority_filter': priority_filter,
        'search_q': search_q,
        'depot_choices': DEPOT_CHOICES,
        'kpi': {
            'active_job_cards': active_job_cards_count,
            'grounded_vehicles': grounded_vehicles_count,
            'low_stock_parts': low_stock_parts_count,
            'mtd_parts_spend': mtd_parts_spend,
        },
        'parts_catalog': parts_catalog,
        'vehicles_list': vehicles_list,
        'recent_usage_logs': recent_usage_logs,
        'open_requisitions': open_requisitions,
    }
    return render(request, 'maintenance/workshop_mechanic_studio.html', context)


@login_required
@require_staff_capability('maintenance_work_orders')
def api_scan_spare_part(request):
    """
    Scans or searches spare parts inventory by QR barcode, SKU, or name.
    Returns live inventory levels, bin location, unit price, and safety stock status.
    """
    from .models import PartInventory
    from django.db.models import Q

    query = (request.GET.get('q') or request.GET.get('barcode') or request.GET.get('sku') or '').strip()
    if not query:
        return JsonResponse({'success': False, 'message': 'Barcode or SKU query required.'}, status=400)

    part = PartInventory.objects.filter(Q(barcode__iexact=query) | Q(sku__iexact=query)).first()
    if not part:
        part = PartInventory.objects.filter(part_name__icontains=query).first()

    if not part:
        return JsonResponse({'success': False, 'found': False, 'message': f"No spare part found matching '{query}'."})

    return JsonResponse({
        'success': True,
        'found': True,
        'part': {
            'id': part.id,
            'part_name': part.part_name,
            'sku': part.sku,
            'barcode': part.barcode,
            'category': part.category,
            'category_display': part.get_category_display(),
            'bin_location': part.bin_location or 'Unassigned',
            'current_stock': part.current_stock,
            'minimum_stock_level': part.minimum_stock_level,
            'unit_of_measure': part.unit_of_measure,
            'unit_of_measure_display': part.get_unit_of_measure_display(),
            'default_unit_price': float(part.default_unit_price),
            'base_depot': part.base_depot,
            'is_critical_part': part.is_critical_part,
            'stock_status': part.stock_status,
            'is_low_stock': part.is_low_stock,
            'is_out_of_stock': part.is_out_of_stock,
        }
    })


@login_required
@require_staff_capability('maintenance_work_orders')
def api_checkout_spare_part(request):
    """
    Atomic 1-tap spare part checkout to active job card.
    Prevents stock leakage, creates immutable audit log, and deducts PartInventory immediately.
    """
    import json
    from decimal import Decimal
    from django.db import transaction
    from .models import ServiceRecord, PartInventory, SparePart, SparePartUsageLog, PartPurchaseRequisition

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        job_card_id = int(data.get('job_card_id'))
        part_id = int(data.get('part_id'))
        quantity = int(data.get('quantity', 1))
        checkout_mode = data.get('checkout_mode', 'camera_qr')
        barcode_scanned = data.get('barcode_scanned', '')
        notes = data.get('notes', '')

        if quantity <= 0:
            return JsonResponse({'success': False, 'message': 'Quantity must be at least 1.'}, status=400)

        with transaction.atomic():
            job_card = get_object_or_404(ServiceRecord.objects.select_for_update(), pk=job_card_id)
            part = get_object_or_404(PartInventory.objects.select_for_update(), pk=part_id)

            if part.current_stock < quantity:
                return JsonResponse({
                    'success': False,
                    'message': f"Insufficient stock for {part.part_name}. Requested: {quantity}, Available: {part.current_stock} {part.get_unit_of_measure_display()}."
                }, status=400)

            part.current_stock -= quantity
            part.save(update_fields=['current_stock'])

            unit_price = part.default_unit_price or Decimal('0.00')
            total_price = unit_price * Decimal(str(quantity))

            spare_part = SparePart.objects.create(
                service_record=job_card,
                inventory_item=part,
                part_name=part.part_name,
                quantity=quantity,
                unit_price=unit_price,
                is_inventory_deducted=True
            )

            usage_log = SparePartUsageLog.objects.create(
                service_record=job_card,
                inventory_item=part,
                vehicle=job_card.vehicle,
                quantity=quantity,
                unit_price=unit_price,
                total_cost=total_price,
                checkout_mode=checkout_mode,
                checked_out_by=request.user,
                mechanic_name=job_card.mechanic_name or request.user.get_full_name() or request.user.username,
                barcode_scanned=barcode_scanned or part.barcode or '',
                notes=notes
            )

            job_card.recalculate_totals()

            auto_requisition_triggered = False
            req_info = None
            if part.current_stock <= part.minimum_stock_level:
                req = PartPurchaseRequisition.trigger_auto_requisition(part)
                auto_requisition_triggered = True
                req_info = {
                    'requisition_number': req.requisition_number,
                    'suggested_quantity': req.suggested_quantity,
                    'urgency': req.urgency,
                }

        return JsonResponse({
            'success': True,
            'message': f"Successfully checked out {quantity}x {part.part_name} to Job Card {job_card.job_card_number}.",
            'checkout': {
                'part_id': part.id,
                'part_name': part.part_name,
                'quantity': quantity,
                'unit_price': float(unit_price),
                'total_cost': float(total_price),
                'remaining_stock': part.current_stock,
                'stock_status': part.stock_status,
                'job_card_parts_cost': float(job_card.parts_total_cost),
                'job_card_grand_total': float(job_card.total_cost),
            },
            'auto_requisition_triggered': auto_requisition_triggered,
            'requisition': req_info,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_staff_capability('maintenance_work_orders')
def api_create_workshop_job_card(request):
    """Creates a new workshop job card and grounds the vehicle in bay."""
    import json
    from decimal import Decimal
    from .models import ServiceRecord, DefectTicket, PreTripInspectionChecklist
    from core.models import Vehicle

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        vehicle_id = int(data.get('vehicle_id'))
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

        service_type = data.get('service_type', 'routine')
        priority = data.get('priority', 'normal')
        mechanic_name = data.get('mechanic_name', '').strip()
        bay_number = data.get('bay_number', 'Bay 1').strip()
        garage_name = data.get('garage_name', 'In-House Workshop Hub').strip()
        odometer_reading = int(data.get('odometer_reading') or (vehicle.current_km or 0))
        description = data.get('description', '').strip()
        labor_charges = Decimal(str(data.get('labor_charges', '0.00')))
        base_depot = data.get('base_depot', vehicle.base_depot)

        defect_ticket_id = data.get('defect_ticket_id')
        defect_ticket = DefectTicket.objects.filter(pk=defect_ticket_id).first() if defect_ticket_id else None

        inspection_checklist_id = data.get('inspection_checklist_id')
        inspection_checklist = PreTripInspectionChecklist.objects.filter(pk=inspection_checklist_id).first() if inspection_checklist_id else None

        job_card = ServiceRecord.objects.create(
            vehicle=vehicle,
            service_type=service_type,
            priority=priority,
            status='in_progress',
            assigned_mechanic=request.user,
            mechanic_name=mechanic_name or request.user.get_full_name() or request.user.username,
            bay_number=bay_number,
            base_depot=base_depot,
            date=timezone.now().date(),
            odometer_reading=odometer_reading,
            garage_name=garage_name,
            description=description,
            labor_charges=labor_charges,
            total_cost=labor_charges,
            defect_ticket=defect_ticket,
            inspection_checklist=inspection_checklist
        )

        vehicle.status = 'maintenance'
        vehicle.save(update_fields=['status'])

        if defect_ticket:
            defect_ticket.status = 'in_progress'
            defect_ticket.notes = f"Linked to Job Card {job_card.job_card_number}"
            defect_ticket.save(update_fields=['status', 'notes'])

        return JsonResponse({
            'success': True,
            'message': f"Job Card {job_card.job_card_number} created for {vehicle.registration_number}.",
            'job_card_id': job_card.id,
            'job_card_number': job_card.job_card_number,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_staff_capability('maintenance_work_orders')
def api_update_job_card_status(request, pk):
    """Updates job card status stepper and releases vehicle if completed."""
    import json
    from decimal import Decimal
    from .models import ServiceRecord

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        job_card = get_object_or_404(ServiceRecord, pk=pk)
        new_status = data.get('status')
        if new_status:
            job_card.status = new_status

        if 'labor_charges' in data:
            job_card.labor_charges = Decimal(str(data['labor_charges']))

        if 'mechanic_name' in data:
            job_card.mechanic_name = data['mechanic_name'].strip()

        if 'bay_number' in data:
            job_card.bay_number = data['bay_number'].strip()

        if 'description' in data and data['description']:
            job_card.description = data['description'].strip()

        job_card.save()
        job_card.recalculate_totals()

        if job_card.status == 'completed' and job_card.defect_ticket:
            job_card.defect_ticket.status = 'resolved'
            job_card.defect_ticket.resolved_date = timezone.now().date()
            job_card.defect_ticket.save(update_fields=['status', 'resolved_date'])

        return JsonResponse({
            'success': True,
            'message': f"Job Card {job_card.job_card_number} updated to {job_card.get_status_display()}.",
            'status': job_card.status,
            'status_display': job_card.get_status_display(),
            'vehicle_status': job_card.vehicle.status,
            'grand_total': float(job_card.total_cost),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_staff_capability('maintenance_work_orders')
def api_part_quick_restock(request):
    """1-Click stock receiving and restocking."""
    import json
    from .models import PartInventory, PartPurchaseRequisition

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        part_id = int(data.get('part_id'))
        quantity = int(data.get('quantity', 0))

        if quantity <= 0:
            return JsonResponse({'success': False, 'message': 'Restock quantity must be positive.'}, status=400)

        part = get_object_or_404(PartInventory, pk=part_id)
        part.current_stock += quantity
        part.last_restocked_at = timezone.now()
        part.save(update_fields=['current_stock', 'last_restocked_at'])

        PartPurchaseRequisition.objects.filter(
            inventory_item=part,
            status__in=['draft', 'auto_triggered', 'approved', 'po_placed']
        ).update(status='received', restocked_at=timezone.now())

        return JsonResponse({
            'success': True,
            'message': f"Restocked {quantity} {part.get_unit_of_measure_display()} for {part.part_name}. Current stock: {part.current_stock}.",
            'current_stock': part.current_stock,
            'stock_status': part.stock_status,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_staff_capability('maintenance_work_orders')
def job_card_work_order_print_view(request, pk):
    """Renders printable A4 garage work order sheet and parts consumption voucher."""
    from .models import ServiceRecord
    from django.http import Http404
    job_card = (
        ServiceRecord.objects.select_related('vehicle', 'assigned_mechanic', 'defect_ticket', 'inspection_checklist')
        .prefetch_related('spare_parts__inventory_item', 'part_usage_logs')
        .filter(pk=pk)
        .first()
    )
    if not job_card:
        job_card = (
            ServiceRecord.objects.select_related('vehicle', 'assigned_mechanic', 'defect_ticket', 'inspection_checklist')
            .prefetch_related('spare_parts__inventory_item', 'part_usage_logs')
            .first()
        )
    if not job_card:
        raise Http404("No Job Cards found in workshop.")
    
    if not job_card.job_card_number:
        job_card.job_card_number = f"JC-DEMO-{job_card.id:04d}"
    context = {
        'title': f"Work Order - {job_card.job_card_number}",
        'job_card': job_card,
        'printed_at': timezone.now(),
        'printed_by': request.user,
    }
    return render(request, 'maintenance/job_card_work_order_print.html', context)



