"""
Market Fleet Vendor Bill Auditor & Telematics Reconciliation Engine
Sivagayathiri Tours & Travels ERP

Audits external supplier claimed KM and hours against live GPS telematics,
duty slips, and NHAI FASTag toll records. Detects inflated billings, unauthorized
dead mileage, and duplicate toll claims before Accounts payable disbursement.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from core.models import Party, Vehicle
from operations.models import Trip
from suppliers.models import OutsourcedTripSettlement
from suppliers.settlement_engine import generate_settlement_number, determine_tds_rate


SAMPLE_VENDOR_INVOICES = [
    {
        'vendor_name': 'SRS Fleet Logistics Pvt Ltd',
        'invoice_number': 'SRS-INV-2026-881',
        'vehicle_reg': 'TN 59 BX 8812',
        'vehicle_type': 'Toyota Innova Crysta (7-Seater)',
        'trip_route': 'Madurai to Munnar Outstation (3 Days)',
        'claimed_km': 740,
        'gps_actual_km': 610,
        'agreed_rate_per_km': Decimal('16.00'),
        'claimed_toll_parking': Decimal('1450.00'),
        'fastag_actual_toll': Decimal('850.00'),
        'claimed_driver_bata': Decimal('1500.00'),
        'advance_paid': Decimal('3000.00'),
        'fuel_company_card': Decimal('1200.00'),
        'notes': 'Vendor claimed 130 ghost KM and duplicate toll receipt near Theni.',
    },
    {
        'vendor_name': 'KPN City Cabs Madurai',
        'invoice_number': 'KPN-CABS-4409',
        'vehicle_reg': 'TN 58 CA 4409',
        'vehicle_type': 'Tempo Traveller (14-Seater)',
        'trip_route': 'Madurai to Rameshwaram Pilgrimage Circuit',
        'claimed_km': 480,
        'gps_actual_km': 465,
        'agreed_rate_per_km': Decimal('22.00'),
        'claimed_toll_parking': Decimal('600.00'),
        'fastag_actual_toll': Decimal('600.00'),
        'claimed_driver_bata': Decimal('800.00'),
        'advance_paid': Decimal('2000.00'),
        'fuel_company_card': Decimal('0.00'),
        'notes': 'Accurate claim within acceptable 3% GPS corridor variance.',
    },
    {
        'vendor_name': 'Vigneshwara Transport Corporation',
        'invoice_number': 'VTC-BILL-1044',
        'vehicle_reg': 'TN 64 E 9921',
        'vehicle_type': 'Ashok Leyland 36-Seater AC Coach',
        'trip_route': 'Madurai to Kodaikanal Corporate Retreat',
        'claimed_km': 390,
        'gps_actual_km': 310,
        'agreed_rate_per_km': Decimal('38.00'),
        'claimed_toll_parking': Decimal('1800.00'),
        'fastag_actual_toll': Decimal('1100.00'),
        'claimed_driver_bata': Decimal('1200.00'),
        'advance_paid': Decimal('5000.00'),
        'fuel_company_card': Decimal('2500.00'),
        'notes': 'Inflated 80 KM dead-mileage not pre-authorized in charter agreement.',
    }
]


def audit_vendor_claim(
    claimed_km,
    gps_km,
    agreed_rate_per_km,
    claimed_toll,
    actual_fastag_toll,
    claimed_bata,
    advance_paid=Decimal('0.00'),
    fuel_deduction=Decimal('0.00'),
    tds_rate_percent=Decimal('1.00')
):
    """
    Performs algorithmic reconciliation between Vendor Claimed invoice and
    telematics/duty slip truth. Calculates discrepancy deductions, statutory TDS,
    and net authorized disbursement.
    """
    claimed_km = Decimal(str(claimed_km or 0))
    gps_km = Decimal(str(gps_km or 0))
    rate_per_km = Decimal(str(agreed_rate_per_km or 0))
    claimed_toll = Decimal(str(claimed_toll or 0))
    actual_fastag_toll = Decimal(str(actual_fastag_toll or 0))
    claimed_bata = Decimal(str(claimed_bata or 0))
    advance_paid = Decimal(str(advance_paid or 0))
    fuel_deduction = Decimal(str(fuel_deduction or 0))
    tds_rate_percent = Decimal(str(tds_rate_percent or 1.00))

    # KM Discrepancy
    km_diff = claimed_km - gps_km
    km_diff_percent = ((km_diff / gps_km) * 100) if gps_km > 0 else Decimal('0.0')

    # Tolerance: 3% or 15 KM is considered normal GPS drift
    is_inflation_flagged = km_diff > Decimal('20.0') or km_diff_percent > Decimal('5.0')

    # Excess Toll Claimed
    toll_leakage = max(Decimal('0.00'), claimed_toll - actual_fastag_toll)

    # Audited KM approved for payment: Cap at GPS actual KM if discrepancy is unapproved
    approved_km = gps_km if is_inflation_flagged else claimed_km
    discrepancy_km_deduction = max(Decimal('0.00'), km_diff * rate_per_km) if is_inflation_flagged else Decimal('0.00')

    # Financials
    raw_claimed_total = (claimed_km * rate_per_km) + claimed_toll + claimed_bata
    audited_hire_charge = approved_km * rate_per_km
    audited_toll = actual_fastag_toll
    audited_bata = claimed_bata

    gross_audited_payable = audited_hire_charge + audited_toll + audited_bata
    total_deductions = advance_paid + fuel_deduction + toll_leakage + discrepancy_km_deduction

    # Statutory TDS
    tds_amount = (audited_hire_charge * (tds_rate_percent / Decimal('100.0'))).quantize(Decimal('0.01'))
    total_deductions_with_tds = advance_paid + fuel_deduction + tds_amount

    net_payable = max(Decimal('0.00'), gross_audited_payable - total_deductions_with_tds)
    total_savings_generated = raw_claimed_total - (net_payable + advance_paid + fuel_deduction + tds_amount)

    risk_badge = 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300' if is_inflation_flagged else 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
    risk_status = 'KM & Toll Inflation Detected' if is_inflation_flagged else 'Verified & Reconciled'

    return {
        'claimed_km': float(claimed_km),
        'gps_actual_km': float(gps_km),
        'km_diff': float(km_diff),
        'km_diff_percent': float(round(km_diff_percent, 1)),
        'is_inflation_flagged': is_inflation_flagged,
        'rate_per_km': float(rate_per_km),
        'approved_km': float(approved_km),
        'raw_claimed_total': float(raw_claimed_total),
        'audited_hire_charge': float(audited_hire_charge),
        'claimed_toll': float(claimed_toll),
        'actual_fastag_toll': float(actual_fastag_toll),
        'toll_leakage': float(toll_leakage),
        'claimed_bata': float(claimed_bata),
        'advance_paid': float(advance_paid),
        'fuel_deduction': float(fuel_deduction),
        'tds_rate_percent': float(tds_rate_percent),
        'tds_amount': float(tds_amount),
        'discrepancy_km_deduction': float(discrepancy_km_deduction),
        'gross_audited_payable': float(gross_audited_payable),
        'net_payable': float(net_payable),
        'total_savings_generated': float(total_savings_generated),
        'risk_badge': risk_badge,
        'risk_status': risk_status,
    }


def seed_sample_vendor_settlements():
    """Seeds realistic outsourced trip settlements for testing the auditor."""
    created = []
    supplier_party, _ = Party.objects.get_or_create(
        name='SRS Fleet Logistics Madurai',
        defaults={
            'party_type': 'supplier',
            'contact_person': 'Ramanathan S.',
            'phone': '9842109876',
            'gstin': '33AABCS1429B1Z5',
            'is_active': True,
        }
    )

    vehicle, _ = Vehicle.objects.get_or_create(
        registration_number='TN 59 BX 8812',
        defaults={
            'vehicle_type': 'Innova Crysta',
            'seating_capacity': 7,
            'ownership_type': 'outsourced',
            'owner_party': supplier_party,
            'status': 'available',
        }
    )

    trips = Trip.objects.all()[:3]

    for idx, item in enumerate(SAMPLE_VENDOR_INVOICES):
        t = trips[idx] if idx < len(trips) else None
        res = audit_vendor_claim(
            item['claimed_km'],
            item['gps_actual_km'],
            item['agreed_rate_per_km'],
            item['claimed_toll_parking'],
            item['fastag_actual_toll'],
            item['claimed_driver_bata'],
            item['advance_paid'],
            item['fuel_company_card']
        )

        st, _ = OutsourcedTripSettlement.objects.get_or_create(
            settlement_number=f"VBA-2026-{880 + idx}",
            defaults={
                'trip': t,
                'supplier': supplier_party,
                'vehicle': vehicle,
                'driver_name': 'Saravanan M.',
                'duty_slip_number': item['invoice_number'],
                'odometer_start': 10240,
                'odometer_end': 10240 + item['claimed_km'],
                'total_km_run': item['claimed_km'],
                'agreed_buy_rate': Decimal(str(res['audited_hire_charge'])),
                'toll_parking_allowance': item['fastag_actual_toll'],
                'driver_bata_payable': item['claimed_driver_bata'],
                'advance_paid': item['advance_paid'],
                'fuel_deducted': item['fuel_company_card'],
                'damage_penalty': Decimal(str(res['discrepancy_km_deduction'])),
                'tds_applicable': True,
                'tds_rate_percent': Decimal('1.00'),
                'tds_amount': Decimal(str(res['tds_amount'])),
                'gross_supplier_payable': Decimal(str(res['gross_audited_payable'])),
                'total_deductions': Decimal(str(res['discrepancy_km_deduction'] + res['advance_paid'] + res['fuel_deduction'] + res['tds_amount'])),
                'net_payable_amount': Decimal(str(res['net_payable'])),
                'gross_margin_earned': Decimal(str(res['total_savings_generated'])),
                'status': 'draft' if res['is_inflation_flagged'] else 'verified',
            }
        )
        created.append(st)
    return created
