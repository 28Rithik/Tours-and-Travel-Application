"""
operations/echallan_sentry.py
Parivahan RTO Traffic E-Challan Sentry & Fine Recovery Engine
Sivagayathiri Tours & Travels ERP

Monitors national & state highway traffic police e-challans (speed cameras,
wrong parking, red lights, overloading, document checks), routes financial liability
between driver deduction, customer invoice billing, or company trip overhead,
and tracks real-time payment reconciliation.
"""

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from core.models import Vehicle, Driver
from operations.models import Trip, TrafficFine


def get_echallan_dashboard_metrics():
    """
    Returns summary statistics for highway & city traffic e-challans.
    """
    fines = TrafficFine.objects.select_related('vehicle', 'driver', 'trip').all()
    total_fines = fines.count()
    unpaid_fines = fines.filter(paid_by='unpaid')
    unpaid_count = unpaid_fines.count()
    unpaid_total_amt = sum(f.fine_amount for f in unpaid_fines)

    paid_fines = fines.exclude(paid_by='unpaid')
    paid_count = paid_fines.count()
    paid_total_amt = sum(f.fine_amount for f in paid_fines)

    driver_liability_amt = sum(f.fine_amount for f in fines.filter(financial_responsibility='driver', paid_by='unpaid'))
    company_liability_amt = sum(f.fine_amount for f in fines.filter(financial_responsibility='company', paid_by='unpaid'))
    customer_liability_amt = sum(f.fine_amount for f in fines.filter(financial_responsibility='customer', paid_by='unpaid'))

    return {
        'total_fines': total_fines,
        'unpaid_count': unpaid_count,
        'unpaid_total_amt': unpaid_total_amt,
        'paid_count': paid_count,
        'paid_total_amt': paid_total_amt,
        'driver_liability_amt': driver_liability_amt,
        'company_liability_amt': company_liability_amt,
        'customer_liability_amt': customer_liability_amt,
    }


def update_echallan_liability(fine_id, responsibility, notes=""):
    """
    Sets financial liability to 'driver', 'customer', 'supplier', or 'company'.
    """
    fine = TrafficFine.objects.get(pk=fine_id)
    fine.financial_responsibility = responsibility
    if notes:
        fine.notes = f"{fine.notes}\n[Liability updated]: {notes}".strip()
    fine.save()
    return fine


def mark_echallan_paid(fine_id, paid_by='company', transaction_ref=""):
    """
    Records payment of a traffic challan via Parivahan portal or spot cash.
    """
    fine = TrafficFine.objects.get(pk=fine_id)
    fine.paid_by = paid_by
    if transaction_ref:
        fine.notes = f"{fine.notes}\n[Payment Ref: {transaction_ref}]".strip()
    fine.save()
    return fine


def seed_sample_echallans():
    """
    Seeds realistic highway speed camera and traffic police challans from South Indian corridors.
    """
    if TrafficFine.objects.exists():
        return

    now = timezone.now()
    vehicles = list(Vehicle.objects.all()[:5])
    drivers = list(Driver.objects.filter(status='active')[:5])
    trips = list(Trip.objects.all()[:5])

    if not vehicles or not drivers:
        return

    samples = [
        {
            'challan_num': 'TN-ECH-2026-90412',
            'violation': 'speeding',
            'amount': Decimal('1000.00'),
            'paid_by': 'unpaid',
            'resp': 'driver',
            'days_ago': 2,
            'notes': 'NH-44 Salem - Karur Expressway: 98 km/h in 80 km/h radar zone. Driver responsible.',
        },
        {
            'challan_num': 'KL-ECH-2026-11842',
            'violation': 'parking',
            'amount': Decimal('500.00'),
            'paid_by': 'unpaid',
            'resp': 'driver',
            'days_ago': 4,
            'notes': 'Munnar Town Center: Commercial vehicle parked in no-parking zone near post office.',
        },
        {
            'challan_num': 'TN-ECH-2026-88102',
            'violation': 'documents',
            'amount': Decimal('2000.00'),
            'paid_by': 'company',
            'resp': 'company',
            'days_ago': 7,
            'notes': 'Attibele Border Checkpost: Pollution certificate was undergoing renewal. Company paid & absorbed.',
        },
        {
            'challan_num': 'TN-ECH-2026-44910',
            'violation': 'seatbelt_passenger',
            'amount': Decimal('1000.00'),
            'paid_by': 'unpaid',
            'resp': 'customer',
            'days_ago': 1,
            'notes': 'Coimbatore Airport Bypass: Rear passenger refused to buckle seatbelt during RTO drive. Billed to customer invoice.',
        },
        {
            'challan_num': 'KA-ECH-2026-77319',
            'violation': 'rash_driving',
            'amount': Decimal('1500.00'),
            'paid_by': 'unpaid',
            'resp': 'driver',
            'days_ago': 5,
            'notes': 'Bangalore Electronic City Flyover: Sudden lane switching without indicator. Marked for driver settlement deduction.',
        },
    ]

    for i, s in enumerate(samples):
        v = vehicles[i % len(vehicles)]
        d = drivers[i % len(drivers)]
        t = trips[i % len(trips)] if trips else None

        TrafficFine.objects.create(
            challan_number=s['challan_num'],
            vehicle=v,
            driver=d,
            trip=t,
            date_of_offence=now - timedelta(days=s['days_ago']),
            violation_type=s['violation'],
            fine_amount=s['amount'],
            paid_by=s['paid_by'],
            financial_responsibility=s['resp'],
            notes=s['notes'],
        )
