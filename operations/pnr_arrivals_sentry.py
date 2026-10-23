"""
operations/pnr_arrivals_sentry.py
Flight & Train PNR Group Arrival Manifest Sentry
Handles multi-pax arrivals at Coimbatore Airport (CJB), Chennai (MAA),
Bangalore (BLR), and railway junctions with automated placard generation.
"""
from datetime import timedelta
from django.utils import timezone
from .models import GroupArrivalManifest, Trip
from core.models import Vehicle, Driver


def get_pnr_dashboard_metrics():
    """
    Computes summary statistics for scheduled group arrivals.
    """
    manifests = GroupArrivalManifest.objects.all()
    today_arrivals = manifests.count()
    delayed_arrivals = manifests.filter(delay_minutes__gt=0).count()
    total_pax = sum(m.total_pax for m in manifests)
    placard_ready = manifests.filter(status__in=['placard_displayed', 'landed_arrived']).count()

    return {
        'total_arrivals': today_arrivals,
        'delayed_count': delayed_arrivals,
        'total_pax_incoming': total_pax,
        'placard_ready': placard_ready,
    }


def seed_sample_pnr_arrivals():
    """
    Seeds incoming tourist & corporate VIP arrivals at South Indian terminals.
    """
    if GroupArrivalManifest.objects.exists():
        return

    now = timezone.now()
    v_crysta = Vehicle.objects.filter(ownership_type='owned').first() or Vehicle.objects.first()
    v_tempo = Vehicle.objects.filter(seating_capacity__gte=12).first() or Vehicle.objects.last() or v_crysta
    d_driver = Driver.objects.filter(status='active').first() or Driver.objects.first()
    d_driver2 = Driver.objects.filter(status='active').last() or Driver.objects.last()
    trip = Trip.objects.first()

    manifests = [
        {
            'manifest_code': 'ARR-20261023-01',
            'transit_type': 'flight',
            'pnr_or_flight_number': '6E-458',
            'carrier_name': 'IndiGo Airlines',
            'arrival_terminal': "Coimbatore Int'l Airport (CJB) - Terminal 1 Arrival Gate",
            'origin_city': 'Mumbai (BOM)',
            'scheduled_arrival': now + timedelta(hours=1, minutes=15),
            'actual_arrival': None,
            'delay_minutes': 0,
            'guest_leader_name': 'Dr. Rajesh Narayanan & Family',
            'guest_phone': '+91 98401 22334',
            'total_pax': 4,
            'luggage_count': 5,
            'trip': trip,
            'assigned_vehicle': v_crysta,
            'assigned_driver': d_driver,
            'placard_title': 'WELCOME DR. RAJESH NARAYANAN & FAMILY - SIVAGAYATHIRI TRAVELS',
            'status': 'placard_displayed',
            'hotel_destination': 'Savoy - IHCL SeleQtions, Ooty (via Kotagiri)',
        },
        {
            'manifest_code': 'ARR-20261023-02',
            'transit_type': 'flight',
            'pnr_or_flight_number': 'AI-657',
            'carrier_name': 'Air India',
            'arrival_terminal': "Coimbatore Int'l Airport (CJB) - VIP Arrival Gate",
            'origin_city': 'New Delhi (DEL)',
            'scheduled_arrival': now + timedelta(hours=3, minutes=30),
            'actual_arrival': None,
            'delay_minutes': 25,
            'guest_leader_name': 'L&T Construction Senior Delegation (Mr. Amitava Roy)',
            'guest_phone': '+91 99001 88772',
            'total_pax': 11,
            'luggage_count': 14,
            'trip': None,
            'assigned_vehicle': v_tempo,
            'assigned_driver': d_driver2,
            'placard_title': 'L&T PROJECT REVIEW DELEGATION - SIVAGAYATHIRI ENTERPRISE',
            'status': 'delayed',
            'hotel_destination': 'Radisson Blu Hotel, Avinashi Road, Coimbatore',
        },
        {
            'manifest_code': 'ARR-20261023-03',
            'transit_type': 'train',
            'pnr_or_flight_number': '20643 Vande Bharat',
            'carrier_name': 'Southern Railway',
            'arrival_terminal': 'Coimbatore Junction (CBE) - Platform 1 VIP Exit',
            'origin_city': 'Chennai Central (MAS)',
            'scheduled_arrival': now - timedelta(minutes=45),
            'actual_arrival': now - timedelta(minutes=40),
            'delay_minutes': 0,
            'guest_leader_name': 'Mr. K. Anandha Kumar (TCS Bangalore)',
            'guest_phone': '+91 97910 55432',
            'total_pax': 3,
            'luggage_count': 3,
            'trip': None,
            'assigned_vehicle': v_crysta,
            'assigned_driver': d_driver,
            'placard_title': 'WELCOME MR. ANANDHA KUMAR & GUESTS - SIVAGAYATHIRI TRAVELS',
            'status': 'boarded_en_route',
            'hotel_destination': 'Sterling Ooty Fern Hill Resort',
        }
    ]

    for m in manifests:
        GroupArrivalManifest.objects.create(**m)
