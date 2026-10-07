"""
🤖 Dynamic AI Quotation & Tariff Calculator Engine
===================================================
Automatic route distance computation, dynamic hill station/interstate permit
addition, and multi-vehicle convoy quotation generator.
"""
import math
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone

from core.models import VehicleType


# ==============================================================================
# ROUTE DATABASE — Common Indian Routes with Distances (km)
# ==============================================================================
ROUTE_DATABASE = {
    # Chennai Hub
    ('chennai', 'bangalore'): 350, ('chennai', 'madurai'): 462, ('chennai', 'pondicherry'): 150,
    ('chennai', 'coimbatore'): 505, ('chennai', 'tirupati'): 135, ('chennai', 'ooty'): 560,
    ('chennai', 'kodaikanal'): 530, ('chennai', 'rameshwaram'): 575, ('chennai', 'kanyakumari'): 700,
    ('chennai', 'trichy'): 332, ('chennai', 'salem'): 340, ('chennai', 'vellore'): 140,
    ('chennai', 'thanjavur'): 342, ('chennai', 'mahabalipuram'): 60, ('chennai', 'hyderabad'): 630,
    ('chennai', 'mysore'): 480, ('chennai', 'munnar'): 585, ('chennai', 'wayanad'): 680,
    ('chennai', 'vizag'): 800, ('chennai', 'goa'): 630, ('chennai', 'kerala'): 700,
    # Bangalore Hub
    ('bangalore', 'mysore'): 150, ('bangalore', 'ooty'): 270, ('bangalore', 'coorg'): 265,
    ('bangalore', 'goa'): 560, ('bangalore', 'hampi'): 340, ('bangalore', 'chikmagalur'): 245,
    ('bangalore', 'wayanad'): 280, ('bangalore', 'pondicherry'): 310, ('bangalore', 'munnar'): 475,
    ('bangalore', 'hyderabad'): 570, ('bangalore', 'tirupati'): 255,
    # Coimbatore Hub
    ('coimbatore', 'ooty'): 86, ('coimbatore', 'kodaikanal'): 170, ('coimbatore', 'munnar'): 160,
    ('coimbatore', 'pollachi'): 40, ('coimbatore', 'valparai'): 100,
    # Madurai Hub
    ('madurai', 'rameshwaram'): 170, ('madurai', 'kodaikanal'): 120, ('madurai', 'thekkady'): 140,
    ('madurai', 'kanyakumari'): 245, ('madurai', 'courtallam'): 160,
    # Hyderabad Hub
    ('hyderabad', 'tirupati'): 555, ('hyderabad', 'vizag'): 620, ('hyderabad', 'warangal'): 150,
    ('hyderabad', 'srisailam'): 215, ('hyderabad', 'goa'): 630,
}

# Hill stations requiring surcharges
HILL_STATIONS = {
    'ooty', 'kodaikanal', 'munnar', 'valparai', 'wayanad', 'coorg', 'chikmagalur',
    'yercaud', 'coonoor', 'kotagiri', 'meghamalai', 'courtallam', 'yelagiri',
    'horsley_hills', 'araku', 'lambasingi', 'shimla', 'manali', 'darjeeling',
    'mussoorie', 'nainital', 'gangtok', 'shillong',
}

# States requiring interstate permits
STATE_BORDERS = {
    'tamil_nadu': {'chennai', 'madurai', 'coimbatore', 'trichy', 'salem', 'vellore',
                   'thanjavur', 'pondicherry', 'rameshwaram', 'kanyakumari', 'ooty',
                   'kodaikanal', 'mahabalipuram', 'pollachi', 'valparai', 'yercaud',
                   'coonoor', 'kotagiri', 'courtallam', 'yelagiri'},
    'karnataka': {'bangalore', 'mysore', 'coorg', 'hampi', 'chikmagalur', 'mangalore'},
    'kerala': {'munnar', 'wayanad', 'thekkady', 'kochi', 'thiruvananthapuram', 'alleppey', 'kerala'},
    'andhra_pradesh': {'tirupati', 'vizag', 'hyderabad', 'vijayawada', 'araku', 'horsley_hills', 'srisailam'},
    'telangana': {'hyderabad', 'warangal'},
    'goa': {'goa'},
}


def _normalize_city(name):
    """Normalize a city name for lookup."""
    return (name or '').strip().lower().replace(' ', '_').replace('-', '_')


def _get_state(city):
    """Determine state from city name."""
    norm = _normalize_city(city)
    for state, cities in STATE_BORDERS.items():
        if norm in cities:
            return state
    return 'unknown'


def _lookup_distance(origin, destination):
    """Lookup distance from route database (bidirectional)."""
    o, d = _normalize_city(origin), _normalize_city(destination)
    return ROUTE_DATABASE.get((o, d)) or ROUTE_DATABASE.get((d, o))


CITY_COORDINATES = {
    'chennai': (13.0827, 80.2707),
    'coimbatore': (11.0168, 76.9558),
    'bangalore': (12.9716, 77.5946),
    'madurai': (9.9252, 78.1198),
    'ooty': (11.4102, 76.6950),
    'salem': (11.6643, 78.1460),
    'trichy': (10.7905, 78.7047),
    'pondicherry': (11.9416, 79.8083),
    'kodaikanal': (10.2381, 77.4892),
    'munnar': (10.0889, 77.0595),
    'mysore': (12.2958, 76.6394),
    'hyderabad': (17.3850, 78.4867),
    'tirupati': (13.6288, 79.4192),
    'rameshwaram': (9.2876, 79.3129),
    'kanyakumari': (8.0883, 77.5385),
    'vellore': (12.9165, 79.1325),
    'thanjavur': (10.7870, 79.1378),
    'pollachi': (10.6609, 77.0048),
    'coorg': (12.3375, 75.8069),
    'wayanad': (11.6854, 76.1320),
    'goa': (15.2993, 74.1240),
    'kochi': (9.9312, 76.2673),
}


def compute_route_distance(origin, destination, custom_km=None):
    """
    Compute route distance between two cities.
    Priority:
    1. Custom KM override
    2. OSRM Road Routing Machine (exact highway meters)
    3. Route Database table
    4. Curvature algorithmic fallback
    """
    if custom_km and int(custom_km) > 0:
        return {
            'distance_km': int(custom_km),
            'duration_minutes': max(15, round((int(custom_km) / 50.0) * 60)),
            'is_estimated': False,
            'route_found': True,
            'source': 'user_input',
        }

    norm_orig = _normalize_city(origin)
    norm_dest = _normalize_city(destination)

    # 1. Try OSRM Road Routing Engine
    if norm_orig in CITY_COORDINATES and norm_dest in CITY_COORDINATES:
        try:
            from operations.routing_service import OSRMRoutingService
            c1 = CITY_COORDINATES[norm_orig]
            c2 = CITY_COORDINATES[norm_dest]
            osrm_res = OSRMRoutingService.get_route(c1[0], c1[1], c2[0], c2[1])
            if osrm_res and osrm_res.get('status') in ['success', 'estimated']:
                return {
                    'distance_km': round(osrm_res['distance_km']),
                    'duration_minutes': osrm_res.get('duration_minutes', 60),
                    'is_estimated': (osrm_res.get('engine_used') == 'algorithmic_curvature_engine'),
                    'route_found': True,
                    'source': f"osrm_{osrm_res.get('engine_used', 'engine')}",
                    'geometry': osrm_res.get('geometry', [])
                }
        except Exception:
            pass

    # 2. Database lookup
    known = _lookup_distance(origin, destination)
    if known:
        return {
            'distance_km': known,
            'duration_minutes': max(20, round((known / 50.0) * 60)),
            'is_estimated': False,
            'route_found': True,
            'source': 'route_database',
        }

    # 3. Fallback estimate
    seed = abs(hash(f"{norm_orig}_{norm_dest}")) % 1000
    estimated_km = 200 + seed
    km_final = min(estimated_km, 1200)
    return {
        'distance_km': km_final,
        'duration_minutes': round((km_final / 45.0) * 60),
        'is_estimated': True,
        'route_found': False,
        'source': 'estimated',
    }


def compute_single_vehicle_quote(
    origin,
    destination,
    vehicle_type_id=None,
    trip_type='one_way',
    duration_days=1,
    custom_km=None,
    pax_count=1,
    gst_rate=Decimal('5.00'),
    include_driver_bata=True,
    include_toll_parking=True,
    include_interstate_permit=None,
    include_hill_surcharge=None,
):
    """
    Compute a fully-loaded quotation for a single vehicle.
    Returns a dict with complete cost breakdown.
    """
    # 1. Route Distance
    route = compute_route_distance(origin, destination, custom_km)
    distance_km = route['distance_km']

    # Round trip doubles the distance
    if trip_type == 'round_trip':
        total_km = distance_km * 2
    elif trip_type == 'multi_day':
        # Multi-day: minimum 250 km/day guarantee
        min_km_per_day = 250
        total_km = max(distance_km * 2, min_km_per_day * duration_days)
    else:
        total_km = distance_km

    # 2. Vehicle Rate
    vehicle_type = None
    rate_per_km = Decimal('14.00')  # Default
    if vehicle_type_id:
        try:
            vehicle_type = VehicleType.objects.get(pk=vehicle_type_id)
            rate_per_km = vehicle_type.rate_per_km or Decimal('14.00')
        except VehicleType.DoesNotExist:
            pass

    vtype_name = vehicle_type.name if vehicle_type else 'Standard Vehicle'

    # 3. Base Fare
    base_fare = (Decimal(str(total_km)) * rate_per_km).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

    # 4. Driver Bata (Daily Allowance)
    driver_bata_per_day = Decimal('400.00')
    driver_bata = Decimal('0.00')
    if include_driver_bata:
        actual_days = max(duration_days, math.ceil(total_km / 350))  # ~350 km/day realistic
        driver_bata = (driver_bata_per_day * actual_days).quantize(Decimal('1'))

    # 5. Toll & Parking Estimate
    toll_parking = Decimal('0.00')
    if include_toll_parking:
        toll_per_100km = Decimal('150.00')
        parking_flat = Decimal('200.00')
        toll_parking = ((Decimal(str(total_km)) / 100) * toll_per_100km + parking_flat).quantize(Decimal('1'))

    # 6. Hill Station Surcharge
    dest_norm = _normalize_city(destination)
    origin_norm = _normalize_city(origin)
    is_hill = (dest_norm in HILL_STATIONS or origin_norm in HILL_STATIONS)
    if include_hill_surcharge is not None:
        is_hill = include_hill_surcharge

    hill_surcharge = Decimal('0.00')
    if is_hill:
        hill_surcharge = (base_fare * Decimal('0.15')).quantize(Decimal('1'))  # 15% surcharge

    # 7. Interstate Permit
    origin_state = _get_state(origin)
    dest_state = _get_state(destination)
    is_interstate = (origin_state != dest_state and origin_state != 'unknown' and dest_state != 'unknown')
    if include_interstate_permit is not None:
        is_interstate = include_interstate_permit

    permit_charge = Decimal('0.00')
    if is_interstate:
        permit_charge = Decimal('2500.00')  # Standard interstate permit

    # 8. Sub-total
    sub_total = base_fare + driver_bata + toll_parking + hill_surcharge + permit_charge

    # 9. GST
    gst_amount = (sub_total * (gst_rate / 100)).quantize(Decimal('0.01'))
    grand_total = (sub_total + gst_amount).quantize(Decimal('0.01'))

    # 10. Per-passenger cost
    per_pax = (grand_total / max(pax_count, 1)).quantize(Decimal('0.01'))

    return {
        'origin': origin,
        'destination': destination,
        'trip_type': trip_type,
        'trip_type_label': {'one_way': 'One Way', 'round_trip': 'Round Trip', 'multi_day': 'Multi-Day Package'}.get(trip_type, trip_type),
        'duration_days': duration_days,
        'route': route,
        'distance_km': distance_km,
        'total_km': total_km,
        'vehicle_type': vtype_name,
        'vehicle_type_id': vehicle_type_id,
        'rate_per_km': rate_per_km,
        'base_fare': base_fare,
        'driver_bata': driver_bata,
        'toll_parking': toll_parking,
        'is_hill_station': is_hill,
        'hill_surcharge': hill_surcharge,
        'is_interstate': is_interstate,
        'permit_charge': permit_charge,
        'sub_total': sub_total,
        'gst_rate': gst_rate,
        'gst_amount': gst_amount,
        'grand_total': grand_total,
        'pax_count': pax_count,
        'per_pax_cost': per_pax,
    }


def compute_convoy_quotation(
    origin,
    destination,
    vehicles,
    trip_type='round_trip',
    duration_days=1,
    custom_km=None,
    gst_rate=Decimal('5.00'),
):
    """
    Multi-vehicle convoy quotation generator.
    `vehicles` is a list of dicts: [{'vehicle_type_id': 1, 'count': 2, 'pax': 30}, ...]
    Returns combined quotation with individual vehicle breakdowns.
    """
    convoy_quotes = []
    fleet_total = Decimal('0.00')
    fleet_pax = 0

    for v in vehicles:
        vt_id = v.get('vehicle_type_id')
        count = int(v.get('count', 1))
        pax = int(v.get('pax', 0))

        single_quote = compute_single_vehicle_quote(
            origin=origin,
            destination=destination,
            vehicle_type_id=vt_id,
            trip_type=trip_type,
            duration_days=duration_days,
            custom_km=custom_km,
            pax_count=pax or 1,
            gst_rate=gst_rate,
        )

        unit_total = single_quote['grand_total']
        fleet_subtotal = unit_total * count

        convoy_quotes.append({
            **single_quote,
            'unit_count': count,
            'fleet_subtotal': fleet_subtotal,
        })

        fleet_total += fleet_subtotal
        fleet_pax += (pax or 0) * count

    per_pax_convoy = (fleet_total / max(fleet_pax, 1)).quantize(Decimal('0.01'))

    return {
        'origin': origin,
        'destination': destination,
        'trip_type': trip_type,
        'duration_days': duration_days,
        'vehicle_breakdown': convoy_quotes,
        'fleet_total_vehicles': sum(v.get('count', 1) for v in vehicles),
        'fleet_total_pax': fleet_pax,
        'fleet_grand_total': fleet_total,
        'fleet_per_pax_cost': per_pax_convoy,
        'generated_at': timezone.now().isoformat(),
    }
