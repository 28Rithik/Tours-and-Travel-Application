import re
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from core.models import Party, Vehicle
from operations.models import Trip
from finance.models import SupplierTripCost, LedgerAdjustment
from .models import OutsourcedTripSettlement


PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')


def generate_settlement_number():
    """Generates unique sequential settlement number like ST-2026-00001."""
    year = timezone.now().year
    prefix = f"ST-{year}-"
    last = OutsourcedTripSettlement.objects.filter(
        settlement_number__startswith=prefix
    ).order_by('-id').first()

    if last and last.settlement_number:
        try:
            last_seq = int(last.settlement_number.split('-')[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:05d}"


def determine_tds_rate(pan_number: str, party: Party = None, force_section: str = None):
    """
    Determines statutory TDS section and rate under Indian Income Tax Act:
    - If 194C(6) declaration provided (transporter with <= 10 vehicles): 0%
    - Sec 194C Individual / HUF (4th PAN char 'P'): 1.00%
    - Sec 194C Company / Firm / LLP (4th PAN char 'C', 'F', 'L', 'T', 'A'): 2.00%
    - Sec 206AA (Invalid / Missing PAN): 20.00%
    """
    if force_section == 'EXEMPT_DECLARATION':
        return 'EXEMPT_DECLARATION', Decimal('0.00')

    pan = (pan_number or '').strip().upper()
    if not pan and party and party.gstin and len(party.gstin) >= 12:
        # Chars 3 to 12 of Indian GSTIN represent entity PAN
        pan = party.gstin[2:12].upper()

    if not pan or not PAN_REGEX.match(pan):
        return '206AA_NO_PAN', Decimal('20.00')

    fourth_char = pan[3]
    if fourth_char == 'P':
        return '194C_INDIVIDUAL', Decimal('1.00')
    elif fourth_char in ('C', 'F', 'L', 'T', 'A'):
        return '194C_COMPANY', Decimal('2.00')
    else:
        return '194C_INDIVIDUAL', Decimal('1.00')


@transaction.atomic
def calculate_and_create_settlement(
    supplier: Party,
    vehicle: Vehicle,
    agreed_buy_rate: Decimal,
    trip: Trip = None,
    contract_trip=None,
    toll_parking_allowance: Decimal = Decimal('0.00'),
    driver_bata_payable: Decimal = Decimal('0.00'),
    advance_paid: Decimal = Decimal('0.00'),
    fuel_deducted: Decimal = Decimal('0.00'),
    damage_penalty: Decimal = Decimal('0.00'),
    pan_number: str = '',
    tds_applicable: bool = True,
    custom_tds_section: str = None,
    driver_name: str = '',
    driver_phone: str = '',
    odometer_start: int = None,
    odometer_end: int = None,
    duty_slip_number: str = '',
    notes: str = ''
):
    """
    Creates or updates an outsourced trip settlement ledger entry with full mathematical precision.
    """
    if supplier.party_type != 'supplier':
        raise ValidationError(f"Party '{supplier.name}' is not configured as a Supplier.")

    # Auto-resolve PAN
    pan = (pan_number or '').strip().upper()
    if not pan and supplier.gstin and len(supplier.gstin) >= 12:
        pan = supplier.gstin[2:12].upper()

    # Determine TDS section & rate
    if tds_applicable:
        section, rate = determine_tds_rate(pan, party=supplier, force_section=custom_tds_section)
    else:
        section, rate = 'EXEMPT_DECLARATION', Decimal('0.00')

    # Resolve customer revenue / sell rate
    customer_sell = Decimal('0.00')
    if trip:
        customer_sell = Decimal(str(trip.total_amount or (trip.booking.quoted_price if trip.booking else 0) or 0))

    # Total KM run
    total_km = 0
    if odometer_start is not None and odometer_end is not None:
        total_km = max(0, odometer_end - odometer_start)

    # Driver details fallback
    d_name = driver_name or getattr(vehicle, 'supplier_driver_name', '') or (trip.driver.name if trip and trip.driver else '')
    d_phone = driver_phone or getattr(vehicle, 'supplier_driver_phone', '') or (trip.driver.phone if trip and trip.driver else '')

    settlement = OutsourcedTripSettlement(
        settlement_number=generate_settlement_number(),
        trip=trip,
        contract_trip=contract_trip,
        supplier=supplier,
        vehicle=vehicle,
        settlement_date=timezone.now().date(),
        driver_name=d_name,
        driver_phone=d_phone,
        odometer_start=odometer_start,
        odometer_end=odometer_end,
        total_km_run=total_km,
        duty_slip_number=duty_slip_number,
        customer_sell_rate=customer_sell,
        agreed_buy_rate=Decimal(str(agreed_buy_rate or 0)),
        toll_parking_allowance=Decimal(str(toll_parking_allowance or 0)),
        driver_bata_payable=Decimal(str(driver_bata_payable or 0)),
        advance_paid=Decimal(str(advance_paid or 0)),
        fuel_deducted=Decimal(str(fuel_deducted or 0)),
        damage_penalty=Decimal(str(damage_penalty or 0)),
        tds_applicable=tds_applicable,
        tds_section=section,
        pan_number=pan,
        tds_rate_percent=rate,
        notes=notes,
        status='draft'
    )

    settlement.recalculate_totals()
    settlement.save()
    return settlement


@transaction.atomic
def approve_and_post_settlement_ledger(settlement: OutsourcedTripSettlement, approved_by_user=None):
    """
    Approves the settlement and posts to finance:
    1. Synchronizes / creates finance.SupplierTripCost
    2. Adjusts supplier ledger
    3. Updates settlement status to 'approved'
    """
    if settlement.status in ('approved', 'paid'):
        return settlement

    settlement.recalculate_totals()
    settlement.status = 'approved'
    settlement.approved_by = approved_by_user

    # Synchronize SupplierTripCost in finance module
    if settlement.trip_id:
        SupplierTripCost.objects.update_or_create(
            trip=settlement.trip,
            supplier=settlement.supplier,
            vehicle=settlement.vehicle,
            defaults={
                'date': settlement.settlement_date,
                'amount': settlement.agreed_buy_rate,
                'description': f"Approved Outsourced Settlement {settlement.settlement_number} (Net: ₹{settlement.net_payable_amount})"
            }
        )

    # Post LedgerAdjustment for any toll/bata reimbursements or deductions if applicable
    net_diff = settlement.net_payable_amount - settlement.agreed_buy_rate
    if net_diff != Decimal('0.00'):
        LedgerAdjustment.objects.create(
            party=settlement.supplier,
            date=settlement.settlement_date,
            amount=net_diff,
            description=f"Outsourced Settlement {settlement.settlement_number} TDS/Toll/Fuel Net Adjustment"
        )

    settlement.save()
    return settlement
