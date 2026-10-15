"""
Seed Enterprise Fleet Vehicles across the 6 Operating Hubs:
- Coimbatore Central HQ
- Tirupur Branch
- Erode Branch
- Chennai Branch
- Hosur Branch
- Trichy Branch

Maps vehicles to VehicleCategory & VehicleType with authentic Tamil Nadu commercial RTO registrations.
"""

import os
import sys
import datetime
from decimal import Decimal
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import Vehicle, VehicleType, VehicleCategory, Driver
from core.depot_scoping import (
    DEPOT_COIMBATORE, DEPOT_TIRUPUR, DEPOT_ERODE,
    DEPOT_CHENNAI, DEPOT_HOSUR, DEPOT_TRICHY
)

def seed_fleet_vehicles():
    print("=" * 80)
    print("SEEDING ENTERPRISE REGIONAL FLEET VEHICLES")
    print("=" * 80)

    # Get categories
    cat_sedan = VehicleCategory.objects.get(code='sedan')
    cat_suv = VehicleCategory.objects.get(code='suv_muv')
    cat_van = VehicleCategory.objects.get(code='mini_coach')
    cat_coach = VehicleCategory.objects.get(code='luxury_coach')

    # Get sample vehicle types
    vt_sedan = VehicleType.objects.filter(seating_capacity=4, name__icontains='Dzire').first() or VehicleType.objects.filter(seating_capacity=4).first()
    vt_crysta = VehicleType.objects.filter(name__icontains='Crysta').first() or VehicleType.objects.filter(seating_capacity=7).first()
    vt_urbania = VehicleType.objects.filter(name__icontains='Urbania').first() or VehicleType.objects.filter(name__icontains='Tempo').first()
    vt_coach = VehicleType.objects.filter(seating_capacity__gte=40).first()

    today = datetime.date.today()
    one_year_later = today + datetime.timedelta(days=365)
    six_months_later = today + datetime.timedelta(days=180)

    # Pre-fetch a driver if available
    default_driver = Driver.objects.filter(status='active').first()

    FLEET_DATA = [
        # 1. COIMBATORE CENTRAL HQ
        {
            'reg': 'TN 38 BH 1008',
            'type': vt_crysta,
            'cat': cat_suv,
            'depot': DEPOT_COIMBATORE,
            'brand': 'Toyota',
            'model': 'Innova Crysta 2.4 ZX',
            'year': 2024,
            'color': 'Pearl White',
            'fuel': 'diesel',
            'seats': 7,
            'status': 'available',
            'gps': '865421045812901',
            'fastag': 'FASTAG-TN38-001',
            'km': 34200,
        },
        {
            'reg': 'TN 38 BJ 2045',
            'type': vt_urbania,
            'cat': cat_van,
            'depot': DEPOT_COIMBATORE,
            'brand': 'Force Motors',
            'model': 'Urbania Premium 17S',
            'year': 2024,
            'color': 'Silver Metallic',
            'fuel': 'diesel',
            'seats': 17,
            'status': 'available',
            'gps': '865421045812902',
            'fastag': 'FASTAG-TN38-002',
            'km': 48100,
        },
        {
            'reg': 'TN 38 BK 9009',
            'type': vt_coach,
            'cat': cat_coach,
            'depot': DEPOT_COIMBATORE,
            'brand': 'Volvo',
            'model': '9600 B11R Multi-Axle',
            'year': 2023,
            'color': 'Royal Blue',
            'fuel': 'diesel',
            'seats': 49,
            'status': 'available',
            'gps': '865421045812903',
            'fastag': 'FASTAG-TN38-003',
            'km': 112000,
        },
        # 2. TIRUPUR BRANCH
        {
            'reg': 'TN 39 CK 4410',
            'type': vt_urbania,
            'cat': cat_van,
            'depot': DEPOT_TIRUPUR,
            'brand': 'Force Motors',
            'model': 'Urbania Corporate Shifter',
            'year': 2024,
            'color': 'Pure White',
            'fuel': 'diesel',
            'seats': 17,
            'status': 'available',
            'gps': '865421045812904',
            'fastag': 'FASTAG-TN39-001',
            'km': 28900,
        },
        {
            'reg': 'TN 39 CL 5522',
            'type': vt_sedan,
            'cat': cat_sedan,
            'depot': DEPOT_TIRUPUR,
            'brand': 'Maruti Suzuki',
            'model': 'Dzire ZXi Tour',
            'year': 2023,
            'color': 'Silky Silver',
            'fuel': 'petrol',
            'seats': 4,
            'status': 'available',
            'gps': '865421045812905',
            'fastag': 'FASTAG-TN39-002',
            'km': 54300,
        },
        # 3. ERODE BRANCH
        {
            'reg': 'TN 33 DA 7788',
            'type': vt_coach,
            'cat': cat_coach,
            'depot': DEPOT_ERODE,
            'brand': 'BharatBenz',
            'model': 'Glider 1624 AC Sleeper',
            'year': 2023,
            'color': 'Crimson Red',
            'fuel': 'diesel',
            'seats': 40,
            'status': 'available',
            'gps': '865421045812906',
            'fastag': 'FASTAG-TN33-001',
            'km': 87600,
        },
        # 4. CHENNAI BRANCH
        {
            'reg': 'TN 07 EL 1122',
            'type': vt_crysta,
            'cat': cat_suv,
            'depot': DEPOT_CHENNAI,
            'brand': 'Toyota',
            'model': 'Innova Hycross Hybrid',
            'year': 2024,
            'color': 'Attitude Black',
            'fuel': 'petrol',
            'seats': 7,
            'status': 'available',
            'gps': '865421045812907',
            'fastag': 'FASTAG-TN07-001',
            'km': 19500,
        },
        {
            'reg': 'TN 10 FN 3344',
            'type': vt_sedan,
            'cat': cat_sedan,
            'depot': DEPOT_CHENNAI,
            'brand': 'Toyota',
            'model': 'Etios GD Platinum',
            'year': 2022,
            'color': 'Classic Grey',
            'fuel': 'diesel',
            'seats': 4,
            'status': 'available',
            'gps': '865421045812908',
            'fastag': 'FASTAG-TN10-001',
            'km': 92000,
        },
        {
            'reg': 'TN 14 GP 8899',
            'type': vt_coach,
            'cat': cat_coach,
            'depot': DEPOT_CHENNAI,
            'brand': 'Scania',
            'model': 'Metrolink HD 14.5M',
            'year': 2023,
            'color': 'Emerald Green',
            'fuel': 'diesel',
            'seats': 53,
            'status': 'available',
            'gps': '865421045812909',
            'fastag': 'FASTAG-TN14-001',
            'km': 135000,
        },
        # 5. HOSUR BRANCH
        {
            'reg': 'TN 70 HA 4050',
            'type': vt_urbania,
            'cat': cat_van,
            'depot': DEPOT_HOSUR,
            'brand': 'Force Motors',
            'model': 'Urbania Cross-Border Shifter',
            'year': 2024,
            'color': 'Arctic White',
            'fuel': 'diesel',
            'seats': 17,
            'status': 'available',
            'gps': '865421045812910',
            'fastag': 'FASTAG-TN70-001',
            'km': 31400,
        },
        {
            'reg': 'TN 24 HB 6070',
            'type': vt_sedan,
            'cat': cat_sedan,
            'depot': DEPOT_HOSUR,
            'brand': 'Maruti Suzuki',
            'model': 'Dzire CNG Tour S',
            'year': 2023,
            'color': 'Super White',
            'fuel': 'cng',
            'seats': 4,
            'status': 'available',
            'gps': '865421045812911',
            'fastag': 'FASTAG-TN24-001',
            'km': 42000,
        },
        # 6. TRICHY BRANCH
        {
            'reg': 'TN 45 KA 2345',
            'type': vt_crysta,
            'cat': cat_suv,
            'depot': DEPOT_TRICHY,
            'brand': 'Toyota',
            'model': 'Innova Crysta 2.4 GX',
            'year': 2023,
            'color': 'Garnet Red',
            'fuel': 'diesel',
            'seats': 7,
            'status': 'available',
            'gps': '865421045812912',
            'fastag': 'FASTAG-TN45-001',
            'km': 61200,
        },
        {
            'reg': 'TN 48 KB 9876',
            'type': vt_urbania,
            'cat': cat_van,
            'depot': DEPOT_TRICHY,
            'brand': 'Force Motors',
            'model': 'Tempo Traveller Temple Tourer',
            'year': 2023,
            'color': 'Sun Yellow / White',
            'fuel': 'diesel',
            'seats': 12,
            'status': 'available',
            'gps': '865421045812913',
            'fastag': 'FASTAG-TN48-001',
            'km': 73400,
        },
    ]

    created_cnt = 0
    updated_cnt = 0
    for v in FLEET_DATA:
        veh, created = Vehicle.objects.update_or_create(
            registration_number=v['reg'],
            defaults={
                'vehicle_type': v['type'],
                'vehicle_category': v['cat'],
                'base_depot': v['depot'],
                'brand': v['brand'],
                'model': v['model'],
                'year': v['year'],
                'color': v['color'],
                'fuel_type': v['fuel'],
                'seating_capacity': v['seats'],
                'status': v['status'],
                'has_ac': True,
                'ownership_type': 'owned',
                'current_km': v['km'],
                'gps_imei': v['gps'],
                'fastag_id': v['fastag'],
                'rc_expiry': one_year_later,
                'insurance_expiry': one_year_later,
                'fc_expiry': one_year_later,
                'permit_expiry': one_year_later,
                'pollution_expiry': six_months_later,
                'tax_expiry': one_year_later,
                'next_service_due_km': v['km'] + 5000,
                'default_driver': default_driver,
            }
        )
        tag = "CREATED" if created else "UPDATED"
        print(f"[{tag}] {veh.registration_number} -> {veh.vehicle_category.name} | {veh.base_depot}")
        if created:
            created_cnt += 1
        else:
            updated_cnt += 1

    print("=" * 80)
    print(f"COMPLETED: {created_cnt} vehicles created, {updated_cnt} vehicles updated.")
    print("=" * 80)

if __name__ == '__main__':
    seed_fleet_vehicles()
