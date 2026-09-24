from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q

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


def calculate_vehicle_cpk(vehicle, start_date=None, end_date=None):
    """
    Computes True Cost-Per-KM (CPK), Revenue-Per-KM (RPK), and Operating Margin.
    """
    trips_qs = Trip.objects.filter(
        vehicle=vehicle,
        status__in=['completed', 'billed', 'settled']
    )
    if start_date:
        trips_qs = trips_qs.filter(start_date__gte=start_date)
    if end_date:
        trips_qs = trips_qs.filter(start_date__lte=end_date)

    # 1. Total KMs Run
    total_km = sum(t.total_km for t in trips_qs)
    if total_km == 0:
        total_km = vehicle.current_km or 0

    # 2. Direct Operating Costs
    fuel_records = FuelRecord.objects.filter(vehicle=vehicle)
    if start_date: fuel_records = fuel_records.filter(date__gte=start_date)
    if end_date: fuel_records = fuel_records.filter(date__lte=end_date)
    fuel_cost = sum((r.amount for r in fuel_records), Decimal('0.0'))

    service_records = ServiceRecord.objects.filter(vehicle=vehicle, status='completed')
    if start_date: service_records = service_records.filter(date__gte=start_date)
    if end_date: service_records = service_records.filter(date__lte=end_date)
    maintenance_cost = sum((s.total_cost for s in service_records), Decimal('0.0'))

    toll_deductions = FastagTollDeduction.objects.filter(vehicle=vehicle)
    if start_date: toll_deductions = toll_deductions.filter(date__date__gte=start_date)
    if end_date: toll_deductions = toll_deductions.filter(date__date__lte=end_date)
    toll_cost = sum((t.amount for t in toll_deductions), Decimal('0.0'))

    driver_bata = sum((t.driver_bata * t.days_count for t in trips_qs if t.driver_bata and t.days_count), Decimal('0.0'))

    # 3. Amortized Fixed Costs (Insurance + Tax + EMI)
    compliance_docs = ComplianceDocument.objects.filter(vehicle=vehicle, premium_amount__isnull=False)
    annual_insurance = sum((d.premium_amount for d in compliance_docs), Decimal('0.0'))
    monthly_insurance = annual_insurance / Decimal('12.0')

    monthly_emi = vehicle.emi_amount if hasattr(vehicle, 'emi_amount') and vehicle.emi_amount else Decimal('0.0')

    total_direct_costs = fuel_cost + maintenance_cost + toll_cost + driver_bata
    total_all_costs = total_direct_costs + monthly_insurance + monthly_emi

    # 4. Revenue
    revenue = sum((t.total_amount for t in trips_qs), Decimal('0.0'))

    # 5. Per-KM Metrics
    safe_km = Decimal(str(max(1, total_km)))
    cpk = round(total_all_costs / safe_km, 2)
    fuel_cpk = round(fuel_cost / safe_km, 2)
    maintenance_cpk = round(maintenance_cost / safe_km, 2)
    rpk = round(revenue / safe_km, 2)
    margin_per_km = round(rpk - cpk, 2)
    margin_pct = round((margin_per_km / rpk) * 100, 1) if rpk > 0 else Decimal('0.0')

    return {
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
    }


def get_fleet_utilization_breakdown():
    """
    Computes real-time fleet utilization breakdown:
    - Active: On Trip
    - Standby: In Yard, Fit for Duty
    - Maintenance: In Workshop / Grounded
    - Idle: Available but no trips in last 5 days
    """
    vehicles = Vehicle.objects.all()
    total_count = vehicles.count()
    if total_count == 0:
        return {
            "total_count": 0,
            "active_count": 0, "standby_count": 0, "maintenance_count": 0, "idle_count": 0,
            "utilization_pct": 0.0, "vehicles": []
        }

    five_days_ago = timezone.now().date() - timedelta(days=5)

    active_count = 0
    standby_count = 0
    maintenance_count = 0
    idle_count = 0

    detailed_vehicles = []

    for v in vehicles:
        # Check if on active trip
        on_active_trip = Trip.objects.filter(
            vehicle=v,
            status__in=['assigned', 'started']
        ).first()

        # Check maintenance condition
        in_maintenance = (
            v.status in ['in_shop', 'breakdown', 'maintenance'] or
            DefectTicket.objects.filter(vehicle=v, status='open').exists() or
            PreTripInspectionChecklist.objects.filter(vehicle=v, overall_status='failed').filter(created_at__date__gte=five_days_ago).exists()
        )

        recent_trip_exists = Trip.objects.filter(vehicle=v, start_date__gte=five_days_ago).exists()

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

    utilization_pct = round((active_count / total_count) * 100, 1)

    return {
        "total_count": total_count,
        "active_count": active_count,
        "standby_count": standby_count,
        "maintenance_count": maintenance_count,
        "idle_count": idle_count,
        "utilization_pct": utilization_pct,
        "vehicles": detailed_vehicles,
    }
