"""
Automated Test Suite for Enterprise Multi-Hub Fleet Isolation & Regional Depot Data Scoping.
Validates:
1. Depot Scope Determination (Super Admin vs. Regional Manager vs. Regional Ops vs. Driver)
2. Scoped Queryset Isolation (Vehicles, Drivers, Trips, Bookings)
3. Live Fleet Mission Control & Telematics Feed (/fleet/live/, /api/fleet/live-feed/)
4. Dispatch Control Center (/dispatch/)
5. Django Admin VehicleAdmin Queryset Scoping
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
import datetime

from core.models import Vehicle, Driver, StaffProfile, VehicleType
from operations.models import Booking, Trip, Client as ClientParty
from core.depot_scoping import (
    DEPOT_CHENNAI, DEPOT_COIMBATORE, DEPOT_MADURAI, DEPOT_BENGALURU,
    get_user_depot_scope, get_scoped_vehicles, get_scoped_drivers,
    get_scoped_trips, get_scoped_bookings
)


class MultiHubDepotScopingTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Ensure a basic VehicleType exists
        self.vtype, _ = VehicleType.objects.get_or_create(
            name='Luxury Volvo Coach',
            defaults={'seating_capacity': 40}
        )

        # 2. Create Users & Staff Profiles across different regional hubs
        # Super Admin at Chennai HQ
        self.user_admin, _ = User.objects.get_or_create(
            username='test_admin_rajesh',
            defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin@test.com'}
        )
        self.user_admin.set_password('pass123')
        self.user_admin.save()
        self.prof_admin, _ = StaffProfile.objects.get_or_create(
            user=self.user_admin,
            defaults={
                'role': 'admin',
                'employee_id': 'TST-ADM-01',
                'branch': DEPOT_CHENNAI,
                'approval_limit_inr': Decimal('2500000.00'),
            }
        )

        # Regional General Manager at Coimbatore Hub
        self.user_mgr, _ = User.objects.get_or_create(
            username='test_mgr_vikram',
            defaults={'is_staff': True, 'is_superuser': False, 'email': 'mgr@test.com'}
        )
        self.user_mgr.set_password('pass123')
        self.user_mgr.save()
        self.prof_mgr, _ = StaffProfile.objects.get_or_create(
            user=self.user_mgr,
            defaults={
                'role': 'manager',
                'employee_id': 'TST-MGR-02',
                'branch': DEPOT_COIMBATORE,
                'approval_limit_inr': Decimal('500000.00'),
            }
        )

        # Regional Operations Lead at Coimbatore Hub (Fenced)
        self.user_ops, _ = User.objects.get_or_create(
            username='test_ops_suresh',
            defaults={'is_staff': True, 'is_superuser': False, 'email': 'ops@test.com'}
        )
        self.user_ops.set_password('pass123')
        self.user_ops.save()
        self.prof_ops, _ = StaffProfile.objects.get_or_create(
            user=self.user_ops,
            defaults={
                'role': 'operations',
                'employee_id': 'TST-OPS-03',
                'branch': DEPOT_COIMBATORE,
                'approval_limit_inr': Decimal('100000.00'),
            }
        )

        # Regional Chauffeur Driver at Madurai Depo (Fenced)
        self.user_driver, _ = User.objects.get_or_create(
            username='test_driver_muthu',
            defaults={'is_staff': True, 'is_superuser': False, 'email': 'drv@test.com'}
        )
        self.user_driver.set_password('pass123')
        self.user_driver.save()
        self.prof_driver, _ = StaffProfile.objects.get_or_create(
            user=self.user_driver,
            defaults={
                'role': 'driver',
                'employee_id': 'TST-DRV-04',
                'branch': DEPOT_MADURAI,
                'approval_limit_inr': Decimal('5000.00'),
            }
        )

        # 3. Create Sample Vehicles across Depots
        self.veh_chennai = Vehicle.objects.create(
            registration_number='TN-01-AA-1001',
            vehicle_type=self.vtype,
            base_depot=DEPOT_CHENNAI,
            status='available'
        )
        self.veh_cbe1 = Vehicle.objects.create(
            registration_number='TN-38-BZ-2001',
            vehicle_type=self.vtype,
            base_depot=DEPOT_COIMBATORE,
            status='available'
        )
        self.veh_cbe2 = Vehicle.objects.create(
            registration_number='TN-38-BZ-2002',
            vehicle_type=self.vtype,
            base_depot=DEPOT_COIMBATORE,
            status='available'
        )
        self.veh_madurai = Vehicle.objects.create(
            registration_number='TN-58-XY-3001',
            vehicle_type=self.vtype,
            base_depot=DEPOT_MADURAI,
            status='available'
        )
        self.veh_blr = Vehicle.objects.create(
            registration_number='KA-01-MJ-4001',
            vehicle_type=self.vtype,
            base_depot=DEPOT_BENGALURU,
            status='available'
        )

        # 4. Create Sample Party & Bookings
        self.party = ClientParty.objects.create(
            name='Infosys Corporate Mobility',
            party_type='corporate',
            billing_cycle='monthly'
        )
        self.booking_cbe = Booking.objects.create(
            party=self.party,
            booking_number='BKG-CBE-901',
            guest_name='Coimbatore Tech Delegation',
            pickup_location='Gandhipuram, Coimbatore',
            destination='Ooty',
            pickup_date=datetime.date(2026, 10, 15),
            drop_date=datetime.date(2026, 10, 17),
            pickup_time=datetime.time(8, 0),
            journey_type='outstation',
            status='confirmed'
        )
        self.booking_madurai = Booking.objects.create(
            party=self.party,
            booking_number='BKG-MDU-902',
            guest_name='Temple Pilgrimage Group',
            pickup_location='Meenakshi Amman Temple, Madurai',
            destination='Rameswaram',
            pickup_date=datetime.date(2026, 10, 16),
            drop_date=datetime.date(2026, 10, 18),
            pickup_time=datetime.time(6, 0),
            journey_type='round_trip',
            status='confirmed'
        )

        # 5. Create Trips
        self.trip_cbe = Trip.objects.create(
            trip_id='TRP-CBE-901',
            booking=self.booking_cbe,
            vehicle=self.veh_cbe1,
            party=self.party,
            start_date=datetime.date(2026, 10, 15),
            end_date=datetime.date(2026, 10, 17),
            status='started'
        )
        self.trip_madurai = Trip.objects.create(
            trip_id='TRP-MDU-902',
            booking=self.booking_madurai,
            vehicle=self.veh_madurai,
            party=self.party,
            start_date=datetime.date(2026, 10, 16),
            end_date=datetime.date(2026, 10, 18),
            status='assigned'
        )

    def test_01_depot_scope_determination(self):
        """Verify role-based clearance logic and toggle privileges."""
        # Super Admin: Global by default, can change depot
        scope_admin = get_user_depot_scope(self.user_admin)
        self.assertIsNone(scope_admin['effective_depot'])
        self.assertTrue(scope_admin['is_global'])
        self.assertTrue(scope_admin['can_change_depot'])

        # Super Admin selecting Coimbatore explicitly
        scope_admin_cbe = get_user_depot_scope(self.user_admin, DEPOT_COIMBATORE)
        self.assertEqual(scope_admin_cbe['effective_depot'], DEPOT_COIMBATORE)

        # Regional General Manager: Defaults to Coimbatore, can toggle to all
        scope_mgr_def = get_user_depot_scope(self.user_mgr)
        self.assertEqual(scope_mgr_def['effective_depot'], DEPOT_COIMBATORE)
        self.assertTrue(scope_mgr_def['can_change_depot'])

        scope_mgr_all = get_user_depot_scope(self.user_mgr, 'all')
        self.assertIsNone(scope_mgr_all['effective_depot'])
        self.assertTrue(scope_mgr_all['is_global'])

        # Regional Operations: Strictly fenced to Coimbatore, cannot escape via query param
        scope_ops_def = get_user_depot_scope(self.user_ops)
        self.assertEqual(scope_ops_def['effective_depot'], DEPOT_COIMBATORE)
        self.assertFalse(scope_ops_def['can_change_depot'])

        # Attempt to bypass fence
        scope_ops_bypass = get_user_depot_scope(self.user_ops, DEPOT_CHENNAI)
        self.assertEqual(scope_ops_bypass['effective_depot'], DEPOT_COIMBATORE)

        # Regional Driver: Strictly fenced to Madurai Depo
        scope_driver = get_user_depot_scope(self.user_driver)
        self.assertEqual(scope_driver['effective_depot'], DEPOT_MADURAI)
        self.assertFalse(scope_driver['can_change_depot'])

    def test_02_scoped_queryset_filtering(self):
        """Verify get_scoped_vehicles and get_scoped_trips accuracy."""
        test_vehicles_qs = Vehicle.objects.filter(
            id__in=[self.veh_chennai.id, self.veh_cbe1.id, self.veh_cbe2.id, self.veh_madurai.id, self.veh_blr.id]
        )

        # Super Admin sees all 5 test vehicles
        admin_vehs = get_scoped_vehicles(self.user_admin, base_qs=test_vehicles_qs)
        self.assertEqual(admin_vehs.count(), 5)

        # Coimbatore Ops sees only 2 Coimbatore vehicles
        cbe_vehs = get_scoped_vehicles(self.user_ops, base_qs=test_vehicles_qs)
        self.assertEqual(cbe_vehs.count(), 2)
        self.assertTrue(all(v.base_depot == DEPOT_COIMBATORE for v in cbe_vehs))

        # Madurai Driver sees only 1 Madurai vehicle
        mdu_vehs = get_scoped_vehicles(self.user_driver, base_qs=test_vehicles_qs)
        self.assertEqual(mdu_vehs.count(), 1)
        self.assertEqual(mdu_vehs.first().registration_number, 'TN-58-XY-3001')

        # Trips Scoping
        test_trips_qs = Trip.objects.filter(id__in=[self.trip_cbe.id, self.trip_madurai.id])
        cbe_trips = get_scoped_trips(self.user_ops, base_qs=test_trips_qs)
        self.assertEqual(cbe_trips.count(), 1)
        self.assertEqual(cbe_trips.first().trip_id, 'TRP-CBE-901')

        mdu_trips = get_scoped_trips(self.user_driver, base_qs=test_trips_qs)
        self.assertEqual(mdu_trips.count(), 1)
        self.assertEqual(mdu_trips.first().trip_id, 'TRP-MDU-902')

    def test_03_fleet_live_mission_control_view(self):
        """Test GET /fleet/live/ with depot scope rendering."""
        # 1. Super Admin sees mission control with can_change_depot=True
        self.client.force_login(self.user_admin)
        resp_admin = self.client.get('/fleet/live/')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, 'mcDepotSelect')

        # 2. Regional Ops sees fenced badge
        self.client.force_login(self.user_ops)
        resp_ops = self.client.get('/fleet/live/')
        self.assertEqual(resp_ops.status_code, 200)
        self.assertContains(resp_ops, 'Coimbatore Hub (Regional Fenced)')

    def test_04_api_fleet_live_feed_telemetry(self):
        """Test GET /api/fleet/live-feed/ returns scoped JSON payload."""
        # Coimbatore Ops: Telemetry JSON includes depot_scope and only Coimbatore vehicles
        self.client.force_login(self.user_ops)
        resp = self.client.get('/api/fleet/live-feed/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('depot_scope', data)
        self.assertEqual(data['depot_scope']['effective_depot'], DEPOT_COIMBATORE)
        self.assertFalse(data['depot_scope']['can_change_depot'])

        # Verify vehicles in feed all belong to Coimbatore Hub
        feed_vehicle_ids = [v['id'] for v in data['vehicles']]
        self.assertIn(self.veh_cbe1.id, feed_vehicle_ids)
        self.assertIn(self.veh_cbe2.id, feed_vehicle_ids)
        self.assertNotIn(self.veh_madurai.id, feed_vehicle_ids)
        self.assertNotIn(self.veh_chennai.id, feed_vehicle_ids)

    def test_05_dispatch_console_scoping(self):
        """Test GET /dispatch/ displays regional scoped trips and resources."""
        self.client.force_login(self.user_ops)
        resp = self.client.get('/dispatch/')
        self.assertEqual(resp.status_code, 200)
        # Should contain Coimbatore trip and not Madurai trip
        self.assertContains(resp, 'TRP-CBE-901')
        self.assertNotContains(resp, 'TRP-MDU-902')

    def test_06_admin_vehicle_queryset_scoping(self):
        """Verify Django Admin VehicleAdmin queryset scoping."""
        from django.test import RequestFactory
        from core.admin import VehicleAdmin
        from django.contrib.admin.sites import AdminSite

        factory = RequestFactory()
        v_admin = VehicleAdmin(Vehicle, AdminSite())

        # Super Admin request
        req_admin = factory.get('/admin/core/vehicle/')
        req_admin.user = self.user_admin
        qs_admin = v_admin.get_queryset(req_admin)
        self.assertIn(self.veh_cbe1, qs_admin)
        self.assertIn(self.veh_madurai, qs_admin)
        self.assertIn(self.veh_chennai, qs_admin)

        # Coimbatore Ops request
        req_ops = factory.get('/admin/core/vehicle/')
        req_ops.user = self.user_ops
        qs_ops = v_admin.get_queryset(req_ops)
        self.assertIn(self.veh_cbe1, qs_ops)
        self.assertIn(self.veh_cbe2, qs_ops)
        self.assertNotIn(self.veh_madurai, qs_ops)
        self.assertNotIn(self.veh_chennai, qs_ops)
