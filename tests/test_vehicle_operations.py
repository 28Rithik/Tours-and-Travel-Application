import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from core.models import Vehicle, Driver, Party, StaffProfile, InterDepotTransferLog
from fleet_contracts.models import TransportContract, Shift, Route, ContractTripLog
from operations.models import Trip


class VehicleOperationsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='fleet_admin_vo',
            email='fleetops@sivagayathiri.in',
            password='Password@123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role='fleet_manager',
            branch='Coimbatore Hub'
        )
        self.client.force_login(self.user)

        # Chauffeur
        self.driver = Driver.objects.create(
            name="Senthil Kumaran",
            phone="+919876543220",
            license_number="TN38-2018-0019283"
        )

        # Vehicles: 1 healthy, 1 service-due / expired
        today = datetime.date.today()
        self.vehicle_healthy = Vehicle.objects.create(
            registration_number="TN-38-BZ-7701",
            brand="Toyota",
            model="Innova Crysta 2.4 GX+",
            seating_capacity=7,
            status="available",
            base_depot="Coimbatore Hub",
            ownership_type="owned",
            current_km=45000,
            next_service_due_km=50000,
            fc_expiry=today + datetime.timedelta(days=200),
            insurance_expiry=today + datetime.timedelta(days=150),
            pollution_expiry=today + datetime.timedelta(days=90),
            default_driver=self.driver
        )

        self.vehicle_locked = Vehicle.objects.create(
            registration_number="TN-38-BZ-7702",
            brand="Force",
            model="Urbania 4400",
            seating_capacity=17,
            status="maintenance",
            base_depot="Coimbatore Hub",
            ownership_type="owned",
            current_km=62000,
            next_service_due_km=60000,  # Overdue by 2000 km!
            fc_expiry=today - datetime.timedelta(days=10),  # Expired FC!
            insurance_expiry=today + datetime.timedelta(days=50),
            pollution_expiry=today + datetime.timedelta(days=30),
            default_driver=self.driver
        )

        # Customer & Commute Route
        self.customer = Party.objects.create(name="Bosch Coimbatore", party_type="customer")
        self.contract = TransportContract.objects.create(
            name="Bosch IT Corridor Shuttle",
            customer=self.customer,
            start_date=today,
            end_date=today + datetime.timedelta(days=365),
            billing_model="monthly_fixed",
            status="active"
        )
        self.route = Route.objects.create(
            contract=self.contract,
            name="Route 202 - Saravanampatti to CHIL SEZ",
            origin="Saravanampatti",
            destination="CHIL SEZ Coimbatore",
            distance_km=16.0
        )
        self.shift = Shift.objects.create(
            route=self.route,
            shift_name="Day Login",
            direction="login",
            timing="08:00:00"
        )

        # Commute Log with Odometer
        self.commute_run = ContractTripLog.objects.create(
            shift=self.shift,
            vehicle=self.vehicle_healthy,
            driver=self.driver,
            date=today,
            status='completed',
            passenger_count=6,
            opening_km=44980,
            closing_km=45000
        )

    def test_vehicle_detail_360_view(self):
        """Verify Asset 360 View renders mechanical specs, health score, and doc wallet."""
        resp = self.client.get(f'/fleet/vehicles/{self.vehicle_healthy.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TN-38-BZ-7701")
        self.assertContains(resp, "Innova Crysta")
        self.assertContains(resp, "RTO Statutory Document Wallet")
        self.assertContains(resp, "CLEARED FOR DISPATCH")
        self.assertContains(resp, "Senthil Kumaran")

    def test_vehicle_detail_360_dispatch_locked(self):
        """Verify Asset 360 View accurately reflects dispatch lockout for expired assets."""
        resp = self.client.get(f'/fleet/vehicles/{self.vehicle_locked.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TN-38-BZ-7702")
        self.assertContains(resp, "DISPATCH LOCKED")
        self.assertContains(resp, "Automated Dispatch Lock Active")

    def test_fleet_allocation_studio_view(self):
        """Verify Fleet Allocation Studio categorizes fleet into verticals."""
        resp = self.client.get('/fleet/allocation/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fleet Allocation &amp; Capacity Studio")
        self.assertContains(resp, "Corporate IT Shifts")
        self.assertContains(resp, "Depot Standby Float")
        self.assertContains(resp, "Workshop Hold")

    def test_fleet_health_sentry_view(self):
        """Verify Fleet Health Sentry computes composite health score and lists clearance."""
        resp = self.client.get('/fleet/health/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fleet Health &amp; Preventive Maintenance Sentry")
        self.assertContains(resp, "Cleared for Dispatch")
        self.assertContains(resp, "Dispatch Locked")
        self.assertContains(resp, "TN-38-BZ-7701")

    def test_fleet_odometer_ledger_view(self):
        """Verify Odometer & Dead Mileage Ledger audits trip run distance."""
        resp = self.client.get('/fleet/odometer/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Odometer Verification &amp; Dead Mileage Ledger")
        self.assertContains(resp, "TN-38-BZ-7701")
        self.assertContains(resp, "44980 KM")
        self.assertContains(resp, "45000 KM")

    def test_api_log_vehicle_odometer(self):
        """Verify API updates odometer and checks for rollback errors."""
        # Valid update
        resp = self.client.post(
            f'/api/fleet/vehicles/{self.vehicle_healthy.id}/odometer/',
            data=json.dumps({'odometer_km': 45500}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.vehicle_healthy.refresh_from_db()
        self.assertEqual(self.vehicle_healthy.current_km, 45500)

        # Rollback attempt (must fail with 400)
        resp_err = self.client.post(
            f'/api/fleet/vehicles/{self.vehicle_healthy.id}/odometer/',
            data=json.dumps({'odometer_km': 40000}),
            content_type='application/json'
        )
        self.assertEqual(resp_err.status_code, 400)
        self.assertIn("Odometer rollback detected", resp_err.json()['message'])

    def test_api_relocate_vehicle_depot(self):
        """Verify inter-depot relocation order transfers vehicle custody."""
        resp = self.client.post(
            f'/api/fleet/vehicles/{self.vehicle_healthy.id}/relocate/',
            data=json.dumps({
                'destination_depot': 'Chennai Central HQ',
                'reason': 'seasonal_peak',
                'notes': 'Reallocated for IT summit convoy'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.vehicle_healthy.refresh_from_db()
        self.assertEqual(self.vehicle_healthy.base_depot, 'Chennai Central HQ')
        self.assertIn('Chennai Central HQ', self.vehicle_healthy.current_location)

        # Verify audit log
        transfer = InterDepotTransferLog.objects.filter(vehicle=self.vehicle_healthy).first()
        self.assertIsNotNone(transfer)
        self.assertEqual(transfer.destination_depot, 'Chennai Central HQ')

    def test_api_toggle_vehicle_dispatch_lock(self):
        """Verify supervisor manual lock and unlock toggles vehicle maintenance state."""
        # Lock
        resp_lock = self.client.post(
            f'/api/fleet/vehicles/{self.vehicle_healthy.id}/lock/',
            data=json.dumps({'action': 'lock', 'reason': 'Brake shudder reported'}),
            content_type='application/json'
        )
        self.assertEqual(resp_lock.status_code, 200)
        self.vehicle_healthy.refresh_from_db()
        self.assertEqual(self.vehicle_healthy.status, 'maintenance')

        # Unlock
        resp_unlock = self.client.post(
            f'/api/fleet/vehicles/{self.vehicle_healthy.id}/lock/',
            data=json.dumps({'action': 'unlock', 'reason': 'Road test signed off by Chief Mechanic'}),
            content_type='application/json'
        )
        self.assertEqual(resp_unlock.status_code, 200)
        self.vehicle_healthy.refresh_from_db()
        self.assertEqual(self.vehicle_healthy.status, 'available')

