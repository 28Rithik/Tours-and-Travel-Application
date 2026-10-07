import os
import sys
import io
import django
from decimal import Decimal

# Setup Django Environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BASE_DIR)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Driver, Vehicle, VehicleType, Party, Client
from operations.models import Booking, Trip, EmergencyIncidentAlert, WhatsAppBotMessage, DriverHandoverSession
from operations.whatsapp_bot import (
    process_inbound_message,
    generate_passenger_dispatch_sheet,
    generate_driver_briefing_sheet,
    generate_emergency_sos_broadcast,
    dispatch_passenger_alert_whatsapp,
    dispatch_driver_briefing_whatsapp,
    normalize_phone_digits,
)
from operations.views import (
    driver_handover_view,
    driver_handover_sos_view,
    whatsapp_webhook_view,
    admin_whatsapp_bot_studio_view,
    api_whatsapp_simulator,
    api_handover_session_audit,
    api_dispatch_whatsapp_trip_sheet,
)


from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage

def attach_session_and_messages(req):
    SessionMiddleware(lambda r: None).process_request(req)
    req.session.save()
    setattr(req, '_messages', FallbackStorage(req))
    return req


def run_tests():
    print("=" * 80)
    print("🧪 STARTING COMPREHENSIVE WHATSAPP BOT & DRIVER HANDOVER TEST SUITE")
    print("=" * 80)

    factory = RequestFactory()
    test_passed = 0
    test_failed = 0

    def assert_check(condition, title, detail=""):
        nonlocal test_passed, test_failed
        if condition:
            print(f"  [PASS] {title}")
            test_passed += 1
        else:
            print(f"  [FAIL] {title} --> {detail}")
            test_failed += 1

    # 1. SETUP TEST ENTITIES
    print("\n--- [STAGE 1] SETUP TEST DATA ---")
    admin_user, _ = User.objects.get_or_create(username='wa_test_admin', defaults={'is_staff': True, 'is_superuser': True})
    
    party, _ = Client.objects.get_or_create(
        name="Global Tech Solutions Ltd",
        defaults={'phone': '9876543210', 'email': 'transport@globaltech.com'}
    )
    
    veh_type, _ = VehicleType.objects.get_or_create(name="Premium Innova Crysta", defaults={'seating_capacity': 7})
    
    driver, _ = Driver.objects.get_or_create(
        phone="9876500001",
        defaults={'name': 'Captain Murugan S', 'status': 'active', 'badge_number': 'DRV-TAMIL-007'}
    )
    
    vehicle, _ = Vehicle.objects.get_or_create(
        registration_number="TN01BV9999",
        defaults={'brand': 'Toyota', 'model': 'Innova Crysta', 'vehicle_type': veh_type, 'current_km': 45000, 'status': 'active'}
    )

    booking, _ = Booking.objects.get_or_create(
        booking_number="BK-WA-TEST-01",
        defaults={
            'party': party,
            'guest_name': 'Rithick Sundar',
            'guest_phone': '9876500002',
            'pickup_location': 'Chennai International Airport T2',
            'destination': 'Radisson Blu Resort Temple Bay Mamallapuram',
            'pickup_date': timezone.now().date(),
            'pickup_time': timezone.now().time(),
            'journey_type': 'outstation',
            'quoted_price': Decimal('8500.00'),
            'status': 'confirmed'
        }
    )

    trip, _ = Trip.objects.get_or_create(
        trip_id="TRIP-WA-TEST-01",
        defaults={
            'booking': booking,
            'party': party,
            'guest_name': booking.guest_name,
            'vehicle': vehicle,
            'driver': driver,
            'start_date': booking.pickup_date,
            'start_time': booking.pickup_time,
            'status': 'assigned',
            'billing_model': 'fixed',
            'fixed_amount': Decimal('8500.00'),
            'opening_km': 45000,
            'tracking_token': 'test_token_wa_12345'
        }
    )
    assert_check(trip.pk is not None, "Test Trip entity initialized", f"Trip ID: {trip.trip_id}")

    # 2. PASSENGER DISPATCH ALERT GENERATION
    print("\n--- [STAGE 2] LUXURY PASSENGER DISPATCH ALERT GENERATION ---")
    sheet = generate_passenger_dispatch_sheet(trip)
    assert_check("SIVAGAYATHIRI TRAVELS" in sheet, "Sheet contains company branding")
    assert_check("Rithick Sundar" in sheet, "Sheet contains guest name")
    assert_check("TN01BV9999" in sheet, "Sheet contains vehicle registration")
    assert_check(driver.name in sheet, "Sheet contains assigned captain")
    assert_check("test_token_wa_12345" in sheet, "Sheet contains live GPS tracking URL")
    assert_check("upi://pay" in sheet, "Sheet contains dynamic NPCI UPI payment deep-link")
    assert_check("₹8,500.00" in sheet, "Sheet contains billing breakdown")

    # 3. DRIVER BRIEFING SHEET GENERATION
    print("\n--- [STAGE 3] DRIVER BRIEFING & HANDOVER ALERT ---")
    briefing = generate_driver_briefing_sheet(trip)
    assert_check(f"/trip/{trip.pk}/handover/" in briefing, "Briefing contains direct mobile handover portal link")
    assert_check("MANDATORY DIGITAL HANDOVER" in briefing, "Briefing contains digital odometer instructions")

    # 4. INBOUND INTENT PARSING
    print("\n--- [STAGE 4] BOT INTENT PARSING ENGINE ---")
    
    # 4a. TRIP Status Intent
    reply_trip, intent_trip, _ = process_inbound_message("9876500002", "TRIP STATUS")
    assert_check(intent_trip == 'trip_status', "Bot correctly parsed TRIP status intent", f"Intent: {intent_trip}")
    assert_check("Rithick Sundar" in reply_trip, "Trip response contains guest details")

    # 4b. START Duty Intent (by Driver)
    reply_start, intent_start, _ = process_inbound_message("9876500001", "START TRIP DUTY")
    assert_check(intent_start == 'start_handover', "Bot correctly parsed START handover intent", f"Intent: {intent_start}")
    assert_check(f"/trip/{trip.pk}/handover/" in reply_start, "Start handover contains direct URL")

    # 4c. END Duty Intent
    reply_end, intent_end, _ = process_inbound_message("9876500001", "END TRIP COMPLETE")
    assert_check(intent_end == 'end_handover', "Bot correctly parsed END handover intent", f"Intent: {intent_end}")

    # 4d. PAY Intent
    reply_pay, intent_pay, _ = process_inbound_message("9876500002", "PAY BILL BALANCE")
    assert_check(intent_pay == 'payment_upi', "Bot correctly parsed UPI Payment intent", f"Intent: {intent_pay}")
    assert_check("upi://pay" in reply_pay, "Payment response contains direct UPI link")

    # 4e. SOS Emergency Intent
    reply_sos, intent_sos, _ = process_inbound_message("9876500001", "EMERGENCY SOS BREAKDOWN ENGINE STOPPED")
    assert_check(intent_sos == 'sos_trigger', "Bot correctly triggered SOS intent", f"Intent: {intent_sos}")
    assert_check("EMERGENCY SOS LOGGED" in reply_sos, "SOS response returned instant reassurance")
    
    # Verify EmergencyIncidentAlert was auto-created in database
    sos_record = EmergencyIncidentAlert.objects.filter(driver=driver).order_by('-reported_at').first()
    assert_check(sos_record is not None, "EmergencyIncidentAlert was auto-created in DB", f"ID: {sos_record.incident_id if sos_record else 'None'}")
    assert_check(sos_record.severity == 'critical', "SOS Alert severity is CRITICAL")

    # 4f. Fallback Menu
    reply_menu, intent_menu, _ = process_inbound_message("9999999999", "HELLO")
    assert_check(intent_menu == 'general_query', "Bot returned general concierge menu on unhandled greeting")
    assert_check("1️⃣ *TRIP*" in reply_menu, "Menu contains standard interactive options")

    # 5. WHATSAPP WEBHOOK VIEW TESTING
    print("\n--- [STAGE 5] META WEBHOOK API (GET VERIFY & POST INGEST) ---")
    
    # 5a. GET Verification Success
    req_verify = factory.get('/api/whatsapp/webhook/', {
        'hub.mode': 'subscribe',
        'hub.verify_token': 'sivagayathiri_travelerp_wa_verify_2026',
        'hub.challenge': 'CHALLENGE_STRING_TOKEN_ABC123'
    })
    resp_verify = whatsapp_webhook_view(req_verify)
    assert_check(resp_verify.status_code == 200, "Webhook verification returned 200 OK")
    assert_check(resp_verify.content.decode('utf-8') == 'CHALLENGE_STRING_TOKEN_ABC123', "Webhook verification echoed challenge token")

    # 5b. GET Verification Failure
    req_bad_verify = factory.get('/api/whatsapp/webhook/', {
        'hub.mode': 'subscribe',
        'hub.verify_token': 'wrong_token',
        'hub.challenge': 'TEST'
    })
    resp_bad = whatsapp_webhook_view(req_bad_verify)
    assert_check(resp_bad.status_code == 403, "Webhook rejected bad token with 403 Forbidden")

    # 5c. POST Inbound Message Ingestion
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": "9876500002",
                        "id": "wamid.HBgLM...",
                        "type": "text",
                        "text": {"body": "TRIP"}
                    }]
                }
            }]
        }]
    }
    req_post = factory.post(
        '/api/whatsapp/webhook/',
        data=webhook_payload,
        content_type='application/json'
    )
    resp_post = whatsapp_webhook_view(req_post)
    assert_check(resp_post.status_code == 200, "Webhook POST ingestion returned 200 OK")

    # 6. MOBILE DRIVER HANDOVER PORTAL
    print("\n--- [STAGE 6] MOBILE DRIVER HANDOVER PORTAL ---")
    trip.status = 'assigned'
    trip.driver_handover_status = 'pending'
    trip.opening_km = 45000
    trip.closing_km = None
    trip.save()
    
    # 6a. GET Handover View
    req_handover_get = attach_session_and_messages(factory.get(f'/trip/{trip.pk}/handover/'))
    resp_handover_get = driver_handover_view(req_handover_get, trip_id=trip.pk)
    assert_check(resp_handover_get.status_code == 200, "Driver Handover Portal GET returned 200 OK")

    # 6b. POST Start Duty Handover with Odometer Photo
    dummy_img = SimpleUploadedFile("start_odo.jpg", b"fake_odometer_image_bytes_start", content_type="image/jpeg")
    req_handover_start = attach_session_and_messages(factory.post(f'/trip/{trip.pk}/handover/', {
        'session_type': 'start',
        'odometer_reading': '45120',
        'gps_latitude': '12.991200',
        'gps_longitude': '80.170500',
        'location_name': 'Chennai Airport Terminal 2 Gate 4',
        'fuel_level_percent': '100',
        'scratch_damage_notes': 'Front bumper minor pre-existing scratch',
        'odometer_photo': dummy_img
    }))
    resp_handover_start = driver_handover_view(req_handover_start, trip_id=trip.pk)
    assert_check(resp_handover_start.status_code == 302, "Start Handover POST redirected successfully")
    
    trip.refresh_from_db()
    assert_check(trip.opening_km == 45120, "Trip opening_km updated to 45,120 KM")
    assert_check(trip.driver_handover_status == 'started', "Trip driver_handover_status updated to 'started'")
    assert_check(trip.status == 'started', "Trip status transitioned to 'started'")
    assert_check(bool(trip.opening_odometer_photo), "Opening odometer photo saved to trip record")
    
    start_session = DriverHandoverSession.objects.filter(trip=trip, session_type='start').first()
    assert_check(start_session is not None, "DriverHandoverSession (start) created in DB")
    assert_check(start_session.odometer_reading == 45120, "Handover session recorded exact start odometer")

    # 6c. POST End Duty Handover with Closing Odometer Photo & Distance Run Calculation
    dummy_end_img = SimpleUploadedFile("end_odo.jpg", b"fake_odometer_image_bytes_end", content_type="image/jpeg")
    req_handover_end = attach_session_and_messages(factory.post(f'/trip/{trip.pk}/handover/', {
        'session_type': 'end',
        'odometer_reading': '45340',
        'gps_latitude': '12.620800',
        'gps_longitude': '80.194400',
        'location_name': 'Mamallapuram Radisson Blu Drop',
        'fuel_level_percent': '75',
        'scratch_damage_notes': 'Smooth journey, passenger arrived safely.',
        'odometer_photo': dummy_end_img
    }))
    resp_handover_end = driver_handover_view(req_handover_end, trip_id=trip.pk)
    assert_check(resp_handover_end.status_code == 302, "End Handover POST redirected successfully")
    
    trip.refresh_from_db()
    assert_check(trip.closing_km == 45340, "Trip closing_km updated to 45,340 KM")
    assert_check(trip.used_km == 220, "Distance run automatically calculated (45340 - 45120 = 220 KM)", f"Used KM: {trip.used_km}")
    assert_check(trip.driver_handover_status == 'ended', "Trip driver_handover_status transitioned to 'ended'")
    assert_check(trip.status == 'completed', "Trip status transitioned to 'completed'")

    # 7. HANDOVER AUDIT & APPROVAL WORKFLOW
    print("\n--- [STAGE 7] HANDOVER AUDIT & APPROVAL WORKFLOW ---")
    end_session = DriverHandoverSession.objects.filter(trip=trip, session_type='end').first()
    assert_check(end_session is not None, "End Duty session found for audit")
    
    req_audit = factory.post(f'/api/whatsapp/handover/{end_session.pk}/audit/', {'action': 'approve'})
    req_audit.user = admin_user
    resp_audit = api_handover_session_audit(req_audit, session_id=end_session.pk)
    assert_check(resp_audit.status_code == 200, "Audit approval API returned 200 OK")
    
    end_session.refresh_from_db()
    assert_check(end_session.status == 'approved', "DriverHandoverSession status updated to 'approved'")
    trip.refresh_from_db()
    assert_check(trip.driver_handover_status == 'approved', "Trip driver_handover_status updated to 'approved'")

    # 8. 1-CLICK PASSENGER DISPATCH BROADCAST API
    print("\n--- [STAGE 8] 1-CLICK PASSENGER DISPATCH ALERT DISPATCHER ---")
    initial_broadcast_count = trip.whatsapp_broadcast_count or 0
    req_dispatch = factory.post(f'/api/whatsapp/trip/{trip.pk}/dispatch/')
    resp_dispatch = api_dispatch_whatsapp_trip_sheet(req_dispatch, trip_id=trip.pk)
    assert_check(resp_dispatch.status_code == 200, "1-Click dispatch API returned 200 OK")
    
    trip.refresh_from_db()
    assert_check(trip.whatsapp_broadcast_count == initial_broadcast_count + 1, "Trip whatsapp_broadcast_count incremented")

    # 9. UNFOLD ADMIN BOT STUDIO VIEW
    print("\n--- [STAGE 9] UNFOLD ADMIN BOT STUDIO VIEW ---")
    req_studio = attach_session_and_messages(factory.get('/admin/operations/whatsapp-bot/'))
    req_studio.user = admin_user
    resp_studio = admin_whatsapp_bot_studio_view(req_studio)
    assert_check(resp_studio.status_code == 200, "Admin WhatsApp Bot Studio view returned 200 OK")

    print("\n" + "=" * 80)
    print(f"📊 TEST EXECUTION SUMMARY: {test_passed} PASSED | {test_failed} FAILED")
    print("=" * 80)

    if test_failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    run_tests()
