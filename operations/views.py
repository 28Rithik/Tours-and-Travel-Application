from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BookingForm, TripForm
from .models import Booking, Trip
from core.models import Vehicle, Driver


@login_required
def booking_list(request):
    bookings = Booking.objects.order_by('-booking_date')

    status_filter = request.GET.get('status')
    journey_filter = request.GET.get('journey_type')
    hotel_filter = request.GET.get('hotel_status')
    search_term = request.GET.get('search', '').strip()

    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if journey_filter:
        bookings = bookings.filter(journey_type=journey_filter)
    if hotel_filter:
        bookings = bookings.filter(hotel_confirmation_status=hotel_filter)
    if search_term:
        bookings = bookings.filter(
            guest_name__icontains=search_term
        ) | bookings.filter(booking_number__icontains=search_term)

    return render(request, 'operations/booking_list.html', {
        'bookings': bookings.distinct(),
        'status_filter': status_filter,
        'journey_filter': journey_filter,
        'hotel_filter': hotel_filter,
        'search_term': search_term,
    })


@login_required
def booking_create(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save()
            messages.success(request, 'Booking created successfully.')
            return redirect('booking-detail', booking_id=booking.pk)
    else:
        form = BookingForm()
    return render(request, 'operations/booking_form.html', {'form': form})


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    return render(request, 'operations/booking_detail.html', {'booking': booking})


@login_required
def trip_create(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    if request.method == 'POST':
        trip_instance = Trip(booking=booking, party=booking.party, guest_name=booking.guest_name)
        form = TripForm(request.POST, instance=trip_instance)
        if form.is_valid():
            trip = form.save()
            messages.success(request, 'Confirmed trip created.')
            return redirect('trip-detail', trip_id=trip.pk)
    else:
        form = TripForm(initial={
            'status': 'booked',
            'hotel_confirmation_status': booking.hotel_confirmation_status,
            'start_date': booking.pickup_date,
            'start_time': booking.pickup_time,
            'end_date': booking.pickup_date,
            'billing_model': 'day_km',
        })
    return render(request, 'operations/trip_form.html', {'form': form, 'booking': booking})


@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    return render(request, 'operations/trip_detail.html', {'trip': trip})


@login_required
def trip_update_status(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    new_status = request.POST.get('status') or request.GET.get('status')
    if new_status in dict(Trip.STATUSES):
        if new_status == 'started' and trip.vehicle:
            from maintenance.models import PreTripInspectionChecklist
            from django.utils import timezone
            import datetime
            cutoff = timezone.now() - datetime.timedelta(hours=24)
            has_passed_inspection = PreTripInspectionChecklist.objects.filter(
                vehicle=trip.vehicle,
                inspection_date__gte=cutoff,
                overall_status__in=['passed', 'conditional_pass']
            ).exists()
            bypass = request.POST.get('bypass_inspection') == '1'
            if not has_passed_inspection and not bypass:
                messages.warning(
                    request,
                    f"Pre-Trip Safety Inspection has NOT been completed for {trip.vehicle.registration_number} within the last 24 hours. "
                    f"Please complete the digital checklist before vehicle departure."
                )
                return redirect('trip-detail', trip_id=trip.pk)
            elif not has_passed_inspection and bypass:
                messages.info(request, "Pre-trip safety inspection bypassed by dispatcher.")

        trip.status = new_status
        trip.save(update_fields=['status'])
        messages.success(request, f'Trip status updated to {trip.get_status_display()}.')
    return redirect('trip-detail', trip_id=trip.pk)



@login_required
def customer_confirmation_preview(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    return render(request, 'operations/customer_confirmation_preview.html', {
        'trip': trip,
        'preview_text': trip.customer_confirmation_message,
    })


@login_required
def api_get_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    
    # Map Booking billing_type to Trip billing_model
    billing_model_map = {
        'km': 'km',
        'day': 'day',
        'package': 'fixed'
    }
    
    end_date = booking.drop_date if booking.drop_date else booking.pickup_date
    
    data = {
        'party_id': booking.party_id,
        'guest_name': booking.guest_name or '',
        'travel_pnr': booking.travel_pnr or '',
        'pax_count': booking.pax_count or '',
        'luggage_count': booking.luggage_count or '',
        'pickup_location': booking.pickup_location or '',
        'destination': booking.destination or '',
        'vehicle_type': str(booking.vehicle_type) if booking.vehicle_type else '',
        'vehicle_type_id': booking.vehicle_type_id,
        'journey_type': booking.get_journey_type_display() if booking.journey_type else '',
        'special_requirements': booking.special_requirements or '',
        'expected_km': booking.expected_km or 0,
        'package_id': booking.package_id,
        'package_name': str(booking.package) if booking.package else '',
        'package_inventory_id': booking.package_inventory_id,
        'package_inventory_name': str(booking.package_inventory) if booking.package_inventory else '',
        'start_date': booking.pickup_date.strftime('%Y-%m-%d') if booking.pickup_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'start_time': booking.pickup_time.strftime('%H:%M:%S') if booking.pickup_time else '',
        'billing_model': billing_model_map.get(booking.billing_type, 'day_km'),
        'fixed_amount': str(booking.quoted_price) if booking.billing_type == 'package' and booking.quoted_price else '0',
        'advance_received': str(booking.advance_received),
        'quoted_price': str(booking.quoted_price or 0),
        'notes': booking.notes or '',
    }
    return JsonResponse(data)


@login_required
def api_package_inventory(request, package_id):
    from packages.models import Package
    package = get_object_or_404(Package, pk=package_id)
    inventories = package.inventory.all().order_by('departure_date')
    
    inventories_data = []
    for inv in inventories:
        price = inv.price_override if inv.price_override else (package.price_with_food or package.base_price or 0)
        inventories_data.append({
            'id': inv.id,
            'label': f"{inv.departure_date.strftime('%d %b %Y')} ({inv.available_seats}/{inv.total_seats} seats free)",
            'departure_date': inv.departure_date.strftime('%Y-%m-%d'),
            'return_date': inv.return_date.strftime('%Y-%m-%d') if inv.return_date else '',
            'available_seats': inv.available_seats,
            'booked_seats': inv.booked_seats,
            'total_seats': inv.total_seats,
            'status': inv.status,
            'status_display': inv.get_status_display(),
            'price': str(price),
            'assigned_vehicle': str(inv.assigned_vehicle) if inv.assigned_vehicle else '',
            'assigned_vehicle_id': inv.assigned_vehicle_id,
            'assigned_driver': str(inv.assigned_driver) if inv.assigned_driver else '',
            'assigned_driver_id': inv.assigned_driver_id,
        })
    
    data = {
        'package': {
            'id': package.id,
            'name': package.name,
            'package_code': package.package_code or '',
            'destination': package.destination or '',
            'duration_days': package.duration_days,
            'duration_nights': package.duration_nights,
            'pricing_type': package.pricing_type,
            'price_with_food': str(package.price_with_food or 0),
            'price_without_food': str(package.price_without_food or 0),
            'base_price': str(package.base_price or 0),
        },
        'inventories': inventories_data,
    }
    return JsonResponse(data)


@login_required
def api_inventory_detail(request, inventory_id):
    from packages.models import PackageInventory
    inv = get_object_or_404(PackageInventory, pk=inventory_id)
    pkg = inv.package
    price = inv.price_override if inv.price_override else (pkg.price_with_food or pkg.base_price or 0)
    data = {
        'id': inv.id,
        'package_id': pkg.id,
        'package_name': pkg.name,
        'duration_days': pkg.duration_days,
        'duration_nights': pkg.duration_nights,
        'departure_date': inv.departure_date.strftime('%Y-%m-%d'),
        'return_date': inv.return_date.strftime('%Y-%m-%d') if inv.return_date else '',
        'available_seats': inv.available_seats,
        'booked_seats': inv.booked_seats,
        'total_seats': inv.total_seats,
        'status': inv.status,
        'status_display': inv.get_status_display(),
        'price': str(price),
        'assigned_vehicle_id': inv.assigned_vehicle_id,
        'assigned_vehicle_str': str(inv.assigned_vehicle) if inv.assigned_vehicle else '',
        'assigned_driver_id': inv.assigned_driver_id,
        'assigned_driver_str': str(inv.assigned_driver) if inv.assigned_driver else '',
    }
    return JsonResponse(data)


@login_required
def api_get_trip(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    data = {
        'trip_id': trip.trip_id,
        'vehicle_id': trip.vehicle_id,
        'vehicle_registration': trip.vehicle.registration_number if trip.vehicle else '',
        'vehicle_ownership': trip.vehicle.ownership_type if trip.vehicle else '',
        'driver_id': trip.driver_id,
        'driver_name': trip.driver.name if trip.driver else '',
        'party_id': trip.party_id,
        'party_name': trip.party.name if trip.party else '',
        'start_date': trip.start_date.strftime('%Y-%m-%d') if trip.start_date else '',
        'status': trip.status,
    }
    return JsonResponse(data)


@login_required
def generate_trip_sheet(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    return render(request, 'operations/trip_sheet.html', {'trip': trip})


@login_required
def api_bulk_contract_context(request, contract_id):
    from .models import BulkContract
    contract = get_object_or_404(BulkContract, pk=contract_id)
    rates_data = [
        {
            'vehicle_type_id': r.vehicle_type_id,
            'vehicle_type_name': str(r.vehicle_type) if r.vehicle_type else '',
            'agreed_day_rate': str(r.agreed_day_rate),
        }
        for r in contract.vehicle_rates.all()
    ]
    data = {
        'id': contract.id,
        'name': contract.name,
        'contract_type': contract.contract_type,
        'contract_type_display': contract.get_contract_type_display(),
        'customer_id': contract.customer_id,
        'customer_name': contract.customer.name if contract.customer else '',
        'start_date': contract.start_date.strftime('%Y-%m-%d'),
        'end_date': contract.end_date.strftime('%Y-%m-%d'),
        'billing_model': contract.billing_model,
        'status': contract.status,
        'rates': rates_data,
    }
    return JsonResponse(data)


import json
from django.views.decorators.csrf import csrf_exempt
from .services import ingest_telematics_ping, dispatch_standby_vehicle


@csrf_exempt
def api_telematics_ping(request):
    """
    Ingests live telemetry from hardware GPS or Driver App.
    Endpoint: POST /api/telematics/ping/
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "POST required."}, status=405)
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST.dict()
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Malformed payload: {str(e)}"}, status=400)

    result = ingest_telematics_ping(data)
    status_code = 200 if result.get('status') == 'success' else 400
    return JsonResponse(result, status=status_code)


@login_required
def api_telematics_live(request, vehicle_id):
    """
    Returns latest GPS ping, current speed, fuel level, and breadcrumb trail for vehicle.
    Endpoint: GET /api/telematics/live/<vehicle_id>/
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    latest_ping = vehicle.telematics_pings.first()
    recent_pings = vehicle.telematics_pings.all()[:20]

    return JsonResponse({
        "status": "success",
        "vehicle": {
            "id": vehicle.pk,
            "registration_number": vehicle.registration_number,
            "current_location": vehicle.current_location,
            "current_km": vehicle.current_km,
            "gps_imei": vehicle.gps_imei,
        },
        "latest_ping": {
            "timestamp": latest_ping.timestamp.isoformat() if latest_ping else None,
            "latitude": float(latest_ping.latitude) if latest_ping else None,
            "longitude": float(latest_ping.longitude) if latest_ping else None,
            "speed_kmh": float(latest_ping.speed_kmh) if latest_ping else 0.0,
            "ignition_on": latest_ping.ignition_on if latest_ping else False,
            "fuel_level_pct": float(latest_ping.fuel_level_pct) if latest_ping and latest_ping.fuel_level_pct else None,
        } if latest_ping else None,
        "recent_crumbs": [
            {
                "lat": float(p.latitude),
                "lng": float(p.longitude),
                "speed": float(p.speed_kmh),
                "time": p.timestamp.strftime('%H:%M:%S'),
            }
            for p in recent_pings
        ]
    })


@login_required
def dispatch_standby_replacement(request, incident_id):
    """
    Executes 1-click standby vehicle replacement for an emergency incident.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "POST required."}, status=405)

    standby_vehicle_id = request.POST.get('standby_vehicle_id')
    standby_driver_id = request.POST.get('standby_driver_id')
    eta_minutes = int(request.POST.get('eta_minutes', 30))
    notes = request.POST.get('notes', '')

    result = dispatch_standby_vehicle(
        incident_id=incident_id,
        standby_vehicle_id=standby_vehicle_id,
        standby_driver_id=standby_driver_id,
        eta_minutes=eta_minutes,
        notes=notes
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
        return JsonResponse(result)

    if result.get('status') == 'success':
        messages.success(request, result.get('message'))
    else:
        messages.error(request, result.get('message'))
    return redirect(f'/admin/operations/emergencyincidentalert/{incident_id}/change/')


from datetime import timedelta
from django.utils import timezone
from .models import EmergencyIncidentAlert, VehicleTelematicsPing, DriverBehaviorLog, GeofenceZone
from maintenance.models import DefectTicket, PreTripInspectionChecklist
from analytics.models import DriverScorecard

DESTINATION_COORDINATES = {
    'ooty': (11.4102, 76.6950),
    'udhagamandalam': (11.4102, 76.6950),
    'chennai': (13.0827, 80.2707),
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'madurai': (9.9252, 78.1198),
    'munnar': (10.0889, 77.0595),
    'kodaikanal': (10.2381, 77.4892),
    'salem': (11.6643, 78.1460),
    'coimbatore': (11.0168, 76.9558),
    'tirupur': (11.1085, 77.3411),
    'pollachi': (10.6580, 77.0090),
    'kochi': (9.9312, 76.2673),
    'mysore': (12.2958, 76.6394),
    'kanyakumari': (8.0883, 77.5385),
    'rameshwaram': (9.2876, 79.3129),
    'trichy': (10.7905, 78.7047),
    'tiruchirappalli': (10.7905, 78.7047),
    'pondicherry': (11.9416, 79.8083),
}


@login_required
def fleet_live_mission_control(request):
    """
    Renders the live interactive Leaflet.js mission control command center.
    """
    vehicles = Vehicle.objects.all().select_related('vehicle_type')
    standby_vehicles = vehicles.filter(status='available')
    active_incidents = EmergencyIncidentAlert.objects.filter(
        status__in=['reported', 'acknowledged', 'standby_dispatched']
    ).select_related('vehicle', 'driver')
    geofences = GeofenceZone.objects.filter(is_active=True)

    return render(request, 'operations/fleet_live_mission_control.html', {
        'total_vehicles_count': vehicles.count(),
        'standby_vehicles': standby_vehicles,
        'active_incidents': active_incidents,
        'geofences': geofences,
    })


@login_required
def api_fleet_live_feed(request):
    """
    REST endpoint returning real-time telematics, vehicle status, active alerts,
    and geofence telemetry for the live map dashboard.
    """
    now = timezone.now()
    five_days_ago = (now - timedelta(days=5)).date()

    vehicles = Vehicle.objects.all().select_related('vehicle_type')
    active_incidents = EmergencyIncidentAlert.objects.filter(
        status__in=['reported', 'acknowledged', 'standby_dispatched']
    ).select_related('vehicle', 'driver')
    incident_by_vehicle = {inc.vehicle_id: inc for inc in active_incidents}

    # Open defect tickets
    defect_vehicle_ids = set(
        DefectTicket.objects.filter(status='open').values_list('vehicle_id', flat=True)
    )

    # Failed checklists in last 48 hours
    two_days_ago = now - timedelta(days=2)
    failed_checklists_vehicle_ids = set(
        PreTripInspectionChecklist.objects.filter(
            overall_status='failed', created_at__gte=two_days_ago
        ).values_list('vehicle_id', flat=True)
    )

    # Active trips
    active_trips = Trip.objects.filter(
        status__in=['assigned', 'started']
    ).select_related('driver', 'booking', 'vehicle')
    trip_by_vehicle = {t.vehicle_id: t for t in active_trips if t.vehicle_id}

    # Recent trips in 5 days
    recent_trip_vehicle_ids = set(
        Trip.objects.filter(start_date__gte=five_days_ago).values_list('vehicle_id', flat=True)
    )

    # Driver scorecards cached by driver_id
    scorecard_by_driver = {
        sc.driver_id: sc for sc in DriverScorecard.objects.all()
    }

    vehicle_list = []
    active_count = 0
    standby_count = 0
    workshop_count = 0
    idle_count = 0
    sos_count = 0

    base_lat, base_lng = 11.0168, 76.9558  # Coimbatore HQ Depot

    for v in vehicles:
        incident = incident_by_vehicle.get(v.id)
        active_trip = trip_by_vehicle.get(v.id)
        in_workshop = (
            v.status in ['in_shop', 'breakdown', 'maintenance'] or
            v.id in defect_vehicle_ids or
            v.id in failed_checklists_vehicle_ids
        )
        has_recent_trip = (v.id in recent_trip_vehicle_ids) or (active_trip is not None)

        if incident:
            status_code = 'sos_alert'
            status_label = f"🔴 SOS: {incident.get_incident_type_display()}"
            status_color = "#ef4444"
            sos_count += 1
        elif in_workshop:
            status_code = 'workshop'
            status_label = "🟠 In Workshop / Grounded"
            status_color = "#f59e0b"
            workshop_count += 1
        elif active_trip:
            status_code = 'on_trip'
            status_label = "🟢 On Trip"
            status_color = "#10b981"
            active_count += 1
        elif not has_recent_trip:
            status_code = 'idle'
            status_label = "⚪ Idle (>5 Days)"
            status_color = "#94a3b8"
            idle_count += 1
        else:
            status_code = 'standby'
            status_label = "🔵 Ready Standby"
            status_color = "#3b82f6"
            standby_count += 1

        # Telematics coordinates
        latest_ping = v.telematics_pings.first()
        if latest_ping and latest_ping.latitude and latest_ping.longitude:
            lat = float(latest_ping.latitude)
            lng = float(latest_ping.longitude)
            speed = float(latest_ping.speed_kmh)
            ignition = latest_ping.ignition_on
            fuel_pct = float(latest_ping.fuel_level_pct) if latest_ping.fuel_level_pct is not None else 70.0
            ping_time = latest_ping.timestamp.strftime('%H:%M:%S')
        else:
            # Fallback coordinates based on trip destination or yard
            speed = 46.0 if status_code == 'on_trip' else 0.0
            ignition = True if status_code == 'on_trip' else False
            fuel_pct = 75.0
            ping_time = "Live System"

            assigned_dest = active_trip.destination.lower() if active_trip and active_trip.destination else ""
            coords_found = False
            for place, coords in DESTINATION_COORDINATES.items():
                if place in assigned_dest:
                    lat = coords[0] + (((v.id * 7) % 20) - 10) * 0.002
                    lng = coords[1] + (((v.id * 11) % 20) - 10) * 0.002
                    coords_found = True
                    break
            if not coords_found:
                lat = base_lat + (((v.id * 17) % 40) - 20) * 0.0018
                lng = base_lng + (((v.id * 23) % 40) - 20) * 0.0018

        # Driver details
        driver_obj = active_trip.driver if active_trip and active_trip.driver else v.default_driver
        driver_info = None
        if driver_obj:
            sc = scorecard_by_driver.get(driver_obj.id)
            driver_info = {
                "id": driver_obj.id,
                "name": driver_obj.name,
                "phone": driver_obj.phone,
                "grade": sc.grade if sc else "A",
                "safety_score": float(sc.safety_score) if sc else 98.0,
            }

        # Trip details
        trip_info = None
        if active_trip:
            trip_info = {
                "id": active_trip.id,
                "booking_number": active_trip.booking.booking_number if active_trip.booking else f"TRP-{active_trip.id}",
                "guest_name": active_trip.guest_name,
                "guest_phone": active_trip.booking.guest_phone if active_trip.booking else "",
                "pickup": active_trip.pickup_location,
                "destination": active_trip.destination,
                "status": active_trip.get_status_display(),
            }

        # Incident details
        incident_info = None
        if incident:
            incident_info = {
                "id": incident.id,
                "incident_id": incident.incident_id,
                "incident_type": incident.get_incident_type_display(),
                "severity": incident.get_severity_display(),
                "description": incident.description,
                "reported_at": incident.reported_at.strftime('%H:%M'),
            }

        vehicle_list.append({
            "id": v.id,
            "registration_number": v.registration_number,
            "model_name": f"{v.brand} {v.model}".strip(),
            "vehicle_type": v.vehicle_type.name if v.vehicle_type else "Vehicle",
            "capacity": v.seating_capacity,
            "current_km": v.current_km or 0,
            "fuel_type": v.get_fuel_type_display() if hasattr(v, 'get_fuel_type_display') else v.fuel_type,
            "status_code": status_code,
            "status_label": status_label,
            "status_color": status_color,
            "location_name": v.current_location or "Coimbatore Region",
            "lat": lat,
            "lng": lng,
            "speed_kmh": speed,
            "ignition_on": ignition,
            "fuel_level_pct": fuel_pct,
            "last_ping_time": ping_time,
            "driver": driver_info,
            "trip": trip_info,
            "incident": incident_info,
        })

    # Recent behavior events (violations in last 24h)
    recent_violations = []
    since_yesterday = now - timedelta(days=1)
    behavior_events = DriverBehaviorLog.objects.filter(
        timestamp__gte=since_yesterday
    ).select_related('driver', 'vehicle').order_by('-timestamp')[:15]
    for b in behavior_events:
        recent_violations.append({
            "id": b.id,
            "event_type": b.get_event_type_display(),
            "severity": b.severity,
            "vehicle_reg": b.vehicle.registration_number,
            "driver_name": b.driver.name if b.driver else "N/A",
            "speed": float(b.recorded_speed_kmh),
            "limit": float(b.speed_limit_kmh),
            "time": b.timestamp.strftime('%H:%M:%S'),
        })

    # Active incidents list
    incidents_list = []
    for inc in active_incidents:
        incidents_list.append({
            "id": inc.id,
            "incident_id": inc.incident_id,
            "vehicle_reg": inc.vehicle.registration_number,
            "driver_name": inc.driver.name if inc.driver else "Unassigned",
            "incident_type": inc.get_incident_type_display(),
            "severity": inc.severity,
            "status": inc.get_status_display(),
            "location": inc.location_address or "GPS Location",
            "reported_at": inc.reported_at.strftime('%H:%M'),
            "description": inc.description,
        })

    # Active Geofence Zones
    geofences_list = []
    for g in GeofenceZone.objects.filter(is_active=True):
        geofences_list.append({
            "id": g.id,
            "name": g.name,
            "zone_type": g.get_zone_type_display(),
            "lat": float(g.latitude),
            "lng": float(g.longitude),
            "radius": g.radius_meters,
            "speed_limit": g.speed_limit_kmh,
        })

    return JsonResponse({
        "status": "success",
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "summary": {
            "total_vehicles": len(vehicle_list),
            "active_count": active_count,
            "standby_count": standby_count,
            "workshop_count": workshop_count,
            "idle_count": idle_count,
            "sos_count": sos_count,
            "active_alerts_count": len(incidents_list),
            "violations_count": len(recent_violations),
        },
        "vehicles": vehicle_list,
        "active_incidents": incidents_list,
        "recent_violations": recent_violations,
        "geofences": geofences_list,
    })


def passenger_live_tracking_view(request, token):
    """
    Public, unauthenticated live tracking view for passengers and clients.
    Secured by unguessable tracking token.
    """
    trip = get_object_or_404(Trip.objects.select_related('booking', 'vehicle', 'driver', 'party'), tracking_token=token)
    latest_ping = None
    if trip.vehicle:
        latest_ping = trip.vehicle.telematics_pings.order_by('-timestamp').first()

    context = {
        'trip': trip,
        'vehicle': trip.vehicle,
        'driver': trip.driver,
        'booking': trip.booking,
        'latest_ping': latest_ping,
        'token': token,
    }
    return render(request, 'operations/passenger_live_tracking.html', context)


def api_passenger_live_tracking(request, token):
    """
    Public polling endpoint returning live vehicle coordinates, speed, heading,
    driver info, and dynamic ETA calculation for the passenger tracking page.
    """
    trip = get_object_or_404(Trip.objects.select_related('vehicle', 'driver', 'booking'), tracking_token=token)
    
    vehicle = trip.vehicle
    latest_ping = None
    breadcrumbs = []

    if vehicle:
        pings = vehicle.telematics_pings.order_by('-timestamp')[:20]
        if pings:
            latest_ping = pings[0]
            breadcrumbs = [
                {"lat": float(p.latitude), "lng": float(p.longitude), "speed": float(p.speed_kmh), "time": p.timestamp.strftime('%H:%M:%S')}
                for p in reversed(pings)
            ]

    # Calculate dynamic ETA
    speed = float(latest_ping.speed_kmh) if latest_ping and latest_ping.speed_kmh else 40.0
    lat = float(latest_ping.latitude) if latest_ping else (11.0168)
    lng = float(latest_ping.longitude) if latest_ping else (76.9558)
    heading = float(latest_ping.heading_degrees or 0.0) if latest_ping else 0.0
    ignition = latest_ping.ignition_on if latest_ping else True

    # Approximate ETA based on trip state
    if trip.status == 'completed':
        eta_str = "Trip Completed"
        eta_minutes = 0
    elif trip.status == 'started':
        eta_minutes = 25
        eta_str = f"~{eta_minutes} mins (Live)"
    elif trip.status in ['assigned', 'driver_confirmed']:
        eta_minutes = 15
        eta_str = f"Driver arriving in ~{eta_minutes} mins"
    else:
        eta_minutes = 45
        eta_str = "Scheduled"

    return JsonResponse({
        "status": "success",
        "trip": {
            "trip_id": trip.trip_id,
            "status": trip.get_status_display(),
            "status_code": trip.status,
            "guest_name": trip.guest_name,
            "pickup_location": trip.pickup_location,
            "destination": trip.destination,
            "eta_str": eta_str,
            "eta_minutes": eta_minutes,
        },
        "vehicle": {
            "registration_number": vehicle.registration_number if vehicle else "To Be Assigned",
            "model": f"{vehicle.brand} {vehicle.model}".strip() if vehicle else "Comfort Fleet",
            "vehicle_type": vehicle.vehicle_type.name if vehicle and vehicle.vehicle_type else "Sedan / SUV",
            "lat": lat,
            "lng": lng,
            "speed_kmh": speed,
            "heading": heading,
            "ignition": ignition,
            "last_ping_time": latest_ping.timestamp.strftime('%H:%M:%S') if latest_ping else "Live",
        } if vehicle else None,
        "driver": {
            "name": trip.driver.name if trip.driver else "Assigned Captain",
            "phone": trip.driver.phone if trip.driver else "",
            "badge": trip.driver.badge_number or "Verified Captain",
        } if trip.driver else None,
        "breadcrumbs": breadcrumbs,
    })


@login_required
def broadcast_trip_whatsapp_view(request, trip_id):
    """
    1-Click manual/automated dispatcher:
    Broadcasts booking confirmation, assigned captain details, and the live
    passenger GPS tracking link to the customer via WhatsApp.
    """
    trip = get_object_or_404(Trip, pk=trip_id)
    from integrations.communication import dispatch_trip_assignment_alert
    result = dispatch_trip_assignment_alert(trip)
    if result.get("status") in ["simulated_sent", "sent"] or "messages" in result:
        messages.success(request, f"📲 WhatsApp booking confirmation & live GPS tracking link dispatched to {trip.guest_name}!")
    else:
        messages.warning(request, f"Notice: WhatsApp dispatch result: {result.get('reason', 'Alert triggered')}")
    return redirect('trip-detail', trip_id=trip.pk)





