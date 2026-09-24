from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Cleaner, Driver, DriverEmploymentPeriod, Party, RateCard, Vehicle, VehicleType
from finance.models import (
    DriverAdvance,
    DriverAdvanceAllocation,
    DriverSettlement,
    FuelRecord,
    LedgerAdjustment,
    Payment,
    SupplierTripCost,
    TripExpense,
    EmployeePayment,
)
from operations.models import Booking, BulkContract, BulkContractDay, Trip, TripCrewAssignment, TripJourney, ContractVehicleRate, ContractDayRequirement
from statements.models import GeneratedStatement


class Command(BaseCommand):
    help = 'Create repeatable Sivagayathiri Tours and Travels demo data.'

    @transaction.atomic
    def handle(self, *args, **options):
        prefix = 'DEMO-'
        first_names = ['Arun', 'Priya', 'Karthik', 'Meena', 'Ravi', 'Divya', 'Suresh', 'Anitha', 'Vignesh', 'Lakshmi', 'Mohan', 'Deepa', 'Prakash', 'Revathi', 'Gopal', 'Swetha', 'Naveen', 'Kavitha', 'Senthil', 'Ramya']
        last_names = ['Kumar', 'Rajan', 'Reddy', 'Iyer', 'Nair', 'Krishnan', 'Bala', 'Sharma', 'Menon', 'Joseph', 'Subramaniam', 'Das']
        cities = ['Coimbatore', 'Chennai', 'Bengaluru', 'Ooty', 'Mysuru', 'Madurai', 'Salem', 'Erode', 'Tiruppur', 'Trichy', 'Kochi', 'Bengaluru Airport']
        company, _ = Party.objects.get_or_create(
            name='Sivagayathiri Tours and Travels',
            defaults={
                'party_type': 'corporate', 'phone': '0422-4000000',
                'email': 'hello@sivagayathiritravels.example',
                'address': 'Coimbatore, Tamil Nadu', 'billing_cycle': 'monthly',
            },
        )
        parties = [company]
        party_types = ['corporate', 'individual', 'travel_agency', 'hotel', 'other']
        for index in range(1, 101):
            party, _ = Party.objects.get_or_create(
                name=f'{first_names[index % len(first_names)]} {last_names[index % len(last_names)]} {index:03d}',
                defaults={
                    'party_type': party_types[index % len(party_types)],
                    'phone': f'90000{index:05d}',
                    'email': f'customer{index:03d}@demo.example',
                    'address': f'{index} {cities[index % len(cities)]} Road, Tamil Nadu',
                    'billing_cycle': ['weekly', 'monthly', 'per_trip'][index % 3],
                    'credit_period_days': [3, 10, 30, 50][index % 4],
                    'default_day_rate': Decimal('1800') + index * 25,
                    'default_km_rate': Decimal('12.00') + (index % 5),
                },
            )
            parties.append(party)

        suppliers = []
        for index in range(1, 26):
            supplier, _ = Party.objects.get_or_create(
                name=f'{last_names[index % len(last_names)]} City Travels {index:02d}',
                defaults={
                    'party_type': 'supplier', 'phone': f'91000{index:05d}',
                    'address': f'{index} Supplier Road, Coimbatore, Tamil Nadu',
                    'billing_cycle': 'per_trip', 'credit_period_days': 15,
                },
            )
            suppliers.append(supplier)
            parties.append(supplier)

        drivers = []
        for index in range(1, 121):
            employer = suppliers[index % len(suppliers)] if index > 45 else None
            driver, _ = Driver.objects.get_or_create(
                name=f'{first_names[index % len(first_names)]} {last_names[(index + 3) % len(last_names)]} Driver {index:03d}',
                defaults={
                    'employer_party': employer, 'phone': f'92000{index:05d}',
                    'license_number': f'DEMO-LIC-{index:04d}',
                    'status': 'active',
                },
            )
            drivers.append(driver)

        for index in range(1, 31):
            cleaner, _ = Cleaner.objects.get_or_create(
                name=f'{first_names[(index + 7) % len(first_names)]} {last_names[(index + 2) % len(last_names)]} Cleaner {index:03d}',
                defaults={'phone': f'92500{index:05d}', 'joining_date': date(2024, 1, 1), 'status': 'active', 'default_daily_rate': Decimal('500')},
            )
            DriverEmploymentPeriod.objects.get_or_create(driver=drivers[index - 1], joined_on=date(2023, 9, 1), left_on=date(2024, 11, 30), defaults={'notes': f'{prefix} previous employment'})
            DriverEmploymentPeriod.objects.get_or_create(driver=drivers[index - 1], joined_on=date(2025, 9, 1), defaults={'notes': f'{prefix} rejoined employment'})

        vehicle_types = {}
        for type_name in ['Innova Crysta', 'Innova', 'Sedan', 'Tempo Traveller', 'Ertiga']:
            vt, _ = VehicleType.objects.get_or_create(
                name=type_name,
                defaults={
                    'category': 'SUV' if 'Innova' in type_name else 'Sedan' if type_name == 'Sedan' else 'Van',
                    'default_day_rate': 3000 if 'Innova' in type_name else 2500 if type_name == 'Sedan' else 5000,
                    'default_km_rate': 15,
                    'driver_bata': 500,
                    'seating_capacity': 7 if 'Innova' in type_name else 4,
                    'minimum_km_per_day': 250,
                    'extra_km_rate': 18 if 'Innova' in type_name else 15 if type_name == 'Sedan' else 25,
                    'extra_hour_rate': 300,
                    'night_halt_charge': 500,
                    'expected_mileage_kmpl': 11.5 if 'Innova' in type_name else 14.0 if type_name == 'Sedan' else 8.0,
                    'fuel_type': 'diesel' if 'Innova' in type_name else 'petrol' if type_name == 'Sedan' else 'diesel',
                    'transmission_type': 'automatic' if 'Crysta' in type_name else 'manual',
                    'toll_class': 'car' if type_name == 'Sedan' else 'lcv' if 'Traveller' in type_name else 'car',
                    'is_luxury': 'Crysta' in type_name or 'Sedan' in type_name,
                    'has_ac': True,
                    'amenities': 'WiFi, Reclining Seats' if 'Crysta' in type_name or 'Traveller' in type_name else 'Standard',
                }
            )
            vehicle_types[type_name] = vt

        vehicles = []
        for index in range(1, 121):
            outsourced = index > 85
            owner = suppliers[index % len(suppliers)] if outsourced else None
            v_type_str = ['Innova Crysta', 'Innova', 'Sedan', 'Tempo Traveller', 'Ertiga'][index % 5]
            vehicle, _ = Vehicle.objects.get_or_create(
                registration_number=f'TN-DEMO-{index:02d}',
                defaults={
                    'vehicle_type': vehicle_types[v_type_str],
                    'ownership_type': 'outsourced' if outsourced else 'owned',
                    'owner_party': owner, 'brand': 'Toyota' if index % 3 else 'Maruti',
                    'model': 'Demo Model', 'fuel_type': 'diesel',
                    'seating_capacity': 7 if index % 2 else 4, 'current_km': 104000 + index * 100,
                },
            )
            vehicles.append(vehicle)

        rate_cards = []
        for index in range(1, 101):
            customer = parties[1 + ((index - 1) % 100)]
            vehicle = vehicles[(index - 1) % len(vehicles)] if index % 3 == 0 else None
            rate_card, _ = RateCard.objects.get_or_create(
                party=customer, vehicle_type=vehicle.vehicle_type if vehicle else vehicle_types['Innova Crysta'],
                vehicle=vehicle, effective_from=date(2026, 1, 1),
                defaults={
                    'day_rate': Decimal('1900') + index * 10, 'km_rate': Decimal('13.50') + (index % 4),
                    'extra_km_rate': Decimal('16.00'), 'driver_bata': Decimal('400') + (index % 3) * 50,
                    'night_charges': Decimal('300'), 'airport_charges': Decimal('250'),
                    'permit_charges': Decimal('150'), 'other_charges': Decimal('100'),
                },
            )
            rate_cards.append(rate_card)

        bookings = []
        trips = []
        for index in range(1, 1001):
            customer = parties[1 + ((index - 1) % 100)]
            pickup_date = date(2024, 1, 1) + timedelta(days=(index - 1) % 1090)
            vehicle = vehicles[(index - 1) % len(vehicles)]
            driver = drivers[(index - 1) % len(drivers)]
            booking, _ = Booking.objects.get_or_create(
                booking_number=f'BK-DEMO-{index:04d}',
                defaults={
                    'party': customer, 'guest_name': f'{first_names[index % len(first_names)]} {last_names[(index + 5) % len(last_names)]} Guest',
                    'guest_phone': f'93000{index:05d}', 'pickup_location': cities[index % len(cities)],
                    'destination': cities[(index + 3) % len(cities)],
                    'pickup_date': pickup_date, 'pickup_time': time(8 + index % 4, 30),
                    'journey_type': ['local', 'outstation', 'airport', 'round_trip'][index % 4],
                    'vehicle_type': vehicle.vehicle_type,
                },
            )
            bookings.append(booking)
            trip_status = 'started' if index % 10 == 0 else ('assigned' if index % 10 == 1 else 'completed')
            trip, _ = Trip.objects.get_or_create(
                trip_id=f'TR-DEMO-{index:04d}',
                defaults={
                    'booking': booking, 'party': customer, 'guest_name': booking.guest_name,
                    'vehicle': vehicle, 'driver': driver, 'status': trip_status,
                    'start_date': pickup_date, 'end_date': pickup_date + timedelta(days=2 + index % 4),
                    'start_time': booking.pickup_time, 'end_time': time(20, 0),
                    'opening_km': 104000 + index * 100, 'closing_km': 104000 + index * 100 + 300 + index * 10,
                    'billing_model': ['fixed', 'day_km', 'km', 'day'][index % 4],
                    'day_rate': Decimal('2100'), 'km_rate': Decimal('14'),
                    'fixed_amount': Decimal('15000') + index * 100, 'days_count': Decimal(3 + index % 3),
                    'driver_bata': Decimal('900'), 'commission': Decimal('250'),
                },
            )
            trips.append(trip)
            TripJourney.objects.get_or_create(
                trip=trip, start_location='Coimbatore', end_location=booking.destination,
                defaults={'start_km': trip.opening_km, 'end_km': trip.closing_km},
            )

        for index, trip in enumerate(trips, start=1):
            TripExpense.objects.get_or_create(trip=trip, expense_type='toll', date=trip.start_date, description=f'{prefix} toll', defaults={'amount': Decimal(200 + index), 'paid_by': 'company', 'billable_to_customer': True})
            TripExpense.objects.get_or_create(trip=trip, expense_type='parking', date=trip.start_date, description=f'{prefix} parking', defaults={'amount': Decimal(50 + index), 'paid_by': 'company', 'billable_to_customer': True})
            TripExpense.objects.get_or_create(trip=trip, expense_type='water', date=trip.start_date, description=f'{prefix} water bottles', defaults={'amount': Decimal('100'), 'paid_by': 'company', 'billable_to_customer': True})
            TripExpense.objects.get_or_create(trip=trip, expense_type='repair', date=trip.start_date, description=f'{prefix} internal repair', defaults={'amount': Decimal('300'), 'paid_by': 'company', 'billable_to_customer': False})
            FuelRecord.objects.get_or_create(vehicle=trip.vehicle, trip=trip, date=trip.start_date, defaults={'opening_km': trip.opening_km, 'closing_km': trip.closing_km, 'fuel_quantity': Decimal('30'), 'fuel_price': Decimal('100'), 'fuel_station': 'Demo Fuel Station'})
            advance, _ = DriverAdvance.objects.get_or_create(driver=trip.driver, date=trip.start_date, notes=f'{prefix} driver advance', defaults={'amount': Decimal('2000')})
            DriverAdvanceAllocation.objects.get_or_create(advance=advance, trip=trip, defaults={'amount': Decimal('500')})
            DriverSettlement.objects.get_or_create(driver=trip.driver, trip=trip, defaults={'total_days': trip.days_count, 'batta': Decimal('900'), 'advance_adjusted': Decimal('500'), 'settled_on': trip.end_date})
            Payment.objects.get_or_create(party=trip.party, trip=trip, date=trip.end_date, payment_type='customer_receipt', payment_mode=['cash', 'upi', 'card'][index % 3], defaults={'amount': trip.total_amount / 2, 'notes': f'{prefix} customer receipt'})
            if trip.vehicle.ownership_type == 'outsourced':
                supplier = trip.vehicle.owner_party
                SupplierTripCost.objects.get_or_create(trip=trip, vehicle=trip.vehicle, supplier=supplier, date=trip.start_date, defaults={'amount': Decimal('8500'), 'description': f'{prefix} outsourced rental'})
                Payment.objects.get_or_create(party=supplier, trip=trip, date=trip.end_date, payment_type='supplier_payment', payment_mode='bank_transfer', defaults={'amount': Decimal('3000'), 'notes': f'{prefix} supplier payment'})
            if index <= 30:
                EmployeePayment.objects.get_or_create(driver=trip.driver, trip=trip, date=trip.end_date, payment_type='daily_pay', payment_mode='bank_transfer', defaults={'amount': Decimal('1000'), 'notes': f'{prefix} driver pay'})

        cleaners = list(Cleaner.objects.filter(name__contains='Cleaner').order_by('id')[:30])
        for index, trip in enumerate(trips[:30], start=1):
            cleaner = cleaners[index - 1]
            TripCrewAssignment.objects.get_or_create(trip=trip, role='driver', driver=trip.driver)
            TripCrewAssignment.objects.get_or_create(trip=trip, role='cleaner', cleaner=cleaner)
            EmployeePayment.objects.get_or_create(cleaner=cleaner, trip=trip, date=trip.end_date, payment_type='daily_pay', payment_mode='cash', defaults={'amount': Decimal('500'), 'notes': f'{prefix} cleaner pay'})

        for index in range(1, 6):
            contract, _ = BulkContract.objects.get_or_create(name=f'{prefix} Film Shoot Contract {index:02d}', defaults={'customer': parties[1 + index], 'start_date': date(2026, 4, 20), 'end_date': date(2026, 4, 30), 'billing_model': 'per_vehicle_day', 'status': 'active', 'gst_rate': Decimal('5')})
            ContractVehicleRate.objects.get_or_create(contract=contract, vehicle_type=vehicle_types['Innova Crysta'], defaults={'agreed_day_rate': Decimal('3500')})
            ContractVehicleRate.objects.get_or_create(contract=contract, vehicle_type=vehicle_types['Tempo Traveller'], defaults={'agreed_day_rate': Decimal('5500')})
            for day_offset in range(11):
                day, _ = BulkContractDay.objects.get_or_create(contract=contract, date=contract.start_date + timedelta(days=day_offset))
                ContractDayRequirement.objects.get_or_create(contract_day=day, vehicle_type=vehicle_types['Innova Crysta'], defaults={'quantity': 5})
                ContractDayRequirement.objects.get_or_create(contract_day=day, vehicle_type=vehicle_types['Tempo Traveller'], defaults={'quantity': 3 + day_offset})
                for vehicle_index in range(3):
                    vehicle = vehicles[85 + day_offset * 3 + vehicle_index] if index == 5 else vehicles[(index * 5 + day_offset * 3 + vehicle_index) % len(vehicles)]
                    Trip.objects.get_or_create(bulk_contract_day=day, vehicle=vehicle, defaults={'driver': drivers[(index + vehicle_index) % len(drivers)], 'start_time': time(6, 0), 'end_time': time(18, 0), 'status': 'booked'})

        for index, party in enumerate(parties[1:], start=1):
            LedgerAdjustment.objects.get_or_create(party=party, date=date(2026, 5, 1) + timedelta(days=index % 10), description=f'{prefix} adjustment', defaults={'amount': Decimal('0')})

        for index in range(1, 101):
            party = parties[index]
            GeneratedStatement.objects.get_or_create(party=party, from_date=date(2024, 1, 1), to_date=date(2026, 12, 31), file_format='pdf', defaults={'opening_balance': party.opening_balance, 'closing_balance': party.opening_balance})

        self.stdout.write(self.style.SUCCESS('Created or preserved Sivagayathiri demo data.'))
        self.stdout.write('Demo identifiers use BK-DEMO-#### and TR-DEMO-####.')
