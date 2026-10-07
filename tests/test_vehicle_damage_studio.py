import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models import Vehicle, VehicleType
from maintenance.models import VehicleDamageInspection, VehicleDamageMarker

User = get_user_model()


class VehicleDamageStudioTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpassword123'
        )
        self.client.force_login(self.user)

        self.vtype = VehicleType.objects.create(name='SUV 7-Seater', seating_capacity=7)
        self.vehicle = Vehicle.objects.create(
            registration_number='KA-01-DM-9999',
            brand='Toyota',
            model='Innova Crysta',
            vehicle_type=self.vtype,
            seating_capacity=7,
            status='available',
            current_km=45200
        )

    def test_01_damage_marker_studio_view_renders(self):
        """Test the studio renders HTTP 200 with vehicle choices and blueprint canvas."""
        res = self.client.get('/maintenance/damage-marker/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '2D Vehicle Damage Marker')
        self.assertContains(res, 'KA-01-DM-9999')
        self.assertContains(res, 'blueprint-canvas-container')

        # Also test admin URL alias
        admin_res = self.client.get('/admin/maintenance/damage-marker/')
        self.assertEqual(admin_res.status_code, 200)

    def test_02_api_save_checkout_inspection(self):
        """Test departure checkout handover inspection creation with pre-existing damage."""
        payload = {
            'vehicle_id': self.vehicle.pk,
            'inspection_type': 'checkout',
            'vehicle_body_style': 'suv',
            'customer_name': 'Ramesh Kumar',
            'customer_phone': '+91 98450 11223',
            'inspector_name': 'Dispatcher Arjun',
            'odometer_reading': 45200,
            'fuel_level_percent': 100,
            'security_deposit_held': 15000,
            'notes': 'Pre-departure check completed. Vehicle immaculate except minor rear scrape.',
            'markers': [
                {
                    'marker_number': 1,
                    'damage_type': 'scratch',
                    'severity': 'minor',
                    'panel_zone': 'rear_bumper',
                    'x_percent': 85.5,
                    'y_percent': 50.0,
                    'is_pre_existing': True,
                    'is_new_damage': False,
                    'estimated_repair_cost': 1500,
                    'notes': 'Pre-existing minor surface scrape'
                }
            ]
        }

        res = self.client.post(
            '/maintenance/api/damage-inspection/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['total_markers'], 1)
        self.assertEqual(data['new_damage_deductions'], 0.0)
        self.assertEqual(data['deposit_refund_amount'], 15000.0)

        # Confirm DB record
        inspection = VehicleDamageInspection.objects.get(pk=data['inspection_id'])
        self.assertEqual(inspection.vehicle, self.vehicle)
        self.assertEqual(inspection.customer_name, 'Ramesh Kumar')
        self.assertEqual(inspection.markers.count(), 1)
        m = inspection.markers.first()
        self.assertTrue(m.is_pre_existing)
        self.assertFalse(m.is_new_damage)

    def test_03_api_save_checkin_diff_with_deductions(self):
        """Test return check-in handover with new damage, deducting from security deposit."""
        # 1. First create departure baseline
        checkout = VehicleDamageInspection.objects.create(
            vehicle=self.vehicle,
            inspection_type='checkout',
            customer_name='Ramesh Kumar',
            odometer_reading=45200,
            security_deposit_held=Decimal('15000.00'),
            deposit_refund_amount=Decimal('15000.00'),
            deposit_status='held'
        )
        VehicleDamageMarker.objects.create(
            inspection=checkout,
            marker_number=1,
            damage_type='scratch',
            severity='minor',
            panel_zone='rear_bumper',
            x_percent=Decimal('85.50'),
            y_percent=Decimal('50.00'),
            is_pre_existing=True,
            is_new_damage=False,
            estimated_repair_cost=Decimal('1500.00')
        )

        # 2. Return Check-in with 1 pre-existing and 1 new dent on front left door (₹3,500)
        checkin_payload = {
            'vehicle_id': self.vehicle.pk,
            'inspection_type': 'checkin',
            'vehicle_body_style': 'suv',
            'customer_name': 'Ramesh Kumar',
            'customer_phone': '+91 98450 11223',
            'inspector_name': 'Dispatcher Arjun',
            'odometer_reading': 45850,
            'fuel_level_percent': 85,
            'security_deposit_held': 15000,
            'baseline_checkout_id': checkout.pk,
            'notes': 'Return check-in complete. New dent observed on front left door.',
            'markers': [
                {
                    'marker_number': 1,
                    'damage_type': 'scratch',
                    'severity': 'minor',
                    'panel_zone': 'rear_bumper',
                    'x_percent': 85.5,
                    'y_percent': 50.0,
                    'is_pre_existing': True,
                    'is_new_damage': False,
                    'estimated_repair_cost': 1500,
                    'notes': 'Pre-existing minor surface scrape'
                },
                {
                    'marker_number': 2,
                    'damage_type': 'dent',
                    'severity': 'moderate',
                    'panel_zone': 'door_fl',
                    'x_percent': 35.0,
                    'y_percent': 25.0,
                    'is_pre_existing': False,
                    'is_new_damage': True,
                    'estimated_repair_cost': 3500,
                    'notes': 'New dent incurred during trip'
                }
            ]
        }

        res = self.client.post(
            '/maintenance/api/damage-inspection/save/',
            data=json.dumps(checkin_payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['total_markers'], 2)
        # ₹3500 deducted from ₹15000 deposit => net refund ₹11500
        self.assertEqual(data['new_damage_deductions'], 3500.0)
        self.assertEqual(data['deposit_refund_amount'], 11500.0)

        # Vehicle odometer should have updated
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_km, 45850)

    def test_04_api_inspection_detail(self):
        """Test retrieving inspection details and plotted coordinates via API."""
        inspection = VehicleDamageInspection.objects.create(
            vehicle=self.vehicle,
            inspection_type='checkout',
            customer_name='Ananya Sen',
            odometer_reading=45200,
            security_deposit_held=Decimal('10000.00'),
            deposit_status='held'
        )
        VehicleDamageMarker.objects.create(
            inspection=inspection,
            marker_number=1,
            damage_type='crack',
            severity='severe',
            panel_zone='windshield',
            x_percent=Decimal('42.00'),
            y_percent=Decimal('50.00'),
            is_new_damage=False,
            is_pre_existing=True,
            estimated_repair_cost=Decimal('5000.00')
        )

        res = self.client.get(f'/maintenance/api/damage-inspection/{inspection.pk}/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['customer_name'], 'Ananya Sen')
        self.assertEqual(len(data['markers']), 1)
        self.assertEqual(data['markers'][0]['damage_type'], 'crack')
        self.assertEqual(data['markers'][0]['x_percent'], 42.0)

    def test_05_printable_damage_inspection_certificate(self):
        """Test rendering the print-ready handover certificate HTML with plotted pins."""
        inspection = VehicleDamageInspection.objects.create(
            vehicle=self.vehicle,
            inspection_type='checkin',
            customer_name='Vikram Malhotra',
            customer_phone='+91 99887 66554',
            odometer_reading=46100,
            fuel_level_percent=90,
            security_deposit_held=Decimal('20000.00'),
            new_damage_deductions=Decimal('4000.00'),
            deposit_refund_amount=Decimal('16000.00'),
            deposit_status='settled_deduction',
            notes='All accessories accounted for. Scuff on rear bumper.'
        )
        VehicleDamageMarker.objects.create(
            inspection=inspection,
            marker_number=1,
            damage_type='paint_chip',
            severity='minor',
            panel_zone='hood',
            x_percent=Decimal('25.00'),
            y_percent=Decimal('50.00'),
            is_pre_existing=True,
            estimated_repair_cost=Decimal('800.00')
        )
        VehicleDamageMarker.objects.create(
            inspection=inspection,
            marker_number=2,
            damage_type='dent',
            severity='moderate',
            panel_zone='rear_bumper',
            x_percent=Decimal('88.00'),
            y_percent=Decimal('50.00'),
            is_new_damage=True,
            estimated_repair_cost=Decimal('4000.00')
        )

        res = self.client.get(f'/maintenance/damage-inspection/{inspection.pk}/print/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'TRAVEL ERP')
        self.assertContains(res, 'Fleet Operations &amp; Vehicle Handover Certificate')
        self.assertContains(res, 'KA-01-DM-9999')
        self.assertContains(res, 'Vikram Malhotra')
        self.assertContains(res, '₹20000.00')
        self.assertContains(res, '- ₹4000.00')
        self.assertContains(res, '₹16000.00')
        self.assertContains(res, 'cert-pin new-damage')
        self.assertContains(res, 'cert-pin pre-existing')
