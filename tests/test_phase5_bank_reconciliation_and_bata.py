from decimal import Decimal
from datetime import date, time, timedelta
import json
import io

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Vehicle, VehicleType, Driver, Party
from operations.models import Trip, Booking
from finance.models import (
    CorporateGSTInvoice,
    Payment,
    BankStatementUpload,
    BankStatementEntry,
    Account,
    JournalEntry,
)
from finance.bank_reconciliation import (
    parse_bank_statement_csv,
    extract_utr_or_ref,
    auto_match_statement_entries,
    execute_bank_reconciliation,
)
from operations.driver_bata_engine import calculate_trip_driver_bata


class Phase5BankReconciliationAndBataTestCase(TestCase):
    """
    Comprehensive Automated Test Suite for Phase 5:
    1. Automated Bank Statement CSV Parser & UTR Extraction Engine
    2. Multi-Strategy ERP Auto-Matching (Exact UTR, Booking ID, Name + Amount, Proximity)
    3. One-Click Bank Reconciliation & Double-Entry Payment Posting
    4. Bank Reconciliation Studio UI & Audit CSV Export
    5. Multi-Component Driver Allowance (Batta) Engine (Daily, Night Halt, Early Morning, Overtime)
    6. Trip Auto-Bata API & Operational Console Integration
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='cfo_admin',
            email='cfo@sivagayathiri.com',
            password='password123'
        )
        self.client.login(username='cfo_admin', password='password123')

        # Provision GL Accounts
        self.bank_account = Account.objects.create(
            name="HDFC Main Current Bank Account",
            code="1010",
            account_type="asset"
        )
        self.ar_account = Account.objects.create(
            name="Trade Debtors & Accounts Receivable",
            code="1020",
            account_type="asset"
        )

        # Provision Corporate & Retail Parties
        self.party_corp = Party.objects.create(name='Infosys BPM Limited', party_type='customer')
        self.party_retail = Party.objects.create(name='Dr. Arvind Swaminathan', party_type='customer')

        # Provision Fleet & Chauffeurs
        self.vtype_innova = VehicleType.objects.create(
            name='Innova Crysta Luxury',
            seating_capacity=7,
            driver_bata=Decimal('500.00')
        )
        self.vtype_coach = VehicleType.objects.create(
            name='Volvo Luxury Coach',
            seating_capacity=54,
            driver_bata=Decimal('1000.00')
        )

        self.vehicle_innova = Vehicle.objects.create(
            registration_number='TN-38-CL-4411',
            vehicle_type=self.vtype_innova,
            seating_capacity=7,
            status='available'
        )
        self.vehicle_coach = Vehicle.objects.create(
            registration_number='TN-38-BZ-9090',
            vehicle_type=self.vtype_coach,
            seating_capacity=54,
            status='available'
        )

        self.driver = Driver.objects.create(
            name='Karthik Murugan',
            phone='9842533777',
            status='active'
        )

        # Provision Bookings
        self.booking_arvind = Booking.objects.create(
            booking_number='BK-2026-0042',
            party=self.party_retail,
            guest_name='Dr. Arvind Swaminathan',
            guest_phone='9840112233',
            pickup_location='Coimbatore Airport',
            destination='Ooty Heritage Tea Estate',
            pickup_date=date(2026, 10, 1),
            pickup_time='05:30:00',
            vehicle_type=self.vtype_innova,
            quoted_price=Decimal('25000.00'),
            status='pending',
        )

        self.trip = Trip.objects.create(
            trip_id='TR-2026-0042',
            booking=self.booking_arvind,
            party=self.party_retail,
            guest_name='Dr. Arvind Swaminathan',
            vehicle=self.vehicle_innova,
            driver=self.driver,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 3),
            start_time=time(5, 30),  # Early morning < 06:00
            end_time=time(19, 0),
            days_count=3,
            fixed_amount=Decimal('25000.00'),
            status='assigned',
        )

        # Provision Corporate Invoice
        self.invoice = CorporateGSTInvoice.objects.create(
            invoice_number='INV-2026-0088',
            party=self.party_corp,
            recipient_legal_name=self.party_corp.name,
            invoice_date=date(2026, 10, 1),
            total_invoice_value=Decimal('85000.00'),
            taxable_value=Decimal('80952.38'),
            paid_amount=Decimal('0.00'),
            payment_status='unpaid'
        )

    def test_utr_extraction_regex(self):
        """Test extraction of 12-digit UTR and IMPS/UPI codes from complex bank narratives."""
        narr1 = "UPI/627491028374/Dr Arvind/BK-2026-0042 Advance/HDFC Bank"
        self.assertEqual(extract_utr_or_ref(narr1), "627491028374")

        narr2 = "NEFT-SBI-429184019283-Infosys BPM Corporate Tour"
        self.assertEqual(extract_utr_or_ref(narr2), "429184019283")

        narr3 = "IMPS/P2A/919840112233/Payment Ref"
        self.assertEqual(extract_utr_or_ref(narr3), "919840112233")

    def test_parse_bank_statement_csv(self):
        """Test parsing bank statement CSV into standardized records."""
        sample_csv = (
            "Txn Date,Narration,Ref / UTR,Debit,Credit,Balance\n"
            "01-10-2026,UPI/627491028374/Dr Arvind Swaminathan/HDFC,627491028374,,25000.00,125000.00\n"
            "01-10-2026,NEFT-SBI-429184019283-Corporate Payment,429184019283,,85000.00,210000.00\n"
            "02-10-2026,GARAGE PETROL DIESEL REFILL COIMBATORE,,12500.00,,197500.00\n"
        )
        parsed = parse_bank_statement_csv(sample_csv)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]['transaction_date'], date(2026, 10, 1))
        self.assertEqual(parsed[0]['deposit_amount'], Decimal('25000.00'))
        self.assertEqual(parsed[0]['reference_or_utr'], '627491028374')
        self.assertEqual(parsed[2]['withdrawal_amount'], Decimal('12500.00'))

    def test_auto_matching_algorithm(self):
        """Test multi-strategy auto-matching against open Bookings and Invoices."""
        upload = BankStatementUpload.objects.create(
            bank_name='hdfc',
            filename='hdfc_oct_feed.csv',
            account_number='50200084729104',
            uploaded_by=self.user,
            total_transactions=2
        )

        # Entry 1: Contains exact booking number BK-2026-0042 and ₹25,000
        e1 = BankStatementEntry.objects.create(
            upload=upload,
            transaction_date=date(2026, 10, 1),
            narration="UPI/627491028374/Dr Arvind Swaminathan/BK-2026-0042 Advance/HDFC",
            reference_or_utr="627491028374",
            deposit_amount=Decimal('25000.00'),
            balance=Decimal('125000.00')
        )

        # Entry 2: Contains exact invoice number INV-2026-0088 and ₹85,000
        e2 = BankStatementEntry.objects.create(
            upload=upload,
            transaction_date=date(2026, 10, 1),
            narration="NEFT-SBI-429184019283-Infosys BPM INV-2026-0088 Payment",
            reference_or_utr="429184019283",
            deposit_amount=Decimal('85000.00'),
            balance=Decimal('210000.00')
        )

        matched_count = auto_match_statement_entries(upload.entries.all())
        self.assertEqual(matched_count, 2)

        e1.refresh_from_db()
        self.assertEqual(e1.status, 'matched')
        self.assertEqual(e1.match_confidence, 100)
        self.assertEqual(e1.matched_booking, self.booking_arvind)

        e2.refresh_from_db()
        self.assertEqual(e2.status, 'matched')
        self.assertEqual(e2.match_confidence, 100)
        self.assertEqual(e2.matched_invoice, self.invoice)

    def test_execute_bank_reconciliation_and_payment_creation(self):
        """Test 1-click execution creates Payment and updates Booking status."""
        upload = BankStatementUpload.objects.create(
            bank_name='sbi',
            filename='sbi_feed.csv',
            uploaded_by=self.user,
            total_transactions=1
        )
        entry = BankStatementEntry.objects.create(
            upload=upload,
            transaction_date=date(2026, 10, 1),
            narration="UPI/627491028374/Dr Arvind Swaminathan/BK-2026-0042",
            reference_or_utr="627491028374",
            deposit_amount=Decimal('25000.00'),
            matched_booking=self.booking_arvind,
            matched_party=self.party_retail,
            match_confidence=100,
            status='matched'
        )

        payment = execute_bank_reconciliation(entry, user=self.user)
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('25000.00'))
        self.assertEqual(payment.reference_number, '627491028374')

        entry.refresh_from_db()
        self.assertEqual(entry.status, 'reconciled')
        self.assertEqual(entry.matched_payment, payment)

        # Booking should transition from pending to confirmed
        self.booking_arvind.refresh_from_db()
        self.assertEqual(self.booking_arvind.status, 'confirmed')

        # Upload metrics updated
        upload.refresh_from_db()
        self.assertEqual(upload.reconciled_count, 1)
        self.assertEqual(upload.reconciled_amount, Decimal('25000.00'))

    def test_bank_reconciliation_studio_view_and_api(self):
        """Test Bank Reconciliation Studio renders HTTP 200 and handles CSV upload."""
        # 1. Studio View
        res_studio = self.client.get(reverse('admin-bank-reconciliation-studio'))
        self.assertEqual(res_studio.status_code, 200)
        self.assertContains(res_studio, 'Bank Statement Auto-Reconciler')

        # 2. Upload API
        csv_sample = (
            "Txn Date,Narration,Ref / UTR,Debit,Credit,Balance\n"
            "01-10-2026,UPI/884910294817/BK-2026-0042 Advance,884910294817,,25000.00,100000.00\n"
        )
        res_upload = self.client.post(
            reverse('api-finance-bank-reconciliation-upload'),
            {'bank_name': 'sbi', 'account_number': '123456789', 'csv_text': csv_sample}
        )
        self.assertEqual(res_upload.status_code, 200)
        data = res_upload.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['total_parsed'], 1)
        self.assertEqual(data['matched_count'], 1)

        # 3. Export CSV Report
        upload_id = data['upload_id']
        res_export = self.client.get(reverse('export-bank-reconciliation') + f"?upload_id={upload_id}")
        self.assertEqual(res_export.status_code, 200)
        self.assertEqual(res_export['Content-Type'], 'text/csv')
        self.assertIn('884910294817', res_export.content.decode('utf-8'))

    def test_driver_bata_calculation_engine_multiday_tour(self):
        """Test multi-day tour driver bata breakdown: base daily + night halts + early morning."""
        res = calculate_trip_driver_bata(self.trip)

        # 3 days @ ₹500 (vehicle.driver_bata) = ₹1,500
        self.assertEqual(res['base_bata'], Decimal('1500.00'))
        self.assertEqual(res['days_count'], 3)
        self.assertEqual(res['daily_rate'], Decimal('500.00'))

        # 3 days tour has 2 night halts @ ₹400 = ₹800
        self.assertEqual(res['night_halts_count'], 2)
        self.assertEqual(res['night_halt_bata'], Decimal('800.00'))

        # Pickup at 05:30 AM triggers early morning allowance = ₹200
        self.assertEqual(res['early_morning_bata'], Decimal('200.00'))

        # Total = 1500 + 800 + 200 = 2,500
        self.assertEqual(res['total_bata'], Decimal('2500.00'))
        self.assertIn('Base: 3 day(s) @ ₹500', res['calculation_notes'])
        self.assertIn('2 Night Halt(s) @ ₹400', res['calculation_notes'])
        self.assertIn('Early Morning Reporting', res['calculation_notes'])

    def test_trip_calculate_auto_bata_method_and_api(self):
        """Test Trip.calculate_auto_bata() method and REST calculation API."""
        # Method call
        res = self.trip.calculate_auto_bata(save=True)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.driver_bata, Decimal('2500.00'))
        self.assertIn('night_halt_bata', self.trip.driver_bata_breakdown)

        # API Call
        url = reverse('api-trip-calculate-bata', args=[self.trip.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['total_bata'], 2500.0)
        self.assertEqual(data['driver_name'], 'Karthik Murugan')
        self.assertIn('Calculated total driver allowance: ₹2,500.00', data['message'])

    def test_trip_detail_view_includes_bata_panel(self):
        """Test operations trip detail view renders the Driver Allowance (Bata) panel."""
        self.trip.calculate_auto_bata(save=True)
        url = reverse('trip-detail', args=[self.trip.pk])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Driver Allowance (Bata) Breakdown')
        self.assertContains(res, '₹2500.00')
        self.assertContains(res, 'Auto-Calculate Bata')
