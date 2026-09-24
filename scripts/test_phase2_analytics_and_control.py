import os
import sys
from decimal import Decimal
from datetime import timedelta

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.test import Client as TestClient
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Vehicle, Driver, VehicleType, Client as PartyClient
from operations.models import Booking, Trip, EmergencyIncidentAlert, VehicleTelematicsPing, DriverBehaviorLog, TrafficFine
from fleet_contracts.models import ContractTripLog, TransportContract
from maintenance.models import ServiceRecord, ComplianceDocument, DefectTicket, PreTripInspectionChecklist
from finance_fleet.models import FuelRecord, FastagTollDeduction, CorporateFastagAccount
from packages.models import TourFeedbackLog, Package
from analytics.models import DriverScorecard
from analytics.services import calculate_driver_scorecard, calculate_vehicle_cpk, get_fleet_utilization_breakdown


def run_tests():
    print("=" * 70)
    print("  PHASE 2: ANALYTICS & LIVE OPERATIONS CONTROL TEST SUITE")
    print("=" * 70)

    now = timezone.now()
    today = now.date()

    # -------------------------------------------------------------
    # 0. Setup Staff User & Test Fixtures
    # -------------------------------------------------------------
    staff_user, _ = User.objects.get_or_create(
        username="phase2_commander",
        defaults={"is_staff": True, "is_superuser": True}
    )
    staff_user.is_staff = True
    staff_user.is_superuser = True
    staff_user.set_password("fleetpass123")
    staff_user.save()

    client = TestClient()
    client.force_login(staff_user)

    vtype_sedan, _ = VehicleType.objects.get_or_create(
        name="Phase2 Sedan Segment",
        defaults={"seating_capacity": 4, "fuel_type": "diesel", "default_km_rate": Decimal("14.0")}
    )
    vtype_bus, _ = VehicleType.objects.get_or_create(
        name="Phase2 Bus Segment",
        defaults={"seating_capacity": 40, "fuel_type": "diesel", "default_km_rate": Decimal("45.0")}
    )

    party_corp, _ = PartyClient.objects.get_or_create(
        name="Phase2 Analytics Enterprise",
        defaults={"phone": "9887766554"}
    )

    # Vehicles
    veh_sedan, _ = Vehicle.objects.get_or_create(
        registration_number="TN38-AN-2001",
        defaults={
            "vehicle_type": vtype_sedan,
            "brand": "Maruti",
            "model": "Dzire",
            "ownership_type": "owned",
            "status": "available",
            "current_km": 20000,
            "current_location": "Coimbatore HQ Yard",
            "emi_amount": Decimal("12000.00"),
        }
    )
    veh_sedan.current_km = 20000
    veh_sedan.emi_amount = Decimal("12000.00")
    veh_sedan.save()

    veh_bus, _ = Vehicle.objects.get_or_create(
        registration_number="TN38-AN-2002",
        defaults={
            "vehicle_type": vtype_bus,
            "brand": "BharatBenz",
            "model": "Glider 40S",
            "ownership_type": "owned",
            "status": "available",
            "current_km": 50000,
            "current_location": "Coimbatore HQ Yard",
            "emi_amount": Decimal("35000.00"),
        }
    )
    veh_bus.current_km = 50000
    veh_bus.emi_amount = Decimal("35000.00")
    veh_bus.save()

    # Drivers
    captain_star, _ = Driver.objects.get_or_create(
        name="Captain Karthik Star",
        defaults={"phone": "9771122334", "status": "active", "driver_type": "owned"}
    )
    captain_remedial, _ = Driver.objects.get_or_create(
        name="Captain Remedial Ravi",
        defaults={"phone": "9772233445", "status": "active", "driver_type": "owned"}
    )

    # Clean existing test records for idempotence
    DriverBehaviorLog.objects.filter(driver__in=[captain_star, captain_remedial]).delete()
    TrafficFine.objects.filter(driver__in=[captain_star, captain_remedial]).delete()
    FuelRecord.objects.filter(vehicle__in=[veh_sedan, veh_bus]).delete()
    FastagTollDeduction.objects.filter(vehicle__in=[veh_sedan, veh_bus]).delete()
    ServiceRecord.objects.filter(vehicle__in=[veh_sedan, veh_bus]).delete()
    ComplianceDocument.objects.filter(vehicle__in=[veh_sedan, veh_bus]).delete()
    EmergencyIncidentAlert.objects.filter(vehicle__in=[veh_sedan, veh_bus]).delete()
    from finance.models import DriverSettlement
    DriverSettlement.objects.filter(trip__vehicle__in=[veh_sedan, veh_bus]).delete()
    Trip.objects.filter(vehicle__in=[veh_sedan, veh_bus]).delete()
    TourFeedbackLog.objects.filter(customer_review_text__icontains=captain_star.name).delete()

    print("[PASS] Test environment & test fixtures initialized.")

    # -------------------------------------------------------------
    # 1. Driver Scorecard Engine Verification (calculate_driver_scorecard)
    # -------------------------------------------------------------
    print("\n--- Testing 1: Driver Performance Scorecard Computation ---")

    # Star Captain Data:
    # 1 Trip completed, 300 KM, on time, no safety infractions, 5-star rating, normal fuel
    booking_star = Booking.objects.create(
        party=party_corp,
        guest_name="Guest Executive Star",
        guest_phone="9988776655",
        pickup_location="Coimbatore",
        destination="Ooty Boat House",
        pickup_date=today,
        pickup_time=timezone.now().time(),
        expected_km=300,
        status="completed"
    )
    trip_star = Trip.objects.create(
        booking=booking_star,
        driver=captain_star,
        vehicle=veh_sedan,
        start_date=today,
        end_date=today,
        opening_km=20000,
        closing_km=20300,
        status="completed",
        billing_model="fixed",
        fixed_amount=Decimal("4500.00"),
        driver_bata=Decimal("400.00"),
        days_count=1
    )

    # Feedback 5-star for star driver
    test_pkg = Package.objects.first()
    if not test_pkg:
        test_pkg = Package.objects.create(name="Ooty Summer Getaway", destination="Ooty")
    TourFeedbackLog.objects.create(
        package=test_pkg,
        guest_name="Guest Executive Star",
        overall_rating=5,
        coach_driver_rating=5,
        customer_review_text=f"Exceptional hospitality by {captain_star.name}, very smooth drive!"
    )

    # Remedial Driver Data:
    # 2 Overspeeding infractions, 1 Traffic fine
    DriverBehaviorLog.objects.create(
        vehicle=veh_bus,
        driver=captain_remedial,
        event_type="overspeeding",
        severity="high",
        recorded_speed_kmh=Decimal("94.5"),
        speed_limit_kmh=Decimal("70.0"),
        penalty_points=10
    )
    DriverBehaviorLog.objects.create(
        vehicle=veh_bus,
        driver=captain_remedial,
        event_type="harsh_braking",
        severity="medium",
        recorded_speed_kmh=Decimal("65.0"),
        penalty_points=5
    )
    TrafficFine.objects.create(
        vehicle=veh_bus,
        driver=captain_remedial,
        fine_amount=Decimal("1500.00"),
        date_of_offence=now,
        challan_number="CH-TEST-2024",
        violation_type="signal"
    )

    # Compute scorecards
    card_star = calculate_driver_scorecard(captain_star, start_date=today.replace(day=1), end_date=today)
    card_remedial = calculate_driver_scorecard(captain_remedial, start_date=today.replace(day=1), end_date=today)

    print(f"  * Star Captain Overall Score: {card_star.overall_composite_score}% | Grade: {card_star.grade}")
    print(f"    - Punctuality: {card_star.punctuality_score}% | Safety: {card_star.safety_score}%")
    print(f"    - Rating: {card_star.customer_rating_score}% | Fuel Eco: {card_star.fuel_efficiency_score}%")

    assert card_star.overall_composite_score >= Decimal("90.0"), "Star captain should score >= 90%"
    assert card_star.grade in ["A+", "A"], f"Star captain grade should be A+ or A, got {card_star.grade}"
    assert card_star.safety_score == Decimal("100.0"), "Star captain should have 100% safety score"

    print(f"  * Remedial Driver Overall Score: {card_remedial.overall_composite_score}% | Grade: {card_remedial.grade}")
    print(f"    - Overspeeding Count: {card_remedial.overspeeding_count} | Harsh Braking: {card_remedial.harsh_braking_count}")
    print(f"    - Traffic Fines: {card_remedial.traffic_fines_count} (Rs. {card_remedial.total_fine_amount})")
    print(f"    - Safety Score: {card_remedial.safety_score}%")

    # Safety deductions: (1 overspeed * 10) + (1 harsh brake * 5) + (1 fine * 15) = 30 points deducted -> 70%
    assert card_remedial.safety_score == Decimal("70.00"), f"Expected safety score 70.0, got {card_remedial.safety_score}"
    assert card_remedial.overspeeding_count == 1
    assert card_remedial.traffic_fines_count == 1
    assert card_remedial.overall_composite_score < card_star.overall_composite_score

    # Check persistence in DB
    db_card = DriverScorecard.objects.get(driver=captain_star, month=today.replace(day=1))
    assert db_card.pk == card_star.pk
    print("[PASS] Driver Scorecard Engine multi-dimension weighting and grade logic verified.")

    # -------------------------------------------------------------
    # 2. Cost-Per-KM (CPK) Engine Verification (calculate_vehicle_cpk)
    # -------------------------------------------------------------
    print("\n--- Testing 2: True Cost-Per-KM (CPK) & Unit Economics ---")

    # Seed operational expenses for veh_sedan
    # Fuel: 20 Litres @ Rs. 100/L = Rs. 2,000
    FuelRecord.objects.create(
        vehicle=veh_sedan,
        trip=trip_star,
        date=today,
        fuel_quantity=Decimal("20.0"),
        fuel_price=Decimal("100.00"),
        fuel_station="HPCO Bunk Bypass"
    )
    # Toll: Rs. 250
    fastag_acc, _ = CorporateFastagAccount.objects.get_or_create(
        account_number="FASTAG-ICICI-001",
        defaults={"account_name": "Primary ICICI Fastag Master", "balance": Decimal("50000.00")}
    )
    FastagTollDeduction.objects.create(
        account=fastag_acc,
        vehicle=veh_sedan,
        toll_plaza="Kaniyur Toll Plaza",
        date=now,
        amount=Decimal("250.00")
    )
    # Service: Rs. 1,500
    ServiceRecord.objects.create(
        vehicle=veh_sedan,
        service_type="routine",
        status="completed",
        date=today,
        odometer_reading=20100,
        total_cost=Decimal("1500.00")
    )
    # Insurance Compliance: Rs. 24,000 / yr -> Rs. 2,000 / month
    ComplianceDocument.objects.create(
        vehicle=veh_sedan,
        document_type="insurance",
        document_number="POL-AIG-99901",
        premium_amount=Decimal("24000.00"),
        expiry_date=today + timedelta(days=300)
    )

    cpk_data = calculate_vehicle_cpk(veh_sedan, start_date=today.replace(day=1), end_date=today)

    print(f"  * Vehicle: {cpk_data['registration_number']} ({cpk_data['vehicle_type']})")
    print(f"    - Total Distance: {cpk_data['total_km']} KM")
    print(f"    - Total Revenue: Rs. {cpk_data['revenue']}")
    print(f"    - Fuel Cost: Rs. {cpk_data['fuel_cost']} (Fuel CPK: Rs. {cpk_data['fuel_cpk']}/KM)")
    print(f"    - Maintenance Cost: Rs. {cpk_data['maintenance_cost']}")
    print(f"    - Toll Cost: Rs. {cpk_data['toll_cost']}")
    print(f"    - Driver Bata: Rs. {cpk_data['driver_bata']}")
    print(f"    - Fixed Amortized (EMI + Ins): Rs. {cpk_data['fixed_amortized']}")
    print(f"    - Total Cost: Rs. {cpk_data['total_cost']}")
    print(f"    - CPK (Cost-Per-KM): Rs. {cpk_data['cpk']}/KM")
    print(f"    - RPK (Revenue-Per-KM): Rs. {cpk_data['rpk']}/KM")
    print(f"    - Operating Margin: Rs. {cpk_data['margin_per_km']}/KM ({cpk_data['margin_pct']}%)")

    assert cpk_data['total_km'] == 300, f"Expected 300 KM, got {cpk_data['total_km']}"
    assert cpk_data['fuel_cost'] == Decimal("2000.00")
    assert cpk_data['toll_cost'] == Decimal("250.00")
    assert cpk_data['maintenance_cost'] == Decimal("1500.00")
    assert cpk_data['driver_bata'] == Decimal("400.00")
    # Fixed = EMI (12,000) + Monthly Insurance (24,000 / 12 = 2,000) = 14,000
    assert cpk_data['fixed_amortized'] == Decimal("14000.00")
    # Total cost = 2000 + 1500 + 250 + 400 + 14000 = 18150
    assert cpk_data['total_cost'] == Decimal("18150.00")
    # CPK = 18150 / 300 = 60.50
    assert cpk_data['cpk'] == Decimal("60.50")
    # RPK = 4500 / 300 = 15.00
    assert cpk_data['rpk'] == Decimal("15.00")

    print("[PASS] True Cost-Per-KM Engine computed direct and fixed amortized costs with mathematical precision.")

    # -------------------------------------------------------------
    # 3. Fleet Utilization Breakdown Verification (get_fleet_utilization_breakdown)
    # -------------------------------------------------------------
    print("\n--- Testing 3: Fleet Real-time Utilization Analytics ---")

    # Put veh_bus into active trip
    trip_bus_active = Trip.objects.create(
        booking=booking_star,
        driver=captain_remedial,
        vehicle=veh_bus,
        start_date=today,
        status="started",
        opening_km=50000
    )

    util_data = get_fleet_utilization_breakdown()
    print(f"  * Total Fleet: {util_data['total_count']}")
    print(f"  * Active on Duty: {util_data['active_count']}")
    print(f"  * Ready Standby: {util_data['standby_count']}")
    print(f"  * In Workshop / Defect: {util_data['maintenance_count']}")
    print(f"  * Idle (>5 Days): {util_data['idle_count']}")
    print(f"  * Utilization Percentage: {util_data['utilization_pct']}%")

    assert util_data['total_count'] >= 2
    assert util_data['active_count'] >= 1, "At least 1 vehicle should be active on trip"
    assert util_data['utilization_pct'] > 0.0

    print("[PASS] Fleet Utilization analytics computed duty status segments correctly.")

    # -------------------------------------------------------------
    # 4. Live Operations Feed REST Endpoint (/api/fleet/live-feed/)
    # -------------------------------------------------------------
    print("\n--- Testing 4: Live Fleet Feed REST Endpoint (/api/fleet/live-feed/) ---")

    # Create a telematics ping for veh_bus
    VehicleTelematicsPing.objects.create(
        vehicle=veh_bus,
        trip=trip_bus_active,
        latitude=Decimal("11.0250000"),
        longitude=Decimal("76.9600000"),
        speed_kmh=Decimal("56.40"),
        ignition_on=True,
        fuel_level_pct=Decimal("82.00")
    )

    # Create an emergency incident for testing ticker & alerts
    incident_alert = EmergencyIncidentAlert.objects.create(
        incident_type="breakdown",
        severity="critical",
        vehicle=veh_bus,
        driver=captain_remedial,
        trip=trip_bus_active,
        latitude=Decimal("11.0250000"),
        longitude=Decimal("76.9600000"),
        location_address="Avinashi Road Flyover, Coimbatore",
        description="Air pressure failure on front brake booster",
        status="reported"
    )

    resp_feed = client.get('/api/fleet/live-feed/')
    assert resp_feed.status_code == 200, f"Expected 200, got {resp_feed.status_code}"
    feed_json = resp_feed.json()

    assert feed_json['status'] == "success"
    assert "summary" in feed_json
    assert "vehicles" in feed_json
    assert "active_incidents" in feed_json
    assert "recent_violations" in feed_json

    # Check that veh_bus is returned with SOS alert status
    bus_item = next((v for v in feed_json['vehicles'] if v['id'] == veh_bus.id), None)
    assert bus_item is not None, "veh_bus must be in live feed vehicles"
    assert bus_item['status_code'] == 'sos_alert', f"Expected sos_alert, got {bus_item['status_code']}"
    assert bus_item['speed_kmh'] == 56.4
    assert bus_item['ignition_on'] is True
    assert bus_item['fuel_level_pct'] == 82.0
    assert bus_item['lat'] == 11.025
    assert bus_item['lng'] == 76.96
    assert bus_item['incident'] is not None
    assert bus_item['incident']['incident_id'] == incident_alert.incident_id

    # Check summary alert count
    assert feed_json['summary']['sos_count'] >= 1
    assert feed_json['summary']['active_alerts_count'] >= 1

    print(f"  * Feed Vehicles Count: {len(feed_json['vehicles'])}")
    print(f"  * Feed Active SOS Incidents: {len(feed_json['active_incidents'])}")
    print(f"  * Telematics values: Lat {bus_item['lat']}, Lng {bus_item['lng']}, Speed {bus_item['speed_kmh']} km/h")
    print("[PASS] Live Feed API endpoint /api/fleet/live-feed/ returned complete telemetry payload.")

    # -------------------------------------------------------------
    # 5. Live Fleet Mission Control Command Center (/fleet/live/)
    # -------------------------------------------------------------
    print("\n--- Testing 5: Live Fleet Mission Control UI (/fleet/live/) ---")

    resp_mc = client.get('/fleet/live/')
    assert resp_mc.status_code == 200, f"Expected 200, got {resp_mc.status_code}"
    content_mc = resp_mc.content.decode('utf-8')

    assert "liveFleetMap" in content_mc, "Map container #liveFleetMap must be in HTML"
    assert "Fleet Operations Command" in content_mc
    assert "LIVE TELEMETRY" in content_mc
    assert "standbyDispatchModal" in content_mc
    assert "/api/fleet/live-feed/" in content_mc

    print("[PASS] Mission Control interactive Leaflet UI (/fleet/live/) renders 200 OK with full DOM components.")

    # -------------------------------------------------------------
    # 6. Fleet Analytics & CPK Dashboard (/analytics/fleet/)
    # -------------------------------------------------------------
    print("\n--- Testing 6: Fleet Intelligence Dashboard (/analytics/fleet/) ---")

    resp_analytics = client.get('/analytics/fleet/')
    assert resp_analytics.status_code == 200, f"Expected 200, got {resp_analytics.status_code}"
    content_analytics = resp_analytics.content.decode('utf-8')

    assert "Fleet Intelligence & Cost Analytics" in content_analytics
    assert "Unit Economics (Benchmark CPK vs Revenue-Per-KM)" in content_analytics
    assert "Performance Scorecard Leaderboard" in content_analytics
    assert "Captain Karthik Star" in content_analytics

    print("[PASS] Fleet Analytics & CPK Dashboard (/analytics/fleet/) renders 200 OK.")

    # -------------------------------------------------------------
    # 7. Driver Scorecard Detail API (/analytics/driver-scorecard/<id>/)
    # -------------------------------------------------------------
    print("\n--- Testing 7: Driver Scorecard Detail API ---")

    resp_score = client.get(f'/analytics/driver-scorecard/{captain_star.id}/')
    assert resp_score.status_code == 200, f"Expected 200, got {resp_score.status_code}"
    score_json = resp_score.json()

    assert score_json['status'] == "success"
    assert score_json['driver']['name'] == captain_star.name
    assert score_json['scorecard']['grade'] in ["A+", "A"]
    assert score_json['scorecard']['safety_score'] == 100.0

    print(f"  * Captain {score_json['driver']['name']}: Grade {score_json['scorecard']['grade']} ({score_json['scorecard']['overall_score']}%)")
    print("[PASS] Driver Scorecard Detail API returned structured performance data.")

    # -------------------------------------------------------------
    # 8. Unauthenticated Access Protection Check
    # -------------------------------------------------------------
    print("\n--- Testing 8: Security & Authentication Gates ---")

    anon_client = TestClient()
    resp_anon_mc = anon_client.get('/fleet/live/')
    assert resp_anon_mc.status_code == 302, "Unauthenticated /fleet/live/ must redirect to login"
    assert '/login/' in resp_anon_mc.url

    resp_anon_feed = anon_client.get('/api/fleet/live-feed/')
    assert resp_anon_feed.status_code == 302, "Unauthenticated /api/fleet/live-feed/ must redirect to login"

    resp_anon_analytics = anon_client.get('/analytics/fleet/')
    assert resp_anon_analytics.status_code == 302, "Unauthenticated /analytics/fleet/ must redirect to login"

    print("[PASS] Security checks confirmed all operational endpoints are protected by authentication.")

    print("\n" + "=" * 70)
    print("  ALL PHASE 2 ANALYTICS & LIVE CONTROL TESTS PASSED (8/8)!")
    print("=" * 70)


if __name__ == '__main__':
    run_tests()
