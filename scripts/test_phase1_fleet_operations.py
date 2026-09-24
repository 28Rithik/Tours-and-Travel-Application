import os
import sys
import django
from decimal import Decimal

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client as TestClient
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Vehicle, Driver, VehicleType, Client as PartyClient
from operations.models import (
    Booking, Trip, EmergencyIncidentAlert, VehicleTelematicsPing,
    DriverBehaviorLog, GeofenceZone
)
from maintenance.models import PreTripInspectionChecklist, DefectTicket
from finance_fleet.models import FuelRecord
from driver_portal.models import DriverPortalAccount
from operations.services import ingest_telematics_ping, dispatch_standby_vehicle

def run_tests():
    print("=" * 70)
    print("  PHASE 1 FLEET MANAGEMENT VERIFICATION TEST SUITE")
    print("=" * 70)

    # 1. Setup Base Test Data
    vtype = VehicleType.objects.first()
    if not vtype:
        vtype = VehicleType.objects.create(name="Toyota Innova Crysta", seating_capacity=7)
    client_corp, _ = PartyClient.objects.get_or_create(name="Infosys BPO Fleet", defaults={"phone": "9888800001"})

    vehicle_primary, _ = Vehicle.objects.get_or_create(
        registration_number="TN01-FL-9001",
        defaults={
            "vehicle_type": vtype,
            "ownership_type": "owned",
            "status": "active",
            "brand": "Toyota",
            "model": "Innova Crysta",
            "year": 2024,
            "color": "Silver",
            "fuel_type": "diesel",
            "seating_capacity": 7,
            "current_km": 45000,
            "gps_imei": "IMEI-TEST-9001",
        }
    )
    vehicle_primary.current_km = 45000
    vehicle_primary.save(update_fields=['current_km'])

    vehicle_standby, _ = Vehicle.objects.get_or_create(
        registration_number="TN01-FL-9002",
        defaults={
            "vehicle_type": vtype,
            "ownership_type": "owned",
            "status": "active",
            "brand": "Toyota",
            "model": "Innova Crysta Standby",
            "year": 2024,
            "color": "White",
            "fuel_type": "diesel",
            "seating_capacity": 7,
            "current_km": 30000,
            "gps_imei": "IMEI-TEST-9002",
        }
    )

    # Clean up any previous test runs
    PreTripInspectionChecklist.objects.filter(vehicle=vehicle_primary).delete()
    VehicleTelematicsPing.objects.filter(vehicle=vehicle_primary).delete()
    DriverBehaviorLog.objects.filter(vehicle=vehicle_primary).delete()
    EmergencyIncidentAlert.objects.filter(vehicle__in=[vehicle_primary, vehicle_standby]).delete()
    Trip.objects.filter(trip_id__startswith="TRIP-SAFE-").delete()

    driver_primary, _ = Driver.objects.get_or_create(
        phone="9876543210",
        defaults={
            "name": "Murugan Velu",
            "driver_type": "permanent",
            "status": "active",
            "license_number": "TN01-2018-998877",
        }
    )

    driver_standby, _ = Driver.objects.get_or_create(
        phone="9876543211",
        defaults={
            "name": "Karthik Subramanian",
            "driver_type": "permanent",
            "status": "active",
            "license_number": "TN01-2019-112233",
        }
    )

    print("  [Setup] Test vehicles and drivers initialized.")

    # -------------------------------------------------------------
    # TEST 1: Pre-Trip Safety Inspection & Auto Defect Generation
    # -------------------------------------------------------------
    print("\n--- Test 1: Pre-Trip Safety Inspection Checklist ---")

    # A: Passing Inspection
    pass_insp = PreTripInspectionChecklist.objects.create(
        vehicle=vehicle_primary,
        driver=driver_primary,
        odometer_reading=45100,
        brakes_functional=True,
        tyres_tread_and_pressure=True,
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
        driver_signature_name=driver_primary.name,
    )
    pass_insp.auto_evaluate_status()
    pass_insp.save()
    assert pass_insp.overall_status == 'passed', f"Expected 'passed', got {pass_insp.overall_status}"
    assert vehicle_primary.current_km == 45100, f"Expected odometer sync to 45100, got {vehicle_primary.current_km}"
    print(f"  [PASS] Passing inspection created: #{pass_insp.inspection_number} (Status: {pass_insp.overall_status})")

    # B: Failing Inspection (e.g. Failed Brakes & Low Coolant)
    fail_insp = PreTripInspectionChecklist.objects.create(
        vehicle=vehicle_primary,
        driver=driver_primary,
        odometer_reading=45120,
        brakes_functional=False,  # CRITICAL FAIL
        tyres_tread_and_pressure=True,
        engine_oil_level=True,
        coolant_level=False,     # CRITICAL FAIL
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
        defect_notes="Brake pedal spongy, radiator coolant reservoir below MIN.",
        driver_signature_name=driver_primary.name,
    )
    fail_insp.auto_evaluate_status()
    fail_insp.save()
    assert fail_insp.overall_status == 'failed', f"Expected 'failed', got {fail_insp.overall_status}"
    assert fail_insp.defect_ticket is not None, "Expected linked DefectTicket to be auto-generated!"
    assert fail_insp.defect_ticket.status == 'open', f"Expected open ticket, got {fail_insp.defect_ticket.status}"
    print(f"  [PASS] Failing inspection detected: #{fail_insp.inspection_number} -> Auto-generated DefectTicket #{fail_insp.defect_ticket.pk}")

    # -------------------------------------------------------------
    # TEST 2: Trip Safety Gate Enforcement
    # -------------------------------------------------------------
    print("\n--- Test 2: Trip Departure Safety Gate Verification ---")
    booking = Booking.objects.create(
        party=client_corp,
        guest_name="Mr. Rajesh Kumar",
        pickup_location="Airport T1",
        destination="Whitefield Tech Park",
        pickup_date=timezone.now().date(),
        pickup_time=timezone.now().time(),
        journey_type="airport",
        vehicle_type=vtype,
        pax_count=4,
        quoted_price=Decimal("2500.00"),
        billing_type="day",
    )

    uninspected_vehicle, _ = Vehicle.objects.get_or_create(
        registration_number="TN01-FL-9999",
        defaults={"vehicle_type": vtype, "status": "active", "brand": "Toyota", "model": "Innova", "year": 2023, "fuel_type": "diesel", "seating_capacity": 7}
    )

    test_trip = Trip.objects.create(
        trip_id="TRIP-SAFE-001",
        booking=booking,
        party=client_corp,
        guest_name=booking.guest_name,
        vehicle=uninspected_vehicle,
        driver=driver_primary,
        status="booked",
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
        billing_model="fixed",
        fixed_amount=Decimal("2500.00"),
    )

    # Attempt to start trip with uninspected vehicle via test client
    user_admin = User.objects.filter(is_superuser=True).first()
    if not user_admin:
        user_admin = User.objects.create_superuser("admin_test", "admin@test.com", "pass123")
    
    client = TestClient()
    client.force_login(user_admin)

    # 1. Uninspected start without bypass -> Should be blocked with warning
    resp_uninspected = client.post(f"/trips/{test_trip.pk}/status/", {"status": "started"})
    test_trip.refresh_from_db()
    assert test_trip.status != "started", f"Security violation: Trip started without pre-trip inspection! Status: {test_trip.status}"
    print(f"  [PASS] Uninspected vehicle trip blocked as expected (Status remains: {test_trip.status})")

    # 2. Start with authorized bypass -> Should succeed
    resp_bypass = client.post(f"/trips/{test_trip.pk}/status/", {"status": "started", "bypass_inspection": "1"})
    test_trip.refresh_from_db()
    assert test_trip.status == "started", f"Expected 'started' with bypass, got {test_trip.status}"
    print(f"  [PASS] Trip started with authorized bypass override: {test_trip.status}")

    # -------------------------------------------------------------
    # TEST 3: Emergency Breakdown & Standby Replacement Dispatch
    # -------------------------------------------------------------
    print("\n--- Test 3: Emergency SOS & Standby Vehicle Dispatch ---")
    alert = EmergencyIncidentAlert.objects.create(
        incident_type="breakdown",
        severity="critical",
        vehicle=uninspected_vehicle,
        driver=driver_primary,
        trip=test_trip,
        latitude=Decimal("12.9716000"),
        longitude=Decimal("77.5946000"),
        location_address="NH44 Highway, Km 42 near Hosur",
        passenger_count=4,
        passengers_safety_status="all_safe",
        description="Radiator hose burst. Engine overheating on highway.",
        status="reported",
    )
    assert alert.incident_id.startswith("INC-"), f"Invalid incident id {alert.incident_id}"
    print(f"  [PASS] Emergency Incident Alert recorded: #{alert.incident_id} ({alert.get_incident_type_display()})")

    # Execute 1-click Standby Replacement Dispatch
    dispatch_res = dispatch_standby_vehicle(
        incident_id=alert.pk,
        standby_vehicle_id=vehicle_standby.pk,
        standby_driver_id=driver_standby.pk,
        eta_minutes=25,
        notes="Standby Innova Crysta dispatched from Hosur Yard."
    )
    assert dispatch_res["status"] == "success", f"Dispatch failed: {dispatch_res}"

    alert.refresh_from_db()
    test_trip.refresh_from_db()

    assert alert.status == "standby_dispatched", f"Expected status 'standby_dispatched', got {alert.status}"
    assert alert.standby_vehicle == vehicle_standby, "Standby vehicle mismatch on alert!"
    assert test_trip.vehicle == vehicle_standby, f"Trip vehicle not swapped! Found: {test_trip.vehicle}"
    assert test_trip.driver == driver_standby, f"Trip driver not swapped! Found: {test_trip.driver}"
    assert "EMERGENCY STANDBY DISPATCH" in test_trip.partner_handover_notes, "Handover notes missing on trip!"
    print(f"  [PASS] 1-Click Standby Dispatch verified: Vehicle swapped from {uninspected_vehicle.registration_number} to {vehicle_standby.registration_number}")

    # -------------------------------------------------------------
    # TEST 4: Telematics Ingestion & Automated Driver Behavior
    # -------------------------------------------------------------
    print("\n--- Test 4: Telematics Ping Ingestion & Behavior Events ---")

    # A: Normal Speed Ping (65.0 km/h)
    normal_ping_payload = {
        "imei": vehicle_primary.gps_imei,
        "latitude": 12.9812,
        "longitude": 77.5998,
        "speed_kmh": 65.0,
        "heading": 180.0,
        "ignition_on": True,
        "fuel_level_pct": 72.5,
        "odometer_km": 45150,
    }
    res_normal = ingest_telematics_ping(normal_ping_payload)
    assert res_normal["status"] == "success", f"Normal ping failed: {res_normal}"
    vehicle_primary.refresh_from_db()
    assert vehicle_primary.current_km == 45150, f"Odometer not updated! Got {vehicle_primary.current_km}"
    assert "12.98120" in vehicle_primary.current_location, f"Location not updated! Got {vehicle_primary.current_location}"
    print(f"  [PASS] Normal telematics ping ingested: {vehicle_primary.registration_number} @ 65 km/h, Odometer: {vehicle_primary.current_km} KM")

    # B: Overspeeding Ping (95.0 km/h) -> Trigger DriverBehaviorLog
    overspeed_ping_payload = {
        "imei": vehicle_primary.gps_imei,
        "latitude": 12.9900,
        "longitude": 77.6100,
        "speed_kmh": 95.0,
        "heading": 185.0,
        "ignition_on": True,
        "fuel_level_pct": 70.0,
        "odometer_km": 45165,
    }
    res_overspeed = ingest_telematics_ping(overspeed_ping_payload)
    assert res_overspeed["status"] == "success"
    assert len(res_overspeed["events_triggered"]) > 0, "Expected overspeeding event to trigger!"

    behavior_log = DriverBehaviorLog.objects.filter(
        vehicle=vehicle_primary,
        event_type="overspeeding"
    ).order_by("-timestamp").first()

    assert behavior_log is not None, "DriverBehaviorLog record not found!"
    assert behavior_log.recorded_speed_kmh == Decimal("95.0"), f"Expected 95.0 km/h, got {behavior_log.recorded_speed_kmh}"
    assert behavior_log.penalty_points >= 10, f"Expected penalty >= 10, got {behavior_log.penalty_points}"
    print(f"  [PASS] Automated overspeeding violation captured: {behavior_log.recorded_speed_kmh} km/h (Penalty: -{behavior_log.penalty_points} pts)")

    # C: Geofence Zone Speed Violation
    depot_zone, _ = GeofenceZone.objects.get_or_create(
        name="Hosur Maintenance Depot",
        defaults={
            "zone_type": "depot",
            "latitude": Decimal("12.7300"),
            "longitude": Decimal("77.8300"),
            "radius_meters": 1000,
            "speed_limit_kmh": 25,
            "is_active": True,
        }
    )
    geofence_speeding_payload = {
        "imei": vehicle_primary.gps_imei,
        "latitude": 12.7302,  # Inside Hosur depot (<50m away)
        "longitude": 77.8301,
        "speed_kmh": 45.0,     # Exceeds depot 25 km/h limit
        "ignition_on": True,
    }
    res_geo = ingest_telematics_ping(geofence_speeding_payload)
    assert any("Hosur Maintenance Depot" in e for e in res_geo["events_triggered"]), f"Geofence breach not detected: {res_geo}"
    print(f"  [PASS] Geofence zone perimeter & speed rule triggered: {res_geo['events_triggered']}")

    # -------------------------------------------------------------
    # TEST 5: HTTP API Endpoints (/api/telematics/ping/ & /live/)
    # -------------------------------------------------------------
    print("\n--- Test 5: HTTP REST Endpoints ---")
    resp_api = client.post(
        "/api/telematics/ping/",
        data='{"imei": "IMEI-TEST-9001", "latitude": 12.985, "longitude": 77.605, "speed_kmh": 70.0, "ignition_on": true}',
        content_type="application/json"
    )
    assert resp_api.status_code == 200, f"API Ping returned {resp_api.status_code}: {resp_api.content}"
    print("  [PASS] POST /api/telematics/ping/ returned 200 OK.")

    resp_live = client.get(f"/api/telematics/live/{vehicle_primary.pk}/")
    assert resp_live.status_code == 200, f"API Live returned {resp_live.status_code}"
    live_json = resp_live.json()
    assert live_json["status"] == "success"
    assert "recent_crumbs" in live_json
    print(f"  [PASS] GET /api/telematics/live/{vehicle_primary.pk}/ returned {len(live_json['recent_crumbs'])} telemetry breadcrumbs.")

    # -------------------------------------------------------------
    # TEST 6: Mobile Driver Web Portal
    # -------------------------------------------------------------
    print("\n--- Test 6: Mobile Driver Web Portal User Journey ---")
    driver_client = TestClient()

    # A: Driver Login with Phone & PIN
    login_resp = driver_client.post("/driver/login/", {
        "phone": driver_primary.phone,
        "pin": "1234",
    }, follow=True)
    assert login_resp.status_code == 200
    assert driver_client.session.get("driver_id") == driver_primary.pk
    print(f"  [PASS] Driver portal login successful for {driver_primary.name} ({driver_primary.phone})")

    # B: Driver Dashboard
    dash_resp = driver_client.get("/driver/")
    assert dash_resp.status_code == 200
    assert driver_primary.name in dash_resp.content.decode("utf-8")
    print("  [PASS] Driver mobile dashboard rendered with duties & vehicle status.")

    # C: Driver Inspection Submission
    insp_post_resp = driver_client.post("/driver/inspection/", {
        "vehicle_id": vehicle_primary.pk,
        "odometer_reading": "45200",
        "brakes_functional": "1",
        "tyres_tread_and_pressure": "1",
        "engine_oil_level": "1",
        "coolant_level": "1",
        "brake_fluid_level": "1",
        "battery_and_wiring": "1",
        "headlights_and_highbeam": "1",
        "taillights_and_brakelights": "1",
        "indicators_and_hazard": "1",
        "wipers_and_washer_fluid": "1",
        "horn_and_mirrors": "1",
        "first_aid_kit_present": "1",
        "fire_extinguisher_present": "1",
        "spare_wheel_and_jack": "1",
        "ac_or_fans_working": "1",
        "cabin_cleanliness": "1",
        "driver_signature_name": driver_primary.name,
    }, follow=True)
    assert insp_post_resp.status_code == 200
    portal_insp = PreTripInspectionChecklist.objects.filter(vehicle=vehicle_primary, driver=driver_primary).order_by("-created_at").first()
    assert portal_insp.overall_status == "passed"
    print(f"  [PASS] Driver pre-trip inspection submitted via mobile form: #{portal_insp.inspection_number}")

    # D: Driver Highway Fuel Refill Log
    fuel_post_resp = driver_client.post("/driver/fuel/", {
        "vehicle_id": vehicle_primary.pk,
        "fuel_quantity": "50.0",
        "fuel_price": "97.50",
        "fuel_station": "Indian Oil Highway Oasis - Krishnagiri",
        "opening_km": "45250",
    }, follow=True)
    assert fuel_post_resp.status_code == 200
    fuel_rec = FuelRecord.objects.filter(vehicle=vehicle_primary, fuel_station__icontains="Krishnagiri").first()
    assert fuel_rec is not None, "Fuel record not created!"
    assert fuel_rec.fuel_quantity == Decimal("50.0")
    print(f"  [PASS] Highway fuel refill logged from mobile portal: 50L @ Rs. 97.50/L at {fuel_rec.fuel_station}")

    # E: Driver SOS Trigger
    sos_post_resp = driver_client.post("/driver/sos/", {
        "incident_type": "tyre_burst",
        "severity": "high",
        "latitude": "12.8500",
        "longitude": "77.7200",
        "location_address": "Near Attibele Toll Plaza",
        "passenger_count": "3",
        "passengers_safety_status": "all_safe",
        "description": "Right rear tyre puncture on expressway. Passengers safe inside.",
    }, follow=True)
    assert sos_post_resp.status_code == 200
    sos_alert = EmergencyIncidentAlert.objects.filter(driver=driver_primary, incident_type="tyre_burst").order_by("-reported_at").first()
    assert sos_alert is not None, "SOS Emergency alert not created!"
    assert sos_alert.severity == "high"
    print(f"  [PASS] 1-Tap Emergency SOS broadcast from driver mobile: #{sos_alert.incident_id} ({sos_alert.get_incident_type_display()})")

    print("\n" + "=" * 70)
    print("  ALL PHASE 1 FLEET MANAGEMENT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
