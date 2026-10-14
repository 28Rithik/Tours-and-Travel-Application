import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Vehicle, VehicleType, Driver, Party, StaffProfile
from operations.models import Trip, Booking
from core.management.commands.setup_enterprise_roles import Command as SetupRolesCommand


class StaffFleetRosterAndWorkshopPermsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Run enterprise role setup
        cmd = SetupRolesCommand()
        cmd.handle()

        # Users created by setup_enterprise_roles
        cls.karthik = User.objects.get(username='workshop_karthik')
        cls.suresh = User.objects.get(username='ops_suresh')
        cls.admin_user = User.objects.get(username='admin_rajesh')

        # Test Vehicle Type
        cls.vtype = VehicleType.objects.create(name='Innova Crysta 7S', seating_capacity=7)

        # Test Driver
        cls.driver = Driver.objects.create(
            name='K. Palanisamy',
            phone='9842100111',
            license_number='DL-CBE-2020-0012',
            base_depot='Coimbatore Hub',
            status='active'
        )

        # Test Vehicle
        cls.vehicle = Vehicle.objects.create(
            registration_number='TN-38-BZ-9900',
            brand='Toyota',
            model='Innova Crysta',
            vehicle_type=cls.vtype,
            seating_capacity=7,
            base_depot='Coimbatore Hub',
            status='available',
            default_driver=cls.driver,
            current_km=45000
        )

    def setUp(self):
        self.client = Client()

    def test_whatsapp_bot_studio_renders_with_staff_portal(self):
        """Verify WhatsApp Bot studio extends base.html and has the TravelERP sidebar."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/operations/whatsapp-bot/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TravelERP')
        self.assertContains(response, 'WhatsApp Business Bot')
        # Check that base.html elements are rendered
        self.assertContains(response, 'nav-section-title')

    def test_workshop_karthik_permissions(self):
        """Verify Karthik has permissions for vehicle and driver and gets 200 on admin lists."""
        self.assertTrue(self.karthik.has_perm('core.view_vehicle'))
        self.assertTrue(self.karthik.has_perm('core.change_vehicle'))
        self.assertTrue(self.karthik.has_perm('core.view_driver'))

        self.client.force_login(self.karthik)
        resp_v = self.client.get('/admin/core/vehicle/')
        self.assertEqual(resp_v.status_code, 200)

        resp_d = self.client.get('/admin/core/driver/')
        self.assertEqual(resp_d.status_code, 200)

    def test_fleet_vehicles_roster_view(self):
        """Verify dedicated staff vehicle roster view loads with HTTP 200 and KPI cards."""
        self.client.force_login(self.suresh)
        response = self.client.get('/fleet/vehicles/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fleet Assets')
        self.assertContains(response, 'TN-38-BZ-9900')
        self.assertContains(response, 'Toyota')
        self.assertContains(response, 'Register Vehicle')

    def test_fleet_vehicles_roster_add_vehicle_post(self):
        """Verify staff can add a new vehicle via POST directly in the staff portal."""
        self.client.force_login(self.suresh)
        post_data = {
            'action': 'add_vehicle',
            'registration_number': 'TN-38-CA-1122',
            'brand': 'BharatBenz',
            'model': 'Glider 12M Coach',
            'vehicle_type': str(self.vtype.id),
            'seating_capacity': '45',
            'base_depot': 'Coimbatore Hub',
            'ownership_type': 'owned',
            'fuel_type': 'diesel',
            'current_km': '12000',
            'default_driver': str(self.driver.id),
        }
        response = self.client.post('/fleet/vehicles/', data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Vehicle.objects.filter(registration_number='TN-38-CA-1122').exists())
        new_v = Vehicle.objects.get(registration_number='TN-38-CA-1122')
        self.assertEqual(new_v.brand, 'BharatBenz')
        self.assertEqual(new_v.seating_capacity, 45)

    def test_fleet_drivers_roster_view_and_register_post(self):
        """Verify dedicated chauffeur directory loads and allows registering a chauffeur."""
        self.client.force_login(self.suresh)
        get_resp = self.client.get('/fleet/drivers/')
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, 'Chauffeurs')
        self.assertContains(get_resp, 'K. Palanisamy')

        post_data = {
            'action': 'add_driver',
            'name': 'M. Murugan',
            'phone': '9842155667',
            'license_number': 'TN-38-2022-009988',
            'base_depot': 'Coimbatore Hub',
        }
        post_resp = self.client.post('/fleet/drivers/', data=post_data, follow=True)
        self.assertEqual(post_resp.status_code, 200)
        self.assertTrue(Driver.objects.filter(name='M. Murugan').exists())

    def test_api_toggle_vehicle_status_staff(self):
        """Verify 1-click availability toggle between available and maintenance."""
        self.client.force_login(self.suresh)

        # Toggle from available to maintenance
        url = f'/api/fleet/vehicles/{self.vehicle.id}/toggle-status/'
        resp1 = self.client.post(url)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1['status'], 'success')
        self.assertEqual(data1['new_status'], 'maintenance')

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, 'maintenance')

        # Toggle back from maintenance to available
        resp2 = self.client.post(url)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2['status'], 'success')
        self.assertEqual(data2['new_status'], 'available')

    def test_api_toggle_blocked_on_active_trip(self):
        """Verify toggle is rejected with 400 when vehicle is deployed on active trip."""
        today = datetime.date.today()
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=today,
            end_date=today,
            status='started'
        )

        self.client.force_login(self.suresh)
        url = f'/api/fleet/vehicles/{self.vehicle.id}/toggle-status/'
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('active Trip', data['message'])

    def test_operations_suresh_can_access_tire_studio_and_compliance(self):
        """Verify Operations Lead Suresh can access Tire Studio and Compliance without 403."""
        self.client.force_login(self.suresh)
        resp_tire = self.client.get('/maintenance/tire-studio/')
        self.assertEqual(resp_tire.status_code, 200)

        resp_comp = self.client.get('/maintenance/compliance/')
        self.assertEqual(resp_comp.status_code, 200)

    def test_fleet_vehicles_roster_edit_vehicle_post(self):
        """Verify staff can enrich vehicle specs, FASTag, and RTO dates via POST directly in portal."""
        self.client.force_login(self.suresh)
        post_data = {
            'action': 'edit_vehicle',
            'vehicle_id': str(self.vehicle.id),
            'registration_number': self.vehicle.registration_number,
            'brand': 'Toyota Kirloskar',
            'model': 'Innova Crysta 2.4 VX',
            'vehicle_type': str(self.vtype.id),
            'seating_capacity': '7',
            'base_depot': 'Coimbatore Hub',
            'ownership_type': 'owned',
            'fuel_type': 'diesel',
            'current_km': '46500',
            'default_driver': str(self.driver.id),
            'fc_expiry': '2027-05-15',
            'fastag_id': '607417-001-9988',
            'gps_imei': '864209040112233',
            'has_ac': 'on',
            'has_air_suspension': 'on',
            'fuel_tank_capacity': '65',
        }
        resp = self.client.post('/fleet/vehicles/', data=post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.brand, 'Toyota Kirloskar')
        self.assertEqual(self.vehicle.fastag_id, '607417-001-9988')
        self.assertEqual(self.vehicle.gps_imei, '864209040112233')
        self.assertTrue(self.vehicle.has_ac)
        self.assertTrue(self.vehicle.has_air_suspension)
        self.assertEqual(self.vehicle.fc_expiry, datetime.date(2027, 5, 15))
