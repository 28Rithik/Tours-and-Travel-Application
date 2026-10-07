from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, time
from core.models import Vehicle, Supplier, Client, VehicleType
from operations.models import Trip, Booking
from finance.models import FuelRecord, Payment

class FinanceHardeningTests(TestCase):
    def setUp(self):
        self.vtype, _ = VehicleType.objects.get_or_create(name='Sedan')
        self.client = Client.objects.create(name='Test Client', phone='123')
        self.supplier = Supplier.objects.create(name='Test Supplier', phone='456')
        self.owned_vehicle = Vehicle.objects.create(registration_number='TN01-1111', ownership_type='owned', vehicle_type=self.vtype)
        self.booking = Booking.objects.create(
            party=self.client, pickup_date=date(2025, 1, 1), pickup_time=time(10, 0),
            pickup_location='A', destination='B', journey_type='local', vehicle_type=self.vtype, guest_name='Guest'
        )
        
        self.trip = Trip.objects.create(
            booking=self.booking, party=self.client, vehicle=self.owned_vehicle,
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 1),
            status='settled', closing_km=100
        )

    def test_block_fuel_on_settled_trip(self):
        fuel = FuelRecord(
            vehicle=self.owned_vehicle, trip=self.trip, date=date(2025, 1, 1),
            opening_km=0, closing_km=100, fuel_quantity=10, fuel_price=100
        )
        with self.assertRaises(ValidationError) as cm:
            fuel.clean()
        self.assertIn('Cannot add fuel to a trip that is already settled', str(cm.exception))

    def test_negative_fuel_km(self):
        fuel = FuelRecord(
            vehicle=self.owned_vehicle, date=date(2025, 1, 1),
            opening_km=100, closing_km=50, fuel_quantity=10, fuel_price=100
        )
        with self.assertRaises(ValidationError) as cm:
            fuel.clean()
        self.assertIn('Closing kilometres cannot be lower than opening', str(cm.exception))
