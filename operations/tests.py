from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, time, timedelta
from core.models import Vehicle, Party, Driver, Client, Supplier
from operations.models import Trip, Booking

class OperationsHardeningTests(TestCase):
    def setUp(self):
        self.client = Client.objects.create(name='Test Client', phone='123')
        self.supplier = Supplier.objects.create(name='Test Supplier', phone='456')
        self.owned_vehicle = Vehicle.objects.create(registration_number='TN01-1111', ownership_type='owned', vehicle_type='Sedan')
        self.supplier_vehicle = Vehicle.objects.create(registration_number='TN02-2222', ownership_type='outsourced', vehicle_type='Sedan', owner_party=self.supplier)
        self.owned_driver = Driver.objects.create(name='Owned Driver', driver_type='owned', phone='777')
        self.supplier_driver = Driver.objects.create(name='Supplier Driver', driver_type='supplier', phone='888', employer_party=self.supplier)
        
        self.booking = Booking.objects.create(
            party=self.client, pickup_date=date(2025, 1, 1), pickup_time=time(10, 0),
            pickup_location='A', destination='B', journey_type='local', vehicle_type='Sedan', guest_name='Guest'
        )

    def test_missing_closing_km_on_completion(self):
        trip = Trip(
            booking=self.booking, party=self.client, vehicle=self.owned_vehicle, driver=self.owned_driver,
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 1), status='completed'
        )
        with self.assertRaises(ValidationError) as cm:
            trip.clean()
        self.assertIn('closing_km', cm.exception.error_dict)

    def test_supplier_mismatch_owned_vehicle_supplier_driver(self):
        trip = Trip(
            booking=self.booking, party=self.client, vehicle=self.owned_vehicle, driver=self.supplier_driver,
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 1)
        )
        with self.assertRaises(ValidationError) as cm:
            trip.clean()
        self.assertIn('driver', cm.exception.error_dict)

    def test_supplier_mismatch_supplier_vehicle_owned_driver(self):
        trip = Trip(
            booking=self.booking, party=self.client, vehicle=self.supplier_vehicle, driver=self.owned_driver,
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 1)
        )
        with self.assertRaises(ValidationError) as cm:
            trip.clean()
        self.assertIn('driver', cm.exception.error_dict)
