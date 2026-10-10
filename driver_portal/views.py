from decimal import Decimal
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import Driver, Vehicle
from operations.models import Trip, EmergencyIncidentAlert
from fleet_contracts.models import ContractTripLog
from maintenance.models import PreTripInspectionChecklist, DefectTicket
from finance_fleet.models import FuelRecord
from .models import DriverPortalAccount


def get_current_driver(request):
    # 1. Direct query param token for SMS/WhatsApp links or QR code scans
    token = request.GET.get('token')
    if token:
        trip = Trip.objects.filter(tracking_token=token).first()
        if trip and trip.driver:
            request.session['driver_id'] = trip.driver.pk
            return trip.driver
    # 2. Check session driver_id
    driver_id = request.session.get('driver_id')
    if driver_id:
        driver = Driver.objects.filter(pk=driver_id).first()
        if driver:
            return driver
    # 3. Check authenticated user
    if request.user.is_authenticated:
        if hasattr(request.user, 'driver_portal_account'):
            return request.user.driver_portal_account.driver
        # Check driver by user username or email
        driver = Driver.objects.filter(phone=request.user.username).first()
        if driver:
            return driver
        # Fallback if admin/staff is previewing driver portal
        if request.user.is_staff or request.user.is_superuser:
            first_driver = Driver.objects.filter(status='active').first() or Driver.objects.first()
            if first_driver:
                return first_driver
    return None


def driver_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        driver = get_current_driver(request)
        if not driver:
            messages.info(request, "Please log in to access the Driver Portal.")
            return redirect('driver_portal:login')
        request.driver = driver
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def driver_login(request):
    if request.user.is_authenticated and get_current_driver(request):
        return redirect('driver_portal:dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()

        if not phone:
            messages.error(request, "Please enter your registered phone number.")
            return render(request, 'driver_portal/login.html')

        # Find driver by phone (ignoring spaces or hyphens)
        clean_phone = phone.replace(' ', '').replace('-', '').replace('+91', '')
        driver = Driver.objects.filter(phone__icontains=clean_phone).first()

        if not driver:
            messages.error(request, f"No driver profile found matching phone {phone}. Please contact dispatch.")
            return render(request, 'driver_portal/login.html')

        # Get or create user
        portal_user = User.objects.filter(username=f"driver_{driver.pk}").first()
        if not portal_user:
            portal_user = User.objects.create_user(
                username=f"driver_{driver.pk}",
                password=f"pin_{pin or '1234'}"
            )

        # Get or create portal account
        portal_acc, created = DriverPortalAccount.objects.get_or_create(
            driver=driver,
            defaults={
                'quick_pin': pin if pin else '1234',
                'user': portal_user
            }
        )
        if not portal_acc.user:
            portal_acc.user = portal_user
            portal_acc.save(update_fields=['user'])

        # PIN Check
        if pin and portal_acc.quick_pin and portal_acc.quick_pin != pin:
            messages.error(request, "Incorrect PIN. Please re-enter your 4-digit driver PIN.")
            return render(request, 'driver_portal/login.html', {'entered_phone': phone})

        # Login user session
        auth_login(request, portal_acc.user)
        request.session['driver_id'] = driver.pk
        portal_acc.last_login_at = timezone.now()
        portal_acc.save(update_fields=['last_login_at'])

        messages.success(request, f"Welcome back, Captain {driver.name}!")
        return redirect('driver_portal:dashboard')

    return render(request, 'driver_portal/login.html')


def driver_logout(request):
    auth_logout(request)
    if 'driver_id' in request.session:
        del request.session['driver_id']
    messages.info(request, "You have been logged out safely.")
    return redirect('driver_portal:login')


@driver_login_required
def driver_dashboard(request):
    driver = request.driver
    today = timezone.now().date()

    # Active or assigned trips
    active_trips = Trip.objects.filter(
        driver=driver,
        status__in=['assigned', 'started']
    ).order_by('start_date')

    recent_trips = Trip.objects.filter(
        driver=driver
    ).order_by('-start_date')[:5]

    # Current vehicle
    current_trip = active_trips.first()
    current_vehicle = current_trip.vehicle if current_trip else (driver.default_vehicles.first() or Vehicle.objects.filter(default_driver=driver).first())

    # Today's inspection status for current vehicle
    inspection_today = None
    if current_vehicle:
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        inspection_today = PreTripInspectionChecklist.objects.filter(
            vehicle=current_vehicle,
            driver=driver,
            inspection_date__gte=cutoff
        ).first()

    return render(request, 'driver_portal/dashboard.html', {
        'driver': driver,
        'current_trip': current_trip,
        'active_trips': active_trips,
        'recent_trips': recent_trips,
        'current_vehicle': current_vehicle,
        'inspection_today': inspection_today,
    })


@driver_login_required
def driver_inspection(request):
    driver = request.driver
    vehicle_id = request.GET.get('vehicle_id') or request.POST.get('vehicle_id')
    trip_id = request.GET.get('trip_id') or request.POST.get('trip_id')

    trip = Trip.objects.filter(pk=trip_id).first() if trip_id else None
    vehicle = Vehicle.objects.filter(pk=vehicle_id).first() if vehicle_id else (trip.vehicle if trip else None)
    if not vehicle:
        vehicle = Vehicle.objects.filter(status='active').first()

    if request.method == 'POST':
        odometer_reading = int(request.POST.get('odometer_reading', vehicle.current_km if vehicle else 0))
        odometer_photo = request.FILES.get('odometer_photo')

        def is_checked(name):
            return request.POST.get(name) in ['1', 'true', 'on', 'yes']

        checklist = PreTripInspectionChecklist(
            vehicle=vehicle,
            driver=driver,
            trip=trip,
            odometer_reading=odometer_reading,
            odometer_photo=odometer_photo,
            tyres_tread_and_pressure=is_checked('tyres_tread_and_pressure'),
            brakes_functional=is_checked('brakes_functional'),
            engine_oil_level=is_checked('engine_oil_level'),
            coolant_level=is_checked('coolant_level'),
            brake_fluid_level=is_checked('brake_fluid_level'),
            battery_and_wiring=is_checked('battery_and_wiring'),
            headlights_and_highbeam=is_checked('headlights_and_highbeam'),
            taillights_and_brakelights=is_checked('taillights_and_brakelights'),
            indicators_and_hazard=is_checked('indicators_and_hazard'),
            wipers_and_washer_fluid=is_checked('wipers_and_washer_fluid'),
            horn_and_mirrors=is_checked('horn_and_mirrors'),
            first_aid_kit_present=is_checked('first_aid_kit_present'),
            fire_extinguisher_present=is_checked('fire_extinguisher_present'),
            spare_wheel_and_jack=is_checked('spare_wheel_and_jack'),
            ac_or_fans_working=is_checked('ac_or_fans_working'),
            cabin_cleanliness=is_checked('cabin_cleanliness'),
            has_visible_body_scratches=is_checked('has_visible_body_scratches'),
            exterior_condition_notes=request.POST.get('exterior_condition_notes', ''),
            defect_notes=request.POST.get('defect_notes', ''),
            driver_signature_name=request.POST.get('driver_signature_name', driver.name),
        )
        checklist.auto_evaluate_status()
        checklist.save()

        if checklist.overall_status == 'passed':
            messages.success(request, f"Pre-Trip Safety Inspection #{checklist.inspection_number} PASSED! Vehicle {vehicle.registration_number} is certified safe for departure.")
        elif checklist.overall_status == 'conditional_pass':
            messages.warning(request, f"Pre-Trip Inspection #{checklist.inspection_number} noted minor issues (Conditional Pass). Proceed with caution.")
        else:
            messages.error(request, f"Inspection #{checklist.inspection_number} FAILED. Critical defects logged to workshop. Vehicle is grounded.")

        return redirect('driver_portal:dashboard')

    return render(request, 'driver_portal/inspection.html', {
        'driver': driver,
        'vehicle': vehicle,
        'trip': trip,
    })


@driver_login_required
def driver_trip_detail(request, trip_id):
    driver = request.driver
    if request.user.is_staff or request.user.is_superuser:
        trip = get_object_or_404(Trip.objects.select_related('vehicle', 'driver', 'booking', 'party'), pk=trip_id)
    else:
        trip = get_object_or_404(Trip.objects.select_related('vehicle', 'driver', 'booking', 'party'), pk=trip_id, driver=driver)

    if not trip.pickup_pin:
        import random
        trip.pickup_pin = f"{random.randint(1000, 9999)}"
        trip.save(update_fields=['pickup_pin'])

    milestone_events = trip.milestone_events.all().order_by('timestamp', 'milestone_index')
    expenses = trip.expenses.all().order_by('-date')
    commute_passes = trip.commute_passes.select_related('commuter', 'boarded_stop').order_by('is_boarded', 'commuter__name')

    return render(request, 'driver_portal/trip_detail.html', {
        'trip': trip,
        'driver': driver,
        'milestone_events': milestone_events,
        'expenses': expenses,
        'commute_passes': commute_passes,
        'milestone_index': trip.milestone_index,
        'progress_percent': trip.milestone_progress_percent,
        'total_expenses': trip.total_expenses,
        'pickup_pin': trip.pickup_pin,
        'is_pin_verified': trip.is_pin_verified,
    })


@driver_login_required
def driver_trip_start(request, trip_id):
    driver = request.driver
    trip = get_object_or_404(Trip, pk=trip_id, driver=driver)

    if request.method == 'POST':
        opening_km = request.POST.get('opening_km')
        if opening_km:
            trip.opening_km = int(opening_km)
            if trip.vehicle and int(opening_km) > (trip.vehicle.current_km or 0):
                trip.vehicle.current_km = int(opening_km)
                trip.vehicle.save(update_fields=['current_km'])

        trip.status = 'started'
        trip.start_date = timezone.now().date()
        trip.start_time = timezone.now().time()
        trip.save()

        messages.success(request, f"Trip #{trip.trip_id} started! Drive safely.")
        return redirect('driver_portal:trip_detail', trip_id=trip.pk)

    return redirect('driver_portal:trip_detail', trip_id=trip.pk)


@driver_login_required
def driver_trip_end(request, trip_id):
    driver = request.driver
    trip = get_object_or_404(Trip, pk=trip_id, driver=driver)

    if request.method == 'POST':
        closing_km = request.POST.get('closing_km')
        notes = request.POST.get('trip_completion_notes', '')

        if closing_km:
            trip.closing_km = int(closing_km)
            if trip.vehicle and int(closing_km) > (trip.vehicle.current_km or 0):
                trip.vehicle.current_km = int(closing_km)
                trip.vehicle.save(update_fields=['current_km'])

        trip.status = 'completed'
        trip.end_date = timezone.now().date()
        trip.end_time = timezone.now().time()
        if notes:
            trip.partner_handover_notes = (trip.partner_handover_notes or '') + f"\n[Driver End Trip Notes]: {notes}"
        trip.save()

        messages.success(request, f"Trip #{trip.trip_id} completed successfully! Excellent work.")
        return redirect('driver_portal:dashboard')

    return redirect('driver_portal:trip_detail', trip_id=trip.pk)


@driver_login_required
def driver_fuel_log(request):
    driver = request.driver
    today = timezone.now().date()
    vehicle = driver.default_vehicles.first() or Vehicle.objects.filter(default_driver=driver).first() or Vehicle.objects.first()

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        fuel_qty = Decimal(request.POST.get('fuel_quantity', '0'))
        fuel_price = Decimal(request.POST.get('fuel_price', '0'))
        fuel_station = request.POST.get('fuel_station', '')
        opening_km = int(request.POST.get('opening_km', 0))
        receipt_photo = request.FILES.get('receipt')

        selected_vehicle = Vehicle.objects.filter(pk=vehicle_id).first() or vehicle

        fuel_record = FuelRecord.objects.create(
            vehicle=selected_vehicle,
            date=today,
            opening_km=opening_km,
            fuel_quantity=fuel_qty,
            fuel_price=fuel_price,
            fuel_station=fuel_station,
            receipt=receipt_photo
        )

        if opening_km and opening_km > (selected_vehicle.current_km or 0):
            selected_vehicle.current_km = opening_km
            selected_vehicle.save(update_fields=['current_km'])

        messages.success(request, f"Fuel purchase of {fuel_qty}L (₹{fuel_price * fuel_qty:.2f}) logged successfully.")
        return redirect('driver_portal:dashboard')

    vehicles = Vehicle.objects.filter(status='active')
    return render(request, 'driver_portal/fuel_log.html', {
        'driver': driver,
        'vehicles': vehicles,
        'default_vehicle': vehicle,
    })


@driver_login_required
def driver_sos_trigger(request):
    driver = request.driver
    active_trip = Trip.objects.filter(driver=driver, status='started').first()
    vehicle = active_trip.vehicle if active_trip else (driver.default_vehicles.first() or Vehicle.objects.filter(default_driver=driver).first() or Vehicle.objects.first())

    if request.method == 'POST':
        incident_type = request.POST.get('incident_type', 'breakdown')
        severity = request.POST.get('severity', 'critical')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        location_address = request.POST.get('location_address', '')
        passenger_count = int(request.POST.get('passenger_count', active_trip.pax_count if active_trip and active_trip.pax_count else 0))
        passengers_safety_status = request.POST.get('passengers_safety_status', 'all_safe')
        description = request.POST.get('description', 'Driver triggered SOS from mobile portal.')

        alert = EmergencyIncidentAlert.objects.create(
            incident_type=incident_type,
            severity=severity,
            vehicle=vehicle,
            driver=driver,
            trip=active_trip,
            reported_at=timezone.now(),
            latitude=Decimal(str(lat)) if lat else None,
            longitude=Decimal(str(lng)) if lng else None,
            location_address=location_address,
            passenger_count=passenger_count,
            passengers_safety_status=passengers_safety_status,
            description=description,
            status='reported'
        )

        messages.error(request, f"🚨 EMERGENCY SOS #{alert.incident_id} BROADCAST! Operations Desk notified immediately.")
        return redirect('driver_portal:dashboard')

    return render(request, 'driver_portal/sos.html', {
        'driver': driver,
        'vehicle': vehicle,
        'active_trip': active_trip,
    })


def pwa_manifest(request):
    """Serve PWA manifest with standard application/manifest+json MIME type."""
    from django.conf import settings
    from django.http import HttpResponse
    manifest_path = settings.BASE_DIR / 'static' / 'manifest.json'
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = '{}'
    return HttpResponse(content, content_type='application/manifest+json')


def pwa_service_worker(request):
    """Serve PWA Service Worker with Service-Worker-Allowed root scope."""
    from django.conf import settings
    from django.http import HttpResponse
    sw_path = settings.BASE_DIR / 'static' / 'sw.js'
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = '// Service Worker'
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response

