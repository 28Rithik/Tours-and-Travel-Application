"""
Statutory Interstate Border Road Tax & All India Tourist Permit (AITP) Sentry
Sivagayathiri Tours & Travels ERP

Computes interstate state entry taxes, cross-references AITP compliance,
verifies check-post clearances (Walayar, Attibele, Gorimedu, etc.), and prevents
unauthorized border crossings across South Indian commercial corridors.
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone
from core.models import Vehicle
from operations.models import Trip, InterstateBorderPermit


# Statutory South Indian Border Tax Tariffs (per vehicle seating bracket & destination state)
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
        'tariffs': {
            'sedan': {'label': '4-5 Seater (Sedan/Hatch)', 'amount': Decimal('650.00'), 'validity_days': 7},
            'suv': {'label': '6-7 Seater (Innova / Crysta)', 'amount': Decimal('750.00'), 'validity_days': 7},
            'tempo': {'label': '12-17 Seater (Tempo Traveller)', 'amount': Decimal('950.00'), 'validity_days': 7},
            'minibus': {'label': '21-33 Seater (Mini Coach)', 'amount': Decimal('1400.00'), 'validity_days': 7},
            'coach': {'label': '40-54 Seater (Luxury Coach)', 'amount': Decimal('2200.00'), 'validity_days': 7},
        }
    },
    'Karnataka': {
        'default_checkpost': 'Attibele / Zuzuvadi Check-post (NH-44 Hosur)',
        'all_checkposts': [
            'Attibele / Zuzuvadi Check-post (NH-44 Hosur)',
            'Bandipur / Kakkanallah Check-post (Ooty - Mysore)',
            'Punajanur Check-post (Sathyamangalam - Chamarajanagar)',
        ],
        'tariffs': {
            'sedan': {'label': '4-5 Seater (Sedan/Hatch)', 'amount': Decimal('950.00'), 'validity_days': 7},
            'suv': {'label': '6-7 Seater (Innova / Crysta)', 'amount': Decimal('1100.00'), 'validity_days': 7},
            'tempo': {'label': '12-17 Seater (Tempo Traveller)', 'amount': Decimal('1600.00'), 'validity_days': 7},
            'minibus': {'label': '21-33 Seater (Mini Coach)', 'amount': Decimal('2400.00'), 'validity_days': 7},
            'coach': {'label': '40-54 Seater (Luxury Coach)', 'amount': Decimal('3800.00'), 'validity_days': 7},
        }
    },
    'Puducherry': {
        'default_checkpost': 'Gorimedu Check-post (Tindivanam - Pondy)',
        'all_checkposts': [
            'Gorimedu Check-post (Tindivanam - Pondy)',
            'Madagadipet Check-post (Villupuram - Pondy)',
            'Mullodai Check-post (Cuddalore - Pondy)',
        ],
        'tariffs': {
            'sedan': {'label': '4-5 Seater (Sedan/Hatch)', 'amount': Decimal('400.00'), 'validity_days': 7},
            'suv': {'label': '6-7 Seater (Innova / Crysta)', 'amount': Decimal('450.00'), 'validity_days': 7},
            'tempo': {'label': '12-17 Seater (Tempo Traveller)', 'amount': Decimal('600.00'), 'validity_days': 7},
            'minibus': {'label': '21-33 Seater (Mini Coach)', 'amount': Decimal('850.00'), 'validity_days': 7},
            'coach': {'label': '40-54 Seater (Luxury Coach)', 'amount': Decimal('1200.00'), 'validity_days': 7},
        }
    },
    'Andhra Pradesh': {
        'default_checkpost': 'Naraharipet Check-post (Chittoor - Vellore)',
        'all_checkposts': [
            'Naraharipet Check-post (Chittoor - Vellore)',
            'Gummidipoondi Check-post (NH-16 Tada)',
        ],
        'tariffs': {
            'sedan': {'label': '4-5 Seater (Sedan/Hatch)', 'amount': Decimal('750.00'), 'validity_days': 7},
            'suv': {'label': '6-7 Seater (Innova / Crysta)', 'amount': Decimal('900.00'), 'validity_days': 7},
            'tempo': {'label': '12-17 Seater (Tempo Traveller)', 'amount': Decimal('1350.00'), 'validity_days': 7},
            'minibus': {'label': '21-33 Seater (Mini Coach)', 'amount': Decimal('1900.00'), 'validity_days': 7},
            'coach': {'label': '40-54 Seater (Luxury Coach)', 'amount': Decimal('2800.00'), 'validity_days': 7},
        }
    },
    'Goa': {
        'default_checkpost': 'Mollem Check-post (Belgaum - Goa)',
        'all_checkposts': [
            'Mollem Check-post (Belgaum - Goa)',
            'Patradevi Check-post (Maharashtra - Goa)',
        ],
        'tariffs': {
            'sedan': {'label': '4-5 Seater (Sedan/Hatch)', 'amount': Decimal('1000.00'), 'validity_days': 7},
            'suv': {'label': '6-7 Seater (Innova / Crysta)', 'amount': Decimal('1200.00'), 'validity_days': 7},
            'tempo': {'label': '12-17 Seater (Tempo Traveller)', 'amount': Decimal('2000.00'), 'validity_days': 7},
            'minibus': {'label': '21-33 Seater (Mini Coach)', 'amount': Decimal('2800.00'), 'validity_days': 7},
            'coach': {'label': '40-54 Seater (Luxury Coach)', 'amount': Decimal('4200.00'), 'validity_days': 7},
        }
    }
}


def detect_target_state(destination_text):
    """Detects whether an outstation itinerary enters an interstate territory."""
    if not destination_text:
        return None
    d = destination_text.lower()

    if any(k in d for k in ['munnar', 'kochi', 'cochin', 'alleppey', 'alappuzha', 'wayanad', 'trivandrum', 'thiruvananthapuram', 'thekkady', 'kovalam', 'kerala']):
        return 'Kerala'
    if any(k in d for k in ['bangalore', 'bengaluru', 'mysore', 'mysuru', 'coorg', 'madikeri', 'chikmagalur', 'hampi', 'karnataka']):
        return 'Karnataka'
    if any(k in d for k in ['pondicherry', 'puducherry', 'auroville']):
        return 'Puducherry'
    if any(k in d for k in ['tirupati', 'chittoor', 'nellore', 'vijayawada', 'andhra']):
        return 'Andhra Pradesh'
    if any(k in d for k in ['goa', 'panaji', 'calangute']):
        return 'Goa'

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
    taxes, and returns permit clearance status.
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
            'checkpost': 'N/A (Intrastate)',
            'permit_record': None,
        }

    state_config = STATUTORY_BORDER_TAX_MATRIX[target_state]
    v_bracket = categorize_vehicle_for_permit(trip.vehicle)
    tariff_info = state_config['tariffs'].get(v_bracket, state_config['tariffs']['suv'])
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

    if existing_permit:
        if existing_permit.status == 'valid':
            # Check if expiring soon
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
        status_label = 'Border Tax Unpaid (Check-post Payment Required)'
        badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'

    return {
        'is_interstate': True,
        'target_state': target_state,
        'status': status,
        'status_label': status_label,
        'badge': badge,
        'required_tax': required_amount,
        'checkpost': existing_permit.checkpost_name if existing_permit and existing_permit.checkpost_name else default_checkpost,
        'permit_record': existing_permit,
        'bracket_label': tariff_info['label'],
        'validity_days': tariff_info['validity_days'],
    }


def issue_sample_interstate_permits():
    """Seeds realistic border permits for demonstration."""
    trips = Trip.objects.select_related('vehicle', 'booking').filter(vehicle__isnull=False)[:5]
    created = []
    sample_data = [
        ('Kerala', 'Walayar Check-post (NH-544 Palakkad)', Decimal('750.00'), 'KL-TAX-2026-9812'),
        ('Karnataka', 'Attibele / Zuzuvadi Check-post (NH-44 Hosur)', Decimal('1100.00'), 'KA-RTO-2026-4401'),
        ('Puducherry', 'Gorimedu Check-post (Tindivanam - Pondy)', Decimal('450.00'), 'PY-PERMIT-2026-102'),
    ]

    for idx, t in enumerate(trips):
        if idx >= len(sample_data):
            break
        state, checkpost, amt, rcpt = sample_data[idx]
        p, _ = InterstateBorderPermit.objects.get_or_create(
            vehicle=t.vehicle,
            target_state=state,
            defaults={
                'trip': t,
                'origin_state': 'Tamil Nadu',
                'permit_type': 'single_entry',
                'checkpost_name': checkpost,
                'tax_amount': amt,
                'receipt_number': rcpt,
                'valid_from': timezone.now() - timedelta(days=1),
                'valid_until': timezone.now() + timedelta(days=6),
                'status': 'valid',
                'notes': f'Commercial entry pass paid at {checkpost}',
            }
        )
        created.append(p)
    return created
