import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Vehicle, VehicleType, Driver, Party
from operations.models import Booking, Trip, TripMilestoneEvent
from finance.models import TripExpense

User = get_user_model()


class TripMilestoneLifecycleTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin_lifecycle',
            email='admin_lifecycle@test.com',
            password='testpassword123'
        )
        self.client.force_login(self.user)

        self.party = Party.objects.create(name='Global Corporate Travels', party_type='corporate')
        self.vtype = VehicleType.objects.create(name='Innova Premium', seating_capacity=7)
        self.vehicle = Vehicle.objects.create(
            registration_number='KA-05-TR-7777',
            brand='Toyota',
            model='Innova Crysta',
            vehicle_type=self.vtype,
            seating_capacity=7,
            status='available',
            current_km=52000
        )
        self.driver = Driver.objects.create(
            name='Karthik Selvam',
            phone='+91 98400 99881',
            status='active',
            license_number='TN0120200001234'
        )
        self.booking = Booking.objects.create(
            party=self.party,
            vehicle_type=self.vtype,
            pickup_date=timezone.now().date(),
            pickup_time='09:00',
            pickup_location='Bangalore Airport Terminal 2',
            destination='Mysore Palace & Resort',
            guest_name='Arjun Nair',
            guest_phone='+91 98450 77665',
            status='confirmed'
        )
        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.party,
            vehicle=self.vehicle,
            driver=self.driver,
            guest_name='Arjun Nair',
            start_date=timezone.now().date(),
            status='assigned'
        )
        # Ensure PIN is generated
        self.assertTrue(bool(self.trip.pickup_pin))
        self.assertEqual(len(self.trip.pickup_pin), 4)

    def test_01_milestone_stepper_portal_renders(self):
        """Test the 7-milestone tour lifecycle cockpit renders HTTP 200."""
        res = self.client.get(f'/trip/{self.trip.pk}/lifecycle/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '7-Milestone Tour Lifecycle')
        self.assertContains(res, self.trip.trip_id)
        self.assertContains(res, 'KA-05-TR-7777')
        self.assertContains(res, 'Car Pickup')
        self.assertContains(res, 'Guest PIN')
        self.assertContains(res, 'Car Drop')

    def test_02_milestone_1_car_pickup(self):
        """Test Milestone 1: Car pickup records opening odometer and departures depot."""
        payload = {
            'milestone': 'car_pickup',
            'odometer_reading': '52050',
            'notes': 'Departed depot with clean vehicle'
        }
        res = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['current_milestone'], 'car_pickup')
        self.assertEqual(data['milestone_index'], 1)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.opening_km, 52050)
        self.assertIsNotNone(self.trip.car_pickup_at)
        self.assertEqual(self.trip.status, 'started')

    def test_03_milestone_2_driver_reached(self):
        """Test Milestone 2: Driver reached pickup point with GPS coordinates."""
        payload = {
            'milestone': 'driver_reached',
            'location_name': 'Terminal 2 Pillar 4',
            'gps_latitude': '13.1986',
            'gps_longitude': '77.7066'
        }
        res = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['current_milestone'], 'driver_reached')
        self.assertEqual(data['milestone_index'], 2)

        self.trip.refresh_from_db()
        self.assertIsNotNone(self.trip.driver_reached_at)

    def test_04_milestone_3_passenger_pin_verification(self):
        """Test Milestone 3: Wrong PIN rejected (400); Correct 4-digit PIN verified (200)."""
        correct_pin = self.trip.pickup_pin
        wrong_pin = '0000' if correct_pin != '0000' else '1111'

        # 1. Wrong PIN attempt
        bad_res = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data={
            'milestone': 'guest_pickup',
            'passenger_pin': wrong_pin
        })
        self.assertEqual(bad_res.status_code, 400)
        bad_data = bad_res.json()
        self.assertEqual(bad_data['status'], 'error')
        self.assertIn('Invalid Passenger Security PIN', bad_data['message'])

        # 2. Correct PIN attempt
        good_res = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data={
            'milestone': 'guest_pickup',
            'passenger_pin': correct_pin
        })
        self.assertEqual(good_res.status_code, 200)
        good_data = good_res.json()
        self.assertEqual(good_data['status'], 'success')
        self.assertTrue(good_data['is_pin_verified'])
        self.assertEqual(good_data['current_milestone'], 'guest_pickup')
        self.assertEqual(good_data['milestone_index'], 3)

        self.trip.refresh_from_db()
        self.assertTrue(self.trip.is_pin_verified)
        self.assertIsNotNone(self.trip.guest_pickup_at)

    def test_05_milestone_4_to_7_full_lifecycle_completion(self):
        """Test complete traversal of remaining milestones: on_trip -> guest_drop -> expenses -> car_drop."""
        # Milestone 4: On Trip
        r4 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data={'milestone': 'on_trip'})
        self.assertEqual(r4.status_code, 200)

        # Milestone 5: Guest Drop
        r5 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data={
            'milestone': 'guest_drop',
            'location_name': 'Mysore Palace Main Gate',
            'notes': 'Guest luggage unloaded'
        })
        self.assertEqual(r5.status_code, 200)

        # Milestone 6: Log quick expense
        exp_res = self.client.post(f'/api/trip/{self.trip.pk}/expense/add/', data={
            'expense_type': 'toll',
            'amount': '450.00',
            'description': 'NICE Road Toll Plaza'
        })
        self.assertEqual(exp_res.status_code, 200)
        exp_data = exp_res.json()
        self.assertEqual(exp_data['status'], 'success')
        self.assertEqual(exp_data['total_expenses'], 450.0)

        # Advance milestone 6
        r6 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data={'milestone': 'expenses_photo'})
        self.assertEqual(r6.status_code, 200)

        # Milestone 7: Car Drop (Closing KM)
        self.trip.opening_km = 52000
        self.trip.save()

        r7 = self.client.post(f'/api/trip/{self.trip.pk}/milestone/advance/', data={
            'milestone': 'car_drop',
            'odometer_reading': '52340',
            'notes': 'Returned to depot, keys handed over'
        })
        self.assertEqual(r7.status_code, 200)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.current_milestone, 'car_drop')
        self.assertEqual(self.trip.closing_km, 52340)
        self.assertEqual(self.trip.used_km, 340)
        self.assertEqual(self.trip.status, 'completed')
        self.assertIsNotNone(self.trip.car_drop_at)

        # Check API status summary
        stat_res = self.client.get(f'/api/trip/{self.trip.pk}/milestones/')
        self.assertEqual(stat_res.status_code, 200)
        stat_data = stat_res.json()
        self.assertEqual(stat_data['status'], 'success')
        self.assertEqual(stat_data['current_milestone'], 'car_drop')
        self.assertEqual(stat_data['total_expenses'], 450.0)
        self.assertEqual(stat_data['used_km'], 340)
        self.assertGreaterEqual(len(stat_data['events']), 4)
