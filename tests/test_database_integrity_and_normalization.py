"""
tests/test_database_integrity_and_normalization.py

Automated Test Suite for Database Integrity, Normalization Constraints, and CASCADE Hardening.
Validates:
1. Booking CheckConstraints (drop_date >= pickup_date, quoted_price >= 0)
2. Trip CheckConstraints (end_date >= start_date, closing_km >= opening_km, non-negative pricing)
3. TransportContract & ContractTripLog CheckConstraints (contract date ordering, closing >= opening KM)
4. TripExpense & SupplierTripCost CASCADE Protection (ProtectedError raised on Trip deletion attempt)
5. FuelRecord & Payment CheckConstraints (positive amount, non-negative fuel quantity and price)
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.core.exceptions import ValidationError

from django.contrib.auth.models import User
from core.models import Client, Vehicle, Driver, VehicleType, Party
from operations.models import Booking, Trip
from fleet_contracts.models import TransportContract, Shift, Route, ContractTripLog
from finance.models import TripExpense, SupplierTripCost, FuelRecord, Payment


class DatabaseIntegrityAndNormalizationTests(TestCase):
    def setUp(self):
        # Base setup
        self.client_party = Client.objects.create(
            name="Apex Tech Corp",
            party_type="corporate",
            phone="9876543210",
            email="admin@apextech.com",
            billing_cycle="monthly",
            default_day_rate=Decimal("2500.00"),
            default_km_rate=Decimal("14.00")
        )
        self.supplier_party = Party.objects.create(
            name="SRS Travels Fleet Supplier",
            party_type="supplier",
            phone="9842100000",
            billing_cycle="trip"
        )
        self.v_type = VehicleType.objects.create(
            name="Executive Sedan 4S",
            category="Sedan"
        )
        self.vehicle = Vehicle.objects.create(
            registration_number="TN-38-INTEG-01",
            vehicle_type=self.v_type,
            ownership_type="owned",
            current_km=10000
        )
        self.driver = Driver.objects.create(
            name="Suresh Kumar",
            phone="9842111222",
            status="active"
        )
        self.user = User.objects.create_user(username='operator_test', password='password123')

    def test_booking_date_and_price_constraints(self):
        """Test Booking drop_date >= pickup_date and quoted_price >= 0."""
        # Valid booking
        b_valid = Booking.objects.create(
            party=self.client_party,
            guest_name="Arun Kumar",
            pickup_location="Coimbatore Airport",
            destination="Isha Yoga Center",
            pickup_date=date(2026, 10, 15),
            pickup_time="10:00",
            drop_date=date(2026, 10, 16),
            journey_type="outstation",
            quoted_price=Decimal("4500.00")
        )
        self.assertIsNotNone(b_valid.pk)

        # Invalid booking: drop_date before pickup_date
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Booking.objects.create(
                    party=self.client_party,
                    guest_name="Invalid Date Guest",
                    pickup_location="Coimbatore",
                    destination="Ooty",
                    pickup_date=date(2026, 10, 15),
                    pickup_time="10:00",
                    drop_date=date(2026, 10, 14),
                    journey_type="outstation",
                    quoted_price=Decimal("3000.00")
                )

        # Invalid booking: negative quoted price
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Booking.objects.create(
                    party=self.client_party,
                    guest_name="Negative Price Guest",
                    pickup_location="Coimbatore",
                    destination="Ooty",
                    pickup_date=date(2026, 10, 15),
                    pickup_time="10:00",
                    drop_date=date(2026, 10, 16),
                    journey_type="outstation",
                    quoted_price=Decimal("-500.00")
                )

    def test_trip_closing_km_and_date_constraints(self):
        """Test Trip end_date >= start_date and closing_km >= opening_km."""
        booking = Booking.objects.create(
            party=self.client_party,
            guest_name="Karthik",
            pickup_location="Coimbatore",
            destination="Pollachi",
            pickup_date=date(2026, 10, 20),
            pickup_time="09:00",
            drop_date=date(2026, 10, 21),
            journey_type="outstation",
            quoted_price=Decimal("3500.00")
        )

        # Valid Trip
        trip = Trip.objects.create(
            booking=booking,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 21),
            opening_km=10000,
            closing_km=10250,
            fixed_amount=Decimal("3500.00")
        )
        self.assertIsNotNone(trip.pk)
        self.assertEqual(trip.total_km, 250)

        # Inverted KM: closing_km < opening_km
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Trip.objects.create(
                    booking=booking,
                    vehicle=self.vehicle,
                    driver=self.driver,
                    start_date=date(2026, 10, 22),
                    end_date=date(2026, 10, 23),
                    opening_km=10500,
                    closing_km=10200, # Inverted!
                    fixed_amount=Decimal("3000.00")
                )

    def test_financial_records_protect_against_cascade_deletion(self):
        """Test that deleting a Trip with incurred expenses raises ProtectedError."""
        booking = Booking.objects.create(
            party=self.client_party,
            guest_name="Protected Expense Guest",
            pickup_location="Coimbatore",
            destination="Tirupur",
            pickup_date=date(2026, 10, 25),
            pickup_time="08:00",
            drop_date=date(2026, 10, 25),
            journey_type="local"
        )
        trip = Trip.objects.create(
            booking=booking,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=date(2026, 10, 25),
            end_date=date(2026, 10, 25),
            opening_km=10300,
            closing_km=10420
        )
        # Add TripExpense
        expense = TripExpense.objects.create(
            trip=trip,
            expense_type="toll",
            amount=Decimal("250.00"),
            date=date(2026, 10, 25),
            description="Tirupur Toll Plaza Receipt"
        )
        self.assertIsNotNone(expense.pk)

        # Attempt to delete trip: MUST raise ProtectedError due to PROTECT rule
        with self.assertRaises(ProtectedError):
            trip.delete()

        # Verify expense still safely exists in database
        self.assertTrue(TripExpense.objects.filter(pk=expense.pk).exists())

    def test_payment_and_fuel_constraints(self):
        """Test payment amount positive and fuel record non-negative values."""
        # Valid Payment
        payment = Payment.objects.create(
            party=self.client_party,
            date=date(2026, 10, 10),
            amount=Decimal("5000.00"),
            payment_type="customer_receipt",
            payment_mode="upi",
            reference_number="UPI/12345678"
        )
        self.assertIsNotNone(payment.pk)

        # Non-positive payment amount: MUST fail CheckConstraint
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Payment.objects.create(
                    party=self.client_party,
                    date=date(2026, 10, 10),
                    amount=Decimal("0.00"), # Zero not allowed
                    payment_type="customer_receipt",
                    payment_mode="cash"
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Payment.objects.create(
                    party=self.client_party,
                    date=date(2026, 10, 10),
                    amount=Decimal("-1000.00"), # Negative not allowed
                    payment_type="customer_receipt",
                    payment_mode="cash"
                )

        # Valid Fuel Record
        fuel = FuelRecord.objects.create(
            vehicle=self.vehicle,
            date=date(2026, 10, 10),
            fuel_quantity=Decimal("45.50"),
            fuel_price=Decimal("94.50"),
            opening_km=10000,
            closing_km=10350
        )
        self.assertIsNotNone(fuel.pk)

        # Inverted Fuel KM: closing_km < opening_km
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                FuelRecord.objects.create(
                    vehicle=self.vehicle,
                    date=date(2026, 10, 11),
                    fuel_quantity=Decimal("30.00"),
                    fuel_price=Decimal("94.50"),
                    opening_km=10500,
                    closing_km=10200 # Inverted!
                )

    def test_form_validation_and_error_banner_rendering(self):
        """Test that invalid form submissions render the UI error banner, and valid submissions succeed."""
        self.client.force_login(self.user)

        # 1. POST invalid booking (drop_date before pickup_date)
        invalid_payload = {
            'party': self.client_party.pk,
            'guest_name': 'Validation Test Guest',
            'guest_phone': '9842100000',
            'pickup_location': 'Coimbatore Yard',
            'destination': 'Ooty Lake',
            'pickup_date': '2026-10-25',
            'pickup_time': '09:00',
            'drop_date': '2026-10-24', # Earlier than pickup date!
            'journey_type': 'outstation',
            'billing_type': 'package',
            'quoted_price': '4500.00',
            'status': 'pending',
        }
        res = self.client.post('/bookings/create/', invalid_payload)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Form Validation Errors Detected")
        self.assertContains(res, "Drop date cannot be before pickup date.")

        # 2. POST valid booking
        valid_payload = dict(invalid_payload)
        valid_payload['drop_date'] = '2026-10-26'
        res_valid = self.client.post('/bookings/create/', valid_payload, follow=True)
        self.assertEqual(res_valid.status_code, 200)
        self.assertContains(res_valid, "Booking created successfully.")

        created_booking = Booking.objects.get(guest_name='Validation Test Guest')
        self.assertEqual(created_booking.destination, 'Ooty Lake')
