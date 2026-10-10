from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F

from core.models import Driver, Vehicle
from operations.models import Trip, TrafficFine, DriverBehaviorLog
from fleet_contracts.models import ContractTripLog
from maintenance.models import ServiceRecord, ComplianceDocument, DefectTicket, PreTripInspectionChecklist
from finance_fleet.models import FuelRecord, FastagTollDeduction
from packages.models import TourFeedbackLog
from .models import DriverScorecard


def calculate_driver_scorecard(driver, start_date=None, end_date=None, period_type='monthly'):
    """
    Computes multi-dimensional driver scorecard:
    - 25% Punctuality & Reliability
    - 30% Safety & Infractions
    - 25% Customer Rating & Hospitality
    - 20% Fuel Eco-Driving Efficiency
    """
    now = timezone.now()
    if not start_date:
        start_date = now.date().replace(day=1)
    if not end_date:
        # End of current month or today
        end_date = now.date()

    # 1. Trips Volume & Punctuality
    trips_qs = Trip.objects.filter(
        driver=driver,
        start_date__gte=start_date,
        start_date__lte=end_date
    )
    contract_trips_qs = ContractTripLog.objects.filter(
        driver=driver,
        date__gte=start_date,
        date__lte=end_date
    )

    ops_trips_count = trips_qs.count()
    contract_trips_count = contract_trips_qs.count()
    total_trips = ops_trips_count + contract_trips_count

    ops_completed = trips_qs.filter(status__in=['completed', 'billed', 'settled']).count()
    contract_completed = contract_trips_qs.filter(status__in=['completed', 'delayed']).count()
    completed_trips = ops_completed + contract_completed

    # Total KMs driven
    kms_ops = sum(t.total_km for t in trips_qs)
    kms_contract = sum(
        (ct.closing_km - ct.opening_km) for ct in contract_trips_qs 
        if ct.closing_km and ct.opening_km and ct.closing_km >= ct.opening_km
    )
    total_kms = kms_ops + kms_contract

    # Punctuality calculation (contract delays > 10m)
    delayed_contract = contract_trips_qs.filter(delay_minutes__gt=10).count()
    delayed_trips = delayed_contract
    on_time_trips = max(0, total_trips - delayed_trips)

    if total_trips > 0:
        punctuality_pct = Decimal(str(max(0, 100.0 - (delayed_trips * 10.0))))
    else:
        punctuality_pct = Decimal("100.0")

    # 2. Safety & Driving Infractions
    behavior_events = DriverBehaviorLog.objects.filter(
        driver=driver,
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date
    )
    overspeeding_count = behavior_events.filter(event_type='overspeeding').count()
    harsh_braking_count = behavior_events.filter(event_type='harsh_braking').count()

    traffic_fines = TrafficFine.objects.filter(
        driver=driver,
        date_of_offence__date__gte=start_date,
        date_of_offence__date__lte=end_date
    )
    traffic_fines_count = traffic_fines.count()
    total_fine_amount = sum((f.fine_amount for f in traffic_fines), Decimal('0.0'))

    # Deduct safety points: 10 per overspeed, 5 per harsh brake, 15 per traffic fine
    safety_deductions = (overspeeding_count * 10) + (harsh_braking_count * 5) + (traffic_fines_count * 15)
    safety_score = Decimal(str(max(0, 100 - safety_deductions)))

    # 3. Customer Rating & Hospitality
    feedbacks = TourFeedbackLog.objects.filter(
        Q(customer_review_text__icontains=driver.name)
    )
    feedback_count = feedbacks.count()
    if feedback_count > 0:
        avg_rating = feedbacks.aggregate(avg=Avg('overall_rating'))['avg'] or 5.0
        avg_rating = Decimal(str(round(avg_rating, 2)))
        customer_rating_score = Decimal(str(round((avg_rating / Decimal('5.0')) * Decimal('100.0'), 2)))
    else:
        avg_rating = Decimal("5.0")
        customer_rating_score = Decimal("95.0")  # Standard benchmark for unreviewed drivers

    # 4. Fuel Eco-Driving Efficiency
    fuel_records = FuelRecord.objects.filter(
        Q(trip__driver=driver) | Q(contract_trip__driver=driver),
        date__gte=start_date,
        date__lte=end_date
    )
    actual_fuel_litres = fuel_records.aggregate(total=Sum('fuel_quantity'))['total'] or Decimal('0.0')

    # Expected fuel: assume benchmark mileage from vehicle (e.g. 12 km/L for cars, 4.5 for bus)
    if total_kms > 0:
        # Default benchmark 10 km/L if not specified
        expected_fuel_litres = Decimal(str(round(total_kms / 10.0, 2)))
    else:
        expected_fuel_litres = actual_fuel_litres

    if expected_fuel_litres > 0 and actual_fuel_litres > 0:
        if actual_fuel_litres <= expected_fuel_litres:
            fuel_efficiency_score = Decimal("100.0")
        else:
            excess_pct = ((actual_fuel_litres - expected_fuel_litres) / expected_fuel_litres) * Decimal("100.0")
            deduction = excess_pct * Decimal("1.5")
            fuel_efficiency_score = max(Decimal("0.0"), Decimal("100.0") - deduction)
            fuel_efficiency_score = Decimal(str(round(fuel_efficiency_score, 2)))
    else:
        fuel_efficiency_score = Decimal("95.0")

    # 5. Composite Weighted Score
    # 25% Punctuality + 30% Safety + 25% Customer Rating + 20% Fuel Eco
    composite = (
        (punctuality_pct * Decimal("0.25")) +
        (safety_score * Decimal("0.30")) +
        (customer_rating_score * Decimal("0.25")) +
        (fuel_efficiency_score * Decimal("0.20"))
    )
    composite = Decimal(str(round(composite, 2)))

    # Grade Assignment
    if composite >= Decimal("95.0"):
        grade = "A+"
    elif composite >= Decimal("85.0"):
        grade = "A"
    elif composite >= Decimal("70.0"):
        grade = "B"
    elif composite >= Decimal("55.0"):
        grade = "C"
    else:
        grade = "D"

    # Save or update Scorecard
    scorecard, _ = DriverScorecard.objects.update_or_create(
        driver=driver,
        month=start_date,
        period_type=period_type,
        defaults={
            "total_trips": total_trips,
            "completed_trips": completed_trips,
            "total_kms_driven": total_kms,
            "on_time_trips": on_time_trips,
            "delayed_trips": delayed_trips,
            "punctuality_score": punctuality_pct,
            "overspeeding_count": overspeeding_count,
            "harsh_braking_count": harsh_braking_count,
            "traffic_fines_count": traffic_fines_count,
            "total_fine_amount": total_fine_amount,
            "safety_score": safety_score,
            "feedback_count": feedback_count,
            "average_rating": avg_rating,
            "customer_rating_score": customer_rating_score,
            "expected_fuel_litres": expected_fuel_litres,
            "actual_fuel_litres": actual_fuel_litres,
            "fuel_efficiency_score": fuel_efficiency_score,
            "overall_composite_score": composite,
            "grade": grade,
        }
    )
    return scorecard


def calculate_fleet_cpk_bulk(vehicles, start_date=None, end_date=None):
    """
    Computes True Cost-Per-KM (CPK), Revenue-Per-KM (RPK), and Operating Margin
    across multiple vehicles in bulk (single-query set aggregations).
    """
    if not vehicles:
        return []

    vehicle_ids = [v.pk for v in vehicles]

    # 1. Trips stats: Prefetch completed/billed/settled trips with related contracts & expenses once
    trips_qs = Trip.objects.filter(
        vehicle_id__in=vehicle_ids,
        status__in=['completed', 'billed', 'settled']
    ).select_related('booking', 'bulk_contract_day__contract').prefetch_related('expenses', 'traffic_fines')
    if start_date:
        trips_qs = trips_qs.filter(start_date__gte=start_date)
    if end_date:
        trips_qs = trips_qs.filter(start_date__lte=end_date)

    trips_by_vehicle = {}
    for t in trips_qs:
        trips_by_vehicle.setdefault(t.vehicle_id, []).append(t)

    # 2. Fuel records
    fuel_qs = FuelRecord.objects.filter(vehicle_id__in=vehicle_ids)
    if start_date: fuel_qs = fuel_qs.filter(date__gte=start_date)
    if end_date: fuel_qs = fuel_qs.filter(date__lte=end_date)
    fuel_by_vehicle = dict(
        fuel_qs.values('vehicle_id').annotate(
            total=Sum(F('fuel_quantity') * F('fuel_price'))
        ).values_list('vehicle_id', 'total')
    )

    # 3. Service records
    service_qs = ServiceRecord.objects.filter(vehicle_id__in=vehicle_ids, status='completed')
    if start_date: service_qs = service_qs.filter(date__gte=start_date)
    if end_date: service_qs = service_qs.filter(date__lte=end_date)
    service_by_vehicle = dict(
        service_qs.values('vehicle_id').annotate(
            total=Sum('total_cost')
        ).values_list('vehicle_id', 'total')
    )

    # 4. FASTag Toll
    toll_qs = FastagTollDeduction.objects.filter(vehicle_id__in=vehicle_ids)
    if start_date: toll_qs = toll_qs.filter(date__date__gte=start_date)
    if end_date: toll_qs = toll_qs.filter(date__date__lte=end_date)
    toll_by_vehicle = dict(
        toll_qs.values('vehicle_id').annotate(
            total=Sum('amount')
        ).values_list('vehicle_id', 'total')
    )

    # 5. Compliance documents (insurance)
    compliance_by_vehicle = dict(
        ComplianceDocument.objects.filter(
            vehicle_id__in=vehicle_ids,
            premium_amount__isnull=False
        ).values('vehicle_id').annotate(
            total=Sum('premium_amount')
        ).values_list('vehicle_id', 'total')
    )

    cpk_list = []
    for vehicle in vehicles:
        trips = trips_by_vehicle.get(vehicle.pk, [])
        total_km = sum(t.total_km for t in trips)
        if total_km == 0:
            total_km = vehicle.current_km or 0

        fuel_cost = fuel_by_vehicle.get(vehicle.pk) or Decimal('0.0')
        maintenance_cost = service_by_vehicle.get(vehicle.pk) or Decimal('0.0')
        toll_cost = toll_by_vehicle.get(vehicle.pk) or Decimal('0.0')
        driver_bata = sum((t.driver_bata * t.days_count for t in trips if t.driver_bata and t.days_count), Decimal('0.0'))

        annual_insurance = compliance_by_vehicle.get(vehicle.pk) or Decimal('0.0')
        monthly_insurance = annual_insurance / Decimal('12.0')
        monthly_emi = vehicle.emi_amount if hasattr(vehicle, 'emi_amount') and vehicle.emi_amount else Decimal('0.0')

        total_direct_costs = fuel_cost + maintenance_cost + toll_cost + driver_bata
        total_all_costs = total_direct_costs + monthly_insurance + monthly_emi

        revenue = sum((t.total_amount for t in trips), Decimal('0.0'))

        safe_km = Decimal(str(max(1, total_km)))
        cpk = round(total_all_costs / safe_km, 2)
        fuel_cpk = round(fuel_cost / safe_km, 2)
        maintenance_cpk = round(maintenance_cost / safe_km, 2)
        rpk = round(revenue / safe_km, 2)
        margin_per_km = round(rpk - cpk, 2)
        margin_pct = round((margin_per_km / rpk) * 100, 1) if rpk > 0 else Decimal('0.0')

        cpk_list.append({
            "vehicle": vehicle,
            "registration_number": vehicle.registration_number,
            "vehicle_type": vehicle.vehicle_type.name if vehicle.vehicle_type else "General",
            "total_km": total_km,
            "revenue": revenue,
            "fuel_cost": fuel_cost,
            "maintenance_cost": maintenance_cost,
            "toll_cost": toll_cost,
            "driver_bata": driver_bata,
            "fixed_amortized": monthly_insurance + monthly_emi,
            "total_cost": total_all_costs,
            "cpk": cpk,
            "fuel_cpk": fuel_cpk,
            "maintenance_cpk": maintenance_cpk,
            "rpk": rpk,
            "margin_per_km": margin_per_km,
            "margin_pct": margin_pct,
        })

    return cpk_list


def calculate_vehicle_cpk(vehicle, start_date=None, end_date=None):
    """
    Computes True Cost-Per-KM (CPK), Revenue-Per-KM (RPK), and Operating Margin
    for a single vehicle.
    """
    results = calculate_fleet_cpk_bulk([vehicle], start_date=start_date, end_date=end_date)
    return results[0] if results else {}


def get_fleet_utilization_breakdown():
    """
    Computes real-time fleet utilization breakdown in bulk (4 set queries):
    - Active: On Trip
    - Standby: In Yard, Fit for Duty
    - Maintenance: In Workshop / Grounded
    - Idle: Available but no trips in last 5 days
    """
    vehicles = list(Vehicle.objects.all().select_related('vehicle_type'))
    total_count = len(vehicles)
    if total_count == 0:
        return {
            "total_count": 0,
            "active_count": 0, "standby_count": 0, "maintenance_count": 0, "idle_count": 0,
            "utilization_pct": 0.0, "vehicles": []
        }

    five_days_ago = timezone.now().date() - timedelta(days=5)

    # Bulk Query 1: Active trips
    active_trips_qs = Trip.objects.filter(
        status__in=['assigned', 'started']
    ).select_related('driver').order_by('-start_date')
    active_trips_by_vehicle = {}
    for t in active_trips_qs:
        if t.vehicle_id not in active_trips_by_vehicle:
            active_trips_by_vehicle[t.vehicle_id] = t

    # Bulk Query 2: Open defect tickets
    open_defect_vehicle_ids = set(
        DefectTicket.objects.filter(status='open').values_list('vehicle_id', flat=True)
    )

    # Bulk Query 3: Failed pre-trip checklists in last 5 days
    failed_inspection_vehicle_ids = set(
        PreTripInspectionChecklist.objects.filter(
            overall_status='failed',
            created_at__date__gte=five_days_ago
        ).values_list('vehicle_id', flat=True)
    )

    # Bulk Query 4: Recent trips in last 5 days
    recent_trip_vehicle_ids = set(
        Trip.objects.filter(start_date__gte=five_days_ago).values_list('vehicle_id', flat=True)
    )

    active_count = 0
    standby_count = 0
    maintenance_count = 0
    idle_count = 0

    detailed_vehicles = []

    for v in vehicles:
        on_active_trip = active_trips_by_vehicle.get(v.pk)

        in_maintenance = (
            v.status in ['in_shop', 'breakdown', 'maintenance'] or
            (v.pk in open_defect_vehicle_ids) or
            (v.pk in failed_inspection_vehicle_ids)
        )

        recent_trip_exists = (v.pk in recent_trip_vehicle_ids)

        if on_active_trip:
            status_cat = "active"
            status_label = "🟢 On Trip"
            active_count += 1
        elif in_maintenance:
            status_cat = "maintenance"
            status_label = "🟠 In Workshop"
            maintenance_count += 1
        elif not recent_trip_exists:
            status_cat = "idle"
            status_label = "⚪ Idle (>5 Days)"
            idle_count += 1
        else:
            status_cat = "standby"
            status_label = "🔵 Ready Standby"
            standby_count += 1

        detailed_vehicles.append({
            "vehicle": v,
            "registration_number": v.registration_number,
            "model": f"{v.brand} {v.model}",
            "vehicle_type": v.vehicle_type.name if v.vehicle_type else "Vehicle",
            "status_cat": status_cat,
            "status_label": status_label,
            "current_location": v.current_location or "Depot Yard",
            "current_km": v.current_km or 0,
            "active_trip": on_active_trip,
        })

    utilization_pct = round((active_count / max(1, total_count)) * 100, 1)

    return {
        "total_count": total_count,
        "active_count": active_count,
        "standby_count": standby_count,
        "maintenance_count": maintenance_count,
        "idle_count": idle_count,
        "utilization_pct": utilization_pct,
        "vehicles": detailed_vehicles,
    }


def get_driver_scorecards_leaderboard(start_date=None, end_date=None, period_type='monthly', refresh=False):
    """
    Returns sorted driver scorecards leaderboard for all active drivers.
    Uses existing persisted monthly snapshots (1 query) or computes missing ones in bulk.
    """
    now = timezone.now()
    if not start_date:
        start_date = now.date().replace(day=1)
    if not end_date:
        end_date = now.date()

    active_drivers = list(Driver.objects.filter(status='active'))
    if not active_drivers:
        return []

    active_driver_ids = [d.pk for d in active_drivers]

    if not refresh:
        existing = list(
            DriverScorecard.objects.filter(
                month=start_date,
                period_type=period_type,
                driver_id__in=active_driver_ids
            ).select_related('driver').order_by('-overall_composite_score')
        )
        if len(existing) >= len(active_drivers) and len(existing) > 0:
            return existing

    # Bulk Compute across all active drivers:
    # 1. Ops Trips
    trips_stats = {
        row['driver_id']: row for row in Trip.objects.filter(
            driver_id__in=active_driver_ids,
            start_date__gte=start_date,
            start_date__lte=end_date
        ).values('driver_id').annotate(
            total_trips=Count('id'),
            completed_trips=Count('id', filter=Q(status__in=['completed', 'billed', 'settled'])),
            total_km=Sum(F('closing_km') - F('opening_km'), filter=Q(closing_km__gte=F('opening_km')))
        )
    }

    # 2. Contract Trips
    contract_stats = {
        row['driver_id']: row for row in ContractTripLog.objects.filter(
            driver_id__in=active_driver_ids,
            date__gte=start_date,
            date__lte=end_date
        ).values('driver_id').annotate(
            total_trips=Count('id'),
            completed_trips=Count('id', filter=Q(status__in=['completed', 'delayed'])),
            delayed_trips=Count('id', filter=Q(delay_minutes__gt=10)),
            km_sum=Sum(F('closing_km') - F('opening_km'), filter=Q(closing_km__gte=F('opening_km')))
        )
    }

    # 3. Driver behavior
    behavior_stats = {
        row['driver_id']: row for row in DriverBehaviorLog.objects.filter(
            driver_id__in=active_driver_ids,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).values('driver_id').annotate(
            overspeeding=Count('id', filter=Q(event_type='overspeeding')),
            harsh_braking=Count('id', filter=Q(event_type='harsh_braking'))
        )
    }

    # 4. Traffic fines
    fine_stats = {
        row['driver_id']: row for row in TrafficFine.objects.filter(
            driver_id__in=active_driver_ids,
            date_of_offence__date__gte=start_date,
            date_of_offence__date__lte=end_date
        ).values('driver_id').annotate(
            fine_count=Count('id'),
            fine_sum=Sum('fine_amount')
        )
    }

    # 5. Fuel records
    fuel_by_driver = dict(
        FuelRecord.objects.filter(
            trip__driver_id__in=active_driver_ids,
            date__gte=start_date,
            date__lte=end_date
        ).values('trip__driver_id').annotate(
            actual_litres=Sum('fuel_quantity')
        ).values_list('trip__driver_id', 'actual_litres')
    )

    scorecard_objs = []
    for driver in active_drivers:
        d_id = driver.pk
        t_stat = trips_stats.get(d_id, {})
        c_stat = contract_stats.get(d_id, {})
        b_stat = behavior_stats.get(d_id, {})
        f_stat = fine_stats.get(d_id, {})

        total_trips = t_stat.get('total_trips', 0) + c_stat.get('total_trips', 0)
        completed_trips = t_stat.get('completed_trips', 0) + c_stat.get('completed_trips', 0)
        total_kms = (t_stat.get('total_km') or 0) + (c_stat.get('km_sum') or 0)
        delayed_trips = c_stat.get('delayed_trips', 0)
        on_time_trips = max(0, total_trips - delayed_trips)

        if total_trips > 0:
            punctuality_pct = Decimal(str(max(0, 100.0 - (delayed_trips * 10.0))))
        else:
            punctuality_pct = Decimal("100.0")

        overspeeding_count = b_stat.get('overspeeding', 0)
        harsh_braking_count = b_stat.get('harsh_braking', 0)
        traffic_fines_count = f_stat.get('fine_count', 0)
        total_fine_amount = f_stat.get('fine_sum') or Decimal('0.0')

        safety_deductions = (overspeeding_count * 10) + (harsh_braking_count * 5) + (traffic_fines_count * 15)
        safety_score = Decimal(str(max(0, 100 - safety_deductions)))

        avg_rating = Decimal("5.0")
        customer_rating_score = Decimal("95.0")
        feedback_count = 0

        actual_fuel_litres = fuel_by_driver.get(d_id) or Decimal('0.0')
        expected_fuel_litres = Decimal(str(round(total_kms / 10.0, 2))) if total_kms > 0 else actual_fuel_litres

        if expected_fuel_litres > 0 and actual_fuel_litres > 0:
            if actual_fuel_litres <= expected_fuel_litres:
                fuel_efficiency_score = Decimal("100.0")
            else:
                excess_pct = ((actual_fuel_litres - expected_fuel_litres) / expected_fuel_litres) * Decimal("100.0")
                deduction = excess_pct * Decimal("1.5")
                fuel_efficiency_score = max(Decimal("0.0"), Decimal("100.0") - deduction)
                fuel_efficiency_score = Decimal(str(round(fuel_efficiency_score, 2)))
        else:
            fuel_efficiency_score = Decimal("95.0")

        composite = (
            (punctuality_pct * Decimal("0.25")) +
            (safety_score * Decimal("0.30")) +
            (customer_rating_score * Decimal("0.25")) +
            (fuel_efficiency_score * Decimal("0.20"))
        )
        composite = Decimal(str(round(composite, 2)))

        if composite >= Decimal("95.0"): grade = "A+"
        elif composite >= Decimal("85.0"): grade = "A"
        elif composite >= Decimal("70.0"): grade = "B"
        elif composite >= Decimal("55.0"): grade = "C"
        else: grade = "D"

        card, _ = DriverScorecard.objects.update_or_create(
            driver=driver,
            month=start_date,
            period_type=period_type,
            defaults={
                "total_trips": total_trips,
                "completed_trips": completed_trips,
                "total_kms_driven": total_kms,
                "on_time_trips": on_time_trips,
                "delayed_trips": delayed_trips,
                "punctuality_score": punctuality_pct,
                "overspeeding_count": overspeeding_count,
                "harsh_braking_count": harsh_braking_count,
                "traffic_fines_count": traffic_fines_count,
                "total_fine_amount": total_fine_amount,
                "safety_score": safety_score,
                "feedback_count": feedback_count,
                "average_rating": avg_rating,
                "customer_rating_score": customer_rating_score,
                "expected_fuel_litres": expected_fuel_litres,
                "actual_fuel_litres": actual_fuel_litres,
                "fuel_efficiency_score": fuel_efficiency_score,
                "overall_composite_score": composite,
                "grade": grade,
            }
        )
        scorecard_objs.append(card)

    scorecard_objs.sort(key=lambda x: x.overall_composite_score, reverse=True)
    return scorecard_objs

