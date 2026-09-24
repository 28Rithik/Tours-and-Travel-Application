from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from core.models import Vehicle
from maintenance.models import PartInventory, ServiceRecord, SparePart

class MaintenanceHardeningTests(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(registration_number='TN01-1111', vehicle_type='Sedan')
        self.inventory = PartInventory.objects.create(part_name='Brake Pad', current_stock=2, default_unit_price=100)
        self.service = ServiceRecord.objects.create(
            vehicle=self.vehicle, date=date(2025, 1, 1),
            odometer_reading=10000, garage_name='Test Garage', status='in_progress'
        )

    def test_negative_inventory_blocked(self):
        spare = SparePart(
            service_record=self.service,
            inventory_item=self.inventory,
            quantity=4, # More than current_stock of 2
            unit_price=100
        )
        with self.assertRaises(ValidationError) as cm:
            spare.clean()
        self.assertIn('quantity', cm.exception.error_dict)

    def test_valid_inventory_passes(self):
        spare = SparePart(
            service_record=self.service,
            inventory_item=self.inventory,
            quantity=1,
            unit_price=100
        )
        spare.clean() # Should not raise
