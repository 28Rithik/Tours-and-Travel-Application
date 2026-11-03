import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Vehicle, Driver, Party, StaffProfile
from fleet_contracts.models import TransportContract, Shift, Route, ContractTripLog
from operations.models import Trip, Booking
from driver_portal.models import RouteIssueReport


class TransportControlCenterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin_tcc',
            email='tcc@sivagayathiri.in',
            password='Password@123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role='fleet_manager',
            branch='Coimbatore Hub'
        )
        self.client.force_login(self.user)

        # Setup Customer Party
        self.customer = Party.objects.create(
            name="TCS Siruseri Campus",
            party_type="customer"
        )

        # Setup Contract & Route
        self.contract = TransportContract.objects.create(
            name="TCS Siruseri Tech Transport",
            customer=self.customer,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=365),
            billing_model="monthly_fixed",
            status="active"
        )
        self.route = Route.objects.create(
            contract=self.contract,
            name="Route 101 - Gandhipuram to TIDEL",
            origin="Gandhipuram Central",
            destination="TIDEL Park Coimbatore",
            distance_km=14.5
        )
        self.shift = Shift.objects.create(
            route=self.route,
            shift_name="Morning Shift Inbound",
            direction="login",
            timing="07:30:00"
        )

        # Setup Drivers & Vehicles
        self.driver_active = Driver.objects.create(
            name="Karthik Pandian",
            phone="+919876543210",
            license_number="TN38-2019-0091823"
        )
        self.driver_standby = Driver.objects.create(
            name="Murugan Standby",
            phone="+919876543211",
            license_number="TN38-2020-0081726"
        )

        self.vehicle_active = Vehicle.objects.create(
            registration_number="TN-38-BZ-9001",
            brand="Toyota",
            model="Innova Crysta",
            seating_capacity=7,
            status="on_trip",
            base_depot="Coimbatore Hub"
        )
        self.vehicle_delayed = Vehicle.objects.create(
            registration_number="TN-38-BZ-9002",
            brand="Force",
            model="Urbania 4400",
            seating_capacity=17,
            status="on_trip",
            base_depot="Coimbatore Hub"
        )
        self.vehicle_standby = Vehicle.objects.create(
            registration_number="TN-38-BZ-9999",
            brand="Toyota",
            model="Innova Crysta",
            seating_capacity=7,
            status="available",
            base_depot="Coimbatore Hub"
        )

        # Setup Commute Trip Runs for Today
        today = timezone.now().date()
        self.commute_active = ContractTripLog.objects.create(
            shift=self.shift,
            vehicle=self.vehicle_active,
            driver=self.driver_active,
            date=today,
            status='in_progress',
            passenger_count=6,
            delay_minutes=0
        )

        self.commute_delayed = ContractTripLog.objects.create(
            shift=self.shift,
            vehicle=self.vehicle_delayed,
            driver=self.driver_active,
            date=today,
            status='in_progress',
            passenger_count=14,
            delay_minutes=25,
            delay_reason="Waterlogging & Hope College Bottleneck"
        )

        # Log a RouteIssueReport
        RouteIssueReport.objects.create(
            contract_trip_log=self.commute_delayed,
            driver=self.driver_active,
            issue_type='traffic_jam',
            delay_minutes=25,
            notes="Hope College heavy traffic standstill",
            status='reported'
        )

    def test_control_center_page_renders_with_fids(self):
        """Verify Control Center renders successfully with FIDS metric pills and tables."""
        resp = self.client.get('/operations/control-center/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fleet Operations Command")
        self.assertContains(resp, "kpiDelayedCount")
        self.assertContains(resp, "FIDS Wall Board")
        self.assertContains(resp, "initial-trip-monitoring")
        self.assertContains(resp, "fidsWallOverlay")

    def test_api_trip_monitoring_feed(self):
        """Verify the FIDS REST API returns categorized trips and accurate counts."""
        resp = self.client.get('/api/fleet/trip-monitoring/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn('counts', data)
        self.assertIn('active_trips', data)
        self.assertIn('delayed_trips', data)
        self.assertIn('unstarted_trips', data)
        self.assertIn('completed_trips', data)

        # Check counts
        self.assertGreaterEqual(data['counts']['total'], 2)
        self.assertGreaterEqual(data['counts']['delayed'], 1)

        # Verify delayed trip details
        delayed_ids = [t['id'] for t in data['delayed_trips']]
        self.assertIn(f"COMMUTE-{self.commute_delayed.id}", delayed_ids)
        delayed_item = next(t for t in data['delayed_trips'] if t['id'] == f"COMMUTE-{self.commute_delayed.id}")
        self.assertEqual(delayed_item['vehicle_reg'], "TN-38-BZ-9002")
        self.assertGreaterEqual(delayed_item['delay_minutes'], 25)

    def test_api_fleet_live_feed_has_delayed_support(self):
        """Verify live telematics payload includes yellow delayed vehicle classification."""
        resp = self.client.get('/api/fleet/live-feed/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn('summary', data)
        self.assertIn('delayed_count', data['summary'])
        self.assertIn('trip_monitoring', data)

        # Check vehicles list contains the delayed vehicle
        v_delayed = next((v for v in data['vehicles'] if v['id'] == self.vehicle_delayed.id), None)
        self.assertIsNotNone(v_delayed)
        self.assertEqual(v_delayed['status_code'], 'delayed')
        self.assertEqual(v_delayed['status_color'], '#eab308')

    def test_api_trip_standby_swap(self):
        """Verify 1-click Standby Swap rescues a delayed commute run."""
        swap_payload = {
            'trip_type': 'commute',
            'trip_id': self.commute_delayed.id,
            'standby_vehicle_id': self.vehicle_standby.id,
            'driver_id': self.driver_standby.id,
            'reason': 'Traffic bottleneck rescue'
        }
        resp = self.client.post(
            '/api/fleet/trip-standby-swap/',
            data=json.dumps(swap_payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        res_json = resp.json()
        self.assertEqual(res_json['status'], 'success')
        self.assertIn("TN-38-BZ-9999", res_json['message'])

        # Reload commute log from DB
        self.commute_delayed.refresh_from_db()
        self.assertEqual(self.commute_delayed.vehicle, self.vehicle_standby)
        self.assertEqual(self.commute_delayed.driver, self.driver_standby)
        self.assertIn("Standby Swapped to TN-38-BZ-9999", self.commute_delayed.delay_reason)
