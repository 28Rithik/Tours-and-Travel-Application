"""
Statutory Interstate Border Road Tax & All India Tourist Permit (AITP) Sentry
& Eco-Sensitive Hill Station E-Pass Engine (Nilgiris / Kodaikanal / Valparai)
Sivagayathiri Tours & Travels ERP

Computes interstate state entry taxes, cross-references AITP compliance,
verifies check-post clearances (Walayar, Attibele, Gorimedu, etc.), and enforces
Madras High Court / TNeGA Eco-Sensitive Zone E-Passes across Tamil Nadu hill corridors.
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone
from core.models import Vehicle
from operations.models import Trip, InterstateBorderPermit, EcoSensitiveZoneEPass


# Statutory South Indian Border Tax Tariffs (per vehicle seating bracket & destination state)
# For Kerala: TN commercial vehicles pay ONLY Kerala entry permit fee (₹200) under reciprocal agreement (₹0 border road tax).
# For Karnataka & Andhra Pradesh: TN commercial vehicles pay State Permit fee (₹200) + State Motor Vehicle Border Road Tax.
# For Puducherry: State Permit fee (₹100) + Entry Tax.
STATUTORY_BORDER_TAX_MATRIX = {
    'Kerala': {
        'default_checkpost': 'Walayar Check-post (NH-544 Palakkad)',
        'all_checkposts': [
            'Walayar Check-post (NH-544 Palakkad)',
            'Gopalapuram Check-post (Pollachi - Palakkad)',
            'Meenakshipuram Check-post (Pollachi - Chittur)',
            'Aryankavu Check-post (Tenkasi - Kollam)',
            'Kumily Check-post (Theni - Idukki)',
            'Nadukani Check-post (Gudalur - Nilambur)',
        ],
        'state_permit_fee': Decimal('200.00'),
        'rule_summary': 'Reciprocal Agreement: Kerala Permit fee only (₹200 fixed), ₹0 State Border Road Tax for tourist contract carriages.',
        'tariffs': {
            'sedan': {'label': 'Motor Cab (Sedan / Hatch <=5s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('0.00'), 'amount': Decimal('200.00'), 'validity_days': 7},
            'suv': {'label': 'Motor Cab (Innova / Crysta 6-7s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('0.00'), 'amount': Decimal('200.00'), 'validity_days': 7},
            'tempo': {'label': 'Maxi Cab (Tempo Traveller 9-17s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('0.00'), 'amount': Decimal('200.00'), 'validity_days': 7},
            'minibus': {'label': 'Omnibus (Mini Coach 21-33s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('0.00'), 'amount': Decimal('200.00'), 'validity_days': 7},
            'coach': {'label': 'Omnibus (Luxury Coach 40-54s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('0.00'), 'amount': Decimal('200.00'), 'validity_days': 7},
        }
    },
    'Karnataka': {
        'default_checkpost': 'Attibele / Zuzuvadi Check-post (NH-44 Hosur)',
        'all_checkposts': [
            'Attibele / Zuzuvadi Check-post (NH-44 Hosur)',
            'Bandipur / Kakkanallah Check-post (Ooty - Mysore)',
            'Punajanur Check-post (Sathyamangalam - Chamarajanagar)',
        ],
        'state_permit_fee': Decimal('200.00'),
        'rule_summary': 'Karnataka Temporary Permit (₹200) + Karnataka Motor Vehicles Taxation Act Border Road Tax.',
        'tariffs': {
            'sedan': {'label': 'Motor Cab (Sedan / Hatch <=5s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('750.00'), 'amount': Decimal('950.00'), 'validity_days': 7},
            'suv': {'label': 'Motor Cab (Innova / Crysta 6-7s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('900.00'), 'amount': Decimal('1100.00'), 'validity_days': 7},
            'tempo': {'label': 'Maxi Cab (Tempo Traveller 9-17s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('1400.00'), 'amount': Decimal('1600.00'), 'validity_days': 7},
            'minibus': {'label': 'Omnibus (Mini Coach 21-33s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('2200.00'), 'amount': Decimal('2400.00'), 'validity_days': 7},
            'coach': {'label': 'Omnibus (Luxury Coach 40-54s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('3600.00'), 'amount': Decimal('3800.00'), 'validity_days': 7},
        }
    },
    'Andhra Pradesh': {
        'default_checkpost': 'Naraharipet Check-post (Chittoor - Vellore)',
        'all_checkposts': [
            'Naraharipet Check-post (Chittoor - Vellore)',
            'Gummidipoondi Check-post (NH-16 Tada)',
        ],
        'state_permit_fee': Decimal('200.00'),
        'rule_summary': 'Andhra Pradesh State Permit (₹200) + AP Motor Vehicles Taxation Border Road Tax.',
        'tariffs': {
            'sedan': {'label': 'Motor Cab (Sedan / Hatch <=5s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('550.00'), 'amount': Decimal('750.00'), 'validity_days': 7},
            'suv': {'label': 'Motor Cab (Innova / Crysta 6-7s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('700.00'), 'amount': Decimal('900.00'), 'validity_days': 7},
            'tempo': {'label': 'Maxi Cab (Tempo Traveller 9-17s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('1150.00'), 'amount': Decimal('1350.00'), 'validity_days': 7},
            'minibus': {'label': 'Omnibus (Mini Coach 21-33s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('1700.00'), 'amount': Decimal('1900.00'), 'validity_days': 7},
            'coach': {'label': 'Omnibus (Luxury Coach 40-54s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('2600.00'), 'amount': Decimal('2800.00'), 'validity_days': 7},
        }
    },
    'Puducherry': {
        'default_checkpost': 'Gorimedu Check-post (Tindivanam - Pondy)',
        'all_checkposts': [
            'Gorimedu Check-post (Tindivanam - Pondy)',
            'Madagadipet Check-post (Villupuram - Pondy)',
            'Mullodai Check-post (Cuddalore - Pondy)',
        ],
        'state_permit_fee': Decimal('100.00'),
        'rule_summary': 'Puducherry UT Permit (₹100) + Entry Road Tax.',
        'tariffs': {
            'sedan': {'label': 'Motor Cab (Sedan / Hatch <=5s)', 'permit_fee': Decimal('100.00'), 'border_tax': Decimal('300.00'), 'amount': Decimal('400.00'), 'validity_days': 7},
            'suv': {'label': 'Motor Cab (Innova / Crysta 6-7s)', 'permit_fee': Decimal('100.00'), 'border_tax': Decimal('350.00'), 'amount': Decimal('450.00'), 'validity_days': 7},
            'tempo': {'label': 'Maxi Cab (Tempo Traveller 9-17s)', 'permit_fee': Decimal('100.00'), 'border_tax': Decimal('500.00'), 'amount': Decimal('600.00'), 'validity_days': 7},
            'minibus': {'label': 'Omnibus (Mini Coach 21-33s)', 'permit_fee': Decimal('100.00'), 'border_tax': Decimal('750.00'), 'amount': Decimal('850.00'), 'validity_days': 7},
            'coach': {'label': 'Omnibus (Luxury Coach 40-54s)', 'permit_fee': Decimal('100.00'), 'border_tax': Decimal('1100.00'), 'amount': Decimal('1200.00'), 'validity_days': 7},
        }
    },
    'Goa': {
        'default_checkpost': 'Mollem Check-post (Belgaum - Goa)',
        'all_checkposts': [
            'Mollem Check-post (Belgaum - Goa)',
            'Patradevi Check-post (Maharashtra - Goa)',
        ],
        'state_permit_fee': Decimal('200.00'),
        'rule_summary': 'Goa State Entry Permit (₹200) + Goa Motor Vehicles Passenger Border Tax.',
        'tariffs': {
            'sedan': {'label': 'Motor Cab (Sedan / Hatch <=5s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('800.00'), 'amount': Decimal('1000.00'), 'validity_days': 7},
            'suv': {'label': 'Motor Cab (Innova / Crysta 6-7s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('1000.00'), 'amount': Decimal('1200.00'), 'validity_days': 7},
            'tempo': {'label': 'Maxi Cab (Tempo Traveller 9-17s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('1800.00'), 'amount': Decimal('2000.00'), 'validity_days': 7},
            'minibus': {'label': 'Omnibus (Mini Coach 21-33s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('2600.00'), 'amount': Decimal('2800.00'), 'validity_days': 7},
            'coach': {'label': 'Omnibus (Luxury Coach 40-54s)', 'permit_fee': Decimal('200.00'), 'border_tax': Decimal('4000.00'), 'amount': Decimal('4200.00'), 'validity_days': 7},
        }
    }
}


# ==============================================================================
# ECO-SENSITIVE HILL STATION E-PASS ZONES CONFIG (MADRAS HIGH COURT / TNeGA)
# ==============================================================================

ECO_SENSITIVE_ZONES_CONFIG = {
    'nilgiris': {
        'name': 'Nilgiris (Ooty / Coonoor / Kotagiri / Gudalur)',
        'district': 'The Nilgiris',
        'portal_url': 'https://epass.tnega.org',
        'portal_name': 'TNeGA Nilgiris e-Pass Portal',
        'keywords': ['ooty', 'udhagamandalam', 'coonoor', 'kotagiri', 'gudalur', 'pykara', 'wellington', 'nilgiris', 'avalanche'],
        'default_checkpost': 'Burliyar Checkpost (Mettupalayam - Coonoor)',
        'all_checkposts': [
            'Burliyar Checkpost (Mettupalayam - Coonoor)',
            'Katteri Checkpost (Coonoor Ghat)',
            'Kakkanallah Checkpost (Mudumalai / Bandipur Border)',
            'Nadukani Checkpost (Gudalur - Nilambur Border)',
            'Gudalur Checkpost (Gudalur Town)',
            'Ketti Checkpost (Ketti Valley)',
        ],
        'mandate': 'Madras High Court Order (W.P. No. 25777/2023) Vehicular Carrying Capacity Sentry',
        'cost': Decimal('0.00'),
    },
    'kodaikanal': {
        'name': 'Kodaikanal (Dindigul District)',
        'district': 'Dindigul',
        'portal_url': 'https://epass.tnega.org',
        'portal_name': 'TNeGA Kodaikanal e-Pass Portal',
        'keywords': ['kodaikanal', 'kodai', 'vattakanal', 'mannavanur', 'poombarai', 'perumalmalai'],
        'default_checkpost': 'Silver Cascade Checkpost (Ghat Road)',
        'all_checkposts': [
            'Silver Cascade Checkpost (Ghat Road)',
            'Shenbaganur Checkpost',
            'Machur Checkpost (Palani - Kodai Ghat)',
        ],
        'mandate': 'Madras High Court Order — Mandatory TNeGA E-Pass for Kodaikanal Entry',
        'cost': Decimal('0.00'),
    },
    'valparai': {
        'name': 'Valparai (Anamalai Tiger Reserve)',
        'district': 'Coimbatore',
        'portal_url': 'https://forests.tn.gov.in',
        'portal_name': 'TN Forest Department Anamalai Tiger Reserve Sentry',
        'keywords': ['valparai', 'sholayar', 'solaiyar', 'topslip', 'anamalai', 'aliyar', 'attakatti'],
        'default_checkpost': 'Aliyar Checkpost (40 Hairpin Bends Foothills)',
        'all_checkposts': [
            'Aliyar Checkpost (40 Hairpin Bends Foothills)',
            'Attakatti Checkpost (20th Hairpin Bend)',
            'Malakkappara Checkpost (Kerala - TN Forest Border)',
        ],
        'mandate': 'Anamalai Tiger Reserve Eco-Sensitive Forest Entry Pass & Green Sentry',
        'cost': Decimal('50.00'),
    },
    'yercaud': {
        'name': 'Yercaud (Shevaroys Hill Entry)',
        'district': 'Salem',
        'portal_url': 'https://salem.nic.in',
        'portal_name': 'Salem District Administration Ghat Portal',
        'keywords': ['yercaud', 'shevaroys', 'manjakkuttai', 'pagoda point'],
        'default_checkpost': 'Adivaram Toll Gate (Salem - Yercaud Foothills)',
        'all_checkposts': [
            'Adivaram Toll Gate (Salem - Yercaud Foothills)',
            'Kuppanur Checkpost (Alternative Ghat Road)',
        ],
        'mandate': 'Salem District Ghat Vehicle Green Pass',
        'cost': Decimal('30.00'),
    }
}


def detect_target_state(destination_text):
    """Detects whether an outstation itinerary enters an interstate territory."""
    if not destination_text:
        return None
    d = destination_text.lower()

    if any(k in d for k in ['munnar', 'kochi', 'cochin', 'alleppey', 'alappuzha', 'wayanad', 'trivandrum', 'thiruvananthapuram', 'thekkady', 'kovalam', 'kerala', 'calicut', 'kozhikode']):
        return 'Kerala'
    if any(k in d for k in ['bangalore', 'bengaluru', 'mysore', 'mysuru', 'coorg', 'madikeri', 'chikmagalur', 'hampi', 'karnataka', 'mangalore', 'udupi']):
        return 'Karnataka'
    if any(k in d for k in ['pondicherry', 'puducherry', 'auroville']):
        return 'Puducherry'
    if any(k in d for k in ['tirupati', 'chittoor', 'nellore', 'vijayawada', 'andhra', 'visakhapatnam', 'vizag']):
        return 'Andhra Pradesh'
    if any(k in d for k in ['goa', 'panaji', 'calangute', 'baga', 'madgaon']):
        return 'Goa'

    return None


def detect_hill_station_epass_zone(destination_text):
    """Detects whether an itinerary enters an eco-sensitive hill station requiring an e-Pass."""
    if not destination_text:
        return None
    d = destination_text.lower()

    for zone_key, zone_data in ECO_SENSITIVE_ZONES_CONFIG.items():
        if any(kw in d for kw in zone_data['keywords']):
            return zone_key
    return None


def categorize_vehicle_for_permit(vehicle):
    """Categorizes vehicle capacity for statutory state tax."""
    if not vehicle:
        return 'suv'
    seats = vehicle.seating_capacity or 4
    cat_code = str(vehicle.vehicle_category).upper() if vehicle.vehicle_category else ''

    if seats <= 5 or 'SEDAN' in cat_code or 'HATCH' in cat_code:
        return 'sedan'
    elif seats <= 8 or 'SUV' in cat_code or 'CRYSTA' in cat_code:
        return 'suv'
    elif seats <= 18 or 'TEMPO' in cat_code or 'VAN' in cat_code:
        return 'tempo'
    elif seats <= 35:
        return 'minibus'
    else:
        return 'coach'


def audit_trip_border_permit(trip):
    """
    Audits an active Trip to verify if it crosses state borders, calculates statutory
    taxes (State Permit fee + Border Road Tax), honors AITP national exemptions,
    and returns permit clearance status.
    """
    dest = ''
    if trip.booking:
        dest = trip.booking.destination or ''
    elif trip.package:
        dest = trip.package.title or ''

    target_state = detect_target_state(dest)

    if not target_state:
        return {
            'is_interstate': False,
            'target_state': None,
            'status': 'exempt',
            'status_label': 'Intrastate (Tamil Nadu Domestic)',
            'badge': 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
            'required_tax': Decimal('0.00'),
            'state_permit_fee': Decimal('0.00'),
            'border_road_tax': Decimal('0.00'),
            'checkpost': 'N/A (Intrastate)',
            'permit_record': None,
            'is_aitp_exempt': False,
        }

    state_config = STATUTORY_BORDER_TAX_MATRIX[target_state]
    v_bracket = categorize_vehicle_for_permit(trip.vehicle)
    tariff_info = state_config['tariffs'].get(v_bracket, state_config['tariffs']['suv'])
    
    # Check if vehicle has active All India Tourist Permit (AITP)
    vehicle = trip.vehicle
    has_valid_aitp = False
    if vehicle:
        if getattr(vehicle, 'has_aitp', False) and getattr(vehicle, 'aitp_expiry', None):
            today = timezone.localdate()
            if vehicle.aitp_expiry >= today:
                has_valid_aitp = True

    if has_valid_aitp:
        state_permit_fee = Decimal('0.00')
        border_road_tax = Decimal('0.00')
        required_amount = Decimal('0.00')
    else:
        state_permit_fee = tariff_info['permit_fee']
        border_road_tax = tariff_info['border_tax']
        required_amount = tariff_info['amount']

    default_checkpost = state_config['default_checkpost']

    # Search existing permit record for this trip or active permit for this vehicle
    now = timezone.now()
    existing_permit = InterstateBorderPermit.objects.filter(
        vehicle=trip.vehicle,
        target_state=target_state,
        valid_until__gte=now
    ).order_by('-valid_until').first()

    if not existing_permit and trip:
        existing_permit = InterstateBorderPermit.objects.filter(trip=trip).first()

    if has_valid_aitp:
        status = 'valid'
        status_label = f'Cleared (AITP National Authorization #{vehicle.aitp_permit_number or "Active"})'
        badge = 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300'
    elif existing_permit:
        if existing_permit.status == 'valid':
            if existing_permit.valid_until and existing_permit.valid_until <= now + timedelta(hours=24):
                status = 'expiring_soon'
                status_label = 'Border Pass Expiring Soon (<24h)'
                badge = 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
            else:
                status = 'valid'
                status_label = 'Cleared & Compliant'
                badge = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
        else:
            status = existing_permit.status
            status_label = existing_permit.get_status_display()
            badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
    else:
        status = 'pending_payment'
        if target_state == 'Kerala':
            status_label = 'Kerala Permit Fee Due (₹200 at Walayar)'
        else:
            status_label = f'{target_state} Permit (₹200) + Border Tax Due (₹{border_road_tax:,.0f})'
        badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'

    return {
        'is_interstate': True,
        'target_state': target_state,
        'status': status,
        'status_label': status_label,
        'badge': badge,
        'required_tax': required_amount,
        'state_permit_fee': state_permit_fee,
        'border_road_tax': border_road_tax,
        'is_aitp_exempt': has_valid_aitp,
        'checkpost': existing_permit.checkpost_name if existing_permit and existing_permit.checkpost_name else default_checkpost,
        'permit_record': existing_permit,
        'bracket_label': tariff_info['label'],
        'validity_days': tariff_info['validity_days'],
        'rule_summary': state_config['rule_summary'],
    }


def audit_trip_hill_epass(trip):
    """
    Audits an active Trip to verify if it enters an eco-sensitive hill station
    (Nilgiris, Kodaikanal, Valparai) requiring mandatory Madras High Court / TNeGA e-Pass.
    """
    dest = ''
    if trip.booking:
        dest = trip.booking.destination or ''
    elif trip.package:
        dest = trip.package.title or ''

    zone_key = detect_hill_station_epass_zone(dest)
    if not zone_key:
        return {
            'requires_epass': False,
            'zone_key': None,
            'zone_name': 'Plains / Non-Restricted Route',
            'status': 'exempt',
            'status_label': 'Plains Route (No Hill e-Pass Required)',
            'badge': 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
            'epass_record': None,
        }

    zone_info = ECO_SENSITIVE_ZONES_CONFIG[zone_key]
    today = timezone.localdate()

    # Search existing e-Pass for this trip or active e-pass for vehicle & zone
    existing_epass = EcoSensitiveZoneEPass.objects.filter(
        vehicle=trip.vehicle,
        zone=zone_key,
        exit_date__gte=today
    ).order_by('-exit_date').first()

    if not existing_epass and trip:
        existing_epass = EcoSensitiveZoneEPass.objects.filter(trip=trip).first()

    if existing_epass:
        if existing_epass.status == 'active':
            if existing_epass.verified_at_checkpost:
                status = 'checkpost_cleared'
                status_label = f'Verified at {existing_epass.checkpost_name or "Checkpost"}'
                badge = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
            else:
                status = 'active'
                status_label = f'TNeGA e-Pass Approved (#{existing_epass.epass_number})'
                badge = 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
        elif existing_epass.status == 'pending':
            status = 'pending'
            status_label = 'Pending TNeGA Portal Verification'
            badge = 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
        else:
            status = existing_epass.status
            status_label = existing_epass.get_status_display()
            badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
    else:
        status = 'missing'
        status_label = f'Mandatory {zone_info["name"]} e-Pass Required'
        badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'

    return {
        'requires_epass': True,
        'zone_key': zone_key,
        'zone_name': zone_info['name'],
        'portal_url': zone_info['portal_url'],
        'portal_name': zone_info['portal_name'],
        'default_checkpost': zone_info['default_checkpost'],
        'all_checkposts': zone_info['all_checkposts'],
        'mandate': zone_info['mandate'],
        'status': status,
        'status_label': status_label,
        'badge': badge,
        'epass_record': existing_epass,
    }


def issue_sample_interstate_permits():
    """Seeds realistic border permits with the ₹200 fee vs border tax breakdown."""
    trips = Trip.objects.select_related('vehicle', 'booking').filter(vehicle__isnull=False)[:6]
    created = []
    sample_data = [
        # State, Checkpost, Permit Fee, Border Tax, Receipt No
        ('Kerala', 'Walayar Check-post (NH-544 Palakkad)', Decimal('200.00'), Decimal('0.00'), 'KL-PERMIT-2026-9812'),
        ('Karnataka', 'Attibele / Zuzuvadi Check-post (NH-44 Hosur)', Decimal('200.00'), Decimal('900.00'), 'KA-RTO-2026-4401'),
        ('Andhra Pradesh', 'Naraharipet Check-post (Chittoor - Vellore)', Decimal('200.00'), Decimal('700.00'), 'AP-BORDER-2026-3104'),
        ('Puducherry', 'Gorimedu Check-post (Tindivanam - Pondy)', Decimal('100.00'), Decimal('350.00'), 'PY-PERMIT-2026-102'),
    ]

    for idx, t in enumerate(trips):
        if idx >= len(sample_data):
            break
        state, checkpost, p_fee, b_tax, rcpt = sample_data[idx]
        p, _ = InterstateBorderPermit.objects.get_or_create(
            vehicle=t.vehicle,
            target_state=state,
            defaults={
                'trip': t,
                'origin_state': 'Tamil Nadu',
                'permit_type': 'single_entry',
                'checkpost_name': checkpost,
                'state_permit_fee': p_fee,
                'border_road_tax': b_tax,
                'tax_amount': p_fee + b_tax,
                'receipt_number': rcpt,
                'valid_from': timezone.now() - timedelta(days=1),
                'valid_until': timezone.now() + timedelta(days=6),
                'status': 'valid',
                'payment_mode': 'parivahan_online',
                'notes': f'Parivahan entry pass paid at {checkpost}',
            }
        )
        created.append(p)
    return created


def issue_sample_hill_epasses():
    """Seeds realistic TNeGA Eco-Sensitive Zone e-Passes for Nilgiris, Kodaikanal, Valparai."""
    trips = Trip.objects.select_related('vehicle', 'driver').filter(vehicle__isnull=False)[:6]
    created = []
    today = timezone.localdate()

    samples = [
        ('nilgiris', 'TNEGA-NIL-2026-84910', 'Burliyar Checkpost (Mettupalayam - Coonoor)', 'Savoy - IHCL SeleQtions, Ooty', 4),
        ('kodaikanal', 'TNEGA-KOD-2026-31802', 'Silver Cascade Checkpost (Ghat Road)', 'Tamara Luxury Resort, Kodaikanal', 6),
        ('valparai', 'ATR-VAL-2026-19401', 'Aliyar Checkpost (40 Hairpin Bends Foothills)', 'Briar Tea Bungalows, Valparai', 8),
    ]

    for idx, s in enumerate(samples):
        if idx >= len(trips):
            break
        t = trips[idx]
        zone, epass_num, checkpost, hotel, tourists = s
        ep, _ = EcoSensitiveZoneEPass.objects.get_or_create(
            epass_number=epass_num,
            defaults={
                'trip': t,
                'vehicle': t.vehicle,
                'driver': t.driver,
                'zone': zone,
                'entry_date': today,
                'exit_date': today + timedelta(days=3),
                'num_tourists': tourists,
                'hotel_name': hotel,
                'hotel_booking_ref': f'HTL-BK-2026-{idx+101}',
                'purpose': 'tourism',
                'checkpost_name': checkpost,
                'qr_code_token': f'TNEGA-SHA256-{epass_num}',
                'status': 'active',
                'verified_at_checkpost': True if idx == 0 else False,
                'verified_timestamp': timezone.now() if idx == 0 else None,
                'notes': f'TNeGA e-Pass approved under Madras High Court eco-sentry guidelines.',
            }
        )
        created.append(ep)
    return created
