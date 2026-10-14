import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Driver, Vehicle, VehicleType, Party, StaffProfile
from operations.models import Booking, Trip, TrafficFine
from finance.models import (
    TripExpense, DriverSettlement, BataTierRule, DriverAllowanceLedger,
    Payment, PettyCashAccount, PettyCashTransaction
)
from finance.driver_settlement_engine import DriverSettlementEngine


class DriverSettlementAndBataStudioTestCase(TestCase):
    """
    Comprehensive Test Suite for Option A:
    Automated Driver Settlement & Bata Payroll Engine (1-Click Payout Studio).
    """

    def setUp(self):
        self.client = Client()

        # Create Admin User & Staff Profile
        self.user = User.objects.create_superuser(
            username='settlement_controller',
            email='controller@travelerp.com',
            password='Password@123'
        )
        self.profile = StaffProfile.objects.create(
            user=self.user,
            role='finance_controller',
            branch='Coimbatore Hub'
        )
        self.client.force_login(self.user)

        # Vehicle Type & Vehicle Asset
        self.v_type = VehicleType.objects.create(
            name='Toyota Innova Crysta',
            seating_capacity=7,
            driver_bata=Decimal('500.00')
        )
        self.vehicle = Vehicle.objects.create(
            registration_number='TN38BZ9999',
            vehicle_type=self.v_type,
            seating_capacity=7,
            ownership_type='owned',
            status='available',
            base_depot='Coimbatore Hub'
        )

        # Driver Captain
        self.driver = Driver.objects.create(
            name='Murugan K',
            phone='9840198765',
            driver_type='owned',
            status='active',
            base_depot='Coimbatore Hub',
            upi_id='murugan@okaxis',
            bank_account_number='5010022334455',
            ifsc_code='HDFC0001234',
            bank_name='HDFC Bank',
            aadhar_number='123456789012',
            joining_date=datetime.date(2025, 1, 1)
        )

        # Client / Customer
        self.customer = Party.objects.create(
            name='Cognizant Tech Park Executive',
            party_type='customer',
            phone='9443311223'
        )

        # Depot Petty Cash Float
        self.petty_acc = PettyCashAccount.objects.create(
            account_name='Coimbatore Hub Cashier Float',
            account_type='depot_cashier',
            allocated_limit=Decimal('50000.00'),
            current_balance=Decimal('25000.00'),
            base_depot='Coimbatore Hub',
            is_active=True
        )

        # Bata Tier Rules
        self.rule_suv_ghat = BataTierRule.objects.create(
            name='SUV Ghat Road Nilgiris Slab',
            vehicle_category='suv',
            duty_type='ghat_road',
            base_bata_per_day=Decimal('550.00'),
            night_halt_allowance=Decimal('450.00'),
            early_morning_allowance=Decimal('250.00'),
            late_night_allowance=Decimal('250.00'),
            ghat_road_daily_bonus=Decimal('400.00'),
            overtime_hourly_rate=Decimal('120.00')
        )

    def test_ghat_road_terrain_detection(self):
        """Validates automatic detection of Western Ghats elevation triggers."""
        # Ghat Trip (Ooty)
        booking_ooty = Booking.objects.create(
            booking_number='BKG-OOTY-101',
            party=self.customer,
            guest_name='Executive Commuter',
            pickup_location='Coimbatore Airport',
            destination='Ooty Botanical Gardens',
            pickup_date=datetime.date(2026, 10, 10),
            pickup_time=datetime.time(5, 0), # Early reporting
            drop_date=datetime.date(2026, 10, 12),
            vehicle_type=self.v_type,
            status='confirmed'
        )
        trip_ooty = Trip.objects.create(
            trip_id='TRP-OOTY-101',
            booking=booking_ooty,
            driver=self.driver,
            vehicle=self.vehicle,
            status='completed',
            start_date=datetime.date(2026, 10, 10),
            end_date=datetime.date(2026, 10, 12),
            start_time=datetime.time(5, 0),
            end_time=datetime.time(23, 30), # Late night drop
            days_count=3,
        )

        is_ghat = DriverSettlementEngine.detect_ghat_road(trip_ooty)
        self.assertTrue(is_ghat, "Trip to Ooty must automatically trigger ghat road detection.")

        calc = DriverSettlementEngine.calculate_trip_driver_settlement(trip_ooty)
        self.assertTrue(calc['is_ghat_road'])
        self.assertEqual(calc['duty_type'], 'ghat_road')
        # 3 days * 400.00 = 1200.00 ghat bonus
        self.assertEqual(Decimal(str(calc['ghat_road_allowance'])), Decimal('1200.00'))
        # Early reporting bonus active (< 06:00 AM)
        self.assertEqual(Decimal(str(calc['early_morning_allowance'])), Decimal('250.00'))
        # Late night drop bonus active (>= 23:00)
        self.assertEqual(Decimal(str(calc['late_night_allowance'])), Decimal('250.00'))
        # 2 night halts: 2 * 450 = 900.00
        self.assertEqual(Decimal(str(calc['night_halt_allowance'])), Decimal('900.00'))
        # Base bata: 3 * 550 = 1650.00
        self.assertEqual(Decimal(str(calc['base_bata'])), Decimal('1650.00'))
        # Total Bata: 1650 + 900 + 250 + 250 + 1200 = 4250.00
        self.assertEqual(Decimal(str(calc['total_bata_earned'])), Decimal('4250.00'))

    def test_cash_advance_and_expense_reconciliation(self):
        """Verifies net payout math when driver pays fuel/toll and receives cash advances."""
        booking = Booking.objects.create(
            booking_number='BKG-EXP-202',
            party=self.customer,
            guest_name='Executive Commuter',
            pickup_location='Coimbatore',
            destination='Madurai Meenakshi Temple',
            pickup_date=datetime.date(2026, 10, 13),
            pickup_time=datetime.time(9, 0),
            drop_date=datetime.date(2026, 10, 14),
            vehicle_type=self.v_type,
            status='confirmed'
        )
        trip = Trip.objects.create(
            trip_id='TRP-EXP-202',
            booking=booking,
            driver=self.driver,
            vehicle=self.vehicle,
            status='completed',
            start_date=datetime.date(2026, 10, 13),
            end_date=datetime.date(2026, 10, 14),
            days_count=2,
        )

        # 1. Driver Out-of-pocket expenses
        TripExpense.objects.create(
            trip=trip,
            expense_type='fuel',
            amount=Decimal('2000.00'),
            date=datetime.date(2026, 10, 13),
            paid_by='driver'
        )
        TripExpense.objects.create(
            trip=trip,
            expense_type='toll',
            amount=Decimal('450.00'),
            date=datetime.date(2026, 10, 13),
            paid_by='driver'
        )

        # 2. Pre-trip Cash Advance given to driver from Cashier Float
        PettyCashTransaction.objects.create(
            account=self.petty_acc,
            transaction_type='trip_advance',
            category='fuel',
            amount=Decimal('1500.00'),
            trip=trip,
            status='approved'
        )

        # 3. Cash collected by driver from customer
        Payment.objects.create(
            party=self.customer,
            trip=trip,
            amount=Decimal('500.00'),
            payment_type='customer_receipt',
            payment_mode='cash',
            collected_by='driver',
            date=datetime.date(2026, 10, 14)
        )

        calc = DriverSettlementEngine.calculate_trip_driver_settlement(trip)

        # Reimbursements due to driver: 2000 + 450 = 2450.00
        self.assertEqual(Decimal(str(calc['total_reimbursements'])), Decimal('2450.00'))
        # Deductions: Advance (1500) + Cash Collected (500) = 2000.00
        self.assertEqual(Decimal(str(calc['total_deductions'])), Decimal('2000.00'))

        # Net Payout = Total Bata (e.g. 1400) + Reimbursements (2450) - Deductions (2000) = 1850.00
        net_payable = Decimal(str(calc['net_payout_amount']))
        self.assertGreater(net_payable, 0)
        self.assertTrue(calc['is_payable_to_driver'])
        self.assertIn('upi://pay', calc['upi_intent_url'])
        self.assertIn('murugan%40okaxis', calc['upi_intent_url'])

    def test_cash_surrender_when_advance_exceeds_entitlement(self):
        """Verifies that excess cash advance triggers cash surrender to cashier float."""
        booking = Booking.objects.create(
            booking_number='BKG-SURR-303',
            party=self.customer,
            guest_name='Executive Commuter',
            pickup_location='Coimbatore',
            destination='Salem',
            pickup_date=datetime.date(2026, 10, 14),
            pickup_time=datetime.time(9, 0),
            drop_date=datetime.date(2026, 10, 14),
            vehicle_type=self.v_type,
            status='confirmed'
        )
        trip = Trip.objects.create(
            trip_id='TRP-SURR-303',
            booking=booking,
            driver=self.driver,
            vehicle=self.vehicle,
            status='completed',
            start_date=datetime.date(2026, 10, 14),
            end_date=datetime.date(2026, 10, 14),
            days_count=1,
        )

        # Large advance of Rs. 10,000 issued to driver
        PettyCashTransaction.objects.create(
            account=self.petty_acc,
            transaction_type='trip_advance',
            amount=Decimal('10000.00'),
            trip=trip,
            status='approved'
        )

        calc = DriverSettlementEngine.calculate_trip_driver_settlement(trip)
        net_amount = Decimal(str(calc['net_payout_amount']))

        self.assertLess(net_amount, 0, "Driver must owe money back when advance exceeds bata and expenses.")
        self.assertTrue(calc['is_recoverable_from_driver'])
        self.assertFalse(calc['is_payable_to_driver'])

    def test_execute_settlement_workflow_and_ledger(self):
        """Verifies full 1-click execution: updates Trip status, creates voucher, and updates ledger."""
        booking = Booking.objects.create(
            booking_number='BKG-SETTLE-404',
            party=self.customer,
            guest_name='Executive Commuter',
            pickup_location='Coimbatore',
            destination='Palakkad',
            pickup_date=datetime.date(2026, 10, 15),
            pickup_time=datetime.time(9, 0),
            drop_date=datetime.date(2026, 10, 15),
            vehicle_type=self.v_type,
            status='confirmed'
        )
        trip = Trip.objects.create(
            trip_id='TRP-SETTLE-404',
            booking=booking,
            driver=self.driver,
            vehicle=self.vehicle,
            status='completed',
            start_date=datetime.date(2026, 10, 15),
            end_date=datetime.date(2026, 10, 15),
            days_count=1,
        )

        settlement = DriverSettlementEngine.execute_settlement(
            trip=trip,
            settled_by_user=self.user,
            payment_mode='upi',
            payout_reference_utr='UPI-2026-TEST9999',
            fuel_bonus_or_penalty=Decimal('200.00'),
            depot_name='Coimbatore Hub'
        )

        self.assertIsNotNone(settlement)
        self.assertEqual(settlement.status, 'settled')
        self.assertTrue(settlement.voucher_number.startswith('DSV-'))
        self.assertEqual(settlement.payout_reference_utr, 'UPI-2026-TEST9999')

        # Check Trip updated
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'settled')

        # Check Driver Allowance Ledger
        ledger_entries = DriverAllowanceLedger.objects.filter(driver=self.driver, trip=trip)
        self.assertGreaterEqual(ledger_entries.count(), 2)

    def test_settlement_studio_views_and_apis(self):
        """Verifies HTTP responses for Studio UI, context API, execution API, and printable voucher."""
        booking = Booking.objects.create(
            booking_number='BKG-VIEW-505',
            party=self.customer,
            guest_name='Executive Commuter',
            pickup_location='Coimbatore',
            destination='Munnar Hills',
            pickup_date=datetime.date(2026, 10, 16),
            pickup_time=datetime.time(9, 0),
            drop_date=datetime.date(2026, 10, 18),
            vehicle_type=self.v_type,
            status='confirmed'
        )
        trip = Trip.objects.create(
            trip_id='TRP-VIEW-505',
            booking=booking,
            driver=self.driver,
            vehicle=self.vehicle,
            status='completed',
            start_date=datetime.date(2026, 10, 16),
            end_date=datetime.date(2026, 10, 18),
            days_count=3,
        )

        # 1. Studio Dashboard View
        resp_studio = self.client.get('/finance/driver-settlement-studio/')
        self.assertEqual(resp_studio.status_code, 200)
        self.assertContains(resp_studio, 'Driver Settlement')
        self.assertContains(resp_studio, 'Bata Payroll Studio')
        self.assertContains(resp_studio, 'Murugan K')

        # 2. Context API
        resp_context = self.client.get(f'/api/finance/settle/{trip.id}/context/')
        self.assertEqual(resp_context.status_code, 200)
        ctx_data = resp_context.json()
        self.assertEqual(ctx_data['status'], 'success')
        self.assertEqual(ctx_data['data']['driver_name'], 'Murugan K')

        # 3. Settlement Execution POST API
        resp_exec = self.client.post(
            f'/api/finance/settle/{trip.id}/',
            data={
                'payment_mode': 'upi',
                'payout_reference_utr': 'UPI-TEST-123456',
                'fuel_bonus_or_penalty': 150,
            },
            content_type='application/json'
        )
        self.assertEqual(resp_exec.status_code, 200)
        exec_data = resp_exec.json()
        self.assertEqual(exec_data['status'], 'success')
        settlement_id = exec_data['settlement_id']

        # 4. Printable Voucher View
        resp_voucher = self.client.get(f'/finance/settlement/{settlement_id}/voucher/')
        self.assertEqual(resp_voucher.status_code, 200)
        self.assertContains(resp_voucher, 'Driver Settlement Voucher')
        self.assertContains(resp_voucher, 'Sivagayathiri Tours')

        # 5. Driver Mobile Digital Acknowledgment API
        resp_ack = self.client.post(f'/api/finance/settlement/{settlement_id}/acknowledge/')
        self.assertEqual(resp_ack.status_code, 200)
        settlement = DriverSettlement.objects.get(pk=settlement_id)
        self.assertTrue(settlement.driver_acknowledged)
