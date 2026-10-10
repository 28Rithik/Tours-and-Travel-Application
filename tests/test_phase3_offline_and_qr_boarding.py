"""
tests/test_phase3_offline_and_qr_boarding.py

Automated Test Suite for Phase 3:
Chauffeur Mobile Cockpit — Offline IndexedDB Queue, PWA Auto-Sync, and Camera QR Boarding Pass Scanner.
Validates:
1. Private Tour Guest Security PIN verification (valid and invalid PINs)
2. Commuter Dynamic QR Boarding Pass token validation (PASS:<token>)
3. Commuter Dynamic 4-Digit OTP validation (PIN:<otp>)
4. Passenger Manifest & Live Attendance API (/api/trip/<trip_id>/passengers/)
5. Driver PWA Trip Cockpit UI rendering with offline sync scripts and camera scanner modal
"""

import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Vehicle, Driver, VehicleType, Party, Client as CoreClient
from operations.models import Trip, Booking, TripMilestoneEvent
from fleet_contracts.models import TransportContract, CommuterManifest, Shift, Route, RouteStop
from fleet_commute.models import CommuterBoardingPass


class Phase3OfflineAndQrBoardingTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Staff User & Driver
        self.user = User.objects.create_user(
            username='chauffeur_tester',
            password='password123',
            is_staff=True
        )
        self.driver = Driver.objects.create(
            name="Rajesh Chauffeur",
            phone="9876543210",
            badge_number="CHF-099",
            status="active"
        )
        self.vtype = VehicleType.objects.create(name="Executive MPV", category="MUV/SUV")
        self.vehicle = Vehicle.objects.create(
            registration_number="TN-38-PWA-9999",
            vehicle_type=self.vtype,
            ownership_type="owned",
            current_km=25000,
            status="active"
        )
        self.party = CoreClient.objects.create(
            name="Siva Gayathri Corporate Tours",
            phone="9842100000"
        )

        # 2. Private Tour Trip
        self.booking = Booking.objects.create(
            booking_number="BK-PHASE3-01",
            party=self.party,
            guest_name="Dr. Ananya Sharma",
            guest_phone="9988776655",
            pickup_location="Airport Terminal 2",
            destination="Hilton Luxury Suites",
            pickup_date=timezone.now().date(),
            pickup_time="09:00:00",
            journey_type="one_way",
            vehicle_type=self.vtype,
            quoted_price=Decimal("4500.00")
        )
        self.private_trip = Trip.objects.create(
            booking=self.booking,
            driver=self.driver,
            vehicle=self.vehicle,
            start_date=timezone.now().date(),
            status="scheduled",
            current_milestone="driver_reached",
            guest_name="Dr. Ananya Sharma",
            pickup_pin="4821",
            is_pin_verified=False
        )

        # 3. Commuter Shuttle Trip Setup
        self.corp_client = CoreClient.objects.create(
            name="Infosys Technologies Ltd",
            phone="9123456789"
        )
        today = timezone.now().date()
        self.contract = TransportContract.objects.create(
            name="Infosys Morning Commute 2026",
            customer=self.corp_client,
            contract_category='corporate',
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=360),
            status='active'
        )
        self.route = Route.objects.create(
            contract=self.contract,
            name="OMR Expressway Line"
        )
        self.stop = RouteStop.objects.create(
            route=self.route,
            name="Sholinganallur Junction",
            stop_order=1
        )
        self.shift = Shift.objects.create(
            route=self.route,
            shift_name="General Morning Shift",
            direction="pickup",
            timing="08:00:00"
        )
        self.commuter1 = CommuterManifest.objects.create(
            contract=self.contract,
            name="Priya Raman",
            commuter_id="INF-8812",
            phone="9876500001",
            gender="female",
            boarding_stop=self.stop
        )
        self.commuter2 = CommuterManifest.objects.create(
            contract=self.contract,
            name="Arun Kumar",
            commuter_id="INF-8813",
            phone="9876500002",
            gender="male",
            boarding_stop=self.stop
        )

        self.commute_trip = Trip.objects.create(
            driver=self.driver,
            vehicle=self.vehicle,
            start_date=today,
            status="started",
            current_milestone="guest_pickup",
            pickup_pin="9999",
            is_pin_verified=False
        )

        self.pass1 = CommuterBoardingPass.objects.create(
            commuter=self.commuter1,
            trip=self.commute_trip,
            date=today,
            shift=self.shift,
            boarding_otp="1234",
            pass_token="test_token_priya_1234567890abcdef",
            is_boarded=False
        )
        self.pass2 = CommuterBoardingPass.objects.create(
            commuter=self.commuter2,
            trip=self.commute_trip,
            date=today,
            shift=self.shift,
            boarding_otp="5678",
            pass_token="test_token_arun_abcdef1234567890",
            is_boarded=False
        )

    def test_verify_boarding_with_valid_pin(self):
        """Validating private tour passenger with correct 4-digit PIN."""
        url = reverse('api-trip-verify-boarding', kwargs={'trip_id': self.private_trip.pk})
        payload = {'passenger_pin': '4821'}

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'guest_pin')
        self.assertTrue(data['is_pin_verified'])

        # Verify DB state
        self.private_trip.refresh_from_db()
        self.assertTrue(self.private_trip.is_pin_verified)
        self.assertIsNotNone(self.private_trip.guest_pickup_at)
        self.assertEqual(self.private_trip.current_milestone, 'on_trip')

        # Verify milestone event logged
        event = TripMilestoneEvent.objects.filter(trip=self.private_trip, milestone='guest_pickup').first()
        self.assertIsNotNone(event)
        self.assertTrue(event.is_pin_verified)
        self.assertEqual(event.passenger_pin_entered, '4821')

    def test_verify_boarding_with_invalid_pin(self):
        """Validating private tour passenger with incorrect 4-digit PIN returns 400 error."""
        url = reverse('api-trip-verify-boarding', kwargs={'trip_id': self.private_trip.pk})
        payload = {'passenger_pin': '0000'}

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid Passenger Security PIN', data['message'])

        self.private_trip.refresh_from_db()
        self.assertFalse(self.private_trip.is_pin_verified)

    def test_verify_boarding_with_commuter_qr_token(self):
        """Validating employee commuter via PASS:<pass_token> camera QR scan."""
        url = reverse('api-trip-verify-boarding', kwargs={'trip_id': self.commute_trip.pk})
        payload = {'qr_data': f"PASS:{self.pass1.pass_token}"}

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'commuter_pass')
        self.assertEqual(data['passenger_name'], 'Priya Raman')
        self.assertEqual(data['total_boarded'], 1)
        self.assertEqual(data['total_manifest'], 2)

        # Verify DB state
        self.pass1.refresh_from_db()
        self.assertTrue(self.pass1.is_boarded)
        self.assertIsNotNone(self.pass1.boarded_at)

    def test_verify_boarding_with_commuter_otp(self):
        """Validating employee commuter via 4-digit OTP entered or scanned as PIN:5678."""
        url = reverse('api-trip-verify-boarding', kwargs={'trip_id': self.commute_trip.pk})
        payload = {'qr_data': "PIN:5678"}

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['passenger_name'], 'Arun Kumar')

        self.pass2.refresh_from_db()
        self.assertTrue(self.pass2.is_boarded)

    def test_passengers_list_api(self):
        """Fetching live passenger manifest checklist."""
        # Board one commuter
        self.pass1.is_boarded = True
        self.pass1.boarded_at = timezone.now()
        self.pass1.save()

        url = reverse('api-trip-passengers-list', kwargs={'trip_id': self.commute_trip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['total_passengers'], 2)
        self.assertEqual(data['total_boarded'], 1)
        self.assertEqual(len(data['passengers']), 2)

    def test_driver_pwa_trip_detail_page_renders_offline_sync_and_qr_modal(self):
        """Ensure driver cockpit renders PWA offline badge, sync script, and QR scanner modal."""
        self.client.force_login(self.user)
        # Setup driver session
        session = self.client.session
        session['driver_id'] = self.driver.pk
        session.save()

        url = reverse('driver_portal:trip_detail', kwargs={'trip_id': self.private_trip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        # Check PWA offline sync engine script inclusion
        self.assertIn('driver_offline_sync.js', content)
        # Check connection badge & queue indicators
        self.assertIn('pwaConnectionBadge', content)
        self.assertIn('offlineQueuePill', content)
        # Check QR scanner camera modal & video viewfinder
        self.assertIn('qrScannerModal', content)
        self.assertIn('pwaQrVideo', content)
        self.assertIn('Scan Passenger QR Boarding Pass', content)
        # Check passenger manifest checklist
        self.assertIn('Passenger Manifest Checklist', content)
