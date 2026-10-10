from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from core.models import Vehicle, Driver, VehicleType, Client as PartyClient
from operations.models import Trip, Booking
from operations.dispatch_engine import SmartDispatchEngine

User = get_user_model()


class SmartDispatchEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('dispatch_admin', 'admin@example.com', 'pass123')
        self.client = Client()
        self.client.force_login(self.user)

        self.party = PartyClient.objects.create(
            name="Apex Corporate Systems",
            phone="9876543210",
            party_type="client"
        )

        self.sedan_type = VehicleType.objects.create(name="Prime Sedan", seating_capacity=4)
        self.suv_type = VehicleType.objects.create(name="Luxury SUV", seating_capacity=7)

        today = timezone.localdate()

        # Clean Compliant Vehicle
        self.clean_vehicle = Vehicle.objects.create(
            registration_number="TN 38 CL 1001",
            brand="Toyota",
            model="Innova Crysta",
            vehicle_type=self.suv_type,
            seating_capacity=7,
            ownership_type="owned",
            status="available",
            insurance_expiry=today + timedelta(days=120),
            fc_expiry=today + timedelta(days=200),
            pollution_expiry=today + timedelta(days=90),
            permit_expiry=today + timedelta(days=300),
        )

        # Expired Non-Compliant Vehicle
        self.expired_vehicle = Vehicle.objects.create(
            registration_number="TN 38 EX 9999",
            brand="Maruti",
            model="Dzire",
            vehicle_type=self.sedan_type,
            seating_capacity=4,
            ownership_type="owned",
            status="available",
            insurance_expiry=today - timedelta(days=10),  # EXPIRED
            fc_expiry=today + timedelta(days=50),
            pollution_expiry=today + timedelta(days=10),
        )

        # Well-rested Driver
        self.rested_driver = Driver.objects.create(
            name="Suresh Chauffeur",
            phone="9112233445",
            license_number="TN38-2015-001",
            license_validity_tr=today + timedelta(days=365),
            status="active",
            hill_station_experience=True,
        )

        # Driver with expired license
        self.expired_driver = Driver.objects.create(
            name="Ramesh Expired",
            phone="9223344556",
            license_number="TN38-2010-002",
            license_validity_tr=today - timedelta(days=5),  # EXPIRED
            status="active",
        )

        # Create a pending Booking & Trip
        self.booking = Booking.objects.create(
            party=self.party,
            guest_name="Mr. Arvind Raman",
            guest_phone="9876543210",
            pickup_location="Coimbatore Airport",
            destination="Ooty Botanical Gardens",
            pickup_date=today + timedelta(days=1),
            pickup_time="08:00:00",
            journey_type="outstation",
            vehicle_type=self.suv_type,
            pax_count=5,
            status="pending"
        )

        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.party,
            guest_name=self.booking.guest_name,
            start_date=self.booking.pickup_date,
            end_date=self.booking.pickup_date + timedelta(days=1),
            status="booked"
        )

    def test_evaluate_candidates_ranks_compliant_vehicle_highest(self):
        """
        Verify that SmartDispatchEngine ranks the compliant SUV highest
        and penalizes/disqualifies the expired vehicle and expired driver.
        """
        result = SmartDispatchEngine.evaluate_candidates(self.trip.id)
        self.assertEqual(result['status'], 'success')

        ranked_vehicles = result['ranked_vehicles']
        self.assertTrue(len(ranked_vehicles) >= 2)

        # Clean vehicle should not be disqualified and should have top score
        top_veh = ranked_vehicles[0]
        self.assertEqual(top_veh['registration_number'], self.clean_vehicle.registration_number)
        self.assertFalse(top_veh['is_disqualified'])
        self.assertGreater(top_veh['score'], 60)

        # Expired vehicle must be flagged as disqualified
        expired_v = next(v for v in ranked_vehicles if v['registration_number'] == self.expired_vehicle.registration_number)
        self.assertTrue(expired_v['is_disqualified'])
        self.assertIn("Non-Compliant", expired_v['disqualification_reason'])

    def test_driver_evaluation_flags_expired_license(self):
        """
        Verify that a driver with an expired license is disqualified.
        """
        result = SmartDispatchEngine.evaluate_candidates(self.trip.id)
        ranked_drivers = result['ranked_drivers']

        top_driver = ranked_drivers[0]
        self.assertEqual(top_driver['id'], self.rested_driver.id)
        self.assertFalse(top_driver['is_disqualified'])

        bad_driver = next(d for d in ranked_drivers if d['id'] == self.expired_driver.id)
        self.assertTrue(bad_driver['is_disqualified'])
        self.assertIn("License Expired", bad_driver['disqualification_reason'])

    def test_capacity_disqualification_for_undersized_vehicle(self):
        """
        When trip pax_count is 5, a 4-seater vehicle must be disqualified.
        """
        result = SmartDispatchEngine.evaluate_candidates(self.trip.id)
        ranked_vehicles = result['ranked_vehicles']
        dzire = next(v for v in ranked_vehicles if v['registration_number'] == self.expired_vehicle.registration_number)
        self.assertTrue(dzire['is_disqualified'])

    def test_api_smart_dispatch_recommendations_endpoint(self):
        """
        Verify GET /api/trips/<trip_id>/dispatch-recommendations/ returns JSON 200.
        """
        url = reverse('api-trip-dispatch-recommendations', args=[self.trip.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('top_pairs', data)
        self.assertTrue(len(data['top_pairs']) > 0)
        self.assertEqual(data['top_pairs'][0]['vehicle']['registration_number'], self.clean_vehicle.registration_number)

    def test_quick_assign_blocks_expired_vehicle_without_override(self):
        """
        Attempting to assign an expired vehicle without compliance_override
        must return HTTP 400 with compliance_blocked status.
        """
        url = reverse('trip-quick-assign', args=[self.trip.id])
        payload = {
            'vehicle_id': self.expired_vehicle.id,
            'driver_id': self.rested_driver.id,
        }
        response = self.client.post(url, payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'compliance_blocked')
        self.assertTrue(any('Insurance' in v for v in data['violations']))

    def test_quick_assign_allows_allocation_with_manager_override(self):
        """
        When compliance_override is supplied, allocation should succeed with audit warning.
        """
        url = reverse('trip-quick-assign', args=[self.trip.id])
        payload = {
            'vehicle_id': self.expired_vehicle.id,
            'driver_id': self.rested_driver.id,
            'compliance_override': '1',
        }
        response = self.client.post(url, payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['override_applied'])
        
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.vehicle_id, self.expired_vehicle.id)
        self.assertEqual(self.trip.driver_id, self.rested_driver.id)
        self.assertEqual(self.trip.status, 'assigned')
