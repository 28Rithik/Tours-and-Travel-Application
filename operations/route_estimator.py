"""
Sivagayathiri Travels & Tours — Corridor Matrix & Highway Route Distance Estimator.
Provides distance, expected driving time, toll plaza counts, toll charges,
and state border entry tax (Kerala, Karnataka, Pondicherry, Andhra Pradesh)
for South Indian commercial fleet circuits.
"""

from decimal import Decimal
import re

# Comprehensive South Indian Commercial Hubs and Intercity Tourism Matrix
# Format: (hub_a, hub_b): { distance_km, hours, tolls_count, toll_amount, permit_required, permit_state, permit_fee }
CORRIDOR_MATRIX = {
    # Coimbatore Outstation Circuits
    ('coimbatore', 'ooty'): {
        'distance_km': 86, 'hours': 3.0, 'tolls_count': 1, 'toll_amount': 65,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'kodaikanal'): {
        'distance_km': 175, 'hours': 4.5, 'tolls_count': 2, 'toll_amount': 150,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'munnar'): {
        'distance_km': 160, 'hours': 4.5, 'tolls_count': 1, 'toll_amount': 80,
        'permit_required': True, 'permit_state': 'Kerala', 'permit_fee': 650
    },
    ('coimbatore', 'chennai'): {
        'distance_km': 510, 'hours': 8.5, 'tolls_count': 8, 'toll_amount': 680,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'bangalore'): {
        'distance_km': 365, 'hours': 6.5, 'tolls_count': 6, 'toll_amount': 450,
        'permit_required': True, 'permit_state': 'Karnataka', 'permit_fee': 950
    },
    ('coimbatore', 'bengaluru'): {
        'distance_km': 365, 'hours': 6.5, 'tolls_count': 6, 'toll_amount': 450,
        'permit_required': True, 'permit_state': 'Karnataka', 'permit_fee': 950
    },
    ('coimbatore', 'madurai'): {
        'distance_km': 215, 'hours': 4.0, 'tolls_count': 3, 'toll_amount': 240,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'mysore'): {
        'distance_km': 200, 'hours': 5.0, 'tolls_count': 2, 'toll_amount': 180,
        'permit_required': True, 'permit_state': 'Karnataka', 'permit_fee': 950
    },
    ('coimbatore', 'mysuru'): {
        'distance_km': 200, 'hours': 5.0, 'tolls_count': 2, 'toll_amount': 180,
        'permit_required': True, 'permit_state': 'Karnataka', 'permit_fee': 950
    },
    ('coimbatore', 'trichy'): {
        'distance_km': 215, 'hours': 4.0, 'tolls_count': 3, 'toll_amount': 220,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'tiruchirappalli'): {
        'distance_km': 215, 'hours': 4.0, 'tolls_count': 3, 'toll_amount': 220,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'salem'): {
        'distance_km': 165, 'hours': 3.0, 'tolls_count': 3, 'toll_amount': 210,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'kochi'): {
        'distance_km': 190, 'hours': 4.5, 'tolls_count': 3, 'toll_amount': 220,
        'permit_required': True, 'permit_state': 'Kerala', 'permit_fee': 650
    },
    ('coimbatore', 'cochin'): {
        'distance_km': 190, 'hours': 4.5, 'tolls_count': 3, 'toll_amount': 220,
        'permit_required': True, 'permit_state': 'Kerala', 'permit_fee': 650
    },
    ('coimbatore', 'palakkad'): {
        'distance_km': 55, 'hours': 1.5, 'tolls_count': 1, 'toll_amount': 70,
        'permit_required': True, 'permit_state': 'Kerala', 'permit_fee': 650
    },
    ('coimbatore', 'tirupur'): {
        'distance_km': 50, 'hours': 1.0, 'tolls_count': 1, 'toll_amount': 55,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'erode'): {
        'distance_km': 100, 'hours': 2.0, 'tolls_count': 2, 'toll_amount': 130,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'kanyakumari'): {
        'distance_km': 450, 'hours': 8.0, 'tolls_count': 7, 'toll_amount': 520,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'rameshwaram'): {
        'distance_km': 380, 'hours': 7.0, 'tolls_count': 5, 'toll_amount': 380,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('coimbatore', 'wayanad'): {
        'distance_km': 220, 'hours': 5.5, 'tolls_count': 2, 'toll_amount': 140,
        'permit_required': True, 'permit_state': 'Kerala', 'permit_fee': 650
    },
    ('coimbatore', 'pondicherry'): {
        'distance_km': 390, 'hours': 7.0, 'tolls_count': 5, 'toll_amount': 420,
        'permit_required': True, 'permit_state': 'Puducherry', 'permit_fee': 400
    },

    # Chennai & Bangalore Hubs
    ('chennai', 'bangalore'): {
        'distance_km': 345, 'hours': 6.0, 'tolls_count': 5, 'toll_amount': 410,
        'permit_required': True, 'permit_state': 'Karnataka', 'permit_fee': 950
    },
    ('chennai', 'pondicherry'): {
        'distance_km': 155, 'hours': 3.0, 'tolls_count': 2, 'toll_amount': 130,
        'permit_required': True, 'permit_state': 'Puducherry', 'permit_fee': 400
    },
    ('chennai', 'madurai'): {
        'distance_km': 460, 'hours': 7.5, 'tolls_count': 7, 'toll_amount': 580,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('chennai', 'trichy'): {
        'distance_km': 330, 'hours': 5.5, 'tolls_count': 5, 'toll_amount': 410,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('chennai', 'salem'): {
        'distance_km': 345, 'hours': 5.5, 'tolls_count': 5, 'toll_amount': 420,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('bangalore', 'mysore'): {
        'distance_km': 145, 'hours': 2.0, 'tolls_count': 2, 'toll_amount': 330,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('bangalore', 'ooty'): {
        'distance_km': 270, 'hours': 6.0, 'tolls_count': 3, 'toll_amount': 240,
        'permit_required': True, 'permit_state': 'Tamil Nadu', 'permit_fee': 800
    },
    ('bangalore', 'coorg'): {
        'distance_km': 260, 'hours': 5.5, 'tolls_count': 3, 'toll_amount': 250,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('madurai', 'rameshwaram'): {
        'distance_km': 170, 'hours': 3.0, 'tolls_count': 2, 'toll_amount': 140,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('madurai', 'kanyakumari'): {
        'distance_km': 245, 'hours': 4.0, 'tolls_count': 4, 'toll_amount': 290,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
    ('madurai', 'kodaikanal'): {
        'distance_km': 120, 'hours': 3.0, 'tolls_count': 1, 'toll_amount': 80,
        'permit_required': False, 'permit_state': None, 'permit_fee': 0
    },
}

# Known Coordinates (Lat, Long) for Geodetic fallback
CITY_COORDINATES = {
    'coimbatore': (11.0168, 76.9558),
    'ooty': (11.4102, 76.6950),
    'kodaikanal': (10.2381, 77.4892),
    'munnar': (10.0889, 77.0595),
    'chennai': (13.0827, 80.2707),
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'madurai': (9.9252, 78.1198),
    'mysore': (12.2958, 76.6394),
    'mysuru': (12.2958, 76.6394),
    'trichy': (10.7905, 78.7047),
    'tiruchirappalli': (10.7905, 78.7047),
    'salem': (11.6643, 78.1460),
    'kochi': (9.9312, 76.2673),
    'palakkad': (10.7867, 76.6548),
    'tirupur': (11.1085, 77.3411),
    'erode': (11.3410, 77.7172),
    'kanyakumari': (8.0883, 77.5385),
    'rameshwaram': (9.2876, 79.3129),
    'pondicherry': (11.9416, 79.8083),
    'wayanad': (11.6854, 76.1320),
}


def _normalize_name(name):
    if not name:
        return ''
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', name.strip().lower())
    # remove common suffixes like "city", "railway station", "airport", "junction"
    cleaned = re.sub(r'\b(city|railway|station|airport|junction|junction|stand|depot|hq)\b', '', cleaned).strip()
    return cleaned


def estimate_route(origin, destination, is_round_trip=False, vehicle_category_code='SEDAN'):
    """
    Computes distance, driving time, tolls, and interstate permit requirements.
    Falls back gracefully to geodetic curvature estimation if not in matrix.
    """
    norm_orig = _normalize_name(origin) or 'coimbatore'
    norm_dest = _normalize_name(destination) or 'ooty'

    data = None
    # Check direct pair or reverse
    for (a, b), info in CORRIDOR_MATRIX.items():
        if (norm_orig in a or a in norm_orig) and (norm_dest in b or b in norm_dest):
            data = info.copy()
            break
        elif (norm_dest in a or a in norm_dest) and (norm_orig in b or b in norm_orig):
            data = info.copy()
            break

    if not data:
        # Fallback approximation: check if origin and destination match known cities
        c1 = None
        c2 = None
        for city, coords in CITY_COORDINATES.items():
            if city in norm_orig or norm_orig in city:
                c1 = coords
            if city in norm_dest or norm_dest in city:
                c2 = coords

        if c1 and c2:
            import math
            # Haversine formula
            lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
            lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a_val = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c_val = 2 * math.atan2(math.sqrt(a_val), math.sqrt(1 - a_val))
            straight_km = 6371 * c_val
            # Indian highway road curvature factor: 1.28
            dist_km = int(round(straight_km * 1.28))
            tolls_cnt = max(1, int(dist_km // 65))
            toll_cost = tolls_cnt * 75
            hours = round(dist_km / 55.0, 1)
            data = {
                'distance_km': dist_km,
                'hours': hours,
                'tolls_count': tolls_cnt,
                'toll_amount': toll_cost,
                'permit_required': False,
                'permit_state': None,
                'permit_fee': 0,
            }
        else:
            # Default fallback for unknown routes
            data = {
                'distance_km': 150,
                'hours': 3.5,
                'tolls_count': 2,
                'toll_amount': 140,
                'permit_required': False,
                'permit_state': None,
                'permit_fee': 0,
            }

    # Adjust for round-trip
    distance = data['distance_km']
    tolls_amt = data['toll_amount']
    tolls_count = data['tolls_count']
    hours = data['hours']

    if is_round_trip:
        distance *= 2
        tolls_amt = int(tolls_amt * 1.8)  # standard fastag return rebate (within 24h)
        tolls_count *= 2
        hours *= 2

    # Adjust toll & permit for vehicle category
    cat_multiplier = 1.0
    v_code = str(vehicle_category_code).upper()
    if 'SUV' in v_code or 'CRYSTA' in v_code:
        cat_multiplier = 1.15
    elif 'TEMPO' in v_code or 'VAN' in v_code:
        cat_multiplier = 1.6
        if data['permit_required']:
            data['permit_fee'] = int(data['permit_fee'] * 1.5)
    elif 'BUS' in v_code or 'COACH' in v_code:
        cat_multiplier = 2.4
        if data['permit_required']:
            data['permit_fee'] = int(data['permit_fee'] * 2.8)

    tolls_amt = int(round(tolls_amt * cat_multiplier))

    return {
        'status': 'success',
        'origin': origin,
        'destination': destination,
        'is_round_trip': is_round_trip,
        'distance_km': distance,
        'duration_hours': hours,
        'tolls_count': tolls_count,
        'estimated_tolls_inr': tolls_amt,
        'permit_required': data['permit_required'],
        'permit_state': data['permit_state'],
        'estimated_permit_fee_inr': data['permit_fee'],
        'benchmark_diesel_liters': round(distance / 12.0, 1),
    }
