import os
import sys
import json
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

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.contrib.admin.sites import site
from django.urls import reverse
from django.core.management import call_command
from django.utils import timezone

# Model Imports
from core.models import Vehicle, VehicleType, Driver, Cleaner, LicenseClass, Client as CoreClient, Supplier as CoreSupplier, RateCard, Party
from operations.models import Booking, Trip, BulkContract, BulkContractDay, VehicleTelematicsPing, EmergencyIncidentAlert, DriverBehaviorLog, GeofenceZone, TrafficFine
from packages.models import (
    Package, PackageSeasonalRate, PackageHotelAllotment, PackageVehicleTariff,
    PackageTemplate, ItineraryDay, TempleDarshanSlot, InternationalDocumentChecklist,
    PackageAddon, PackageB2BMargin, TourFeedbackLog, CollegeIVExpedition, TourPassengerManifest,
    PackageInventory
)
from packages.manifest_autoassign import auto_assign_for_expedition
from fleet_contracts.models import (
    TransportContract, ContractFleetRoster, CommuterManifest, ContractTripLog,
    NightSafetyEscortLog, ContractSLAPenalty, ContractMonthlyInvoice
)
from fleet_commute.models import CommuteRoute, RouteStop, CommuteShift, DailyTripLog
from maintenance.models import (
    VehicleAsset, PreTripInspectionChecklist, DefectTicket, ServiceReminder, ServiceRecord, PartInventory
)
from maintenance_compliance.models import ComplianceDocument, InsuranceClaim
from maintenance.services import check_compliance_expiries, check_preventive_maintenance_due, send_compliance_renewal_warnings_alert
from driver_portal.models import DriverPortalAccount
from analytics.models import DriverScorecard, ReportLog
from finance.models import TripExpense, DriverAdvance, DriverSettlement, SupplierTripCost
from finance_fleet.models import FuelRecord, CorporatePetroAccount, CorporateFastagAccount, FastagTollDeduction
from finance_payroll.models import DriverSalaryProfile, DriverPayslip, EmployeePayment
from finance_treasury.models import Payment, VehicleLoan, LedgerAdjustment, TripProfitReport
from crm.models import (
    Inquiry, InquiryFollowUp, Quotation, QuotationDay, QuotationItem,
    HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster,
    PartnerProfile, B2CCustomerProfile, SupplierProfile, SupplierContractedRate,
    SupplierServiceVoucher, DmcTask, FlightMaster, DmcDocument, TravelComplaint,
    SupplierPaymentRequisition, DmcInvoice
)
from enterprise_governance.models import SupplierContractProxy, CommissionRuleProxy, AuditLogEntryProxy
from operations.forms import BookingForm, TripForm
from statements.forms import StatementForm
from statements.models import GeneratedStatement
from integrations.communication import send_whatsapp_message, send_email_notification


class SystemE2EVerifier:
    def __init__(self):
        self.client = Client(enforce_csrf_checks=False)
        self.factory = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('e2e_admin', 'e2e@example.com', 'adminpass123')
        self.client.force_login(self.admin_user)
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0

    def assert_check(self, condition, phase_name, test_title, details=""):
        self.total_tests += 1
        if phase_name not in self.results:
            self.results[phase_name] = {'passed': 0, 'failed': 0, 'tests': []}

        if condition:
            self.passed_tests += 1
            self.results[phase_name]['passed'] += 1
            det = f" -> {details}" if details else ""
            print(f"  [PASS] {test_title}{det}")
            self.results[phase_name]['tests'].append((test_title, True, details))
        else:
            self.results[phase_name]['failed'] += 1
            print(f"  [FAIL] {test_title} - {details}")
            self.results[phase_name]['tests'].append((test_title, False, details))
            raise AssertionError(f"Test failed in {phase_name}: {test_title} - {details}")

    def verify_admin_forms_for_models(self, models_list, phase_name):
        request = self.factory.get('/admin/')
        request.user = self.admin_user
        for model in models_list:
            admin_obj = site._registry.get(model)
            self.assert_check(admin_obj is not None, phase_name, f"Admin registered for {model.__name__}", f"app={model._meta.app_label}")
            form_class = admin_obj.get_form(request)
            self.assert_check(form_class is not None, phase_name, f"Admin form resolved for {model.__name__}")
            form_inst = form_class()
            has_fields = (hasattr(form_inst, 'fields') and len(form_inst.fields) > 0) or (len(admin_obj.get_readonly_fields(request)) > 0)
            self.assert_check(has_fields, phase_name, f"Admin form fields verified for {model.__name__}", f"field_count={len(form_inst.fields)}, readonly_count={len(admin_obj.get_readonly_fields(request))}")

    # =========================================================================
    # PHASE 1: Commercial Sales Pipeline, CRM & Quotation Engine, Billing & Invoicing
    # =========================================================================
    def run_phase_1(self):
        phase = "Phase 1: CRM, Quotation Engine & Invoicing"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 1.1 Verify Admin Forms for CRM models
        crm_models = [
            Inquiry, Quotation, DmcInvoice, DmcTask, PartnerProfile, B2CCustomerProfile,
            SupplierProfile, SupplierContractedRate, SupplierServiceVoucher, SupplierPaymentRequisition,
            HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster,
            FlightMaster, DmcDocument, TravelComplaint
        ]
        self.verify_admin_forms_for_models(crm_models, phase)

        # 1.2 Inquiry Pipeline View
        resp = self.client.get('/crm/queries/')
        self.assert_check(resp.status_code == 200, phase, "GET /crm/queries/ pipeline dashboard returns 200")
        resp = self.client.get('/crm/inquiries/')
        self.assert_check(resp.status_code == 200, phase, "GET /crm/inquiries/ pipeline alias returns 200")

        # 1.3 Inquiry Create Model & Data Flow
        party = CoreClient.objects.first()
        inq = Inquiry.objects.create(
            party=party,
            guest_name='E2E Test Corporate Lead',
            guest_phone='+91 98401 22334',
            guest_email='lead@e2etest.com',
            source='website',
            pickup_location='Coimbatore Junction',
            destination='Ooty & Kodaikanal',
            pickup_date=datetime.date.today() + datetime.timedelta(days=10),
            pickup_time=datetime.time(9, 0),
            drop_date=datetime.date.today() + datetime.timedelta(days=14),
            adult_count=4,
            priority='high',
            special_requirements='End to end validation inquiry',
        )
        self.assert_check(inq is not None and bool(inq.inquiry_number), phase, "Inquiry saved in database", f"inquiry_number={inq.inquiry_number}")

        # 1.4 Quotation Builder & Submission
        q_data = {
            'party': party.id,
            'title': 'E2E Custom Hill Station Tour',
            'destination': 'Ooty & Kodaikanal',
            'start_date': str(datetime.date.today() + datetime.timedelta(days=10)),
            'end_date': str(datetime.date.today() + datetime.timedelta(days=14)),
            'pax_count': 4,
            'markup_percent': '15.00',
            'gst_rate': '5.00',
        }
        resp = self.client.post(f'/crm/quotations/new/?inquiry_id={inq.id}', q_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /crm/quotations/new/ creates quotation")
        quote = Quotation.objects.filter(title='E2E Custom Hill Station Tour').order_by('-id').first()
        self.assert_check(quote is not None, phase, "Quotation saved in database", f"quote_no={quote.quotation_number if quote else 'None'}")

        # 1.5 Quotation Add Day & Add Item APIs
        resp = self.client.post(f'/crm/api/quotations/{quote.id}/add-day/', {
            'title': 'Day 1: Arrival & Ooty Lake Tour',
            'overnight_destination': 'Ooty',
            'description': 'Check in at Sterling Resort and evening boat ride.',
            'hotel_meal_plan': 'CP'
        })
        self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /crm/api/quotations/<id>/add-day/ adds itinerary day")

        resp = self.client.post(f'/crm/api/quotations/{quote.id}/add-item/', {
            'category': 'transport',
            'item_name': 'Innova Crysta 4 Days Coach',
            'quantity': 1,
            'unit_cost': '14000.00'
        })
        self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /crm/api/quotations/<id>/add-item/ adds transport cost")

        quote.refresh_from_db()
        self.assert_check(quote.net_cost >= Decimal('14000.00'), phase, "Quotation net cost recalculated", f"net_cost=₹{quote.net_cost}")

        # 1.6 Quotation Preview & Convert to Booking
        resp = self.client.get(f'/crm/quotations/{quote.id}/preview/')
        self.assert_check(resp.status_code == 200, phase, "GET /crm/quotations/<id>/preview/ returns 200")

        # 1.7 DMC Task Creation & Toggle API
        task_data = {
            'title': 'E2E Verify Hotel Confirmation Voucher',
            'assigned_to': str(self.admin_user.id),
            'priority': 'high',
            'due_date': str(datetime.date.today() + datetime.timedelta(days=2)),
            'description': 'Verify voucher with hotelier',
            'related_inquiry': str(inq.id),
        }
        resp = self.client.post('/crm/api/tasks/create/', task_data)
        self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /crm/api/tasks/create/ creates task via API")
        task_id = resp.json().get('task_id')
        resp = self.client.post(f'/crm/api/tasks/{task_id}/toggle/')
        self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /crm/api/tasks/<id>/toggle/ toggles task status")

        # 1.8 Document Vault Upload API
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("test_tariff_agreement.pdf", b"%PDF-1.4 Mock PDF tariff document bytes", content_type="application/pdf")
        doc_data = {
            'title': 'E2E Tariff Master Agreement 2026',
            'category': 'contract_rate_sheet',
            'description': 'Uploaded by E2E master test suite',
            'document_file': mock_file,
        }
        resp = self.client.post('/crm/api/documents/upload/', doc_data)
        self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /crm/api/documents/upload/ uploads file to vault")

        # 1.9 Quality Complaint Lodging & Root-Cause Resolution
        supplier = SupplierProfile.objects.first()
        complaint_data = {
            'complainant_name': 'Dr. K. Swaminathan',
            'complainant_phone': '+91 94441 55667',
            'complainant_type': 'b2c_traveler',
            'category': 'hotel_quality',
            'severity': 'medium',
            'issue_description': 'AC cooling delayed in room 302 on night 1.',
            'supplier_involved': str(supplier.id if supplier else ''),
        }
        resp = self.client.post('/crm/complaints/lodge/', complaint_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /crm/complaints/lodge/ lodges grievance")
        complaint = TravelComplaint.objects.filter(complainant_name='Dr. K. Swaminathan').order_by('-id').first()
        self.assert_check(complaint is not None, phase, "TravelComplaint recorded in database", f"ticket={complaint.complaint_number if complaint else ''}")
        if complaint:
            res_payload = {
                'status': 'resolved',
                'resolution_notes': 'Complimentary buffet breakfast offered and room upgraded to Premier Suite.',
                'investigation_remarks': 'Compressor capacitor was serviced and replaced.',
                'supplier_rating': '4'
            }
            resp = self.client.post(f'/crm/api/complaints/{complaint.id}/resolve/', res_payload)
            self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /crm/api/complaints/<id>/resolve/ resolves complaint")

        # 1.10 Supplier Payment Requisition Payout Workflow
        req_data = {
            'supplier': str(supplier.id if supplier else ''),
            'amount_requested': '12500.00',
            'payment_type': 'full',
            'cost_to_company': '12500.00',
            'cost_to_client': '15500.00',
            'invoice_number': 'SUP-INV-2026-99',
            'notes': 'Advance for Nilgiri block booking',
        }
        resp = self.client.post('/crm/requisitions/create/', req_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /crm/requisitions/create/ creates payment requisition")
        req_obj = SupplierPaymentRequisition.objects.filter(invoice_number='SUP-INV-2026-99').order_by('-id').first()
        self.assert_check(req_obj is not None, phase, "SupplierPaymentRequisition saved in database")
        if req_obj:
            resp = self.client.post(f'/crm/api/requisitions/{req_obj.id}/update-status/', {'action': 'approve'})
            self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "Requisition approved via API")
            resp = self.client.post(f'/crm/api/requisitions/{req_obj.id}/update-status/', {'action': 'disburse', 'transaction_reference': 'UTR9988776655'})
            self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "Requisition disbursed with UTR logged via API")

        # 1.11 Commercial Invoicing Suite
        inv_data = {
            'invoice_type': 'tax_invoice',
            'party': str(party.id),
            'taxable_amount': '30000.00',
            'gst_rate': '5.00',
            'tax_regime': 'intra_state',
            'place_of_supply': 'Tamil Nadu (33)',
            'description_of_service': 'Custom Nilgiris Tour Operations',
        }
        resp = self.client.post('/crm/invoices/create/', inv_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /crm/invoices/create/ generates Tax Invoice")
        inv = DmcInvoice.objects.filter(party=party, taxable_amount=Decimal('30000.00')).order_by('-id').first()
        self.assert_check(inv is not None, phase, "DmcInvoice recorded in database", f"invoice_number={inv.invoice_number if inv else ''}")
        if inv:
            resp = self.client.get(f'/crm/invoices/{inv.id}/')
            self.assert_check(resp.status_code == 200, phase, "GET /crm/invoices/<id>/ printable invoice view returns 200")
            resp = self.client.post(f'/crm/api/invoices/{inv.id}/dispatch/')
            self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "Invoice dispatched via WhatsApp API")

        # 1.12 AR Aging & Reports Hub
        resp = self.client.get('/crm/reports/client-pending-payments/')
        self.assert_check(resp.status_code == 200, phase, "GET /crm/reports/client-pending-payments/ returns 200")
        sample_b = Booking.objects.first()
        if sample_b:
            resp = self.client.post('/crm/api/reports/send-payment-reminder/', {'booking_id': str(sample_b.id)})
            self.assert_check(resp.status_code in [200, 400], phase, "POST /crm/api/reports/send-payment-reminder/ handles reminder")
        resp = self.client.get('/crm/reports/')
        self.assert_check(resp.status_code == 200, phase, "GET /crm/reports/ destination turnover & executive hub returns 200")
        resp = self.client.get('/crm/reports/?export=destinations_csv')
        self.assert_check(resp.status_code == 200 and resp.get('Content-Type') == 'text/csv', phase, "Export destination reports to CSV returns 200")

    # =========================================================================
    # PHASE 2: Fleet Dispatch, Trips & Live Mission Control
    # =========================================================================
    def run_phase_2(self):
        phase = "Phase 2: Fleet Dispatch & Operations"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 2.1 Verify Admin Forms for Operations
        ops_models = [
            Booking, Trip, BulkContract, BulkContractDay, VehicleTelematicsPing,
            EmergencyIncidentAlert, DriverBehaviorLog, GeofenceZone, TrafficFine
        ]
        self.verify_admin_forms_for_models(ops_models, phase)

        # 2.2 Booking Form View & Submission
        # Mark previous test trips as completed to avoid scheduling conflict locks
        Trip.objects.filter(notes__icontains='E2E Phase 2').update(status='completed')

        test_start = datetime.date.today() + datetime.timedelta(days=3)
        test_end = datetime.date.today() + datetime.timedelta(days=6)

        resp = self.client.get('/bookings/create/')
        self.assert_check(resp.status_code == 200, phase, "GET /bookings/create/ returns 200")

        party = CoreClient.objects.first()
        vtype = VehicleType.objects.first()
        b_data = {
            'party': party.id,
            'guest_name': 'E2E Phase 2 Guest',
            'guest_phone': '+91 98409 88776',
            'pickup_location': 'Coimbatore Airport (CJB)',
            'destination': 'Valparai Tea Estates',
            'pickup_date': str(test_start),
            'pickup_time': '09:00',
            'reporting_time': '08:30',
            'drop_date': str(test_end),
            'journey_type': 'round_trip',
            'vehicle_type': vtype.id,
            'billing_type': 'package',
            'quoted_price': '18500.00',
            'status': 'confirmed',
            'hotel_confirmation_status': 'pending',
            'hotel_paid_by': 'company',
            'notes': 'E2E Phase 2 verified booking',
        }
        form = BookingForm(data=b_data)
        self.assert_check(form.is_valid(), phase, "BookingForm validation check passed", f"errors={form.errors.as_text() if form.errors else 'None'}")
        resp = self.client.post('/bookings/create/', b_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /bookings/create/ persists booking")
        booking = Booking.objects.filter(guest_name='E2E Phase 2 Guest').order_by('-id').first()
        self.assert_check(booking is not None, phase, "Booking saved in database", f"id={booking.id if booking else ''}")

        # 2.3 Trip Creation & Driver Assignment Form
        # Pick an unassigned driver and vehicle during the test window
        busy_drivers = Trip.objects.filter(
            status__in=['assigned', 'driver_confirmed', 'started'],
            start_date__lte=test_end,
            end_date__gte=test_start
        ).values_list('driver_id', flat=True)
        driver = Driver.objects.filter(status='active').exclude(id__in=busy_drivers).first() or Driver.objects.first()

        busy_vehicles = Trip.objects.filter(
            status__in=['assigned', 'driver_confirmed', 'started'],
            start_date__lte=test_end,
            end_date__gte=test_start
        ).values_list('vehicle_id', flat=True)
        compliant_vehs = Vehicle.objects.filter(status__in=['available', 'active']).exclude(id__in=busy_vehicles)
        compliant_vehs = compliant_vehs.exclude(
            fc_expiry__lt=test_end
        ).exclude(
            insurance_expiry__lt=test_end
        ).exclude(
            permit_expiry__lt=test_end
        ).exclude(
            pollution_expiry__lt=test_end
        )
        veh = compliant_vehs.first() or Vehicle.objects.filter(status='available').first()

        trip_data = {
            'vehicle': veh.id if veh else '',
            'driver': driver.id if driver else '',
            'status': 'assigned',
            'start_date': str(test_start),
            'end_date': str(test_end),
            'start_time': '09:00',
            'end_time': '18:00',
            'billing_model': 'fixed',
            'day_rate': '0.00',
            'km_rate': '0.00',
            'fixed_amount': '18500.00',
            'days_count': 3,
            'driver_bata': '1500.00',
            'partner_handover_notes': '',
            'notes': 'E2E Phase 2 assigned trip',
        }
        trip_form = TripForm(data=trip_data, instance=Trip(booking=booking, party=booking.party))
        self.assert_check(trip_form.is_valid(), phase, "TripForm validation check passed", f"errors={trip_form.errors.as_text() if trip_form.errors else 'None'}")
        resp = self.client.post(f'/bookings/{booking.id}/trip/create/', trip_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /bookings/<id>/trip/create/ dispatches trip")
        trip = Trip.objects.filter(booking=booking).order_by('-id').first()
        self.assert_check(trip is not None, phase, "Trip saved in database", f"trip_id={trip.id if trip else ''}")

        # 2.4 Trip Operational Views (Trip Sheet & Confirmation)
        if trip:
            resp = self.client.get(f'/trips/{trip.id}/')
            self.assert_check(resp.status_code == 200, phase, "GET /trips/<id>/ returns 200")
            resp = self.client.get(f'/trips/{trip.id}/trip-sheet/')
            self.assert_check(resp.status_code == 200, phase, "GET /trips/<id>/trip-sheet/ returns 200")
            resp = self.client.get(f'/trips/{trip.id}/customer-confirmation/')
            self.assert_check(resp.status_code == 200, phase, "GET /trips/<id>/customer-confirmation/ returns 200")

            # 2.5 Trip Status Transition API
            resp = self.client.post(f'/trips/{trip.id}/status/', {'status': 'started'})
            self.assert_check(resp.status_code in [200, 302], phase, "Trip transitioned to started")

            # 2.6 Public Live Passenger Tracking Link
            self.assert_check(bool(trip.tracking_token), phase, "Trip tracking_token generated", f"token={trip.tracking_token}")
            resp = self.client.get(f'/track/{trip.tracking_token}/')
            self.assert_check(resp.status_code == 200, phase, "GET /track/<token>/ passenger live view returns 200")
            resp = self.client.get(f'/api/track/{trip.tracking_token}/live/')
            self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "GET /api/track/<token>/live/ returns live GPS coordinates")

            # 2.7 WhatsApp Broadcast View
            resp = self.client.post(f'/trips/{trip.id}/broadcast-whatsapp/')
            self.assert_check(resp.status_code in [200, 302], phase, "WhatsApp trip broadcast triggers cleanly")

        # 2.8 Live Fleet Mission Control & Telematics Feed
        resp = self.client.get('/fleet/live/')
        self.assert_check(resp.status_code == 200, phase, "GET /fleet/live/ Mission Control returns 200")
        resp = self.client.get('/api/fleet/live-feed/')
        self.assert_check(resp.status_code == 200 and 'vehicles' in resp.json(), phase, "GET /api/fleet/live-feed/ returns JSON fleet feed")

        # 2.9 Telematics GPS Ping API
        if veh:
            ping_data = {
                'vehicle_id': veh.id,
                'latitude': 11.0168,
                'longitude': 76.9558,
                'speed': 55.4,
                'odometer': 124500,
                'ignition': True,
            }
            resp = self.client.post('/api/telematics/ping/', json.dumps(ping_data), content_type='application/json')
            self.assert_check(resp.status_code == 200 and resp.json().get('status') == 'success', phase, "POST /api/telematics/ping/ logs GPS ping")

        # 2.10 Statement Generation Form
        stmt_data = {
            'statement_type': 'party',
            'party': party.id,
            'from_date': str(datetime.date.today() - datetime.timedelta(days=30)),
            'to_date': str(datetime.date.today()),
            'file_format': 'pdf',
        }
        form = StatementForm(data=stmt_data)
        self.assert_check(form.is_valid(), phase, "StatementForm validation check passed", f"errors={form.errors.as_text() if form.errors else 'None'}")

    # =========================================================================
    # PHASE 3: Holiday Packages, Itinerary Catalog & Group Tours
    # =========================================================================
    def run_phase_3(self):
        phase = "Phase 3: Packages, Itinerary & Group Tours"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 3.1 Verify Admin Forms for Packages & Group Tours
        pkg_models = [
            Package, PackageSeasonalRate, PackageHotelAllotment, PackageVehicleTariff,
            PackageTemplate, ItineraryDay, TempleDarshanSlot, InternationalDocumentChecklist,
            PackageAddon, PackageB2BMargin, TourFeedbackLog
        ]
        self.verify_admin_forms_for_models(pkg_models, phase)

        # 3.2 Unit Economics & COGS Logic Verification
        test_pkg, _ = Package.objects.update_or_create(
            name="E2E Grand Kerala Backwaters & Munnar 5D",
            defaults={
                'destination': 'Munnar, Thekkady, Alleppey',
                'category': 'hill_station',
                'duration_nights': 4,
                'duration_days': 5,
                'min_pax': 40,
                'base_price': Decimal('12000.00'),
                'price_with_food': Decimal('14500.00'),
                'price_without_food': Decimal('10000.00'),
                'cost_hotel_per_pax': Decimal('4500.00'),
                'cost_coach_per_pax': Decimal('2500.00'),
                'cost_meals_per_pax': Decimal('2200.00'),
                'cost_activities_per_pax': Decimal('800.00'),
                'cost_misc_per_pax': Decimal('500.00'),
            }
        )
        self.assert_check(test_pkg.total_direct_cost_per_pax == Decimal('10500.00'), phase, "Direct COGS correctly summed to ₹10,500")
        self.assert_check(test_pkg.gross_margin_per_pax == Decimal('4000.00'), phase, "Gross margin per pax is ₹4,000")
        self.assert_check(round(test_pkg.gross_margin_percentage, 1) == 27.6, phase, "Gross margin % is 27.6%")
        self.assert_check(test_pkg.projected_batch_gross_profit == Decimal('160000.00'), phase, "Projected batch profit is ₹1,60,000 for 40 pax")

        # 3.3 Seasonal Rate Calculations
        season, _ = PackageSeasonalRate.objects.get_or_create(
            package=test_pkg,
            season_name="December Winter Carnival",
            defaults={
                'season_type': 'peak',
                'start_date': datetime.date(2025, 12, 15),
                'end_date': datetime.date(2026, 1, 5),
                'surge_percentage': Decimal('25.00'),
                'is_active': True,
            }
        )
        peak_rate = test_pkg.get_effective_price(travel_date=datetime.date(2025, 12, 25), with_food=True)
        self.assert_check(peak_rate == Decimal('14500.00') * Decimal('1.25'), phase, "Effective peak rate includes 25% surge", f"peak_rate=₹{peak_rate}")

        # 3.4 Hotel Room Allotment Occupancy
        allotment, _ = PackageHotelAllotment.objects.get_or_create(
            package=test_pkg,
            hotel_name="Fragrant Nature Munnar",
            check_in_date=datetime.date(2025, 12, 25),
            defaults={
                'check_out_date': datetime.date(2025, 12, 28),
                'room_category': 'deluxe',
                'rooms_blocked': 25,
                'rooms_occupied': 20,
                'cost_per_room_night': Decimal('4200.00'),
                'status': 'confirmed',
            }
        )
        self.assert_check(allotment.occupancy_rate == 80.0, phase, "Hotel occupancy rate is 80.0%")
        self.assert_check(allotment.rooms_available == 5, phase, "Available rooms is 5")

        # 3.5 College IV Auto-assignment Manifest Logic
        iv_exp, _ = CollegeIVExpedition.objects.get_or_create(
            college_name="Sri Krishna College of Engineering",
            department_and_batch="B.Tech Artificial Intelligence (2023-27)",
            defaults={
                'start_date': datetime.date(2025, 11, 10),
                'end_date': datetime.date(2025, 11, 14),
                'package': test_pkg,
                'faculty_incharge_name': "Prof. S. Karthikeyan",
                'faculty_incharge_phone': "+91 98433 11223",
                'student_count_male': 30,
                'student_count_female': 20,
                'faculty_count': 4,
                'total_pax': 54,
                'status': 'confirmed',
                'transit_mode': 'road_coach',
                'bus_count': 2,
            }
        )
        if TourPassengerManifest.objects.filter(iv_expedition=iv_exp).count() == 0:
            for i in range(1, 5):
                TourPassengerManifest.objects.create(
                    iv_expedition=iv_exp, passenger_name=f"Faculty Staff {i}",
                    category='faculty', gender='male' if i % 2 == 1 else 'female'
                )
            for i in range(1, 51):
                TourPassengerManifest.objects.create(
                    iv_expedition=iv_exp, passenger_name=f"Student {i:02d}",
                    category='student', gender='male' if i <= 30 else 'female', roll_number=f"23AI{i:03d}"
                )
        auto_res = auto_assign_for_expedition(iv_exp.id, seats_per_bus=45, students_per_room=4)
        self.assert_check('error' not in auto_res, phase, "College IV Manifest auto-assignment executed successfully", f"count={auto_res.get('total_passengers')}")

        # 3.6 Proposal Quotation & Voucher Views
        resp = self.client.get(f'/packages/quote/{test_pkg.id}/')
        self.assert_check(resp.status_code == 200, phase, "GET /packages/quote/<id>/ 5-page proposal returns 200")
        resp = self.client.get(f'/packages/voucher/{test_pkg.id}/')
        self.assert_check(resp.status_code == 200, phase, "GET /packages/voucher/<id>/ voucher view returns 200")
        resp = self.client.get(f'/packages/manifest/{iv_exp.id}/rooming-list/')
        self.assert_check(resp.status_code == 200, phase, "GET /packages/manifest/<id>/rooming-list/ returns 200")

    # =========================================================================
    # PHASE 4: Institutional Contracts, Employee Commute & Corporate Partners
    # =========================================================================
    def run_phase_4(self):
        phase = "Phase 4: Contracts, Commute & Corporate Partners"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 4.1 Verify Admin Forms for Contracts & Commute
        contracts_models = [
            TransportContract, ContractFleetRoster, CommuterManifest,
            ContractTripLog, NightSafetyEscortLog, ContractSLAPenalty, ContractMonthlyInvoice
        ]
        commute_models = [
            CommuteRoute, RouteStop, CommuteShift, DailyTripLog
        ]
        self.verify_admin_forms_for_models(contracts_models + commute_models, phase)

        # 4.2 Transport Contract Creation & Calculations
        client_obj = CoreClient.objects.first()
        contract, _ = TransportContract.objects.get_or_create(
            name="Cognizant Tech Park 24x7 Commute",
            defaults={
                'customer': client_obj,
                'contract_category': 'corporate',
                'billing_model': 'per_trip',
                'billing_cycle': 'calendar_month',
                'default_rate': Decimal('2800.00'),
                'committed_vehicle_count': 10,
                'standby_vehicle_count': 2,
                'start_date': datetime.date(2025, 1, 1),
                'end_date': datetime.date(2025, 12, 31),
                'fuel_escalation_enabled': True,
                'base_diesel_price': Decimal('94.00'),
                'fuel_revision_factor': Decimal('0.2500'),
                'status': 'active',
            }
        )
        self.assert_check(contract.status == 'active', phase, "Transport Contract is active", f"name={contract.name}")

        # 4.3 Dedicated Fleet Roster
        veh = Vehicle.objects.first()
        driver = Driver.objects.first()

        # Ensure vehicle and driver have valid compliance dates for roster
        veh.fc_expiry = datetime.date.today() + datetime.timedelta(days=180)
        veh.insurance_expiry = datetime.date.today() + datetime.timedelta(days=180)
        veh.save(update_fields=['fc_expiry', 'insurance_expiry'])
        driver.license_validity_tr = datetime.date.today() + datetime.timedelta(days=180)
        driver.save(update_fields=['license_validity_tr'])

        # Clear any prior active roster for this vehicle/driver to prevent double-booking conflict
        from django.db.models import Q
        ContractFleetRoster.objects.filter(Q(primary_vehicle=veh) | Q(primary_driver=driver)).update(is_active=False)

        roster, _ = ContractFleetRoster.objects.get_or_create(
            contract=contract,
            primary_vehicle=veh,
            defaults={
                'primary_driver': driver,
                'is_active': True,
                'notes': 'E2E dedicated shift allocation',
            }
        )
        roster.is_active = True
        roster.save(update_fields=['is_active'])
        self.assert_check(roster.is_active is True, phase, "Contract fleet roster assignment valid")

        # 4.4 Commute Route & Stops
        route, _ = CommuteRoute.objects.get_or_create(
            contract=contract,
            name="Route 14B - Gandhipuram to CHIL SEZ",
            defaults={
                'origin': 'Gandhipuram Central Bus Stand',
                'destination': 'CHIL SEZ IT Park Keeranatham',
                'distance_km': 19,
                'estimated_travel_minutes': 45,
                'is_active': True,
            }
        )
        stop, _ = RouteStop.objects.get_or_create(
            route=route,
            stop_order=1,
            defaults={
                'name': "Peelamedu PSG Tech Junction",
                'scheduled_offset_minutes': 12,
                'is_active': True,
            }
        )
        self.assert_check(route.name == "Route 14B - Gandhipuram to CHIL SEZ", phase, "CommuteRoute and RouteStops established")

        # 4.5 SLA Penalties Calculation
        sla_penalty, _ = ContractSLAPenalty.objects.get_or_create(
            contract=contract,
            date=datetime.date.today(),
            defaults={
                'penalty_type': 'late_arrival',
                'penalty_amount': Decimal('500.00'),
                'description': 'Reported 25 minutes late due to tyre puncture.',
                'waived': False,
            }
        )
        self.assert_check(sla_penalty.penalty_amount == Decimal('500.00'), phase, "ContractSLAPenalty verified")

    # =========================================================================
    # PHASE 5: Fleet Assets, Preventive Maintenance & RTO Safety Compliance
    # =========================================================================
    def run_phase_5(self):
        phase = "Phase 5: Fleet Maintenance & RTO Safety"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 5.1 Verify Admin Forms for Maintenance
        maint_models = [
            Vehicle, VehicleType, PreTripInspectionChecklist, DefectTicket,
            ServiceReminder, ServiceRecord, VehicleAsset, PartInventory,
            ComplianceDocument, InsuranceClaim
        ]
        self.verify_admin_forms_for_models(maint_models, phase)

        # 5.2 Pre-Trip Checklist Submission & Critical Defect Auto-Creation
        veh = Vehicle.objects.first()
        driver = Driver.objects.first()
        checklist = PreTripInspectionChecklist.objects.create(
            vehicle=veh,
            driver=driver,
            odometer_reading=145200,
            tyres_tread_and_pressure=False,  # Failed critical item
            brakes_functional=True,
            engine_oil_level=True,
            coolant_level=True,
            brake_fluid_level=True,
            battery_and_wiring=True,
            headlights_and_highbeam=True,
            taillights_and_brakelights=True,
            indicators_and_hazard=True,
            wipers_and_washer_fluid=True,
            horn_and_mirrors=True,
            first_aid_kit_present=True,
            fire_extinguisher_present=True,
            spare_wheel_and_jack=True,
            ac_or_fans_working=True,
            cabin_cleanliness=True,
            overall_status='failed',
            defect_notes='Front right tyre tread worn below 2mm legal limit.'
        )
        self.assert_check(checklist.overall_status == 'failed', phase, "PreTripInspectionChecklist recorded critical failure")

        # 5.3 Defect Ticket Lifecycle
        defect = DefectTicket.objects.filter(vehicle=veh).order_by('-id').first()
        if not defect:
            defect = DefectTicket.objects.create(
                vehicle=veh,
                reported_by=driver.name if driver else 'Duty Driver',
                description='Front right tyre replacement required immediately.',
                status='open'
            )
        self.assert_check(defect is not None, phase, "DefectTicket exists in open state")
        defect.status = 'resolved'
        defect.notes = 'Replaced with new Apollo Endurace tyre from central stock.'
        defect.resolved_date = datetime.date.today()
        defect.save(update_fields=['status', 'notes', 'resolved_date'])
        self.assert_check(defect.status == 'resolved', phase, "DefectTicket successfully resolved")

        # 5.4 Compliance & Maintenance Dashboard Views & APIs
        resp = self.client.get('/maintenance/compliance/')
        self.assert_check(resp.status_code == 200, phase, "GET /maintenance/compliance/ dashboard returns 200")
        resp = self.client.get('/maintenance/api/compliance-summary/')
        self.assert_check(resp.status_code == 200 and 'compliance_rate' in resp.json(), phase, "GET /maintenance/api/compliance-summary/ returns 200 JSON")
        resp = self.client.get('/maintenance/api/send-renewal-warnings/')
        self.assert_check(resp.status_code == 200 and resp.json().get('status') in ['dispatched', 'all_healthy'], phase, "GET /maintenance/api/send-renewal-warnings/ triggers alerts")

        # 5.5 RTO Expiry Watchdog & Hard-Lock Blocker Test
        # Create an expired vehicle document
        expired_veh = Vehicle.objects.filter(status='active').last() or Vehicle.objects.last()
        ComplianceDocument.objects.update_or_create(
            vehicle=expired_veh,
            document_type='fc',
            defaults={
                'document_number': 'FC-EXPIRED-TEST-999',
                'issue_date': datetime.date.today() - datetime.timedelta(days=400),
                'expiry_date': datetime.date.today() - datetime.timedelta(days=10),
            }
        )
        expired_veh.fc_expiry = datetime.date.today() - datetime.timedelta(days=10)
        expired_veh.save(update_fields=['fc_expiry'])
        exp_data = check_compliance_expiries(threshold_days=30)
        expired_veh_ids = [item['id'] for item in exp_data['expired'] if item.get('entity_type') == 'vehicle']
        self.assert_check(expired_veh.id in expired_veh_ids, phase, "RTO Watchdog identified vehicle with expired fitness certificate")

    # =========================================================================
    # PHASE 6: Crew Management, Driver Mobile Portal & Telematics Analytics
    # =========================================================================
    def run_phase_6(self):
        phase = "Phase 6: Crew, Driver Portal & Telematics"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 6.1 Verify Admin Forms for Crew & Driver Portal
        crew_models = [Driver, Cleaner, LicenseClass, DriverPortalAccount, DriverScorecard, ReportLog]
        self.verify_admin_forms_for_models(crew_models, phase)

        # 6.2 Driver Mobile Portal Authentication
        driver = Driver.objects.filter(status='active').first() or Driver.objects.first()
        self.assert_check(driver is not None, phase, "Active driver profile found", f"name={driver.name}")
        if not driver.phone:
            driver.phone = '+919876543210'
            driver.save(update_fields=['phone'])

        resp = self.client.get('/driver/login/')
        self.assert_check(resp.status_code == 200, phase, "GET /driver/login/ mobile portal returns 200")

        # Authenticate via driver login POST
        login_data = {
            'phone': driver.phone,
            'pin': '1234',
        }
        resp = self.client.post('/driver/login/', login_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /driver/login/ authenticates captain")

        # 6.3 Driver Dashboard View
        resp = self.client.get('/driver/')
        self.assert_check(resp.status_code == 200, phase, "GET /driver/ mobile dashboard returns 200")

        # 6.4 Driver Trip Execution Flow (Start, Checklist, SOS, End)
        trip = Trip.objects.filter(driver=driver).first()
        if not trip:
            trip = Trip.objects.first()
            trip.driver = driver
            trip.save(update_fields=['driver'])

        # Start Trip
        resp = self.client.post(f'/driver/trip/{trip.id}/start/', {'opening_km': '125000'})
        self.assert_check(resp.status_code in [200, 302], phase, "POST /driver/trip/<id>/start/ records start odometer")

        # Submit Inspection Checklist
        chk_data = {
            'vehicle_id': trip.vehicle.id if trip.vehicle else Vehicle.objects.first().id,
            'trip_id': trip.id,
            'odometer_reading': '125000',
            'tyres_tread_and_pressure': '1',
            'brakes_functional': '1',
            'engine_oil_level': '1',
            'coolant_level': '1',
            'brake_fluid_level': '1',
            'battery_and_wiring': '1',
            'headlights_and_highbeam': '1',
            'taillights_and_brakelights': '1',
            'indicators_and_hazard': '1',
            'wipers_and_washer_fluid': '1',
            'horn_and_mirrors': '1',
            'first_aid_kit_present': '1',
            'fire_extinguisher_present': '1',
            'spare_wheel_and_jack': '1',
            'ac_or_fans_working': '1',
            'cabin_cleanliness': '1',
        }
        resp = self.client.post('/driver/inspection/', chk_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /driver/inspection/ records mobile pre-trip check")

        # Trigger SOS Button
        sos_data = {
            'incident_type': 'sos_panic',
            'severity': 'critical',
            'description': 'E2E simulated emergency SOS button test',
            'latitude': '11.0168',
            'longitude': '76.9558',
        }
        resp = self.client.post('/driver/sos/', sos_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /driver/sos/ records emergency SOS alert")

        # End Trip
        end_data = {
            'closing_km': '125340',
            'trip_completion_notes': 'Safe arrival at depot.',
        }
        resp = self.client.post(f'/driver/trip/{trip.id}/end/', end_data)
        self.assert_check(resp.status_code in [200, 302], phase, "POST /driver/trip/<id>/end/ records final odometer & ends trip")

        # 6.5 Analytics & Driver Scorecards
        self.client.force_login(self.admin_user)
        resp = self.client.get('/analytics/dashboard/')
        self.assert_check(resp.status_code == 200, phase, "GET /analytics/dashboard/ returns 200")
        resp = self.client.get('/analytics/fleet/')
        self.assert_check(resp.status_code == 200, phase, "GET /analytics/fleet/ telematics analytics returns 200")

    # =========================================================================
    # PHASE 7: Finance, Fuel Operations, Cash Desk, Payroll & Accounts Payable
    # =========================================================================
    def run_phase_7(self):
        phase = "Phase 7: Finance, Fuel, Cash Desk & Payroll"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 7.1 Verify Admin Forms for Finance
        fin_models = [
            TripExpense, DriverAdvance, DriverSettlement, SupplierTripCost,
            FuelRecord, CorporatePetroAccount, CorporateFastagAccount, FastagTollDeduction,
            DriverSalaryProfile, DriverPayslip, EmployeePayment,
            Payment, VehicleLoan, LedgerAdjustment, TripProfitReport
        ]
        self.verify_admin_forms_for_models(fin_models, phase)

        # 7.2 Trip Cash Desk: Advance, Expense & Settlement
        trip = Trip.objects.first()
        driver = trip.driver if trip and trip.driver else Driver.objects.first()
        advance = DriverAdvance.objects.create(
            trip=trip,
            driver=driver,
            amount=Decimal('3000.00'),
            date=datetime.date.today(),
            notes='En-route diesel and toll cash advance'
        )
        self.assert_check(advance.amount == Decimal('3000.00'), phase, "DriverAdvance recorded")

        expense = TripExpense.objects.create(
            trip=trip,
            expense_type='toll',
            amount=Decimal('850.00'),
            date=datetime.date.today(),
            description='NH544 toll booth receipt'
        )
        self.assert_check(expense.amount == Decimal('850.00'), phase, "TripExpense recorded")

        settlement = DriverSettlement.objects.create(
            trip=trip,
            driver=driver,
            total_days=Decimal('1.00'),
            batta=Decimal('800.00'),
            advance_adjusted=Decimal('500.00'),
            settled_on=datetime.date.today()
        )
        expected_balance = settlement.batta + settlement.driver_expenses - settlement.advance_adjusted - settlement.cash_collected - settlement.traffic_fines_deduction
        self.assert_check(settlement.balance == expected_balance, phase, "DriverSettlement calculated and settled", f"balance=₹{settlement.balance}")

        # 7.3 Corporate Fuel & FASTag Logging
        veh = Vehicle.objects.first()
        fuel = FuelRecord.objects.create(
            vehicle=veh,
            date=datetime.date.today(),
            opening_km=146000,
            fuel_quantity=Decimal('45.00'),
            fuel_price=Decimal('93.50'),
            fuel_station='Indian Oil COCO Coimbatore'
        )
        self.assert_check(fuel.amount == Decimal('4207.50'), phase, "FuelRecord recorded with calculated amount", f"amount=₹{fuel.amount}")

        fastag_acc, _ = CorporateFastagAccount.objects.get_or_create(
            account_number="FASTAG-ICICI-001",
            defaults={'account_name': "ICICI Corporate Master Wallet", 'balance': Decimal('15000.00'), 'is_active': True}
        )
        toll_ded = FastagTollDeduction.objects.create(
            account=fastag_acc,
            vehicle=veh,
            date=timezone.now(),
            amount=Decimal('115.00'),
            toll_plaza="Kaniyur Toll Plaza NH544"
        )
        self.assert_check(toll_ded.amount == Decimal('115.00'), phase, "FastagTollDeduction recorded")

        # 7.4 Payroll Batch Run & Payslip View
        sal_profile, _ = DriverSalaryProfile.objects.get_or_create(
            driver=driver,
            defaults={
                'basic_salary': Decimal('22000.00'),
                'allowances': Decimal('3000.00'),
                'epf_number': 'EPF-100234',
                'esi_number': 'ESI-998822',
            }
        )
        resp = self.client.get('/finance/accounting/')
        self.assert_check(resp.status_code == 200, phase, "GET /finance/accounting/ returns 200")
        resp = self.client.get('/finance/export/tally/sales/')
        self.assert_check(resp.status_code == 200, phase, "GET /finance/export/tally/sales/ returns 200")

        # 7.5 Profitability Reports
        resp = self.client.get('/reports/vehicle-profitability/')
        self.assert_check(resp.status_code == 200, phase, "GET /reports/vehicle-profitability/ returns 200")
        resp = self.client.get('/reports/party-profitability/')
        self.assert_check(resp.status_code == 200, phase, "GET /reports/party-profitability/ returns 200")

    # =========================================================================
    # PHASE 8: Enterprise Governance, Security, User Access & End-to-End System Integration
    # =========================================================================
    def run_phase_8(self):
        phase = "Phase 8: Governance, Integration & Health"
        print(f"\n{'='*80}\n🌟 STARTING {phase.upper()}\n{'='*80}")

        # 8.1 Verify Admin Forms for Enterprise Governance & Auth
        gov_models = [SupplierContractProxy, CommissionRuleProxy, AuditLogEntryProxy, User]
        self.verify_admin_forms_for_models(gov_models, phase)

        # 8.2 Django Admin Portal Layout & Systemic Ordering
        resp = self.client.get('/admin/')
        self.assert_check(resp.status_code == 200, phase, "GET /admin/ admin portal index returns 200")
        content = resp.content.decode('utf-8', errors='ignore')
        self.assert_check("Travel ERP" in content or "TravelERP" in content or "Mission Control" in content, phase, "Enterprise Operations / Mission Control dashboard present")

        # 8.3 Razorpay Payment Gateway Webhook Receiver
        webhook_payload = {
            "id": f"evt_mock_e2e_{int(timezone.now().timestamp())}",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_mock_e2e_998811",
                        "amount": 250000,
                        "currency": "INR",
                        "status": "captured",
                        "notes": {
                            "reference_id": "BKG-NONEXISTENT-TEST"
                        }
                    }
                }
            }
        }
        resp = self.client.post('/payments/webhook/razorpay/', json.dumps(webhook_payload), content_type='application/json')
        self.assert_check(resp.status_code in [200, 400], phase, "Razorpay webhook endpoint processes incoming events safely")

        # 8.4 Event Trigger Engine: WhatsApp & Email Alerts
        wa_res = send_whatsapp_message(
            to_phone="+91 98401 22334",
            message_text="[E2E] Trip TRIP-E2E-101 confirmed. Vehicle: TN 38 BK 9988."
        )
        self.assert_check('status' in wa_res or 'messages' in wa_res, phase, "WhatsApp event notification triggered cleanly")

        mail_res = send_email_notification(
            to_email="dispatch@travelerp.com",
            subject="[E2E ALERT] Fleet Emergency Incident Logged",
            body_html="<p>Emergency alert triggered by test runner. All units standing by.</p>"
        )
        self.assert_check(mail_res is True, phase, "Email event notification alert triggered cleanly")

        # 8.5 Customer Portal Home
        resp = self.client.get('/customer-portal/')
        self.assert_check(resp.status_code == 200, phase, "GET /customer-portal/ returns 200")

        # 8.6 Django System Check (0 Issues)
        print("\n🩺 Running Django System Check across all installed apps...")
        try:
            call_command('check')
            system_check_clean = True
        except Exception as e:
            system_check_clean = False
            print(f"System check error: {e}")
        self.assert_check(system_check_clean, phase, "Django system check identified 0 issues")

    # =========================================================================
    # MASTER RUNNER
    # =========================================================================
    def run_all(self):
        start_time = timezone.now()
        print("\n" + "#" * 80)
        print("🚀 EXECUTING COMPLETE 8-PHASE SYSTEMIC BACKEND & CONNECTIVITY VERIFICATION")
        print("#" * 80)

        self.run_phase_1()
        self.run_phase_2()
        self.run_phase_3()
        self.run_phase_4()
        self.run_phase_5()
        self.run_phase_6()
        self.run_phase_7()
        self.run_phase_8()

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("📊 8-PHASE SYSTEM VERIFICATION SUMMARY REPORT")
        print("=" * 80)
        for phase, data in self.results.items():
            print(f"  ✓ {phase}: {data['passed']}/{data['passed'] + data['failed']} PASSED")

        print("-" * 80)
        print(f"🎯 TOTAL VERIFIED TESTS: {self.passed_tests}/{self.total_tests} PASSED (100% OK)")
        print(f"⏱️ EXECUTION TIME: {duration:.2f} seconds")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    verifier = SystemE2EVerifier()
    verifier.run_all()
