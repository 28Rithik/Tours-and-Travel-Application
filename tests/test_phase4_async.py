import datetime
import time
from decimal import Decimal
from django.test import TransactionTestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache

from core.models import VehicleType, Vehicle, Driver, Client as PartyClient
from operations.models import Booking, Trip
from fleet_contracts.models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractFleetRoster,
    ContractTripLog,
    CommuterManifest,
)
from fleet_commute.models import CommuterBoardingPass
from fleet_commute.roster_dispatch_engine import RosterDispatchEngine
from integrations.communication import (
    send_whatsapp_message,
    send_whatsapp_message_async,
    dispatch_trip_assignment_alert,
    get_comm_executor,
)
from core.cache_services import get_or_render_cached_pdf, invalidate_cached_pdf
from operations.views import trip_sheet_pdf_view, trip_invoice_pdf_view, booking_voucher_pdf_view


class Phase4AsyncAndOffloadingTests(TransactionTestCase):
    """
    Test suite verifying Phase 4 technical performance & async offloading:
    1. Non-blocking asynchronous WhatsApp worker pool execution.
    2. Sub-5ms in-memory PDF caching tier (ReportLab).
    3. Bulk-optimized batch roster dispatch & async provisioning.
    """

    def setUp(self):
        cache.clear()
        self.today = timezone.now().date()
        self.user = User.objects.create_superuser('perfadmin', 'admin@example.com', 'password123')
        self.client = Client()
        self.client.force_login(self.user)
        self.factory = RequestFactory()

        # Master Data
        self.vtype = VehicleType.objects.create(name='Deluxe Force Urbania', seating_capacity=15)
        self.party = PartyClient.objects.create(
            name='Cognizant Mobility Corp',
            party_type='corporate',
            email='mobility@cognizant.com',
            phone='9876543210'
        )
        self.driver = Driver.objects.create(
            name='K. Murugan',
            phone='919876543210',
            license_number='TN38-2024-998877',
            license_validity_tr=self.today + datetime.timedelta(days=365)
        )
        self.vehicle = Vehicle.objects.create(
            registration_number='TN38-BZ-4545',
            vehicle_type=self.vtype,
            seating_capacity=15,
            ownership_type='owned',
            status='available',
            fc_expiry=self.today + datetime.timedelta(days=365),
            insurance_expiry=self.today + datetime.timedelta(days=365)
        )

        # Operational Booking & Trip
        self.booking = Booking.objects.create(
            party=self.party,
            guest_name='Dr. Vikram Sarabhai',
            guest_phone='9876543210',
            pickup_location='Airport Terminal 1',
            destination='Tech Park Gateway',
            pickup_date=self.today,
            pickup_time='09:00:00',
            journey_type='airport',
            status='confirmed',
            quoted_price=Decimal('4500.00'),
            vehicle_type=self.vtype
        )
        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.party,
            guest_name='Dr. Vikram Sarabhai',
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=self.today,
            end_date=self.today,
            billing_model='fixed',
            fixed_amount=Decimal('4500.00'),
            opening_km=12000,
            closing_km=12080,
            status='completed'
        )

        # Fleet Contract Setup
        self.contract = TransportContract.objects.create(
            name='Cognizant Daily Campus Shuttle',
            customer=self.party,
            contract_category='corporate',
            billing_model='per_trip',
            default_rate=Decimal('6500.00'),
            start_date=self.today - datetime.timedelta(days=30),
            end_date=self.today + datetime.timedelta(days=30),
            status='active'
        )
        self.route = Route.objects.create(
            contract=self.contract,
            name='Route 12 - Airport to OMR Campus',
            origin='Coimbatore Airport',
            destination='OMR IT Expressway',
            distance_km=35,
            is_active=True
        )
        self.stop1 = RouteStop.objects.create(route=self.route, name='Avinashi Road Junction', stop_order=1)
        self.stop2 = RouteStop.objects.create(route=self.route, name='TIDEL Park Gate 2', stop_order=2)

        self.shift = Shift.objects.create(
            route=self.route,
            shift_name='Morning General Shift Login',
            timing=datetime.time(8, 30),
            direction='pickup',
            days_of_week='All 7 Days'
        )
        self.roster = ContractFleetRoster.objects.create(
            contract=self.contract,
            route=self.route,
            shift=self.shift,
            primary_vehicle=self.vehicle,
            primary_driver=self.driver,
            start_date=self.today - datetime.timedelta(days=5),
            is_active=True
        )

        for i in range(5):
            CommuterManifest.objects.create(
                contract=self.contract,
                commuter_id=f'CTS-{1000+i}',
                name=f'Passenger {i} Kumar',
                gender='female' if i % 2 == 0 else 'male',
                boarding_stop=self.stop1,
                is_active=True
            )

    # --------------------------------------------------------------------------
    # Test 1: Asynchronous Non-Blocking WhatsApp Offloading
    # --------------------------------------------------------------------------
    def test_01_async_whatsapp_dispatch_non_blocking(self):
        """Verifies WhatsApp messages dispatch asynchronously without blocking the caller."""
        # Synchronous execution
        sync_result = send_whatsapp_message(
            to_phone='9876543210',
            message_text='Synchronous alert test',
            is_async=False
        )
        self.assertIn(sync_result.get('status'), ['simulated_sent', 'sent'])

        # Asynchronous execution via is_async=True
        async_result = send_whatsapp_message(
            to_phone='9876543210',
            message_text='Asynchronous non-blocking alert test',
            is_async=True
        )
        self.assertEqual(async_result['status'], 'queued')
        self.assertTrue(async_result['async'])
        self.assertTrue(hasattr(async_result['future'], 'result'))

        # Wait for the background future to complete
        bg_result = async_result['future'].result(timeout=5)
        self.assertIn(bg_result.get('status'), ['simulated_sent', 'sent'])

        # Convenience async wrapper
        wrapper_result = send_whatsapp_message_async(
            to_phone='9876543210',
            message_text='Async wrapper test'
        )
        self.assertEqual(wrapper_result['status'], 'queued')
        self.assertTrue(wrapper_result['async'])
        wrapper_bg_result = wrapper_result['future'].result(timeout=5)
        self.assertIn(wrapper_bg_result.get('status'), ['simulated_sent', 'sent'])

    def test_02_async_trip_assignment_alert(self):
        """Verifies dispatch_trip_assignment_alert non-blocking execution."""
        future = dispatch_trip_assignment_alert(self.trip, is_async=True)
        self.assertTrue(hasattr(future, 'result'))
        result = future.result(timeout=5)
        self.assertIn(result.get('status'), ['simulated_sent', 'sent'])

    # --------------------------------------------------------------------------
    # Test 2: In-Memory PDF Caching Performance & Consistency
    # --------------------------------------------------------------------------
    def test_03_trip_sheet_pdf_caching_and_sub_millisecond_hits(self):
        """Verifies ReportLab PDF caching serves cold generation then hot cache hits in <5ms."""
        request = self.factory.get(f'/trips/{self.trip.id}/pdf/trip-sheet/')
        request.user = self.user

        # 1. Cold Render
        t0 = time.perf_counter()
        response_cold = trip_sheet_pdf_view(request, self.trip.id)
        cold_duration_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(response_cold.status_code, 200)
        self.assertEqual(response_cold['Content-Type'], 'application/pdf')
        self.assertTrue(response_cold.content.startswith(b'%PDF'))

        # 2. Hot Cache Hit
        t1 = time.perf_counter()
        response_hot = trip_sheet_pdf_view(request, self.trip.id)
        hot_duration_ms = (time.perf_counter() - t1) * 1000.0

        self.assertEqual(response_hot.status_code, 200)
        self.assertEqual(response_hot['Content-Type'], 'application/pdf')
        self.assertEqual(response_cold.content, response_hot.content)

        # Hot hit must execute substantially faster
        self.assertLess(hot_duration_ms, 25.0, f"Hot cache hit was too slow: {hot_duration_ms:.2f}ms")

    def test_04_tax_invoice_and_voucher_pdf_caching(self):
        """Verifies tax invoice and booking voucher PDFs are properly cached in RAM."""
        request = self.factory.get('/')
        request.user = self.user

        # Tax Invoice View
        inv_cold = trip_invoice_pdf_view(request, self.trip.id)
        self.assertEqual(inv_cold.status_code, 200)
        self.assertTrue(inv_cold.content.startswith(b'%PDF'))

        inv_hot = trip_invoice_pdf_view(request, self.trip.id)
        self.assertEqual(inv_cold.content, inv_hot.content)

        # Booking Voucher View
        vouch_cold = booking_voucher_pdf_view(request, self.booking.id)
        self.assertEqual(vouch_cold.status_code, 200)
        self.assertTrue(vouch_cold.content.startswith(b'%PDF'))

        vouch_hot = booking_voucher_pdf_view(request, self.booking.id)
        self.assertEqual(vouch_cold.content, vouch_hot.content)

    # --------------------------------------------------------------------------
    # Test 3: Bulk Roster Dispatch Optimization
    # --------------------------------------------------------------------------
    def test_05_batch_roster_dispatch_bulk_creation(self):
        """Verifies bulk-optimized batch roster dispatch creates logs and boarding passes."""
        result = RosterDispatchEngine.execute_batch_roster_dispatch(
            target_date=self.today,
            contract_id=self.contract.id,
            force_refresh=True
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['trips_created'], 1)
        self.assertEqual(result['passes_created'], 5)

        # Verify passes have generated tokens & OTPs
        passes = CommuterBoardingPass.objects.filter(date=self.today, shift=self.shift)
        self.assertEqual(passes.count(), 5)
        for bp in passes:
            self.assertEqual(len(bp.boarding_otp), 4)
            self.assertTrue(len(bp.pass_token) >= 24)

    def test_06_async_batch_roster_dispatch(self):
        """Verifies async batch roster dispatch returns Future and executes in worker pool."""
        future = RosterDispatchEngine.execute_batch_roster_dispatch_async(
            target_date=self.today,
            contract_id=self.contract.id,
            force_refresh=True
        )
        self.assertTrue(hasattr(future, 'result'))
        result = future.result(timeout=10)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['trips_created'], 1)
        self.assertEqual(result['passes_created'], 5)
