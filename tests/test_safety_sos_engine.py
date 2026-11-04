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
    CommuterManifest,
    NightSafetyEscortLog,
)
from fleet_commute.models import CommuteIncident
from operations.models import EmergencyIncidentAlert
from fleet_commute.safety_engine import SafetyIncidentEngine, haversine_distance_meters


class SafetyIncidentEngineTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='safety_chief_cb',
            email='safety@sivagayathiri.in',
            password='Password@123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role='safety_officer',
            branch='Coimbatore Hub'
        )
        self.client.force_login(self.user)

        self.today = datetime.date.today()

        # Primary Fleet Assets
        self.driver = Driver.objects.create(
            name="Senthil K. (Captain Senthil)",
            phone="+919842111005",
            license_number="TN38-2018-0045678",
            status="active"
        )
        self.vehicle = Vehicle.objects.create(
            registration_number="TN-38-BZ-4401",
            brand="Force",
            model="Urbania 17-Seater",
            seating_capacity=17,
            status="available",
            base_depot="Coimbatore Central HQ",
            current_km=32000,
            fc_expiry=self.today + datetime.timedelta(days=180),
            insurance_expiry=self.today + datetime.timedelta(days=180)
        )

        # Standby Rescue Assets
        self.standby_driver = Driver.objects.create(
            name="Murugan R. (Standby Pilot)",
            phone="+919842111099",
            license_number="TN38-2019-0099887",
            status="active"
        )
        self.standby_vehicle = Vehicle.objects.create(
            registration_number="TN-38-BZ-9999",
            brand="Toyota",
            model="Innova Crysta 2.4",
            seating_capacity=7,
            status="available",
            base_depot="Civil Aerodrome Depot",
            current_km=15000,
            fc_expiry=self.today + datetime.timedelta(days=200),
            insurance_expiry=self.today + datetime.timedelta(days=200)
        )

        # Corporate Client & Route Corridor
        self.customer = Party.objects.create(
            name="Bosch Global Software Technologies",
            party_type="customer"
        )
        self.contract = TransportContract.objects.create(
            name="Bosch CHIL SEZ Corridor Mobility SLA",
            customer=self.customer,
            start_date=self.today - datetime.timedelta(days=30),
            end_date=self.today + datetime.timedelta(days=330),
            billing_model="per_trip",
            default_rate=Decimal('2200.00'),
            gst_rate=Decimal('5.00'),
            status="active"
        )
        self.route = Route.objects.create(
            contract=self.contract,
            name="Corridor 101 - Gandhipuram to Bosch CHIL SEZ",
            origin="Gandhipuram",
            destination="Bosch CHIL SEZ",
            distance_km=22.5
        )
        self.stop_1 = RouteStop.objects.create(
            route=self.route,
            name="Gandhipuram Bus Stand",
            stop_order=1,
            latitude=Decimal('11.018300'),
            longitude=Decimal('76.972500')
        )
        self.stop_2 = RouteStop.objects.create(
            route=self.route,
            name="Peelamedu PSG Tech Signal",
            stop_order=2,
            latitude=Decimal('11.024500'),
            longitude=Decimal('77.003100')
        )
        self.stop_3 = RouteStop.objects.create(
            route=self.route,
            name="Saravanampatti CHIL SEZ Gate 2",
            stop_order=3,
            latitude=Decimal('11.082000'),
            longitude=Decimal('76.995000')
        )

        self.shift = Shift.objects.create(
            route=self.route,
            shift_name="Night Drop BPO",
            direction="outbound",
            timing=datetime.time(22, 30)
        )

        self.trip = ContractTripLog.objects.create(
            shift=self.shift,
            date=self.today,
            vehicle=self.vehicle,
            driver=self.driver,
            status='in_progress',
            passenger_count=12,
            opening_km=32000
        )

        self.commuter = CommuterManifest.objects.create(
            contract=self.contract,
            commuter_id="BOSCH-EMP-9021",
            name="Pooja Sundaram",
            gender="female",
            phone="+919842109876",
            pickup_address="Peelamedu, Coimbatore",
            is_active=True
        )

    def test_haversine_distance(self):
        """Verify haversine distance calculation between known landmarks."""
        # Distance between Gandhipuram (11.0183, 76.9725) and Peelamedu (11.0245, 77.0031) ~ 3.4 km
        d = haversine_distance_meters(11.0183, 76.9725, 11.0245, 77.0031)
        self.assertGreater(d, 3000.0)
        self.assertLess(d, 4000.0)

    def test_trigger_panic_sos_commuter_silent(self):
        """Verify silent SOS creates CommuteIncident with is_silent_sos=True."""
        res = SafetyIncidentEngine.trigger_panic_sos(
            source_type='commuter_silent',
            commuter_id=self.commuter.commuter_id,
            trip_id=self.trip.id,
            latitude=11.0245,
            longitude=77.0031,
            location_name="Near Peelamedu PSG Tech",
            description="Stealth distress triggered by commuter.",
            is_silent=True
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["is_silent_sos"])
        self.assertEqual(res["severity"], "critical")

        incident = CommuteIncident.objects.get(incident_id=res["incident_id"])
        self.assertTrue(incident.is_silent_sos)
        self.assertEqual(incident.passengers_affected, 12)
        self.assertGreaterEqual(len(incident.action_log), 1)

    def test_trigger_panic_sos_driver_panic(self):
        """Verify driver panic creates linked EmergencyIncidentAlert in operations."""
        res = SafetyIncidentEngine.trigger_panic_sos(
            source_type='driver_panic',
            driver_id=self.driver.id,
            vehicle_id=self.vehicle.id,
            trip_id=self.trip.id,
            latitude=11.0500,
            longitude=77.0000,
            location_name="Avinashi Road Bypass",
            description="Driver report of hostile vehicle following cab."
        )
        self.assertEqual(res["status"], "success")
        alert = EmergencyIncidentAlert.objects.filter(incident_id=res["incident_id"]).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.incident_type, 'sos_panic')
        self.assertEqual(alert.vehicle, self.vehicle)

    def test_detect_corridor_deviation_within_threshold(self):
        """Verify vehicle within 200m of route stop is NOT flagged as deviated."""
        res = SafetyIncidentEngine.detect_corridor_deviation(
            trip_id=self.trip.id,
            current_lat=11.0248, # ~40m from stop_2 (11.0245)
            current_lng=77.0032,
            threshold_meters=600.0
        )
        self.assertEqual(res["status"], "success")
        self.assertFalse(res["is_deviated"])
        self.assertFalse(res["incident_triggered"])

    def test_detect_corridor_deviation_exceeding_threshold(self):
        """Verify vehicle 2.5 km off route corridor is flagged as deviated and triggers incident."""
        res = SafetyIncidentEngine.detect_corridor_deviation(
            trip_id=self.trip.id,
            current_lat=11.0500,
            current_lng=77.0800, # Significantly east of corridor
            threshold_meters=600.0,
            auto_trigger_alert=True
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["is_deviated"])
        self.assertTrue(res["incident_triggered"])
        self.assertIsNotNone(res["incident_details"])

    def test_dispatch_standby_rescue(self):
        """Verify assigning standby rescue vehicle and driver updates incident status."""
        sos = SafetyIncidentEngine.trigger_panic_sos(
            source_type='driver_panic',
            trip_id=self.trip.id,
            vehicle_id=self.vehicle.id,
            driver_id=self.driver.id
        )
        res = SafetyIncidentEngine.dispatch_standby_rescue(
            incident_id=sos["incident_id"],
            standby_vehicle_id=self.standby_vehicle.id,
            standby_driver_id=self.standby_driver.id,
            eta_minutes=12,
            officer_user=self.user,
            notes="Standby Innova Crysta dispatched."
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["rescue_eta_minutes"], 12)

        incident = CommuteIncident.objects.get(incident_id=sos["incident_id"])
        self.assertEqual(incident.status, 'rescue_dispatched')
        self.assertEqual(incident.rescue_vehicle, self.standby_vehicle)
        self.assertEqual(incident.rescue_driver, self.standby_driver)

    def test_escalate_emergency_protocol(self):
        """Verify speed-dial escalation logs priority audit trail."""
        sos = SafetyIncidentEngine.trigger_panic_sos(
            source_type='commuter_silent',
            trip_id=self.trip.id
        )
        res = SafetyIncidentEngine.escalate_emergency_protocol(
            incident_id=sos["incident_id"],
            escalation_target='police_112',
            notes="Forwarded live GPS track to TN Police PCR 112.",
            officer_user=self.user
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["escalation_target"], 'police_112')

        incident = CommuteIncident.objects.get(incident_id=sos["incident_id"])
        last_log = incident.action_log[-1]
        self.assertEqual(last_log["action"], "emergency_escalated")
        self.assertEqual(last_log["escalation_target"], "police_112")

    def test_verify_night_safe_drop(self):
        """Verify night safety escort safe drop sign-off updates verification status."""
        res = SafetyIncidentEngine.verify_night_safe_drop(
            trip_id=self.trip.id,
            guard_name="M. Velusamy",
            agency="SIS Security Services",
            badge_number="SEC-TN-042",
            female_count=3,
            verification_status="verified_call",
            confirmed_by="Pooja Sundaram (Commuter)",
            remarks="Phone call confirmation recorded. Reached safely."
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["verification_status"], "verified_call")

        escort = NightSafetyEscortLog.objects.get(id=res["escort_log_id"])
        self.assertEqual(escort.escort_guard_name, "M. Velusamy")
        self.assertEqual(escort.female_passengers_count, 3)
        self.assertEqual(escort.safe_drop_confirmed_by, "Pooja Sundaram (Commuter)")

    def test_resolve_incident(self):
        """Verify resolving incident clears active status and returns rescue asset to available."""
        sos = SafetyIncidentEngine.trigger_panic_sos(
            source_type='driver_panic',
            trip_id=self.trip.id,
            vehicle_id=self.vehicle.id,
            driver_id=self.driver.id
        )
        # Dispatch rescue
        SafetyIncidentEngine.dispatch_standby_rescue(
            incident_id=sos["incident_id"],
            standby_vehicle_id=self.standby_vehicle.id,
            standby_driver_id=self.standby_driver.id
        )
        # Resolve
        res = SafetyIncidentEngine.resolve_incident(
            incident_id=sos["incident_id"],
            resolution_notes="Threat dispelled. Commuters safely delivered to CHIL SEZ.",
            officer_user=self.user
        )
        self.assertEqual(res["status"], "success")

        incident = CommuteIncident.objects.get(incident_id=sos["incident_id"])
        self.assertEqual(incident.status, 'resolved')
        self.assertIsNotNone(incident.resolved_at)

        # Standby vehicle returned to available
        self.standby_vehicle.refresh_from_db()
        self.assertEqual(self.standby_vehicle.status, 'available')

    def test_safety_incident_desk_view_render(self):
        """Verify /safety/ renders radar, KPI cards, and incident table."""
        resp = self.client.get('/safety/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Safety, SOS &amp; Incident Response Desk")
        self.assertContains(resp, "Critical Alarms")
        self.assertContains(resp, "Night Escort Compliance")
        self.assertContains(resp, "Standby Rescue Units")

    def test_night_escort_governance_view_render(self):
        """Verify /safety/night-escort/ renders compliance table and metrics."""
        resp = self.client.get('/safety/night-escort/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Night Escort &amp; Female Safe-Drop Desk")
        self.assertContains(resp, "Compliance Rate")
        self.assertContains(resp, "TAMIL NADU SHOPS &amp; FACTORIES ACT")

    def test_api_safety_trigger_sos(self):
        """Verify POST /api/safety/sos/trigger/ returns 200 and incident code."""
        resp = self.client.post(
            '/api/safety/sos/trigger/',
            data=json.dumps({
                'source_type': 'commuter_silent',
                'commuter_id': self.commuter.commuter_id,
                'trip_id': self.trip.id,
                'latitude': 11.0245,
                'longitude': 77.0031,
                'location_name': 'Peelamedu Tech Signal',
                'description': 'Test silent alarm trigger.'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("INC-SOS-", data["incident_id"])

    def test_api_safety_dispatch_rescue(self):
        """Verify POST /api/safety/rescue/dispatch/ assigns relief unit."""
        sos = SafetyIncidentEngine.trigger_panic_sos(source_type='driver_panic', trip_id=self.trip.id)
        resp = self.client.post(
            '/api/safety/rescue/dispatch/',
            data=json.dumps({
                'incident_id': sos["incident_id"],
                'standby_vehicle_id': self.standby_vehicle.id,
                'standby_driver_id': self.standby_driver.id,
                'eta_minutes': 10,
                'notes': 'Dispatched via API'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

    def test_api_safety_night_escort_signoff(self):
        """Verify POST /api/safety/night-escort/signoff/ records verification."""
        resp = self.client.post(
            '/api/safety/night-escort/signoff/',
            data=json.dumps({
                'trip_id': self.trip.id,
                'guard_name': 'K. Ramanathan',
                'agency': 'G4S Security',
                'badge_number': 'G4S-TN-99',
                'female_count': 2,
                'verification_status': 'verified_sms',
                'confirmed_by': 'Supervisor Sign-off',
                'remarks': 'Doorstep verified'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["guard_name"], "K. Ramanathan")

