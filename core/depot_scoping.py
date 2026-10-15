"""
Enterprise Multi-Hub Fleet Isolation & Regional Depot Data Scoping Module.
Enforces data fencing and regional operational boundaries across:
- Chennai Central HQ
- Coimbatore Hub
- Madurai Depo
- Bengaluru Station
- Central Control Room

Governance Rules:
1. Super Admin (is_superuser=True) & Executive HQ Staff (branch='Chennai Central HQ' or role in ['admin', 'finance_controller']):
   - Full global visibility across all regional hubs and vehicle assets.
   - May selectively focus into any specific regional depot using ?depot=<name>.
2. Regional General Managers (role='manager'):
   - Defaults to their assigned hub (e.g. Coimbatore Hub).
   - Holds multi-hub clearance to toggle ?depot=all or view other regional stations for fleet balancing.
3. Regional Operational Staff (role in ['operations', 'driver', 'workshop_manager', 'sales', ...]):
   - Strict data fencing: only vehicles, trips, and bookings originating from or homed at their assigned branch.
   - Unauthorized attempts to view other hubs are clamped to their assigned branch.
"""

from typing import Optional, Dict, Any, List
from django.db.models import Q, QuerySet

DEPOT_COIMBATORE = 'Coimbatore Central HQ'
DEPOT_TIRUPUR = 'Tirupur Branch'
DEPOT_ERODE = 'Erode Branch'
DEPOT_CHENNAI = 'Chennai Branch'
DEPOT_HOSUR = 'Hosur Branch'
DEPOT_TRICHY = 'Trichy Branch'
DEPOT_CONTROL_ROOM = 'Central Control Room'

# Legacy aliases for database and test compatibility
LEGACY_DEPOT_CHENNAI = 'Chennai Central HQ'
LEGACY_DEPOT_COIMBATORE = 'Coimbatore Hub'
LEGACY_DEPOT_MADURAI = 'Madurai Depo'
LEGACY_DEPOT_BENGALURU = 'Bengaluru Station'
DEPOT_MADURAI = LEGACY_DEPOT_MADURAI
DEPOT_BENGALURU = LEGACY_DEPOT_BENGALURU

DEPOT_CHOICES = [
    (DEPOT_COIMBATORE, 'Coimbatore Central HQ (Main Location)'),
    (DEPOT_TIRUPUR, 'Tirupur Branch (Industrial / Knitwear Hub)'),
    (DEPOT_ERODE, 'Erode Branch (Textile & Outstation Hub)'),
    (DEPOT_CHENNAI, 'Chennai Branch (Metro & Airport Concierge)'),
    (DEPOT_HOSUR, 'Hosur Branch (Industrial Corridor & Border Hub)'),
    (DEPOT_TRICHY, 'Trichy Branch (Central Transit & Temple Hub)'),
    (DEPOT_CONTROL_ROOM, 'Central Control Room (24/7 SOS Hub)'),
    # Legacy choices
    (LEGACY_DEPOT_CHENNAI, 'Chennai Central HQ (Legacy)'),
    (LEGACY_DEPOT_COIMBATORE, 'Coimbatore Hub (Legacy)'),
    (LEGACY_DEPOT_MADURAI, 'Madurai Depo (Legacy)'),
    (LEGACY_DEPOT_BENGALURU, 'Bengaluru Station (Legacy)'),
]

ALL_DEPOTS = [
    DEPOT_COIMBATORE,
    DEPOT_TIRUPUR,
    DEPOT_ERODE,
    DEPOT_CHENNAI,
    DEPOT_HOSUR,
    DEPOT_TRICHY,
    DEPOT_CONTROL_ROOM,
]

DEPOT_KEYWORDS = {
    DEPOT_COIMBATORE: [
        'coimbatore', 'cbe', 'ooty', 'nilgiris', 'pollachi', 'avinashi',
        'mettupalayam', 'palakkad', 'valparai', 'sulur', 'saravanampatti', 'peelamedu'
    ],
    DEPOT_TIRUPUR: [
        'tiruppur', 'tirupur', 'palladam', 'kangeyam', 'dharapuram', 'udumalaipettai', 'avinasipalayam'
    ],
    DEPOT_ERODE: [
        'erode', 'bhavani', 'perundurai', 'gobichettipalayam', 'anthiyur', 'sathyamangalam', 'bannari'
    ],
    DEPOT_CHENNAI: [
        'chennai', 'tambaram', 'guindy', 'omr', 'ecr', 'central', 'egmore',
        'chengalpattu', 'kanchipuram', 'mahabalipuram', 'tirupati', 'pondicherry', 'puducherry'
    ],
    DEPOT_HOSUR: [
        'hosur', 'krishnagiri', 'sipcot', 'electronic city', 'bangalore', 'bengaluru', 'denkanikottai'
    ],
    DEPOT_TRICHY: [
        'trichy', 'tiruchirappalli', 'srirangam', 'samayapuram', 'thanjavur', 'kumbakonam', 'pudukkottai'
    ],
}

DEPOT_RTO_PREFIXES = {
    DEPOT_COIMBATORE: [
        'TN37', 'TN38', 'TN40', 'TN41', 'TN43', 'TN66', 'TN99'
    ],
    DEPOT_TIRUPUR: [
        'TN39', 'TN42', 'TN78'
    ],
    DEPOT_ERODE: [
        'TN33', 'TN34', 'TN36', 'TN86'
    ],
    DEPOT_CHENNAI: [
        'TN01', 'TN02', 'TN03', 'TN04', 'TN05', 'TN06', 'TN07', 'TN08',
        'TN09', 'TN10', 'TN11', 'TN12', 'TN13', 'TN14', 'TN18', 'TN19',
        'TN20', 'TN21', 'TN22', 'TN85'
    ],
    DEPOT_HOSUR: [
        'TN70', 'TN24', 'KA01', 'KA02', 'KA03', 'KA04', 'KA05', 'KA51', 'KA53'
    ],
    DEPOT_TRICHY: [
        'TN45', 'TN48', 'TN81'
    ],
}


def normalize_depot_name(depot_str: Optional[str]) -> Optional[str]:
    """Resolves short strings or slug-like names to standardized Depot Names."""
    if not depot_str:
        return None
    cleaned = depot_str.strip().lower()
    if cleaned in ['all', 'global', '*']:
        return 'all'
    if 'tirupur' in cleaned or 'tiruppur' in cleaned:
        return DEPOT_TIRUPUR
    if 'erode' in cleaned:
        return DEPOT_ERODE
    if 'hosur' in cleaned:
        return DEPOT_HOSUR
    if 'trichy' in cleaned or 'tiruchirappalli' in cleaned:
        return DEPOT_TRICHY
    if 'chennai' in cleaned:
        return DEPOT_CHENNAI
    if 'coimbatore' in cleaned or 'cbe' in cleaned:
        return DEPOT_COIMBATORE
    if 'madurai' in cleaned:
        return LEGACY_DEPOT_MADURAI
    if 'bengaluru' in cleaned or 'bangalore' in cleaned:
        return LEGACY_DEPOT_BENGALURU
    if 'control' in cleaned:
        return DEPOT_CONTROL_ROOM
    for code, label in DEPOT_CHOICES:
        if cleaned == code.lower() or cleaned == label.lower():
            return code
    return None


def map_city_to_depot(location_name: Optional[str]) -> str:
    """Classifies a pickup or destination city into its operational hub."""
    if not location_name:
        return DEPOT_COIMBATORE
    loc = location_name.lower()
    for depot, keywords in DEPOT_KEYWORDS.items():
        if any(k in loc for k in keywords):
            return depot
    return DEPOT_COIMBATORE


def map_reg_to_depot(reg_no: Optional[str]) -> str:
    """Classifies a vehicle registration number by RTO state/district prefix."""
    if not reg_no:
        return DEPOT_CHENNAI
    cleaned = reg_no.upper().replace(' ', '').replace('-', '')
    for depot, prefixes in DEPOT_RTO_PREFIXES.items():
        if any(cleaned.startswith(p) for p in prefixes):
            return depot
    return DEPOT_CHENNAI


def get_user_depot_scope(user, requested_depot: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates the user's role and departmental credentials to compute their
    effective depot scope.

    Returns:
        {
            'effective_depot': str or None (None indicates Global / All Depots),
            'is_global': bool,
            'can_change_depot': bool,
            'user_branch': str,
            'user_role': str,
            'requested_depot': str or None,
            'depot_choices': list of (code, label),
            'display_label': str,
        }
    """
    normalized_req = normalize_depot_name(requested_depot)

    # 1. Anonymous or unauthenticated fallback
    if not user or not user.is_authenticated:
        return {
            'effective_depot': None,
            'is_global': True,
            'can_change_depot': False,
            'user_branch': DEPOT_CHENNAI,
            'user_role': 'anonymous',
            'requested_depot': requested_depot,
            'depot_choices': DEPOT_CHOICES,
            'display_label': 'Global Fleet',
        }

    # 2. Super Admin or un-profiled Staff User (dev/superuser pass-through)
    if user.is_superuser or not hasattr(user, 'staff_profile'):
        effective = None if (normalized_req in [None, 'all']) else normalized_req
        return {
            'effective_depot': effective,
            'is_global': True,
            'can_change_depot': True,
            'user_branch': DEPOT_CHENNAI,
            'user_role': 'admin' if user.is_superuser else 'staff',
            'requested_depot': requested_depot,
            'depot_choices': DEPOT_CHOICES,
            'display_label': effective if effective else 'Global Fleet (All Hubs)',
        }

    profile = user.staff_profile
    user_branch = profile.branch or DEPOT_CHENNAI
    user_role = profile.role

    # 3. HQ Management Clearance:
    # Users at Chennai Central HQ or Central Control Room or role admin/finance_controller
    has_hq_clearance = (
        user_branch in [DEPOT_CHENNAI, DEPOT_CONTROL_ROOM, 'All Depots'] or
        user_role in ['admin', 'finance_controller']
    )

    if has_hq_clearance:
        effective = None if (normalized_req in [None, 'all']) else normalized_req
        return {
            'effective_depot': effective,
            'is_global': True,
            'can_change_depot': True,
            'user_branch': user_branch,
            'user_role': user_role,
            'requested_depot': requested_depot,
            'depot_choices': DEPOT_CHOICES,
            'display_label': effective if effective else 'Global Fleet (All Hubs)',
        }

    # 4. Regional General Manager Clearance:
    # Defaults to their home regional hub, but permitted to view all or switch
    if user_role == 'manager':
        if normalized_req == 'all':
            effective = None
        elif normalized_req in ALL_DEPOTS:
            effective = normalized_req
        else:
            effective = user_branch  # default to regional station

        return {
            'effective_depot': effective,
            'is_global': effective is None,
            'can_change_depot': True,
            'user_branch': user_branch,
            'user_role': user_role,
            'requested_depot': requested_depot,
            'depot_choices': DEPOT_CHOICES,
            'display_label': effective if effective else 'Global Fleet (All Hubs)',
        }

    # 5. Strict Regional Operational Staff (Operations, Drivers, Workshop, Sales):
    # Fenced strictly to their home branch. Query params cannot escape regional perimeter.
    effective = user_branch
    return {
        'effective_depot': effective,
        'is_global': False,
        'can_change_depot': False,
        'user_branch': user_branch,
        'user_role': user_role,
        'requested_depot': requested_depot,
        'depot_choices': [(user_branch, user_branch)],
        'display_label': f"{effective} (Regional Fenced)",
    }


def get_scoped_vehicles(user, requested_depot: Optional[str] = None, base_qs: Optional[QuerySet] = None) -> QuerySet:
    """
    Returns the Vehicle queryset scoped by the user's operational depot clearance.
    """
    from core.models import Vehicle

    if base_qs is None:
        base_qs = Vehicle.objects.all()

    scope = get_user_depot_scope(user, requested_depot)
    effective_depot = scope['effective_depot']

    if not effective_depot:
        return base_qs

    return base_qs.filter(base_depot=effective_depot)


def get_scoped_drivers(user, requested_depot: Optional[str] = None, base_qs: Optional[QuerySet] = None) -> QuerySet:
    """
    Returns the Driver queryset scoped by the user's operational depot clearance.
    """
    from core.models import Driver

    if base_qs is None:
        base_qs = Driver.objects.all()

    scope = get_user_depot_scope(user, requested_depot)
    effective_depot = scope['effective_depot']

    if not effective_depot:
        return base_qs

    return base_qs.filter(
        Q(base_depot=effective_depot) |
        Q(staff_accounts__branch=effective_depot) |
        Q(default_vehicles__base_depot=effective_depot)
    ).distinct()


def get_scoped_trips(user, requested_depot: Optional[str] = None, base_qs: Optional[QuerySet] = None) -> QuerySet:
    """
    Returns the Trip queryset scoped by depot. Matches on:
    - Vehicle assigned to trip having that base_depot
    - Driver assigned to trip having that base_depot
    - Or booking pickup location matching regional city keywords for that depot
    """
    from operations.models import Trip

    if base_qs is None:
        base_qs = Trip.objects.all()

    scope = get_user_depot_scope(user, requested_depot)
    effective_depot = scope['effective_depot']

    if not effective_depot:
        return base_qs

    keywords = DEPOT_KEYWORDS.get(effective_depot, [])
    location_q = Q()
    for kw in keywords:
        location_q |= Q(booking__pickup_location__icontains=kw)

    return base_qs.filter(
        Q(vehicle__base_depot=effective_depot) |
        Q(driver__base_depot=effective_depot) |
        location_q
    ).distinct()


def get_scoped_bookings(user, requested_depot: Optional[str] = None, base_qs: Optional[QuerySet] = None) -> QuerySet:
    """
    Returns the Booking queryset scoped by depot. Matches on:
    - Pickup location containing depot city keywords
    - Or any associated trip with vehicle homed at that depot
    """
    from operations.models import Booking

    if base_qs is None:
        base_qs = Booking.objects.all()

    scope = get_user_depot_scope(user, requested_depot)
    effective_depot = scope['effective_depot']

    if not effective_depot:
        return base_qs

    keywords = DEPOT_KEYWORDS.get(effective_depot, [])
    location_q = Q()
    for kw in keywords:
        location_q |= Q(pickup_location__icontains=kw)

    return base_qs.filter(
        location_q |
        Q(trips__vehicle__base_depot=effective_depot)
    ).distinct()
