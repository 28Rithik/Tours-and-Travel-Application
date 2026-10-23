"""
operations/breakdown_sos_sentry.py
Highway Breakdown & Emergency SOS Replacement Dispatch Sentry
Handles real-time highway breakdown tracking, passenger safety alerts,
nearest mechanic dispatch, and 1-click replacement vehicle relief missions.
"""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from .models import HighwayBreakdownSOS, Trip
from core.models import Vehicle, Driver


def get_sos_dashboard_metrics():
    """
    Returns live statistics on highway breakdown incidents.
    """
    active_incidents = HighwayBreakdownSOS.objects.exclude(status__in=['resolved', 'towed_depot'])
    critical_count = active_incidents.filter(severity='critical').count()
    passengers_stranded = sum(i.passengers_stranded for i in active_incidents)
    resolved_count = HighwayBreakdownSOS.objects.filter(status='resolved').count()
    total_incidents = HighwayBreakdownSOS.objects.count()

    return {
        'active_sos': active_incidents.count(),
        'critical_sos': critical_count,
        'passengers_stranded': passengers_stranded,
        'resolved_count': resolved_count,
        'total_incidents': total_incidents,
    }


def seed_sample_breakdown_incidents():
    """
    Seeds representative highway breakdown scenarios on key South Indian corridors.
    """
    if HighwayBreakdownSOS.objects.exists():
        return

    now = timezone.now()
    v_crysta = Vehicle.objects.filter(ownership_type='owned').first() or Vehicle.objects.first()
    v_tt = Vehicle.objects.filter(seating_capacity__gte=12).first() or Vehicle.objects.last()
    v_relief = Vehicle.objects.filter(status='available').exclude(id=v_crysta.id if v_crysta else 0).first()

    d_primary = Driver.objects.filter(is_active=True).first()
    d_relief = Driver.objects.filter(is_active=True).exclude(id=d_primary.id if d_primary else 0).first()
    trip = Trip.objects.first()

    samples = [
        {
            'incident_id': 'SOS-20261023-01',
            'trip': trip,
            'vehicle': v_crysta,
            'driver': d_primary,
            'issue_type': 'engine_overheat',
            'highway_corridor': 'nh544_salem_cbe',
            'breakdown_location': 'NH-544 (KM 138 near Vijayamangalam Toll Plaza, Perundurai bypass)',
            'passengers_stranded': 5,
            'passenger_contact_name': 'Mr. K. Senthil Nathan',
            'passenger_contact_phone': '+91 98421 99881',
            'status': 'replacement_en_route',
            'severity': 'critical',
            'replacement_vehicle': v_relief,
            'replacement_driver': d_relief,
            'nearest_mechanic_assigned': 'TVS Auto Care Perundurai (Mr. Murugan)',
            'mechanic_phone': '+91 94432 12890',
            'estimated_delay_minutes': 35,
            'customer_notified_sms': True,
            'resolution_notes': 'Radiator hose punctured under high load. Standby Innova dispatched from Erode depot. Guest family served refreshments at A2B highway restaurant.',
        },
        {
            'incident_id': 'SOS-20261023-02',
            'trip': None,
            'vehicle': v_tt,
            'driver': d_relief,
            'issue_type': 'tire_blowout',
            'highway_corridor': 'ooty_ghats',
            'breakdown_location': 'Mettupalayam - Coonoor Ghat Road (9th Hairpin Bend near Marappalam)',
            'passengers_stranded': 14,
            'passenger_contact_name': 'Mrs. Archana Venkatesh (PSG Tech Group)',
            'passenger_contact_phone': '+91 97890 44321',
            'status': 'mechanic_dispatched',
            'severity': 'moderate',
            'replacement_vehicle': None,
            'replacement_driver': None,
            'nearest_mechanic_assigned': 'Coonoor Hill Auto Service (Mr. Xavier)',
            'mechanic_phone': '+91 98422 77610',
            'estimated_delay_minutes': 25,
            'customer_notified_sms': True,
            'resolution_notes': 'Rear left tire puncture on rocky shoulder. Jack deployed on level ground. Mechanic arriving from Burliar checkpost.',
        },
        {
            'incident_id': 'SOS-20261022-03',
            'trip': None,
            'vehicle': v_crysta,
            'driver': d_primary,
            'issue_type': 'electrical_alternator',
            'highway_corridor': 'nh44_bangalore_madurai',
            'breakdown_location': 'NH-44 Krishnagiri Toll Plaza service lane',
            'passengers_stranded': 4,
            'passenger_contact_name': 'Dr. Ramanujam',
            'passenger_contact_phone': '+91 94440 33211',
            'status': 'resolved',
            'severity': 'minor',
            'replacement_vehicle': None,
            'replacement_driver': None,
            'nearest_mechanic_assigned': 'Bosch Service Krishnagiri',
            'mechanic_phone': '+91 98940 55443',
            'estimated_delay_minutes': 15,
            'customer_notified_sms': True,
            'resolved_at': now - timedelta(hours=8),
            'resolution_notes': 'Battery terminal corrosion cleaned, alternator belt retensioned. Vehicle resumed journey safely.',
        }
    ]

    for s in samples:
        if s['vehicle']:
            HighwayBreakdownSOS.objects.create(**s)
