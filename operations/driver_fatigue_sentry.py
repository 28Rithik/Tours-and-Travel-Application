"""
Chauffeur Fatigue & Mandatory Duty Rest Sentry
Sivagayathiri Tours & Travels ERP

Implements Motor Transport Workers compliance, 8-hour mandatory inter-duty rest intervals,
continuous driving hour surveillance, and hazardous night ghat road safety alerts.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from core.models import Driver
from operations.models import Trip, DriverFatigueAuditLog
from django.core.cache import cache


GHAT_KEYWORDS = [
    'ooty', 'udhagamandalam', 'kodaikanal', 'kodai', 'yercaud', 'valparai',
    'kolli', 'kolli hills', 'munnar', 'thekkady', 'wayanad', 'coorg',
    'madikeri', 'chikmagalur', 'gudalur', 'hairpin', 'ghat'
]


def is_ghat_route(destination_or_route):
    """Detects whether a route involves mountain / ghat terrain with hairpin bends."""
    if not destination_or_route:
        return False
    text = str(destination_or_route).lower()
    return any(k in text for k in GHAT_KEYWORDS)


def is_night_window(dt=None):
    """Detects whether given datetime or current time falls in night driving hours (22:00 to 06:00)."""
    t = dt or timezone.now()
    hour = t.hour
    return hour >= 22 or hour < 6


def evaluate_driver_fatigue(driver, prospective_trip=None):
    """
    Evaluates chauffeur rest status, prior duty completion, and fatigue risk.
    Enforces mandatory 8h rest, checks continuous driving hours, and flags night ghat hazards.
    """
    now = timezone.now()
    
    # 1. Identify driver's latest completed trip or ongoing trip
    prior_trip = Trip.objects.filter(
        driver=driver,
        status__in=['completed', 'billed']
    ).order_by('-end_date', '-id').first()

    active_trip = prospective_trip or Trip.objects.filter(
        driver=driver,
        status__in=['assigned', 'dispatched', 'in_progress', 'active']
    ).order_by('-start_date', '-id').first()

    # Calculate rest hours
    rest_hours = Decimal('12.00')  # Default baseline if no prior trip
    if prior_trip and prior_trip.end_date:
        # Convert date/time
        end_dt = timezone.make_aware(
            datetime.combine(prior_trip.end_date, datetime.min.time())
        ) if isinstance(prior_trip.end_date, type(now.date())) else prior_trip.end_date
        
        diff_hours = (now - end_dt).total_seconds() / 3600.0
        rest_hours = Decimal(str(max(0.0, round(diff_hours, 1))))

    # Continuous duty hours if on active trip
    continuous_duty = Decimal('0.00')
    ghat_detected = False
    night_detected = is_night_window(now)

    if active_trip:
        dest_text = ""
        if active_trip.booking:
            dest_text = f"{active_trip.booking.pickup_location} to {active_trip.booking.destination}"
        elif active_trip.package:
            dest_text = active_trip.package.title
        elif active_trip.notes:
            dest_text = active_trip.notes

        ghat_detected = is_ghat_route(dest_text)

        if active_trip.start_date:
            start_dt = timezone.make_aware(
                datetime.combine(active_trip.start_date, datetime.min.time())
            ) if isinstance(active_trip.start_date, type(now.date())) else active_trip.start_date
            
            hours_elapsed = (now - start_dt).total_seconds() / 3600.0
            if hours_elapsed > 0:
                continuous_duty = Decimal(str(min(16.0, round(hours_elapsed, 1))))
            else:
                continuous_duty = Decimal('2.0')

    # Determine risk level
    if ghat_detected and night_detected:
        risk_level = 'ghat_night_risk'
        risk_label = 'Night Ghat Road Hazard Alert'
        badge = 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300'
        can_dispatch = False
        message = 'High Risk: Active night driving through mountain ghat corridor. Driver must take hill station halt.'
    elif rest_hours < Decimal('5.0'):
        risk_level = 'critical_deficit'
        risk_label = 'Critical Rest Deficit (<5h)'
        badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
        can_dispatch = False
        message = f'Severe rest deficit ({rest_hours}h rest). Mandatory 8h statutory rest interval violated.'
    elif rest_hours < Decimal('8.0') or continuous_duty >= Decimal('9.0'):
        risk_level = 'fatigue_risk'
        risk_label = 'Fatigue Warning (5-8h Rest / Extended Shift)'
        badge = 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
        can_dispatch = False
        message = f'Fatigue caution: Only {rest_hours}h rest since prior trip or {continuous_duty}h continuous duty.'
    elif rest_hours <= Decimal('10.0'):
        risk_level = 'adequate_rest'
        risk_label = 'Adequate Rest (8-10h)'
        badge = 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
        can_dispatch = True
        message = 'Driver complies with standard statutory 8-hour rest requirements.'
    else:
        risk_level = 'well_rested'
        risk_label = 'Well Rested (>10h)'
        badge = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
        can_dispatch = True
        message = f'Chauffeur fully rested ({rest_hours}h rest interval). Green light for dispatch.'

    return {
        'driver': driver,
        'driver_name': driver.name,
        'driver_phone': getattr(driver, 'phone', 'N/A'),
        'risk_level': risk_level,
        'risk_label': risk_label,
        'badge': badge,
        'rest_hours_elapsed': rest_hours,
        'continuous_duty_hours': continuous_duty,
        'is_ghat_route': ghat_detected,
        'is_night_shift': night_detected,
        'can_dispatch': can_dispatch,
        'warning_message': message,
        'prior_trip': prior_trip,
        'active_trip': active_trip,
    }


def audit_all_active_drivers():
    """Audits entire driver roster and computes fleet safety metrics, cached for 60s."""
    cache_key = 'driver_fatigue_audit_cache'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    drivers = Driver.objects.filter(status='active')[:25]
    if not drivers.exists():
        drivers = Driver.objects.all()[:25]

    evaluations = []
    stats = {
        'total_audited': 0,
        'well_rested': 0,
        'adequate_rest': 0,
        'fatigue_risk': 0,
        'critical_deficit': 0,
        'ghat_night_risk': 0,
        'override_count': 0,
    }

    for d in drivers:
        res = evaluate_driver_fatigue(d)
        evaluations.append(res)
        stats['total_audited'] += 1
        stats[res['risk_level']] = stats.get(res['risk_level'], 0) + 1

    # Check recent overrides
    recent_overrides = DriverFatigueAuditLog.objects.filter(manager_override=True).count()
    stats['override_count'] = recent_overrides

    result = (evaluations, stats)
    cache.set(cache_key, result, timeout=60)
    return result


def record_fatigue_override(driver_id, trip_id=None, reason="", user=None):
    """Allows dispatcher / safety manager to record safety override with justification."""
    driver = Driver.objects.get(id=driver_id)
    trip = Trip.objects.filter(id=trip_id).first() if trip_id else None
    eval_res = evaluate_driver_fatigue(driver, prospective_trip=trip)

    log = DriverFatigueAuditLog.objects.create(
        driver=driver,
        trip=trip,
        previous_trip=eval_res.get('prior_trip'),
        rest_hours_elapsed=eval_res['rest_hours_elapsed'],
        continuous_duty_hours=eval_res['continuous_duty_hours'],
        is_ghat_route=eval_res['is_ghat_route'],
        is_night_shift=eval_res['is_night_shift'],
        risk_level=eval_res['risk_level'],
        manager_override=True,
        override_reason=reason or 'Manager authorized with auxiliary co-driver / mandatory tea halt relief.',
        override_by=user if user and user.is_authenticated else None
    )
    cache.delete('driver_fatigue_audit_cache')
    return log


def seed_sample_fatigue_audits():
    """Seeds realistic safety logs for the sentry dashboard."""
    drivers = Driver.objects.all()[:5]
    if not drivers:
        return []

    logs = []
    scenarios = [
        (Decimal('11.5'), Decimal('3.5'), False, False, 'well_rested', False, ''),
        (Decimal('8.5'), Decimal('6.0'), False, False, 'adequate_rest', False, ''),
        (Decimal('6.2'), Decimal('8.5'), False, True, 'fatigue_risk', True, 'Relief driver assigned at Salem Toll Plaza'),
        (Decimal('3.5'), Decimal('10.0'), False, False, 'critical_deficit', False, 'Blocked from dispatch until 18:00 hrs'),
        (Decimal('7.0'), Decimal('4.0'), True, True, 'ghat_night_risk', True, 'Ooty hairpin ascent authorized with co-driver'),
    ]

    trips = list(Trip.objects.all()[:5])

    for i, d in enumerate(drivers):
        if i >= len(scenarios):
            break
        rest, cont, ghat, night, risk, over, reason = scenarios[i]
        t = trips[i] if i < len(trips) else None
        
        log, _ = DriverFatigueAuditLog.objects.get_or_create(
            driver=d,
            risk_level=risk,
            defaults={
                'trip': t,
                'rest_hours_elapsed': rest,
                'continuous_duty_hours': cont,
                'is_ghat_route': ghat,
                'is_night_shift': night,
                'manager_override': over,
                'override_reason': reason,
            }
        )
        logs.append(log)
    return logs
