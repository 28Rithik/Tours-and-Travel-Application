import json
import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Vehicle, Driver, Party, StaffProfile
from fleet_contracts.models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractFleetRoster,
    CommuterManifest,
    ContractTripLog,
)
from fleet_commute.models import CommuterBoardingPass
from fleet_commute.dispatch_brain import DispatchBrainEngine


class DispatchBrainTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='dispatch_controller_db',
            email='controller@sivagayathiri.in',
            password='Password@123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role='fleet_manager',
            branch='Coimbatore Hub'
        )
        self.client.force_login(self.user)

        self.today = datetime.date.today()
        self.tomorrow = self.today + datetime.timedelta(days=1)

        # Chauffeurs
        self.driver_1 = Driver.objects.create(
            name="Murugan Senior Chauffeur",
            phone="+919842111001",
            license_number="TN38-2015-0012345",
            status="available"
        )
        self.driver_2 = Driver.objects.create(
            name="Karthik Rested Chauffeur",
            phone="+919842111002",
            license_number="TN38-2018-0098765",
            status="available"
        )

        # Commercial Vehicles
        # 1. 7-seater Innova Crysta (Healthy)
        self.vehicle_muv = Vehicle.objects.create(
            registration_number="TN-38-DB-1001",
            brand="Toyota",
            model="Innova Crysta 2.4 GX+",
            seating_capacity=7,
            status="available",
            base_depot="Coimbatore Central HQ",
            current_km=50000,
            next_service_due_km=60000,
            fc_expiry=self.today + datetime.timedelta(days=180),
            insurance_expiry=self.today + datetime.timedelta(days=180),
            pollution_expiry=self.today + datetime.timedelta(days=180),
            default_driver=self.driver_1
        )

        # 2. 17-seater Force Urbania (Healthy)
        self.vehicle_van = Vehicle.objects.create(
            registration_number="TN-38-DB-1002",
            brand="Force",
            model="Urbania 4400",
            seating_capacity=17,
            status="available",
            base_depot="Coimbatore Central HQ",
            current_km=30000,
            next_service_due_km=40000,
            fc_expiry=self.today + datetime.timedelta(days=180),
            insurance_expiry=self.today + datetime.timedelta(days=180),
            pollution_expiry=self.today + datetime.timedelta(days=180),
            default_driver=self.driver_2
        )

        # 3. 35-seater BharatBenz (Locked - Expired FC)
        self.vehicle_bus_locked = Vehicle.objects.create(
            registration_number="TN-38-DB-1003",
            brand="BharatBenz",
            model="1017 Fixed Glass",
            seating_capacity=35,
            status="maintenance",
            base_depot="Coimbatore Central HQ",
            current_km=85000,
            next_service_due_km=80000, # Overdue
            fc_expiry=self.today - datetime.timedelta(days=5), # Expired
            insurance_expiry=self.today + datetime.timedelta(days=180),
            pollution_expiry=self.today + datetime.timedelta(days=180)
        )

        # Corporate Client & Contracts
        self.customer = Party.objects.create(name="Bosch Tech Park", party_type="customer")
        self.contract = TransportContract.objects.create(
            name="Bosch Tech Park Annual Commute SLA 2026",
            customer=self.customer,
            start_date=self.today - datetime.timedelta(days=30),
            end_date=self.today + datetime.timedelta(days=335),
            billing_model="monthly_fixed",
            status="active"
        )

        # Routes & Stops
        self.route_1 = Route.objects.create(
            contract=self.contract,
            name="Route 101 - Vadavalli to Bosch Campus",
            origin="Vadavalli",
            destination="Bosch Campus CHIL SEZ",
            distance_km=22.0
        )
        self.stop_1 = RouteStop.objects.create(
            route=self.route_1,
            stop_order=1,
            name="Vadavalli Bus Terminus",
            scheduled_offset_minutes=0,
            expected_passenger_count=3
        )
        self.stop_2 = RouteStop.objects.create(
            route=self.route_1,
            stop_order=2,
            name="RS Puram Eye Hospital",
            scheduled_offset_minutes=15,
            expected_passenger_count=3
        )

        # Shifts
        self.shift_morning = Shift.objects.create(
            route=self.route_1,
            shift_name="Morning IT Login",
            direction="inbound",
            timing=datetime.time(7, 30),
            days_of_week="Mon-Fri"
        )
        self.shift_evening = Shift.objects.create(
            route=self.route_1,
            shift_name="Evening IT Logout",
            direction="outbound",
            timing=datetime.time(17, 30),
            days_of_week="Mon-Fri"
        )

        # Roster Allocation
        self.roster_morning = ContractFleetRoster.objects.create(
            contract=self.contract,
            route=self.route_1,
            shift=self.shift_morning,
            primary_vehicle=self.vehicle_muv,
            primary_driver=self.driver_1,
            start_date=self.today - datetime.timedelta(days=30),
            is_active=True
        )

        # Registered Commuters (6 pax total)
        for i in range(1, 7):
            CommuterManifest.objects.create(
                contract=self.contract,
                commuter_type="corporate_employee",
                commuter_id=f"BOSCH-{1000+i}",
                name=f"Engineer {i}",
                phone=f"+91987650000{i}",
                boarding_stop=self.stop_1 if i <= 3 else self.stop_2,
                gender="Female" if i == 1 else "Male",
                is_active=True
            )

    def test_dispatch_brain_studio_view(self):
        """Verify Dispatch Brain Studio renders with planning matrix and KPI decks."""
        resp = self.client.get('/commute/dispatch-brain/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Shift Planning &amp; Dispatch Brain")
        self.assertContains(resp, "Planned Shifts")
        self.assertContains(resp, "Capacity Efficiency")
        self.assertContains(resp, "Cleared for Dispatch")
        self.assertContains(resp, "Bosch Tech Park")

    def test_dispatch_planning_brain_alias_url(self):
        """Verify /dispatch/planning/ alias route works properly."""
        resp = self.client.get('/dispatch/planning/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dispatch Brain Planner")

    def test_api_dispatch_brain_matrix(self):
        """Verify API returns structured JSON planning matrix for date."""
        resp = self.client.get(f'/commute/api/dispatch-brain/matrix/?date={self.tomorrow.strftime("%Y-%m-%d")}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        matrix = data["data"]
        self.assertIn("shifts", matrix)
        self.assertGreaterEqual(matrix["total_shifts"], 1)

    def test_capacity_optimizer_right_sizing(self):
        """Verify capacity optimizer picks right-sized vehicle without wasting capacity."""
        # 6 passengers demand -> Innova Crysta (7 seats) should be chosen over 17-seat Urbania
        veh = DispatchBrainEngine.find_best_vehicle_for_demand(
            pax_demand=6,
            target_date=self.tomorrow,
            preferred_depot="Coimbatore Central HQ"
        )
        self.assertIsNotNone(veh)
        self.assertEqual(veh.registration_number, "TN-38-DB-1001") # Innova Crysta

        # 14 passengers demand -> Urbania (17 seats) should be chosen
        veh_large = DispatchBrainEngine.find_best_vehicle_for_demand(
            pax_demand=14,
            target_date=self.tomorrow,
            preferred_depot="Coimbatore Central HQ"
        )
        self.assertIsNotNone(veh_large)
        self.assertEqual(veh_large.registration_number, "TN-38-DB-1002") # Urbania

    def test_dispatch_lock_exclusion(self):
        """Verify fitness engine flags locked vehicles with expired FC and avoids assigning them."""
        fitness = DispatchBrainEngine.evaluate_vehicle_fitness(self.vehicle_bus_locked, self.tomorrow)
        self.assertFalse(fitness["is_cleared"])
        self.assertTrue(any("expired" in r.lower() or "overdue" in r.lower() for r in fitness["reasons"]))

    def test_auto_optimize_and_dispatch_api(self):
        """Verify 1-click auto optimization provisions trips and boarding passes with OTPs."""
        resp = self.client.post(
            '/commute/api/dispatch-brain/auto-optimize/',
            data=json.dumps({
                'date': self.tomorrow.strftime('%Y-%m-%d'),
                'replace_locked': True
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["trips_created"] + data["trips_updated"], 1)
        self.assertGreaterEqual(data["boarding_passes_created"], 1)

        # Verify persisted trip log
        log = ContractTripLog.objects.filter(shift=self.shift_morning, date=self.tomorrow).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'scheduled')
        self.assertEqual(log.vehicle, self.vehicle_muv)

        # Verify boarding pass with 4-digit OTP
        bp = CommuterBoardingPass.objects.filter(trip_log=log).first()
        self.assertIsNotNone(bp)
        self.assertEqual(len(bp.boarding_otp), 4)

    def test_conflict_detection(self):
        """Verify system detects double-booking when same vehicle is assigned to overlapping shifts."""
        # Create second shift at exact same time with same vehicle
        shift_overlap = Shift.objects.create(
            route=self.route_1,
            shift_name="Duplicate Overlapping Shift",
            direction="inbound",
            timing=datetime.time(7, 30),
            days_of_week="Mon-Fri"
        )
        ContractFleetRoster.objects.create(
            contract=self.contract,
            route=self.route_1,
            shift=shift_overlap,
            primary_vehicle=self.vehicle_muv,
            primary_driver=self.driver_1,
            start_date=self.today - datetime.timedelta(days=10),
            is_active=True
        )

        matrix = DispatchBrainEngine.build_planning_matrix(self.tomorrow)
        self.assertGreaterEqual(matrix["conflict_count"], 1)

    def test_api_dispatch_brain_swap(self):
        """Verify manual resource swap replaces vehicle on trip log with audit note."""
        log = ContractTripLog.objects.create(
            shift=self.shift_morning,
            date=self.tomorrow,
            vehicle=self.vehicle_muv,
            driver=self.driver_1,
            status='scheduled',
            passenger_count=6
        )

        resp = self.client.post(
            '/commute/api/dispatch-brain/swap/',
            data=json.dumps({
                'trip_log_id': log.id,
                'vehicle_id': self.vehicle_van.id,
                'reason': 'Customer requested larger vehicle for luggage'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        log.refresh_from_db()
        self.assertEqual(log.vehicle, self.vehicle_van)
        self.assertEqual(log.is_replacement_vehicle, True)
        self.assertIn("Customer requested larger vehicle", log.delay_reason)

    def test_api_dispatch_brain_broadcast(self):
        """Verify broadcast API returns success delivery payload."""
        resp = self.client.post(
            '/commute/api/dispatch-brain/broadcast/',
            data=json.dumps({'date': self.tomorrow.strftime('%Y-%m-%d')}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")
