import os
import sys
import datetime
from decimal import Decimal
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.contrib.auth.models import User
from core.models import (
    Party, Client, Driver, Vehicle, VehicleType, VehicleCategory, LicenseClass, StaffProfile
)
from core.depot_scoping import DEPOT_COIMBATORE, DEPOT_CHENNAI, DEPOT_ERODE, DEPOT_TIRUPUR
from operations.models import Booking, Trip
from finance.models import PettyCashAccount, PettyCashTransaction

def run_seed():
    print("=" * 80)
    print("SEEDING LIVE OPERATIONS ECOSYSTEM (Drivers, Parties, Bookings & Active Trips)")
    print("=" * 80)

    # 1. License Classes
    lc_lmv, _ = LicenseClass.objects.get_or_create(code='LMV-TR', defaults={'name': 'Light Motor Vehicle - Commercial Transport', 'example_vehicles': 'Innova, Dzire, Ertiga'})
    lc_hmv, _ = LicenseClass.objects.get_or_create(code='HMV-PSV', defaults={'name': 'Heavy Motor Vehicle - Passenger Transport', 'example_vehicles': 'Volvo Bus, BharatBenz, Ashok Leyland'})
    lc_hill, _ = LicenseClass.objects.get_or_create(code='HILL-AUTH', defaults={'name': 'Ghat Road & Hill Driving Endorsement', 'example_vehicles': 'Nilgiris Ooty, Kodaikanal, Valparai'})

    # 2. Corporate & Tourism Clients / Parties
    parties_data = [
        {
            'name': 'Apex Global Corporate Tours',
            'party_type': 'corporate',
            'phone': '+91 98422 10010',
            'email': 'tours@apexglobal.in',
            'address': 'TIDEL Park Coimbatore, Civil Aerodrome Post, Coimbatore 641014',
            'gstin': '33AABCA1234F1Z5',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'Bosch Global Software Technologies (BGSW)',
            'party_type': 'corporate',
            'phone': '+91 98422 20020',
            'email': 'transport.cbe@in.bosch.com',
            'address': 'CHIL SEZ IT Park, Saravanampatti, Coimbatore 641035',
            'gstin': '33AAACB0012P1ZV',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'PSG College of Technology — Student Union',
            'party_type': 'travel_agency',
            'phone': '+91 94431 33445',
            'email': 'studentunion@psgtech.edu',
            'address': 'Avinashi Road, Peelamedu, Coimbatore 641004',
            'gstin': '33AAATP0987G1Z1',
            'billing_cycle': 'trip',
        },
        {
            'name': 'Anand Kumar (Executive Family Tour)',
            'party_type': 'individual',
            'phone': '+91 98411 23456',
            'email': 'anand.k@gmail.com',
            'address': 'Race Course Road, Coimbatore 641018',
            'gstin': '',
            'billing_cycle': 'trip',
        },
        {
            'name': 'Nilgiri Heritage Holidays & Resorts',
            'party_type': 'travel_agency',
            'phone': '+91 94432 77889',
            'email': 'bookings@nilgiriheritage.com',
            'address': 'Commercial Road, Ooty, The Nilgiris 643001',
            'gstin': '33AAAFN5544K1Z8',
            'billing_cycle': 'fortnightly',
        }
    ]

    parties_map = {}
    for pd in parties_data:
        p, _ = Party.objects.get_or_create(
            name=pd['name'],
            defaults=pd
        )
        parties_map[pd['name']] = p
    print(f"✓ Parties verified / created: {len(parties_map)}")

    # 3. Authentic Tamil Nadu Fleet Captains / Chauffeurs
    drivers_data = [
        {
            'name': 'Murugan K. (Captain Murugan)',
            'phone': '+91 98421 11001',
            'driver_type': 'owned',
            'joining_date': datetime.date(2021, 3, 15),
            'status': 'active',
            'base_depot': DEPOT_COIMBATORE,
            'aadhar_number': '7823 4412 9011',
            'bank_account_number': '50100234129841',
            'bank_name': 'HDFC Bank',
            'ifsc_code': 'HDFC0001234',
            'upi_id': 'murugan.cbe@oksbi',
            'license_number': 'TN-38-2015-0012891',
            'licensing_authority': 'TN-38 COIMBATORE NORTH RTO',
            'license_validity_tr': datetime.date(2029, 6, 20),
            'hill_station_experience': True,
            'languages_spoken': 'Tamil, English, Malayalam',
        },
        {
            'name': 'Senthil Kumar R.',
            'phone': '+91 98421 22002',
            'driver_type': 'owned',
            'joining_date': datetime.date(2022, 1, 10),
            'status': 'active',
            'base_depot': DEPOT_COIMBATORE,
            'aadhar_number': '8912 3341 5567',
            'bank_account_number': '20391823901',
            'bank_name': 'State Bank of India',
            'ifsc_code': 'SBIN0001004',
            'upi_id': 'senthil.tour@apl',
            'license_number': 'TN-38-2017-0044192',
            'licensing_authority': 'TN-38 COIMBATORE SOUTH RTO',
            'license_validity_tr': datetime.date(2028, 11, 15),
            'hill_station_experience': True,
            'languages_spoken': 'Tamil, English, Hindi',
        },
        {
            'name': 'Selvam P. (Heavy Multi-Axle Specialist)',
            'phone': '+91 98421 33003',
            'driver_type': 'owned',
            'joining_date': datetime.date(2019, 8, 1),
            'status': 'active',
            'base_depot': DEPOT_COIMBATORE,
            'aadhar_number': '9012 4451 8890',
            'bank_account_number': '601293847581',
            'bank_name': 'Canara Bank',
            'ifsc_code': 'CNRB0002011',
            'upi_id': 'selvam.volvo@icici',
            'license_number': 'TN-37-2014-0099182',
            'licensing_authority': 'TN-37 COIMBATORE SOUTH RTO',
            'license_validity_tr': datetime.date(2029, 3, 30),
            'hill_station_experience': True,
            'languages_spoken': 'Tamil, Malayalam, Kannada',
        },
        {
            'name': 'Manoj Prabhakar',
            'phone': '+91 98421 44004',
            'driver_type': 'owned',
            'joining_date': datetime.date(2023, 5, 20),
            'status': 'active',
            'base_depot': DEPOT_TIRUPUR,
            'aadhar_number': '6712 5590 1234',
            'bank_account_number': '918273645012',
            'bank_name': 'Indian Overseas Bank',
            'ifsc_code': 'IOBA0001122',
            'upi_id': 'manoj.prabha@okhdfcbank',
            'license_number': 'TN-42-2019-0012841',
            'licensing_authority': 'TN-42 TIRUPUR RTO',
            'license_validity_tr': datetime.date(2030, 4, 18),
            'hill_station_experience': False,
            'languages_spoken': 'Tamil, English',
        },
        {
            'name': 'Karthikeyan S.',
            'phone': '+91 98421 55005',
            'driver_type': 'owned',
            'joining_date': datetime.date(2020, 11, 1),
            'status': 'active',
            'base_depot': DEPOT_ERODE,
            'aadhar_number': '5512 8890 3341',
            'bank_account_number': '401928374650',
            'bank_name': 'State Bank of India',
            'ifsc_code': 'SBIN0000832',
            'upi_id': 'karthi.erode@paytm',
            'license_number': 'TN-33-2016-0033281',
            'licensing_authority': 'TN-33 ERODE RTO',
            'license_validity_tr': datetime.date(2029, 8, 25),
            'hill_station_experience': True,
            'languages_spoken': 'Tamil, Malayalam',
        }
    ]

    drivers_map = {}
    for dd in drivers_data:
        d, created = Driver.objects.get_or_create(
            name=dd['name'],
            defaults=dd
        )
        if created:
            d.license_classes.add(lc_lmv, lc_hill)
        drivers_map[dd['name']] = d
    print(f"✓ Drivers verified / created: {len(drivers_map)}")

    # 4. Fetch Key Fleet Vehicles
    v_crysta = Vehicle.objects.filter(brand__icontains='Toyota').first() or Vehicle.objects.filter(registration_number='TN 38 BH 1008').first() or Vehicle.objects.first()
    v_urbania = Vehicle.objects.filter(model__icontains='Urbania').first() or Vehicle.objects.filter(seating_capacity__gte=12).first() or Vehicle.objects.all()[1]
    v_sedan = Vehicle.objects.filter(seating_capacity=4).first() or Vehicle.objects.all()[2]
    v_bus = Vehicle.objects.filter(seating_capacity__gte=30).first() or Vehicle.objects.last()

    print(f"✓ Selected vehicles for operations:")
    print(f"  • SUV/MUV: {v_crysta.registration_number}")
    print(f"  • Urbania/Tempo: {v_urbania.registration_number}")
    print(f"  • Sedan: {v_sedan.registration_number}")
    print(f"  • Coach: {v_bus.registration_number}")

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    two_days_ago = today - datetime.timedelta(days=2)
    tomorrow = today + datetime.timedelta(days=1)
    three_days_later = today + datetime.timedelta(days=3)

    # 5. Seed Realistic Bookings
    bookings_data = [
        {
            'booking_number': 'BK-2026-0001',
            'party': Client.objects.get(pk=parties_map['Anand Kumar (Executive Family Tour)'].pk),
            'guest_name': 'Anand Kumar & Family',
            'guest_phone': '+91 98411 23456',
            'pickup_location': 'Race Course, Coimbatore',
            'destination': 'Ooty & Coonoor Heritage Circuit (3D2N)',
            'pickup_date': today,
            'pickup_time': datetime.time(7, 30),
            'drop_date': three_days_later,
            'journey_type': 'outstation',
            'billing_type': 'package',
            'quoted_price': Decimal('22500.00'),
            'expected_km': 450,
            'status': 'confirmed',
        },
        {
            'booking_number': 'BK-2026-0002',
            'party': Client.objects.get(pk=parties_map['Bosch Global Software Technologies (BGSW)'].pk),
            'guest_name': 'Dr. Matthias Weber / Corporate Delegation',
            'guest_phone': '+91 98422 20020',
            'pickup_location': 'CHIL SEZ IT Park, Saravanampatti',
            'destination': 'Kodaikanal Leadership Conclave (2D1N)',
            'pickup_date': today,
            'pickup_time': datetime.time(6, 0),
            'drop_date': tomorrow,
            'journey_type': 'outstation',
            'billing_type': 'day_km',
            'quoted_price': Decimal('28000.00'),
            'expected_km': 550,
            'status': 'confirmed',
        },
        {
            'booking_number': 'BK-2026-0003',
            'party': Client.objects.get(pk=parties_map['Apex Global Corporate Tours'].pk),
            'guest_name': 'Sneha Nair (Airport Transfer)',
            'guest_phone': '+91 98422 10010',
            'pickup_location': 'Coimbatore Airport (CJB)',
            'destination': 'Isha Yoga Center, Velliangiri Foothills',
            'pickup_date': yesterday,
            'pickup_time': datetime.time(10, 0),
            'drop_date': yesterday,
            'journey_type': 'airport',
            'billing_type': 'package',
            'quoted_price': Decimal('3200.00'),
            'expected_km': 95,
            'status': 'completed',
        },
        {
            'booking_number': 'BK-2026-0004',
            'party': Client.objects.get(pk=parties_map['PSG College of Technology — Student Union'].pk),
            'guest_name': 'Prof. Balasubramaniam (Head of Tour)',
            'guest_phone': '+91 94431 33445',
            'pickup_location': 'PSG Tech Main Gate, Peelamedu',
            'destination': 'Munnar & Kochi IV Expedition (4D3N)',
            'pickup_date': two_days_ago,
            'pickup_time': datetime.time(5, 0),
            'drop_date': today,
            'journey_type': 'outstation',
            'billing_type': 'package',
            'quoted_price': Decimal('85000.00'),
            'expected_km': 980,
            'status': 'completed',
        },
    ]

    bookings_map = {}
    for bd in bookings_data:
        b, _ = Booking.objects.get_or_create(
            booking_number=bd['booking_number'],
            defaults=bd
        )
        bookings_map[bd['booking_number']] = b
    print(f"✓ Bookings verified / created: {len(bookings_map)}")

    # 6. Seed Realistic Trips (Active On-Duty & Completed for Settlement)
    trips_data = [
        # Trip 1: ACTIVE ON-DUTY (Innova Crysta to Ooty)
        {
            'trip_id': 'TRIP-2026-0012',
            'booking': bookings_map['BK-2026-0001'],
            'party': parties_map['Anand Kumar (Executive Family Tour)'],
            'guest_name': 'Anand Kumar & Family',
            'vehicle': v_crysta,
            'driver': drivers_map['Murugan K. (Captain Murugan)'],
            'status': 'started',
            'start_date': today,
            'end_date': three_days_later,
            'start_time': datetime.time(7, 30),
            'opening_km': v_crysta.current_km or 54200,
            'billing_model': 'fixed',
            'fixed_amount': Decimal('22500.00'),
            'days_count': 3,
            'driver_bata': Decimal('1500.00'),
            'driver_handover_status': 'started',
            'current_milestone': 'on_trip',
            'notes': 'Outstation family holiday. Stepney & fastag verified by dispatcher.',
        },
        # Trip 2: ACTIVE ON-DUTY (Force Urbania to Kodaikanal)
        {
            'trip_id': 'TRIP-2026-0014',
            'booking': bookings_map['BK-2026-0002'],
            'party': parties_map['Bosch Global Software Technologies (BGSW)'],
            'guest_name': 'Dr. Matthias Weber',
            'vehicle': v_urbania,
            'driver': drivers_map['Senthil Kumar R.'],
            'status': 'started',
            'start_date': today,
            'end_date': tomorrow,
            'start_time': datetime.time(6, 0),
            'opening_km': v_urbania.current_km or 48100,
            'billing_model': 'day_km',
            'day_rate': Decimal('9000.00'),
            'km_rate': Decimal('24.00'),
            'days_count': 2,
            'driver_bata': Decimal('1200.00'),
            'driver_handover_status': 'started',
            'current_milestone': 'on_trip',
            'notes': 'Corporate leadership team. Clean seat covers and bottled water loaded.',
        },
        # Trip 3: COMPLETED (Swift Dzire Airport Transfer - Ready for Settlement!)
        {
            'trip_id': 'TRIP-2026-0010',
            'booking': bookings_map['BK-2026-0003'],
            'party': parties_map['Apex Global Corporate Tours'],
            'guest_name': 'Sneha Nair',
            'vehicle': v_sedan,
            'driver': drivers_map['Manoj Prabhakar'],
            'status': 'completed',
            'start_date': yesterday,
            'end_date': yesterday,
            'start_time': datetime.time(10, 0),
            'end_time': datetime.time(14, 30),
            'opening_km': (v_sedan.current_km or 35000) - 110,
            'closing_km': v_sedan.current_km or 35000,
            'billing_model': 'fixed',
            'fixed_amount': Decimal('3200.00'),
            'days_count': 1,
            'driver_bata': Decimal('500.00'),
            'driver_handover_status': 'ended',
            'current_milestone': 'car_drop',
            'notes': 'Airport run completed smoothly. Driver collected Rs 3200 cash.',
        },
        # Trip 4: COMPLETED (Volvo Bus IV - Ready for Settlement & Bata Payout!)
        {
            'trip_id': 'TRIP-2026-0008',
            'booking': bookings_map['BK-2026-0004'],
            'party': parties_map['PSG College of Technology — Student Union'],
            'guest_name': 'Prof. Balasubramaniam',
            'vehicle': v_bus,
            'driver': drivers_map['Selvam P. (Heavy Multi-Axle Specialist)'],
            'status': 'completed',
            'start_date': two_days_ago,
            'end_date': today,
            'start_time': datetime.time(5, 0),
            'end_time': datetime.time(18, 0),
            'opening_km': (v_bus.current_km or 112000) - 980,
            'closing_km': v_bus.current_km or 112000,
            'billing_model': 'fixed',
            'fixed_amount': Decimal('85000.00'),
            'days_count': 3,
            'driver_bata': Decimal('3000.00'),
            'driver_handover_status': 'ended',
            'current_milestone': 'car_drop',
            'notes': 'Kerala tour completed. Toll receipts & diesel slip submitted at depot.',
        }
    ]

    for td in trips_data:
        t, created = Trip.objects.get_or_create(
            trip_id=td['trip_id'],
            defaults=td
        )
        if created:
            # Set vehicle to on_trip if started
            if td['status'] == 'started' and td['vehicle']:
                td['vehicle'].status = 'on_trip'
                td['vehicle'].default_driver = td['driver']
                td['vehicle'].save(update_fields=['status', 'default_driver'])
    print(f"✓ Operational Trips seeded: {Trip.objects.count()}")

    # 7. Seed Depot Petty Cash Float
    cash_user = User.objects.filter(username__in=['cash_ramesh', 'admin']).first()
    petty_acc, _ = PettyCashAccount.objects.get_or_create(
        account_name='Coimbatore Central Depot Cash Register',
        defaults={
            'base_depot': DEPOT_COIMBATORE,
            'holder_user': cash_user,
            'allocated_limit': Decimal('100000.00'),
            'current_balance': Decimal('50000.00'),
            'opening_balance': Decimal('50000.00'),
            'is_active': True,
        }
    )
    print(f"✓ Depot Petty Cash Account verified: {petty_acc.account_name} (₹{petty_acc.current_balance})")

    print("=" * 80)
    print("OPERATIONS ECOSYSTEM SEED COMPLETE & READY FOR PRODUCTION TEST")
    print(f"Total Drivers: {Driver.objects.count()}")
    print(f"Total Parties: {Party.objects.count()}")
    print(f"Total Bookings: {Booking.objects.count()}")
    print(f"Total Trips: {Trip.objects.count()}")
    print("=" * 80)

if __name__ == '__main__':
    run_seed()
