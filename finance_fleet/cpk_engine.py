from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q

from core.models import Vehicle, VehicleType, Driver
from operations.models import Trip
from finance.models import FuelRecord, FastagTollDeduction, TripExpense, DriverSettlement
from maintenance.models import ServiceRecord, ComplianceDocument

DEFAULT_DIESEL_PRICE = Decimal('92.50')  # Standard Tamil Nadu / Chennai Commercial Diesel Price (₹/L)

# Baseline vehicle mileage fallbacks if not configured on vehicle or vehicle_type
CATEGORY_DEFAULT_MILEAGE = {
    'sedan': Decimal('14.00'),
    'dzire': Decimal('15.00'),
    'etios': Decimal('14.00'),
    'suv': Decimal('11.00'),
    'innova': Decimal('11.50'),
    'crysta': Decimal('11.00'),
    'tempo': Decimal('8.50'),
    'traveller': Decimal('8.00'),
    'minibus': Decimal('6.50'),
    'bus': Decimal('4.50'),
    'coach': Decimal('4.00'),
    'default': Decimal('10.00'),
}

CATEGORY_DEFAULT_MAINTENANCE_CPK = {
    'sedan': Decimal('1.20'),
    'suv': Decimal('1.80'),
    'innova': Decimal('1.80'),
    'tempo': Decimal('2.50'),
    'traveller': Decimal('2.50'),
    'bus': Decimal('4.00'),
    'coach': Decimal('4.50'),
    'default': Decimal('1.75'),
}

CATEGORY_DEFAULT_BATTA = {
    'sedan': Decimal('400.00'),
    'suv': Decimal('500.00'),
    'innova': Decimal('500.00'),
    'tempo': Decimal('600.00'),
    'traveller': Decimal('700.00'),
    'bus': Decimal('900.00'),
    'coach': Decimal('1000.00'),
    'default': Decimal('500.00'),
}


def resolve_expected_mileage(vehicle):
    """
    Returns baseline expected mileage (KM/L) for a vehicle with intelligent fallbacks.
    """
    if vehicle.expected_mileage and vehicle.expected_mileage > 0:
        return vehicle.expected_mileage
    if vehicle.vehicle_type and vehicle.vehicle_type.expected_mileage_kmpl and vehicle.vehicle_type.expected_mileage_kmpl > 0:
        return vehicle.vehicle_type.expected_mileage_kmpl

    # Match based on model or vehicle type name
    name_str = f"{vehicle.brand} {vehicle.model} {vehicle.vehicle_type.name if vehicle.vehicle_type else ''}".lower()
    for cat, mileage in CATEGORY_DEFAULT_MILEAGE.items():
        if cat in name_str:
            return mileage
    return CATEGORY_DEFAULT_MILEAGE['default']


def resolve_maintenance_allowance_cpk(vehicle):
    """Returns baseline maintenance allowance per KM for wear & tear."""
    name_str = f"{vehicle.brand} {vehicle.model} {vehicle.vehicle_type.name if vehicle.vehicle_type else ''}".lower()
    for cat, rate in CATEGORY_DEFAULT_MAINTENANCE_CPK.items():
        if cat in name_str:
            return rate
    return CATEGORY_DEFAULT_MAINTENANCE_CPK['default']


def resolve_driver_batta_rate(vehicle):
    """Returns default daily driver batta for the vehicle category."""
    if vehicle.vehicle_type and vehicle.vehicle_type.driver_bata and vehicle.vehicle_type.driver_bata > 0:
        return vehicle.vehicle_type.driver_bata
    name_str = f"{vehicle.brand} {vehicle.model} {vehicle.vehicle_type.name if vehicle.vehicle_type else ''}".lower()
    for cat, batta in CATEGORY_DEFAULT_BATTA.items():
        if cat in name_str:
            return batta
    return CATEGORY_DEFAULT_BATTA['default']


def calculate_vehicle_cpk(vehicle, diesel_price_override=None, start_date=None, end_date=None):
    """
    Computes complete Cost-Per-KM (CPK), Revenue-Per-KM (RPK), and Operating Margin
    for a single fleet vehicle across Fuel, Tolls, Driver Batta, Maintenance, and Fixed Overheads.
    """
    diesel_price = Decimal(str(diesel_price_override or DEFAULT_DIESEL_PRICE))

    # 1. Operational KM & Revenue from completed/billed/settled trips
    trips_qs = Trip.objects.filter(
        vehicle=vehicle,
        status__in=['completed', 'billed', 'settled']
    )
    if start_date:
        trips_qs = trips_qs.filter(start_date__gte=start_date)
    if end_date:
        trips_qs = trips_qs.filter(start_date__lte=end_date)

    trip_count = trips_qs.count()
    total_km = sum((t.total_km for t in trips_qs), 0)
    billed_revenue = sum((t.total_amount for t in trips_qs), Decimal('0.00'))

    # If trips have no logged total_km, estimate from vehicle current_km or default
    if total_km == 0 and trip_count > 0:
        total_km = trip_count * 150  # 150 km baseline per trip

    safe_km = Decimal(str(max(1, total_km)))

    # 2. Fuel Economics
    fuel_qs = FuelRecord.objects.filter(vehicle=vehicle)
    if start_date:
        fuel_qs = fuel_qs.filter(date__gte=start_date)
    if end_date:
        fuel_qs = fuel_qs.filter(date__lte=end_date)

    actual_fuel_liters = sum((f.fuel_quantity for f in fuel_qs if f.fuel_quantity), Decimal('0.00'))
    actual_fuel_cost = sum((f.amount for f in fuel_qs), Decimal('0.00'))

    expected_mileage = resolve_expected_mileage(vehicle)

    # If actual fuel records exist, use actual liters; if live diesel price override provided, recalculate
    if actual_fuel_liters > 0:
        actual_mileage = round(safe_km / actual_fuel_liters, 2)
        if diesel_price_override:
            fuel_cost = round(actual_fuel_liters * diesel_price, 2)
        else:
            fuel_cost = actual_fuel_cost
    else:
        # Theoretical fuel consumption based on expected mileage & live diesel price
        actual_mileage = expected_mileage
        estimated_liters = safe_km / expected_mileage
        fuel_cost = round(estimated_liters * diesel_price, 2)
        actual_fuel_liters = round(estimated_liters, 2)

    fuel_cpk = round(fuel_cost / safe_km, 2)

    # Fuel theft / efficiency anomaly
    mileage_variance_pct = Decimal('0.0')
    is_theft_suspected = False
    excess_fuel_cost = Decimal('0.00')

    if actual_mileage > 0 and expected_mileage > 0:
        mileage_variance_pct = round(((actual_mileage - expected_mileage) / expected_mileage) * Decimal('100.0'), 1)
        if mileage_variance_pct < Decimal('-15.0'):
            is_theft_suspected = True
            expected_liters = safe_km / expected_mileage
            excess_liters = max(Decimal('0.00'), actual_fuel_liters - expected_liters)
            excess_fuel_cost = round(excess_liters * diesel_price, 2)

    # 3. FASTag & Electronic Tolls
    toll_qs = FastagTollDeduction.objects.filter(vehicle=vehicle)
    if start_date:
        toll_qs = toll_qs.filter(transaction_time__date__gte=start_date)
    if end_date:
        toll_qs = toll_qs.filter(transaction_time__date__lte=end_date)
    fastag_tolls = sum((t.amount for t in toll_qs), Decimal('0.00'))

    # Manual tolls logged in trip expenses
    manual_tolls = sum(
        (exp.amount for t in trips_qs for exp in t.expenses.filter(expense_type='toll')),
        Decimal('0.00')
    )
    total_toll_cost = fastag_tolls + manual_tolls
    toll_cpk = round(total_toll_cost / safe_km, 2)

    # 4. Driver Batta & Crew Allowances
    # Calculated from trip driver_bata * days_count + driver_food expenses + driver settlements
    driver_batta_trips = sum(
        ((t.driver_bata or resolve_driver_batta_rate(vehicle)) * Decimal(str(max(1, t.days_count))) for t in trips_qs),
        Decimal('0.00')
    )
    driver_food_exp = sum(
        (exp.amount for t in trips_qs for exp in t.expenses.filter(expense_type='driver_food')),
        Decimal('0.00')
    )
    driver_settlement_batta = sum(
        (s.batta for t in trips_qs for s in t.settlements.all()),
        Decimal('0.00')
    )
    total_driver_cost = max(driver_batta_trips, driver_settlement_batta) + driver_food_exp
    driver_cpk = round(total_driver_cost / safe_km, 2)

    # 5. Vehicle Maintenance, Tyres & Servicing
    service_qs = ServiceRecord.objects.filter(vehicle=vehicle, status='completed')
    if start_date:
        service_qs = service_qs.filter(date__gte=start_date)
    if end_date:
        service_qs = service_qs.filter(date__lte=end_date)
    direct_maintenance = sum((s.total_cost for s in service_qs), Decimal('0.00'))

    trip_repairs = sum(
        (exp.amount for t in trips_qs for exp in t.expenses.filter(expense_type='repair')),
        Decimal('0.00')
    )
    # If no service recorded yet, use standard amortized maintenance allowance per KM
    baseline_maint_allowance = safe_km * resolve_maintenance_allowance_cpk(vehicle)
    total_maintenance_cost = max(direct_maintenance + trip_repairs, baseline_maint_allowance)
    maintenance_cpk = round(total_maintenance_cost / safe_km, 2)

    # 6. Fixed Overheads Amortization (Insurance + Road Tax + EMI)
    compliance_docs = ComplianceDocument.objects.filter(vehicle=vehicle, premium_amount__isnull=False)
    annual_insurance = sum((d.premium_amount for d in compliance_docs), Decimal('0.00'))
    # Monthly insurance allocation
    monthly_insurance = annual_insurance / Decimal('12.00')
    monthly_emi = vehicle.emi_amount if hasattr(vehicle, 'emi_amount') and vehicle.emi_amount else Decimal('0.00')
    total_fixed_cost = monthly_insurance + monthly_emi
    fixed_cpk = round(total_fixed_cost / safe_km, 2)

    # 7. Total Cost, RPK, and Profitability
    total_operating_cost = fuel_cost + total_toll_cost + total_driver_cost + total_maintenance_cost + total_fixed_cost
    total_cpk = round(total_operating_cost / safe_km, 2)
    rpk = round(billed_revenue / safe_km, 2)
    net_profit = billed_revenue - total_operating_cost
    net_margin_per_km = round(rpk - total_cpk, 2)
    margin_pct = round((net_profit / billed_revenue) * Decimal('100.0'), 1) if billed_revenue > 0 else Decimal('0.0')

    # 8. Profitability Tier Health Badge
    if margin_pct >= Decimal('25.0'):
        tier = 'tier_1_high'
        tier_label = '🟢 Tier 1: High Profit (≥25%)'
        tier_badge = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    elif margin_pct >= Decimal('10.0'):
        tier = 'tier_2_standard'
        tier_label = '🟡 Tier 2: Standard Margin (10-25%)'
        tier_badge = 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    elif margin_pct >= Decimal('0.0'):
        tier = 'tier_3_low'
        tier_label = '🟠 Tier 3: Low Margin (0-10%)'
        tier_badge = 'bg-orange-500/10 text-orange-400 border-orange-500/20'
    else:
        tier = 'tier_4_loss'
        tier_label = '🔴 Tier 4: Loss-Making Asset (<0%)'
        tier_badge = 'bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse'

    return {
        'vehicle': vehicle,
        'vehicle_id': vehicle.pk,
        'registration_number': vehicle.registration_number,
        'model_name': f"{vehicle.brand} {vehicle.model}".strip() or (vehicle.vehicle_type.name if vehicle.vehicle_type else 'Fleet Vehicle'),
        'vehicle_type': vehicle.vehicle_type.name if vehicle.vehicle_type else 'Standard Fleet',
        'seating_capacity': vehicle.seating_capacity,
        'trip_count': trip_count,
        'total_km': total_km,
        'billed_revenue': billed_revenue,
        'fuel_cost': fuel_cost,
        'fuel_liters': actual_fuel_liters,
        'actual_mileage': actual_mileage,
        'expected_mileage': expected_mileage,
        'mileage_variance_pct': mileage_variance_pct,
        'is_theft_suspected': is_theft_suspected,
        'excess_fuel_cost': excess_fuel_cost,
        'toll_cost': total_toll_cost,
        'driver_cost': total_driver_cost,
        'maintenance_cost': total_maintenance_cost,
        'fixed_cost': total_fixed_cost,
        'total_operating_cost': total_operating_cost,
        'fuel_cpk': fuel_cpk,
        'toll_cpk': toll_cpk,
        'driver_cpk': driver_cpk,
        'maintenance_cpk': maintenance_cpk,
        'fixed_cpk': fixed_cpk,
        'total_cpk': total_cpk,
        'rpk': rpk,
        'net_profit': net_profit,
        'net_margin_per_km': net_margin_per_km,
        'margin_pct': margin_pct,
        'tier': tier,
        'tier_label': tier_label,
        'tier_badge': tier_badge,
    }


def get_fleet_cpk_radar_metrics(diesel_price_override=None, start_date=None, end_date=None, vehicle_type_id=None):
    """
    Aggregates multi-dimensional fleet-wide CPK and Profitability metrics.
    """
    diesel_price = Decimal(str(diesel_price_override or DEFAULT_DIESEL_PRICE))
    vehicles_qs = Vehicle.objects.filter(status__in=['available', 'assigned', 'on_trip'])
    if vehicle_type_id:
        vehicles_qs = vehicles_qs.filter(vehicle_type_id=vehicle_type_id)

    vehicle_rows = []
    total_fleet_km = 0
    total_fleet_revenue = Decimal('0.00')
    total_fuel_cost = Decimal('0.00')
    total_fuel_liters = Decimal('0.00')
    total_toll_cost = Decimal('0.00')
    total_driver_cost = Decimal('0.00')
    total_maintenance_cost = Decimal('0.00')
    total_fixed_cost = Decimal('0.00')
    total_fleet_cost = Decimal('0.00')
    theft_alert_count = 0
    total_theft_loss = Decimal('0.00')

    tier_counts = {
        'tier_1_high': 0,
        'tier_2_standard': 0,
        'tier_3_low': 0,
        'tier_4_loss': 0,
    }

    for v in vehicles_qs[:60]:  # Top active fleet slice
        data = calculate_vehicle_cpk(v, diesel_price_override=diesel_price, start_date=start_date, end_date=end_date)
        vehicle_rows.append(data)

        total_fleet_km += data['total_km']
        total_fleet_revenue += data['billed_revenue']
        total_fuel_cost += data['fuel_cost']
        total_fuel_liters += data['fuel_liters']
        total_toll_cost += data['toll_cost']
        total_driver_cost += data['driver_cost']
        total_maintenance_cost += data['maintenance_cost']
        total_fixed_cost += data['fixed_cost']
        total_fleet_cost += data['total_operating_cost']

        if data['is_theft_suspected']:
            theft_alert_count += 1
            total_theft_loss += data['excess_fuel_cost']

        tier_counts[data['tier']] += 1

    safe_fleet_km = Decimal(str(max(1, total_fleet_km)))

    fleet_avg_cpk = round(total_fleet_cost / safe_fleet_km, 2)
    fleet_fuel_cpk = round(total_fuel_cost / safe_fleet_km, 2)
    fleet_toll_cpk = round(total_toll_cost / safe_fleet_km, 2)
    fleet_driver_cpk = round(total_driver_cost / safe_fleet_km, 2)
    fleet_maint_cpk = round(total_maintenance_cost / safe_fleet_km, 2)
    fleet_fixed_cpk = round(total_fixed_cost / safe_fleet_km, 2)
    fleet_avg_rpk = round(total_fleet_revenue / safe_fleet_km, 2)
    fleet_net_profit = total_fleet_revenue - total_fleet_cost
    fleet_margin_pct = round((fleet_net_profit / total_fleet_revenue) * Decimal('100.0'), 1) if total_fleet_revenue > 0 else Decimal('0.0')

    # Sort vehicle leaderboard by margin_pct descending
    sorted_vehicles = sorted(vehicle_rows, key=lambda x: x['margin_pct'], reverse=True)
    top_performers = sorted_vehicles[:5]
    underperformers = [v for v in sorted_vehicles if v['margin_pct'] < Decimal('10.0')]

    return {
        'diesel_price': diesel_price,
        'vehicles_analyzed': len(vehicle_rows),
        'total_fleet_km': total_fleet_km,
        'total_fleet_revenue': total_fleet_revenue,
        'total_fleet_cost': total_fleet_cost,
        'fleet_net_profit': fleet_net_profit,
        'fleet_margin_pct': fleet_margin_pct,
        'fleet_avg_cpk': fleet_avg_cpk,
        'fleet_avg_rpk': fleet_avg_rpk,
        'fleet_fuel_cpk': fleet_fuel_cpk,
        'fleet_toll_cpk': fleet_toll_cpk,
        'fleet_driver_cpk': fleet_driver_cpk,
        'fleet_maint_cpk': fleet_maint_cpk,
        'fleet_fixed_cpk': fleet_fixed_cpk,
        'total_fuel_liters': total_fuel_liters,
        'theft_alert_count': theft_alert_count,
        'total_theft_loss': total_theft_loss,
        'tier_counts': tier_counts,
        'leaderboard': sorted_vehicles,
        'top_performers': top_performers,
        'underperformers': underperformers,
    }


def get_route_profitability_benchmarks(diesel_price=DEFAULT_DIESEL_PRICE):
    """
    Analyzes core inter-city and corporate routes to provide tariff guidance and break-even pricing.
    """
    routes = [
        {'route_name': 'Chennai ➔ Bengaluru (Highway IT Corridor)', 'distance_km': 350, 'tolls': Decimal('420.00'), 'days': 1},
        {'route_name': 'Chennai ➔ Pondicherry (East Coast Road)', 'distance_km': 160, 'tolls': Decimal('165.00'), 'days': 1},
        {'route_name': 'Chennai ➔ Coimbatore (Textile Hub Express)', 'distance_km': 510, 'tolls': Decimal('680.00'), 'days': 2},
        {'route_name': 'Chennai ➔ Tirupati (Temple Shuttle)', 'distance_km': 140, 'tolls': Decimal('120.00'), 'days': 1},
        {'route_name': 'Chennai ➔ Madurai (South Heritage Highway)', 'distance_km': 460, 'tolls': Decimal('560.00'), 'days': 2},
        {'route_name': 'Chennai ➔ Ooty (Hill Station Circuit)', 'distance_km': 560, 'tolls': Decimal('720.00'), 'days': 3},
    ]

    benchmarks = []
    for r in routes:
        dist = Decimal(str(r['distance_km']))
        # Innova Crysta standard benchmark (11.0 km/l)
        fuel_liters = dist / Decimal('11.00')
        fuel_cost = round(fuel_liters * diesel_price, 2)
        toll_cost = r['tolls']
        driver_cost = Decimal('600.00') * Decimal(str(r['days']))
        maintenance_cost = round(dist * Decimal('1.80'), 2)
        fixed_overhead = round(dist * Decimal('0.85'), 2)

        total_route_cost = fuel_cost + toll_cost + driver_cost + maintenance_cost + fixed_overhead
        route_cpk = round(total_route_cost / dist, 2)

        # Minimum quote for 25% target margin: Price = Cost / (1 - 0.25)
        recommended_quote = (total_route_cost / Decimal('0.75')).quantize(Decimal('100'), rounding=ROUND_HALF_UP)
        recommended_rpk = round(recommended_quote / dist, 2)
        projected_margin = recommended_quote - total_route_cost

        benchmarks.append({
            'route_name': r['route_name'],
            'distance_km': r['distance_km'],
            'days': r['days'],
            'fuel_liters': round(fuel_liters, 1),
            'fuel_cost': fuel_cost,
            'toll_cost': toll_cost,
            'driver_cost': driver_cost,
            'maintenance_cost': maintenance_cost,
            'total_route_cost': total_route_cost,
            'route_cpk': route_cpk,
            'recommended_quote': recommended_quote,
            'recommended_rpk': recommended_rpk,
            'projected_margin': projected_margin,
            'margin_pct': Decimal('25.0'),
        })

    return benchmarks


def simulate_what_if_tariff(diesel_price=DEFAULT_DIESEL_PRICE, distance_km=300, vehicle_category='innova', target_margin_pct=Decimal('25.0'), toll_override=None, days_count=1):
    """
    Live What-If Simulation and Tariff Optimizer.
    Given fuel price, distance, and vehicle category, computes exact cost components, break-even,
    and recommended quote price to guarantee the specified operating margin.
    """
    dist = Decimal(str(max(1, distance_km)))
    price = Decimal(str(diesel_price))
    margin_target = Decimal(str(target_margin_pct))
    days = Decimal(str(max(1, days_count)))
    cat = str(vehicle_category).lower()

    # Resolve parameters
    mileage = CATEGORY_DEFAULT_MILEAGE.get(cat, CATEGORY_DEFAULT_MILEAGE['default'])
    maint_rate = CATEGORY_DEFAULT_MAINTENANCE_CPK.get(cat, CATEGORY_DEFAULT_MAINTENANCE_CPK['default'])
    batta_rate = CATEGORY_DEFAULT_BATTA.get(cat, CATEGORY_DEFAULT_BATTA['default'])

    # 1. Fuel
    fuel_liters = round(dist / mileage, 2)
    fuel_cost = round(fuel_liters * price, 2)

    # 2. Toll
    if toll_override is not None:
        toll_cost = Decimal(str(toll_override))
    else:
        # Standard average toll estimation: approx ₹1.10 per KM on major Indian NHAI highways
        toll_cost = round(dist * Decimal('1.10'), 2)

    # 3. Driver Batta
    driver_cost = round(batta_rate * days, 2)

    # 4. Maintenance & Wear
    maintenance_cost = round(dist * maint_rate, 2)

    # 5. Fixed Overheads Amortization (approx ₹0.85/KM)
    fixed_overhead = round(dist * Decimal('0.85'), 2)

    # 6. Total Operating Cost
    total_cost = fuel_cost + toll_cost + driver_cost + maintenance_cost + fixed_overhead
    cpk = round(total_cost / dist, 2)

    # 7. Margin & Recommended Quote
    divisor = Decimal('1.00') - (margin_target / Decimal('100.00'))
    if divisor <= Decimal('0.05'):
        divisor = Decimal('0.05')
    recommended_quote = (total_cost / divisor).quantize(Decimal('10'), rounding=ROUND_HALF_UP)
    recommended_rpk = round(recommended_quote / dist, 2)
    net_profit = recommended_quote - total_cost
    break_even_quote = total_cost

    return {
        'diesel_price': price,
        'distance_km': int(dist),
        'vehicle_category': cat.upper(),
        'days_count': int(days),
        'mileage_kmpl': mileage,
        'fuel_liters': fuel_liters,
        'fuel_cost': fuel_cost,
        'toll_cost': toll_cost,
        'driver_cost': driver_cost,
        'maintenance_cost': maintenance_cost,
        'fixed_overhead': fixed_overhead,
        'total_trip_cost': total_cost,
        'cpk': cpk,
        'break_even_quote': break_even_quote,
        'target_margin_pct': margin_target,
        'recommended_quote': recommended_quote,
        'recommended_rpk': recommended_rpk,
        'projected_profit': net_profit,
    }


def get_fuel_anomaly_radar(threshold_variance_pct=Decimal('15.0')):
    """
    Scans fleet for vehicles with abnormal mileage drops (>15% variance from baseline)
    and quantifies the excess fuel theft / leakage financial loss.
    """
    vehicles = Vehicle.objects.filter(fuel_records__isnull=False).distinct()
    anomalies = []

    for v in vehicles:
        fuel_qs = v.fuel_records.all()
        total_liters = sum((f.fuel_quantity for f in fuel_qs if f.fuel_quantity), Decimal('0.00'))
        if total_liters <= Decimal('0.00'):
            continue

        total_km = sum((t.total_km for t in v.trips.filter(status__in=['completed', 'billed', 'settled'])), 0)
        if total_km == 0:
            total_km = v.trips.count() * 150

        if total_km <= 0:
            continue

        actual_mileage = round(Decimal(str(total_km)) / total_liters, 2)
        expected_mileage = resolve_expected_mileage(v)

        variance_pct = round(((actual_mileage - expected_mileage) / expected_mileage) * Decimal('100.0'), 1)
        if variance_pct < -abs(threshold_variance_pct):
            expected_liters = Decimal(str(total_km)) / expected_mileage
            excess_liters = max(Decimal('0.00'), total_liters - expected_liters)
            financial_loss = round(excess_liters * DEFAULT_DIESEL_PRICE, 2)

            anomalies.append({
                'vehicle_id': v.pk,
                'registration_number': v.registration_number,
                'model_name': f"{v.brand} {v.model}".strip() or "Fleet Asset",
                'actual_mileage': actual_mileage,
                'expected_mileage': expected_mileage,
                'variance_pct': variance_pct,
                'excess_liters': round(excess_liters, 1),
                'financial_loss': financial_loss,
                'assigned_driver': v.default_driver.name if v.default_driver else 'Unassigned',
                'severity': 'danger' if variance_pct < Decimal('-25.0') else 'warning',
            })

    return sorted(anomalies, key=lambda x: x['financial_loss'], reverse=True)
