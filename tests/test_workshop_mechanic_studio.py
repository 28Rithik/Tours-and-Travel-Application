import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Vehicle, VehicleType, Party
from maintenance.models import (
    PartInventory, ServiceRecord, SparePart,
    SparePartUsageLog, PartPurchaseRequisition, DefectTicket
)
from core.depot_scoping import DEPOT_CHENNAI, DEPOT_COIMBATORE


class WorkshopMechanicStudioTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create staff user with manager / workshop capability
        self.user = User.objects.create_user(
            username='workshop_lead',
            email='workshop@sivagayathiri.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True
        )
        from core.models import StaffProfile
        StaffProfile.objects.create(
            user=self.user,
            role='workshop_manager',
            employee_id='SGT-WRK-01',
            branch=DEPOT_CHENNAI
        )
        self.client.force_login(self.user)

        # Setup Vehicle Type and Vehicle
        self.veh_type = VehicleType.objects.create(name='Tempo Traveller 17S', seating_capacity=17)
        self.vehicle = Vehicle.objects.create(
            registration_number='TN01AB9999',
            vehicle_type=self.veh_type,
            status='available',
            current_km=54000,
            base_depot=DEPOT_CHENNAI,
            brand='Force Motors',
            model='Traveller 3350'
        )

        # Setup Part Inventory items
        self.brake_pads = PartInventory.objects.create(
            part_name='Brake Pads Front Premium Set',
            sku='BRK-FP-101',
            barcode='EAN-8901234567890',
            category='brakes',
            bin_location='BAY-B / RACK-2 / BIN-04',
            unit_of_measure='sets',
            current_stock=10,
            minimum_stock_level=3,
            reorder_quantity=15,
            default_unit_price=Decimal('1850.00'),
            base_depot=DEPOT_CHENNAI,
            is_critical_part=True
        )

        self.oil_filter = PartInventory.objects.create(
            part_name='OEM Spin-On Engine Oil Filter',
            sku='FLT-OIL-302',
            category='filters',
            bin_location='BAY-A / RACK-1 / BIN-12',
            unit_of_measure='pcs',
            current_stock=2,  # Already low stock
            minimum_stock_level=5,
            reorder_quantity=20,
            default_unit_price=Decimal('420.00'),
            base_depot=DEPOT_CHENNAI,
            is_critical_part=False
        )

        # Setup a Service Record (Job Card)
        self.job_card = ServiceRecord.objects.create(
            vehicle=self.vehicle,
            service_type='routine',
            priority='normal',
            status='in_progress',
            assigned_mechanic=self.user,
            mechanic_name='Murugan M',
            bay_number='Bay 2',
            base_depot=DEPOT_CHENNAI,
            date=timezone.now().date(),
            odometer_reading=54000,
            garage_name='Chennai Central Garage',
            description='Periodic 50,000 KM maintenance service & brake inspection.',
            labor_charges=Decimal('800.00')
        )

    def test_part_inventory_model_properties_and_auto_barcode(self):
        """Test PartInventory stock properties and auto barcode assignment."""
        part = PartInventory.objects.create(
            part_name='Coolant Ready Mix 5L Can',
            sku='CLN-5L',
            category='cooling',
            current_stock=8,
            minimum_stock_level=4,
            default_unit_price=Decimal('650.00')
        )
        # Should have auto-generated a barcode since none was provided
        self.assertTrue(part.barcode)
        self.assertTrue(part.barcode.startswith('PRT-CLN-5L'))

        # Check stock status properties
        self.assertFalse(part.is_out_of_stock)
        self.assertFalse(part.is_low_stock)
        self.assertEqual(part.stock_status, 'in_stock')

        # Drop stock to low
        part.current_stock = 4
        part.save()
        self.assertTrue(part.is_low_stock)
        self.assertEqual(part.stock_status, 'low_stock')

        # Drop stock to 0
        part.current_stock = 0
        part.save()
        self.assertTrue(part.is_out_of_stock)
        self.assertEqual(part.stock_status, 'out_of_stock')

    def test_job_card_recalculate_totals_and_vehicle_grounding(self):
        """Test ServiceRecord automatically grounds vehicle in bay and totals spare parts."""
        # Vehicle status should be 'maintenance' while job card is in progress
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, 'maintenance')

        # Add spare part to job card
        sp = SparePart.objects.create(
            service_record=self.job_card,
            inventory_item=self.brake_pads,
            quantity=2,
            unit_price=self.brake_pads.default_unit_price
        )

        self.job_card.refresh_from_db()
        expected_parts_cost = Decimal('3700.00')  # 2 * 1850
        expected_total = Decimal('800.00') + expected_parts_cost  # Labor (800) + Parts (3700) = 4500
        self.assertEqual(self.job_card.parts_total_cost, expected_parts_cost)
        self.assertEqual(self.job_card.total_cost, expected_total)

        # Complete the job card: vehicle should transition back to 'available'
        self.job_card.status = 'completed'
        self.job_card.save()

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, 'available')
        self.assertIsNotNone(self.job_card.completed_at)

    def test_api_scan_spare_part_by_barcode_and_sku(self):
        """Test scanning spare parts via barcode, exact SKU, and partial name."""
        # 1. By exact barcode
        res = self.client.get('/maintenance/api/parts/scan/', {'q': 'EAN-8901234567890'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['found'])
        self.assertEqual(data['part']['sku'], 'BRK-FP-101')
        self.assertEqual(data['part']['current_stock'], 10)

        # 2. By SKU
        res = self.client.get('/maintenance/api/parts/scan/', {'q': 'FLT-OIL-302'})
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['part']['part_name'], 'OEM Spin-On Engine Oil Filter')

        # 3. By partial name
        res = self.client.get('/maintenance/api/parts/scan/', {'q': 'Brake Pads'})
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['part']['id'], self.brake_pads.id)

        # 4. Unknown item
        res = self.client.get('/maintenance/api/parts/scan/', {'q': 'NONEXISTENT-PART-XYZ'})
        data = res.json()
        self.assertFalse(data.get('found', True))

    def test_api_checkout_spare_part_atomic_deduction_and_auto_reorder(self):
        """Test 1-tap checkout deducting stock, logging usage, and triggering auto purchase requisition."""
        initial_stock = self.brake_pads.current_stock  # 10
        checkout_qty = 8  # Will leave stock at 2, below minimum_stock_level of 3

        payload = {
            'job_card_id': self.job_card.id,
            'part_id': self.brake_pads.id,
            'quantity': checkout_qty,
            'checkout_mode': 'camera_qr',
            'barcode_scanned': self.brake_pads.barcode,
            'notes': 'Fitted front axle replacement'
        }

        res = self.client.post(
            '/maintenance/api/parts/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['checkout']['remaining_stock'], 2)
        self.assertTrue(data['auto_requisition_triggered'])

        # Verify PartInventory deducted
        self.brake_pads.refresh_from_db()
        self.assertEqual(self.brake_pads.current_stock, 2)

        # Verify SparePart added to Job Card
        sp = self.job_card.spare_parts.filter(inventory_item=self.brake_pads).first()
        self.assertIsNotNone(sp)
        self.assertEqual(sp.quantity, checkout_qty)
        self.assertTrue(sp.is_inventory_deducted)

        # Verify immutable SparePartUsageLog created
        log = SparePartUsageLog.objects.filter(service_record=self.job_card, inventory_item=self.brake_pads).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.quantity, checkout_qty)
        self.assertEqual(log.total_cost, Decimal('14800.00'))  # 8 * 1850
        self.assertEqual(log.checked_out_by, self.user)

        # Verify PartPurchaseRequisition auto-created
        req = PartPurchaseRequisition.objects.filter(inventory_item=self.brake_pads, status='auto_triggered').first()
        self.assertIsNotNone(req)
        self.assertEqual(req.suggested_quantity, self.brake_pads.reorder_quantity)
        self.assertEqual(req.urgency, 'urgent')  # Because is_critical_part is True

    def test_api_checkout_insufficient_stock_fails_gracefully(self):
        """Test trying to checkout more than available stock returns error without deducting."""
        payload = {
            'job_card_id': self.job_card.id,
            'part_id': self.oil_filter.id,
            'quantity': 5,  # Only 2 available
        }
        res = self.client.post(
            '/maintenance/api/parts/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data['success'])
        self.assertIn('Insufficient stock', data['message'])

        # Verify stock was untouched
        self.oil_filter.refresh_from_db()
        self.assertEqual(self.oil_filter.current_stock, 2)

    def test_api_create_job_card_grounds_vehicle(self):
        """Test creating a new job card through API grounds vehicle into bay."""
        new_veh = Vehicle.objects.create(
            registration_number='TN38CC1234',
            vehicle_type=self.veh_type,
            status='available',
            base_depot=DEPOT_COIMBATORE,
            current_km=12000
        )

        defect = DefectTicket.objects.create(
            vehicle=new_veh,
            reported_by='Driver Ramesh',
            description='Engine overheating on highway',
            status='open'
        )

        payload = {
            'vehicle_id': new_veh.id,
            'service_type': 'breakdown',
            'priority': 'urgent',
            'bay_number': 'Bay 3',
            'mechanic_name': 'Karthik S',
            'description': 'Radiator flush and hose clamp replacement',
            'labor_charges': '1200.00',
            'defect_ticket_id': defect.id,
            'base_depot': DEPOT_COIMBATORE
        }

        res = self.client.post(
            '/maintenance/api/job-card/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])

        # Vehicle must now be in 'maintenance'
        new_veh.refresh_from_db()
        self.assertEqual(new_veh.status, 'maintenance')

        # Defect ticket should be marked in_progress
        defect.refresh_from_db()
        self.assertEqual(defect.status, 'in_progress')

    def test_api_part_quick_restock_resolves_requisition(self):
        """Test 1-click restock adds stock and marks auto requisition received."""
        # Create an auto-triggered requisition
        req = PartPurchaseRequisition.trigger_auto_requisition(self.oil_filter)
        self.assertEqual(req.status, 'auto_triggered')

        payload = {
            'part_id': self.oil_filter.id,
            'quantity': 20
        }
        res = self.client.post(
            '/maintenance/api/parts/restock/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['current_stock'], 22)  # 2 + 20

        # Verify requisition resolved
        req.refresh_from_db()
        self.assertEqual(req.status, 'received')
        self.assertIsNotNone(req.restocked_at)

    def test_workshop_mechanic_studio_view_renders_200(self):
        """Test loading the Workshop Mechanic Studio UI renders cleanly with 200 OK."""
        res = self.client.get('/maintenance/workshop-studio/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Workshop Mechanic Studio')
        self.assertContains(res, self.job_card.job_card_number)
        self.assertContains(res, self.vehicle.registration_number)

    def test_job_card_work_order_print_view_renders_200(self):
        """Test loading the printable A4 work order voucher sheet renders cleanly."""
        res = self.client.get(f'/maintenance/job-card/{self.job_card.id}/print/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Workshop Job Card')
        self.assertContains(res, self.job_card.job_card_number)
        self.assertContains(res, self.vehicle.registration_number)
