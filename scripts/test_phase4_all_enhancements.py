import calendar
import datetime
from decimal import Decimal
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client as TestClient, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from core.models import Driver, Party, Vehicle, VehicleType, Client as ClientModel
from operations.models import Booking, Trip, VehicleTelematicsPing, EmergencyIncidentAlert
from packages.models import Package, PackageInventory
from customer_portal.models import CustomerAccount
from maintenance.models import ServiceReminder, DefectTicket, VehicleAsset, ComplianceDocument
from maintenance.services import (
    check_compliance_expiries,
    verify_trip_dispatch_compliance,
    check_preventive_maintenance_due,
)
from integrations.communication import (
    dispatch_trip_assignment_alert,
    dispatch_emergency_sos_broadcast,
    dispatch_payslip_alert,
    send_whatsapp_message,
)
from finance.models import DriverSalaryProfile, DriverPayslip, Payment
from payments_gateway.models import PaymentWebhookEvent, InstallmentPlan
from crm.models import CommunicationLog


def run_phase4_verification():
    print("=" * 80)
    print("🚀 RUNNING PHASE 4: ENTERPRISE OPERATIONAL ENHANCEMENTS TEST SUITE")
    print("=" * 80)

    today = timezone.now().date()
    test_client = TestClient()

    # Setup admin user for authenticated endpoints
    admin_user, _ = User.objects.get_or_create(
        username='phase4_tester',
        defaults={'email': 'phase4@test.com', 'is_staff': True, 'is_superuser': True}
    )
    admin_user.set_password('pass123')
    admin_user.save()
    test_client.force_login(admin_user)

    # Fetch or create vehicle type
    vtype, _ = VehicleType.objects.get_or_create(
        name='Phase4 Luxury Coach',
        defaults={'seating_capacity': 35, 'default_km_rate': Decimal('28.00')}
    )

    # -------------------------------------------------------------------------
    # TEST 1: RTO COMPLIANCE EXPIRY WATCHDOG & DISPATCH SAFETY GATE
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: RTO Compliance Expiry Watchdog & Safety Gate ---")
    
    # Create test vehicle with distinct expiry timelines
    v_test, _ = Vehicle.objects.get_or_create(
        registration_number='TN38-TEST-9901',
        defaults={
            'brand': 'BharatBenz',
            'model': 'Glider 12M',
            'seating_capacity': 35,
            'vehicle_type': vtype,
            'status': 'available',
            'current_km': 75000,
            'fc_expiry': today - datetime.timedelta(days=2),           # Expired (critical violation)
            'insurance_expiry': today + datetime.timedelta(days=4),    # Critical (<=7 days)
            'permit_expiry': today + datetime.timedelta(days=20),      # Warning (<=30 days)
            'tax_expiry': today + datetime.timedelta(days=90),         # Healthy
            'pollution_expiry': today + datetime.timedelta(days=15),   # Warning (<=30 days)
        }
    )
    # Ensure updated values
    v_test.fc_expiry = today - datetime.timedelta(days=2)
    v_test.insurance_expiry = today + datetime.timedelta(days=4)
    v_test.permit_expiry = today + datetime.timedelta(days=20)
    v_test.status = 'available'
    v_test.save()

    # Create test driver
    d_test, _ = Driver.objects.get_or_create(
        license_number='DL-TN38-P4TEST-01',
        defaults={
            'name': 'Murugan Phase4 Captain',
            'phone': '9876543299',
            'status': 'active',
            'badge_number': 'BDG-P4-001',
            'license_validity_tr': today + datetime.timedelta(days=6),  # Critical (<=7 days)
            'license_validity_nt': today + datetime.timedelta(days=180),
        }
    )
    d_test.phone = '9876543299'
    d_test.license_validity_tr = today + datetime.timedelta(days=6)
    d_test.status = 'active'
    d_test.save()

    # 1.1 Scan compliance expiries
    compliance_results = check_compliance_expiries(threshold_days=30)
    assert 'expired' in compliance_results, "check_compliance_expiries missing 'expired' bucket"
    assert 'critical' in compliance_results, "check_compliance_expiries missing 'critical' bucket"
    assert 'warning' in compliance_results, "check_compliance_expiries missing 'warning' bucket"
    assert compliance_results['total_vehicles_scanned'] > 0, "No vehicles scanned"
    assert compliance_results['total_drivers_scanned'] > 0, "No drivers scanned"

    # Verify vehicle test expiry caught
    expired_ids = [item['identifier'] for item in compliance_results['expired']]
    assert 'TN38-TEST-9901' in expired_ids, f"TN38-TEST-9901 not in expired list: {expired_ids}"
    
    critical_ids = [item['identifier'] for item in compliance_results['critical']]
    assert 'TN38-TEST-9901' in critical_ids or 'Murugan Phase4 Captain' in critical_ids, "Critical list did not capture expiring records"

    print(f"  [PASS] Compliance Watchdog scanned {compliance_results['total_vehicles_scanned']} vehicles & {compliance_results['total_drivers_scanned']} drivers.")
    print(f"         Compliance Rate: {compliance_results['compliance_rate']}% | Expired items: {len(compliance_results['expired'])}")

    # 1.2 Verify trip dispatch compliance safety gate
    # Vehicle has expired FC -> MUST fail dispatch verification
    is_safe, violations = verify_trip_dispatch_compliance(v_test, d_test, today, today + datetime.timedelta(days=1))
    assert not is_safe, "Compliance gate failed to block vehicle with expired FC!"
    assert any("FC" in v for v in violations), f"Expected FC violation in {violations}"
    print(f"  [PASS] Safety Gate blocked non-compliant vehicle dispatch: {violations[0]}")

    # Temporarily renew FC, resolve any existing defect tickets & test pass
    v_test.fc_expiry = today + datetime.timedelta(days=60)
    v_test.insurance_expiry = today + datetime.timedelta(days=60)
    v_test.permit_expiry = today + datetime.timedelta(days=60)
    v_test.tax_expiry = today + datetime.timedelta(days=60)
    v_test.pollution_expiry = today + datetime.timedelta(days=60)
    v_test.save()
    v_test.defect_tickets.filter(status__in=['open', 'in_progress']).update(status='resolved')
    d_test.license_validity_tr = today + datetime.timedelta(days=60)
    d_test.save()

    is_safe_clean, violations_clean = verify_trip_dispatch_compliance(v_test, d_test, today, today + datetime.timedelta(days=1))
    assert is_safe_clean, f"Safety gate unexpectedly blocked valid vehicle: {violations_clean}"
    print("  [PASS] Safety Gate confirmed legal dispatch for valid vehicle & driver.")

    # -------------------------------------------------------------------------
    # TEST 2: PREVENTIVE MAINTENANCE ODOMETER & TYRE/BATTERY WEAR SCHEDULER
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Preventive Maintenance & Asset Wear Engine ---")
    
    # Create service reminder that is overdue
    v_test.current_km = 80050
    v_test.save()
    reminder, _ = ServiceReminder.objects.get_or_create(
        vehicle=v_test,
        service_task='Differential Oil & Brake Pad Overhaul',
        defaults={
            'interval_km': 10000,
            'last_service_km': 70000,
            'is_active': True,
        }
    )
    reminder.last_service_km = 70000
    reminder.interval_km = 10000
    reminder.is_active = True
    reminder.save()

    # Create tyre asset with high wear (v_test.current_km = 80050, installed at 32050 -> run = 48000 / 50000 = 96%)
    asset, _ = VehicleAsset.objects.get_or_create(
        vehicle=v_test,
        serial_number='MRF-P4-STEER-01',
        defaults={
            'asset_type': 'tyre',
            'position': 'front_left',
            'installed_date': today - datetime.timedelta(days=200),
            'installed_odometer': 32050,
            'expected_life_km': 50000,
            'status': 'in_use',
        }
    )
    asset.installed_odometer = 32050
    asset.expected_life_km = 50000
    asset.status = 'in_use'
    asset.save()
    assert asset.needs_replacement, f"Asset at 96% wear should need replacement (run: {asset.current_run_km}, max: {asset.expected_life_km})"

    maint_results = check_preventive_maintenance_due(vehicle_id=v_test.id)
    assert len(maint_results['services_due']) > 0, "Overdue service reminder not detected"
    assert len(maint_results['assets_due']) > 0, "Worn tyre asset not detected"

    # Verify auto-created DefectTicket
    auto_ticket = DefectTicket.objects.filter(
        vehicle=v_test,
        description__icontains='Differential Oil & Brake Pad Overhaul',
        status='open'
    ).first()
    assert auto_ticket is not None, "Preventive maintenance engine failed to auto-generate DefectTicket for overdue service"
    wear_pct = round(asset.current_run_km / asset.expected_life_km * 100, 1)
    print(f"  [PASS] Auto-generated DefectTicket #{auto_ticket.id}: '{auto_ticket.description}'")
    print(f"  [PASS] Asset Wear Monitor flagged tyre '{asset.serial_number}' at {wear_pct}% wear.")

    # -------------------------------------------------------------------------
    # TEST 3: LIVE PASSENGER GPS TRACKING & TOKENIZED API
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Live Public Passenger GPS Tracking Links ---")

    # Create a test booking and trip
    client_party, _ = ClientModel.objects.get_or_create(
        name='Sangeetha P4 Travels Group',
        defaults={'phone': '9443312345', 'email': 'sangeetha@test.com', 'address': 'Gandhipuram, Coimbatore'}
    )

    booking, _ = Booking.objects.get_or_create(
        booking_number='BK-P4-TRACK-001',
        defaults={
            'party': client_party,
            'guest_name': 'Dr. Sangeetha Ramanathan',
            'guest_phone': '9443312345',
            'pickup_location': 'Gandhipuram Central, Coimbatore',
            'destination': 'Ooty Botanical Gardens',
            'pickup_date': today,
            'pickup_time': datetime.time(8, 30),
            'vehicle_type': vtype,
            'billing_type': 'package',
            'status': 'confirmed',
            'quoted_price': Decimal('8500.00'),
        }
    )

    trip, _ = Trip.objects.get_or_create(
        trip_id='TR-P4-TRACK-001',
        defaults={
            'booking': booking,
            'party': client_party,
            'vehicle': v_test,
            'driver': d_test,
            'start_date': today,
            'end_date': today + datetime.timedelta(days=1),
            'start_time': datetime.time(8, 30),
            'guest_name': 'Dr. Sangeetha Ramanathan',
            'status': 'started',
        }
    )
    trip.vehicle = v_test
    trip.driver = d_test
    trip.status = 'started'
    trip.save()

    # Verify tracking token auto-generation
    assert trip.tracking_token is not None and len(trip.tracking_token) > 10, "Trip tracking token was not auto-generated"
    assert trip.tracking_url == f"/track/{trip.tracking_token}/", f"Unexpected tracking_url: {trip.tracking_url}"
    print(f"  [PASS] Auto-generated Tracking Token: {trip.tracking_token}")
    print(f"  [PASS] Live Tracking URL: {trip.tracking_url}")

    # Add mock GPS telematics ping
    ping = VehicleTelematicsPing.objects.create(
        vehicle=v_test,
        trip=trip,
        latitude=Decimal('11.016844'),
        longitude=Decimal('76.955832'),
        speed_kmh=Decimal('54.5'),
        heading_degrees=285.0,
        ignition_on=True,
        fuel_level_pct=Decimal('78.0')
    )

    # 3.1 Test Public HTML Tracking View
    unauth_client = TestClient() # Completely unauthenticated public user
    resp_html = unauth_client.get(trip.tracking_url)
    assert resp_html.status_code == 200, f"Public tracking view failed: {resp_html.status_code}"
    content_str = resp_html.content.decode('utf-8')
    assert trip.trip_id in content_str, "Trip ID missing in public tracking view"
    assert v_test.registration_number in content_str, "Vehicle plate missing in tracking view"
    assert d_test.name in content_str, "Driver name missing in tracking view"
    print(f"  [PASS] Public Passenger Tracking Page loaded successfully (HTTP 200).")

    # 3.2 Test 404 on bad token
    resp_404 = unauth_client.get('/track/invalid-token-12345/')
    assert resp_404.status_code == 404, "Invalid token did not return 404"
    print("  [PASS] Invalid token securely rejected with HTTP 404.")

    # 3.3 Test Live Polling JSON API
    api_url = f"/api/track/{trip.tracking_token}/live/"
    resp_json = unauth_client.get(api_url)
    assert resp_json.status_code == 200, f"Tracking JSON API failed: {resp_json.status_code}"
    api_data = json.loads(resp_json.content.decode('utf-8'))
    assert api_data['status'] == 'success', f"Expected status 'success', got {api_data.get('status')}"
    assert api_data['vehicle']['registration_number'] == v_test.registration_number
    assert round(api_data['vehicle']['speed_kmh']) == 55 or round(api_data['vehicle']['speed_kmh']) == 54
    assert len(api_data['breadcrumbs']) > 0, "Breadcrumbs trail missing in live polling"
    print(f"  [PASS] Live GPS Tracking Polling API: {api_data['vehicle']['speed_kmh']} km/h, heading {api_data['vehicle']['heading']}°, ETA: {api_data['trip']['eta_str']}")

    # -------------------------------------------------------------------------
    # TEST 4: OMNICHANNEL WHATSAPP & CRM NOTIFICATION ENGINE
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Omnichannel WhatsApp Dispatch Engine ---")

    # 4.1 Trip assignment alert
    comm_res = dispatch_trip_assignment_alert(trip)
    assert comm_res.get('status') == 'simulated_sent', f"Expected simulated_sent, got {comm_res}"
    # Verify CRM communication log entry
    crm_log = CommunicationLog.objects.filter(booking=booking, comm_type='whatsapp').last()
    assert crm_log is not None, "Failed to create CRM CommunicationLog for trip assignment alert"
    assert trip.tracking_token in crm_log.message_content, "Tracking URL missing from WhatsApp message content"
    print(f"  [PASS] Trip Assignment WhatsApp sent and logged to CRM (ID #{crm_log.id}).")

    # 4.2 Emergency SOS alert
    EmergencyIncidentAlert.objects.filter(incident_id='INC-P4-TEST-01').delete()
    incident = EmergencyIncidentAlert.objects.create(
        incident_id='INC-P4-TEST-01',
        vehicle=v_test,
        driver=d_test,
        trip=trip,
        incident_type='tyre_puncture',
        severity='medium',
        location_address='NH544 Near Avinashi Bypass, KM 118',
        passenger_count=18,
        passengers_safety_status='all_safe',
        description='Right rear tyre puncture on outer ring road. Passengers safe inside AC cabin.',
    )
    sos_res = dispatch_emergency_sos_broadcast(incident)
    assert sos_res.get('status') == 'simulated_sent', f"Expected simulated_sent, got {sos_res}"
    print(f"  [PASS] Emergency SOS Broadcast sent to control room for incident {incident.incident_id}.")

    # 4.3 Payslip WhatsApp alert
    profile, _ = DriverSalaryProfile.objects.get_or_create(
        driver=d_test,
        defaults={
            'basic_salary': Decimal('22000.00'),
            'allowances': Decimal('10400.00'),
            'epf_number': 'EPF/CBE/12345',
            'esi_number': 'ESI/TN/67890',
            'epf_deduction_rate': Decimal('12.00'),
            'esi_deduction_rate': Decimal('0.75'),
        }
    )
    payslip, _ = DriverPayslip.objects.get_or_create(
        driver=d_test,
        month=today.month,
        year=today.year,
        defaults={
            'days_present': 26,
            'basic_salary': Decimal('22000.00'),
            'allowances': Decimal('10400.00'),
            'epf_deduction': Decimal('1800.00'),
            'esi_deduction': Decimal('400.00'),
            'traffic_fines_deduction': Decimal('500.00'),
            'advances_recovered': Decimal('2000.00'),
        }
    )
    slip_res = dispatch_payslip_alert(payslip)
    assert slip_res.get('status') == 'simulated_sent', f"Expected simulated_sent, got {slip_res}"
    print(f"  [PASS] Payslip Disbursal WhatsApp sent to Captain {d_test.name} for Net ₹{payslip.net_payable}.")

    # -------------------------------------------------------------------------
    # TEST 5: TOUR BOOKING & RAZORPAY WEBHOOK INTEGRATION
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Tour Booking Checkout & Razorpay Webhook ---")

    # Create test package and inventory
    pkg, _ = Package.objects.get_or_create(
        name='Phase4 Nilgiris Scenic Tour',
        defaults={
            'package_code': 'PKG-P4-TEST-01',
            'duration_days': 3,
            'duration_nights': 2,
            'base_price': Decimal('4500.00'),
            'destination': 'Ooty & Coonoor',
            'category': 'hill_station',
        }
    )
    batch, _ = PackageInventory.objects.get_or_create(
        package=pkg,
        departure_date=today + datetime.timedelta(days=14),
        defaults={
            'total_seats': 30,
            'booked_seats': 0,
            'price_override': Decimal('4200.00'),
            'status': 'open',
        }
    )

    # 5.1 Test customer portal tour checkout POST
    # We simulate a customer user with linked client & CustomerAccount
    cust_user, _ = User.objects.get_or_create(username='cust_p4', defaults={'email': 'custp4@test.com'})
    cust_party, _ = ClientModel.objects.get_or_create(
        name='Karthik Subramanian',
        defaults={'phone': '9876501234', 'email': 'custp4@test.com', 'address': 'Race Course, Coimbatore'}
    )
    CustomerAccount.objects.get_or_create(
        user=cust_user,
        defaults={'client_record': cust_party, 'is_email_verified': True}
    )
    cust_client = TestClient()
    cust_client.force_login(cust_user)
    Payment.objects.filter(booking__party=cust_party).delete()
    InstallmentPlan.objects.filter(booking__party=cust_party).delete()
    Booking.objects.filter(party=cust_party).delete()
    PaymentWebhookEvent.objects.filter(event_id='evt_test_p4_payment_12345').delete()

    checkout_url = reverse('customer_portal:checkout', args=[batch.id])
    checkout_post_data = {
        'pax': 2,
        'payment_plan': 'advance', # 50% advance = 2 * 4200 * 0.5 = 4200
        'coupon_code': '',
    }
    # Follow redirects or catch the redirect to mock payment gateway
    resp_chk = cust_client.post(checkout_url, checkout_post_data, follow=False)
    # create_payment_link returns simulated short_url 'https://rzp.io/i/simulated_p4_link'
    assert resp_chk.status_code in [302, 200], f"Unexpected checkout response: {resp_chk.status_code}"

    # Verify pending booking was created with valid VehicleType (not string) and Decimal prices
    new_booking = Booking.objects.filter(party=cust_party, package=pkg).order_by('-id').first()
    assert new_booking is not None, "Checkout failed to create Booking record"
    assert new_booking.status == 'pending', f"Booking should be pending, got {new_booking.status}"
    assert isinstance(new_booking.vehicle_type, VehicleType), f"Booking vehicle_type should be VehicleType model, got {type(new_booking.vehicle_type)}"
    assert new_booking.quoted_price == Decimal('8400.00'), f"Quoted price mismatch: {new_booking.quoted_price}"

    # Verify installment plan created
    inst_plan = InstallmentPlan.objects.filter(booking=new_booking).first()
    assert inst_plan is not None, "Installment plan not created for advance booking"
    print(f"  [PASS] Tour Booking created: {new_booking.booking_number} (Status: {new_booking.status}, Total: ₹{new_booking.quoted_price})")

    # 5.2 Test Razorpay Webhook Confirmation
    # Simulate Razorpay Webhook POST payload for payment_link.paid
    webhook_payload = {
        "id": "evt_test_p4_payment_12345",
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_test_998877",
                    "reference_id": new_booking.booking_number,
                    "amount_paid": 420000, # In paise -> ₹4,200.00
                    "status": "paid"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_test_443322",
                    "amount": 420000,
                    "method": "upi",
                    "description": f"Booking for {pkg.name}"
                }
            }
        }
    }

    resp_hook = unauth_client.post(
        '/payments/webhook/razorpay/',
        data=json.dumps(webhook_payload),
        content_type='application/json'
    )
    assert resp_hook.status_code == 200, f"Webhook failed: {resp_hook.status_code}"

    # Verify Webhook event logged
    evt_log = PaymentWebhookEvent.objects.filter(event_id='evt_test_p4_payment_12345').first()
    assert evt_log is not None, "PaymentWebhookEvent was not logged in DB"

    # Verify Booking status updated to confirmed
    new_booking.refresh_from_db()
    assert new_booking.status == 'confirmed', f"Booking status was not updated to confirmed: {new_booking.status}"

    # Verify Payment record created in finance app
    payment_rec = Payment.objects.filter(booking=new_booking).last()
    assert payment_rec is not None, "Payment record not created on Razorpay webhook capture"
    assert payment_rec.amount == Decimal('4200.00'), f"Payment amount mismatch: {payment_rec.amount}"
    assert payment_rec.payment_type == 'customer_receipt'
    print(f"  [PASS] Razorpay Webhook auto-confirmed Booking {new_booking.booking_number} and recorded Payment #{payment_rec.id} of ₹{payment_rec.amount}.")

    # -------------------------------------------------------------------------
    # TEST 6: COMPLIANCE DASHBOARD CONTROL ROOM HTTP VIEW
    # -------------------------------------------------------------------------
    print("\n--- TEST 6: Compliance Dashboard Control Room Views ---")

    resp_dash = test_client.get('/maintenance/compliance/')
    assert resp_dash.status_code == 200, f"Dashboard view failed with {resp_dash.status_code}"
    dash_html = resp_dash.content.decode('utf-8')
    assert "RTO Compliance Watchdog & Maintenance Scheduler" in dash_html or "RTO Compliance Watchdog" in dash_html
    assert "Fleet Compliance Rate" in dash_html
    print("  [PASS] Compliance & Maintenance Control Room Dashboard rendered (HTTP 200).")

    resp_api_comp = test_client.get('/maintenance/api/compliance-summary/')
    assert resp_api_comp.status_code == 200, f"Compliance API failed with {resp_api_comp.status_code}"
    comp_json = json.loads(resp_api_comp.content.decode('utf-8'))
    assert 'compliance_rate' in comp_json
    print(f"  [PASS] Real-time Compliance Summary API: Compliance Rate {comp_json['compliance_rate']}%, Expired: {comp_json['expired_count']}")

    print("\n" + "=" * 80)
    print("🎉 ALL PHASE 4 ENTERPRISE ENHANCEMENTS TESTS PASSED (100% SUCCESS)!")
    print("=" * 80)


if __name__ == '__main__':
    run_phase4_verification()
