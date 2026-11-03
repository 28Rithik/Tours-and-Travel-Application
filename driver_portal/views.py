import json
from decimal import Decimal
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Driver, Vehicle
from operations.models import Trip, EmergencyIncidentAlert
from fleet_contracts.models import ContractTripLog, RouteStop
from fleet_commute.models import CommuterBoardingPass
from maintenance.models import PreTripInspectionChecklist, DefectTicket
from finance_fleet.models import FuelRecord
from .models import DriverPortalAccount, DriverAttendanceLog, RouteIssueReport


def get_current_driver(request):
    """
    Identifies the active driver from:
    1. Query param ?driver_id=XX (for admin / dispatch preview and driver switcher)
    2. Direct token in ?token=XX (from SMS / WhatsApp link)
    3. Session driver_id
    4. Authenticated user's linked driver profile
    5. Fallback to first active driver for staff/superuser preview
    """
    # 0. Query param override for staff / switcher
    req_driver_id = request.GET.get('driver_id')
    if req_driver_id:
        driver_candidate = Driver.objects.filter(pk=req_driver_id).first()
        if driver_candidate:
            request.session['driver_id'] = driver_candidate.pk
            return driver_candidate

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

        clean_phone = phone.replace(' ', '').replace('-', '').replace('+91', '')
        driver = Driver.objects.filter(phone__icontains=clean_phone).first()

        if not driver:
            messages.error(request, f"No driver profile found matching phone {phone}. Please contact dispatch.")
            return render(request, 'driver_portal/login.html')

        portal_user = User.objects.filter(username=f"driver_{driver.pk}").first()
        if not portal_user:
            portal_user = User.objects.create_user(
                username=f"driver_{driver.pk}",
                password=f"pin_{pin or '1234'}"
            )

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

        if pin and portal_acc.quick_pin and portal_acc.quick_pin != pin:
            messages.error(request, "Incorrect PIN. Please re-enter your 4-digit driver PIN.")
            return render(request, 'driver_portal/login.html', {'entered_phone': phone})

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


# ==============================================================================
# 1. DRIVER DASHBOARD & ATTENDANCE COCKPIT
# ==============================================================================

@driver_login_required
def driver_dashboard(request):
    driver = request.driver
    today = timezone.now().date()
    now = timezone.now()

    # 1. Today's Full Schedule: Corporate Commute Trips + Outstation Tours
    commute_trips = list(ContractTripLog.objects.filter(
        driver=driver,
        date=today
    ).select_related('shift__route', 'vehicle').order_by('scheduled_departure_time', 'id'))

    tour_trips = list(Trip.objects.filter(
        driver=driver,
        start_date=today
    ).select_related('vehicle', 'booking', 'party').order_by('start_time', 'id'))

    # Active trip in progress
    active_commute = next((t for t in commute_trips if t.status in ['assigned', 'in_progress']), None)
    active_tour = next((t for t in tour_trips if t.status in ['assigned', 'driver_confirmed', 'started']), None)
    current_trip = active_tour
    active_commute_trip = active_commute

    # 2. Assigned Vehicle
    current_vehicle = None
    if active_commute and active_commute.vehicle:
        current_vehicle = active_commute.vehicle
    elif active_tour and active_tour.vehicle:
        current_vehicle = active_tour.vehicle
    else:
        current_vehicle = driver.default_vehicles.first() or Vehicle.objects.filter(default_driver=driver).first() or Vehicle.objects.filter(status='active').first()

    # 3. Pre-Trip Inspection status
    inspection_today = None
    if current_vehicle:
        cutoff = now - timezone.timedelta(hours=24)
        inspection_today = PreTripInspectionChecklist.objects.filter(
            vehicle=current_vehicle,
            driver=driver,
            inspection_date__gte=cutoff
        ).first()

    # 4. Attendance & Duty Hours Sentry
    active_attendance = DriverAttendanceLog.objects.filter(
        driver=driver,
        date=today,
        status='on_duty'
    ).first()

    latest_attendance = DriverAttendanceLog.objects.filter(
        driver=driver,
        date=today
    ).first()

    if active_attendance:
        elapsed_seconds = (now - active_attendance.clock_in_time).total_seconds()
        duty_hours_elapsed = round(elapsed_seconds / 3600.0, 2)
        duty_hours_formatted = f"{int(duty_hours_elapsed)}h {int((duty_hours_elapsed % 1) * 60)}m"
        is_on_duty = True
        safe_hours_remaining = max(0.0, round(8.0 - duty_hours_elapsed, 1))
        fatigue_status = 'safe' if duty_hours_elapsed < 6.0 else ('warning' if duty_hours_elapsed < 8.0 else 'critical')
    elif latest_attendance:
        duty_hours_elapsed = float(latest_attendance.duty_hours or 0.0)
        duty_hours_formatted = f"{int(duty_hours_elapsed)}h {int((duty_hours_elapsed % 1) * 60)}m"
        is_on_duty = False
        safe_hours_remaining = max(0.0, round(8.0 - duty_hours_elapsed, 1))
        fatigue_status = 'completed'
    else:
        duty_hours_elapsed = 0.0
        duty_hours_formatted = "0h 0m"
        is_on_duty = False
        safe_hours_remaining = 8.0
        fatigue_status = 'off_duty'

    # 5. Today's Operational Stats
    total_trips_today = len(commute_trips) + len(tour_trips)
    completed_commute = sum(1 for c in commute_trips if c.status == 'completed')
    completed_tour = sum(1 for t in tour_trips if t.status == 'completed')
    completed_trips_count = completed_commute + completed_tour

    in_progress_count = (1 if active_commute else 0) + (1 if active_tour else 0)
    pending_trips_count = max(0, total_trips_today - completed_trips_count - in_progress_count)

    total_passengers_today = sum(c.passenger_count or 0 for c in commute_trips) + sum(t.pax_count or 0 for t in tour_trips)
    total_km_today = sum(
        (c.closing_km - c.opening_km) for c in commute_trips if c.closing_km and c.opening_km and c.closing_km >= c.opening_km
    )

    # 6. Recent Past Trips
    recent_trips = Trip.objects.filter(driver=driver).order_by('-start_date')[:5]

    # 7. Demo Driver Switcher (For testing & dispatch evaluation)
    roster_drivers = list(Driver.objects.filter(status='active').order_by('name')[:15])

    return render(request, 'driver_portal/dashboard.html', {
        'driver': driver,
        'today': today,
        'commute_trips': commute_trips,
        'tour_trips': tour_trips,
        'active_commute_trip': active_commute_trip,
        'current_trip': current_trip,
        'current_vehicle': current_vehicle,
        'inspection_today': inspection_today,
        # Attendance & Duty Sentry
        'active_attendance': active_attendance,
        'latest_attendance': latest_attendance,
        'is_on_duty': is_on_duty,
        'duty_hours_elapsed': duty_hours_elapsed,
        'duty_hours_formatted': duty_hours_formatted,
        'safe_hours_remaining': safe_hours_remaining,
        'fatigue_status': fatigue_status,
        # Today KPIs
        'total_trips_today': total_trips_today,
        'completed_trips_count': completed_trips_count,
        'in_progress_count': in_progress_count,
        'pending_trips_count': pending_trips_count,
        'total_passengers_today': total_passengers_today,
        'total_km_today': total_km_today,
        'recent_trips': recent_trips,
        'roster_drivers': roster_drivers,
    })


# ==============================================================================
# 2. ROUTE NAVIGATION & PICKUP COCKPIT (DOMAIN 2)
# ==============================================================================

@driver_login_required
def driver_commute_navigation(request, trip_log_id):
    """
    Real-time Route Navigation, Pickup Sequence, and Passenger Manifest Cockpit.
    Provides live Google Maps turn-by-turn navigation, stop-by-stop sequencing,
    boarding OTP verification, absent passenger flags, and delay notifications.
    """
    driver = request.driver
    trip_log = get_object_or_404(
        ContractTripLog.objects.select_related('shift__route', 'vehicle', 'driver'),
        pk=trip_log_id
    )

    route = trip_log.shift.route
    stops = list(route.stops.filter(is_active=True).order_by('stop_order'))
    passes = list(CommuterBoardingPass.objects.filter(
        trip_log=trip_log
    ).select_related('commuter__boarding_stop', 'boarded_stop'))

    # Group passengers by stop
    stops_data = []
    current_active_stop = None
    total_boarded = 0
    total_absent = 0
    total_waiting = 0

    for idx, stop in enumerate(stops):
        # Match commuters whose assigned stop is this stop
        stop_passes = [
            p for p in passes
            if (p.commuter.boarding_stop_id == stop.id) or (p.boarded_stop_id == stop.id)
        ]
        # If no passes matched directly, distribute unassigned passes evenly for rich demo display
        if not stop_passes and idx == 0:
            stop_passes = [p for p in passes if not p.commuter.boarding_stop_id and not p.boarded_stop_id]

        boarded_in_stop = sum(1 for p in stop_passes if p.is_boarded)
        absent_in_stop = sum(1 for p in stop_passes if p.is_no_show)
        waiting_in_stop = len(stop_passes) - boarded_in_stop - absent_in_stop

        total_boarded += boarded_in_stop
        total_absent += absent_in_stop
        total_waiting += waiting_in_stop

        is_completed = (len(stop_passes) > 0 and waiting_in_stop == 0)
        is_current = False
        if not is_completed and current_active_stop is None:
            is_current = True
            current_active_stop = {
                'stop': stop,
                'order': stop.stop_order,
                'name': stop.name,
                'landmark': stop.pickup_landmark or 'Designated Bus Bay',
                'waiting_count': waiting_in_stop,
                'total_passengers': len(stop_passes),
                'passes': stop_passes,
                'latitude': stop.latitude,
                'longitude': stop.longitude,
            }

        stops_data.append({
            'stop': stop,
            'order': stop.stop_order,
            'name': stop.name,
            'offset_minutes': stop.scheduled_offset_minutes,
            'landmark': stop.pickup_landmark or 'Main Road Pickup Bay',
            'passes': stop_passes,
            'boarded_count': boarded_in_stop,
            'absent_count': absent_in_stop,
            'waiting_count': waiting_in_stop,
            'is_completed': is_completed,
            'is_current': is_current,
        })

    # Fallback to last stop if all stops completed
    if not current_active_stop and stops:
        last_stop = stops[-1]
        current_active_stop = {
            'stop': last_stop,
            'order': last_stop.stop_order,
            'name': last_stop.name,
            'landmark': last_stop.pickup_landmark or 'Final Office Gate',
            'waiting_count': 0,
            'total_passengers': len(passes),
            'passes': [],
            'latitude': last_stop.latitude,
            'longitude': last_stop.longitude,
        }

    # Generate Google Maps Deep Link for current destination
    maps_destination = f"{current_active_stop['name']}, {route.destination}"
    if current_active_stop.get('latitude') and current_active_stop.get('longitude'):
        maps_destination = f"{current_active_stop['latitude']},{current_active_stop['longitude']}"
    google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={maps_destination.replace(' ', '+')}"

    # Recent reported issues on this trip
    reported_issues = RouteIssueReport.objects.filter(contract_trip_log=trip_log).order_by('-reported_at')[:3]

    return render(request, 'driver_portal/commute_navigation.html', {
        'driver': driver,
        'trip_log': trip_log,
        'route': route,
        'stops_data': stops_data,
        'current_active_stop': current_active_stop,
        'google_maps_url': google_maps_url,
        'total_boarded': total_boarded,
        'total_absent': total_absent,
        'total_waiting': total_waiting,
        'total_manifest': len(passes),
        'reported_issues': reported_issues,
    })


# ==============================================================================
# 3. ATTENDANCE & TRIP ACTION APIS
# ==============================================================================

@driver_login_required
@require_POST
def api_driver_clock_in(request):
    """Start shift duty and log driver clock-in."""
    driver = request.driver
    today = timezone.now().date()
    shift_name = request.POST.get('shift_name', 'general')
    location = request.POST.get('location', 'Coimbatore Central Depot Gate')
    odometer_start = request.POST.get('odometer_start')

    # Close any dangling previous attendance
    DriverAttendanceLog.objects.filter(driver=driver, status='on_duty').update(
        status='off_duty',
        clock_out_time=timezone.now()
    )

    att = DriverAttendanceLog.objects.create(
        driver=driver,
        date=today,
        shift_name=shift_name,
        status='on_duty',
        clock_in_time=timezone.now(),
        clock_in_location=location,
        odometer_start=int(odometer_start) if odometer_start else None,
        fatigue_rest_compliant=True
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Clock-in successful! Welcome on duty, Captain {driver.name}.",
        'attendance_id': att.id,
        'clock_in_time': att.clock_in_time.strftime('%I:%M %p')
    })


@driver_login_required
@require_POST
def api_driver_clock_out(request):
    """End shift duty and log driver clock-out."""
    driver = request.driver
    location = request.POST.get('location', 'Coimbatore Central Depot Gate')
    odometer_end = request.POST.get('odometer_end')
    notes = request.POST.get('notes', '')

    active_att = DriverAttendanceLog.objects.filter(driver=driver, status='on_duty').first()
    if not active_att:
        return JsonResponse({'status': 'error', 'message': 'No active shift found to clock out from.'}, status=400)

    active_att.clock_out_time = timezone.now()
    active_att.clock_out_location = location
    if odometer_end:
        active_att.odometer_end = int(odometer_end)
    active_att.duty_hours = active_att.calculate_duty_hours()
    active_att.status = 'off_duty'
    if notes:
        active_att.notes = (active_att.notes or '') + f"\n[Clock-out notes]: {notes}"
    active_att.save()

    return JsonResponse({
        'status': 'success',
        'message': f"Shift completed safely! Total duty logged: {active_att.duty_hours} hours.",
        'duty_hours': float(active_att.duty_hours)
    })


@driver_login_required
@require_POST
def api_driver_report_delay(request):
    """Report traffic congestion, road blockage, or mechanical delay."""
    driver = request.driver
    trip_log_id = request.POST.get('trip_log_id')
    issue_type = request.POST.get('issue_type', 'traffic_jam')
    delay_minutes = int(request.POST.get('delay_minutes', 15))
    current_location = request.POST.get('current_location', 'Corridor Route')
    notes = request.POST.get('notes', '')

    trip_log = ContractTripLog.objects.filter(pk=trip_log_id).first() if trip_log_id else None

    report = RouteIssueReport.objects.create(
        driver=driver,
        contract_trip_log=trip_log,
        issue_type=issue_type,
        delay_minutes=delay_minutes,
        current_location=current_location,
        notes=notes,
        status='reported'
    )

    if trip_log:
        trip_log.delay_minutes = delay_minutes
        trip_log.delay_reason = f"[{report.get_issue_type_display()}]: {notes or 'Reported via Driver Portal'}"
        trip_log.save(update_fields=['delay_minutes', 'delay_reason'])

    return JsonResponse({
        'status': 'success',
        'message': f"Delay alert (+{delay_minutes}m) logged and broadcasted to Transport Control Center.",
        'report_id': report.id,
        'delay_minutes': delay_minutes
    })


@driver_login_required
@require_POST
def api_driver_board_commuter(request):
    """Mark an employee boarded at their pickup stop with optional OTP check."""
    driver = request.driver
    pass_id = request.POST.get('pass_id')
    otp = request.POST.get('otp', '').strip()

    bp = get_object_or_404(CommuterBoardingPass, pk=pass_id)

    # Optional OTP validation
    if otp and bp.boarding_otp and otp != bp.boarding_otp:
        return JsonResponse({'status': 'error', 'message': 'Incorrect OTP! Please check commuter boarding PIN.'}, status=400)

    bp.is_boarded = True
    bp.is_no_show = False
    bp.boarded_at = timezone.now()
    bp.boarded_by_driver = driver
    bp.save(update_fields=['is_boarded', 'is_no_show', 'boarded_at', 'boarded_by_driver'])

    return JsonResponse({
        'status': 'success',
        'message': f"✅ {bp.commuter.name} boarded successfully!",
        'pass_id': bp.id,
        'boarded_time': bp.boarded_at.strftime('%I:%M %p')
    })


@driver_login_required
@require_POST
def api_driver_absent_commuter(request):
    """Mark a commuter as absent / no-show at pickup point."""
    driver = request.driver
    pass_id = request.POST.get('pass_id')
    reason = request.POST.get('reason', 'Passenger absent at pickup point')

    bp = get_object_or_404(CommuterBoardingPass, pk=pass_id)
    bp.is_no_show = True
    bp.is_boarded = False
    bp.no_show_at = timezone.now()
    bp.no_show_reason = reason
    bp.boarded_by_driver = driver
    bp.save(update_fields=['is_no_show', 'is_boarded', 'no_show_at', 'no_show_reason', 'boarded_by_driver'])

    return JsonResponse({
        'status': 'success',
        'message': f"⚠️ {bp.commuter.name} marked absent/no-show.",
        'pass_id': bp.id,
        'absent_time': bp.no_show_at.strftime('%I:%M %p')
    })


@driver_login_required
@require_POST
def api_start_commute_trip(request, trip_log_id):
    """Start commute trip and record opening odometer."""
    driver = request.driver
    trip_log = get_object_or_404(ContractTripLog, pk=trip_log_id, driver=driver)
    opening_km = request.POST.get('opening_km')

    trip_log.status = 'in_progress'
    trip_log.actual_departure_time = timezone.now().time()
    if opening_km:
        trip_log.opening_km = int(opening_km)
        if trip_log.vehicle and int(opening_km) > (trip_log.vehicle.current_km or 0):
            trip_log.vehicle.current_km = int(opening_km)
            trip_log.vehicle.save(update_fields=['current_km'])
    trip_log.save()

    messages.success(request, f"🚀 Route {trip_log.shift.route.name} started! Have a safe drive.")
    return redirect('driver_portal:commute_navigation', trip_log_id=trip_log.pk)


@driver_login_required
@require_POST
def api_complete_commute_trip(request, trip_log_id):
    """Complete commute trip, record closing odometer, and log mileage."""
    driver = request.driver
    trip_log = get_object_or_404(ContractTripLog, pk=trip_log_id, driver=driver)
    closing_km = request.POST.get('closing_km')

    trip_log.status = 'completed'
    trip_log.actual_arrival_time = timezone.now().time()
    if closing_km:
        trip_log.closing_km = int(closing_km)
        if trip_log.vehicle and int(closing_km) > (trip_log.vehicle.current_km or 0):
            trip_log.vehicle.current_km = int(closing_km)
            trip_log.vehicle.save(update_fields=['current_km'])
    trip_log.save()

    messages.success(request, f"🏁 Trip #{trip_log.pk} completed successfully! Excellent work.")
    return redirect('driver_portal:dashboard')


# ==============================================================================
# 4. PRE-TRIP INSPECTION, TOUR DETAILS, FUEL & SOS (EXISTING CAPABILITIES)
# ==============================================================================

@driver_login_required
def driver_inspection(request):
    driver = request.driver
    vehicle_id = request.GET.get('vehicle_id') or request.POST.get('vehicle_id')
    trip_id = request.GET.get('trip_id') or request.POST.get('trip_id')

    trip = Trip.objects.filter(pk=trip_id).first() if trip_id else None
    vehicle = Vehicle.objects.filter(pk=vehicle_id).first() if vehicle_id else (trip.vehicle if trip else None)
    if not vehicle:
        vehicle = driver.default_vehicles.first() or Vehicle.objects.filter(status='active').first()

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
    sw_path = settings.BASE_DIR / 'static' / 'sw.js'
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = '// Service Worker'
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response
