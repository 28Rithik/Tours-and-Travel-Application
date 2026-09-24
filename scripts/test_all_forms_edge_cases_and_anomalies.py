import os
import sys
import datetime
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

import logging
logging.getLogger('django.request').setLevel(logging.CRITICAL)

from django.contrib.admin.sites import site
from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

from operations.models import Booking, Trip, BulkContract, TrafficFine
from operations.forms import BookingForm, TripForm
from statements.forms import StatementForm
from crm.models import Quotation, Inquiry, HotelMaster, SupplierProfile
from fleet_contracts.models import TransportContract, ContractSLAPenalty, ContractMonthlyInvoice
from packages.models import Package, PackageAddon, PackageHotelAllotment, PackageVehicleTariff
from finance.models import TripExpense, DriverAdvance, DriverSalaryProfile, FuelRecord
from maintenance.models import VehicleAsset, PartInventory, PreTripInspectionChecklist
from core.models import Vehicle, Driver, Party, VehicleType


class ComprehensiveFormAndAnomalyVerifier:
    def __init__(self):
        self.factory = RequestFactory()
        self.client = Client(raise_request_exception=False)
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('anomaly_tester', 'tester@travel.com', 'adminpass123')
        self.client.force_login(self.admin_user)
        self.total_tests = 0
        self.passed_tests = 0
        self.anomalies_detected = []

    def assert_test(self, condition, title, details=""):
        self.total_tests += 1
        if condition:
            self.passed_tests += 1
            extra = f" -> {details}" if details else ""
            print(f"  [PASS] {title}{extra}")
        else:
            self.anomalies_detected.append(f"{title}: {details}")
            print(f"  [FAIL] {title} - {details}")

    def run_all(self):
        start_time = timezone.now()
        print("\n" + "=" * 80)
        print("🔍 ENTERPRISE BACKEND ANOMALY & DEEP EDGE-CASE VERIFICATION SUITE")
        print("=" * 80)

        # ----------------------------------------------------------------------
        # PHASE 1: ALL 136 ADMIN MODELFORMS INITIALIZATION & EMPTY DATA VALIDATION
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("📋 PHASE 1: ALL 136 ADMIN MODELFORMS & INLINES DEEP INITIALIZATION")
        print("=" * 80)
        request = self.factory.get('/admin/')
        request.user = self.admin_user

        all_models = sorted(list(site._registry.keys()), key=lambda m: f"{m._meta.app_label}.{m.__name__}")
        print(f"Discovered {len(all_models)} registered models in admin.site._registry...")

        for model in all_models:
            model_name = f"{model._meta.app_label}.{model.__name__}"
            model_admin = site._registry[model]

            # 1.1 Form class generation
            try:
                form_class = model_admin.get_form(request)
                self.assert_test(form_class is not None, f"Form Generated: {model_name}")
            except Exception as e:
                self.assert_test(False, f"Form Generation Failed: {model_name}", str(e))
                continue

            # 1.2 Empty POST data validation (must not throw unhandled 500 exceptions)
            try:
                empty_form = form_class(data={})
                is_valid = empty_form.is_valid()
                errors = empty_form.errors
                self.assert_test(isinstance(errors, dict), f"Empty Form Clean Validation: {model_name}", f"is_valid={is_valid}, error_fields={len(errors)}")
            except Exception as e:
                self.assert_test(False, f"Empty Form Crash: {model_name}", str(e))

            # 1.3 Inlines generation & formset instantiation
            try:
                inlines = model_admin.get_inline_instances(request)
                inline_count = len(inlines)
                inlines_ok = True
                for inline in inlines:
                    formset_class = inline.get_formset(request)
                    if formset_class is None:
                        inlines_ok = False
                self.assert_test(inlines_ok, f"Inlines Resolution ({inline_count} inlines): {model_name}")
            except Exception as e:
                self.assert_test(False, f"Inlines Resolution Error: {model_name}", str(e))

        # ----------------------------------------------------------------------
        # PHASE 2: ADVERSARIAL BOUNDARY DATA INJECTION INTO ADMIN FORMS
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("💥 PHASE 2: ADVERSARIAL & BOUNDARY DATA INJECTION TESTING")
        print("=" * 80)
        
        adversarial_payloads = [
            ("Extreme negative numbers", {"amount": -9999999, "quoted_price": -50000, "km_rate": -100, "expected_km": -999}),
            ("XSS / Script Injection", {"name": "<script>alert('xss')</script>", "guest_name": "<b>Injected</b>", "notes": "'; DROP TABLE trips;--"}),
            ("Massive string length overflow", {"guest_name": "A" * 5000, "pickup_location": "B" * 5000, "destination": "C" * 5000}),
            ("Malformed / Inverted dates", {"pickup_date": "invalid-date", "drop_date": "2010-01-01", "start_date": "2030-01-01", "end_date": "2020-01-01"}),
            ("Null byte & control characters", {"guest_name": "Guest\x00Name", "notes": "Control\x01\x02\x03"}),
        ]

        # Test on BookingForm
        for label, payload in adversarial_payloads:
            try:
                b_form = BookingForm(data=payload)
                valid = b_form.is_valid()
                errors = b_form.errors
                self.assert_test(not valid and len(errors) > 0, f"BookingForm Adversarial Rejection ({label})", f"errors_caught={list(errors.keys())}")
            except Exception as e:
                self.assert_test(False, f"BookingForm Crashed on {label}", str(e))

        # Test on TripForm
        for label, payload in adversarial_payloads:
            try:
                t_form = TripForm(data=payload)
                valid = t_form.is_valid()
                errors = t_form.errors
                self.assert_test(not valid and len(errors) > 0, f"TripForm Adversarial Rejection ({label})", f"errors_caught={list(errors.keys())}")
            except Exception as e:
                self.assert_test(False, f"TripForm Crashed on {label}", str(e))

        # Test on StatementForm
        for label, payload in adversarial_payloads:
            try:
                s_form = StatementForm(data=payload)
                valid = s_form.is_valid()
                errors = s_form.errors
                self.assert_test(not valid and len(errors) > 0, f"StatementForm Adversarial Rejection ({label})", f"errors_caught={list(errors.keys())}")
            except Exception as e:
                self.assert_test(False, f"StatementForm Crashed on {label}", str(e))

        # ----------------------------------------------------------------------
        # PHASE 3: COMPUTED PROPERTY ANOMALIES & ZERO-DIVISION AUDIT
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("➗ PHASE 3: COMPUTED PROPERTIES, ZERO-DIVISION & NULL SAFETY AUDIT")
        print("=" * 80)

        # 3.1 Quotation with 0 pax & 0 days
        try:
            q_zero = Quotation(pax_count=0, total_quoted_price=Decimal('50000.00'), destination='Munnar')
            pax_price = q_zero.per_pax_price
            self.assert_test(pax_price == Decimal('50000.00'), "Quotation: 0 Pax fallback handles division cleanly", f"per_pax={pax_price}")
            
            # String representation with None price
            q_none = Quotation(quotation_number='QT-TEST-NONE', total_quoted_price=None, destination='Ooty')
            str_repr = str(q_none)
            self.assert_test('₹0.00' in str_repr, "Quotation: __str__ handles None total_quoted_price cleanly", f"str={str_repr}")
        except Exception as e:
            self.assert_test(False, "Quotation Edge Case Exception", str(e))

        # 3.2 Trip with None guest_name, None booking, opening_km > closing_km
        try:
            t_edge = Trip(
                guest_name=None,
                booking=None,
                opening_km=15000,
                closing_km=14500, # Inverted / rollover odometer
                fixed_amount=Decimal('12000.00')
            )
            # Verify used_km clamps to 0
            self.assert_test(t_edge.used_km == 0, "Trip: Inverted odometer (closing < opening) clamps to 0 km", f"used_km={t_edge.used_km}")
            # Verify customer_confirmation_message doesn't throw TypeError on None guest_name
            conf_msg = t_edge.customer_confirmation_message
            self.assert_test("Hello Valued Guest" in conf_msg, "Trip: customer_confirmation_message handles null guest_name & booking cleanly")
            # Verify handover_message doesn't throw AttributeError on None booking
            hand_msg = t_edge.handover_message
            self.assert_test("Trip Details:" in hand_msg, "Trip: handover_message handles null booking cleanly")
            # Verify final_bill_message handles nulls
            bill_msg = t_edge.final_bill_message
            self.assert_test("Total Bill Value:" in bill_msg, "Trip: final_bill_message handles nulls cleanly")
        except Exception as e:
            self.assert_test(False, "Trip Edge Case Exception", str(e))

        # 3.3 ContractSLAPenalty & MonthlyInvoice __str__ with None amounts and null contracts
        try:
            penalty_none = ContractSLAPenalty(penalty_amount=None, contract=None)
            p_str = str(penalty_none)
            self.assert_test("No Contract" in p_str and "₹0" in p_str, "ContractSLAPenalty: __str__ handles null contract & None amount cleanly", f"str={p_str}")

            inv_none = ContractMonthlyInvoice(grand_total=None, contract=None, invoice_number='INV-DRAFT')
            inv_str = str(inv_none)
            self.assert_test("No Contract" in inv_str and "₹0" in inv_str, "ContractMonthlyInvoice: __str__ handles null contract & None grand_total cleanly", f"str={inv_str}")
        except Exception as e:
            self.assert_test(False, "Fleet Contract Model __str__ Exception", str(e))

        # 3.4 PackageAddon with None selling_price
        try:
            addon_none = PackageAddon(title="Jeep Safari", selling_price=None, cost_price=None)
            self.assert_test(addon_none.margin_per_unit == 0, "PackageAddon: margin_per_unit handles None selling_price & cost_price")
            self.assert_test(addon_none.margin_percentage == 0.0, "PackageAddon: margin_percentage handles None selling_price without zero-division")
            addon_str = str(addon_none)
            self.assert_test("₹0" in addon_str, "PackageAddon: __str__ handles None selling_price cleanly", f"str={addon_str}")
        except Exception as e:
            self.assert_test(False, "PackageAddon Edge Case Exception", str(e))

        # 3.5 FuelRecord with 0 fuel_quantity and inverted km
        try:
            fuel_zero = FuelRecord(opening_km=1000, closing_km=900, fuel_quantity=0)
            self.assert_test(fuel_zero.distance == 0, "FuelRecord: Inverted km clamped to 0 distance")
            self.assert_test(fuel_zero.mileage == 0, "FuelRecord: 0 fuel_quantity safely returns 0 mileage without ZeroDivisionError")
        except Exception as e:
            self.assert_test(False, "FuelRecord Zero Division Exception", str(e))

        # 3.6 VehicleAsset with 0 expected life km
        try:
            asset_zero = VehicleAsset(asset_type='tyre', installed_odometer=0, expected_life_km=0)
            # Check maintenance display logic
            from maintenance.admin import VehicleAssetAdmin
            admin_inst = VehicleAssetAdmin(VehicleAsset, site)
            health = admin_inst.replacement_alert(asset_zero)
            self.assert_test("N/A" in str(health), "VehicleAsset: 0 expected_life_km gracefully displays 'N/A' without ZeroDivisionError")
        except Exception as e:
            self.assert_test(False, "VehicleAsset Zero Division Exception", str(e))

        # ----------------------------------------------------------------------
        # PHASE 4: POST ENDPOINTS & VIEWS STRESS & SECURITY CHECKS
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("🛡️ PHASE 4: POST VIEWS & ENDPOINTS STRESS & SECURITY INTEGRITY")
        print("=" * 80)

        # 4.1 Telematics ping with extreme out-of-range GPS coords
        resp = self.client.post('/operations/api/telematics/ping/', data={
            'vehicle': 999999, # non-existent vehicle
            'latitude': 999.999, # out of range lat
            'longitude': -888.888, # out of range lon
            'speed_kmh': -50
        })
        self.assert_test(resp.status_code in [400, 404], "Telematics API: Rejects invalid vehicle & out-of-range GPS without 500", f"status={resp.status_code}")

        # 4.2 Statement generation POST with inverted date range
        resp = self.client.post('/statements/generate/', data={
            'statement_type': 'party',
            'party': 1,
            'from_date': '2026-12-31',
            'to_date': '2026-01-01', # inverted range
            'file_format': 'pdf'
        })
        self.assert_test(resp.status_code in [200, 400], "Statements View: Handles inverted date range cleanly without 500", f"status={resp.status_code}")

        # 4.3 Driver Inspection POST with empty / corrupted form
        resp = self.client.post('/driver/inspection/', data={})
        self.assert_test(resp.status_code in [200, 302, 400], "Driver Inspection: Empty POST handled without 500 crash", f"status={resp.status_code}")

        # 4.4 Driver SOS POST with invalid / missing payload
        resp = self.client.post('/driver/sos/', data={})
        self.assert_test(resp.status_code in [200, 302, 400], "Driver SOS: Empty POST handled gracefully without 500", f"status={resp.status_code}")

        # 4.5 Customer checkout POST with empty data
        resp = self.client.post('/customer/checkout/999999/', data={})
        self.assert_test(resp.status_code in [200, 302, 404], "Customer Checkout: Non-existent package handled safely", f"status={resp.status_code}")

        # 4.6 Read-only admin add attempts (Security / Permission enforcement)
        readonly_adds = [
            ('/admin/enterprise_governance/auditlogentryproxy/add/', 'AuditLogEntryProxy'),
            ('/admin/operations/vehicletelematicsping/add/', 'VehicleTelematicsPing'),
            ('/admin/digital_services/paymentwebhookeventproxy/add/', 'PaymentWebhookEventProxy'),
            ('/admin/finance_treasury/tripprofitreport/add/', 'TripProfitReport'),
        ]
        for url, name in readonly_adds:
            resp = self.client.get(url)
            self.assert_test(resp.status_code == 403, f"Security Boundary Check (403 Forbidden for Read-Only Add): {name}", f"url={url}")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        print("\n" + "=" * 80)
        print("🎯 ENTERPRISE ANOMALY & EDGE-CASE SUITE EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Total Deep Verification Checks: {self.passed_tests}/{self.total_tests}")
        print(f"Total Anomalies / Exceptions: {len(self.anomalies_detected)}")
        if self.anomalies_detected:
            for anomaly in self.anomalies_detected:
                print(f"  ❌ {anomaly}")
        else:
            print("  ✅ 100% OF ALL FORMS, INLINES, AND COMPUTED PROPERTIES HANDLED WITH ZERO ANOMALIES!")
        print(f"⏱️ EXECUTION TIME: {duration:.2f} seconds")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    ComprehensiveFormAndAnomalyVerifier().run_all()
