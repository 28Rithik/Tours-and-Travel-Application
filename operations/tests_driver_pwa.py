import base64
import json
from decimal import Decimal
from datetime import date, time

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Vehicle, Driver, VehicleType, Party
from operations.models import Trip, Booking, TripMilestoneEvent
from operations.pdf_generator import render_trip_sheet_pdf
from finance.models import TripExpense


class DriverPwaLifecycleTests(TestCase):
    """
    Comprehensive Automated Test Suite for Phase 3:
    Chauffeur Mobile PWA Cockpit, 7-Milestone Lifecycle, Quick Expense Logger,
    and Customer Digital Signature & Feedback Engine.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='driver_pwa_user',
            password='testpassword123',
            is_staff=True
        )

        self.party = Party.objects.create(
            name="Apex Corporate Mobility",
            phone="9876543210",
            email="dispatch@apex.com",
            gstin="33ABCDE1234F1Z5"
        )

        self.vtype = VehicleType.objects.create(name="Prime Sedan")

        self.vehicle = Vehicle.objects.create(
            registration_number="TN-38-PWA-001",
            brand="Toyota",
            model="Innova Crysta",
            seating_capacity=7,
            vehicle_type=self.vtype,
            ownership_type="owned",
            current_km=45000,
            status="active",
            insurance_expiry=date(2027, 12, 31),
            fc_expiry=date(2027, 12, 31),
            permit_expiry=date(2027, 12, 31),
            tax_expiry=date(2027, 12, 31),
            pollution_expiry=date(2027, 12, 31)
        )

        self.driver = Driver.objects.create(
            name="Karthik Chauffeur",
            phone="9876543211",
            badge_number="CHAUFFEUR-007",
            status="active",
            driver_type="owned",
            license_validity_tr=date(2028, 12, 31)
        )

        self.booking = Booking.objects.create(
            booking_number="BK-PWA-01",
            party=self.party,
            guest_name="Vikram Seth",
            guest_phone="9898989898",
            pickup_location="Coimbatore Airport (CJB)",
            destination="Ooty Botanical Gardens",
            pickup_date=timezone.localdate(),
            pickup_time="09:00:00",
            pax_count=3,
            vehicle_type=self.vtype
        )

        self.trip = Trip.objects.create(
            trip_id="TR-PWA-001",
            booking=self.booking,
            party=self.party,
            guest_name="Vikram Seth",
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            opening_km=45000,
            status="assigned",
            current_milestone="car_pickup",
            pickup_pin="4821"
        )

    def test_milestone_advance_car_pickup(self):
        """Milestone 1: Car pickup updates opening KM, vehicle KM, and marks trip started."""
        url = reverse('api-trip-milestone-advance', kwargs={'trip_id': self.trip.pk})
        response = self.client.post(url, {
            'milestone': 'car_pickup',
            'odometer_reading': '45100',
            'fuel_level_percent': '100',
            'notes': 'Depot departure verified.'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['milestone_index'], 1)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.opening_km, 45100)
        self.assertEqual(self.trip.status, 'started')
        self.assertIsNotNone(self.trip.car_pickup_at)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_km, 45100)

    def test_milestone_advance_driver_reached_with_gps(self):
        """Milestone 2: Driver reached records GPS latitude, longitude, and timestamp."""
        url = reverse('api-trip-milestone-advance', kwargs={'trip_id': self.trip.pk})
        response = self.client.post(url, {
            'milestone': 'driver_reached',
            'gps_latitude': '11.016844',
            'gps_longitude': '76.955832',
            'location_name': 'Coimbatore Airport Terminal 1'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        self.trip.refresh_from_db()
        self.assertIsNotNone(self.trip.driver_reached_at)
        self.assertEqual(self.trip.current_milestone, 'driver_reached')

        event = TripMilestoneEvent.objects.filter(trip=self.trip, milestone='driver_reached').first()
        self.assertIsNotNone(event)
        self.assertEqual(float(event.gps_latitude), 11.016844)

    def test_milestone_guest_pickup_pin_validation(self):
        """Milestone 3: Enforces 4-digit security PIN verification."""
        url = reverse('api-trip-milestone-advance', kwargs={'trip_id': self.trip.pk})

        # Wrong PIN should fail
        bad_response = self.client.post(url, {
            'milestone': 'guest_pickup',
            'passenger_pin': '9999'
        })
        self.assertEqual(bad_response.status_code, 400)
        bad_data = bad_response.json()
        self.assertIn('Invalid Passenger Security PIN', bad_data['message'])

        # Correct PIN should succeed
        good_response = self.client.post(url, {
            'milestone': 'guest_pickup',
            'passenger_pin': '4821'
        })
        self.assertEqual(good_response.status_code, 200)
        good_data = good_response.json()
        self.assertTrue(good_data['is_pin_verified'])

        self.trip.refresh_from_db()
        self.assertTrue(self.trip.is_pin_verified)
        self.assertIsNotNone(self.trip.guest_pickup_at)

    def test_quick_expense_logging_api(self):
        """Quick expense logger captures Fastag toll, parking, diesel and updates running tally."""
        url = reverse('api-trip-quick-expense', kwargs={'trip_id': self.trip.pk})
        response = self.client.post(url, {
            'expense_type': 'toll',
            'amount': '185.00',
            'description': 'Attibele Fastag Plaza',
            'paid_by': 'driver'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['amount'], 185.0)

        self.trip.refresh_from_db()
        self.assertEqual(float(self.trip.total_expenses), 185.0)
        self.assertEqual(TripExpense.objects.filter(trip=self.trip).count(), 1)

    def test_api_trip_customer_signature_and_rating(self):
        """Customer touch signature, 5-star rating, and review feedback remarks are persisted."""
        url = reverse('api-trip-customer-signature', kwargs={'trip_id': self.trip.pk})
        
        # 1x1 transparent PNG data URL for test
        sample_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.client.post(
            url,
            data=json.dumps({
                'customer_signature_data': sample_sig,
                'guest_rating': 5,
                'guest_feedback': 'Exceptional service by Karthik! Punctual and professional.'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['guest_rating'], 5)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.customer_signature_data, sample_sig)
        self.assertEqual(self.trip.guest_rating, 5)
        self.assertEqual(self.trip.guest_feedback, 'Exceptional service by Karthik! Punctual and professional.')
        self.assertIsNotNone(self.trip.customer_signature_at)

    def test_driver_pwa_token_based_access(self):
        """Driver opens mobile URL via ?token=<tracking_token> without password login prompt."""
        url = reverse('driver_portal:trip_detail', kwargs={'trip_id': self.trip.pk}) + f"?token={self.trip.tracking_token}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.trip.trip_id)
        self.assertContains(response, "Vikram Seth")
        self.assertContains(response, "4821")  # Passenger PIN
        self.assertContains(response, "Duty Lifecycle Stage")

    def test_render_trip_sheet_with_digital_signature(self):
        """PDF Generator embeds passenger digital signature image and rating in Trip Sheet."""
        sample_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        self.trip.customer_signature_data = sample_sig
        self.trip.guest_rating = 5
        self.trip.save()

        pdf_bytes = render_trip_sheet_pdf(self.trip)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 5000)
