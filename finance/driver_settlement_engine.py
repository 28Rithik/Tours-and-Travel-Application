"""
Automated Driver Settlement & Bata Payroll Engine (1-Click Payout Studio)
Enterprise Indian Fleet Bata, Ghat Road Elevation Bonus, and Expense Reconciliation.
"""
from decimal import Decimal
import datetime
import urllib.parse
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q

GHAT_KEYWORDS = {
    'ooty', 'nilgiris', 'kodaikanal', 'kodai', 'munnar', 'valparai',
    'yercaud', 'wayanad', 'vagamon', 'coorg', 'chikmagalur', 'thekkady',
    'gudalur', 'coonoor', 'kotagiri', 'idhukki', 'idukki'
}


class DriverSettlementEngine:
    """
    Core Financial Engine for Multi-Tier Bata Calculation and Net Payout Reconciliation.
    """

    @classmethod
    def detect_ghat_road(cls, trip) -> bool:
        """
        Scans trip destination, package circuit, booking pickup/drop, and notes
        for Western Ghats and hill-station elevation triggers.
        """
        text_corpus = []
        if getattr(trip, 'destination', None):
            text_corpus.append(str(trip.destination).lower())
        if getattr(trip, 'notes', None):
            text_corpus.append(str(trip.notes).lower())
        if getattr(trip, 'booking', None):
            b = trip.booking
            if getattr(b, 'pickup_location', None):
                text_corpus.append(str(b.pickup_location).lower())
            if getattr(b, 'drop_location', None):
                text_corpus.append(str(b.drop_location).lower())
            if getattr(b, 'destination', None):
                text_corpus.append(str(b.destination).lower())
            if getattr(b, 'package', None) and getattr(b.package, 'name', None):
                text_corpus.append(str(b.package.name).lower())
        if getattr(trip, 'package', None) and getattr(trip.package, 'name', None):
            text_corpus.append(str(trip.package.name).lower())

        combined_text = " ".join(text_corpus)
        return any(k in combined_text for k in GHAT_KEYWORDS)

    @classmethod
    def get_vehicle_category(cls, vehicle) -> str:
        """Categorizes vehicle into Sedan, SUV, Tempo Traveller, Mini Coach, or Luxury Coach."""
        if not vehicle:
            return 'suv'
        
        cap = getattr(vehicle, 'seating_capacity', 7) or 7
        name = ""
        if getattr(vehicle, 'vehicle_type', None):
            name = str(vehicle.vehicle_type.name).lower()
        elif getattr(vehicle, 'model_name', None):
            name = str(vehicle.model_name).lower()

        if cap <= 4 or 'etios' in name or 'dzire' in name or 'sedan' in name:
            return 'sedan'
        elif cap <= 8 or 'innova' in name or 'crysta' in name or 'ertiga' in name:
            return 'suv'
        elif cap <= 18 or 'tempo' in name or 'traveller' in name or 'tt' in name:
            return 'tempo_traveller'
        elif cap <= 26 or 'mini' in name:
            return 'mini_coach'
        else:
            return 'luxury_coach'

    @classmethod
    def calculate_trip_driver_settlement(cls, trip) -> dict:
        """
        Computes the complete driver settlement itemization:
        1. Multi-tier Bata (Base, Night Halt, Early Morning, Late Night, Ghat Road, Overtime)
        2. Driver Out-of-Pocket Reimbursements (Fuel slips, Tolls/Fastag, Misc)
        3. Deductions (Trip Cash Advances, Cash Collected from Customer, Traffic Fines)
        4. Net Payable / Net Recoverable
        5. UPI Intent & QR payload
        """
        from finance.models import (
            TripExpense, FuelRecord, DriverSettlement,
            BataTierRule, PettyCashTransaction
        )
        from operations.models import TrafficFine
        from finance.models import Payment

        driver = getattr(trip, 'driver', None)
        if not driver:
            raise ValueError(f"Trip #{getattr(trip, 'trip_id', trip.id)} does not have an assigned driver.")

        days = max(getattr(trip, 'days_count', 1) or 1, 1)
        vehicle = getattr(trip, 'vehicle', None)
        category = cls.get_vehicle_category(vehicle)
        is_ghat = cls.detect_ghat_road(trip)

        duty_type = 'ghat_road' if is_ghat else ('outstation' if days > 1 else 'local')

        # 1. Base Bata & Surcharges from BataTierRule or Intelligent Defaults
        rule = BataTierRule.objects.filter(vehicle_category=category, duty_type=duty_type, is_active=True).first()
        if not rule:
            rule = BataTierRule.objects.filter(vehicle_category=category, is_active=True).first()

        if rule:
            daily_base_rate = rule.base_bata_per_day
            night_halt_rate = rule.night_halt_allowance
            early_morn_rate = rule.early_morning_allowance
            late_night_rate = rule.late_night_allowance
            ghat_bonus_rate = rule.ghat_road_daily_bonus if is_ghat else Decimal('0.00')
            overtime_rate = rule.overtime_hourly_rate
        else:
            defaults = {
                'sedan': (Decimal('400.00'), Decimal('350.00'), Decimal('150.00'), Decimal('150.00'), Decimal('250.00')),
                'suv': (Decimal('500.00'), Decimal('400.00'), Decimal('200.00'), Decimal('200.00'), Decimal('350.00')),
                'tempo_traveller': (Decimal('700.00'), Decimal('500.00'), Decimal('250.00'), Decimal('250.00'), Decimal('400.00')),
                'mini_coach': (Decimal('800.00'), Decimal('600.00'), Decimal('300.00'), Decimal('300.00'), Decimal('500.00')),
                'luxury_coach': (Decimal('1000.00'), Decimal('800.00'), Decimal('400.00'), Decimal('400.00'), Decimal('600.00')),
            }
            def_tup = defaults.get(category, defaults['suv'])
            daily_base_rate, night_halt_rate, early_morn_rate, late_night_rate, ghat_bonus_rate = def_tup
            overtime_rate = Decimal('100.00')

        base_bata = (daily_base_rate * Decimal(str(days))).quantize(Decimal('0.01'))

        # Night Halts
        night_halts_count = max(days - 1, 0)
        if days == 1 and getattr(trip, 'end_time', None) and trip.end_time >= datetime.time(22, 0):
            night_halts_count = 1
        night_halt_allowance = (Decimal(str(night_halts_count)) * night_halt_rate).quantize(Decimal('0.01'))

        # Early Morning Reporting (< 06:00 AM)
        early_morning_allowance = Decimal('0.00')
        if getattr(trip, 'start_time', None) and trip.start_time < datetime.time(6, 0):
            early_morning_allowance = early_morn_rate

        # Late Night Drop (>= 23:00 / 11:00 PM)
        late_night_allowance = Decimal('0.00')
        if getattr(trip, 'end_time', None) and trip.end_time >= datetime.time(23, 0):
            late_night_allowance = late_night_rate

        # Ghat Road Elevation Bonus
        ghat_road_allowance = Decimal('0.00')
        if is_ghat:
            ghat_road_allowance = (ghat_bonus_rate * Decimal(str(days))).quantize(Decimal('0.01'))

        # Multi-day Expedition Incentive (>= 5 days)
        expedition_bonus = Decimal('500.00') if days >= 5 else Decimal('0.00')

        # Single-Day Extended Shift Overtime (> 12 hours)
        overtime_allowance = Decimal('0.00')
        overtime_hours = 0
        if days == 1 and getattr(trip, 'start_time', None) and getattr(trip, 'end_time', None):
            try:
                t1 = datetime.datetime.combine(datetime.date.today(), trip.start_time)
                t2 = datetime.datetime.combine(datetime.date.today(), trip.end_time)
                if t2 < t1:
                    t2 += datetime.timedelta(days=1)
                duration_hrs = (t2 - t1).total_seconds() / 3600.0
                if duration_hrs > 12.0:
                    overtime_hours = int(duration_hrs - 12.0)
                    overtime_allowance = (Decimal(str(overtime_hours)) * overtime_rate).quantize(Decimal('0.01'))
            except Exception:
                pass

        total_bata_earned = (
            base_bata + night_halt_allowance + early_morning_allowance +
            late_night_allowance + ghat_road_allowance + expedition_bonus + overtime_allowance
        ).quantize(Decimal('0.01'))

        # 2. Driver Out-of-Pocket Reimbursements (Paid by Driver)
        driver_expenses_qs = TripExpense.objects.filter(trip=trip, paid_by='driver')
        fuel_paid_by_driver = driver_expenses_qs.filter(expense_type='fuel').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        toll_parking_paid_by_driver = driver_expenses_qs.filter(expense_type__in=['toll', 'parking']).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        other_expenses_paid_by_driver = driver_expenses_qs.exclude(expense_type__in=['fuel', 'toll', 'parking']).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        total_reimbursements = (fuel_paid_by_driver + toll_parking_paid_by_driver + other_expenses_paid_by_driver).quantize(Decimal('0.01'))

        # 3. Cash Advances Issued to Driver for this Trip
        from finance.models import DriverAdvanceAllocation
        direct_allocations = DriverAdvanceAllocation.objects.filter(trip=trip).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        petty_advances = PettyCashTransaction.objects.filter(
            trip=trip, transaction_type='trip_advance', status='approved'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        cash_advances_received = (direct_allocations + petty_advances).quantize(Decimal('0.01'))

        # 4. Cash Collected Directly from Customer / Guest
        cash_collected_from_customer = Payment.objects.filter(
            trip=trip, payment_type='customer_receipt', collected_by='driver'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        cash_collected_from_customer = cash_collected_from_customer.quantize(Decimal('0.01'))

        # 5. Traffic Challans & Fines (Driver Responsibility)
        fines_qs = TrafficFine.objects.filter(
            trip=trip, driver=driver,
            financial_responsibility='driver',
            paid_by__in=['company', 'unpaid']
        )
        traffic_fines_deducted = fines_qs.aggregate(s=Sum('fine_amount'))['s'] or Decimal('0.00')
        traffic_fines_deducted = traffic_fines_deducted.quantize(Decimal('0.01'))

        # 6. Total Deductions & Net Payout Calculation
        total_deductions = (cash_advances_received + cash_collected_from_customer + traffic_fines_deducted).quantize(Decimal('0.01'))
        
        # Net Amount: Positive = Company owes Driver; Negative = Driver must surrender cash
        gross_entitlement = total_bata_earned + total_reimbursements
        net_payout_amount = (gross_entitlement - total_deductions).quantize(Decimal('0.01'))

        # Advance adjusted cannot exceed total batta earned (for model integrity)
        advance_adjusted = min(cash_advances_received, total_bata_earned)

        # 7. Generate NPCI UPI Dynamic Intent URI & QR String
        driver_upi = getattr(driver, 'upi_id', None) or f"{getattr(driver, 'phone', '9840112345')}@upi"
        driver_name = getattr(driver, 'name', 'Chauffeur')
        abs_amount = abs(net_payout_amount)
        trip_code = getattr(trip, 'trip_id', f'TRP-{trip.id}')
        
        upi_intent_url = ""
        if net_payout_amount > 0 and driver_upi:
            note = f"Bata Settlement Trip {trip_code}"
            upi_params = {
                'pa': driver_upi,
                'pn': driver_name,
                'am': f"{abs_amount:.2f}",
                'cu': 'INR',
                'tn': note,
            }
            upi_intent_url = f"upi://pay?{urllib.parse.urlencode(upi_params)}"

        existing_settlement = DriverSettlement.objects.filter(trip=trip).first()

        breakdown = {
            'trip_id': trip.id,
            'trip_code': trip_code,
            'driver_id': driver.id,
            'driver_name': driver_name,
            'driver_phone': getattr(driver, 'phone', ''),
            'driver_upi': driver_upi,
            'driver_bank_account': getattr(driver, 'bank_account_number', ''),
            'driver_ifsc': getattr(driver, 'ifsc_code', ''),
            'vehicle_reg': getattr(vehicle, 'registration_number', 'N/A') if vehicle else 'N/A',
            'vehicle_category': category,
            'duty_type': duty_type,
            'is_ghat_road': is_ghat,
            'days_count': days,
            'base_rate_per_day': float(daily_base_rate),
            'base_bata': float(base_bata),
            'night_halts_count': night_halts_count,
            'night_halt_allowance': float(night_halt_allowance),
            'early_morning_allowance': float(early_morning_allowance),
            'late_night_allowance': float(late_night_allowance),
            'ghat_road_allowance': float(ghat_road_allowance),
            'expedition_bonus': float(expedition_bonus),
            'overtime_hours': overtime_hours,
            'overtime_allowance': float(overtime_allowance),
            'total_bata_earned': float(total_bata_earned),
            'fuel_paid_by_driver': float(fuel_paid_by_driver),
            'toll_parking_paid_by_driver': float(toll_parking_paid_by_driver),
            'other_expenses_paid_by_driver': float(other_expenses_paid_by_driver),
            'total_reimbursements': float(total_reimbursements),
            'gross_entitlement': float(gross_entitlement),
            'cash_advances_received': float(cash_advances_received),
            'cash_collected_from_customer': float(cash_collected_from_customer),
            'traffic_fines_deducted': float(traffic_fines_deducted),
            'total_deductions': float(total_deductions),
            'net_payout_amount': float(net_payout_amount),
            'is_payable_to_driver': bool(net_payout_amount > 0),
            'is_recoverable_from_driver': bool(net_payout_amount < 0),
            'is_even': bool(net_payout_amount == 0),
            'abs_net_amount': float(abs_amount),
            'upi_intent_url': upi_intent_url,
            'existing_voucher': existing_settlement.voucher_number if existing_settlement else None,
            'existing_status': existing_settlement.status if existing_settlement else None,
        }

        return breakdown

    @classmethod
    @transaction.atomic
    def execute_settlement(
        cls,
        trip,
        settled_by_user,
        payment_mode='upi',
        payout_reference_utr='',
        notes='',
        fuel_bonus_or_penalty=Decimal('0.00'),
        depot_name=None,
    ) -> 'DriverSettlement':
        """
        Executes and records the official Driver Settlement:
        1. Calculates itemized allowance and deduction totals.
        2. Adjusts fuel bonus or penalty.
        3. Creates or updates the DriverSettlement record.
        4. Updates Trip.status = 'settled'.
        5. Logs financial entries in Depot Petty Cash Float (if cash mode) and DriverAllowanceLedger.
        """
        from finance.models import (
            DriverSettlement, DriverAllowanceLedger,
            PettyCashAccount, PettyCashTransaction
        )

        calc = cls.calculate_trip_driver_settlement(trip)
        driver = trip.driver

        net_payout = Decimal(str(calc['net_payout_amount'])) + Decimal(str(fuel_bonus_or_penalty))
        total_bata = Decimal(str(calc['total_bata_earned'])) + Decimal(str(fuel_bonus_or_penalty))
        advance_adjusted = min(Decimal(str(calc['cash_advances_received'])), total_bata)

        settlement, created = DriverSettlement.objects.get_or_create(
            trip=trip,
            defaults={
                'driver': driver,
                'total_days': Decimal(str(calc['days_count'])),
                'batta': total_bata,
                'advance_adjusted': advance_adjusted,
            }
        )

        settlement.driver = driver
        settlement.total_days = Decimal(str(calc['days_count']))
        settlement.batta = total_bata
        settlement.advance_adjusted = advance_adjusted
        settlement.status = 'settled'
        settlement.settled_on = timezone.now().date()
        settlement.settled_by = settled_by_user

        settlement.base_bata = Decimal(str(calc['base_bata']))
        settlement.night_halt_allowance = Decimal(str(calc['night_halt_allowance']))
        settlement.early_morning_allowance = Decimal(str(calc['early_morning_allowance']))
        settlement.late_night_allowance = Decimal(str(calc['late_night_allowance']))
        settlement.ghat_road_allowance = Decimal(str(calc['ghat_road_allowance']))
        settlement.fuel_bonus_or_penalty = Decimal(str(fuel_bonus_or_penalty))
        settlement.total_bata_earned = total_bata

        settlement.cash_advances_received = Decimal(str(calc['cash_advances_received']))
        settlement.fuel_paid_by_driver = Decimal(str(calc['fuel_paid_by_driver']))
        settlement.toll_parking_paid_by_driver = Decimal(str(calc['toll_parking_paid_by_driver']))
        settlement.other_expenses_paid_by_driver = Decimal(str(calc['other_expenses_paid_by_driver']))
        settlement.cash_collected_from_customer = Decimal(str(calc['cash_collected_from_customer']))
        settlement.traffic_fines_deducted = Decimal(str(calc['traffic_fines_deducted']))
        settlement.net_payout_amount = net_payout

        settlement.payment_mode = payment_mode
        settlement.payout_reference_utr = payout_reference_utr or f"UPI-{timezone.now().strftime('%y%m%d%H%M%S')}"
        settlement.calculation_breakdown = calc
        settlement.save()

        # Update Trip status
        trip.status = 'settled'
        trip.driver_bata = total_bata
        trip.driver_bata_breakdown = calc
        trip.save(update_fields=['status', 'driver_bata', 'driver_bata_breakdown'])

        # Record in Driver Allowance Ledger
        DriverAllowanceLedger.objects.create(
            driver=driver,
            entry_type='bata_earned',
            amount=total_bata,
            balance_after=total_bata,
            trip=trip,
            settlement=settlement,
            date=timezone.now().date(),
            notes=f"Trip #{trip.trip_id} Bata Earned ({calc['duty_type'].upper()})"
        )

        if net_payout > 0:
            DriverAllowanceLedger.objects.create(
                driver=driver,
                entry_type='payout_credit',
                amount=net_payout,
                balance_after=Decimal('0.00'),
                trip=trip,
                settlement=settlement,
                date=timezone.now().date(),
                payment_reference=settlement.payout_reference_utr,
                notes=f"Net Payout via {payment_mode.upper()} Ref: {settlement.payout_reference_utr}"
            )
        elif net_payout < 0:
            DriverAllowanceLedger.objects.create(
                driver=driver,
                entry_type='refund_received',
                amount=abs(net_payout),
                balance_after=Decimal('0.00'),
                trip=trip,
                settlement=settlement,
                date=timezone.now().date(),
                payment_reference=settlement.payout_reference_utr,
                notes=f"Cash Surrender of unspent advance deposited to Cashier"
            )

        # If payment_mode is Cash, automatically sync with Depot Petty Cash Float
        if payment_mode == 'cash':
            depot = depot_name or getattr(driver, 'base_depot', 'Chennai Central HQ')
            petty_acc = PettyCashAccount.objects.filter(base_depot=depot, is_active=True).first()
            if not petty_acc:
                petty_acc = PettyCashAccount.objects.filter(is_active=True).first()

            if petty_acc:
                if net_payout > 0:
                    PettyCashTransaction.objects.create(
                        account=petty_acc,
                        transaction_type='expense',
                        category='driver_food',
                        amount=net_payout,
                        recipient_or_vendor=f"Driver {driver.name}",
                        trip=trip,
                        status='approved',
                        authorized_by=settled_by_user,
                        notes=f"Cash settlement voucher {settlement.voucher_number} for trip {trip.trip_id}"
                    )
                elif net_payout < 0:
                    PettyCashTransaction.objects.create(
                        account=petty_acc,
                        transaction_type='settlement_refund',
                        category='top_up_receipt',
                        amount=abs(net_payout),
                        recipient_or_vendor=f"Driver {driver.name}",
                        trip=trip,
                        status='approved',
                        authorized_by=settled_by_user,
                        notes=f"Cash surrender from driver for trip {trip.trip_id} (Voucher {settlement.voucher_number})"
                    )

        return settlement
