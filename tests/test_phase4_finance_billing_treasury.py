import datetime
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from core.models import Client as CoreClient, VehicleType, Driver, Vehicle
from operations.models import Booking, Trip, TrafficFine
from finance.models import (
    CorporateGSTInvoice, InvoiceLineItem, EWayBill,
    PettyCashAccount, PettyCashTransaction, TripExpense, Payment,
    Account, JournalEntry, JournalItem
)
from finance.services import calculate_party_ledger
from payments_gateway.models import GatewayTransaction, PaymentGatewayConfig


class Phase4FinanceBillingTreasuryTests(TestCase):
    """
    Comprehensive Backend Test Suite for Phase 4:
    Financial Accounting, Multi-Tier Billing, GST E-Way Bills & Petty Cash Treasury.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='finance_admin_phase4',
            email='finance@travelerp.com',
            password='password123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.party_intra = CoreClient.objects.create(
            name='TCS Siruseri Campus Chennai',
            party_type='corporate',
            phone='9840055112',
            email='fleet.finance@tcs.com',
            gstin='33AAACT1234A1Z1',
            state_code='33',
            address='SIPCOT IT Park, Siruseri, Chennai, Tamil Nadu - 603103'
        )

        self.party_inter = CoreClient.objects.create(
            name='Infosys Electronic City Bangalore',
            party_type='corporate',
            phone='9840055999',
            email='travel.blr@infosys.com',
            gstin='29AAACI9876B1Z2',
            state_code='29',
            address='Electronics City, Hosur Road, Bangalore, Karnataka - 560100'
        )

        self.vehicle_type = VehicleType.objects.create(
            name='Toyota Innova Crysta Phase4',
            seating_capacity=7,
            default_day_rate=Decimal('3500.00'),
            default_km_rate=Decimal('16.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN-01-FN-7777',
            vehicle_type=self.vehicle_type,
            status='available',
            current_km=50000
        )

        self.driver = Driver.objects.create(
            name='Ganesan Chauffeur',
            phone='9842511444',
            status='active'
        )

    # -------------------------------------------------------------------------
    # 1. Multi-Tier Billing Calculations & Additional Surcharges
    # -------------------------------------------------------------------------

    def test_multi_tier_billing_models_and_surcharges(self):
        """Test Fixed, KM, and Day billing model calculations on Trip."""
        # 1. Fixed Billing Model
        trip_fixed = Trip.objects.create(
            party=self.party_intra,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            billing_model='fixed',
            fixed_amount=Decimal('12500.00'),
            driver_bata=Decimal('800.00'),
            status='completed'
        )
        self.assertEqual(trip_fixed.bill_value, Decimal('12500.00'))

        # Add toll & travel expenses billable to customer
        TripExpense.objects.create(
            trip=trip_fixed,
            expense_type='toll',
            amount=Decimal('450.00'),
            date=timezone.now().date(),
            billable_to_customer=True
        )
        self.assertEqual(trip_fixed.total_expenses, Decimal('450.00'))

        # Add Traffic Fine with financial_responsibility='customer'
        TrafficFine.objects.create(
            trip=trip_fixed,
            vehicle=self.vehicle,
            driver=self.driver,
            date_of_offence=timezone.now(),
            challan_number='CH-PH4-2026-001',
            violation_type='speeding',
            fine_amount=Decimal('1000.00'),
            financial_responsibility='customer',
            paid_by='company',
            notes='Over-speeding along expressway corridor'
        )
        self.assertEqual(trip_fixed.customer_billable_fines, Decimal('1000.00'))

        # Total amount = bill_value (12500) + total_expenses (450) + fines (1000) = 13950
        self.assertEqual(trip_fixed.total_amount, Decimal('13950.00'))

        # 2. KM Billing Model
        trip_km = Trip.objects.create(
            party=self.party_intra,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            billing_model='km',
            km_rate=Decimal('16.00'),
            opening_km=50000,
            closing_km=50450,  # 450 km used
            status='completed'
        )
        self.assertEqual(trip_km.used_km, 450)
        # 450 km * 16.00 = 7200.00
        self.assertEqual(trip_km.km_amount, Decimal('7200.00'))
        self.assertEqual(trip_km.total_amount, Decimal('7200.00'))

        # 3. Day Billing Model
        trip_day = Trip.objects.create(
            party=self.party_intra,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            billing_model='day',
            day_rate=Decimal('3500.00'),
            days_count=3,
            status='completed'
        )
        # 3 days * 3500.00 = 10500.00
        self.assertEqual(trip_day.day_amount, Decimal('10500.00'))
        self.assertEqual(trip_day.total_amount, Decimal('10500.00'))

    # -------------------------------------------------------------------------
    # 2. Corporate B2B GST Invoicing & Tax Breakdown (Intra vs Inter-State)
    # -------------------------------------------------------------------------

    def test_corporate_b2b_gst_intra_and_interstate_taxation(self):
        """Test Corporate B2B GST invoice auto-generation with CGST/SGST vs IGST."""
        booking = Booking.objects.create(
            party=self.party_intra,
            pickup_location='Chennai Airport',
            destination='Mahabalipuram',
            pickup_date=timezone.now().date(),
            pickup_time=datetime.time(9, 0),
            status='confirmed'
        )
        trip = Trip.objects.create(
            booking=booking,
            party=self.party_intra,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            billing_model='fixed',
            fixed_amount=Decimal('10000.00'),
            status='completed'
        )

        # 1. Intra-State Invoice (TN Supplier 33 to TN Customer 33 -> CGST 2.5% + SGST 2.5%)
        gen_url = reverse('api-finance-generate-invoice-ewaybill')
        payload_intra = {
            'trip_id': trip.id,
            'party_id': self.party_intra.id,
            'taxable_value': '10000.00',
            'gst_rate_percent': '5.00',
            'sac_code': '996601',
            'recipient_state_code': '33',
            'auto_generate_eway': False
        }
        res_intra = self.client.post(gen_url, data=json.dumps(payload_intra), content_type='application/json')
        self.assertEqual(res_intra.status_code, 200)
        data_intra = res_intra.json()
        self.assertTrue(data_intra['success'])
        inv_id_intra = data_intra['invoice_id']

        inv_intra = CorporateGSTInvoice.objects.get(id=inv_id_intra)
        self.assertEqual(inv_intra.taxable_value, Decimal('10000.00'))
        self.assertEqual(inv_intra.cgst_amount, Decimal('250.00'))
        self.assertEqual(inv_intra.sgst_amount, Decimal('250.00'))
        self.assertEqual(inv_intra.igst_amount, Decimal('0.00'))
        self.assertEqual(inv_intra.total_invoice_value, Decimal('10500.00'))
        self.assertIsNotNone(inv_intra.qr_code_data)
        self.assertTrue(bool(inv_intra.qr_code_svg))

        # 2. Inter-State Invoice (TN Supplier 33 to Karnataka Customer 29 -> IGST 5.0%)
        payload_inter = {
            'party_id': self.party_inter.id,
            'taxable_value': '20000.00',
            'gst_rate_percent': '5.00',
            'sac_code': '996601',
            'recipient_state_code': '29',
            'auto_generate_eway': False
        }
        res_inter = self.client.post(gen_url, data=json.dumps(payload_inter), content_type='application/json')
        self.assertEqual(res_inter.status_code, 200)
        data_inter = res_inter.json()
        self.assertTrue(data_inter['success'])
        inv_id_inter = data_inter['invoice_id']

        inv_inter = CorporateGSTInvoice.objects.get(id=inv_id_inter)
        self.assertEqual(inv_inter.taxable_value, Decimal('20000.00'))
        self.assertEqual(inv_inter.cgst_amount, Decimal('0.00'))
        self.assertEqual(inv_inter.sgst_amount, Decimal('0.00'))
        self.assertEqual(inv_inter.igst_amount, Decimal('1000.00'))
        self.assertEqual(inv_inter.total_invoice_value, Decimal('21000.00'))

        # 3. Printable Invoice View Renders HTTP 200
        view_url = reverse('finance-corporate-invoice-view', kwargs={'invoice_id': inv_intra.id})
        res_view = self.client.get(view_url)
        self.assertEqual(res_view.status_code, 200)
        self.assertContains(res_view, inv_intra.invoice_number)
        self.assertContains(res_view, 'TAX INVOICE')

    # -------------------------------------------------------------------------
    # 3. Official NIC E-Way Bill JSON Generation & Validation
    # -------------------------------------------------------------------------

    def test_nic_eway_bill_generation_and_export(self):
        """Test NIC E-Way Bill automated generation and compliant JSON export."""
        booking = Booking.objects.create(
            party=self.party_intra,
            pickup_location='Chennai Port',
            destination='Sri City SEZ',
            pickup_date=timezone.now().date(),
            pickup_time=datetime.time(8, 0),
            status='confirmed'
        )
        trip = Trip.objects.create(
            booking=booking,
            party=self.party_intra,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            billing_model='fixed',
            fixed_amount=Decimal('55000.00'),
            status='completed'
        )

        gen_url = reverse('api-finance-generate-invoice-ewaybill')
        payload = {
            'trip_id': trip.id,
            'party_id': self.party_intra.id,
            'taxable_value': '55000.00',
            'gst_rate_percent': '5.00',
            'trans_distance_km': 85,
            'auto_generate_eway': True,
            'vehicle_number': self.vehicle.registration_number
        }
        res = self.client.post(gen_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertIn('eway_bill_id', data)

        eway_obj = EWayBill.objects.get(id=data['eway_bill_id'])
        self.assertTrue(bool(eway_obj.eway_bill_number))
        self.assertEqual(eway_obj.trans_distance_km, 85)

        # Export NIC E-Way Bill JSON endpoint
        export_url = reverse('api-finance-export-eway-json', kwargs={'invoice_id': data['invoice_id']})
        res_export = self.client.get(export_url)
        self.assertEqual(res_export.status_code, 200)
        nic_json = res_export.json()
        self.assertIn('supplyType', nic_json)
        self.assertIn('docType', nic_json)
        self.assertIn('itemList', nic_json)
        self.assertIn('totalValue', nic_json)

    # -------------------------------------------------------------------------
    # 4. Dynamic UPI QR, Direct UTR Verification & Double-Entry GL Engine
    # -------------------------------------------------------------------------

    def test_dynamic_upi_and_direct_utr_settlement(self):
        """Test dynamic UPI QR code generator and 1-click UTR settlement posting to GL."""
        booking = Booking.objects.create(
            party=self.party_intra,
            guest_name='Mr. Arvind Swamy',
            pickup_location='Chennai Central',
            destination='Pondicherry',
            pickup_date=datetime.date(2026, 11, 20),
            pickup_time=datetime.time(9, 0),
            quoted_price=Decimal('4800.00'),
            status='confirmed'
        )

        # 1. Generate Dynamic UPI Package
        upi_gen_url = reverse('api-dynamic-upi-generate')
        res_upi = self.client.get(f"{upi_gen_url}?booking_id={booking.id}")
        self.assertEqual(res_upi.status_code, 200)
        upi_data = res_upi.json()
        self.assertEqual(upi_data['status'], 'success')
        self.assertTrue(upi_data['upi_url'].startswith('upi://pay?'))
        self.assertIn('qr_svg', upi_data)
        self.assertIn('qr_base64', upi_data)
        self.assertEqual(upi_data['amount'], 4800.0)

        # 2. Confirm Direct UPI Settlement via UTR
        confirm_url = reverse('api-direct-upi-confirm')
        payload_confirm = {
            'booking_id': booking.id,
            'party_id': self.party_intra.id,
            'utr_number': 'UTR20260926998811',
            'amount': '4800.00'
        }
        res_confirm = self.client.post(confirm_url, data=json.dumps(payload_confirm), content_type='application/json')
        self.assertEqual(res_confirm.status_code, 200)
        confirm_data = res_confirm.json()
        self.assertEqual(confirm_data['status'], 'success')
        self.assertIn('journal_entry', confirm_data)

        # Verify GatewayTransaction created
        txn = GatewayTransaction.objects.get(transaction_id=confirm_data['transaction_id'])
        self.assertEqual(txn.gross_amount, Decimal('4800.00'))
        self.assertEqual(txn.fee_amount, Decimal('0.00'))  # Direct UPI has 0 gateway fee
        self.assertIn(txn.status, ['authorized', 'captured'])
        self.assertIsNotNone(txn.journal_entry)

        # Verify Balanced Double-Entry Journal Posting (Debit Bank/Clearing = Credit Party/Receivable)
        je = txn.journal_entry
        self.assertTrue(je.is_posted)
        items = list(je.items.all())
        total_debit = sum(item.debit for item in items)
        total_credit = sum(item.credit for item in items)
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(total_debit, Decimal('4800.00'))

    # -------------------------------------------------------------------------
    # 5. Party Ledger Calculation & Running Balance
    # -------------------------------------------------------------------------

    def test_party_ledger_calculation_and_running_balance(self):
        """Test calculate_party_ledger computes debits, credits, and closing balance."""
        from_date = datetime.date(2026, 1, 1)
        to_date = datetime.date(2026, 12, 31)

        # 1. Create a completed Trip (Debit to customer)
        Trip.objects.create(
            party=self.party_intra,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=datetime.date(2026, 5, 10),
            billing_model='fixed',
            fixed_amount=Decimal('15000.00'),
            status='completed'
        )

        # 2. Record a Payment Receipt (Credit to customer)
        Payment.objects.create(
            party=self.party_intra,
            amount=Decimal('10000.00'),
            payment_type='customer_receipt',
            payment_mode='bank_transfer',
            date=datetime.date(2026, 5, 15),
            reference_number='NEFT-556677'
        )

        ledger = calculate_party_ledger(self.party_intra, from_date, to_date)
        self.assertIn('opening_balance', ledger)
        self.assertIn('closing_balance', ledger)
        self.assertIn('trips', ledger)
        self.assertIn('payments', ledger)
        self.assertEqual(ledger['trip_total'], Decimal('15000.00'))
        self.assertEqual(ledger['receipt_total'], Decimal('10000.00'))
        self.assertEqual(ledger['closing_balance'], Decimal('5000.00'))

        # Verify ledger endpoint returns HTTP 200
        ledger_url = reverse('party-ledger', kwargs={'party_id': self.party_intra.id})
        res_ledger = self.client.get(ledger_url)
        self.assertEqual(res_ledger.status_code, 200)
        self.assertContains(res_ledger, self.party_intra.name)

    # -------------------------------------------------------------------------
    # 6. Admin Accounting Export Dashboard & GST Studio
    # -------------------------------------------------------------------------

    def test_accounting_dashboard_and_gst_studio_views(self):
        """Test accounting export dashboard and GST studio render HTTP 200."""
        res_acc = self.client.get(reverse('accounting-export'))
        self.assertEqual(res_acc.status_code, 200)
        self.assertContains(res_acc, 'Tally, Zoho')

        res_gst = self.client.get(reverse('admin-gst-studio'))
        self.assertEqual(res_gst.status_code, 200)
        self.assertContains(res_gst, 'Corporate GST B2B Invoicing')

        res_pay = self.client.get(reverse('admin-payment-studio'))
        self.assertEqual(res_pay.status_code, 200)
        self.assertContains(res_pay, 'Payment Gateway Studio')
