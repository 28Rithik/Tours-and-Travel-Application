from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from core.models import Vehicle, VehicleType, Driver, Party
from operations.models import Booking, Trip, DriverHandoverSession, EmergencyIncidentAlert, TripMilestoneEvent
from finance.models import TripExpense


class Phase5DriverLifecycleAndHandoverTests(TestCase):
    """
    Automated verification suite for Phase 5:
    Driver Digital Handover Mobile Portal, 2D Vehicle Condition Schematic Check,
    Emergency SOS Triggers, 7-Milestone Tour Lifecycle Progression,
    Passenger PIN Verification, and Central Audit Desk.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('fleet_admin', 'admin@travels.in', 'admin')
        
        cls.vtype = VehicleType.objects.create(
            name='Innova Crysta Luxury',
            category='car',
            seating_capacity=7
        )

        cls.vehicle = Vehicle.objects.create(
            registration_number='TN 38 AA 7788',
            brand='Toyota',
            model='Innova Crysta 2.4 ZX',
            vehicle_type=cls.vtype,
            seating_capacity=7,
            current_km=52000,
            status='available'
        )

        cls.driver = Driver.objects.create(
            name='Captain Karthik Murugan',
            phone='9443123456',
            license_number='TN38-2015-0012345',
            status='available'
        )

        cls.party = Party.objects.create(
            name='Bespoke South India Tours',
            phone='9876543210',
            party_type='customer'
        )

        cls.booking = Booking.objects.create(
            booking_number='BKG-2026-P5-001',
            party=cls.party,
            guest_name='Mr. Sundar Pichai',
            guest_phone='9876543210',
            pickup_location='Coimbatore Airport CJB',
            destination='Ooty Club',
            pickup_date=timezone.now().date(),
            pickup_time='08:30:00',
            status='confirmed',
            vehicle_type=cls.vtype
        )

        cls.trip = Trip.objects.create(
            trip_id='TRIP-2026-P5-001',
            booking=cls.booking,
            vehicle=cls.vehicle,
            driver=cls.driver,
            party=cls.party,
            start_date=timezone.now().date(),
            start_time=timezone.now().time(),
            status='assigned',
            pickup_pin='4821',
            tracking_token='token-lifecycle-test-001'
        )

    def setUp(self):
        self.client = Client()

    def test_01_driver_handover_portal_get(self):
        """Driver Handover mobile portal loads with 2D schematic, vehicle data, and SOS button."""
        res = self.client.get(f'/trip/{self.trip.pk}/handover/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Driver Handover Digital Twin')
        self.assertContains(res, 'TN 38 AA 7788')
        self.assertContains(res, '2D Vehicle Condition Check')
        self.assertContains(res, 'startCarSvg')
        self.assertContains(res, 'endCarSvg')
        self.assertContains(res, '🚨 SOS')
        self.assertContains(res, 'Open 7-Milestone Tour Lifecycle Cockpit')

    def test_02_driver_start_duty_submission(self):
        """Submitting Start Duty logs Handover Session, updates opening KM, and sets trip to started."""
        payload = {
            'session_type': 'start',
            'odometer_reading': '52150',
            'fuel_level_percent': '100',
            'gps_latitude': '11.0168',
            'gps_longitude': '76.9558',
            'location_name': 'Coimbatore Depot',
            'scratch_damage_notes': '[2D Vehicle Schematic Check]: Engine Bonnet (scratch), Left Doors (dent)'
        }
        res = self.client.post(f'/trip/{self.trip.pk}/handover/', payload)
        self.assertEqual(res.status_code, 302)  # Redirects back to handover portal

        # Verify DB records
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.opening_km, 52150)
        self.assertEqual(self.trip.driver_handover_status, 'started')
        self.assertEqual(self.trip.status, 'started')

        session = DriverHandoverSession.objects.filter(trip=self.trip, session_type='start').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.odometer_reading, 52150)
        self.assertEqual(session.fuel_level_percent, 100)
        self.assertIn('Engine Bonnet (scratch)', session.scratch_damage_notes)

    def test_03_driver_end_duty_submission(self):
        """Submitting End Duty logs return odometer KM, distance run, and transitions trip to completed."""
        # Set start state first
        self.trip.opening_km = 52150
        self.trip.status = 'started'
        self.trip.driver_handover_status = 'started'
        self.trip.save()

        payload = {
            'session_type': 'end',
            'odometer_reading': '52450',
            'fuel_level_percent': '80',
            'gps_latitude': '11.4102',
            'gps_longitude': '76.6950',
            'location_name': 'Ooty Club Depot',
            'scratch_damage_notes': '[2D Vehicle Schematic Check]: Front Bumper (chip)'
        }
        res = self.client.post(f'/trip/{self.trip.pk}/handover/', payload)
        self.assertEqual(res.status_code, 302)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.closing_km, 52450)
        self.assertEqual(self.trip.driver_handover_status, 'ended')
        self.assertEqual(self.trip.status, 'completed')
        self.assertEqual(self.trip.used_km, 300)

        session = DriverHandoverSession.objects.filter(trip=self.trip, session_type='end').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.odometer_reading, 52450)

    def test_04_emergency_sos_trigger(self):
        """Triggering SOS alert logs critical EmergencyIncidentAlert with GPS coordinates."""
        payload = {
            'incident_type': 'breakdown',
            'passengers_safety_status': 'all_safe',
            'description': 'Flat tyre near Coonoor ghat road, replacement requested.',
            'latitude': '11.3530',
            'longitude': '76.7959'
        }
        res = self.client.post(f'/trip/{self.trip.pk}/handover/sos/', payload)
        self.assertEqual(res.status_code, 302)

        alert = EmergencyIncidentAlert.objects.filter(trip=self.trip).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.incident_type, 'breakdown')
        self.assertEqual(alert.severity, 'critical')
        self.assertEqual(alert.passengers_safety_status, 'all_safe')

    def test_05_tour_lifecycle_portal_and_milestones(self):
        """Full 7-Milestone tour lifecycle progression including passenger PIN security verification."""
        # 1. GET Lifecycle Cockpit
        res = self.client.get(f'/trip/{self.trip.pk}/lifecycle/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '7-Milestone Tour Lifecycle')
        self.assertContains(res, 'Car Pickup')
        self.assertContains(res, 'Guest PIN')
        self.assertContains(res, 'Car Drop')

        # 2. Advance Milestone 1: car_pickup
        res_m1 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', {
            'milestone': 'car_pickup',
            'odometer_reading': '52000',
            'location_name': 'Coimbatore Depot'
        })
        self.assertEqual(res_m1.status_code, 200)
        self.assertEqual(res_m1.json()['status'], 'success')
        self.assertEqual(res_m1.json()['current_milestone'], 'car_pickup')

        # 3. Advance Milestone 2: driver_reached
        res_m2 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', {
            'milestone': 'driver_reached',
            'location_name': 'Coimbatore Airport Terminal 1'
        })
        self.assertEqual(res_m2.status_code, 200)
        self.assertEqual(res_m2.json()['current_milestone'], 'driver_reached')

        # 4. Advance Milestone 3: guest_pickup (With Invalid PIN first)
        res_bad_pin = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', {
            'milestone': 'guest_pickup',
            'passenger_pin': '9999'
        })
        self.assertEqual(res_bad_pin.status_code, 400)
        self.assertIn('Invalid Passenger Security PIN', res_bad_pin.json()['message'])

        # 5. Advance Milestone 3: guest_pickup (With Valid PIN 4821)
        res_good_pin = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', {
            'milestone': 'guest_pickup',
            'passenger_pin': '4821'
        })
        self.assertEqual(res_good_pin.status_code, 200)
        self.assertTrue(res_good_pin.json()['is_pin_verified'])

        # 6. Advance Milestone 4: on_trip
        res_m4 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', {
            'milestone': 'on_trip',
            'notes': 'Via Mettupalayam Ghats'
        })
        self.assertEqual(res_m4.status_code, 200)

        # 7. Milestone 6: Log travel expense
        res_exp = self.client.post(f'/api/trip/{self.trip.pk}/expense/add/', {
            'expense_type': 'toll',
            'amount': '185.00',
            'description': 'L&T Bypass Toll Plaza slip'
        })
        self.assertEqual(res_exp.status_code, 200)
        self.assertEqual(TripExpense.objects.filter(trip=self.trip).count(), 1)

        # 8. Milestone 7: car_drop (Closure)
        res_m7 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', {
            'milestone': 'car_drop',
            'odometer_reading': '52300',
            'location_name': 'Ooty Main Garage'
        })
        self.assertEqual(res_m7.status_code, 200)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'completed')
        self.assertEqual(self.trip.closing_km, 52300)

    def test_06_handover_session_audit_api(self):
        """Operations auditor can approve a submitted driver handover session."""
        session = DriverHandoverSession.objects.create(
            trip=self.trip,
            driver=self.driver,
            vehicle=self.vehicle,
            session_type='start',
            odometer_reading=52000,
            status='submitted'
        )
        self.client.force_login(self.superuser)
        res = self.client.post(f'/api/whatsapp/handover/{session.pk}/audit/', {'action': 'approve'})
        self.assertEqual(res.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, 'approved')
