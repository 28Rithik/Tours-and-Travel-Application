"""
operations/cash_advance_settlement.py
Trip Cash Advance & Kharcha Settlement Envelope Engine
Sivagayathiri Tours & Travels ERP

Manages on-road physical cash disbursed at garage out-gate to commercial chauffeurs,
tracks verified fuel/toll/permit/parking/bata expenses, computes net surplus/deficit,
and enforces zero unclosed cash float rules prior to new trip dispatch.
"""

from decimal import Decimal
import random
from django.utils import timezone
from datetime import timedelta
from core.models import Driver, Vehicle
from operations.models import Trip, TripCashAdvanceEnvelope


def get_cash_envelope_metrics():
    """
    Returns summary statistics for on-road cash advances.
    """
    envelopes = TripCashAdvanceEnvelope.objects.all()
    total_envelopes = envelopes.count()
    active_disbursed = envelopes.filter(status__in=['disbursed', 'on_trip']).count()
    pending_audit = envelopes.filter(status='submitted_for_audit').count()
    settled_count = envelopes.filter(status='reconciled_settled').count()

    total_disbursed_amt = sum(e.total_advance_disbursed for e in envelopes)
    total_expenses_amt = sum(e.total_expenses_verified for e in envelopes)
    total_surplus_refunded = sum(e.net_balance for e in envelopes.filter(status='reconciled_settled', net_balance__gt=0))
    total_deficit_reimbursed = sum(abs(e.net_balance) for e in envelopes.filter(status='reconciled_settled', net_balance__lt=0))

    return {
        'total_envelopes': total_envelopes,
        'active_disbursed': active_disbursed,
        'pending_audit': pending_audit,
        'settled_count': settled_count,
        'total_disbursed_amt': total_disbursed_amt,
        'total_expenses_amt': total_expenses_amt,
        'total_surplus_refunded': total_surplus_refunded,
        'total_deficit_reimbursed': total_deficit_reimbursed,
    }


def generate_envelope_code():
    ts = timezone.now().strftime('%Y%m')
    rnd = random.randint(100, 999)
    return f"CAE-{ts}-{rnd}"


def check_driver_pending_advances(driver_id):
    """
    Guard rule: Checks if driver has any unsettled cash envelope from a previous trip.
    Returns (has_pending, pending_envelope).
    """
    pending = TripCashAdvanceEnvelope.objects.filter(
        driver_id=driver_id,
        status__in=['disbursed', 'on_trip', 'submitted_for_audit', 'disputed']
    ).first()
    return (pending is not None, pending)


def issue_cash_advance_envelope(trip, driver, fuel=0, toll=0, permit=0, bata=0, contingency=0, notes=""):
    """
    Disburses a new physical cash envelope for an outstation tour.
    """
    code = generate_envelope_code()
    envelope = TripCashAdvanceEnvelope(
        envelope_code=code,
        trip=trip,
        driver=driver,
        fuel_cash_allocation=Decimal(str(fuel)),
        toll_cash_allocation=Decimal(str(toll)),
        permit_cash_allocation=Decimal(str(permit)),
        driver_bata_allocation=Decimal(str(bata)),
        contingency_cash=Decimal(str(contingency)),
        status='disbursed',
        settlement_notes=notes,
    )
    envelope.recalculate()
    envelope.save()
    return envelope


def log_onroad_expenses_to_envelope(envelope_id, fuel=0, tolls=0, permits=0, parking=0, repairs=0, bata=0, submit_for_audit=False):
    """
    Updates verified expenses submitted by driver/chauffeur upon garage return.
    """
    envelope = TripCashAdvanceEnvelope.objects.get(pk=envelope_id)
    envelope.actual_fuel_spent = Decimal(str(fuel))
    envelope.actual_tolls_spent = Decimal(str(tolls))
    envelope.actual_permits_spent = Decimal(str(permits))
    envelope.actual_parking_spent = Decimal(str(parking))
    envelope.actual_repairs_spent = Decimal(str(repairs))
    envelope.driver_bata_deducted = Decimal(str(bata))
    
    if submit_for_audit:
        envelope.status = 'submitted_for_audit'

    envelope.recalculate()
    envelope.save()
    return envelope


def settle_cash_advance_envelope(envelope_id, notes="", signature_ack=True):
    """
    Finalizes reconciliation. Driver returns surplus or cashier reimburses deficit.
    """
    envelope = TripCashAdvanceEnvelope.objects.get(pk=envelope_id)
    envelope.recalculate()
    envelope.status = 'reconciled_settled'
    envelope.settled_at = timezone.now()
    envelope.driver_signature_acknowledged = signature_ack
    if notes:
        envelope.settlement_notes = f"{envelope.settlement_notes}\n{notes}".strip()
    envelope.save()
    return envelope


def seed_sample_cash_envelopes():
    """
    Seeds realistic commercial tour cash advances across Tamil Nadu and South India circuits.
    """
    if TripCashAdvanceEnvelope.objects.exists():
        return

    now = timezone.now()
    trips = list(Trip.objects.select_related('driver', 'vehicle')[:6])
    drivers = list(Driver.objects.filter(status='active')[:6])

    if not trips or not drivers:
        return

    samples = [
        {
            'fuel': Decimal('7500.00'),
            'toll': Decimal('1400.00'),
            'permit': Decimal('950.00'),
            'bata': Decimal('1800.00'),
            'contingency': Decimal('1500.00'),
            'act_fuel': Decimal('7200.00'),
            'act_toll': Decimal('1400.00'),
            'act_permit': Decimal('950.00'),
            'act_parking': Decimal('350.00'),
            'act_repairs': Decimal('0.00'),
            'act_bata': Decimal('1800.00'),
            'status': 'reconciled_settled',
            'notes': 'Coimbatore to Munnar-Thekkady 3-Day Hill Tour. Driver refunded ₹1,450 surplus cash at Coimbatore depot.',
        },
        {
            'fuel': Decimal('9000.00'),
            'toll': Decimal('1850.00'),
            'permit': Decimal('1600.00'),
            'bata': Decimal('2400.00'),
            'contingency': Decimal('2000.00'),
            'act_fuel': Decimal('9350.00'),
            'act_toll': Decimal('1850.00'),
            'act_permit': Decimal('1600.00'),
            'act_parking': Decimal('500.00'),
            'act_repairs': Decimal('1200.00'),
            'act_bata': Decimal('2400.00'),
            'status': 'reconciled_settled',
            'notes': 'Coimbatore to Bangalore-Mysore-Coorg 4-Day Tour. Emergency puncture & radiator hose repair in Mysore. Cashier reimbursed ₹50 deficit.',
        },
        {
            'fuel': Decimal('5500.00'),
            'toll': Decimal('950.00'),
            'permit': Decimal('0.00'),
            'bata': Decimal('1200.00'),
            'contingency': Decimal('1000.00'),
            'act_fuel': Decimal('5100.00'),
            'act_toll': Decimal('950.00'),
            'act_permit': Decimal('0.00'),
            'act_parking': Decimal('200.00'),
            'act_repairs': Decimal('0.00'),
            'act_bata': Decimal('1200.00'),
            'status': 'submitted_for_audit',
            'notes': 'Madurai to Rameshwaram-Dhanushkodi Temple Circuit (2 Days). Receipts submitted, awaiting accounts cashier signature.',
        },
        {
            'fuel': Decimal('8500.00'),
            'toll': Decimal('1200.00'),
            'permit': Decimal('600.00'),
            'bata': Decimal('1800.00'),
            'contingency': Decimal('1500.00'),
            'act_fuel': Decimal('0.00'),
            'act_toll': Decimal('0.00'),
            'act_permit': Decimal('0.00'),
            'act_parking': Decimal('0.00'),
            'act_repairs': Decimal('0.00'),
            'act_bata': Decimal('0.00'),
            'status': 'on_trip',
            'notes': 'Salem to Kodaikanal 3-Day Family Tour. Vehicle currently on ghat road.',
        },
        {
            'fuel': Decimal('12000.00'),
            'toll': Decimal('2200.00'),
            'permit': Decimal('2400.00'),
            'bata': Decimal('3500.00'),
            'contingency': Decimal('3000.00'),
            'act_fuel': Decimal('0.00'),
            'act_toll': Decimal('0.00'),
            'act_permit': Decimal('0.00'),
            'act_parking': Decimal('0.00'),
            'act_repairs': Decimal('0.00'),
            'act_bata': Decimal('0.00'),
            'status': 'disbursed',
            'notes': 'Tirupur to Goa-Hampi 5-Day College Faculty Tour. Cash handed over at 06:00 AM dispatch.',
        },
    ]

    for i, s in enumerate(samples):
        trip = trips[i % len(trips)]
        driver = trip.driver or drivers[i % len(drivers)]
        env = TripCashAdvanceEnvelope(
            envelope_code=f"CAE-202610-00{i+1}",
            trip=trip,
            driver=driver,
            fuel_cash_allocation=s['fuel'],
            toll_cash_allocation=s['toll'],
            permit_cash_allocation=s['permit'],
            driver_bata_allocation=s['bata'],
            contingency_cash=s['contingency'],
            actual_fuel_spent=s['act_fuel'],
            actual_tolls_spent=s['act_toll'],
            actual_permits_spent=s['act_permit'],
            actual_parking_spent=s['act_parking'],
            actual_repairs_spent=s['act_repairs'],
            driver_bata_deducted=s['act_bata'],
            status=s['status'],
            settlement_notes=s['notes'],
            driver_signature_acknowledged=(s['status'] == 'reconciled_settled'),
            settled_at=now - timedelta(days=i) if s['status'] == 'reconciled_settled' else None
        )
        env.recalculate()
        env.save()
