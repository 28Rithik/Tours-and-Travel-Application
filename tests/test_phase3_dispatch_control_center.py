from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from core.models import Vehicle, Driver, VehicleType, Party
from operations.models import Trip, Booking, WhatsAppBotMessage


class Phase3DispatchControlCenterTests(TestCase):
    """
    Automated verification suite for Phase 3:
    Real-Time Dispatch Control Center, 1-Click Fast Allocation, and WhatsApp Triggers.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin_dispatch', 'admin@travels.in', 'pass123')

        cls.vtype = VehicleType.objects.create(name='Innova Crysta', seating_capacity=7)
        cls.vehicle = Vehicle.objects.create(
            registration_number='TN 38 AA 7788',
            brand='Toyota',
            model='Innova Crysta',
            vehicle_type=cls.vtype,
            status='available'
        )
        cls.driver = Driver.objects.create(
            name='Karthik Murugan',
            phone='9443123456',
            badge_number='TN-DRV-042',
            license_number='DL-TN38-2020-001'
        )
        cls.party = Party.objects.create(
            name='Cognizant Technologies CTS',
            phone='9840112233',
            party_type='customer'
        )
        cls.booking = Booking.objects.create(
            booking_number='BKG-2026-TEST',
            party=cls.party,
            guest_name='Mr. Sundar Pichai',
            guest_phone='9876543210',
            pickup_location='Coimbatore Airport CJB',
            destination='Ooty Club',
            pickup_date=timezone.now().date(),
            pickup_time='08:30:00',
            vehicle_type=cls.vtype,
            status='confirmed',
            quoted_price=Decimal('12500.00')
        )
        cls.trip = Trip.objects.create(
            trip_id='TRIP-2026-999',
            booking=cls.booking,
            party=cls.party,
            guest_name=cls.booking.guest_name,
            start_date=cls.booking.pickup_date,
            start_time=cls.booking.pickup_time,
            status='booked',
            billing_model='day_km',
            fixed_amount=Decimal('12500.00'),
            tracking_token='test-token-dispatch-999'
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_01_dispatch_console_and_tabs(self):
        """Verifies /dispatch/ and /bookings/ render successfully with all tabs and KPIs."""
        # Check /dispatch/ route
        resp = self.client.get('/dispatch/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Dispatch Control Center', resp.content.decode('utf-8'))
        self.assertIn('available_vehicles', resp.context)
        self.assertIn('available_drivers', resp.context)
        self.assertGreaterEqual(resp.context['unassigned_count'], 1)

        # Check tab=unassigned
        resp_unassigned = self.client.get('/dispatch/?tab=unassigned')
        self.assertEqual(resp_unassigned.status_code, 200)
        self.assertEqual(resp_unassigned.context['current_tab'], 'unassigned')

        # Check tab=bookings
        resp_bookings = self.client.get('/dispatch/?tab=bookings')
        self.assertEqual(resp_bookings.status_code, 200)
        self.assertIn('Booking Inquiries', resp_bookings.content.decode('utf-8'))

    def test_02_fast_quick_allocation(self):
        """Verifies 1-Click Fast Allocation endpoint assigns vehicle, driver, and sets status to assigned."""
        resp = self.client.post(
            f'/trips/{self.trip.pk}/quick-assign/',
            {
                'vehicle_id': self.vehicle.pk,
                'driver_id': self.driver.pk,
                'send_whatsapp_driver': '1',
                'send_whatsapp_passenger': '1',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.vehicle, self.vehicle)
        self.assertEqual(self.trip.driver, self.driver)
        self.assertEqual(self.trip.status, 'assigned')

    def test_03_driver_whatsapp_briefing(self):
        """Verifies 1-Click Captain WhatsApp briefing endpoint dispatches duty briefing and logs message."""
        # Ensure trip has driver
        self.trip.driver = self.driver
        self.trip.vehicle = self.vehicle
        self.trip.save()

        resp = self.client.get(
            f'/trips/{self.trip.pk}/broadcast-driver-whatsapp/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')

        # Check WhatsAppBotMessage audit log
        wa_msg = WhatsAppBotMessage.objects.filter(trip=self.trip, intent='driver_briefing').first()
        self.assertIsNotNone(wa_msg)
        self.assertIn('Vanakkam', wa_msg.message_body)
        self.assertIn(self.vehicle.registration_number, wa_msg.message_body)

    def test_04_guest_whatsapp_live_tracking_alert(self):
        """Verifies 1-Click Guest WhatsApp alert dispatches tracking link and logs message."""
        self.trip.driver = self.driver
        self.trip.vehicle = self.vehicle
        self.trip.save()

        resp = self.client.get(
            f'/trips/{self.trip.pk}/broadcast-whatsapp/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')

        # Check WhatsAppBotMessage audit log
        wa_msg = WhatsAppBotMessage.objects.filter(trip=self.trip, intent='dispatch_alert').first()
        self.assertIsNotNone(wa_msg)
        self.assertIn('Namaste', wa_msg.message_body)
        self.assertIn(self.trip.tracking_token, wa_msg.message_body)
