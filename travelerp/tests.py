from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import Driver, Party, RateCard, Vehicle
from finance.models import DriverAdvance, DriverSettlement, FuelRecord, Payment, SupplierTripCost, TripExpense
from finance.services import calculate_party_ledger
from operations.models import Booking, Trip
from travelerp.reports import vehicle_profitability


class UiSmokeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ui-user', password='ui-password-123')
        self.party = Party.objects.create(name='UI Party', party_type='corporate')

    def test_public_and_protected_routes(self):
        root_response = self.client.get('/')
        self.assertEqual(root_response.status_code, 302)
        self.assertEqual(root_response['Location'], '/login/?next=/')
        self.assertRedirects(self.client.get('/dashboard/'), '/login/?next=/dashboard/')
        self.assertRedirects(self.client.get('/statements/generate/'), '/login/?next=/statements/generate/')
        self.client.force_login(self.user)
        for url in ['/dashboard/', '/statements/generate/', '/reports/vehicle-profitability/', '/reports/party-profitability/', f'/parties/{self.party.pk}/ledger/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, 'TravelERP')
            self.assertContains(response, 'Admin workspace')

    def test_statement_form_has_all_controls(self):
        self.client.force_login(self.user)
        response = self.client.get('/statements/generate/')
        self.assertContains(response, 'from_date')
        self.assertContains(response, 'to_date')
        self.assertContains(response, 'vehicle')
        self.assertContains(response, 'driver')
        self.assertContains(response, 'status')
        self.assertContains(response, 'file_format')

    def test_full_mock_operations_to_statement_workflow(self):
        driver = Driver.objects.create(name='Mock Driver')
        vehicle = Vehicle.objects.create(registration_number='TN-MOCK-01', vehicle_type='Crysta', current_km=12000)
        RateCard.objects.create(party=self.party, vehicle_type='Crysta', effective_from='2026-01-01', day_rate=2100, km_rate=14, driver_bata=300)
        booking = Booking.objects.create(
            party=self.party, guest_name='Mock Guest', pickup_location='Chennai', destination='Mysore',
            pickup_date='2026-04-10', pickup_time='08:00', journey_type='outstation', vehicle_type='Crysta',
        )
        trip = Trip.objects.create(
            booking=booking, party=self.party, guest_name=booking.guest_name, vehicle=vehicle, driver=driver,
            status='completed', start_date='2026-04-10', end_date='2026-04-12', start_time='08:00',
            end_time='20:00', opening_km=12000, closing_km=12300, billing_model='day_km',
            day_rate=2100, km_rate=14, days_count=3, driver_bata=900,
        )
        TripExpense.objects.create(trip=trip, expense_type='toll', amount=500, date='2026-04-11', paid_by='company')
        FuelRecord.objects.create(vehicle=vehicle, trip=trip, date='2026-04-10', opening_km=12000, closing_km=12300, fuel_quantity=30, fuel_price=100)
        DriverAdvance.objects.create(driver=driver, trip=trip, date='2026-04-10', amount=400, notes='Trip advance')
        DriverSettlement.objects.create(driver=driver, trip=trip, total_days=3, batta=900, advance_adjusted=400, settled_on='2026-04-13')
        Payment.objects.create(party=self.party, trip=trip, date='2026-04-14', amount=2000, payment_type='customer_receipt', payment_mode='upi')
        self.client.force_login(self.user)
        ledger = self.client.get(f'/parties/{self.party.pk}/ledger/')
        self.assertContains(ledger, 'Closing balance')
        self.assertEqual(self.client.get('/reports/vehicle-profitability/').status_code, 200)
        self.assertEqual(self.client.get('/reports/party-profitability/').status_code, 200)
        for file_format, content_type in [('pdf', 'application/pdf'), ('excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')]:
            response = self.client.post('/statements/generate/', {'statement_type': 'party', 'party': self.party.pk, 'from_date': '2026-04-01', 'to_date': '2026-04-30', 'file_format': file_format, 'vehicle': vehicle.pk, 'driver': driver.pk, 'status': 'completed'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], content_type)

    def test_customer_receipt_overrides_legacy_manual_advance_without_double_counting(self):
        booking = Booking.objects.create(party=self.party, guest_name='Receipt Guest', pickup_location='A', destination='B', pickup_date=date(2026, 4, 10), pickup_time='08:00', journey_type='local', vehicle_type='Sedan')
        trip = Trip.objects.create(booking=booking, party=self.party, guest_name='Receipt Guest', billing_model='fixed', fixed_amount=10000, start_date=date(2026, 4, 10), end_date=date(2026, 4, 10))
        Payment.objects.create(party=self.party, trip=trip, date='2026-04-11', amount=5000, payment_type='customer_receipt', payment_mode='cash')
        self.assertEqual(trip.received_amount, Decimal('5000'))
        self.assertEqual(trip.balance, Decimal('5000'))

    def test_full_payment_after_trip_and_late_payment_are_reconciled(self):
        booking = Booking.objects.create(party=self.party, guest_name='Late Guest', pickup_location='A', destination='B', pickup_date=date(2026, 4, 1), pickup_time='08:00', journey_type='local', vehicle_type='Sedan')
        trip = Trip.objects.create(booking=booking, party=self.party, guest_name='Late Guest', billing_model='fixed', fixed_amount=15000, status='completed', start_date=date(2026, 4, 1), end_date=date(2026, 4, 1))
        Payment.objects.create(party=self.party, trip=trip, date='2026-04-06', amount=15000, payment_type='customer_receipt', payment_mode='bank_transfer')
        self.assertEqual(trip.balance, Decimal('0'))
        Payment.objects.create(party=self.party, trip=trip, date='2026-05-21', amount=15000, payment_type='customer_receipt', payment_mode='cash')
        self.assertEqual(trip.received_amount, Decimal('30000'))
        self.assertEqual(calculate_party_ledger(self.party, date(2026, 5, 1), date(2026, 5, 30))['receipt_total'], Decimal('15000'))

    def test_split_cash_gpay_and_card_payments_sum_to_trip_total(self):
        booking = Booking.objects.create(party=self.party, guest_name='Split Guest', pickup_location='A', destination='B', pickup_date=date(2026, 4, 1), pickup_time='08:00', journey_type='local', vehicle_type='Sedan')
        trip = Trip.objects.create(booking=booking, party=self.party, guest_name='Split Guest', billing_model='fixed', fixed_amount=15000, start_date=date(2026, 4, 1), end_date=date(2026, 4, 1))
        for amount, mode in [(5000, 'cash'), (6000, 'upi'), (4000, 'card')]:
            Payment.objects.create(party=self.party, trip=trip, date='2026-04-02', amount=amount, payment_type='customer_receipt', payment_mode=mode)
        self.assertEqual(trip.received_amount, Decimal('15000'))
        self.assertEqual(trip.balance, Decimal('0'))

    def test_actual_km_overrun_and_billable_customer_items_are_included(self):
        vehicle = Vehicle.objects.create(registration_number='TN-EXTRA-01', vehicle_type='Crysta')
        booking = Booking.objects.create(party=self.party, guest_name='Long Trip Guest', pickup_location='A', destination='B', pickup_date=date(2026, 4, 1), pickup_time='08:00', journey_type='outstation', vehicle_type='Crysta')
        trip = Trip.objects.create(booking=booking, party=self.party, guest_name='Long Trip Guest', vehicle=vehicle, billing_model='km', km_rate=14, opening_km=104500, closing_km=106100, status='completed', start_date=date(2026, 4, 1), end_date=date(2026, 4, 1))
        TripExpense.objects.create(trip=trip, expense_type='water', amount=100, date=date(2026, 4, 1), paid_by='company', billable_to_customer=True)
        TripExpense.objects.create(trip=trip, expense_type='snacks', amount=250, date=date(2026, 4, 1), paid_by='company', billable_to_customer=True)
        TripExpense.objects.create(trip=trip, expense_type='repair', amount=500, date=date(2026, 4, 1), paid_by='company', billable_to_customer=False)
        self.assertEqual(trip.used_km, 1600)
        self.assertEqual(trip.bill_value, Decimal('22400'))
        self.assertEqual(trip.total_amount, Decimal('22750'))

    def test_invalid_payment_cannot_be_saved_cleanly(self):
        payment = Payment(party=self.party, date=date(2026, 4, 1), amount=0, payment_type='customer_receipt', payment_mode='cash')
        with self.assertRaises(ValidationError):
            payment.full_clean()

def test_outsourced_vehicle_supplier_cost_reduces_profit(self):
    supplier = Party.objects.create(name='Partner Cab Owner', party_type='supplier')
    vehicle = Vehicle.objects.create(registration_number='TN-OUT-01', vehicle_type='Innova', ownership_type='outsourced', owner_party=supplier)
    booking = Booking.objects.create(party=self.party, guest_name='Outsourced Guest', pickup_location='A', destination='B', pickup_date=date(2026, 4, 15), pickup_time='09:00', journey_type='local', vehicle_type='Innova')
    trip = Trip.objects.create(booking=booking, party=self.party, guest_name='Outsourced Guest', vehicle=vehicle, status='completed', start_date=date(2026, 4, 15), end_date=date(2026, 4, 15), billing_model='fixed', fixed_amount=10000)
    SupplierTripCost.objects.create(trip=trip, supplier=supplier, vehicle=vehicle, date=date(2026, 4, 15), amount=6500, description='Partner cab rental')
    report_row = next(row for row in vehicle_profitability() if row['group'] == vehicle)
    self.assertEqual(report_row['revenue'], Decimal('10000'))
    self.assertEqual(report_row['cost'], Decimal('6500'))
    self.assertEqual(report_row['profit'], Decimal('3500'))

def test_supplier_can_receive_payable_statement_with_supplier_payment(self):
    supplier = Party.objects.create(name='XYZ Travels', party_type='supplier')
    vehicle = Vehicle.objects.create(registration_number='TN-XYZ-01', vehicle_type='Crysta', ownership_type='outsourced', owner_party=supplier)
    booking = Booking.objects.create(party=self.party, guest_name='Supplier Guest', pickup_location='A', destination='B', pickup_date=date(2026, 4, 20), pickup_time='09:00', journey_type='local', vehicle_type='Crysta')
    trip = Trip.objects.create(booking=booking, party=self.party, guest_name='Supplier Guest', vehicle=vehicle, status='completed', start_date=date(2026, 4, 20), end_date=date(2026, 4, 20), billing_model='fixed', fixed_amount=10000)
    SupplierTripCost.objects.create(trip=trip, supplier=supplier, vehicle=vehicle, date=date(2026, 4, 20), amount=6500)
    Payment.objects.create(party=supplier, date=date(2026, 4, 21), amount=2000, payment_type='supplier_payment', payment_mode='bank_transfer')
    self.client.force_login(self.user)
    response = self.client.post('/statements/generate/', {'statement_type': 'party', 'party': supplier.pk, 'from_date': '2026-04-01', 'to_date': '2026-04-30', 'file_format': 'excel'})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
