import json
import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Vehicle, Driver, Party, StaffProfile
from fleet_contracts.models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractTripLog,
    ContractSLAPenalty,
    ContractMonthlyInvoice,
)
from finance.models import (
    CorporateGSTInvoice,
    InvoiceLineItem,
    DriverAllowanceLedger,
)
from fleet_contracts.billing_engine import ContractBillingEngine


class ContractBillingEngineTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='billing_controller_cb',
            email='billing@sivagayathiri.in',
            password='Password@123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role='fleet_manager',
            branch='Coimbatore Hub'
        )
        self.client.force_login(self.user)

        self.today = datetime.date.today()
        self.year = self.today.year
        self.month = self.today.month
        self.from_date, self.to_date = ContractBillingEngine.get_month_date_range(self.year, self.month)

        # Chauffeur & Vehicle
        self.driver = Driver.objects.create(
            name="Murugan K. (Captain Murugan)",
            phone="+919842111001",
            license_number="TN38-2015-0012345",
            status="active"
        )
        self.vehicle = Vehicle.objects.create(
            registration_number="TN-38-CB-9001",
            brand="Toyota",
            model="Innova Crysta 2.4 GX+",
            seating_capacity=7,
            status="available",
            base_depot="Coimbatore Central HQ",
            current_km=55000,
            next_service_due_km=65000,
            fc_expiry=self.today + datetime.timedelta(days=200),
            insurance_expiry=self.today + datetime.timedelta(days=200)
        )

        # Corporate Client & Fixed Monthly Contract
        self.customer = Party.objects.create(
            name="Cognizant Technologies Coimbatore",
            party_type="customer"
        )
        self.contract_fixed = TransportContract.objects.create(
            name="Cognizant IT Park Monthly Fixed SLA",
            customer=self.customer,
            start_date=self.from_date - datetime.timedelta(days=60),
            end_date=self.to_date + datetime.timedelta(days=300),
            billing_model="fixed_monthly",
            default_rate=Decimal('220000.00'),
            gst_rate=Decimal('5.00'),
            payment_credit_days=30,
            fuel_escalation_enabled=True,
            base_diesel_price=Decimal('92.00'),
            fuel_revision_factor=Decimal('0.20'),
            sla_penalty_cap_pct=Decimal('10.00'),
            status="active"
        )

        # Per KM Contract
        self.contract_per_km = TransportContract.objects.create(
            name="Bosch Campus Per KM SLA",
            customer=self.customer,
            start_date=self.from_date - datetime.timedelta(days=60),
            end_date=self.to_date + datetime.timedelta(days=300),
            billing_model="per_km",
            default_rate=Decimal('25.00'),
            gst_rate=Decimal('5.00'),
            status="active"
        )

        # Routes & Shifts
        self.route_fixed = Route.objects.create(
            contract=self.contract_fixed,
            name="Route 501 - Gandhipuram to Cognizant CHIL SEZ",
            origin="Gandhipuram",
            destination="CHIL SEZ",
            distance_km=25.0
        )
        self.shift_day = Shift.objects.create(
            route=self.route_fixed,
            shift_name="Day Login",
            direction="inbound",
            timing=datetime.time(8, 0)
        )
        self.shift_night = Shift.objects.create(
            route=self.route_fixed,
            shift_name="Night Drop BPO",
            direction="outbound",
            timing=datetime.time(23, 0) # Night duty (triggers night allowance)
        )

        # Commute Trip Logs (Day shift + Night shift)
        self.trip_day = ContractTripLog.objects.create(
            shift=self.shift_day,
            date=self.from_date + datetime.timedelta(days=2),
            vehicle=self.vehicle,
            driver=self.driver,
            status='completed',
            passenger_count=6,
            opening_km=54000,
            closing_km=54030, # 30 km actual
            driver_bata=Decimal('400.00'),
            toll_parking_charges=Decimal('120.00')
        )

        self.trip_night = ContractTripLog.objects.create(
            shift=self.shift_night,
            date=self.from_date + datetime.timedelta(days=2),
            vehicle=self.vehicle,
            driver=self.driver,
            status='completed',
            passenger_count=5,
            opening_km=54030,
            closing_km=54060, # 30 km actual
            driver_bata=Decimal('400.00'),
            toll_parking_charges=Decimal('60.00')
        )

    def test_contract_billing_studio_view(self):
        """Verify Contract Billing Studio renders tariff cards, KPIs, and invoices ledger."""
        resp = self.client.get('/billing/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Contract Tariff &amp; Monthly Revenue Studio")
        self.assertContains(resp, "Total Contract Revenue")
        self.assertContains(resp, "Cognizant Technologies")
        self.assertContains(resp, "Fixed Monthly Lump Sum")

    def test_reconcile_monthly_contract_fixed_monthly(self):
        """Verify reconciliation computes base fixed amount, tolls, and taxes."""
        rec = ContractBillingEngine.reconcile_monthly_contract(
            contract_id=self.contract_fixed.id,
            year=self.year,
            month=self.month
        )
        self.assertEqual(rec["total_trips_completed"], 2)
        self.assertEqual(rec["base_contract_amount"], 220000.00)
        self.assertEqual(rec["toll_parking_amount"], 180.00) # 120 + 60
        self.assertGreater(rec["grand_total"], rec["base_contract_amount"])

    def test_reconcile_monthly_contract_per_km(self):
        """Verify reconciliation computes kms * rate for per_km billing model."""
        route_km = Route.objects.create(
            contract=self.contract_per_km,
            name="Route KM",
            origin="A",
            destination="B",
            distance_km=40.0
        )
        shift_km = Shift.objects.create(route=route_km, shift_name="S1", direction="inbound", timing=datetime.time(9, 0))
        ContractTripLog.objects.create(
            shift=shift_km,
            date=self.from_date + datetime.timedelta(days=5),
            vehicle=self.vehicle,
            driver=self.driver,
            status='completed',
            passenger_count=4,
            opening_km=50000,
            closing_km=50100 # 100 km * 25 rate = 2500
        )
        rec = ContractBillingEngine.reconcile_monthly_contract(
            contract_id=self.contract_per_km.id,
            year=self.year,
            month=self.month
        )
        self.assertEqual(rec["total_kms_run"], 100.0)
        self.assertEqual(rec["base_contract_amount"], 2500.00)

    def test_fuel_escalation_calculation(self):
        """Verify fuel escalation factors in diesel price delta."""
        # Base diesel: 92.00, Prevailing diesel: 97.00 -> Delta = 5.00
        # Fuel factor: 0.20, Total kms: 60 -> Escalation = 5.00 * 0.20 * 60 = 60.00
        rec = ContractBillingEngine.reconcile_monthly_contract(
            contract_id=self.contract_fixed.id,
            year=self.year,
            month=self.month,
            prevailing_diesel_price=Decimal('97.00')
        )
        self.assertEqual(rec["fuel_delta"], 5.00)
        self.assertEqual(rec["fuel_escalation_amount"], 60.00)

    def test_sla_penalty_deduction(self):
        """Verify approved SLA penalty is deducted from taxable invoice value."""
        ContractSLAPenalty.objects.create(
            contract=self.contract_fixed,
            trip_log=self.trip_day,
            date=self.from_date + datetime.timedelta(days=2),
            penalty_type="delay_over_15m",
            penalty_amount=Decimal('1500.00'),
            description="Late arrival by 24 minutes due to flat tire",
            waived=False
        )
        rec = ContractBillingEngine.reconcile_monthly_contract(
            contract_id=self.contract_fixed.id,
            year=self.year,
            month=self.month
        )
        self.assertEqual(rec["sla_penalty_deduction"], 1500.00)
        self.assertEqual(rec["penalties_count"], 1)

    def test_generate_monthly_invoice_and_gst_invoice(self):
        """Verify generate_monthly_invoice creates ContractMonthlyInvoice & CorporateGSTInvoice with QR code."""
        res = ContractBillingEngine.generate_monthly_invoice(
            contract_id=self.contract_fixed.id,
            year=self.year,
            month=self.month
        )
        self.assertEqual(res["status"], "success")

        # Check ContractMonthlyInvoice
        monthly_inv = ContractMonthlyInvoice.objects.get(id=res["monthly_invoice_id"])
        self.assertEqual(monthly_inv.status, "generated")
        self.assertGreater(monthly_inv.grand_total, Decimal('200000.00'))

        # Check CorporateGSTInvoice
        gst_inv = CorporateGSTInvoice.objects.get(id=res["gst_invoice_id"])
        self.assertEqual(gst_inv.invoice_number, monthly_inv.invoice_number)
        self.assertEqual(gst_inv.sac_code, "9966")
        self.assertIn("UPI://PAY", gst_inv.qr_code_data)
        self.assertGreaterEqual(gst_inv.line_items.count(), 1)

    def test_driver_commute_bhatta_calculation(self):
        """Verify driver bhatta calculation accounts for base bhatta and night shift allowance."""
        calc = ContractBillingEngine.calculate_driver_commute_bhatta(
            driver_id=self.driver.id,
            from_date=self.from_date,
            to_date=self.to_date
        )
        self.assertEqual(calc["total_shifts"], 2)
        self.assertEqual(calc["standard_bata"], 800.00) # 400 + 400
        self.assertEqual(calc["night_allowance"], 250.00) # 23:00 night drop bonus
        self.assertEqual(calc["total_earnings"], 1050.00) # 800 + 250
        self.assertEqual(calc["net_payable"], 1050.00)

    def test_driver_commute_bhatta_view(self):
        """Verify driver commute bhatta UI ledger renders."""
        resp = self.client.get('/billing/driver-bhatta/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Chauffeur Duty Bhatta &amp; Allowance Ledger")
        self.assertContains(resp, "Murugan K.")

    def test_api_billing_generate_invoice(self):
        """Verify REST API triggers invoice generation."""
        resp = self.client.post(
            '/contracts/api/billing/generate-invoice/',
            data=json.dumps({
                'contract_id': self.contract_fixed.id,
                'year': self.year,
                'month': self.month,
                'force_recreate': True
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_api_billing_settle_bhatta(self):
        """Verify REST API commits bhatta settlement to DriverAllowanceLedger."""
        resp = self.client.post(
            '/contracts/api/billing/settle-bhatta/',
            data=json.dumps({
                'driver_id': self.driver.id,
                'from_date': self.from_date.strftime('%Y-%m-%d'),
                'to_date': self.to_date.strftime('%Y-%m-%d'),
                'payment_mode': 'upi',
                'reference': 'UPI-REF-9921023'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        # Verify ledger
        ledger = DriverAllowanceLedger.objects.filter(driver=self.driver).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.payment_reference, 'UPI-REF-9921023')

