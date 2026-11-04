import datetime
import calendar
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q, Count

from core.models import Driver, Vehicle, Party
from fleet_contracts.models import (
    TransportContract,
    Route,
    Shift,
    ContractTripLog,
    ContractSLAPenalty,
    ContractMonthlyInvoice,
)
from finance.models import (
    CorporateGSTInvoice,
    InvoiceLineItem,
    DriverAllowanceLedger,
    DriverAdvance,
)


class ContractBillingEngine:
    """
    Enterprise Tariff, Billing & Contract Revenue Engine (Domain 6).
    
    Core Responsibilities:
    1. Contract Rate Card Matrix (Monthly Fixed, Per KM, Per Trip, or Tiered Slab).
    2. Dynamic Fuel Price Escalation Factor (Automatic diesel delta variance adjustment).
    3. Monthly Commute Reconciliation & SLA Penalty Deductions.
    4. 1-Click CGST/SGST/IGST Rule 46 Compliant Tax Invoicing with Digital QR Codes.
    5. Driver Commute Duty Bhatta & Night Shift Allowance Settlement Ledger.
    """

    PREVAILING_DIESEL_PRICE = Decimal('96.80') # Prevailing South India diesel benchmark
    DEFAULT_SAC_CODE = '9966' # Passenger road transport services with operator under Indian GST

    @classmethod
    def get_month_date_range(cls, year: int, month: int) -> Tuple[datetime.date, datetime.date]:
        """Returns the first and last dates of the specified month."""
        from_date = datetime.date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        to_date = datetime.date(year, month, last_day)
        return from_date, to_date

    @classmethod
    def reconcile_monthly_contract(
        cls,
        contract_id: int,
        year: int,
        month: int,
        prevailing_diesel_price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Reconciles all logged commute trips for a contract in a billing month.
        Calculates Base Amount, Extra KMs, Fuel Escalation, Tolls, and SLA Penalties.
        """
        contract = TransportContract.objects.select_related('customer').get(id=contract_id)
        from_date, to_date = cls.get_month_date_range(year, month)

        # 1. Gather all trips logged for this contract in the billing period
        trips_qs = ContractTripLog.objects.filter(
            shift__route__contract=contract,
            date__gte=from_date,
            date__lte=to_date
        ).select_related('shift', 'shift__route', 'vehicle', 'driver')

        completed_trips = trips_qs.filter(status__in=['completed', 'scheduled', 'en_route'])
        total_trips_completed = completed_trips.count()

        # 2. Compute Total Kilometers Run
        total_kms_run = Decimal('0.00')
        total_toll_parking = Decimal('0.00')
        total_driver_bata_accrued = Decimal('0.00')

        for trip in completed_trips:
            # Distance: actual odometer if logged, else contracted route distance
            if trip.opening_km and trip.closing_km and trip.closing_km > trip.opening_km:
                dist = Decimal(str(trip.closing_km - trip.opening_km))
            elif trip.shift and trip.shift.route and trip.shift.route.distance_km:
                dist = Decimal(str(trip.shift.route.distance_km))
            else:
                dist = Decimal('20.00') # Minimum route benchmark
            total_kms_run += dist

            if trip.toll_parking_charges:
                total_toll_parking += Decimal(str(trip.toll_parking_charges))
            if trip.driver_bata:
                total_driver_bata_accrued += Decimal(str(trip.driver_bata))
            else:
                total_driver_bata_accrued += Decimal('350.00') # Standard shift bhatta

        # 3. Base Contract Billing Model Calculation
        billing_model = contract.billing_model
        rate = contract.default_rate or Decimal('0.00')
        base_contract_amount = Decimal('0.00')
        extra_km_amount = Decimal('0.00')

        if billing_model in ['fixed_monthly', 'monthly_fixed']:
            base_contract_amount = rate if rate > 0 else Decimal('185000.00')
            # Check for extra km overage if base includes package km
            included_kms = Decimal('3000.00') # Standard monthly included limit
            if total_kms_run > included_kms:
                extra_km_amount = round((total_kms_run - included_kms) * Decimal('22.50'), 2)
        elif billing_model == 'per_km':
            km_rate = rate if rate > 0 else Decimal('24.50')
            base_contract_amount = round(total_kms_run * km_rate, 2)
        elif billing_model == 'per_trip':
            trip_rate = rate if rate > 0 else Decimal('1800.00')
            base_contract_amount = round(Decimal(str(total_trips_completed)) * trip_rate, 2)
        else: # Default hybrid per_trip_km
            km_rate = rate if rate > 0 else Decimal('24.50')
            base_contract_amount = round(total_kms_run * km_rate, 2)

        # 4. Fuel Escalation Calculation
        curr_fuel_price = prevailing_diesel_price or cls.PREVAILING_DIESEL_PRICE
        base_diesel = contract.base_diesel_price or Decimal('92.00')
        fuel_delta = curr_fuel_price - base_diesel
        fuel_factor = contract.fuel_revision_factor or Decimal('0.20') # 5.0 km/L consumption factor

        fuel_escalation_amount = Decimal('0.00')
        if contract.fuel_escalation_enabled or fuel_delta > 0:
            fuel_escalation_amount = max(Decimal('0.00'), round(fuel_delta * fuel_factor * total_kms_run, 2))

        # 5. SLA Deductions (Un-waived penalties for this period)
        penalties_qs = ContractSLAPenalty.objects.filter(
            contract=contract,
            date__gte=from_date,
            date__lte=to_date,
            waived=False
        )
        sla_penalty_deduction = penalties_qs.aggregate(total=Sum('penalty_amount'))['total'] or Decimal('0.00')

        # Apply SLA penalty cap if configured on contract
        if contract.sla_penalty_cap_pct and contract.sla_penalty_cap_pct > 0:
            max_penalty = round(base_contract_amount * (contract.sla_penalty_cap_pct / Decimal('100.0')), 2)
            if sla_penalty_deduction > max_penalty:
                sla_penalty_deduction = max_penalty

        # 6. Net Taxable Amount
        net_taxable_amount = (
            base_contract_amount +
            extra_km_amount +
            fuel_escalation_amount +
            total_toll_parking -
            sla_penalty_deduction
        )
        if net_taxable_amount < Decimal('0.00'):
            net_taxable_amount = Decimal('0.00')

        # 7. GST Calculation (5% standard for passenger transport)
        gst_rate = contract.gst_rate or Decimal('5.00')
        gst_amount = round((net_taxable_amount * gst_rate) / Decimal('100.0'), 2)
        grand_total = net_taxable_amount + gst_amount

        # State Tax Breakdown (Tamil Nadu TN = 33)
        customer_state = getattr(contract.customer, 'state_code', '33') or '33'
        is_intrastate = (customer_state == '33')
        if is_intrastate:
            half_rate = round(gst_rate / Decimal('2.0'), 2)
            cgst_amount = round(gst_amount / Decimal('2.0'), 2)
            sgst_amount = gst_amount - cgst_amount
            igst_amount = Decimal('0.00')
        else:
            half_rate = Decimal('0.00')
            cgst_amount = Decimal('0.00')
            sgst_amount = Decimal('0.00')
            igst_amount = gst_amount

        month_label = from_date.strftime('%B %Y')

        return {
            "contract_id": contract.id,
            "contract_name": contract.name,
            "customer_name": contract.customer.name,
            "billing_model": billing_model,
            "year": year,
            "month": month,
            "month_label": month_label,
            "from_date": from_date.strftime('%Y-%m-%d'),
            "to_date": to_date.strftime('%Y-%m-%d'),
            "total_trips_completed": total_trips_completed,
            "total_kms_run": float(total_kms_run),
            "base_contract_amount": float(base_contract_amount),
            "extra_km_amount": float(extra_km_amount),
            "prevailing_fuel_price": float(curr_fuel_price),
            "base_fuel_price": float(base_diesel),
            "fuel_delta": float(fuel_delta),
            "fuel_escalation_amount": float(fuel_escalation_amount),
            "toll_parking_amount": float(total_toll_parking),
            "sla_penalty_deduction": float(sla_penalty_deduction),
            "penalties_count": penalties_qs.count(),
            "net_taxable_amount": float(net_taxable_amount),
            "gst_rate": float(gst_rate),
            "gst_amount": float(gst_amount),
            "cgst_amount": float(cgst_amount),
            "sgst_amount": float(sgst_amount),
            "igst_amount": float(igst_amount),
            "is_intrastate": is_intrastate,
            "grand_total": float(grand_total),
            "driver_bata_total": float(total_driver_bata_accrued),
        }

    @classmethod
    def generate_monthly_invoice(
        cls,
        contract_id: int,
        year: int,
        month: int,
        force_recreate: bool = False
    ) -> Dict[str, Any]:
        """
        Atomically generates ContractMonthlyInvoice and official CorporateGSTInvoice with QR code.
        """
        contract = TransportContract.objects.select_related('customer').get(id=contract_id)
        from_date, to_date = cls.get_month_date_range(year, month)
        invoice_number = f"INV-ETS-{year}-{str(month).zfill(2)}-{contract.id:03d}"

        # Reconcile calculations
        reconciliation = cls.reconcile_monthly_contract(contract_id, year, month)

        with transaction.atomic():
            # 1. Create or Update ContractMonthlyInvoice
            monthly_inv, created = ContractMonthlyInvoice.objects.get_or_create(
                contract=contract,
                billing_month=from_date,
                defaults={
                    'invoice_number': invoice_number,
                    'from_date': from_date,
                    'to_date': to_date,
                    'total_trips_completed': reconciliation['total_trips_completed'],
                    'total_kms_run': Decimal(str(reconciliation['total_kms_run'])),
                    'base_contract_amount': Decimal(str(reconciliation['base_contract_amount'])),
                    'extra_km_amount': Decimal(str(reconciliation['extra_km_amount'])),
                    'fuel_escalation_amount': Decimal(str(reconciliation['fuel_escalation_amount'])),
                    'toll_parking_amount': Decimal(str(reconciliation['toll_parking_amount'])),
                    'sla_penalty_deduction': Decimal(str(reconciliation['sla_penalty_deduction'])),
                    'net_taxable_amount': Decimal(str(reconciliation['net_taxable_amount'])),
                    'gst_rate': Decimal(str(reconciliation['gst_rate'])),
                    'gst_amount': Decimal(str(reconciliation['gst_amount'])),
                    'grand_total': Decimal(str(reconciliation['grand_total'])),
                    'status': 'generated',
                    'due_date': to_date + datetime.timedelta(days=contract.payment_credit_days or 30),
                    'notes': f"Automated GST billing run for {reconciliation['month_label']}. Total completed shifts: {reconciliation['total_trips_completed']}."
                }
            )

            if not created and force_recreate:
                monthly_inv.total_trips_completed = reconciliation['total_trips_completed']
                monthly_inv.total_kms_run = Decimal(str(reconciliation['total_kms_run']))
                monthly_inv.base_contract_amount = Decimal(str(reconciliation['base_contract_amount']))
                monthly_inv.extra_km_amount = Decimal(str(reconciliation['extra_km_amount']))
                monthly_inv.fuel_escalation_amount = Decimal(str(reconciliation['fuel_escalation_amount']))
                monthly_inv.toll_parking_amount = Decimal(str(reconciliation['toll_parking_amount']))
                monthly_inv.sla_penalty_deduction = Decimal(str(reconciliation['sla_penalty_deduction']))
                monthly_inv.net_taxable_amount = Decimal(str(reconciliation['net_taxable_amount']))
                monthly_inv.gst_amount = Decimal(str(reconciliation['gst_amount']))
                monthly_inv.grand_total = Decimal(str(reconciliation['grand_total']))
                monthly_inv.status = 'generated'
                monthly_inv.save()

            # Mark SLA penalties as applied to this invoice
            ContractSLAPenalty.objects.filter(
                contract=contract,
                date__gte=from_date,
                date__lte=to_date,
                waived=False
            ).update(applied_to_invoice=monthly_inv)

            # 2. Synchronize Official CorporateGSTInvoice (Tax Invoice under Rule 46)
            gst_inv, gst_created = CorporateGSTInvoice.objects.get_or_create(
                invoice_number=invoice_number,
                defaults={
                    'invoice_date': to_date,
                    'due_date': monthly_inv.due_date,
                    'invoice_type': 'b2b',
                    'party': contract.customer,
                    'transport_contract': contract,
                    'supplier_legal_name': 'Siva Gayathiri Tours & Travels',
                    'supplier_trade_name': 'Sivagayathiri TravelERP',
                    'supplier_gstin': '33AABCS1234F1Z8',
                    'supplier_state_code': '33',
                    'supplier_address': '44/2 Avinashi Road, Civil Aerodrome Post, Coimbatore, Tamil Nadu',
                    'supplier_pincode': '641014',
                    'recipient_legal_name': contract.customer.name,
                    'recipient_trade_name': contract.customer.name,
                    'recipient_gstin': getattr(contract.customer, 'gstin', '33AAACB1234A1Z5') or '33AAACB1234A1Z5',
                    'recipient_state_code': '33',
                    'recipient_address': getattr(contract.customer, 'address', 'Coimbatore IT Corridor, Tamil Nadu') or 'Coimbatore IT Corridor, Tamil Nadu',
                    'recipient_pincode': '641035',
                    'place_of_supply': '33-Tamil Nadu',
                    'sac_code': cls.DEFAULT_SAC_CODE,
                    'supply_type': 'services',
                    'taxable_value': monthly_inv.net_taxable_amount,
                    'gst_rate_percent': monthly_inv.gst_rate,
                    'cgst_rate': Decimal(str(reconciliation['gst_rate'])) / Decimal('2.0') if reconciliation['is_intrastate'] else Decimal('0.00'),
                    'cgst_amount': Decimal(str(reconciliation['cgst_amount'])),
                    'sgst_rate': Decimal(str(reconciliation['gst_rate'])) / Decimal('2.0') if reconciliation['is_intrastate'] else Decimal('0.00'),
                    'sgst_amount': Decimal(str(reconciliation['sgst_amount'])),
                    'igst_rate': Decimal(str(reconciliation['gst_rate'])) if not reconciliation['is_intrastate'] else Decimal('0.00'),
                    'igst_amount': Decimal(str(reconciliation['igst_amount'])),
                    'total_tax': monthly_inv.gst_amount,
                    'total_invoice_value': monthly_inv.grand_total,
                    'payment_status': 'unpaid',
                }
            )

            # Generate Line Items
            InvoiceLineItem.objects.filter(invoice=gst_inv).delete()

            is_intrastate = reconciliation['is_intrastate']
            gst_rate = Decimal(str(reconciliation['gst_rate']))

            # Line 1: Base Contract Operations
            base_amt = Decimal(str(reconciliation['base_contract_amount']))
            cgst_l1 = round(base_amt * (gst_rate / Decimal('200.0')), 2) if is_intrastate else Decimal('0.00')
            sgst_l1 = cgst_l1 if is_intrastate else Decimal('0.00')
            igst_l1 = round(base_amt * (gst_rate / Decimal('100.0')), 2) if not is_intrastate else Decimal('0.00')
            qty_l1 = Decimal(str(reconciliation['total_trips_completed'])) if contract.billing_model == 'per_trip' else Decimal('1.00')
            rate_l1 = base_amt if contract.billing_model != 'per_trip' else (round(base_amt / qty_l1, 2) if qty_l1 > 0 else base_amt)

            InvoiceLineItem.objects.create(
                invoice=gst_inv,
                item_description=f"Corporate Staff Commute Services ({reconciliation['month_label']}) - {reconciliation['total_trips_completed']} Shifts Completed",
                sac_code=cls.DEFAULT_SAC_CODE,
                quantity=qty_l1,
                unit="TRIP" if contract.billing_model == 'per_trip' else "MONTH",
                rate=rate_l1,
                taxable_amount=base_amt,
                cgst_amount=cgst_l1,
                sgst_amount=sgst_l1,
                igst_amount=igst_l1,
                total_amount=base_amt + cgst_l1 + sgst_l1 + igst_l1
            )

            # Line 2: Extra KM Surcharge (if any)
            if reconciliation['extra_km_amount'] > 0:
                extra_amt = Decimal(str(reconciliation['extra_km_amount']))
                cgst_l2 = round(extra_amt * (gst_rate / Decimal('200.0')), 2) if is_intrastate else Decimal('0.00')
                sgst_l2 = cgst_l2 if is_intrastate else Decimal('0.00')
                igst_l2 = round(extra_amt * (gst_rate / Decimal('100.0')), 2) if not is_intrastate else Decimal('0.00')
                InvoiceLineItem.objects.create(
                    invoice=gst_inv,
                    item_description="Overage Distance Surcharge (Exceeded Monthly Package Base)",
                    sac_code=cls.DEFAULT_SAC_CODE,
                    quantity=Decimal('1.00'),
                    unit="KM",
                    rate=extra_amt,
                    taxable_amount=extra_amt,
                    cgst_amount=cgst_l2,
                    sgst_amount=sgst_l2,
                    igst_amount=igst_l2,
                    total_amount=extra_amt + cgst_l2 + sgst_l2 + igst_l2
                )

            # Line 3: Fuel Price Escalation (if any)
            if reconciliation['fuel_escalation_amount'] > 0:
                fuel_amt = Decimal(str(reconciliation['fuel_escalation_amount']))
                cgst_l3 = round(fuel_amt * (gst_rate / Decimal('200.0')), 2) if is_intrastate else Decimal('0.00')
                sgst_l3 = cgst_l3 if is_intrastate else Decimal('0.00')
                igst_l3 = round(fuel_amt * (gst_rate / Decimal('100.0')), 2) if not is_intrastate else Decimal('0.00')
                InvoiceLineItem.objects.create(
                    invoice=gst_inv,
                    item_description=f"Fuel Price Escalation (Diesel Base: ₹{reconciliation['base_fuel_price']}/L vs Prevailing: ₹{reconciliation['prevailing_fuel_price']}/L)",
                    sac_code=cls.DEFAULT_SAC_CODE,
                    quantity=Decimal('1.00'),
                    unit="ADJ",
                    rate=fuel_amt,
                    taxable_amount=fuel_amt,
                    cgst_amount=cgst_l3,
                    sgst_amount=sgst_l3,
                    igst_amount=igst_l3,
                    total_amount=fuel_amt + cgst_l3 + sgst_l3 + igst_l3
                )

            # Line 4: Highway Tolls & FASTag Pass-Through (if any)
            if reconciliation['toll_parking_amount'] > 0:
                toll_amt = Decimal(str(reconciliation['toll_parking_amount']))
                InvoiceLineItem.objects.create(
                    invoice=gst_inv,
                    item_description="Reimbursable Highway FASTag Toll & Parking Charges",
                    sac_code=cls.DEFAULT_SAC_CODE,
                    quantity=Decimal('1.00'),
                    unit="TRIP",
                    rate=toll_amt,
                    taxable_amount=toll_amt,
                    cgst_amount=Decimal('0.00'),
                    sgst_amount=Decimal('0.00'),
                    igst_amount=Decimal('0.00'),
                    total_amount=toll_amt
                )

            # Line 5: SLA Deductions (if any)
            if reconciliation['sla_penalty_deduction'] > 0:
                sla_amt = Decimal(str(reconciliation['sla_penalty_deduction']))
                cgst_l5 = round(sla_amt * (gst_rate / Decimal('200.0')), 2) if is_intrastate else Decimal('0.00')
                sgst_l5 = cgst_l5 if is_intrastate else Decimal('0.00')
                igst_l5 = round(sla_amt * (gst_rate / Decimal('100.0')), 2) if not is_intrastate else Decimal('0.00')
                InvoiceLineItem.objects.create(
                    invoice=gst_inv,
                    item_description=f"Contractual SLA Deductions ({reconciliation['penalties_count']} Delay/Breakdown incidents)",
                    sac_code=cls.DEFAULT_SAC_CODE,
                    quantity=Decimal('1.00'),
                    unit="DED",
                    rate=-sla_amt,
                    taxable_amount=-sla_amt,
                    cgst_amount=-cgst_l5,
                    sgst_amount=-sgst_l5,
                    igst_amount=-igst_l5,
                    total_amount=-(sla_amt + cgst_l5 + sgst_l5 + igst_l5)
                )

            # QR Code string representation
            gst_inv.qr_code_data = f"UPI://PAY?PA=sivagayathiritravels@icici&PN=SivaGayathiriTours&AM={monthly_inv.grand_total}&TR={invoice_number}&CU=INR"
            gst_inv.save()

        return {
            "status": "success",
            "invoice_number": invoice_number,
            "monthly_invoice_id": monthly_inv.id,
            "gst_invoice_id": gst_inv.id,
            "grand_total": float(monthly_inv.grand_total),
            "net_taxable": float(monthly_inv.net_taxable_amount),
            "gst_amount": float(monthly_inv.gst_amount),
            "due_date": monthly_inv.due_date.strftime('%Y-%m-%d') if monthly_inv.due_date else None,
            "message": f"Successfully generated GST Tax Invoice {invoice_number} for ₹{monthly_inv.grand_total:,.2f}."
        }

    @classmethod
    def calculate_driver_commute_bhatta(
        cls,
        driver_id: int,
        from_date: datetime.date,
        to_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Calculates accrued duty bhatta, night allowances, and advances for a corporate commute chauffeur.
        """
        driver = Driver.objects.get(id=driver_id)
        trips = ContractTripLog.objects.filter(
            driver=driver,
            date__gte=from_date,
            date__lte=to_date,
            status__in=['completed', 'scheduled', 'en_route']
        ).select_related('shift', 'shift__route')

        total_shifts = trips.count()
        standard_bata = Decimal('0.00')
        night_allowance = Decimal('0.00')
        early_morning_allowance = Decimal('0.00')

        trip_details = []
        for t in trips:
            bata_val = t.driver_bata or Decimal('350.00') # Base shift bhatta
            standard_bata += bata_val

            # Night duty: departure after 22:00 or before 06:00
            dep_time = t.scheduled_departure_time or (t.shift.timing if t.shift else None)
            is_night = False
            is_early = False
            bonus = Decimal('0.00')

            if dep_time:
                if dep_time.hour >= 22 or dep_time.hour < 5:
                    is_night = True
                    bonus += Decimal('250.00')
                    night_allowance += Decimal('250.00')
                elif dep_time.hour == 5:
                    is_early = True
                    bonus += Decimal('150.00')
                    early_morning_allowance += Decimal('150.00')

            trip_details.append({
                "trip_id": t.id,
                "date": t.date.strftime('%Y-%m-%d'),
                "route_name": t.shift.route.name if (t.shift and t.shift.route) else "Shuttle Run",
                "shift_timing": dep_time.strftime('%H:%M') if dep_time else "N/A",
                "base_bata": float(bata_val),
                "bonus": float(bonus),
                "is_night": is_night,
                "total": float(bata_val + bonus)
            })

        total_earnings = standard_bata + night_allowance + early_morning_allowance

        # Check advances given to driver in date range
        advances_qs = DriverAdvance.objects.filter(
            driver=driver,
            date__gte=from_date,
            date__lte=to_date
        )
        total_advances = advances_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        net_payable = max(Decimal('0.00'), total_earnings - total_advances)

        return {
            "driver_id": driver.id,
            "driver_name": driver.name,
            "driver_phone": driver.phone,
            "from_date": from_date.strftime('%Y-%m-%d'),
            "to_date": to_date.strftime('%Y-%m-%d'),
            "total_shifts": total_shifts,
            "standard_bata": float(standard_bata),
            "night_allowance": float(night_allowance),
            "early_morning_allowance": float(early_morning_allowance),
            "total_earnings": float(total_earnings),
            "total_advances": float(total_advances),
            "net_payable": float(net_payable),
            "trips": trip_details
        }

    @classmethod
    def settle_driver_commute_bhatta(
        cls,
        driver_id: int,
        from_date: datetime.date,
        to_date: datetime.date,
        payment_mode: str = 'bank_transfer',
        reference: str = '',
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Commits chauffeur bhatta settlement into DriverAllowanceLedger.
        """
        driver = Driver.objects.get(id=driver_id)
        calc = cls.calculate_driver_commute_bhatta(driver_id, from_date, to_date)
        net_amount = Decimal(str(calc["net_payable"]))

        with transaction.atomic():
            # Create Allowance Ledger Entry
            ledger_entry = DriverAllowanceLedger.objects.create(
                driver=driver,
                entry_type='bata',
                amount=net_amount,
                balance_after=Decimal('0.00'),
                date=to_date,
                payment_reference=reference or f"BATA-SETTLE-{to_date.strftime('%Y%m%d')}",
                notes=f"Corporate Commute Bhatta Payout ({calc['total_shifts']} shifts). {notes}".strip()
            )

        return {
            "status": "success",
            "ledger_id": ledger_entry.id,
            "driver_name": driver.name,
            "amount_settled": float(net_amount),
            "message": f"Successfully settled ₹{net_amount:,.2f} bhatta for Chauffeur {driver.name}."
        }