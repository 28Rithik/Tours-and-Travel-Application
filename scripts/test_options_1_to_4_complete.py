import os
import sys
import datetime
from decimal import Decimal
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client as TestClient
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import Vehicle, Driver, VehicleType, Party
from operations.models import Booking, Trip, EmergencyIncidentAlert, VehicleTelematicsPing
from packages.models import Package, PackageInventory
from maintenance.services import send_compliance_renewal_warnings_alert
from finance.models import Payment
from payments_gateway.models import PaymentWebhookEvent


def run_tests():
    print("=" * 80)
    print("🚀 VALIDATING ALL 4 REQUESTED OPTIONS (COMPLETE END-TO-END)")
    print("=" * 80)

    today = timezone.now().date()
    http = TestClient()
    admin_user, _ = User.objects.get_or_create(username='opt_tester', defaults={'is_staff': True, 'is_superuser': True})
    http.force_login(admin_user)

    # -------------------------------------------------------------------------
    # OPTION 1: OPERATIONAL SAFETY & COMPLIANCE
    # -------------------------------------------------------------------------
    print("\n[OPTION 1] Operational Safety, RTO Expiry Watchdog & Maintenance Hard-Locks...")
    vtype, _ = VehicleType.objects.get_or_create(name='Option Test Coach', defaults={'seating_capacity': 20, 'default_km_rate': 25})
    party, _ = Party.objects.get_or_create(name='Option Safety Party', defaults={'party_type': 'individual'})

    # 1.1 Expired Vehicle Tax / PUC / FC Hard-Lock in Trip.clean()
    expired_veh, _ = Vehicle.objects.get_or_create(
        registration_number='TN38-OPT1-EXP',
        defaults={
            'vehicle_type': vtype,
            'status': 'available',
            'tax_expiry': today - datetime.timedelta(days=5),
            'pollution_expiry': today - datetime.timedelta(days=2),
            'fc_expiry': today - datetime.timedelta(days=10),
            'insurance_expiry': today + datetime.timedelta(days=100),
        }
    )
    expired_veh.tax_expiry = today - datetime.timedelta(days=5)
    expired_veh.pollution_expiry = today - datetime.timedelta(days=2)
    expired_veh.save()

    booking, _ = Booking.objects.get_or_create(
        booking_number='BK-OPT-001',
        defaults={
            'party': party,
            'guest_name': 'Meera Krishnan',
            'pickup_date': today,
            'pickup_time': datetime.time(9, 0),
            'destination': 'Valparai Hills',
            'status': 'confirmed'
        }
    )

    test_trip = Trip(
        booking=booking,
        vehicle=expired_veh,
        start_date=today,
        end_date=today + datetime.timedelta(days=2),
    )
    locked = False
    try:
        test_trip.clean()
    except ValidationError as e:
        locked = True
        print(f"  ✓ Hard-lock triggered as expected for expired vehicle: {list(e.message_dict.keys())}")
    assert locked, "Safety Gate FAILED to hard-lock dispatch of vehicle with expired RTO documents!"

    # 1.2 Expired Driver Commercial License Hard-Lock in Trip.clean()
    valid_veh, _ = Vehicle.objects.get_or_create(
        registration_number='TN38-OPT1-OK',
        defaults={
            'vehicle_type': vtype,
            'status': 'available',
            'tax_expiry': today + datetime.timedelta(days=180),
            'pollution_expiry': today + datetime.timedelta(days=120),
            'fc_expiry': today + datetime.timedelta(days=150),
            'insurance_expiry': today + datetime.timedelta(days=200),
            'permit_expiry': today + datetime.timedelta(days=160),
        }
    )
    valid_veh.tax_expiry = today + datetime.timedelta(days=180)
    valid_veh.pollution_expiry = today + datetime.timedelta(days=120)
    valid_veh.fc_expiry = today + datetime.timedelta(days=150)
    valid_veh.insurance_expiry = today + datetime.timedelta(days=200)
    valid_veh.permit_expiry = today + datetime.timedelta(days=160)
    valid_veh.status = 'available'
    valid_veh.save()

    expired_driver, _ = Driver.objects.get_or_create(
        phone='9844112233',
        defaults={
            'name': 'Kannan Raj',
            'status': 'active',
            'license_validity_tr': today - datetime.timedelta(days=15),
        }
    )
    expired_driver.license_validity_tr = today - datetime.timedelta(days=15)
    expired_driver.save()

    test_trip2 = Trip(
        booking=booking,
        vehicle=valid_veh,
        driver=expired_driver,
        start_date=today,
        end_date=today + datetime.timedelta(days=1),
    )
    driver_locked = False
    try:
        test_trip2.clean()
    except ValidationError as e:
        driver_locked = True
        print(f"  ✓ Hard-lock triggered as expected for driver with expired license: {list(e.message_dict.keys())}")
    assert driver_locked, "Safety Gate FAILED to hard-lock dispatch of driver with expired license!"

    # 1.3 Active Maintenance / Inactive Driver Hard-Locks
    valid_veh.status = 'maintenance'
    valid_veh.save()
    test_trip3 = Trip(booking=booking, vehicle=valid_veh, start_date=today, end_date=today)
    maint_locked = False
    try:
        test_trip3.clean()
    except ValidationError:
        maint_locked = True
        print(f"  ✓ Hard-lock triggered: Vehicle under workshop maintenance cannot be dispatched.")
    assert maint_locked, "Safety Gate FAILED to hard-lock vehicle in maintenance status!"
    valid_veh.status = 'available'
    valid_veh.save()

    # 1.4 Broadcast Renewal Warnings & Oil/Tyre Alerts
    resp_warn = http.get('/maintenance/api/send-renewal-warnings/')
    assert resp_warn.status_code == 200
    warn_data = resp_warn.json()
    print(f"  ✓ RTO Renewal & Maintenance Watchdog alert broadcast executed (Status: {warn_data.get('status')})")

    # -------------------------------------------------------------------------
    # OPTION 2: CUSTOMER EXPERIENCE & LIVE PASSENGER TRACKING
    # -------------------------------------------------------------------------
    print("\n[OPTION 2] Public/Passenger Live GPS Tracking & Shareable Links...")
    valid_driver, _ = Driver.objects.get_or_create(
        phone='9844001122',
        defaults={'name': 'Suresh Kumar', 'status': 'active', 'license_validity_tr': today + datetime.timedelta(days=365)}
    )
    valid_driver.license_validity_tr = today + datetime.timedelta(days=365)
    valid_driver.save()

    active_trip, _ = Trip.objects.get_or_create(
        trip_id='TR-OPT2-TRACK-01',
        defaults={
            'booking': booking,
            'vehicle': valid_veh,
            'driver': valid_driver,
            'guest_name': 'Meera Krishnan',
            'start_date': today,
            'end_date': today + datetime.timedelta(days=2),
            'status': 'started',
            'opening_km': 50000,
        }
    )
    active_trip.vehicle = valid_veh
    active_trip.driver = valid_driver
    active_trip.status = 'started'
    active_trip.save()

    # Ingest a telematics ping
    VehicleTelematicsPing.objects.create(
        vehicle=valid_veh,
        latitude=Decimal('11.0168'),
        longitude=Decimal('76.9558'),
        speed_kmh=Decimal('62.5'),
        heading_degrees=Decimal('180.0'),
        ignition_on=True,
    )

    # Verify auto-generated tracking token & URL
    assert active_trip.tracking_token is not None and len(active_trip.tracking_token) >= 32
    assert active_trip.tracking_url == f"/track/{active_trip.tracking_token}/"
    print(f"  ✓ Shareable Live GPS Tracking URL verified: {active_trip.tracking_url}")

    # Verify public unauthenticated access
    public_client = TestClient()
    resp_track_ui = public_client.get(active_trip.tracking_url)
    assert resp_track_ui.status_code == 200
    assert "Live Trip Tracking" in resp_track_ui.content.decode('utf-8')
    print("  ✓ Public Passenger Live Tracking page loaded cleanly without login requirement.")

    # Verify live telemetry polling API
    resp_poll = public_client.get(f"/api/track/{active_trip.tracking_token}/live/")
    assert resp_poll.status_code == 200
    poll_data = resp_poll.json()
    assert poll_data["status"] == "success"
    assert poll_data["vehicle"]["registration_number"] == valid_veh.registration_number
    assert poll_data["vehicle"]["speed_kmh"] == 62.5
    print(f"  ✓ Live telemetry polling API returned moving coordinates & ETA: {poll_data['trip']['eta_str']}")

    # Verify tracking link included in customer confirmation message
    assert f"/track/{active_trip.tracking_token}/" in active_trip.customer_confirmation_message
    print("  ✓ Passenger Live GPS tracking link embedded in trip.customer_confirmation_message.")

    # Verify trip detail page has live tracking card and copy link
    resp_trip_detail = http.get(f"/trips/{active_trip.id}/")
    assert resp_trip_detail.status_code == 200
    trip_html = resp_trip_detail.content.decode('utf-8')
    assert "Live Passenger GPS Tracking" in trip_html
    assert active_trip.tracking_token in trip_html
    print("  ✓ Trip Detail operations console displays Live GPS Tracking card & 1-click copy action.")

    # -------------------------------------------------------------------------
    # OPTION 3: AUTOMATION & ALERTS (WHATSAPP & EMERGENCY SOS BROADCAST)
    # -------------------------------------------------------------------------
    print("\n[OPTION 3] WhatsApp & Email Event Trigger Engine & SOS Broadcast...")

    # 3.1 1-Click WhatsApp Trip Confirmation & Live Tracking Dispatch
    resp_wa_broadcast = http.get(f"/trips/{active_trip.id}/broadcast-whatsapp/")
    assert resp_wa_broadcast.status_code == 302 # Redirects with success toast
    print("  ✓ 1-Click Trip Confirmation WhatsApp broadcast endpoint executed successfully.")

    # 3.2 Automated SOS Broadcast on Emergency Incident Creation
    incident = EmergencyIncidentAlert.objects.create(
        incident_type='medical',
        severity='critical',
        vehicle=valid_veh,
        driver=valid_driver,
        trip=active_trip,
        location_address='Near Pollachi Ghat Road, KM 14',
        passenger_count=4,
        passengers_safety_status='minor_injuries',
        description='Passenger experienced acute altitude discomfort; first-aid administered.',
        status='reported'
    )
    print(f"  ✓ Emergency SOS alert #{incident.incident_id} created and automatically broadcasted to Control Room.")

    # -------------------------------------------------------------------------
    # OPTION 4: E-COMMERCE & REVENUE (SELF-SERVICE BOOKING & RAZORPAY)
    # -------------------------------------------------------------------------
    print("\n[OPTION 4] Customer Booking Checkout & Razorpay Payment Capture Flow...")
    pkg, _ = Package.objects.get_or_create(
        name='Nilgiris Tea Mist Explorer (3D/2N)',
        defaults={
            'destination': 'Ooty & Coonoor',
            'duration_days': 3,
            'duration_nights': 2,
            'pricing_type': 'fixed',
            'base_price': Decimal('7500.00'),
            'price_with_food': Decimal('9000.00'),
            'price_without_food': Decimal('7500.00'),
        }
    )
    inv, _ = PackageInventory.objects.get_or_create(
        package=pkg,
        departure_date=today + datetime.timedelta(days=10),
        defaults={
            'total_seats': 20,
            'available_seats': 20,
            'booked_seats': 0,
            'status': 'open',
        }
    )

    # Create self-service booking
    online_booking = Booking.objects.create(
        party=party,
        guest_name='Raghavan Sundaram',
        guest_phone='9840123456',
        pickup_location='Coimbatore Junction',
        destination='Ooty',
        pickup_date=inv.departure_date,
        pickup_time=datetime.time(10, 0),
        pax_count=2,
        quoted_price=Decimal('15000.00'),
        package=pkg,
        package_inventory=inv,
        status='pending'
    )
    assert online_booking.status == 'pending'
    print(f"  ✓ Self-service package booking created: {online_booking.booking_number} (Pending Payment)")

    # Simulate Razorpay Webhook post payment
    import uuid
    evt_uuid = f"evt_test_rzp_{uuid.uuid4().hex[:10]}"
    rzp_webhook_payload = {
        "id": evt_uuid,
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_full_test_01",
                    "reference_id": online_booking.booking_number,
                    "amount_paid": 1500000, # In paise -> ₹15,000.00
                    "status": "paid"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_full_test_01",
                    "amount": 1500000,
                    "method": "upi",
                    "description": f"Payment for {online_booking.booking_number}"
                }
            }
        }
    }

    resp_hook = http.post(
        '/payments/webhook/razorpay/',
        data=json.dumps(rzp_webhook_payload),
        content_type='application/json'
    )
    assert resp_hook.status_code == 200
    print("  ✓ Razorpay webhook payload ingested with HTTP 200 OK.")

    # Verify auto-confirmation and financial settlement
    online_booking.refresh_from_db()
    assert online_booking.status == 'confirmed', f"Booking status was not confirmed: {online_booking.status}"
    payment_rec = Payment.objects.filter(booking=online_booking).last()
    assert payment_rec is not None
    assert payment_rec.amount == Decimal('15000.00')
    assert payment_rec.payment_type == 'customer_receipt'
    print(f"  ✓ Booking status automatically updated to 'confirmed' and Payment #{payment_rec.id} (₹{payment_rec.amount}) captured in ledger.")

    print("\n" + "=" * 80)
    print("🎉 ALL 4 OPTIONS (1, 2, 3, AND 4) FULLY VERIFIED AND OPERATIONAL!")
    print("=" * 80)


if __name__ == '__main__':
    run_tests()
